"""Read-only target-225 replay using saved recipe, market price and quantity inputs.

The game installation is only read. Identifiers stay in memory; output contains
aggregate route diagnostics. This is a solver replay, not live game validation.
"""
import argparse
from functools import lru_cache
import hashlib
from importlib.machinery import EXTENSION_SUFFIXES
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
GAME = Path("C:/Program Files (x86)/World of Warcraft/_cn_beta_")
# Match the full test runner: load the current interpreter's Lua extension
# before historical helpers can prepend another interpreter's wheel.
runtime = ROOT / ".pipeline-runtime/lib"
if not any((runtime / "lupa" / ("lua51" + suffix)).is_file() for suffix in EXTENSION_SUFFIXES):
    runtime = Path.home() / "AppData/Local/Temp/df-lua-runtime"
sys.path.insert(0, str(runtime))
from lupa.lua51 import LuaRuntime


@lru_cache(maxsize=2)
def saved_inputs(game):
    """Freeze one read-only observation batch in memory for all replay cases."""
    folder = max((f for f in (game / "WTF/Account").glob("*/SavedVariables")
                  if (f / "DungeonsForever.lua").is_file()),
                 key=lambda f: (f / "DungeonsForever.lua").stat().st_mtime)
    paths = (game / "Interface/AddOns/Auctionator/Libs/LibCBOR/LibCBOR.lua",
             folder / "Auctionator.lua", folder / "DungeonsForever.lua")
    chunks = tuple(path.read_bytes() for path in paths)
    fingerprint = hashlib.sha256(b''.join(hashlib.sha256(chunk).digest() for chunk in chunks)).hexdigest()
    return chunks, fingerprint


def setup(game=GAME, material_supply=None):
    (cbor_source, auction_source, addon_source), _ = saved_inputs(game)
    auction = LuaRuntime(encoding=None, unpack_returned_tuples=True)
    cbor = auction.execute(cbor_source)
    auction.execute(auction_source.removeprefix(b"\xef\xbb\xbf"))
    raw = auction.globals()[b"AUCTIONATOR_PRICE_DATABASE"][b"PvP"]
    prices = cbor[b"Deserialize"](cbor, raw) if isinstance(raw, bytes) else raw
    item_prices = {int(k): v[b"m"] for k, v in prices.items()
                   if isinstance(k, bytes) and k.isdigit() and v[b"m"] is not None}
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(addon_source.decode("utf-8-sig"))
    lua.execute('''
      ns={LoadForeverPages=true,L=setmetatable({}, {__index=function(_,k)return k end})}
      local chosen,best,chosenKey
      for key,state in pairs(DungeonsForeverDB.prof.economy) do
        local n=0;for _,r in pairs(state.recipes or {}) do if r.learned then n=n+1 end end
        if not best or n>best then chosen,best,chosenKey=state,n,key end
      end
      DungeonsForeverDB.prof.economy['Replay-Realm']=chosen
      function UnitName() return 'Replay' end
      function GetRealmName() return 'Realm' end
      function UnitFactionGroup() return 'Alliance' end
      function UnitLevel() return 60 end
      function debugprofilestop() return os.clock()*1000 end
      function time() return 1 end
      ns.DB=function() return DungeonsForeverDB end
      local version,build=chosen.recipeBuild:match('^(.-):(.*)$')
      function GetBuildInfo() return version,build,nil,16001 end
      function IsPlayerSpell() return false end
      function IsSpellKnown() return false end
      Auctionator={Variables={GetConnectedRealmRoot=function() return 'PvP' end}}
      for _,market in pairs(DungeonsForeverDB.auctionSupply.markets) do
        local chosenChar
        for _,c in pairs(market.characters or {}) do
          if not chosenChar or (c.full and (not chosenChar.full or c.full.revision>chosenChar.full.revision)) then chosenChar=c end
        end
        market.characters['Replay-Realm']=chosenChar
      end
    ''')
    load = lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
    for path in ("Core/Data/Data_ProfRecipes.lua", "Core/Data/Data_ProfLeveling.lua",
                 "Core/Data/Data_ProfMining.lua", "Core/Data/Data_ProfItems.lua",
                 "Core/Data/Data_ProfMaterialSupply.lua",
                 "Core/Data/Data_ProfFormulaQuests.lua", "Core/Data/Data_ProfSpecializations.lua",
                 "Core/Data/Data_ProfSpecializationQuests.lua", "Core/ProfEconomy.lua",
                 "Core/ProfItemPrices.lua", "Core/AuctionatorBridge.lua", "Core/ProfRouteSolver.lua"):
        source = material_supply if path == "Core/Data/Data_ProfMaterialSupply.lua" and material_supply else ROOT / path
        load(str(source))
    lua.globals().replayPrices = lua.table_from(item_prices)
    lua.execute('''
      ns.ProfEconomy.Professions=function() return {
        engineering={cur=60,max=75,primary=true},blacksmithing={cur=151,max=225,primary=true}}
      end
      ns.ProfRouteAuto={AHPriceOf=function(id)return replayPrices[id] end}
    ''')
    return lua


