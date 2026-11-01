"""Export reference learning conditions for gap review, never addon Data.

Requires Lua 5.1 via ``lupa``. No network access or modular checkout is needed.
Run with --check to verify the committed generated file without writing it.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PINNED_REF = "ec184e0d83f9d027e518b95eb0b2545699c5aeea"
CATALOG = "AddOns/DungeonsForever_RecipeData/Data/Data_ProfCatalog.lua"
OUTPUT = ROOT / "docs" / "profession-learning-condition-gaps.json"


def runtime():
    try:
        from lupa.lua51 import LuaRuntime
    except ImportError:
        # Optional existing local dependency cache; the generator itself has no
        # dependency on private pipeline scripts or generated fixture modules.
        cache = ROOT / ".pipeline-runtime" / "lib"
        if cache.exists():
            sys.path.insert(0, str(cache))
        from lupa.lua51 import LuaRuntime
    return LuaRuntime(unpack_returned_tuples=True)


def git_source(path: str, ref: str = PINNED_REF) -> str:
    return subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=ROOT).decode("utf-8")


def plain(value):
    if not hasattr(value, "items"):
        return value
    items = list(value.items())
    if items and all(isinstance(key, (int, float)) and int(key) == key for key, _ in items):
        if sorted(int(key) for key, _ in items) == list(range(1, len(items) + 1)):
            return [plain(value[index]) for index in range(1, len(items) + 1)]
    return {key: plain(item) for key, item in items}


def trim_conditions(values):
    if not isinstance(values, list):
        return []
    result = []
    for original in values:
        condition = dict(original)
        # Keep text when the exact numeric value could not be represented, and
        # for race-ID lists whose fallback parser consumes the source spelling.
        if condition.get("value") is not None and condition.get("kind") != "raceIDs":
            condition.pop("text", None)
        result.append(condition)
    return result


def render_report(ref: str = PINNED_REF) -> str:
    upstream = runtime()
    upstream.execute("ns={}")
    for path in ("AddOns/DungeonsForever/Framework/CatalogCodec.lua", CATALOG,
                 "AddOns/DungeonsForever_RecipeData/Domain/ProfCatalog.lua"):
        upstream.execute("assert(loadstring(...))('DungeonsForever',ns)", git_source(path, ref))
    dev = runtime()
    dev.execute("ns={LoadForeverPages=true};function GetLocale()return 'zhCN'end")
    for name in ("Data_Professions", "Data_ProfRecipes", "Data_ProfLeveling", "Data_ProfMining"):
        dev.execute("assert(loadstring(...))('DungeonsForever',ns)",
                    (ROOT / "Core" / "Data" / (name + ".lua")).read_text(encoding="utf-8-sig"))
    identities = plain(dev.execute("""
      local ids={}
      for _,profession in ipairs(ns.ProfData.order)do
        local group=ns.ProfRecipes[profession]
        for _,kind in ipairs({'rows','crafted','enchants'})do
          for _,row in ipairs(group and group[kind] or {})do
            local spell=kind=='enchants' and row[14] or row[1]
            if type(spell)=='number'and spell>0 then ids[spell]=true end
          end
        end
        for spell in pairs(ns.ProfLeveling[profession] and ns.ProfLeveling[profession].rinfo or {})do ids[spell]=true end
      end
      return ids
    """))
    logical_fields = {"kind", "status", "conditionsKnown", "conditions", "verified", "teachingItemID", "itemID",
                      "teacherSpellID", "trainerTaught", "trainerObserved", "teachingValidated", "unconditional",
                      "source", "sources", "url", "evidence", "coverage"}
    required_fields = {"kind", "status", "conditionsKnown", "conditions", "verified", "teachingItemID",
                       "trainerTaught", "trainerObserved"}
    records = {}
    for spell in sorted(identities):
        routes = plain(upstream.execute("return ns.ProfCatalog.GetLearningRoutes(...)", spell))
        requirement = plain(upstream.execute("return ns.ProfCatalog.GetExtension('recipe_requirements',...)", spell))
        logical = {}
        for route in routes if isinstance(routes, list) else []:
            record = {key: value for key, value in route.items() if key in logical_fields}
            token = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            logical.setdefault(token, record)
        projected = []
        for route in logical.values():
            conditions = trim_conditions(route.get("conditions"))
            if not conditions and route.get("status") == "confirmed":
                continue
            row = {key: value for key, value in route.items() if key in required_fields}
            row["conditions"] = conditions
            if not row.get("teachingItemID") and route.get("itemID"):
                row["teachingItemID"] = route["itemID"]
            projected.append(row)
        record = {}
        if projected:
            record["routes"] = projected
        if requirement:
            conditions = trim_conditions(requirement.get("conditions"))
            if conditions:
                record["requirements"] = {"conditions": conditions}
        if record:
            records[int(spell)] = record
    original_meta = plain(upstream.execute("return ns.ProfCatalog.GetMetadata()"))
    meta = {"schemaVersion": 1, "sourceCommit": ref, "sourceBuild": original_meta.get("build"),
            "learningFingerprint": original_meta.get("learningFingerprint"), "sourcePath": CATALOG,
            "sourceSHA256": hashlib.sha256(git_source(CATALOG, ref).encode("utf-8")).hexdigest(),
            "selection": "existing dev recipe spell IDs; nonempty qualification conditions or nonconfirmed routes only; ordinary unrestricted trainer routes use dev policy"}
    meta['appliedToRuntime']=False
    meta['policy']='documentation only; dev Data and runtime recipe tables remain unchanged; existing dev specialization gates may overlap individual reference conditions'
    report={'metadata':meta,'referenceConditionsForExistingDevRecipes':[
        dict(spell=spell,**record)for spell,record in sorted(records.items())]}
    return json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare only; do not change the output")
    parser.add_argument("--ref", default=PINNED_REF, help="explicit source Git revision (default: pinned modularization commit)")
    args = parser.parse_args()
    rendered = render_report(args.ref)
    if OUTPUT.resolve().parent!=(ROOT/'docs').resolve():
        raise ValueError('Reference report output must remain in docs/')
    if args.check:
        if OUTPUT.read_text(encoding="utf-8") != rendered:
            print(f"Reference report differs from {args.ref}: {OUTPUT}", file=sys.stderr)
            raise SystemExit(1)
        print(f"Learning gap report reproduces exactly from {args.ref} ({len(rendered.encode('utf-8'))} bytes).")
    else:
        OUTPUT.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"Wrote {OUTPUT} from {args.ref}.")


if __name__ == "__main__":
    main()
