"""Dev execution ledger: frozen routes, receipts, allocations and save migration."""
from pathlib import Path
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for runtime in (ROOT / ".pipeline-runtime" / "lib", Path(os.environ.get("TEMP", ".")) / "df-lua-runtime-py312"):
    if runtime.exists():
        sys.path.insert(0, str(runtime))
from lupa.lua51 import LuaRuntime

MOCKS = r'''
ns={LoadForeverPages=true};callbacks={};frames={};clock=1000
time=function() return clock end
UnitName=function() return 'Test' end;GetRealmName=function() return 'Realm' end
ns.Init=function(fn) callbacks[#callbacks+1]=fn end
function CreateFrame()
 local f={events={}}
 function f:SetScript(k,v)self[k]=v end
 function f:RegisterEvent(e)self.events[e]=true end
 function f:UnregisterEvent(e)self.events[e]=nil end
 function f:UnregisterAllEvents()self.events={} end
 frames[#frames+1]=f;return f
end
skills={alchemy={cur=1,max=300,primary=true},mining={cur=300,max=300,primary=true}}
bag={};C_Item={GetItemCount=function(id,bank)assert(not bank);return bag[id] or 0 end}
LOOT_ITEM_CREATED_SELF='You create: %s.'
LOOT_ITEM_CREATED_SELF_MULTIPLE='You create: %sx%d.'
local function copy(x)
 if type(x)~='table' then return x end
 local o={};for k,v in pairs(x)do o[k]=copy(v)end;return o
end
recipes={
 [101]={profession='alchemy',spell=101,item=10,count=2,outputMin=2,outputMax=3,mats={{20,1}},learn=1,yellow=100,green=200,grey=300},
 [102]={profession='alchemy',spell=102,item=11,count=2,outputMin=2,outputMax=2,mats={{10,2}},learn=1,yellow=100,green=200,grey=300}
}
ns.ProfEconomy={Copy=copy,CharacterKey=function()return 'Test-Realm'end,
 Professions=function()return skills end,FindRecipe=function(slug,spell)return recipes[spell]end,
 Gain=function(r,s)if s>=r.grey then return 0 end;return 1 end}
ns.ProfModule={ProfLearned=function()return skills end}
function initialize()for _,fn in ipairs(callbacks)do fn()end;callbacks={} end
function fixture()
 local rec=copy(recipes[101]);local seg={1,3,101,3,segmentID='a',profession='alchemy',recipe=rec,item=10,
 goalSkill=3,expectedGain=2,expectedCrafts=3,attemptLimit=3,outputMin=2,outputMax=3,
 requiredOutputs={[10]=6},materialMinCrafts=3,allocations={}}
 return {executionVersion=1,planVersion=2,planID='plan:one',revision=1,scheme='cheapest',start=1,target=3,
 feasible=true,status='complete',total=90,executionSteps={seg},steps={seg},mats={{id=20,count=3,source='ah'}},formulas={}}
end
'''


class ExecutionFusionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.load("Core/ProfTrack.lua")
        self.load("Core/ProfExecution.lua")
        self.lua.execute("initialize();xp=ns.ProfExecution;t=ns.ProfTrack;plan=fixture();run=xp.Bind('alchemy',plan)")

    def load(self, path):
        self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)", (ROOT / path).read_text(encoding="utf-8"))

    def test_skill_gain_alone_does_not_complete_material_obligation(self):
        self.lua.execute("skills.alchemy.cur=3;xp.Sync('alchemy');local p=t.Progress('alchemy');assert(p.skillDone and not p.materialDone and not p.complete);assert(run.currentIndex==1)")

    def test_high_yield_receipts_satisfy_quota_without_extra_casts(self):
        self.lua.execute("""
          xp.RecordAttempt('alchemy',101,'a');xp.RecordOutput({itemID=10,quantity=3,castGUID='a'})
          xp.RecordAttempt('alchemy',101,'b');xp.RecordOutput({itemID=10,quantity=3,castGUID='b'})
          skills.alchemy.cur=3;xp.Sync('alchemy');local p=t.Progress('alchemy',1)
          assert(p.complete and p.casts==2 and p.outputs==6 and run.currentIndex==2)
        """)

    def test_unconfirmed_casts_and_unrelated_bag_stock_never_become_carry(self):
        self.lua.execute("xp.RecordAttempt('alchemy',101,'a');bag[10]=200;bag[20]=900;assert(next(t.ContinueInventory('alchemy'))==nil)")

    def test_candidate_publications_do_not_replace_frozen_plan(self):
        self.lua.execute("""
          xp.RecordAttempt('alchemy',101,'a');local original=run.plan
          local candidate=fixture();candidate.revision=2;candidate.executionSteps[1][4]=99
          assert(t.Bind('alchemy',candidate)==run and run.plan==original and run.newPlanAvailable)
          assert(t.Progress('alchemy',1).casts==1 and original.executionSteps[1][4]==3)
          assert(not t.Rebase(run,candidate.executionSteps))
        """)

    def test_confirmed_consumed_intermediates_are_deducted_and_bag_capped(self):
        self.lua.execute("""
          local p=fixture();local b={1,3,102,1,segmentID='consumer',profession='alchemy',recipe=recipes[102],item=11,
            goalSkill=3,expectedGain=2,expectedCrafts=1,attemptLimit=1,outputMin=2,requiredOutputs={}}
          p.executionSteps[2]=b;run=xp.StartNew('alchemy',p)
          xp.RecordAttempt('alchemy',101,'a');xp.RecordOutput({itemID=10,quantity=3,castGUID='a'})
          xp.RecordAttempt('alchemy',101,'b');xp.RecordOutput({itemID=10,quantity=3,castGUID='b'})
          xp.RecordAttempt('alchemy',102,'consume');bag[10]=3;bag[20]=900
          assert(xp.GetContinuation('alchemy')[10]==3 and xp.GetContinuation('alchemy')[20]==nil)
          bag[10]=100;assert(xp.GetContinuation('alchemy')[10]==4)
        """)

    def test_manual_verification_preserves_actual_cast_count(self):
        self.lua.execute("xp.RecordAttempt('alchemy',101,'a');assert(t.VerifyOutput('alchemy',1,10,3));local p=t.Progress('alchemy',1);assert(p.outputs==3 and p.casts==1 and p.pendingOutputs==0)")

    def test_duplicate_cast_and_receipt_order_are_reconciled(self):
        self.lua.execute("""
          xp.RecordOutput({itemID=10,quantity=3,castGUID='a'});xp.RecordAttempt('alchemy',101,'a')
          xp.RecordAttempt('alchemy',101,'a');assert(t.Progress('alchemy',1).casts==1 and t.Progress('alchemy',1).outputs==3)
        """)

    def test_recalculate_inherits_only_validated_remaining_outputs(self):
        self.lua.execute("""
          local p=fixture();p.executionSteps[2]={3,4,102,1,segmentID='consumer',profession='alchemy',recipe=recipes[102],item=11,
             goalSkill=4,expectedGain=1,expectedCrafts=1,attemptLimit=1,requiredOutputs={}}
          run=xp.StartNew('alchemy',p);xp.RecordAttempt('alchemy',101,'a');xp.RecordOutput({itemID=10,quantity=3,castGUID='a'})
          bag[10]=20;local inventory,id=xp.PrepareRecalculate('alchemy');assert(inventory[10]==3 and id==run.planID and not xp.GetRun('alchemy'))
          local again,source=xp.PrepareRecalculate('alchemy');assert(again[10]==3 and source==id)
        """)

    def test_reload_keeps_same_plan_and_progress(self):
        self.lua.execute("xp.RecordAttempt('alchemy',101,'a');savedID=run.planID")
        self.load("Core/ProfExecution.lua")
        self.lua.execute("initialize();xp=ns.ProfExecution;t=ns.ProfTrack;assert(t.GetRun('alchemy').planID==savedID and t.Progress('alchemy',1).casts==1)")

    def test_only_execution_observer_is_registered(self):
        self.lua.execute("assert(not t.frame and xp.eventFrame);xp.eventFrame.OnEvent(xp.eventFrame,'UNIT_SPELLCAST_SUCCEEDED','player','hidden',101);assert(t.Progress('alchemy',1).casts==1)")

    def test_legacy_dev_save_migrates_without_losing_receipts(self):
        self.lua.execute("""
          DungeonsForeverDB={prof={track={['Test-Realm']={version=1,nextID=1,nextAttempt=1,active={alchemy='old'},runs={
            old={planID='old',slug='alchemy',status='active',scheme='cheapest',start=1,target=3,
              steps={{from=1,to=3,spell=101,crafts=3,item=10,mats={{20,1}}}},
              progress={{casts=1,attempts={{seq=1,spell=101,item=10,out=3,at=999,castGUID='oldcast'}}}},outputs={[10]=3}}
          }}}}}
        """)
        self.load("Core/ProfExecution.lua")
        self.lua.execute("initialize();xp=ns.ProfExecution;t=ns.ProfTrack;local old=t.GetRun('alchemy');assert(old.planID=='old' and old.legacyTrack and old.executionMigration==1);local p=t.Progress('alchemy',1);assert(p.casts==1 and p.outputs==3);assert(old.plan.executionSteps[1].recipe.spell==101)")

    def test_first_aid_keeps_dev_automatic_route_support(self):
        self.lua.execute("local p=fixture();p.executionSteps[1].profession='first-aid';assert(xp.NormalizePlan('first-aid',p));assert(xp.StartNew('first-aid',p))")

    def test_late_receipt_updates_archived_source_not_replacement(self):
        self.lua.execute("""
          xp.RecordAttempt('alchemy',101,'oldcast');local old=run
          local p=fixture();p.planID='replacement';run=xp.StartNew('alchemy',p)
          xp.RecordOutput({itemID=10,quantity=3,castGUID='oldcast'})
          assert(t.Progress('alchemy',1).outputs==0)
          assert(xp.Progress('alchemy',1,nil,old.planID).actualOutputs==3)
        """)

    def test_consumption_cannot_fulfil_another_material_obligation_twice(self):
        self.lua.execute("""
          local p=fixture();local a=p.executionSteps[1]
          a.expectedGain=0;a.goalSkill=nil;a.requiredOutputs={[10]=2};a[4]=1;a.expectedCrafts=1
          a.allocations={{consumerID='consumer',itemID=10,count=2}}
          local b={1,1,102,1,segmentID='consumer',profession='alchemy',recipe=recipes[102],item=11,
            expectedGain=0,expectedCrafts=1,attemptLimit=1,outputMin=2,requiredOutputs={[11]=2},allocations={}}
          local c=fixture().executionSteps[1];c.segmentID='later';c.expectedGain=0;c.goalSkill=nil;c.requiredOutputs={[10]=2}
          c[4]=1;c.expectedCrafts=1;c.allocations={{consumerID='future',itemID=10,count=2}}
          p.executionSteps={a,b,c};run=xp.StartNew('alchemy',p)
          xp.RecordAttempt('alchemy',101,'first');xp.RecordOutput({itemID=10,quantity=2,castGUID='first'})
          xp.RecordAttempt('alchemy',101,'second');xp.RecordOutput({itemID=10,quantity=2,castGUID='second'})
          xp.RecordAttempt('alchemy',102,'spend1');xp.RecordOutput({itemID=11,quantity=2,castGUID='spend1'})
          xp.RecordAttempt('alchemy',102,'spend2');xp.RecordOutput({itemID=11,quantity=2,castGUID='spend2'})
          local later=xp.Progress('alchemy',3)
          assert(later.actualOutputs==2 and not later.materialDone and later.remainingOutputs==2 and later.divertedOutputs==2)
          assert(xp.Progress('alchemy',1).complete)
        """)

    def load_follow(self):
        self.lua.execute("""
          ns.L=setmetatable({},{__index=function(_,k)return k end})
          ns.ProfData={pro={alchemy={name='Alchemy'}}};ns.ProfLeveling={alchemy={steps={{1,3,101,3}}}}
          ns.ProfRecipes={alchemy={rows={}}};ns.ProfHost={DG={},Unpack=unpack}
          ns.ProfRouteAuto={Available=function()return false end}
          ns.ProfModule.Setting=function(k)return k=='autoRoute' or k=='autoFromCurrent' end
          ns.ProfModule.SettingRaw=function(k)if k=='autoScheme' then return 'cheapest' end end
          C_Item.GetItemCount=function(id)return bag[id] or 0 end
          DungeonsForeverDB.prof.follow={['Test-Realm']={slug='alchemy',skill=1,step=1,t0=1000}}
        """)
        self.load("Core/ProfFollow.lua")
        self.lua.execute("initialize();pf=ns.ProfFollow;follow=DungeonsForeverDB.prof.follow['Test-Realm']")

    def test_hud_does_not_skip_producer_when_skill_already_reached(self):
        self.load_follow()
        self.lua.execute("skills.alchemy.cur=3;pf.Sync();assert(follow.step==1 and not xp.Progress('alchemy',1).complete)")

    def test_hud_advances_only_after_material_quota_is_met(self):
        self.load_follow()
        self.lua.execute("""
          skills.alchemy.cur=3;pf.Sync()
          xp.RecordAttempt('alchemy',101,'a');xp.RecordOutput({itemID=10,quantity=3,castGUID='a'})
          xp.RecordAttempt('alchemy',101,'b');xp.RecordOutput({itemID=10,quantity=3,castGUID='b'})
          pf.Sync();assert(follow.step==2)
        """)

    def test_hud_waiting_for_solver_keeps_automatic_mode(self):
        self.load_follow()
        self.lua.execute("""
          xp.End('alchemy','ended');ns.ProfRouteAuto.Get=function()return {status='searching',steps={}}end
          pf.InvalidateRoute();pf.Sync();assert(pf.pendingPlans.alchemy.status=='searching')
        """)

    def test_hud_uses_normalized_frozen_materials(self):
        self.load_follow()
        self.lua.execute("local needs=pf.SupplementNeeds('alchemy');assert(needs and needs.items[1].id==20 and needs.items[1].need==3)")

    def test_hud_rejects_output_confirmation_from_an_old_plan(self):
        self.load_follow()
        self.lua.execute("assert(not pf.VerifyCurrentOutput(5,{index=1,item=10,planID='obsolete'}));assert(t.Progress('alchemy',1).outputs==0)")

    def test_hud_rank_guidance_reads_actual_caps_for_main_and_current_partner(self):
        self.load_follow()
        self.lua.execute("""
          ns.ProfTrainers={};local ranks={
            {cap=75,sk=0,lv=5,zh='初级'}, {cap=150,sk=50,lv=10,zh='中级'},
            {cap=225,sk=125,lv=20,zh='高级'}, {cap=300,sk=200,lv=35,zh='专家级'}}
          ns.ProfTrainers.alchemy={ranks=ranks,list={}};ns.ProfTrainers.mining={ranks=ranks,list={}}
          caps={alchemy=75,mining=75};GetProfessions=function()return 1,2 end
          GetProfessionInfo=function(slot)
            local p=slot==1 and 'alchemy' or 'mining';return p,nil,75,caps[p],nil,nil,slot==1 and 171 or 186
          end
          UnitLevel=function()return 60 end;UnitFactionGroup=function()return 'Alliance'end
          local seg=run.plan.executionSteps[1];seg.profession='mining';seg[1]=75;seg[2]=150;seg.goalSkill=150
        """)
        self.load("Core/ProfRanks.lua")
        self.lua.execute("""
          local frozen=run.plan.executionSteps[1]
          local tasks=pf.RankTasks('alchemy',300,run.plan.executionSteps,1)
          assert(#tasks==2 and tasks[1].profession=='alchemy' and tasks[1].cap==150)
          assert(tasks[2].profession=='mining' and tasks[2].cap==150)
          assert(not tasks[1].complete and not tasks[2].complete and tasks[1].state.maxSkill==75)
          assert(ns.ProfRanks.Title(tasks[2]):find('150') and #ns.ProfRanks.Lines(tasks[2])>0)
          caps.alchemy=150;caps.mining=150;tasks=pf.RankTasks('alchemy',300,run.plan.executionSteps,1)
          assert(#tasks==1 and tasks[1].profession=='alchemy' and tasks[1].cap==225)
          assert(run.plan.executionSteps[1]==frozen and frozen[2]==150 and run.attemptsDone==0)
        """)

    def test_conversion_requires_explicit_confirmation_and_is_not_a_recipe_cast(self):
        self.load("Core/ProfEssences.lua")
        self.lua.execute("""
          local conversion=ns.ProfEssences.ForItem(10938)
          local p={executionVersion=1,planVersion=2,planID='conversion',scheme='cheapest',feasible=true,status='complete',
             executionSteps={{1,1,0,1,segmentID='convert',profession='enchanting',kind='essence_conversion',
               item=10938,goalSkill=1,expectedGain=0,expectedCrafts=1,attemptLimit=1,outputMin=3,
               conversion=conversion,requiredOutputs={[10938]=3}}},steps={},mats={},formulas={}}
          run=xp.StartNew('enchanting',p);bag[10938]=30
          assert(not xp.Progress('enchanting',1).complete)
          assert(not xp.RecordAttempt('enchanting',0,'not-a-craft'))
          assert(not xp.ConfirmConversion('enchanting',1,1,'obsolete'))
          assert(xp.ConfirmConversion('enchanting',1,1,run.planID))
          local progress=xp.Progress('enchanting',1)
          assert(progress.complete and progress.actualOutputs==3 and run.attemptsDone==0)
          assert(#xp.GetRecipeTotals('enchanting')==0)
        """)

    def test_observer_can_record_another_active_profession_once(self):
        self.lua.execute("""
          local p=fixture();p.planID='mining';p.executionSteps[1].profession='mining';p.executionSteps[1][3]=102
          p.executionSteps[1].recipe=recipes[102];p.executionSteps[1].item=11
          xp.StartNew('mining',p)
          xp.eventFrame.OnEvent(xp.eventFrame,'UNIT_SPELLCAST_SUCCEEDED','player','alchemy-cast',101)
          assert(xp.Progress('alchemy',1).casts==1 and xp.Progress('mining',1).casts==0)
        """)