def replay(profession, start, choice="none", quantities=True, game=GAME, material_supply=None):
    lua = setup(game, material_supply)
    if not quantities:
        lua.execute("ns.AuctionBridge.GetAuctionSupply=function() return nil end")
    opts = lua.table_from({"start": start, "target": 225, "engineeringSpecialization": choice})
    job = lua.globals().ns.ProfRouteSolver.NewJob(profession, opts)
    run = lua.globals().ns.ProfRouteSolver.Run
    dead = lua.eval("function(j) return coroutine.status(j.co)=='dead' end")
    begin = time.perf_counter()
    first_full = None
    while not job.finished and not dead(job) and time.perf_counter() - begin < 15:
        run(job, 2)
        if job.result and job.result.targetReached and first_full is None:
            first_full = round((time.perf_counter() - begin) * 1000, 2)
    result = job.result
    return {"profession": profession, "start": start, "choice": choice,
            "saved_input_sha256": saved_inputs(game)[1],
            "material_supply_fingerprint": lua.globals().ns.ProfMaterialSupplyMeta.fingerprint,
            "quantities": quantities, "first_full_ms": first_full,
            "wall_ms": round((time.perf_counter() - begin) * 1000, 2),
            "error": str(job.error) if job.error else None, "expanded": job.expanded,
            "status": result.status, "budgetLimited": bool(result.budgetLimited),
            "steps": len(result.steps), "plannedTo": result.plannedTo,
            "rawPrefixTo": job.partial.skill[profession] if job.partial else None,
            "targetReached": bool(result.targetReached),
            "blockers": sorted(set(d.code for _, d in (result.blockingDiagnostics or {}).items())),
            "failures": sorted(set(d.code for _, d in (job.failures or {}).items()))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profession", default="all")
    parser.add_argument("--start", type=int)
    parser.add_argument("--choice", default="none", choices=("none", "goblin", "gnomish"))
    parser.add_argument("--without-quantities", action="store_true")
    parser.add_argument("--game-dir", type=Path, default=GAME,
                        help="read-only game installation containing WTF and Interface/AddOns")
    parser.add_argument("--material-supply", type=Path,
                        help="read-only candidate supply Lua for diagnosing an unpublished batch")
    args = parser.parse_args()
    cases = [("engineering", 60), ("alchemy", 1), ("leatherworking", 1),
             ("tailoring", 1), ("blacksmithing", 151)] if args.profession == "all" else [(args.profession, args.start or 1)]
    for profession, start in cases:
        print(json.dumps(replay(profession, start, args.choice, not args.without_quantities,
                                args.game_dir, args.material_supply), ensure_ascii=True), flush=True)
