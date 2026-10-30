"""Deterministic source normalization and compact, lazy Lua emission."""
from __future__ import annotations

import copy
from collections import Counter
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile

from . import SCHEMA_VERSION, RULES_VERSION
from .model import (PRODUCT, SourceError, canonical, checked_bytes, discover, integer,
                    load_tables, parse_page, sha256)


def array_value(row, name, index, default=None):
    return row.get(f"{name}_{index}", row.get(f"{name}[{index}]", default))


def unique(values):
    return [json.loads(value) for value in sorted({canonical(value) for value in values})]


def mask_ids(value, table, race=False):
    mask = integer(value)
    if mask in (0, -1):
        return []
    if mask < 0:
        # A signed field has the same fixed-width bits; Python preserves them.
        mask &= (1 << 64) - 1
    result = []
    bits = {}
    for row in table:
        entity = integer(row["ID"])
        bit = integer(row.get("PlayableRaceBit"), -1) if race else entity - 1
        if bit >= 0:
            bits.setdefault(bit, []).append(entity)
    for bit, entities in bits.items():
        if mask & (1 << bit):
            if len(entities) != 1:
                raise SourceError("ambiguous race/class bit mapping")
            result.append(entities[0])
            mask &= ~(1 << bit)
    if mask:
        raise SourceError("mask contains unmapped identity bits")
    if not result:
        raise SourceError("mask has no mapped player identity")
    return sorted(result)


def vendor_cost(value):
    """Read both legacy gold and Forever gold/currency/item cost tuples."""
    def number(value):
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], list):
        return {}
    parts = value[0]
    if len(parts) == 1 and number(parts[0]):
        return {'price': parts[0]}
    if len(parts) != 3 or not number(parts[0]) or not all(isinstance(x, list) for x in parts[1:]):
        return {}
    def costs(rows):
        if any(not isinstance(row, list) or len(row) != 2 or not number(row[0]) or row[0] == 0
               or not number(row[1]) or row[1] == 0 for row in rows):
            return None
        return [{'id': row[0], 'count': row[1]} for row in rows]
    currencies, items = costs(parts[1]), costs(parts[2])
    if currencies is None or items is None:
        return {}
    result = {'price': parts[0]}
    if currencies or items:
        result.update(hasExtendedCost=True, currencies=currencies, costItems=items)
        if len(currencies) == 1:
            result.update(currencyID=currencies[0]['id'], currencyAmount=currencies[0]['count'])
    return result


