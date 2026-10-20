#!/usr/bin/env python3
"""Audit unresolved recipe-item teaching links using verified local DB2 snapshots.

This script never requests network data or changes the source CSV files. Names
and Item.SubclassID are descriptive fields, never evidence of learning behavior.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlsplit

from fc_prof_items import DataError
from fc_prof_specializations import alias, number, publish


HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
PROFESSION_ROOTS = {129, 164, 165, 171, 182, 185, 186, 197, 202, 333, 356, 393}
TABLE_FIELDS = {
    "itemeffect": ("ID", "SpellID", "TriggerType"),
    "itemxitemeffect": ("ID", "ItemID", "ItemEffectID"),
    "spelleffect": ("ID", "SpellID", "Effect", "EffectTriggerSpell", "EffectMiscValue[0]"),
    "spelllearnspell": ("ID", "SpellID", "LearnSpellID"),
    "skilllineability": ("ID", "Spell", "SkillLine"),
    "skillline": ("ID", "ParentSkillLineID"),
    "spellname": ("ID", "Name_lang"),
}
OUTPUT_FIELDS = (
    "ItemID", "SubclassID", "Name", "TaughtSpellIDs", "TaughtSpellNames",
    "classification", "reason", "LearningPath", "Build",
    "CurrentRecipeSpellIDs", "MappingResolved", "TargetClassifications",
)


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def packed(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def read_bytes(path, snapshots):
    content = path.read_bytes()
    digest = sha256(content)
    if path in snapshots and snapshots[path] != digest:
        raise DataError("input changed during audit: %s" % path)
    snapshots[path] = digest
    return content


def csv_rows(content, path, fields):
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""))
    header = reader.fieldnames or []
    if len(header) != len(set(header)) or not set(fields).issubset(header):
        raise DataError("%s: duplicate or missing CSV columns" % path)
    for index, row in enumerate(reader, 2):
        if None in row or any(value is None for value in row.values()):
            raise DataError("%s:%d: malformed CSV row" % (path, index))
        yield {field: row[field] for field in fields}


def validated_tables(directory, snapshots):
    manifest_path = directory / "manifest.json"
    manifest = json.loads(read_bytes(manifest_path, snapshots))
    build = manifest.get("build", "")
    if not isinstance(build, str) or not re.fullmatch(r"1\.60\.\d+\.\d+", build):
        raise DataError("manifest requires a complete Forever build")
    entries = manifest.get("tables")
    if not isinstance(entries, dict) or not set(TABLE_FIELDS).issubset(entries):
        raise DataError("manifest is missing required teaching or classification tables")
    tables = {}
    for name, metadata in sorted(entries.items()):
        if not re.fullmatch(r"[a-z][a-z0-9]*", name) or not isinstance(metadata, dict):
            raise DataError("invalid manifest table entry")
        path = directory / (name + ".csv")
        content = read_bytes(path, snapshots)
        if metadata.get("sha256") != snapshots[path]:
            raise DataError("%s: manifest SHA-256 mismatch" % path)
        declared_build = metadata.get("build", build)
        source_build = parse_qs(urlsplit(metadata.get("url", "")).query).get("build", [])
        if declared_build != build or (source_build and source_build != [build]):
            raise DataError("%s: manifest source build mismatch" % path)
        fields = TABLE_FIELDS.get(name, ("ID",))
        count, records = 0, []
        identifiers = set()
        for row in csv_rows(content, path, fields):
            count += 1
            identifier = number(row["ID"], "%s.ID" % name)
            if identifier in identifiers:
                raise DataError("%s: duplicate ID %d" % (name, identifier))
            identifiers.add(identifier)
            if name in TABLE_FIELDS:
                for key in fields:
                    if key in ("EffectTriggerSpell", "EffectMiscValue[0]"):
                        if not re.fullmatch(r"-?\d+", row[key]):
                            raise DataError("%s.%s must be an integer" % (name, key))
                        row[key] = int(row[key])
                    elif key != "Name_lang":
                        row[key] = number(row[key], "%s.%s" % (name, key), minimum=0)
                records.append(row)
        if type(metadata.get("rows")) is not int or metadata["rows"] != count:
            raise DataError("%s: manifest row count mismatch" % path)
        if name in TABLE_FIELDS:
            tables[name] = records
    return build, tables, manifest


def recipe_snapshot(path, snapshots, expected_build=None):
    content = read_bytes(path, snapshots)
    mappings = defaultdict(set)
    builds = set()
    for row in csv_rows(content, path, ("RecipeItemID", "RecipeSpellID", "Build")):
        if not re.fullmatch(r"1\.60\.\d+\.\d+", row["Build"]):
            raise DataError("%s: invalid recipe CSV build" % path)
        builds.add(row["Build"])
        if expected_build is not None and row["Build"] != expected_build:
            raise DataError("%s: recipe CSV build mismatch" % path)
        item_id = number(row["RecipeItemID"], "RecipeItemID")
        mappings[item_id]
        if row["RecipeSpellID"]:
            mappings[item_id].add(number(row["RecipeSpellID"], "RecipeSpellID"))
    if len(builds) > 1:
        raise DataError("%s: mixed recipe CSV builds" % path)
    return mappings, next(iter(builds), expected_build or "")


def recipe_mapping(path, snapshots, build):
    return recipe_snapshot(path, snapshots, build)[0]


def select_db2_dir(recipe_path, snapshots):
    _, build = recipe_snapshot(recipe_path, snapshots)
    if not build:
        raise DataError("automatic DB2 selection requires one complete recipe CSV Build")
    cache_root = HERE / "_fc/cache/specializations"
    pointer_path = cache_root / "current.json"
    if pointer_path.exists():
        try:
            pointer = json.loads(read_bytes(pointer_path, snapshots))
            recipe_digest = pointer["outputs"]["recipe_items"]["sha256"]
            target_build = pointer["targetBuild"]
            snapshot = pointer["db2Snapshot"]
            directory = snapshot["path"]
            manifest_digest = snapshot["manifestSHA256"]
            if (not isinstance(directory, str) or not directory or
                    not isinstance(manifest_digest, str) or
                    not re.fullmatch(r"[0-9a-f]{64}", manifest_digest)):
                raise ValueError("invalid snapshot metadata")
            if target_build != build or recipe_digest != snapshots[recipe_path]:
                raise ValueError("current recipe CSV hash or target Build does not match current.json")
            directory = Path(directory)
            if not directory.is_absolute():
                directory = pointer_path.parent / directory
            directory = directory.resolve()
            if sha256(read_bytes(directory / "manifest.json", snapshots)) != manifest_digest:
                raise ValueError("current.json manifest SHA-256 mismatch")
            return directory
        except (KeyError, TypeError, ValueError, OSError) as error:
            raise DataError("cannot select current DB2 snapshot (%s); supply --db2-dir explicitly" % error) from error
    return cache_root / "db2" / build


def item_metadata(item_path, price_path, snapshots, build):
    items, names = {}, {}
    for row in csv_rows(read_bytes(item_path, snapshots), item_path, ("ID", "ClassID", "SubclassID")):
        identifier = number(row["ID"], "Item.ID")
        if identifier in items:
            raise DataError("duplicate Item.ID")
        items[identifier] = (
            number(row["ClassID"], "Item.ClassID", minimum=0),
            number(row["SubclassID"], "Item.SubclassID", minimum=0),
        )
    for row in csv_rows(read_bytes(price_path, snapshots), price_path, ("ItemID", "Name_enUS", "Build")):
        identifier = number(row["ItemID"], "prices.ItemID")
        if identifier in names:
            raise DataError("duplicate prices.ItemID")
        if row["Build"] != build:
            raise DataError("%s: price CSV build mismatch" % price_path)
        names[identifier] = row["Name_enUS"]
    return items, names


def indexes(tables):
    profession_skills = set(PROFESSION_ROOTS)
    while True:
        children = {row["ID"] for row in tables["skillline"]
                    if row["ParentSkillLineID"] in profession_skills}
        if children <= profession_skills:
            break
        profession_skills.update(children)
    effects, skills, edges, items = defaultdict(list), defaultdict(set), defaultdict(list), defaultdict(list)
    missing_item_effects = defaultdict(list)
    rank_spells = set()
    for row in tables["spelleffect"]:
        effects[row["SpellID"]].append(row["Effect"])
        if row["Effect"] in (44, 118):
            rank_spells.add(row["SpellID"])
        if row["Effect"] == 36 and row["EffectTriggerSpell"] > 0:
            edges[row["SpellID"]].append((
                row["EffectTriggerSpell"],
                "SpellEffect[%d].Effect=36/EffectTriggerSpell=%d" % (row["ID"], row["EffectTriggerSpell"]),
            ))
    for row in tables["spelllearnspell"]:
        if row["LearnSpellID"]:
            edges[row["SpellID"]].append((
                row["LearnSpellID"], "SpellLearnSpell[%d].LearnSpellID=%d" %
                (row["ID"], row["LearnSpellID"]),
            ))
    for row in tables["skilllineability"]:
        skills[row["Spell"]].add(row["SkillLine"])
    profession_rank_spells = {
        row["SpellID"] for row in tables["spelleffect"]
        if row["Effect"] in (44, 118) and (
            row["EffectMiscValue[0]"] in profession_skills or
            skills.get(row["SpellID"], set()) & profession_skills)
    }
    item_effects = {row["ID"]: row for row in tables["itemeffect"]}
    for row in tables["itemxitemeffect"]:
        effect = item_effects.get(row["ItemEffectID"])
        if effect is None:
            missing_item_effects[row["ItemID"]].append(
                "Item[%d] -> ItemXItemEffect[%d].ItemEffectID=%d -> missing_ItemEffect_record" %
                (row["ItemID"], row["ID"], row["ItemEffectID"]))
            continue
        if effect["SpellID"]:
            path = ("Item[%d] -> ItemXItemEffect[%d].ItemEffectID=%d -> "
                    "ItemEffect[%d].SpellID=%d/TriggerType=%d") % (
                        row["ItemID"], row["ID"], effect["ID"], effect["ID"],
                        effect["SpellID"], effect["TriggerType"])
            items[row["ItemID"]].append((effect["SpellID"], effect["TriggerType"] == 6, path))
    return {
        "profession_skills": profession_skills, "effects": effects, "skills": skills,
        "edges": edges, "rank_spells": rank_spells, "items": items,
        "missing_item_effects": missing_item_effects,
        "profession_rank_spells": profession_rank_spells,
        "names": {row["ID"]: row["Name_lang"] for row in tables["spellname"]},
    }


def catalog_evidence(path, snapshots, tables):
    metadata = json.loads(read_bytes(path.with_name("source.json"), snapshots))
    content = read_bytes(path, snapshots)
    if metadata.get("sha256") != snapshots[path]:
        raise DataError("recipe catalog source SHA-256 mismatch")
    records = json.loads(content)
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise DataError("recipe catalog must be an array of objects")
    triples = {(row["ID"], row["Spell"], row["SkillLine"]) for row in tables["skilllineability"]}
    normalized, fields = [], set()
    for row in records:
        fields.update(row)
        normalized.append(tuple(number(row.get(key), "catalog." + key) for key in ("id", "spell", "skill")))
    teaching_fields = {
        "recipeitemid", "recipe_item_id", "teachingitemid", "teaching_item_id",
        "sourceitemid", "source_item_id", "formula_item_id",
    }
    return {
        "source": metadata,
        "catalogRows": len(records),
        "matchingSlaRows": sum(row in triples for row in normalized),
        "catalogFields": sorted(fields),
        "catalogHasItemTeachingField": bool(teaching_fields & {key.lower() for key in fields}),
        "matchingUnmappedItemCandidates": [],
        "candidateMatches": [],
        "interpretation": "catalog id/spell/skill checked against SkillLineAbility; products are outputs, not teaching items; candidates do not establish item-to-spell mapping",
    }, {row[1] for row in normalized}


def classify_target(spell, rank_nodes, data):
    if rank_nodes:
        if set(rank_nodes) & data["profession_rank_spells"]:
            return "profession_rank", "teaching_chain_rank_has_profession_skill_evidence"
        return "skill_rank", "teaching_chain_contains_effect_44_or_118_without_profession_skill_evidence"
    if spell not in data["names"] and spell not in data["effects"]:
        return "missing_spell_record", "target_absent_from_SpellName_and_SpellEffect"
    skills = data["skills"].get(spell, set())
    if not skills:
        return "missing_skill_line", "target_exists_without_SkillLineAbility"
    if not skills & data["profession_skills"]:
        return "other_skill_line", "SkillLineAbility_outside_profession_roots_and_children"
    return "profession_recipe_candidate", "explicit_learning_target_has_profession_SkillLineAbility"


def audit_item(item_id, data):
    targets, paths, cycles = defaultdict(list), set(data["missing_item_effects"].get(item_id, [])), []
    stack = [(spell, learned, (spell,), (path,), ())
             for spell, learned, path in data["items"].get(item_id, [])]
    visited_count = 0
    while stack:
        spell, learned, ancestors, path, rank_nodes = stack.pop()
        visited_count += 1
        if visited_count > 10000:
            raise DataError("Item %d teaching graph exceeds audit traversal limit" % item_id)
        if spell in data["rank_spells"]:
            rank_nodes = tuple(sorted(set(rank_nodes) | {spell}))
        links = data["edges"].get(spell, [])
        if not links:
            paths.add(" -> ".join(path))
            if learned:
                category, reason = classify_target(spell, rank_nodes, data)
                targets[spell].append({
                    "classification": category, "reason": reason,
                    "rankSpellIDs": list(rank_nodes),
                    "skillLineIDs": sorted(data["skills"].get(spell, set())),
                })
            continue
        for target, link in links:
            extended = path + (link,)
            if target in ancestors:
                cycles.append(target)
                paths.add(" -> ".join(extended + ("teaching_cycle",)))
                continue
            stack.append((target, True, ancestors + (target,), extended, rank_nodes))
    details = {}
    for spell, observations in sorted(targets.items()):
        unique = {packed(row): row for row in observations}
        details[spell] = [unique[key] for key in sorted(unique)]
    categories = {row["classification"] for observations in details.values() for row in observations}
    if cycles:
        categories.add("teaching_cycle")
    if len(categories) > 1:
        category, reason = "mixed_targets", "different_target_or_chain_classifications"
    elif len(details) > 1:
        category, reason = "multiple_targets", "multiple_explicit_targets:" + next(iter(categories))
    elif categories:
        category = next(iter(categories))
        reason = next(iter(details.values()))[0]["reason"] if details else "explicit_teaching_cycle"
    else:
        category, reason = "no_teaching_relation", "no_TriggerType6_or_nonzero_learning_edge"
    if data["missing_item_effects"].get(item_id):
        reason += ";unresolved_ItemXItemEffect_reference"
    return sorted(details), details, sorted(paths), category, reason


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe-items-csv", type=Path,
                        default=REPO / "scripts/export_buyprice/output/recipe-item-specializations.csv")
    parser.add_argument("--item-csv", type=Path, default=REPO / "scripts/export_buyprice/output/item.csv")
    parser.add_argument("--prices-csv", type=Path,
                        default=REPO / "scripts/export_buyprice/output/item-buy-prices.csv")
    parser.add_argument("--db2-dir", type=Path,
                        help="DB2 snapshot directory; default selects the recipe CSV's unique build")
    parser.add_argument("--baseline-csv", type=Path,
                        help="retain the items unresolved in this older mapping snapshot")
    parser.add_argument("--include-current-unmapped", action="store_true",
                        help="with baseline, audit its unresolved items plus currently unresolved items")
    parser.add_argument("--recipe-catalog-json", type=Path,
                        help="optional independent catalog with adjacent source.json; audit only, never supplies teaching links")
    parser.add_argument("--output-csv", type=Path, default=HERE / "_fc/data/recipe-item-link-audit.csv")
    parser.add_argument("--summary-json", type=Path, default=HERE / "_fc/data/recipe-item-link-audit-summary.json")
    parser.add_argument("--dry-run", "--check", action="store_true", dest="dry_run")
    args = parser.parse_args(argv)
    try:
        snapshots = {}
        if args.db2_dir is None:
            args.db2_dir = select_db2_dir(args.recipe_items_csv.resolve(), snapshots)
        build, tables, manifest = validated_tables(args.db2_dir.resolve(), snapshots)
        current = recipe_mapping(args.recipe_items_csv.resolve(), snapshots, build)
        baseline, baseline_build = (recipe_snapshot(args.baseline_csv.resolve(), snapshots)
                                    if args.baseline_csv else (current, ""))
        current_unmapped = {identifier for identifier, spells in current.items() if not spells}
        baseline_unmapped = {identifier for identifier, spells in baseline.items() if not spells}
        selected = sorted(baseline_unmapped | (current_unmapped if args.include_current_unmapped else set()))
        items, names = item_metadata(args.item_csv.resolve(), args.prices_csv.resolve(), snapshots, build)
        catalog, catalog_spells = (catalog_evidence(args.recipe_catalog_json.resolve(), snapshots, tables)
                                  if args.recipe_catalog_json else (None, set()))
        outputs = [args.output_csv.resolve(), args.summary_json.resolve()]
        if alias(*outputs) or any(alias(out, source) for out in outputs for source in snapshots):
            raise DataError("audit outputs must be distinct and must not overwrite inputs")
        if any(out.is_relative_to(args.db2_dir.resolve()) for out in outputs):
            raise DataError("audit outputs must not be placed inside the DB2 snapshot")
        if outputs[0].suffix.lower() != ".csv" or outputs[1].suffix.lower() != ".json":
            raise DataError("audit output extensions must be .csv and .json")
        data, records = indexes(tables), []
        removed = {identifier for identifier in baseline_unmapped
                   if identifier not in items or items[identifier][0] != 9}
        resolved = {identifier for identifier in baseline_unmapped - removed if current.get(identifier)}
        newly_unmapped = current_unmapped - baseline_unmapped if args.baseline_csv else set()
        for item_id in selected:
            if item_id in removed and args.baseline_csv:
                targets, details, paths = [], {}, []
                category = "removed_from_current_snapshot"
                reason = "absent_from_current_Item" if item_id not in items else "current_Item_ClassID_is_not_9"
            else:
                if item_id not in items or items[item_id][0] != 9:
                    raise DataError("current recipe item %d is missing or Item.ClassID is not 9" % item_id)
                if item_id not in current:
                    raise DataError("current ClassID=9 item %d is absent from recipe CSV" % item_id)
                targets, details, paths, category, reason = audit_item(item_id, data)
            if catalog is not None:
                referenced = {int(value) for path in paths for value in
                              re.findall(r"(?:SpellID=|EffectTriggerSpell=|LearnSpellID=)(\d+)", path)}
                matching = sorted(referenced & catalog_spells)
                if matching:
                    catalog["matchingUnmappedItemCandidates"].append(item_id)
                    catalog["candidateMatches"].append({"ItemID": item_id, "SpellIDs": matching})
            records.append({
                "ItemID": item_id, "SubclassID": items[item_id][1] if item_id in items else "",
                "Name": names.get(item_id, ""),
                "TaughtSpellIDs": packed(targets),
                "TaughtSpellNames": packed([data["names"].get(spell, "") for spell in targets]),
                "classification": category, "reason": reason, "LearningPath": packed(paths),
                "Build": build, "CurrentRecipeSpellIDs": packed(sorted(current.get(item_id, set()))) if item_id not in removed else "[]",
                "MappingResolved": "true" if current.get(item_id) and item_id not in removed else "false",
                "TargetClassifications": packed(details),
            })
        summary = {
            "schemaVersion": 2, "build": build, "targetBuild": build, "baselineBuild": baseline_build,
            "comparisonAvailable": bool(args.baseline_csv),
            "scope": ("baseline_and_current_unmapped" if args.include_current_unmapped else "unmapped_items_in_baseline") if args.baseline_csv
            else "currently_unmapped_items", "items": len(records),
            "newlyUnmapped": len(newly_unmapped), "resolved": len(resolved) if args.baseline_csv else 0,
            "removed": len(removed) if args.baseline_csv else 0,
            "comparisonItemIDs": {
                "newlyUnmapped": sorted(newly_unmapped),
                "resolved": sorted(resolved) if args.baseline_csv else [],
                "removed": sorted(removed) if args.baseline_csv else [],
            },
            "comparisonMeaning": {
                "newlyUnmapped": "current unmapped IDs not in baseline unmapped set; includes newly added and previously mapped items",
                "resolved": "baseline unmapped IDs present as current ClassID=9 items with current recipe mappings",
                "removed": "baseline unmapped IDs absent from current Item or no longer ClassID=9; never counted as resolved",
                "noBaseline": "comparison counts are zero when comparisonAvailable is false",
            },
            "mappingResolved": sum(row["MappingResolved"] == "true" for row in records),
            "stillUnmapped": sum(row["MappingResolved"] == "false" and
                                 row["classification"] != "removed_from_current_snapshot" for row in records),
            "classifications": dict(sorted(Counter(row["classification"] for row in records).items())),
            "stillUnmappedClassifications": dict(sorted(Counter(
                row["classification"] for row in records if row["MappingResolved"] == "false" and
                row["classification"] != "removed_from_current_snapshot").items())),
            "subclasses": dict(sorted(Counter(str(row["SubclassID"]) for row in records).items())),
            "professionSkillLineIDs": sorted(data["profession_skills"]),
            "sources": [{"path": str(path), "sha256": value} for path, value in sorted(snapshots.items())],
            "db2Manifest": manifest,
            "interpretation": {
                "namesAndSubclass": "descriptive_only; SubclassID=0 is Book",
                "missingSkillLine": "not evidence of class-only, deprecated, or unrestricted status",
                "professionRecipeCandidate": "explicit profession link; recipe semantics still require review",
            },
        }
        if catalog is not None:
            summary["recipeCatalogAudit"] = catalog
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
        for path, expected in snapshots.items():
            if sha256(path.read_bytes()) != expected:
                raise DataError("input changed during audit: %s" % path)
        if not args.dry_run:
            publish({
                outputs[0]: stream.getvalue().encode("utf-8-sig"),
                outputs[1]: (json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            })
        print("[%s] %s" % ("CHECK" if args.dry_run else "OK", packed({
            key: summary[key] for key in ("build", "items", "mappingResolved", "stillUnmapped", "classifications")
        })))
        return 0
    except (OSError, ValueError, csv.Error) as error:
        print("fc_recipe_item_audit: %s" % error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
