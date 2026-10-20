"""Read-only replay of saved client observations and AH quotes, not a live API test.

Never writes SavedVariables. Player/realm identities are replaced in memory and
only aggregate route results are printed. Run from any directory in this addon.
"""
from pathlib import Path
import argparse
import json
import sys
import time

sys.path.insert(0, str(Path.home()/"AppData/Local/Temp/df-lua-runtime"))
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


def replay(profession="engineering", start=60, target=225):
    folders=list((ROOT.parents[2]/"WTF/Account").glob("*/SavedVariables"))
    folder=max((f for f in folders if (f/"DungeonsForever.lua").exists()),
               key=lambda f:(f/"DungeonsForever.lua").stat().st_mtime)
    # Preserve arbitrary CBOR bytes while parsing Auctionator's Lua saved file.
    auction=LuaRuntime(encoding=None, unpack_returned_tuples=True)
    cbor=auction.execute((ROOT.parent/"Auctionator/Libs/LibCBOR/LibCBOR.lua").read_bytes())
    auction.execute((folder/"Auctionator.lua").read_bytes().removeprefix(b"\xef\xbb\xbf"))
    databases=auction.globals()[b"AUCTIONATOR_PRICE_DATABASE"]
    raw=databases[b"PvP"]
    prices=cbor[b"Deserialize"](cbor,raw) if isinstance(raw,bytes) else raw
    item_prices={int(k):v[b"m"] for k,v in prices.items()
                 if isinstance(k,bytes) and k.isdigit() and v[b"m"] is not None}
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute((folder/"DungeonsForever.lua").read_text(encoding="utf-8-sig"))
    lua.execute("""
      ns={LoadForeverPages=true,L=setmetatable({}, {__index=function(_,k)return k end})}
      function UnitName() return 'Replay' end
      function GetRealmName() return 'Realm' end
      function UnitFactionGroup() return 'Alliance' end
      function debugprofilestop() return os.clock()*1000 end
      function time() return 1 end
      ns.DB=function() return DungeonsForeverDB end
      local chosen,best
      for _,state in pairs(DungeonsForeverDB.prof.economy) do
        local n=0;for _,recipe in pairs(state.recipes or {}) do if recipe.learned then n=n+1 end end
        if not best or n>best then chosen,best=state,n end
      end
      DungeonsForeverDB.prof.economy['Replay-Realm']=chosen
      local version,build=chosen.recipeBuild:match('^(.-):(.*)$')
      function GetBuildInfo() return version,build end
    """)
    load=lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
    for path in ("Core/Data/Data_ProfRecipes.lua","Core/Data/Data_ProfLeveling.lua",
                 "Core/Data/Data_ProfMining.lua","Core/Data/Data_ProfItems.lua","Core/Data/Data_ProfFormulaQuests.lua",
                 "Core/ProfEconomy.lua","Core/ProfItemPrices.lua","Core/ProfRouteSolver.lua"):
        load(str(ROOT/path))
    lua.globals().replayPrices=lua.table_from(item_prices)
    lua.execute("""
      ns.ProfEconomy.Professions=function() return {
        engineering={cur=60,max=75,primary=true},blacksmithing={cur=151,max=225,primary=true}}
      end
      ns.ProfRouteAuto={AHPriceOf=function(id)return replayPrices[id] end}
    """)
    job=lua.globals().ns.ProfRouteSolver.NewJob(profession,lua.table_from({"start":start,"target":target}))
    run=lua.globals().ns.ProfRouteSolver.Run
    dead=lua.eval("function(j) return coroutine.status(j.co)=='dead' end")
    begin=time.perf_counter(); first=None; first_full=None; slices=0; peak=0
    while not job.finished and not dead(job) and time.perf_counter()-begin<12:
        before=time.perf_counter();run(job,2);slices+=1;peak=max(peak,(time.perf_counter()-before)*1000)
        if job.result and len(job.result.steps)>0 and first is None:first=round((time.perf_counter()-begin)*1000,2)
        if job.result and job.result.targetReached and first_full is None:first_full=round((time.perf_counter()-begin)*1000,2)
    result=job.result
    return {"profession":profession,"start":start,"target":target,"saved_quotes":len(item_prices),
            "first_steps_ms":first,"first_full_route_ms":first_full,"wall_ms":round((time.perf_counter()-begin)*1000,2),
            "peak_slice_ms":round(peak,2),"slices":slices,"error":str(job.error) if job.error else None,
            "expanded":job.expanded,"status":result.status if result else job.status,
            "rawPrefixTo":job.partial.skill[profession] if job.partial else None,
            "steps":len(result.steps) if result else 0,"plannedTo":result.plannedTo if result else None,
            "targetReached":bool(result.targetReached) if result else False,
            "pricePending":bool(result.pricePending) if result else None,
            "diagnosticCodes":sorted(set(d.code for _,d in (result.diagnostics or {}).items())) if result else [],
            "failureCodes":sorted(set(d.code for _,d in (job.failures or {}).items())),
            "blockerCodes":sorted(set(d.code for _,d in (job.blockers or {}).items()))}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profession",default="engineering")
    parser.add_argument("--start",type=int,default=60)
    parser.add_argument("--target",type=int,default=225)
    args=parser.parse_args()
    print(json.dumps(replay(args.profession,args.start,args.target),ensure_ascii=True))