def normalize(raw, manifest):
    if manifest.get("schema") != SCHEMA_VERSION or manifest.get("product") != PRODUCT or not manifest.get("fetchComplete"):
        raise SourceError("snapshot is not a completed latest-product acquisition")
    build = manifest.get("build", "")
    after = manifest.get("latestAfter", {})
    if after.get("version") != build or after.get("build_config") != manifest.get("buildInfo", {}).get("build_config"):
        raise SourceError("snapshot mixed versions or was not rechecked")
    tables = load_tables(raw, manifest)
    members, teaching = discover(tables)
    responses = {record["key"]: record for record in manifest["responses"]}
    evidence = list(responses.values())
    while evidence:
        record = evidence.pop()
        if "path" in record:
            checked_bytes(raw, record)
        evidence.extend(record.get("attemptHistory", []))
    sparse = {integer(row["ID"]): row for row in tables["ItemSparse"]}
    level_rows = tables['SpellLevels']
    level_schema = bool(level_rows) and all({'SpellID', 'DifficultyID', 'BaseLevel', 'SpellLevel'}.issubset(row) for row in level_rows)
    levels = {}
    for row in level_rows:
        if integer(row.get('SpellID')) > 0 and integer(row.get('DifficultyID')) == 0:
            levels[integer(row['SpellID'])] = max(integer(row.get('BaseLevel')), integer(row.get('SpellLevel')))
    page_cache, audit, facts = {}, [], {}

    def page(kind, entity):
        key = f"web:{kind}:{entity}"
        if key not in page_cache:
            record = responses.get(key)
            status = record["status"] if record else "notFetched"
            value = None
            if status == "verified":
                try:
                    value = parse_page(checked_bytes(raw, record), kind, entity, record["finalUrl"])
                except (SourceError, UnicodeError):
                    status = "parseError"
            page_cache[key] = value, status
        return page_cache[key]

    def quest_conditions(entity):
        data, status = page("quest", entity)
        conditions = []
        if data:
            text = " ".join(data["markup"])
            level = re.search(r"Requires level (\d+)", text)
            if level:
                conditions.append({"kind": "level", "value": int(level.group(1))})
            side = re.search(r"Side:.*?(Horde|Alliance)", text)
            if side:
                conditions.append({"kind": "faction", "value": "H" if side.group(1) == "Horde" else "A"})
        # Reading a quest page does not establish every prerequisite, objective,
        # reward choice and delivery cost; quest acquisition is never free stock.
        return {"id": entity, "conditions": conditions, "conditionsKnown": False,
                "status": "unknown", "missingReasons": [status if status != "verified" else "learningRequirementsUnknown"]}

    for (slug, spell), ability_rows in sorted(members.items()):
        web, web_status = page("spell", spell)
        recipe = next((row for row in (web or {}).get("listviews", {}).get("recipes", ())
                       if integer(row.get("id")) == spell), {})
        gaps, base_conditions = [], []
        if web_status != "verified":
            gaps.append(web_status)
        base_known = True
        class_masks = {integer(row.get("ClassMask")) for row in ability_rows}
        class_mask = 0 if 0 in class_masks else sum(set(class_masks)) if len(class_masks) == 1 else None
        if class_mask is None:
            gaps.append("sourceConflict"); base_known = False
        elif class_mask:
            try:
                base_conditions.append({"kind": "classIDs", "values": mask_ids(class_mask, tables["ChrClasses"])})
            except SourceError:
                gaps.append("unsupportedClassMask"); base_known = False
        race_filter = any(integer(array_value(row, "RaceMasks", i, 0)) != 0
                          for row in ability_rows for i in (0, 1))
        race_ids = []
        if web:
            for markup in web["markup"]:
                if "Races:" in markup:
                    race_ids.extend(int(value) for value in re.findall(r"\[race=(\d+)\]", markup))
            if not race_ids and recipe.get("reqrace"):
                try:
                    race_ids = mask_ids(recipe["reqrace"], tables["ChrRaces"], race=True)
                except SourceError:
                    pass
        if race_ids:
            valid_ids = {integer(row["ID"]) for row in tables["ChrRaces"]}
            if set(race_ids).issubset(valid_ids):
                base_conditions.append({"kind": "raceIDs", "values": sorted(set(race_ids))})
            else:
                gaps.append("unsupportedRaceMask"); base_known = False
        elif race_filter:
            gaps.append("unsupportedRaceMask"); base_known = False
        profession_id = integer(ability_rows[0]["SkillLine"])
        if integer(recipe.get("learnedat")) > 0:
            base_conditions.append({"kind": "skill", "professionID": profession_id, "value": integer(recipe["learnedat"])})
        if integer(recipe.get("specialization")) > 0:
            base_conditions.append({"kind": "ability", "value": integer(recipe["specialization"])})
        if integer(recipe.get("level")) > 0:
            base_conditions.append({"kind": "level", "value": integer(recipe["level"])})
        routes = []
        # AutomaticSkillRank=1 is handled by the server's LearnSkillRewardedSpells.
        # This is affirmative same-build DB2 evidence, not absence of a book/NPC.
        ranks = {integer(row.get('MinSkillLineRank')) for row in ability_rows}
        if all(integer(row.get('AcquireMethod')) == 1 for row in ability_rows) and len(ranks) == 1 and min(ranks) > 0:
            rank = min(ranks)
            conditions = [copy.deepcopy(condition) for condition in base_conditions
                          if condition['kind'] not in ('skill', 'level')]
            conditions.append({'kind': 'skill', 'professionID': profession_id, 'value': rank})
            if levels.get(spell, 0) > 0:
                conditions.append({'kind': 'level', 'value': levels[spell]})
            known = base_known and level_schema
            if not level_schema:
                gaps.append('learningRequirementsUnknown')
            routes.append({'id': f'trainer:{spell}', 'kind': 'trainer', 'trainerIDs': [],
                'status': 'confirmed' if known else 'unknown', 'conditionsKnown': known, 'conditions': unique(conditions),
                'trainingCost': 0, 'acquisition': {'coverage': 'complete', 'status': 'confirmed', 'conditions': [],
                    'kind': 'skillGrant', 'skillLineID': profession_id, 'minSkillRank': rank, 'acquireMethod': 1}})
        trainer_ids = sorted({integer(row.get("id")) for row in (web or {}).get("listviews", {}).get("taught-by-npc", ())
                              if integer(row.get("id")) > 0})
        if trainer_ids and not routes:
            known = base_known and "learnedat" in recipe and integer(recipe["learnedat"]) > 0
            route = {"id": f"trainer:{spell}", "kind": "trainer", "trainerIDs": trainer_ids,
                     "status": "confirmed" if known else "unknown", "conditionsKnown": known,
                     "conditions": unique(base_conditions), "acquisition": {"coverage": "partial", "status": "confirmed", "conditions": []}}
            if "trainingcost" in recipe and integer(recipe["trainingcost"], -1) >= 0:
                route["trainingCost"] = integer(recipe["trainingcost"])
            routes.append(route)
        items = dict(teaching.get(spell, {}))
        for row in (web or {}).get("listviews", {}).get("taught-by-item", ()):
            if integer(row.get("id")) > 0:
                items.setdefault(integer(row["id"]), [])
        for item, effect_rows in sorted(items.items()):
            conditions = copy.deepcopy(base_conditions)
            row = sparse.get(item)
            # First Aid's zero-orange web rows display the yellow threshold as
            # learnedat. A same-build teaching book states the real requirement
            # (e.g. Greater Healing Potion 155, yellow 175). Do not add both as
            # cumulative learning requirements. Other native professions keep
            # their existing policy until separately audited.
            if (slug == 'first-aid' and row and integer(row.get('RequiredSkillRank')) > 0
                    and integer(row.get('RequiredSkill')) in (129, 2942)):
                conditions = [c for c in conditions if c.get('kind') != 'skill']
            item_page, item_status = page("item", item)
            item_gaps = []
            known = base_known
            if row is None:
                known = False; item_gaps.append("itemDetailsMissing")
            else:
                for column in ("RequiredSkill", "RequiredSkillRank", "RequiredLevel", "AllowableClass", "RequiredAbility", "MinFactionID", "MinReputation"):
                    if column not in row:
                        known = False; item_gaps.append("learningRequirementsUnknown")
                for column, kind in (("RequiredLevel", "level"), ("RequiredAbility", "ability")):
                    value = integer(row.get(column))
                    if value > 0:
                        conditions.append({"kind": kind, "value": value})
                if integer(row.get("RequiredSkill")) > 0 and integer(row.get("RequiredSkillRank")) > 0:
                    conditions.append({"kind": "skill", "professionID": integer(row["RequiredSkill"]), "value": integer(row["RequiredSkillRank"])})
                if integer(row.get("MinFactionID")) > 0:
                    # ItemSparse uses the zero-based ReputationRank enum
                    # (Hated=0..Exalted=7); the client faction API returns
                    # reaction/standingID as Hated=1..Exalted=8. Missing or
                    # unsupported values must not default to Hated.
                    try:
                        standing = integer(row.get("MinReputation"), None)
                    except SourceError:
                        standing = None
                    if standing is not None and 0 <= standing <= 7:
                        conditions.append({"kind": "reputation", "factionID": integer(row["MinFactionID"]), "value": standing + 1})
                    else:
                        known = False; item_gaps.append("learningRequirementsUnknown")
                if any(integer(row.get(field)) != 0 for field in ("RequiredPVPMedal", "RequiredPVPRank", "RequiredHoliday",
                        "RequiredTransmogHoliday", "ContentTuningID", "InstanceBound")):
                    known = False; item_gaps.append("learningRequirementsUnknown")
                mask = integer(row.get("AllowableClass"), -1)
                if mask not in (0, -1):
                    try:
                        # Item masks can include reserved/future class bits
                        # (e.g. 32767 in Classic). If every class in this exact
                        # build is allowed, those unused bits add no restriction.
                        # A restricted mask still requires a complete mapping.
                        class_bits = {1 << (integer(value["ID"]) - 1) for value in tables["ChrClasses"]
                                      if integer(value["ID"]) > 0}
                        all_classes = sum(class_bits)
                        if not all_classes or mask & all_classes != all_classes:
                            conditions.append({"kind": "classIDs", "values": mask_ids(mask, tables["ChrClasses"])})
                    except SourceError:
                        known = False; item_gaps.append("unsupportedClassMask")
                elif mask == 0:
                    known = False; item_gaps.append("unsupportedClassMask")
                race_words = [array_value(row, "AllowableRace", i) for i in (0, 1)]
                if any(value is None for value in race_words) or any(integer(value) != -1 for value in race_words):
                    ids = []
                    for markup in (item_page or {}).get("markup", ()):
                        if "Races:" in markup:
                            ids.extend(int(value) for value in re.findall(r"\[race=(\d+)\]", markup))
                    if ids:
                        conditions.append({"kind": "raceIDs", "values": sorted(set(ids))})
                    else:
                        known = False; item_gaps.append("unsupportedRaceMask")
            if any(integer(effect.get("PlayerConditionID")) != 0 for effect in effect_rows):
                # This field is marked unverified in the schema. Preserve the
                # reference, not a guessed flattening of AND/OR condition logic.
                known = False; item_gaps.append("unsupportedPlayerCondition")
            vendors = []
            for vendor in (item_page or {}).get("listviews", {}).get("sold-by", ()):
                if integer(vendor.get('id')) <= 0:
                    continue
                quote = {'id': integer(vendor['id']), 'npcID': integer(vendor['id']),
                         'status': 'unknown', 'conditionsKnown': False, **vendor_cost(vendor.get('cost'))}
                quantity = integer((row or {}).get('VendorStackCount'))
                if quantity > 0:
                    quote['quantity'] = quantity
                if isinstance(vendor.get('name') or vendor.get('displayName'), str):
                    quote['name'] = vendor.get('name') or vendor['displayName']
                if isinstance(vendor.get('location'), list):
                    quote['areas'] = vendor['location']
                if isinstance(vendor.get('stock'), int):
                    quote.update(stock=vendor['stock'], unlimited=vendor['stock'] < 0)
                vendors.append(quote)
            quests = [quest_conditions(integer(value["id"])) for value in
                      (item_page or {}).get("listviews", {}).get("reward-from-q", ()) if integer(value.get("id")) > 0]
            drops = [{"id": integer(value["id"])} for value in
                     (item_page or {}).get("listviews", {}).get("dropped-by", ()) if integer(value.get("id")) > 0]
            # A listed NPC and a gold quote do not establish that this player
            # can reach/unlock this offer (quest, phase, faction, event, etc.).
            # Native verified offers and live merchant observations are separate
            # runtime evidence. Keep web quotes as references until then.
            acquisition = {"coverage": "partial", "status": "unknown",
                           "conditionsKnown": False, "conditions": [], "vendors": vendors, "quests": quests, "drops": drops}
            if row and "Bonding" in row:
                bonding = integer(row["Bonding"])
                if bonding in (0, 1, 2, 3, 4, 5):
                    acquisition["bindingType"] = bonding
                    acquisition["bindingSource"] = "ItemSparse"
            elif (item_page or {}).get("bindingType") in (1, 2, 3):
                acquisition["bindingType"] = item_page["bindingType"]
                acquisition["bindingSource"] = "wowhead:item-tooltip"
            if "bindingType" in acquisition:
                bonding = acquisition["bindingType"]
                acquisition["nonAuctionable"] = bonding in (1, 4, 5)
                acquisition["bindOnPickup"] = bonding == 1
            # Knowing where an item comes from is separate from confirming
            # access to a particular vendor/quest. Retain unknown access flags;
            # do not label an explicitly listed source as missing.
            if not (vendors or quests or drops):
                item_gaps.append("acquisitionSourceMissing")
            if item_status != "verified":
                item_gaps.append(item_status)
            route = {"id": f"item:{spell}:{item}", "kind": "item", "teachingItemID": item,
                     "status": "confirmed" if known else "unknown", "conditionsKnown": known,
                     "conditions": unique(conditions), "acquisition": acquisition}
            routes.append(route)
            gaps.extend(item_gaps)
        for value in (web or {}).get("listviews", {}).get("reward-from-q", ()):
            quest_id = integer(value.get("id"))
            if quest_id > 0:
                quest = quest_conditions(quest_id)
                routes.append({"id": f"quest:{spell}:{quest_id}", "kind": "quest", "questIDs": [quest_id],
                    "conditionsKnown": False, "status": "unknown", "conditions": unique(base_conditions + [{"kind": "quest", "value": quest_id}]),
                    "acquisition": {"coverage": "partial", "status": "unknown", "conditions": [], "quests": [quest]}})
        if not routes:
            gaps.append("learningSourceMissing")
        complete = bool(routes) and all(route["conditionsKnown"] for route in routes) and not gaps
        record = {"spell": spell, "profession": slug, "coverage": "complete" if complete else "partial" if routes else "none",
                  "routes": routes, "missingReasons": sorted(set(gaps))}
        facts.setdefault(slug, {})[spell] = record
        if gaps or not complete:
            audit.append({"profession": slug, "spell": spell, "coverage": record["coverage"], "missingReasons": record["missingReasons"],
                          "paths": [{"id": route["id"], "status": route["status"], "conditionsKnown": route["conditionsKnown"]} for route in routes],
                          "abilityRowIDs": sorted(integer(value["ID"]) for value in ability_rows)})
    return facts, audit


