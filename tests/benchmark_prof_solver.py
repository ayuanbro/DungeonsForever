"""Cooperative first-result benchmark with synthetic client data, not game timing."""
from pathlib import Path
import json
import sys
import time

sys.path.insert(0,str(Path.home()/"AppData/Local/Temp/df-lua-runtime"))
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]

def measure(profession,target,secondary=None):
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute("ns={LoadForeverPages=true,L=setmetatable({}, {__index=function(_,k)return k end})}; debugprofilestop=function() return os.clock()*1000 end")
    load=lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
    for file in ["Core/Data/Data_ProfRecipes.lua","Core/Data/Data_ProfLeveling.lua","Core/Data/Data_ProfMining.lua","Core/ProfEconomy.lua","Core/ProfRouteSolver.lua"]:
        load(str(ROOT/file))
    setup=lua.eval('''function(main,target,other)
      local keys={main}; if other then keys[#keys+1]=other end
      local all=ns.EnsureProfRecipes(keys)
      local s={recipes={},prices={},inventory={},professions={},known={}}
      for _,p in ipairs(keys) do
        s.professions[p]={cur=p==main and 1 or 300,max=300}
        for _,r in ipairs(all[p].rows) do
          if r[7] and r[10] and r[12] then
            local n={profession=p,spell=r[1],item=r[2],count=r[3],learn=r[7],yellow=r[8],green=r[9],grey=r[10],mats=r[12],cooldown=r[4]=='Transmutes'}
            s.recipes[#s.recipes+1]=n; s.known[p..':'..r[1]]=true
            for _,m in ipairs(r[12]) do s.prices[m[1]]=1 end
          end
        end
      end
      job=ns.ProfRouteSolver.NewJob(main,{snapshot=s,start=1,target=target})
    end''')
    setup(profession,target,secondary)
    run=lua.eval("function() return ns.ProfRouteSolver.Run(job,2) end")
    status=lua.eval("function() return job.status,job.result and job.result.feasible,job.expanded,job.error end")
    start=time.perf_counter(); calls=0; peak=0
    while time.perf_counter()-start<8:
        t=time.perf_counter(); done=run(); peak=max(peak,(time.perf_counter()-t)*1000); calls+=1
        state,feasible,nodes,error=status()
        if feasible or done: break
    return dict(fixture=f"{profession}+{secondary or 'none'}",target=target,
        first_feasible=bool(feasible),status=state,slices=calls,
        wall_ms=round((time.perf_counter()-start)*1000,2),largest_slice_ms=round(peak,2),expanded=nodes,error=error)

if __name__=="__main__":
    for args in [("alchemy",75),("blacksmithing",300,"mining")]:
        print(json.dumps(measure(*args),ensure_ascii=False))
