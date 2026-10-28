"""Source contracts and parsers. All integer decoding stays exact in Python."""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

PRODUCT = "wowf"
LATEST_URL = "https://wago.tools/api/builds/wowf/latest"
USER_AGENT = "DungeonsForever-profession-data/1.0 (source verification)"
TABLES = ("SkillLine", "SkillLineAbility", "SkillRaceClassInfo", "SpellEffect",
          "SpellLearnSpell", "SpellLevels", "SpellMisc", "SpellName", "ItemSparse",
          "ItemXItemEffect", "ItemEffect", "PlayerCondition", "Faction", "ChrRaces",
          "ChrClasses", "QuestV2", "QuestInfo", "SpellReagents", "Item",
          "SpellEquippedItems", "SpellCategories", "SpellFocusObject")
# Product identities, not recipe catalogues. First aid intentionally excluded.
PROFESSIONS = {171: "alchemy", 164: "blacksmithing", 333: "enchanting", 202: "engineering",
               165: "leatherworking", 197: "tailoring", 186: "mining", 182: "herbalism",
               393: "skinning", 185: "cooking", 356: "fishing", 40: "poisons"}
REQUIRED = {"SkillLine": {"ID"}, "SkillLineAbility": {"ID", "SkillLine", "Spell", "ClassMask"},
            "ItemXItemEffect": {"ID", "ItemID", "ItemEffectID"},
            "ItemEffect": {"ID", "TriggerType", "SpellID", "PlayerConditionID"},
            "ItemSparse": {"ID", "RequiredSkill", "RequiredSkillRank", "RequiredLevel", "AllowableClass"},
            "SpellEffect": {"ID", "SpellID", "Effect", "EffectTriggerSpell"},
            "ChrRaces": {"ID", "PlayableRaceBit"}, "ChrClasses": {"ID"}}


class SourceError(ValueError):
    pass