def base36(value):
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value < 0:
        return "-" + base36(-value)
    if value == 0:
        return "0"
    result = ""
    while value:
        value, rest = divmod(value, 36)
        result = alphabet[rest] + result
    return result


def lua_quote(value):
    return '"' + "".join("\\" + char if char in '\\"' else "\\%03d" % ord(char)
                         if ord(char) < 32 else char for char in value) + '"'


def runtime_facts(facts):
    """Keep full NPC drop evidence offline, never as guaranteed game stock.

    Drop NPC enumerations do not confirm learning or procurement eligibility.
    Omitting that optional list also leaves the native dev drop view intact.
    Trainer IDs, teaching items, conditions, quests and vendor quotes survive.
    """
    projected = copy.deepcopy(facts)
    for records in projected.values():
        for record in records.values():
            for route in record['routes']:
                acquisition = route.get('acquisition', {})
                drops = acquisition.pop('drops', [])
                if drops:
                    acquisition['dropSourceCount'] = len(drops)
                    acquisition['dropDetailsOffline'] = True
                for vendor in acquisition.get('vendors', []):
                    # Names/areas are already indexed by native NPC data; full
                    # web labels remain in the audit, not duplicated per offer.
                    vendor.pop('name', None)
                    vendor.pop('areas', None)
                    if vendor.get('npcID') == vendor.get('id'):
                        vendor.pop('npcID', None)
    return projected


