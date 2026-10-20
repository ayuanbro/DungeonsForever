#!/usr/bin/env python3
"""Replay verified Wowhead caches against current unresolved recipe-item links.

No network calls or mapping updates occur. Missing pages or Listviews remain
unknown; names, descriptions and product IDs never establish teaching links.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

from fc_prof_items import DataError
from fc_prof_specializations import alias, number, publish
from fc_recipe_item_audit import (
    HERE, REPO, audit_item, indexes, read_bytes, recipe_mapping,
    select_db2_dir, sha256, validated_tables,
)
from fc_specialization_fetch import (
    CACHE_VERSION, FetchError, _Scripts, _listview_data, _validate_url, parse_page,
)


def timestamp(value, label):
    if not isinstance(value, str):
        raise DataError("%s must be a timezone-aware timestamp" % label)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise DataError("%s must be a timezone-aware timestamp" % label)
    return value


def cached_pages(cache_dir, snapshots):
    """Validate cache bytes and page identity directly; never instantiate a fetcher."""
    if cache_dir.exists() and not cache_dir.is_dir():
        raise DataError("Wowhead cache path is not a directory")
    pages = []
    for path in sorted(cache_dir.glob("*.json")):
        if not re.fullmatch(r"[0-9a-f]{64}\.json", path.name):
            continue
        cached = json.loads(read_bytes(path, snapshots))
        if (not isinstance(cached, dict) or type(cached.get("version")) is not int or
                cached["version"] != CACHE_VERSION):
            raise DataError("%s: wrong cache version" % path)
        url = cached.get("url")
        if not isinstance(url, str):
            raise DataError("%s: missing cache URL" % path)
        _validate_url(url)
        if path.stem != sha256(url.encode("utf-8")):
            raise DataError("%s: cache filename does not match URL" % path)
        match = re.match(r"/forever/(skill|spell|item)=(\d+)(?:/|$)", unquote(urlsplit(url).path))
        if not match:
            raise DataError("%s: unsupported cache page identity" % path)
        kind, entity_id = match.group(1), number(match.group(2), "cached page ID")
        html = cached.get("html")
        if not isinstance(html, str) or sha256(html.encode("utf-8")) != cached.get("sha256"):
            raise DataError("%s: cache HTML SHA-256 mismatch" % path)
        parsed = parse_page(html, kind, entity_id)
        source = {
            "CacheFile": str(path), "CacheFileSHA256": snapshots[path],
            "Kind": kind, "EntityID": entity_id, "SourceURL": url,
            "SourceSHA256": cached["sha256"], "SourcePatch": parsed["patch"],
            "SourceBuild": parsed["build"], "SourceBuildStatus": "unknown" if not parsed["build"] else "explicit",
            "SourceFetchedAt": timestamp(cached.get("fetched_at"), "fetched_at"),
            "SourceCheckedAt": timestamp(cached.get("checked_at"), "checked_at"),
            "Validation": "sha256_and_forever_page_identity_passed",
        }
        scripts = _Scripts()
        scripts.feed(html)
        item_rows = _listview_data(scripts.scripts, "recipe-items", "item") if kind == "skill" else None
        taught_rows = _listview_data(scripts.scripts, "taught-by-item", "item") if kind == "spell" else None
        for rows in (item_rows, taught_rows):
            for row in rows or []:
                if type(row.get("id")) is not int:
                    raise DataError("%s: Listview item ID must be numeric" % path)
                number(row.get("id"), "Listview item ID")
        pages.append((parsed, source, item_rows, taught_rows))
    return pages


def audit(recipe_items_csv, db2_dir=None, cache_dir=None):
    """Return a reproducible report for the current CSV's unmapped item set."""
    recipe_path = Path(recipe_items_csv).resolve()
    cache_dir = Path(cache_dir or HERE / "_fc/cache/specializations/wowhead-forever").resolve()
    snapshots = {}
    db2_dir = Path(db2_dir).resolve() if db2_dir else select_db2_dir(recipe_path, snapshots)
    build, tables, manifest = validated_tables(db2_dir, snapshots)
    mappings = recipe_mapping(recipe_path, snapshots, build)
    unresolved = {item_id for item_id, spells in mappings.items() if not spells}
    local = indexes(tables)
    pages = cached_pages(cache_dir, snapshots)
    recipe_sources, item_list_sources, explicit_sources = defaultdict(list), defaultdict(list), defaultdict(list)
    existing = []
    for parsed, source, recipe_items, taught_items in pages:
        if source["Kind"] == "skill":
            for row in parsed["recipes"]:
                recipe_sources[row["id"]].append(source)
            for row in recipe_items or []:
                if row["id"] in unresolved:
                    item_list_sources[row["id"]].append(source)
        relationships = []
        if source["Kind"] == "spell":
            relationships = [(row["id"], source["EntityID"], "taught-by-item") for row in taught_items or []]
        elif source["Kind"] == "item":
            relationships = [(source["EntityID"], spell, "teaches") for spell in parsed["taught_spell_ids"]]
        for item_id, spell, relation in relationships:
            evidence = {
                "RecipeItemID": item_id, "RecipeSpellID": spell,
                "Evidence": "Wowhead.Listview." + relation,
                "Source": source,
            }
            if item_id in unresolved:
                explicit_sources[item_id].append(evidence)
            elif item_id in mappings:
                existing.append(dict(evidence, AlreadyMapped=spell in mappings[item_id]))
    records, checked_spells, identity_matches = [], set(), []
    for item_id in sorted(unresolved):
        targets, details, paths, classification, reason = audit_item(item_id, local)
        checked_spells.update(targets)
        matches = []
        for spell in targets:
            for source in recipe_sources.get(spell, []):
                evidence = {
                    "RecipeItemID": item_id, "RecipeSpellID": spell,
                    "Evidence": "explicit_DB2_teaching_chain_and_Wowhead_skill_recipe_identity",
                    "Source": source,
                    "VersionStatus": "patch_matches_exact_build_unknown"
                    if source["SourcePatch"] == build.rsplit(".", 1)[0] else "source_patch_mismatch",
                }
                matches.append(evidence)
                identity_matches.append(evidence)
        explicit = []
        for evidence in explicit_sources.get(item_id, []):
            value = dict(evidence)
            value["LocalTeachingAgreement"] = (
                "matches" if evidence["RecipeSpellID"] in targets else
                "different_explicit_target" if targets else "local_teaching_relation_missing")
            value["VersionStatus"] = (
                "patch_matches_exact_build_unknown"
                if evidence["Source"]["SourcePatch"] == build.rsplit(".", 1)[0] else "source_patch_mismatch")
            explicit.append(value)
        matching_version_evidence = any(
            evidence["VersionStatus"] != "source_patch_mismatch" for evidence in matches + explicit)
        records.append({
            "RecipeItemID": item_id, "LocalTaughtSpellIDs": targets,
            "LocalClassification": classification, "LocalReason": reason,
            "LearningPath": paths, "TargetClassifications": details,
            "Status": "observed_web_evidence" if matching_version_evidence else "pending",
            "RecipeItemsListSources": item_list_sources.get(item_id, []),
            "SkillRecipeIdentityMatches": matches, "ExplicitWebTeachingEvidence": explicit,
            "ItemPages": [source for _, source, _, _ in pages
                          if source["Kind"] == "item" and source["EntityID"] == item_id],
        })
    for path, expected in snapshots.items():
        if sha256(path.read_bytes()) != expected:
            raise DataError("input changed during web audit: %s" % path)
    return {
        "SchemaVersion": 2, "TargetBuild": build,
        "CurrentCSV": {"Path": str(recipe_path), "SHA256": snapshots[recipe_path],
                       "RecipeItemCount": len(mappings), "UnmappedRecipeItemCount": len(unresolved)},
        "DB2Manifest": manifest, "DB2SnapshotDirectory": str(db2_dir),
        "InputSources": [{"Path": str(path), "SHA256": digest} for path, digest in sorted(snapshots.items())],
        "CacheSources": [source for _, source, _, _ in pages],
        "CheckedPageCounts": dict(sorted(Counter(source["Kind"] for _, source, _, _ in pages).items())),
        "Findings": {
            "CandidateSpellIDsChecked": sorted(checked_spells),
            "CandidateSpellIDsAbsentFromCachedSkillRecipeLists": sorted(checked_spells - set(recipe_sources)),
            "ExplicitTeachingAndCachedRecipeIdentityMatches": identity_matches,
            "ExistingTaughtByItemMappings": existing,
            "RecipeItemsListHitIDs": sorted(item_list_sources),
            "ExplicitWebTeachingItemIDs": sorted(explicit_sources),
            "NewMappingsAdded": 0,
        },
        "Coverage": {
            "Complete": False, "Scope": "current_unmapped_items_and_available_validated_caches",
            "ItemsWithObservedWebEvidence": sum(row["Status"] == "observed_web_evidence" for row in records),
            "PendingItems": sum(row["Status"] == "pending" for row in records),
        },
        "Items": records,
        "Boundaries": [
            "No network requests, mapping changes, name matching, or subclass exclusions.",
            "Only explicit teaches/taught-by-item Listviews or DB2 teaching chains establish item-to-spell evidence.",
            "A recipe-items list hit does not establish which spell the item teaches.",
            "Missing cache entries or lists never prove unrestricted, unavailable, or non-recipe status.",
            "A source patch does not establish an exact matching client build.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe-items-csv", type=Path,
                        default=REPO / "scripts/export_buyprice/output/recipe-item-specializations.csv")
    parser.add_argument("--db2-dir", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=HERE / "_fc/cache/specializations/wowhead-forever")
    parser.add_argument("--output-json", type=Path, help="optional report destination; default prints JSON")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = audit(args.recipe_items_csv, args.db2_dir, args.cache_dir)
        content = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.output_json:
            output = args.output_json.resolve()
            sources = [Path(source["Path"]) for source in report["InputSources"]]
            if (any(alias(output, path) for path in sources) or
                    output.is_relative_to(args.cache_dir.resolve()) or
                    output.is_relative_to(Path(report["DB2SnapshotDirectory"]))):
                raise DataError("web audit output must not overwrite inputs or enter cache snapshots")
            if output.suffix.lower() != ".json":
                raise DataError("web audit output must have a .json extension")
            if not args.dry_run:
                publish({output: content.encode("utf-8")})
            print("[%s] %s" % ("CHECK" if args.dry_run else "OK",
                              json.dumps(report["Coverage"], sort_keys=True)))
        else:
            print(content, end="")
        return 0
    except (OSError, ValueError, FetchError) as error:
        print("fc_recipe_item_web_audit: %s" % error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
