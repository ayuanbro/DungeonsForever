"""Native dev route lifecycle integration, running the actual Lua 5.1 sources."""
from pathlib import Path
import unittest
from test_prof_solver_fusion import LuaRuntime, ROOT


MOCKS = r'''
ns={LoadForeverPages=true,L=setmetatable({},{__index=function(_,k)return k end})}
DungeonsForeverDB={prof={}};queue={};callbacks={};timers={};frames={};clock=1000
time=function()return clock end
UnitName=function()return 'Test'end;GetRealmName=function()return 'Realm'end
UnitLevel=function()return 60 end;UnitFactionGroup=function()return 'Alliance'end
function CreateFrame()
 local f={events={}}
 function f:RegisterEvent(event)self.events[event]=true end
 function f:UnregisterEvent(event)self.events[event]=nil end
 function f:SetScript(key,fn)self[key]=fn end
 frames[#frames+1]=f;return f
end
ns.Init=function(fn)callbacks[#callbacks+1]=fn end
ns.IdleJobs={Add=function(fn)queue[#queue+1]=fn end}
C_Timer={After=function(_,fn)timers[#timers+1]=fn end}
bag={};C_Item={GetItemCount=function(id)return bag[id] or 0 end}
skills={alchemy={cur=1,max=300},enchanting={cur=1,max=300}}
-- Existing quantity-ledger fixtures explicitly exercise the enabled policy.
function fixture()
 return {considerAuctionSupply=true,recipes={{profession='alchemy',spell=101,item=10,count=1,mats={{11,1}},learn=1,yellow=100,green=200,grey=300,cooldown=false}},
  professions={alchemy={cur=1,max=300}},known={['alchemy:101']=true},prices={[11]=7},coverageComplete=true}
end
function finish(slug,opts)
 local r=ns.ProfRouteAuto.Get(slug,opts)
 for i=1,1000 do
  ns.ProfRouteAuto.Pump(slug);r=ns.ProfRouteAuto.Get(slug,opts)
  if not ns.ProfRouteAuto.HasWork(slug) then return r end
 end
 error('route did not terminate')
end
'''