def specialization_groups(record):
    """Compact OR-of-AND specialization requirements, including known recipes."""
    supported = {20219, 20222, 9787, 9788, 17039, 17040, 17041, 10656, 10658, 10660}
    groups = []
    for route in record.get('routes', []):
        group = sorted({c['value'] for c in route.get('conditions', [])
                        if c.get('kind') == 'ability' and c.get('value') in supported})
        if not group:
            return []
        if group not in groups:
            groups.append(group)
    return groups


def automatic_skill_rank(record):
    """Index only explicit, confirmed skill grants; full eligibility stays on the path."""
    ranks = set()
    for route in record.get('routes', []):
        acquisition = route.get('acquisition', {})
        rank = acquisition.get('minSkillRank')
        if (route.get('kind') == 'trainer' and route.get('status') == 'confirmed'
                and route.get('conditionsKnown') is True and acquisition.get('kind') == 'skillGrant'
                and acquisition.get('status') == 'confirmed' and acquisition.get('coverage') == 'complete'
                and acquisition.get('conditionsKnown') is not False
                and acquisition.get('acquireMethod') == 1 and type(rank) is int and rank > 0
                and any(c.get('kind') == 'skill' and c.get('professionID') == acquisition.get('skillLineID')
                        and c.get('value') == rank for c in route.get('conditions', []))):
            ranks.add(rank)
    return next(iter(ranks)) if len(ranks) == 1 else None