def integer(value, default=0):
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise SourceError("boolean is not an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer() or abs(value) > 2**53 - 1:
            raise SourceError("inexact numeric field")
        return int(value)
    if not re.fullmatch(r"-?\d+", str(value)):
        raise SourceError("invalid integer field")
    return int(value)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def parse_csv(data: bytes, table: str):
    try:
        text = data.decode("utf-8-sig")
        if text.lstrip().startswith("<"):
            raise SourceError("HTML is not CSV")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        names = reader.fieldnames or []
        if len(names) != len(set(names)) or not REQUIRED.get(table, {"ID"}).issubset(names):
            raise SourceError(f"{table}: missing/duplicate columns")
        rows = list(reader)
        if not rows or any(None in row or any(v is None for v in row.values()) for row in rows):
            raise SourceError(f"{table}: empty or truncated CSV")
        seen = set()
        for row in rows:
            value = integer(row["ID"])
            if value <= 0 or value in seen:
                raise SourceError(f"{table}: duplicate/invalid ID")
            seen.add(value)
        return rows
    except (UnicodeDecodeError, csv.Error, KeyError) as error:
        raise SourceError(f"{table}: {error}") from error


def load_tables(raw: Path, manifest):
    build = manifest.get("build")
    if manifest.get("product") != PRODUCT or not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", str(build)):
        raise SourceError("invalid snapshot build/product")
    result = {}
    for name in TABLES:
        record = next((r for r in manifest["responses"] if r["key"] == "db2:" + name), None)
        if not record or record["status"] != "verified":
            raise SourceError(f"required table unavailable: {name}")
        request = urlsplit(record.get("url", ""))
        if (request.scheme != "https" or request.hostname != "wago.tools" or request.path != f"/db2/{name}/csv"
                or parse_qs(request.query).get("build") != [build]
                or parse_qs(request.query).get("locale") != ["enUS"]):
            raise SourceError(f"{name}: table request identity/build mismatch")
        disposition = record.get("contentDisposition")
        if disposition and f"{name}.{build}.csv" not in disposition:
            raise SourceError(f"{name}: table response identity/build mismatch")
        data = checked_bytes(raw, record)
        result[name] = parse_csv(data, name)
    return result


def checked_bytes(raw: Path, record):
    path = (raw / record["path"]).resolve()
    if not path.is_relative_to(raw.resolve()):
        raise SourceError("snapshot path escapes package")
    data = path.read_bytes()
    if sha256(data) != record["sha256"]:
        raise SourceError("snapshot checksum mismatch: " + record["key"])
    return data


def discover(tables):
    """Discover every member and teaching relation from freshly acquired DB2s."""
    members = {}
    for row in tables["SkillLineAbility"]:
        slug = PROFESSIONS.get(integer(row["SkillLine"]))
        if slug:
            spell = integer(row["Spell"])
            if spell > 0:
                members.setdefault((slug, spell), []).append(row)
    spells = {key[1] for key in members}
    effects = {integer(row["ID"]): row for row in tables["ItemEffect"]}
    learned = {}
    for row in tables["SpellEffect"]:
        if integer(row["Effect"]) == 36 and integer(row["EffectTriggerSpell"]) in spells:
            learned.setdefault(integer(row["SpellID"]), set()).add(integer(row["EffectTriggerSpell"]))
    for row in tables["SpellLearnSpell"]:
        if integer(row["LearnSpellID"]) in spells:
            learned.setdefault(integer(row["SpellID"]), set()).add(integer(row["LearnSpellID"]))
    teaching = {}
    for row in tables["ItemXItemEffect"]:
        effect = effects.get(integer(row["ItemEffectID"]))
        if not effect:
            continue
        sid = integer(effect["SpellID"])
        targets = set(learned.get(sid, ()))
        if integer(effect["TriggerType"]) == 6 and sid in spells:
            targets.add(sid)
        for spell in targets:
            item = integer(row["ItemID"])
            if item > 0:
                teaching.setdefault(spell, {}).setdefault(item, []).append(effect)
    crafting = {integer(row["SpellID"]) for row in tables["SpellEffect"]
                if integer(row["Effect"]) in (24, 53, 157)}
    crafting.update(integer(row["SpellID"]) for row in tables["SpellReagents"]
                    if any(integer(value) > 0 for key, value in row.items()
                           if re.fullmatch(r"Reagent(?:_|\[)\d+\]?", key)))
    # Rank/skill acquisition abilities are not zero-material craft recipes.
    members = {key: rows for key, rows in members.items() if key[1] in crafting
               or key[1] in teaching or any(integer(row.get("TrivialSkillLineRankHigh")) > 0 for row in rows)}
    retained = {spell for _, spell in members}
    teaching = {spell: items for spell, items in teaching.items() if spell in retained}
    return members, teaching


def classify_response(status, data, content_type=""):
    lower = data[:12000].lower()
    if status == 404:
        return "sourceMissing"
    if status in (401, 403, 202, 429) or any(marker in lower for marker in
            (b"window.gokuprops", b"awswaf.com", b"cf-chl-", b"just a moment", b"request blocked")):
        return "sourceBlocked"
    if status != 200:
        return "sourceError"
    return "verified"


def parse_page(data: bytes, kind: str, entity_id: int, final_url: str):
    """Extract literal JSON arrays/strings only; never evaluate downloaded JS."""
    text = data.decode("utf-8-sig")
    expected = re.compile(r"/forever/" + kind + "=" + str(entity_id) + r"(?:/|$)")
    if not expected.search(urlsplit(final_url).path) or "notFound=" in final_url:
        raise SourceError("wrong entity/soft not found")
    if classify_response(200, data) != "verified":
        raise SourceError("challenge is not entity content")
    title = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
    label = "NPC" if kind == "npc" else kind.title()
    if not title or not re.search(r" - " + label + r" - Forever\s*$", html.unescape(title.group(1))):
        raise SourceError("entity title/environment mismatch")
    decoder = json.JSONDecoder()
    listviews, markup = {}, []
    for match in re.finditer(r"new Listview\(\{(.*?)\}\);", text, re.S):
        body = match.group(1)
        identifier = re.search(r"\bid:\s*['\"]([^'\"]+)", body)
        literal = re.search(r"\bdata:\s*(\[|\{)", body)
        if identifier and literal:
            try:
                rows, _ = decoder.raw_decode(body[literal.end()-1:])
                if isinstance(rows, list):
                    listviews[identifier.group(1)] = rows
            except json.JSONDecodeError:
                raise SourceError("malformed listview JSON")
    for match in re.finditer(r"WH\.markup\.printHtml\(\s*", text):
        try:
            value, _ = decoder.raw_decode(text[match.end():])
            if isinstance(value, str):
                markup.append(value)
        except json.JSONDecodeError:
            pass
    if kind == "spell" and not any(integer(r.get("id")) == entity_id
            for r in listviews.get("recipes", ())):
        # Non-crafting member skills remain explicit reference gaps.
        raise SourceError("matching recipe record missing")
    return {"kind": kind, "id": entity_id, "title": html.unescape(title.group(1)),
            "listviews": listviews, "markup": markup}