class ExecutionSupplementSolverTests(unittest.TestCase):
    """The supplement ledger runs the real recursive procurement solver."""

    def setUp(self):
        from test_prof_solver_fusion import FIXTURE
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURE)
        self.lua.execute("""
          callbacks={};ns.Init=function(fn)callbacks[#callbacks+1]=fn end
          UnitName=function()return 'Test'end;GetRealmName=function()return 'Realm'end
          bag={};C_Item={GetItemCount=function(id)return bag[id]or 0 end}
          skills={alchemy={cur=1,max=300}}
        """)
        load = self.lua.eval("function(source)assert(loadstring(source))('DungeonsForever',ns)end")
        for name in ("ProfPolicies", "ProfEssences", "ProfGates", "ProfSolverCapture", "ProfRecovery", "ProfRouteSolver", "ProfTrack", "ProfExecution"):
            load((ROOT / "Core" / (name + ".lua")).read_text(encoding="utf-8-sig"))
        self.lua.execute("""
          ns.ProfEconomy.Professions=function()return skills end
          local r=recipe('alchemy',101,10,1,{{20,1}},1,300)
          local producer=recipe('alchemy',102,20,1,{{30,2}},1,1)
          local snap=snapshot({r,producer},{[20]=100,[30]=1});snap.professions=skills;snap.coverageComplete=true
          local capture=ns.ProfEconomy.Capture
          ns.ProfEconomy.Capture=function(slug,opts,tick)
              local input=ns.ProfEconomy.Copy(opts);input.snapshot=input.snapshot or snap
              return capture(slug,input,tick)
          end
          for _,fn in ipairs(callbacks)do fn()end
          xp=ns.ProfExecution
          run=xp.Bind('alchemy',{executionVersion=1,planVersion=2,planID='base',scheme='cheapest',feasible=true,status='complete',
            executionOptions={recoveryEnabled=false},executionSteps={{1,3,101,1,profession='alchemy',segmentID='base',recipe=r,
              item=10,goalSkill=3,expectedGain=2,expectedCrafts=1,attemptLimit=1,outputMin=1,requiredOutputs={}}},steps={},mats={},formulas={}})
          xp.RecordAttempt('alchemy',101,'used-budget')
        """)

    def test_topup_recursively_makes_material_and_extends_original_allowance(self):
        self.lua.execute("""
          assert(xp.Progress('alchemy',1).extraCrafts==2)
          local returned=xp.CalculateSupplement('alchemy')
          for i=1,5000 do local pending=xp.GetSupplement('alchemy');if not pending or not pending.inFlight then break end;xp.Pump('alchemy')end
          local supplement=xp.GetSupplement('alchemy')
          assert(supplement and not supplement.inFlight and supplement.feasible,tostring(supplement and supplement.error))
          assert(supplement.appended and supplement.total==4,tostring(supplement.total))
          assert(returned==supplement and not returned.inFlight and returned.total==4)
          assert(#run.plan.executionSteps==2 and run.plan.executionSteps[1][3]==102 and run.plan.executionSteps[2][3]==101)
          local progress=xp.Progress('alchemy',2);assert(progress.attemptLimit==3 and progress.casts==1)
        """)


if __name__ == "__main__":
    unittest.main()