def emit_lua(facts, meta):
    strings, string_ids = [], {}
    pools = {name: [] for name in ("conditions", "acquisition", "sets", "gaps")}
    pool_ids = {name: {} for name in pools}
    nested_counts, shared_ids, shared_values = Counter(), {}, []
    shape_ids, shapes = {}, []

    def intern(name, value):
        key = canonical(value)
        if key not in pool_ids[name]:
            pool_ids[name][key] = len(pools[name]) + 1
            pools[name].append(value)
        return pool_ids[name][key]

    def pack(value, literal=False):
        if isinstance(value, (list, dict)) and not literal:
            key = canonical(value)
            if nested_counts[key] > 1:
                if key not in shared_ids:
                    shared_ids[key] = len(shared_values) + 1
                    shared_values.append(None)
                    shared_values[shared_ids[key] - 1] = pack(value, literal=True)
                return "r" + base36(shared_ids[key]) + ";"
        if value is None:
            return "_"
        if value is True:
            return "t"
        if value is False:
            return "f"
        if isinstance(value, int):
            if abs(value) > 2**53 - 1:
                raise SourceError("inexact integer cannot enter Lua runtime")
            if 1 <= value <= 36:
                return "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"[value - 1]
            return "z" if value == 0 else "n" + base36(value) + ";"
        if isinstance(value, str):
            if value not in string_ids:
                string_ids[value] = len(strings) + 1
                strings.append(value)
            return "s" + base36(string_ids[value]) + ";"
        if isinstance(value, list):
            return "[" + "".join(pack(item) for item in value) + "]"
        if isinstance(value, dict):
            constants, dynamic = [], []
            for key in sorted(value):
                child = value[key]
                if isinstance(child, (str, bool)) or child == [] or child in (-1, 0, 1):
                    constants.extend((key, child))
                else:
                    dynamic.append(key)
            shape = [constants, dynamic]
            identity = canonical(shape)
            if identity not in shape_ids:
                shape_ids[identity] = len(shapes) + 1
                shapes.append(shape)
            return "m" + base36(shape_ids[identity]) + ";" + "".join(pack(value[key]) for key in dynamic)
        raise SourceError("unsupported runtime value")

    profiles = {}
    kind_ids = {"trainer": 1, "item": 2, "quest": 3}
    status_ids = {"unknown": 0, "confirmed": 1, "conflict": 2}
    coverage_ids = {"none": 0, "partial": 1, "complete": 2}
    for slug, records in sorted(facts.items()):
        lines = []
        previous_spell = 0
        for spell, record in sorted(records.items()):
            routes = []
            for route in record["routes"]:
                kind = kind_ids[route["kind"]]
                flags = kind + status_ids[route["status"]] * 4 + int(route["conditionsKnown"]) * 16
                conditions = intern("conditions", route["conditions"])
                # Preserve template interning order; only the private route
                # encoding changes, never normalized facts or public fields.
                trainers = intern("sets", route.get("trainerIDs", []))
                quests = intern("sets", route.get("questIDs", []))
                acquisition = intern("acquisition", route.get("acquisition", {}))
                if kind == 1:
                    routes.append([flags, conditions, acquisition, route.get("trainingCost", -1), trainers])
                elif kind == 2:
                    routes.append([flags, route.get("teachingItemID", 0), conditions, acquisition])
                else:
                    routes.append([flags, quests, conditions, acquisition])
            lines.append(base36(spell - previous_spell) + ":" + pack([coverage_ids[record["coverage"]], intern("gaps", record["missingReasons"]), routes]))
            previous_spell = spell
        profiles[slug] = "\n".join(lines)
    def count_nested(value):
        if isinstance(value, (list, dict)):
            key = canonical(value)
            if len(key) >= 24:
                nested_counts[key] += 1
            for child in value.values() if isinstance(value, dict) else value:
                count_nested(child)
    for values in pools.values():
        for value in values:
            count_nested(value)
    encoded_pools = {name: [pack(value) for value in values] for name, values in pools.items()}
    encoded_shapes = [pack(value) for value in shapes]
    # String interning completes before serializing STR.
    lines = ["-- Generated by data_pipeline.professions; edit sources/rules, never this file.",
             "local _,ns=...", "if not ns.IsForever then return end",
             "local STR={" + ",".join(lua_quote(value) for value in strings) + "}", "local RAW={}"]
    for slug, value in profiles.items():
        lines.append("RAW[" + lua_quote(slug) + "]=" + lua_quote(value))
    lines.append('local GRANTS={}')
    for slug, records in sorted(facts.items()):
        grants = [(spell, automatic_skill_rank(record)) for spell, record in sorted(records.items())]
        value = ';'.join(f'{spell}:{rank}' for spell, rank in grants if rank is not None)
        if value:
            lines.append('GRANTS[' + lua_quote(slug) + ']=' + lua_quote(value))
    lines.append('local SPECIALIZATIONS={}')
    for slug, records in sorted(facts.items()):
        entries = []
        for spell, record in sorted(records.items()):
            groups = specialization_groups(record)
            if groups:
                value = '{' + ','.join('{' + ','.join(map(str, group)) + '}' for group in groups) + '}'
                entries.append('[' + str(spell) + ']=' + value)
        if entries:
            lines.append('SPECIALIZATIONS[' + lua_quote(slug) + ']={' + ','.join(entries) + '}')
    for name, values in encoded_pools.items():
        lines.append("local " + name.upper() + "=" + lua_quote("\n".join(values)))
    lines.append("local SHARED=" + lua_quote("\n".join(shared_values)))
    lines.append("local SHAPES=" + lua_quote("\n".join(encoded_shapes)))
    lines.append("local meta={schema=1,rules=" + str(RULES_VERSION) + ",product=" + lua_quote(PRODUCT) + ",build=" + lua_quote(meta["build"]) + ",fingerprint=" + lua_quote(meta["fingerprint"]) + "}")
    lines.append(r'''
local pooled
local function unpackValue(text)
 local p=1
 local function take()
  local c=text:sub(p,p);p=p+1
  local byte=c:byte();if byte>=65 and byte<=90 then return byte-64 elseif byte>=48 and byte<=57 then return byte-21 end
  if c=="z"then return 0 elseif c=="t"then return true elseif c=="f"then return false elseif c=="_"then return nil end
  if c=="n"or c=="s"or c=="r"or c=="m"then
   local e=assert(text:find(";",p,true));local first,sign=p,1
   if text:sub(first,first)=="-"then first=first+1;sign=-1 end
   local n=0;for i=first,e-1 do local b=text:byte(i);n=n*36+(b<=57 and b-48 or b-87)end
   n=n*sign;p=e+1
   if c=="s"then return assert(STR[n])elseif c=="r"then return pooled("shared",n,SHARED)
   elseif c=="m"then
    local shape=pooled("shapes",n,SHAPES);local value={}
    for i=1,#shape[1],2 do value[shape[1][i]]=shape[1][i+1]end
    for _,key in ipairs(shape[2])do value[key]=take()end;return value
   end;return n
  end
  local value={}
  if c=="["then
   while text:sub(p,p)~="]"do value[#value+1]=take()end;p=p+1
  elseif c=="{"then
   while text:sub(p,p)~="}"do local key=take();value[key]=take()end;p=p+1
  else error("Invalid profession learning codec")end
  return value
 end
 return take()
end
local function weakValues()return setmetatable({}, {__mode="v"})end
local function AutomaticSkillRank(slug,spell)
 local values=GRANTS[slug]
 if type(values)=="string"then
  local text=values;values={};GRANTS[slug]=values
  for id,rank in text:gmatch("(%d+):(%d+)")do values[tonumber(id)]=tonumber(rank)end
 end
 return values and values[spell]or nil
end
local decoded={conditions=weakValues(),acquisition=weakValues(),sets=weakValues(),gaps=weakValues(),shared=weakValues(),shapes=weakValues()}
local poolOffsets={}
pooled=function(name,id,raw)
 local values=decoded[name]
 if not values[id]then
  local offsets=poolOffsets[name]
  if not offsets then
   offsets={};poolOffsets[name]=offsets;local start=1
   while start<=#raw do
    offsets[#offsets+1]=start;local finish=raw:find("\n",start,true)
    if not finish then break end;start=finish+1
   end
  end
  local start=assert(offsets[id]);local finish=(offsets[id+1]or #raw+2)-2
  values[id]=unpackValue(raw:sub(start,finish))
 end;return values[id]
end
local indexes,caches,views={},{},{}
local kinds={[1]="trainer",[2]="item",[3]="quest"}
local statuses={[0]="unknown",[1]="confirmed",[2]="conflict"}
local coverages={[0]="none",[1]="partial",[2]="complete"}
local function index(slug)
 if not indexes[slug]then
  local values={};indexes[slug]=values;caches[slug]=weakValues()
  local text=RAW[slug]or "";local start,spell,ordinal=1,0,0
  while start<=#text do
   local colon=text:find(":",start,true);local finish=text:find("\n",colon,true)or #text+1
   spell=spell+tonumber(text:sub(start,colon-1),36);ordinal=ordinal+1
   assert(ordinal<65536);values[spell]=(colon+1)*65536+ordinal;start=finish+1
  end
 end
 return indexes[slug]
end
-- Compact immutable views keep array slots (16 bytes) rather than duplicating
-- hash nodes for every named field. Materialization is explicit at persistence
-- boundaries; normal callers retain the same named-field API.
local floor=math.floor
local function readOnly()error("Profession learning source views are read-only")end
local routeMT={__newindex=readOnly}
routeMT.__index=function(t,key)
 local flags=t[2];local kind=flags%4
 if key=="kind"then return kinds[kind]
 elseif key=="status"then return statuses[floor(flags/4)%4]
 elseif key=="conditionsKnown"then return flags>=16
 elseif key=="conditions"then return pooled("conditions",t[4],CONDITIONS)
 elseif key=="acquisition"then return pooled("acquisition",t[5],ACQUISITION)
 elseif key=="teachingItemID"then if kind==2 then return t[3]end
 elseif key=="trainingCost"then if kind==1 and t[6]and t[6]>=0 then return t[6]end
 elseif key=="trainerIDs"then if kind==1 and t[7]then return pooled("sets",t[7],SETS)end
 elseif key=="questIDs"then if kind==3 then return pooled("sets",t[3],SETS)end
 elseif key=="id"then
  local id=kinds[kind]..":"..t[1]
  if kind==2 then return id..":"..t[3]elseif kind==3 then return id..":"..pooled("sets",t[3],SETS)[1]end
  return id
 end
end
local function routeProjection(t)
 return {id=t.id,kind=t.kind,status=t.status,conditionsKnown=t.conditionsKnown,conditions=t.conditions,
  acquisition=t.acquisition,teachingItemID=t.teachingItemID,trainingCost=t.trainingCost,
  trainerIDs=t.trainerIDs,questIDs=t.questIDs}
end
routeMT.__profLearningMaterialize=routeProjection
local recordMTs={}
local function recordIndex(t,key)
 if key=="spell"then return t[1]elseif key=="profession"then return getmetatable(t).profession
 elseif key=="coverage"then return coverages[t[2]]elseif key=="missingReasons"then return pooled("gaps",t[3],GAPS)
 elseif key=="routes"then return t[4]end
end
local function recordProjection(t)
 return {spell=t.spell,profession=t.profession,coverage=t.coverage,missingReasons=t.missingReasons,routes=t.routes}
end
local function Get(slug,spell)
 if type(slug)~="string"or type(spell)~="number"then return nil end
 local values=index(slug);local cache=caches[slug]
 if not values[spell]then return nil end
 local offset=values[spell];local start=floor(offset/65536);local ordinal=offset-start*65536
 if cache[ordinal]then return cache[ordinal]end
 local text=RAW[slug];local finish=text:find("\n",start,true)or #text+1
 local value=unpackValue(text:sub(start,finish-1));local routes={}
 for _,row in ipairs(value[3])do
  local flags=row[1];local kind=flags%4;local route
  if kind==1 then route={spell,flags,0,row[2],row[3],row[4],row[5]}
  else route={spell,flags,row[2],row[3],row[4]}end
  routes[#routes+1]=setmetatable(route,routeMT)
 end
 local mt=recordMTs[slug]
 if not mt then mt={profession=slug,__index=recordIndex,__newindex=readOnly,__profLearningMaterialize=recordProjection};recordMTs[slug]=mt end
 local record=setmetatable({spell,value[1],value[2],routes},mt)
 cache[ordinal]=record
 return record
end
local function ForProfession(slug)
 if not views[slug]then views[slug]=setmetatable({}, {__index=function(_,spell)return Get(slug,spell)end,__newindex=readOnly})end
 return views[slug]
end
local function Each(slug)
 local values=index(slug);local previous
 return function()previous=next(values,previous);if previous then return previous,Get(slug,previous)end end
end
local function Materialize(value,seen)
 if type(value)~="table"then return value end
 seen=seen or {};if seen[value]then return seen[value]end
 local result={};seen[value]=result
 local mt=getmetatable(value);local projection=mt and mt.__profLearningMaterialize
 for key,child in pairs(projection and projection(value)or value)do result[key]=Materialize(child,seen)end
 return result
end
local function SpecializationGroups(slug,spell)
 return SPECIALIZATIONS[slug]and SPECIALIZATIONS[slug][spell]
end
ns.ProfLearningSources={meta=meta,Get=Get,ForProfession=ForProfession,Each=Each,Materialize=Materialize,AutomaticSkillRank=AutomaticSkillRank,SpecializationGroups=SpecializationGroups}
'''.strip())
    return ("\n".join(lines) + "\n").encode("utf-8")