class NativeRoutePlansTests(unittest.TestCase):
    def test_real_solver_reports_seed_skill_then_search_phase(self):
        self.lua.execute('''
          local solver=ns.ProfRouteSolver;local runner=ns.ProfSolverRun
          local j=solver.NewJob('alchemy',{snapshot=fixture(),start=1,target=35})
          local seed,search=false,false
          for i=1,20000 do
            solver.Run(j,0.01)
            local phase=runner.Stamp(j)
            if phase=='seed' and (j.seedSkill or 1)>1 then seed=true end
            if phase=='search' then search=true end
            if j.finished then break end
          end
          assert(j.finished and j.cpuLimitMs==8000)
          assert(seed and search,'solver did not report both live phases')
        ''')

    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.load=self.lua.eval("function(source)assert(loadstring(source))('DungeonsForever',ns)end")
        for name in ("ProfPolicies","ProfRouteAuto","ProfEssences","ProfSolverCapture","ProfRecovery","ProfRouteSolver","ProfExecution","ProfSolverRun","ProfRoutePlans"):
            self.load((ROOT/"Core"/(name+".lua")).read_text(encoding="utf-8-sig"))
        self.lua.execute('''
          ns.ProfEconomy.Professions=function()return skills end
          ns.ProfEconomy.RecipeSpecializationAllowed=function()return true end
          for _,fn in ipairs(callbacks)do fn()end;callbacks={}
        ''')

    def test_get_schedules_one_job_and_uses_recursive_solver(self):
        self.lua.execute('''
          opts={snapshot=fixture(),start=1,target=3}
          local r=ns.ProfRouteAuto.Get('alchemy',opts)
          assert(r.status=='searching' and #queue==1)
          assert(ns.ProfRouteAuto.Get('alchemy',opts)==r and #queue==1)
          r=finish('alchemy',opts)
          assert(r.status=='complete' and r.total==14 and r.targetReached)
          assert(r.planVersion==2 and #r.executionSteps>0)
        ''')

    def test_invalidating_market_marks_stale_without_restarting_search(self):
        self.lua.execute('''
          local ra=ns.ProfRouteAuto
          opts={snapshot=fixture(),start=1,target=3}
          local r=finish('alchemy',opts);local queued=#queue
          ra.Invalidate('prices')
          assert(ra.Get('alchemy',opts)==r and r.stale and #queue==queued)
          local pending=ra.Recalculate('alchemy',opts)
          assert(pending.status=='searching' and pending~=r)
          assert(finish('alchemy',opts).total==14)
        ''')

    def test_cancel_resume_cannot_run_obsolete_scheduler_callback(self):
        self.lua.execute('''
          local ra=ns.ProfRouteAuto;opts={snapshot=fixture(),start=1,target=3}
          ra.Get('alchemy',opts);local old=queue[1]
          assert(ra.Cancel('alchemy') and ra.Get('alchemy',opts).status=='stopped')
          ra.Continue('alchemy');assert(old()==true,'cancelled callback was revived')
          assert(finish('alchemy',opts).total==14)
          ra.Cancel('alchemy');ra.Continue('alchemy')
          assert(ra.Get('alchemy',opts).status=='complete')
        ''')

    def test_old_generation_cannot_publish_after_recalculate(self):
        self.lua.execute('''
          local ra=ns.ProfRouteAuto;opts={snapshot=fixture(),start=1,target=3}
          ra.Get('alchemy',opts);local old=queue[1]
          local pending=ra.Recalculate('alchemy',opts)
          assert(old()==true and ra.Get('alchemy',opts)==pending)
          assert(finish('alchemy',opts).total==14)
        ''')

    def test_skeleton_reprices_saved_steps_after_reload_without_route_search(self):
        self.lua.execute('''
          captures=0;price=7
          ns.ProfEconomy.Capture=function()
            captures=captures+1;local s=fixture();s.prices[11]=price
            return ns.ProfEconomy.Index(s)
          end
          original=finish('alchemy',{start=1,target=3});assert(original.total==14 and captures==1)
          price=99;skills.alchemy.cur=2
        ''')
        self.load((ROOT/"Core"/"ProfRoutePlans.lua").read_text(encoding="utf-8-sig"))
        self.lua.execute('''
          local r=finish('alchemy',{start=2,target=3})
          assert(r.cached and r.fromSkeleton and r.total==198 and r.start==1 and captures==2)
          assert(r.expanded==0 and not r.optimal and r.searchTermination=='skeleton_rebuilt')
          ns.ProfRouteAuto.Recalculate('alchemy',{start=2,target=3})
          r=finish('alchemy',{start=2,target=3})
          assert(r.total==99 and captures==3 and r.planID~=original.planID)
        ''')

    def test_execution_plan_does_not_follow_candidate_replacement(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end
          local ra=ns.ProfRouteAuto;local r=finish('alchemy',{start=1,target=3})
          local run=assert(ns.ProfExecution.Bind('alchemy',r));local frozen=run.plan
          assert(ra.Get('alchemy',{start=1,target=3})==frozen)
          ra.Invalidate('prices')
          assert(ra.Get('alchemy',{start=2,target=3})==frozen and frozen.stale)
          assert(run.plan==frozen and run.plan.planID==r.planID)
        ''')

    def test_explicit_recalculation_preserves_material_cost_despite_current_bags(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function(slug,opts)
            local s=fixture();s.executionInventory=opts.executionInventory
            return ns.ProfEconomy.Index(s)
          end
          local ra=ns.ProfRouteAuto;local opts={start=1,target=3}
          local original=finish('alchemy',opts);assert(original.total==14)
          local old=assert(ns.ProfExecution.Bind('alchemy',original))
          bag[11]=1
          ra.Recalculate('alchemy',opts);local result=finish('alchemy',opts)
          assert(result.total==14 and next(result.seedInventory)==nil)
          assert(original.total==14 and old.plan.total==14 and old.status=='archived')
          assert(result.planID~=original.planID)
          assert(result.mats[1].count==2,'route budget must include every consumed ingredient')
        ''')

    def test_only_latest_candidate_per_profession_is_saved(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function(slug)
            local s=fixture();s.recipes[1].profession=slug
            s.professions={[slug]={cur=1,max=300}};s.known={[slug..':101']=true}
            return ns.ProfEconomy.Index(s)
          end
          local ra=ns.ProfRouteAuto
          other=finish('enchanting',{start=1,target=3})
          for _,target in ipairs({3,5,4}) do
            local opts={start=1,target=target}
            ra.Recalculate('alchemy',opts);latest=finish('alchemy',opts)
          end
          local store=DungeonsForeverDB.prof.routePlans.characters['Test-Realm']
          local count=0
          for _,entry in pairs(store.routes) do
            count=count+1
            assert(entry.skeleton.actions==nil and entry.skeleton.dependencyGraph==nil)
            assert(entry.skeleton.phaseCpuMs==nil and entry.skeleton.solverWork==nil)
            assert(entry.result==nil and entry.skeleton.inventory==nil)
            for _,key in ipairs({'mats','formulas','total','executionSteps','recoverySnapshot'})do assert(entry.skeleton[key]==nil)end
            for _,row in ipairs(entry.skeleton.steps)do assert(row.recipe==nil and row.cost==nil and row.mats==nil)end
            if entry.slug=='alchemy' then assert(entry.skeleton.planID==latest.planID and entry.skeleton.target==4)
            else assert(entry.slug=='enchanting' and entry.skeleton.planID==other.planID)end
          end
          assert(count==2 and #latest.actions>0,'only persistence should drop replay data')
        ''')
        self.load((ROOT/'Core'/'ProfRoutePlans.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local ra=ns.ProfRouteAuto
          local r=finish('alchemy',{start=1,target=4})
          assert(r.cached and r.planID==latest.planID and r.total==latest.total)
          assert(finish('enchanting',{start=1,target=3}).planID==other.planID)
        ''')

    def test_compact_candidate_reload_preserves_purchases_allocations_and_execution(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()
            local s=fixture();s.recipes[1].yellow=2;s.recipes[1].green=2;s.recipes[1].grey=2
            s.recipes[2]={profession='alchemy',spell=102,item=12,count=1,mats={{10,2}},
              learn=2,yellow=100,green=200,grey=300,cooldown=false}
            s.known['alchemy:102']=true
            return ns.ProfEconomy.Index(s)
          end
          original=finish('alchemy',{start=1,target=4})
          assert(original.targetReached and #original.executionSteps>1)
          DungeonsForeverDB=ns.ProfEconomy.Copy(DungeonsForeverDB)
        ''')
        self.load((ROOT/'Core'/'ProfRoutePlans.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local r=finish('alchemy',{start=1,target=4})
          assert(r.cached and r.fromSkeleton and #r.actions>0 and #original.actions>0)
          local function same(a,b,path)
            path=path or ''
            if type(a)~='table' then assert(a==b,path..': '..tostring(a)..' ~= '..tostring(b));return end
            assert(type(b)=='table')
            for k,v in pairs(a)do same(v,b[k],path..'/'..tostring(k))end
            for k in pairs(b)do assert(a[k]~=nil)end
          end
          for _,key in ipairs({'total','netTotal','matTotal','formulasTotal','feasible','targetReached',
            'learningComplete','supplyComplete','mats','formulas','saleOutputs','recoverySnapshot',
            'diagnostics','seedInventory','retainedToolItems'})do same(original[key],r[key])end
          local function allocations(step)
            local out={}
            for _,edge in ipairs(step.allocations)do
              local key=edge.consumerID..':'..edge.itemID;out[key]=(out[key] or 0)+edge.count
            end
            return out
          end
          for i,step in ipairs(original.executionSteps)do
            local restored=r.executionSteps[i]
            same(allocations(step),allocations(restored),'allocations')
            for _,key in ipairs({1,2,3,4,'segmentID','recipe','requiredOutputs','cost',
              'profession','expectedCrafts','attemptLimit'})do same(step[key],restored[key])end
          end
          for i,step in ipairs(original.steps)do
            for _,key in ipairs({1,2,3,4,'segments','segmentIDs','cost','role'})do same(step[key],r.steps[i][key])end
          end
          local run=assert(ns.ProfExecution.Bind('alchemy',r))
          local first=run.plan.executionSteps[1]
          assert(ns.ProfExecution.RecordAttempt('alchemy',first[3],'cached-cast',first.segmentID))
          assert(ns.ProfExecution.RecordOutput({itemID=first.item,quantity=1,castGUID='cached-cast'}))
          assert(ns.ProfExecution.Progress('alchemy',1).casts==1 and run.materialLedger.consumed[11]==1)
        ''')


    def reload_routes(self):
        self.lua.execute('DungeonsForeverDB=ns.ProfEconomy.Copy(DungeonsForeverDB)')
        self.load((ROOT/'Core'/'ProfRoutePlans.lua').read_text(encoding='utf-8-sig'))

    def test_frozen_execution_survives_full_reload_without_requoting(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end
          original=finish('alchemy',{start=1,target=3})
          local run=assert(ns.ProfExecution.Bind('alchemy',original))
          ns.ProfExecution.RecordAttempt('alchemy',101,'before-reload')
          ns.ProfEconomy.Capture=function()error('frozen execution must not recapture')end
        ''')
        self.load((ROOT/'Core'/'ProfExecution.lua').read_text(encoding='utf-8-sig'))
        self.reload_routes()
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=3})
          assert(r.planID==original.planID and r.total==14 and #r.mats>0 and #r.actions>0)
          assert(not r.fromSkeleton and ns.ProfExecution.Progress('alchemy',1).casts==1)
          assert(ns.ProfExecution.RecordOutput({itemID=10,quantity=1,castGUID='before-reload'}))
        ''')

    def test_missing_recipe_retains_whole_skeleton_and_blocks_execution(self):
        self.lua.execute('''
          missing=false
          ns.ProfEconomy.Capture=function()
            local s=fixture();if missing then s.recipes={}end
            return ns.ProfEconomy.Index(s)
          end
          original=finish('alchemy',{start=1,target=3});missing=true
        ''')
        self.reload_routes()
        self.lua.execute('''
          local r=finish('alchemy',{start=1,target=3})
          assert(r.fromSkeleton and r.status=='recalculate_required' and not r.feasible and not r.completeCost)
          assert(#r.executionSteps==#original.executionSteps and r.executionSteps[1][3]==101)
          assert(not ns.ProfExecution.Bind('alchemy',r),'unresolved skeleton became executable')
          local c=DungeonsForeverDB.prof.routePlans.characters['Test-Realm']
          assert(c.routes[c.active.alchemy].skeleton.steps[1][3]==101)
        ''')

    def test_current_auction_shortage_cannot_turn_into_free_materials(self):
        self.lua.execute('''
          remaining=2
          ns.ProfEconomy.Capture=function()
            local s=fixture();s.auctionSupply={[11]={quantity=remaining}}
            return ns.ProfEconomy.Index(s)
          end
          original=finish('alchemy',{start=1,target=3,considerAuctionSupply=true});remaining=1
        ''')
        self.reload_routes()
        self.lua.execute('''
          local r=finish('alchemy',{start=1,target=3,considerAuctionSupply=true})
          assert(r.status=='recalculate_required' and not r.feasible and not r.priced)
          local found=false;for _,d in ipairs(r.diagnostics)do if d.code=='auctionSupplyLimited'then found=true end end
          assert(found and not ns.ProfExecution.Bind('alchemy',r))
        ''')

    def test_rebuild_shares_whole_vendor_packs_across_saved_steps(self):
        self.lua.execute('''
          price=1;pack=11
          ns.ProfEconomy.Capture=function()
            local s=fixture();s.recipes[1].yellow=2;s.recipes[1].green=2;s.recipes[1].grey=2
            s.recipes[2]={profession='alchemy',spell=102,item=12,count=1,mats={{11,1}},
              learn=2,yellow=100,green=200,grey=300,cooldown=false}
            s.known['alchemy:102']=true;s.prices[11]=price
            s.offers={[11]={{quantity=5,price=pack,unlimited=true,reference=true}}}
            s.auctionSupply={[11]={quantity=2}}
            return ns.ProfEconomy.Index(s)
          end
          original=finish('alchemy',{start=1,target=8,considerAuctionSupply=true})
          assert(original.total==13 and #original.executionSteps==2)
          price=7;pack=10
        ''')
        self.reload_routes()
        self.lua.execute('''
          local r=finish('alchemy',{start=1,target=8,considerAuctionSupply=true})
          assert(r.targetReached and r.total==20 and r.vendorTotal==20 and r.ahTotal==0)
          assert(#r.mats==1 and r.mats[1].count==10 and r.inventory[11]==3)
          assert(r.executionSteps[1][4]==1 and r.executionSteps[2][4]==6 and r.expanded==0)
        ''')

    def test_cross_profession_chronology_is_restored_at_saved_start_skills(self):
        self.lua.execute('''
          secondarySkill=1
          ns.ProfEconomy.Capture=function()
            local s=fixture();s.prices={[11]=100,[12]=2}
            s.professions.enchanting={cur=secondarySkill,max=300}
            s.recipes[2]={profession='enchanting',spell=102,item=11,count=1,mats={{12,1}},
              learn=1,yellow=100,green=200,grey=300,cooldown=false}
            s.known['enchanting:102']=true
            return ns.ProfEconomy.Index(s)
          end
          opts={start=1,target=3,allowSecondaryLeveling=true,secondaryProfession='enchanting'}
          original=finish('alchemy',opts);assert(original.total==4)
          local found=false;for _,step in ipairs(original.executionSteps)do if step.profession=='enchanting'then found=true end end
          assert(found);secondarySkill=50
        ''')
        self.reload_routes()
        self.lua.execute('''
          local r=finish('alchemy',opts)
          assert(r.targetReached and r.total==4 and #r.executionSteps==#original.executionSteps)
          for i,step in ipairs(original.executionSteps)do
            local restored=r.executionSteps[i]
            assert(restored.profession==step.profession and restored.segmentID==step.segmentID)
            for k=1,4 do assert(restored[k]==step[k])end
          end
        ''')

    def test_manual_conversion_is_kept_when_new_quotes_favor_another_route(self):
        self.lua.execute('''
          greater=2;lesser=10
          ns.ProfEconomy.Capture=function()
            return ns.ProfEconomy.Index({recipes={{profession='enchanting',spell=101,count=1,
              mats={{10938,3}},learn=1,yellow=100,green=200,grey=300,cooldown=false}},
              professions={enchanting={cur=1,max=300}},known={['enchanting:101']=true},
              prices={[10938]=lesser,[10939]=greater},essenceConversions=true,coverageComplete=true})
          end
          original=finish('enchanting',{start=1,target=3});assert(original.total==4)
          assert(original.executionSteps[1].kind=='essence_conversion')
          greater=99;lesser=1
        ''')
        self.reload_routes()
        self.lua.execute('''
          local r=finish('enchanting',{start=1,target=3})
          assert(r.targetReached and r.total==198 and not r.optimal)
          assert(#r.executionSteps==#original.executionSteps)
          for i,step in ipairs(original.executionSteps)do
            local restored=r.executionSteps[i]
            assert(restored.kind==step.kind and restored[4]==step[4])
            if step.kind=='essence_conversion'then
              assert(restored.manual and restored.sourceItem==10939 and restored.targetItem==10938)
              assert(restored.sourceCount==step.sourceCount and restored.targetCount==step.targetCount)
            end
          end
        ''')

    def test_specialization_quest_and_its_allocations_survive_reload(self):
        self.lua.execute('''
          skills.engineering={cur=200,max=300}
          ns.ProfEconomy.RecipeSpecializationAllowed=function(r,s,state)
            return r.spell~=102 or state and state.specializationAbilities[20219]==true,'specializationRequired'
          end
          ns.ProfEconomy.Capture=function()
            return ns.ProfEconomy.Index({recipes={
              {profession='engineering',spell=101,item=11,count=1,mats={{12,1}},learn=1,yellow=2,green=2,grey=2,cooldown=false},
              {profession='engineering',spell=102,item=10,count=1,mats={{11,1}},learn=200,yellow=300,green=300,grey=300,cooldown=false}},
              professions={engineering={cur=200,max=300}},known={['engineering:101']=true,['engineering:102']=true},
              prices={[12]=3},coverageComplete=true,specializationAbilities={[20219]=false},
              specializationGoals={{id='gnomish',profession='engineering',questID=3641,abilityID=20219,minSkill=200,inputs={{11,2}}}}})
          end
          original=finish('engineering',{start=200,target=201,engineeringSpecialization='gnomish'})
          assert(original.targetReached and original.total==9)
          local quest=false
          for _,step in ipairs(original.executionSteps)do if step.kind=='specialization_quest'then quest=true end end
          assert(quest)
        ''')
        self.reload_routes()
        self.lua.execute('''
          local r=finish('engineering',{start=200,target=201,engineeringSpecialization='gnomish'})
          assert(r.targetReached and r.total==9 and #r.executionSteps==#original.executionSteps)
          local allocated=0
          for _,step in ipairs(r.executionSteps)do
            if step.kind=='specialization_quest'then
              assert(step.goalID=='gnomish' and step.questID==3641 and step.abilityID==20219)
              assert(step.inputs[1][1]==11 and step.inputs[1][2]==2)
            end
            for _,edge in ipairs(step.allocations)do
              if edge.consumerID=='segment:quest:gnomish:1' then allocated=allocated+edge.count end
            end
          end
          assert(allocated==2 and r.completedSpecializationGoals.gnomish)
        ''')

    def test_logout_saves_inflight_prefix_without_copying_full_result(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end
          original=finish('alchemy',{start=1,target=3})
          -- Reinsert a live job through the actual facade and stop it after
          -- its first usable prefix; a search result contains a poison value
          -- to prove logout never deep-copies the whole result.
          local elapsed=0;debugprofilestop=function()elapsed=elapsed+.03;return elapsed end
          ns.ProfRouteAuto.Recalculate('alchemy',{start=1,target=60,cpuLimitMs=8000})
          for i=1,10000 do
            ns.ProfRouteAuto.Pump('alchemy')
            local r=ns.ProfRouteAuto.Peek('alchemy')
            if r and #r.steps>0 then break end
          end
          local r=ns.ProfRouteAuto.Peek('alchemy')
          assert(r and #r.steps>0 and ns.ProfRouteAuto.HasWork('alchemy'))
          r.actions=setmetatable({},{__profLearningMaterialize=function()error('copied action log')end})
          for _,frame in ipairs(frames)do if frame.events.PLAYER_LOGOUT then frame.OnEvent(frame,'PLAYER_LOGOUT')end end
          local c=DungeonsForeverDB.prof.routePlans.characters['Test-Realm']
          local saved=c.routes[c.active.alchemy].skeleton
          assert(saved.status=='interrupted' and saved.steps and not saved.actions and not saved.mats)
        ''')


    def test_fishing_rebuild_keeps_recipe_and_refreshes_fish_metadata(self):
        self.load((ROOT/'Core'/'ProfFishing.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          price=2
          skills.cooking={cur=1,max=300}
          ns.ProfFishingRoutes={fish={[6291]={areas={{zoneID=12,minSkill=1}},restrictionsVerified=true}}}
          ns.ProfEconomy.Capture=function()
            return ns.ProfEconomy.Index({recipes={{profession='cooking',spell=7751,item=10,count=1,
              mats={{6291,1},{11,1}},learn=1,yellow=100,green=200,grey=300,cooldown=false}},
              professions={cooking={cur=1,max=300}},known={['cooking:7751']=true},prices={[11]=price},coverageComplete=true})
          end
          opts={start=1,target=3,scheme='fishing'}
          original=finish('cooking',opts);assert(original.total==4 and original.fishMaterials[1].count==2)
          price=7;ns.ProfFishingRoutes.fish[6291].areas[1].zoneID=14
        ''')
        self.reload_routes()
        self.lua.execute('''
          local r=finish('cooking',opts)
          assert(r.fromSkeleton and r.targetReached and r.total==14 and r.executionSteps[1][3]==7751)
          assert(r.fishMaterials[1].count==2 and r.fishMaterials[1].areas[1].zoneID==14)
          assert(#r.mats==1 and r.mats[1].id==11 and not r.optimal and not r.searchComplete)
        ''')

    def test_tool_goal_and_retained_material_obligation_are_rebuilt(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()
            local s=fixture();s.recipes[2]={profession='alchemy',spell=102,item=99,count=1,mats={{11,1}},
              learn=1,yellow=1,green=1,grey=1,cooldown=false,tool=true,toolItem=99}
            s.known['alchemy:102']=true
            s.toolGoals={{id='tool',profession='alchemy',item=99,spell=102,minSkill=1,bindOnPickup=true}}
            s.retainedToolItems={[99]=1};s.toolCraftOnlyItems={[99]=true}
            return ns.ProfEconomy.Index(s)
          end
          original=finish('alchemy',{start=1,target=3});assert(original.total==21)
        ''')
        self.reload_routes()
        self.lua.execute('''
          local r=finish('alchemy',{start=1,target=3})
          assert(r.targetReached and r.total==21 and r.completedToolGoals.tool and r.retainedToolItems[99]==1)
          local found=false;for _,step in ipairs(r.executionSteps)do
            if step[3]==102 then
              assert(step.tool and step.toolItem==99 and step.requiredOutputs[99]==1);found=true
            end
          end
          assert(found)
        ''')

    def test_future_formula_reserves_auction_stock_shared_with_earlier_reagent(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()
            local s=fixture();s.recipes[1].mats={{400,1}}
            s.recipes[1].yellow=2;s.recipes[1].green=2;s.recipes[1].grey=2
            s.recipes[2]={profession='alchemy',spell=102,item=12,count=1,mats={{11,1}},formula=400,
              learn=2,yellow=100,green=200,grey=300,cooldown=false}
            s.prices[400]=1;s.offers={[400]={{price=5,quantity=1,unlimited=true}}}
            s.formulaOffers={[400]={}};s.auctionSupply={[400]={quantity=1,observedAt=1000,complete=true,ownerExcluded=true,source='client-auction-results'}}
            return ns.ProfEconomy.Index(s)
          end
          opts={start=1,target=3,considerAuctionSupply=true}
          original=finish('alchemy',opts);assert(original.targetReached and original.total==13)
        ''')
        self.reload_routes()
        self.lua.execute('''
          local r=finish('alchemy',opts)
          assert(r.targetReached and r.total==13 and r.formulasTotal==1 and #r.formulas==1)
          local bought=0;for _,m in ipairs(r.mats)do if m.id==400 then assert(m.source=='vendor');bought=bought+m.count end end
          assert(bought==1 and r.formulas[1].source=='ah' and r.formulas[1].count==1)
        ''')

    def test_opening_inventory_does_not_discount_cost_before_or_after_reload(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end
          opts={start=1,target=3,executionInventory={[11]=1}}
          original=finish('alchemy',opts);assert(original.total==14)
        ''')
        self.reload_routes()
        self.lua.execute('''
          local r=finish('alchemy',{start=1,target=3})
          assert(r.targetReached and r.total==14 and r.mats[1].count==2 and next(r.seedInventory)==nil)
        ''')

    def test_changed_recipe_cannot_satisfy_invalid_saved_allocations(self):
        self.lua.execute('''
          producerCount=2
          ns.ProfEconomy.Capture=function()
            local s=fixture();s.recipes[1].count=producerCount
            s.recipes[1].yellow=2;s.recipes[1].green=2;s.recipes[1].grey=2
            s.recipes[2]={profession='alchemy',spell=102,item=12,count=1,mats={{10,2}},
              learn=2,yellow=100,green=200,grey=300,cooldown=false}
            s.known['alchemy:102']=true;return ns.ProfEconomy.Index(s)
          end
          original=finish('alchemy',{start=1,target=3});producerCount=1
        ''')
        self.reload_routes()
        self.lua.execute('''
          local r=finish('alchemy',{start=1,target=3})
          assert(r.status=='recalculate_required' and not r.feasible and not ns.ProfExecution.Bind('alchemy',r))
          assert(#r.executionSteps==#original.executionSteps)
        ''')


    def test_rebuild_does_not_activate_an_interrupted_recalculation(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end
          original=finish('alchemy',{start=1,target=3})
          assert(ns.ProfExecution.Bind('alchemy',original))
          ns.ProfExecution.PrepareRecalculate('alchemy')
          assert(not ns.ProfExecution.GetRun('alchemy') and ns.ProfExecution.IsPreparing('alchemy'))
        ''')
        self.reload_routes()
        self.lua.execute('''
          local r=finish('alchemy',{start=1,target=3})
          assert(r.fromSkeleton and r.targetReached)
          assert(not ns.ProfExecution.GetRun('alchemy'),'reading a candidate activated frozen execution')
          assert(ns.ProfExecution.IsPreparing('alchemy'))
        ''')


class NativeArchitectureTests(unittest.TestCase):
    def test_all_sources_compile_under_lua51_and_main_toc_paths_exist(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        compile_source=lua.eval("function(source,name)local fn,error=loadstring(source,name);return fn~=nil,error end")
        for path in (ROOT/"Core").rglob("*.lua"):
            ok,error=compile_source(path.read_text(encoding="utf-8-sig"),str(path))
            self.assertTrue(ok,error)
        toc=(ROOT/"DungeonsForever.toc").read_text(encoding="utf-8-sig")
        self.assertIn('## SavedVariables: DungeonsForeverDB',toc)
        self.assertIn('## LoadOnDemand: 0',toc)
        for line in toc.splitlines():
            if line.startswith(('Core\\','Locales\\')):
                relative=line.split(' [',1)[0].replace('\\','/')
                self.assertTrue((ROOT/relative).is_file(),relative)


if __name__=="__main__":unittest.main()
