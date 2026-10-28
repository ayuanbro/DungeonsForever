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
    for record in responses.values():
        if "path" in record:
            checked_bytes(raw, record)
    sparse = {integer(row["ID"]): row for row in tables["ItemSparse"]}
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
        trainer_ids = sorted({integer(row.get("id")) for row in (web or {}).get("listviews", {}).get("taught-by-npc", ())
                              if integer(row.get("id")) > 0})
        if trainer_ids:
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
                cost = vendor.get("cost")
                if (isinstance(cost, list) and len(cost) == 1 and isinstance(cost[0], list)
                        and len(cost[0]) == 1 and isinstance(cost[0][0], int) and cost[0][0] >= 0):
                    quantity = integer((row or {}).get("VendorStackCount"))
                    if quantity <= 0:
                        continue
                    quote = {"id": integer(vendor["id"]), "npcID": integer(vendor["id"]), "price": cost[0][0],
                             "quantity": quantity, "status": "unknown", "conditionsKnown": False}
                    if isinstance(vendor.get("stock"), int):
                        quote.update(stock=vendor["stock"], unlimited=vendor["stock"] < 0)
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
                    acquisition["nonAuctionable"] = bonding in (1, 4, 5)
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


def emit_lua(facts, meta):
    strings, string_ids = [], {}
    pools = {name: [] for name in ("conditions", "acquisition", "sets", "gaps")}
    pool_ids = {name: {} for name in pools}

    def intern(name, value):
        key = canonical(value)
        if key not in pool_ids[name]:
            pool_ids[name][key] = len(pools[name]) + 1
            pools[name].append(value)
        return pool_ids[name][key]

    def pack(value):
        if value is None:
            return "_"
        if value is True:
            return "t"
        if value is False:
            return "f"
        if isinstance(value, int):
            if abs(value) > 2**53 - 1:
                raise SourceError("inexact integer cannot enter Lua runtime")
            return "z" if value == 0 else "n" + base36(value) + ";"
        if isinstance(value, str):
            if value not in string_ids:
                string_ids[value] = len(strings) + 1
                strings.append(value)
            return "s" + base36(string_ids[value]) + ";"
        if isinstance(value, list):
            return "[" + "".join(pack(item) for item in value) + "]"
        if isinstance(value, dict):
            return "{" + "".join(pack(key) + pack(value[key]) for key in sorted(value)) + "}"
        raise SourceError("unsupported runtime value")

    profiles = {}
    kind_ids = {"trainer": 1, "item": 2, "quest": 3}
    status_ids = {"unknown": 0, "confirmed": 1, "conflict": 2}
    coverage_ids = {"none": 0, "partial": 1, "complete": 2}
    for slug, records in sorted(facts.items()):
        lines = []
        for spell, record in sorted(records.items()):
            routes = []
            for route in record["routes"]:
                routes.append([kind_ids[route["kind"]], route.get("teachingItemID", 0), status_ids[route["status"]],
                    int(route["conditionsKnown"]), intern("conditions", route["conditions"]), route.get("trainingCost", -1),
                    intern("sets", route.get("trainerIDs", [])), intern("sets", route.get("questIDs", [])),
                    intern("acquisition", route.get("acquisition", {}))])
            lines.append(str(spell) + ":" + pack([coverage_ids[record["coverage"]], intern("gaps", record["missingReasons"]), routes]))
        profiles[slug] = "\n".join(lines)
    encoded_pools = {name: [pack(value) for value in values] for name, values in pools.items()}
    # String interning completes before serializing STR.
    lines = ["-- Generated by data_pipeline.professions; edit sources/rules, never this file.",
             "local _,ns=...", "if not ns.IsForever then return end",
             "local STR={" + ",".join(lua_quote(value) for value in strings) + "}", "local RAW={}"]
    for slug, value in profiles.items():
        lines.append("RAW[" + lua_quote(slug) + "]=" + lua_quote(value))
    for name, values in encoded_pools.items():
        lines.append("local " + name.upper() + "={" + ",".join(lua_quote(value) for value in values) + "}")
    lines.append("local meta={schema=1,rules=" + str(RULES_VERSION) + ",product=" + lua_quote(PRODUCT) + ",build=" + lua_quote(meta["build"]) + ",fingerprint=" + lua_quote(meta["fingerprint"]) + "}")
    lines.append(r'''
local function unpackValue(text)
 local p=1
 local function take()
  local c=text:sub(p,p);p=p+1
  if c=="z"then return 0 elseif c=="t"then return true elseif c=="f"then return false elseif c=="_"then return nil end
  if c=="n"or c=="s"then
   local e=assert(text:find(";",p,true));local first,sign=p,1
   if text:sub(first,first)=="-"then first=first+1;sign=-1 end
   local n=0;for i=first,e-1 do local b=text:byte(i);n=n*36+(b<=57 and b-48 or b-87)end
   n=n*sign;p=e+1
   if c=="s"then return assert(STR[n])end;return n
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
local decoded={conditions=weakValues(),acquisition=weakValues(),sets=weakValues(),gaps=weakValues()}
local function pooled(name,id,raw)
 local values=decoded[name];if not values[id]then values[id]=unpackValue(raw[id])end;return values[id]
end
local indexes,caches,views={},{},{}
local kinds={[1]="trainer",[2]="item",[3]="quest"}
local statuses={[0]="unknown",[1]="confirmed",[2]="conflict"}
local coverages={[0]="none",[1]="partial",[2]="complete"}
local function index(slug)
 if not indexes[slug]then
  local values={};indexes[slug]=values;caches[slug]=weakValues()
  local text=RAW[slug]or "";local start=1
  while start<=#text do
   local colon=text:find(":",start,true);local finish=text:find("\n",colon,true)or #text+1
   local spell=tonumber(text:sub(start,colon-1));local length=finish-colon-1
   assert(length<65536);values[spell]=(colon+1)*65536+length;start=finish+1
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
 if cache[spell]then return cache[spell]end
 if not values[spell]then return nil end
 local offset=values[spell];local start=floor(offset/65536);local length=offset-start*65536
 local value=unpackValue(RAW[slug]:sub(start,start+length-1));local routes={}
 for _,row in ipairs(value[3])do
  local flags=row[1]+row[3]*4+row[4]*16
  local route={spell,flags,row[1]==3 and row[8]or row[2],row[5],row[9]}
  if row[1]==1 then route[6]=row[6];route[7]=row[7]end
  routes[#routes+1]=setmetatable(route,routeMT)
 end
 local mt=recordMTs[slug]
 if not mt then mt={profession=slug,__index=recordIndex,__newindex=readOnly,__profLearningMaterialize=recordProjection};recordMTs[slug]=mt end
 local record=setmetatable({spell,value[1],value[2],routes},mt)
 cache[spell]=record
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
ns.ProfLearningSources={meta=meta,Get=Get,ForProfession=ForProfession,Each=Each,Materialize=Materialize}
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
    semantic = {"schema": SCHEMA_VERSION, "rules": RULES_VERSION, "product": PRODUCT,
                "build": manifest["build"], "professions": facts}
    fingerprint = sha256(canonical(semantic).encode("utf-8"))
    lua = emit_lua(facts, {"build": manifest["build"], "fingerprint": fingerprint})
    report = {"schema": SCHEMA_VERSION, "rules": RULES_VERSION, "product": PRODUCT,
              "build": manifest["build"], "fingerprint": fingerprint, "generationInput": False,
              "summary": {"recipes": sum(len(records) for records in facts.values()), "recipesWithGaps": len(gaps),
                          "confirmedPaths": sum(route["status"] == "confirmed" for rows in facts.values() for row in rows.values() for route in row["routes"]),
                          "luaBytes": len(lua)}, "gaps": gaps,
              "evidence": [{key: value for key, value in record.items() if key in
                  ("key", "url", "finalUrl", "status", "httpStatus", "path", "sha256", "fetchedAt", "error")}
                  for record in sorted(manifest["responses"], key=lambda record: record["key"])],
              "facts": facts}
    report["professions"] = {slug: {"recipes": len(rows),
        "confirmedPaths": sum(route["status"] == "confirmed" for row in rows.values() for route in row["routes"]),
        "unknownPaths": sum(route["status"] != "confirmed" for row in rows.values() for route in row["routes"]),
        "missingReasons": dict(sorted(Counter(reason for row in rows.values() for reason in row["missingReasons"]).items()))}
        for slug, rows in sorted(facts.items())}
    report["sourceStatuses"] = dict(sorted(Counter(row["status"] for row in manifest["responses"]).items()))
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