def build(raw, output, report_path, check=False):
    raw, output, report_path = Path(raw), Path(output), Path(report_path)
    if output.resolve() == report_path.resolve():
        raise SourceError("Lua output and report paths must differ")
    if not check and output.parent.name == "Data" and output.name != "Data_ProfLearningSources.lua":
        raise SourceError("refusing to overwrite an existing native Data contract")
    if raw.is_file():
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="df-learning-replay-", dir=report_path.parent) as temp:
            target = Path(temp)
            with zipfile.ZipFile(raw) as archive:
                for entry in archive.infolist():
                    if not (target / entry.filename).resolve().is_relative_to(target.resolve()):
                        raise SourceError("archive path escapes package")
                archive.extractall(target)
            return build(target, output, report_path, check=check)
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    facts, gaps = normalize(raw, manifest)
    runtime = runtime_facts(facts)
    semantic = {"schema": SCHEMA_VERSION, "rules": RULES_VERSION, "product": PRODUCT,
                "build": manifest["build"], "professions": runtime}
    fingerprint = sha256(canonical(semantic).encode("utf-8"))
    lua = emit_lua(runtime, {"build": manifest["build"], "fingerprint": fingerprint})
    report = {"schema": SCHEMA_VERSION, "rules": RULES_VERSION, "product": PRODUCT,
              "build": manifest["build"], "fingerprint": fingerprint, "generationInput": False,
              "summary": {"recipes": sum(len(records) for records in facts.values()), "recipesWithGaps": len(gaps),
                          "confirmedPaths": sum(route["status"] == "confirmed" for rows in facts.values() for row in rows.values() for route in row["routes"]),
                          "luaBytes": len(lua)}, "gaps": gaps,
              "evidence": [{key: value for key, value in record.items() if key in
                  ("key", "url", "finalUrl", "status", "httpStatus", "path", "sha256", "fetchedAt", "error")}
                  for record in sorted(manifest["responses"], key=lambda record: record["key"])],
              "facts": facts}
    report['runtimeProjection'] = {'policy': 'compact-source-references-v2',
        'offlineDropReferences': sum(len(route.get('acquisition', {}).get('drops', []))
            for records in facts.values() for record in records.values() for route in record['routes']),
        'preserved': ['learning paths', 'teaching items', 'trainer IDs', 'learning conditions',
                      'quest conditions', 'vendor quotes', 'nonAuctionable', 'coverage and gaps'],
        'nativeDropData': 'unchanged; runtime projection does not overwrite it',
        'vendorLabelsAndAreas': 'offline; native NPC indexes supply runtime labels',
        'duplicateVendorIDs': 'id retained; identical npcID alias omitted'}
    report["professions"] = {slug: {"recipes": len(rows),
        "confirmedPaths": sum(route["status"] == "confirmed" for row in rows.values() for route in row["routes"]),
        "unknownPaths": sum(route["status"] != "confirmed" for row in rows.values() for route in row["routes"]),
        "missingReasons": dict(sorted(Counter(reason for row in rows.values() for reason in row["missingReasons"]).items()))}
        for slug, rows in sorted(facts.items())}
    report["sourceStatuses"] = dict(sorted(Counter(row["status"] for row in manifest["responses"]).items()))
    report["acquisition"] = {key: value for key, value in manifest.get("webRun", {}).items() if key in
        ("id", "targetCount", "newlyRequested", "attempted", "notAttempted", "reused", "reusedStatuses",
         "covered", "uncovered", "effectiveStatuses", "requestCoverageComplete", "acquisitionCoverageComplete")}
    report["sourceGaps"] = [{key: value for key, value in row.items() if key in
        ("key", "url", "finalUrl", "status", "httpStatus", "error", "path", "sha256", "webRunID")}
        for row in sorted(manifest["responses"], key=lambda row: row["key"])
        if row["key"].startswith("web:") and row["status"] != "verified"]
    report_bytes = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if check:
        if output.read_bytes() != lua or report_path.read_bytes() != report_bytes:
            raise SourceError("generated artifacts differ from their locked source snapshot")
    else:
        stages = []
        try:
            for path, data in ((output, lua), (report_path, report_bytes)):
                path.parent.mkdir(parents=True, exist_ok=True)
                handle, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".part", dir=path.parent)
                with os.fdopen(handle, "wb") as stream:
                    stream.write(data)
                stages.append((Path(name), path))
            for stage, path in stages:
                os.replace(stage, path)
        finally:
            for stage, _ in stages:
                stage.unlink(missing_ok=True)
    return report["summary"]
