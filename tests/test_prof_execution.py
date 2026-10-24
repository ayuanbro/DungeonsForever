"""Persistent execution facts, receipt association, and shared procurement integration."""
import os
from pathlib import Path
import sys
import unittest

for path in (Path(os.environ.get("TEMP", "/tmp"))/"df-lua-runtime", Path.home()/"AppData/Local/Temp/df-lua-runtime"):
    sys.path.insert(0, str(path))
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
MOCKS = r'''
ns={LoadForeverPages=true}; frames={}; callbacks={}; jobs={}; clock=1000
time=function() return clock end
UnitName=function() return 'Test' end; GetRealmName=function() return 'Realm' end
function CreateFrame()
 local f={events={}}
 function f:SetScript(k,v) self[k]=v end
 function f:RegisterEvent(e) self.events[e]=true end
 frames[#frames+1]=f;return f
end
ns.Init=function(fn) callbacks[#callbacks+1]=fn end
ns.IdleJobs={Add=function(fn) jobs[#jobs+1]=fn end}
skills={alchemy={cur=1,max=300,primary=true},mining={cur=300,max=300,primary=true}}
bag={}; C_Item={GetItemCount=function(id,bank) assert(not bank);return bag[id] or 0 end}
LOOT_ITEM_CREATED_SELF='You create: %s.'
LOOT_ITEM_CREATED_SELF_MULTIPLE='You create: %sx%d.'
function fixture()
 local rec={profession='alchemy',spell=101,item=10,count=2,outputMin=2,outputMax=3,mats={{20,1}},learn=1,yellow=100,green=200,grey=300,cooldown=false}
 return {executionVersion=1,planVersion=2,planID='plan:one',revision=1,feasible=true,status='complete',total=90,
   executionSteps={{1,3,101,3,segmentID='a',profession='alchemy',recipe=rec,item=10,goalSkill=3,expectedGain=2,expectedCrafts=3,attemptLimit=3,
     outputMin=2,outputMax=3,requiredOutputs={[10]=6},materialMinCrafts=3}},steps={},mats={{id=20,count=3,source='ah'}},formulas={}}
end
function initialize() for _,fn in ipairs(callbacks) do fn() end;callbacks={} end
'''


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.load = self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        self.load(str(ROOT/"Core/ProfEconomy.lua"))
        self.load(str(ROOT/"Core/ProfRouteSolver.lua"))
        self.lua.execute("ns.ProfEconomy.Professions=function() return skills end")
        self.load(str(ROOT/"Core/ProfExecution.lua"))
        self.lua.execute("initialize(); xp=ns.ProfExecution; plan=fixture(); run=xp.Bind('alchemy',plan)")

    def test_skill_target_does_not_skip_material_minimum(self):
        self.lua.execute('''
          skills.alchemy.cur=3;xp.Sync('alchemy')
          local p=xp.Progress('alchemy');assert(p.skillDone and not p.materialDone and not p.complete)
          assert(p.minimumCrafts==3 and p.requiredOutputs==6 and p.remainingCrafts==3)
        ''')

    def test_actual_extra_yield_can_satisfy_quota_before_minimum_yield_count(self):
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'c1');xp.RecordOutput({itemID=10,quantity=3,castGUID='c1'})
          xp.RecordAttempt('alchemy',101,'c2');xp.RecordOutput({itemID=10,quantity=3,castGUID='c2'})
          skills.alchemy.cur=3;xp.Sync('alchemy');local p=xp.Progress('alchemy',1)
          assert(p.casts==2 and p.actualOutputs==6 and p.complete and run.currentIndex==2)
        ''')

    def test_unconfirmed_output_is_lower_bound_not_actual_items(self):
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'c1');local p=xp.Progress('alchemy')
          assert(p.actualOutputs==0 and p.guaranteedOutputs==2 and p.pendingOutputs==1)
          bag[10]=200;assert(next(xp.GetContinuation('alchemy'))==nil)
        ''')

    def test_cast_count_is_not_capped_at_the_estimate(self):
        self.lua.execute('''
          for i=1,7 do xp.RecordAttempt('alchemy',101,'c'..i) end
          assert(xp.Progress('alchemy',1).casts==7 and run.attemptsDone==7)
        ''')

    def test_duplicate_cast_guid_does_not_count_twice(self):
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'c1');xp.RecordAttempt('alchemy',101,'c2');xp.RecordAttempt('alchemy',101,'c1')
          assert(xp.Progress('alchemy',1).casts==2)
        ''')

    def test_background_publications_keep_frozen_progress(self):
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'c1');local old=run.plan
          local candidate=fixture();candidate.revision=22;candidate.executionSteps[1][4]=99
          assert(xp.Bind('alchemy',candidate)==run and run.plan==old and run.newPlanAvailable)
          assert(xp.Progress('alchemy',1).casts==1 and old.executionSteps[1][4]==3)
        ''')

    def test_feasible_search_prefix_can_start_tracking(self):
        self.lua.execute('''
          local p=fixture();p.planID='search';p.status='searching';p.partial=true
          local r=xp.StartNew('alchemy',p);assert(r and r.plan.planID=='search')
        ''')

    def test_reload_restores_same_plan_segment_and_counts(self):
        self.lua.execute("xp.RecordAttempt('alchemy',101,'c1'); savedID=run.planID;savedSegment=run.plan.executionSteps[1].segmentID")
        self.load(str(ROOT/"Core/ProfExecution.lua"))
        self.lua.execute('''
          initialize();xp=ns.ProfExecution;run=xp.Bind('alchemy',fixture())
          assert(run.planID==savedID and run.plan.executionSteps[1].segmentID==savedSegment)
          assert(xp.Progress('alchemy',1).casts==1)
        ''')

    def test_observer_records_without_any_hud_frame(self):
        self.lua.execute('''
          assert(not ns.ProfFollow);xp.eventFrame.OnEvent(xp.eventFrame,'UNIT_SPELLCAST_SUCCEEDED','player','hidden',101)
          xp.eventFrame.OnEvent(xp.eventFrame,'TRADE_SKILL_ITEM_CRAFTED_RESULT',{itemID=10,quantity=3,castGUID='hidden'})
          assert(xp.Progress('alchemy',1).casts==1 and xp.Progress('alchemy',1).actualOutputs==3)
        ''')

    def test_nonplayer_and_unrelated_spells_are_ignored(self):
        self.lua.execute('''
          xp.eventFrame.OnEvent(xp.eventFrame,'UNIT_SPELLCAST_SUCCEEDED','pet','x',101)
          xp.eventFrame.OnEvent(xp.eventFrame,'UNIT_SPELLCAST_SUCCEEDED','player','y',999)
          assert(run.attemptsDone==0)
        ''')

    def test_result_before_spell_success_is_matched(self):
        self.lua.execute('''
          xp.RecordOutput({itemID=10,quantity=3,castGUID='early'});xp.RecordAttempt('alchemy',101,'early')
          assert(xp.Progress('alchemy',1).actualOutputs==3)
        ''')

    def test_structured_and_localized_chat_are_reconciled(self):
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'c1')
          assert(xp.RecordCreatedMessage('You create: |Hitem:10|h[Powder]|h|rx3.',12))
          xp.RecordOutput({itemID=10,quantity=3,castGUID='c1'})
          assert(xp.Progress('alchemy',1).actualOutputs==3 and xp.Progress('alchemy',1).casts==1)
          assert(xp.RecordCreatedMessage('You create: |Hitem:10|h[Powder]|h|rx3.',12))
          assert(xp.Progress('alchemy',1).actualOutputs==3)
        ''')

    def test_two_identical_native_results_are_two_real_crafts(self):
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'c1');xp.RecordAttempt('alchemy',101,'c2')
          xp.RecordOutput({itemID=10,quantity=2,operationID=0,itemGUID='same-stack'})
          xp.RecordOutput({itemID=10,quantity=2,operationID=0,itemGUID='same-stack'})
          assert(xp.Progress('alchemy',1).actualOutputs==4)
        ''')

    def test_chat_format_supports_positional_placeholders_and_ignores_other_loot(self):
        self.lua.execute('''
          LOOT_ITEM_CREATED_SELF_MULTIPLE='制作了%2$dx%1$s。'
          xp.RecordAttempt('alchemy',101,'c1')
          assert(xp.RecordCreatedMessage('制作了3x|Hitem:10|h[粉末]|h。',21))
          assert(not xp.RecordCreatedMessage('You receive loot: |Hitem:10|h[Powder]|h.',22))
          assert(xp.Progress('alchemy',1).actualOutputs==3)
        ''')

    def test_manual_total_is_preserved_and_new_crafts_add_to_it(self):
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'c1');local id=run.plan.executionSteps[1].segmentID
          assert(xp.VerifyOutput('alchemy',id,10,3))
          xp.RecordAttempt('alchemy',101,'c2');xp.RecordOutput({itemID=10,quantity=2,castGUID='c2'})
          assert(xp.Progress('alchemy',1).actualOutputs==5)
          assert(not xp.VerifyOutput('alchemy',id,20,10))
        ''')

    def test_late_receipts_follow_archived_cast_not_new_plan(self):
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'old');oldRun=run
          local seed,id=xp.PrepareRecalculate('alchemy');assert(id==oldRun.planID and not xp.GetPlan('alchemy'))
          local p=fixture();p.planID='plan:two';run=xp.PlanRecalculated('alchemy',p)
          xp.RecordAttempt('alchemy',101,'new');xp.RecordOutput({itemID=10,quantity=3,castGUID='old'})
          assert(oldRun.progress[oldRun.plan.executionSteps[1].segmentID].attempts[1].actual==3)
          assert(xp.Progress('alchemy',1).actualOutputs==0 and oldRun.status=='archived')
        ''')

    def test_old_v2_without_obligations_requires_recalculation(self):
        self.lua.execute('''
          local old=fixture();old.executionVersion=nil
          local p,why=xp.NormalizePlan('alchemy',old);assert(p==nil and why=='migration_required')
        ''')

    def test_pure_leveling_legacy_adapter_does_not_invent_material_requirements(self):
        self.lua.execute('''
          ns.ProfEconomy.FindRecipe=function() return fixture().executionSteps[1].recipe end
          local old={steps={{1,3,101,2}}};local p=xp.NormalizePlan('alchemy',old)
          assert(p.executionVersion==1 and p.executionSteps[1].materialMinCrafts==0)
          assert(next(p.executionSteps[1].requiredOutputs)==nil)
        ''')

    def test_out_of_order_relevant_manual_cast_is_not_lost(self):
        self.lua.execute('''
          local p=fixture();local second=fixture().executionSteps[1];second[3]=102;second.recipe.spell=102;second.item=11;second.recipe.item=11;second.segmentID='b';second.requiredOutputs={[11]=1}
          p.executionSteps[2]=second;run=xp.StartNew('alchemy',p)
          assert(xp.RecordAttempt('alchemy',102,'ahead'))
          assert(xp.Progress('alchemy',2).casts==1 and xp.Progress('alchemy',1).casts==0)
        ''')

    def test_fractional_transition_can_finish_only_when_next_recipe_is_learnable(self):
        self.lua.execute('''
          local p=fixture();local a=p.executionSteps[1];a[2]=1;a.goalSkill=2;a.expectedGain=.5;a.fractionalTransition=true;a.attemptLimit=1;a.requiredOutputs={}
          local b=fixture().executionSteps[1];b.segmentID='b';b[3]=102;b.recipe.spell=102;b.recipe.learn=2;p.executionSteps[2]=b
          run=xp.StartNew('alchemy',p);xp.RecordAttempt('alchemy',101,'fractional');assert(not xp.Progress('alchemy',1).complete)
          b=run.plan.executionSteps[2];b.recipe.learn=1;xp.Sync('alchemy');assert(xp.Progress('alchemy',1).complete)
        ''')

    def test_continuation_uses_only_confirmed_unconsumed_intermediates_capped_by_bags(self):
        self.lua.execute('''
          local p=fixture();local b=fixture().executionSteps[1];b.segmentID='consumer';b[3]=102;b.recipe.spell=102;b.item=11;b.recipe.item=11;b.recipe.mats={{10,2}};b.requiredOutputs={}
          p.executionSteps[2]=b;run=xp.StartNew('alchemy',p)
          xp.RecordAttempt('alchemy',101,'p1');xp.RecordOutput({itemID=10,quantity=3,castGUID='p1'})
          xp.RecordAttempt('alchemy',101,'p2');xp.RecordOutput({itemID=10,quantity=3,castGUID='p2'})
          xp.RecordAttempt('alchemy',102,'consume');bag[10]=3;bag[20]=900
          local seed=xp.GetContinuation('alchemy');assert(seed[10]==3 and seed[20]==nil and seed[11]==nil)
          bag[10]=100;assert(xp.GetContinuation('alchemy')[10]==4)
        ''')

    def test_extra_output_is_allocated_once_to_a_later_occurrence(self):
        self.lua.execute('''
          local p=fixture();local a=p.executionSteps[1]
          a.expectedGain=0;a.goalSkill=nil;a.requiredOutputs={[10]=2}
          local b=fixture().executionSteps[1];b.segmentID='later';b.expectedGain=0;b.goalSkill=nil;b.requiredOutputs={[10]=2}
          local c=fixture().executionSteps[1];c.segmentID='last';c.expectedGain=0;c.goalSkill=nil;c.requiredOutputs={[10]=2}
          p.executionSteps={a,b,c};run=xp.StartNew('alchemy',p)
          xp.RecordAttempt('alchemy',101,'surplus');xp.RecordOutput({itemID=10,quantity=4,castGUID='surplus'})
          assert(xp.Progress('alchemy',1).complete)
          assert(xp.Progress('alchemy',2).complete and xp.Progress('alchemy',2).reusedOutputs==2)
          assert(not xp.Progress('alchemy',3).complete and xp.Progress('alchemy',3).reusedOutputs==0)
        ''')

    def configure_split_material_obligations(self):
        self.lua.execute('''
          local p=fixture();local a=p.executionSteps[1]
          a.expectedGain=0;a.goalSkill=nil;a.requiredOutputs={[10]=2};a.expectedCrafts=1;a[4]=1
          a.allocations={{consumerID='consumer',itemID=10,count=2}}
          local b=fixture().executionSteps[1];b.segmentID='consumer';b[3]=102;b.recipe.spell=102
          b.recipe.item=30;b.item=30;b.recipe.mats={{10,2}};b.expectedGain=0;b.goalSkill=nil
          b.requiredOutputs={[30]=2};b.expectedCrafts=1;b[4]=1;b.allocations={}
          local c=fixture().executionSteps[1];c.segmentID='second-producer';c.expectedGain=0;c.goalSkill=nil
          c.requiredOutputs={[10]=2};c.expectedCrafts=1;c[4]=1
          c.allocations={{consumerID='last-consumer',itemID=10,count=2}}
          local d=fixture().executionSteps[1];d.segmentID='last-consumer';d[3]=103;d.recipe.spell=103
          d.recipe.item=40;d.item=40;d.recipe.mats={{10,2}};d.expectedGain=0;d.goalSkill=nil
          d.requiredOutputs={[40]=2};d.allocations={}
          p.executionSteps={a,b,c,d};run=xp.StartNew('alchemy',p)
          xp.RecordAttempt('alchemy',101,'a');xp.RecordOutput({itemID=10,quantity=2,castGUID='a'})
        ''')

    def test_extra_consumer_cannot_spend_a_future_segments_quota_twice(self):
        self.configure_split_material_obligations()
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'c');xp.RecordOutput({itemID=10,quantity=2,castGUID='c'})
          xp.RecordAttempt('alchemy',102,'b1');xp.RecordOutput({itemID=30,quantity=2,castGUID='b1'})
          xp.RecordAttempt('alchemy',102,'b2');xp.RecordOutput({itemID=30,quantity=2,castGUID='b2'})
          local later=xp.Progress('alchemy',3)
          assert(later.actualOutputs==2 and later.guaranteedOutputs==2,
            'historical production facts must remain separate from available quota')
          assert(not later.materialDone and later.remainingOutputs==2 and later.divertedOutputs==2 and run.currentIndex==3)
          assert(later.divertedOutputs==2 and later.fulfilledOutputs==0)
          assert(xp.Progress('alchemy',1).complete,'intended consumption must not reopen the first producer')
        ''')

    def test_assigned_consumption_keeps_both_producer_obligations_complete(self):
        self.configure_split_material_obligations()
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'c');xp.RecordOutput({itemID=10,quantity=2,castGUID='c'})
          xp.RecordAttempt('alchemy',102,'b1');xp.RecordOutput({itemID=30,quantity=2,castGUID='b1'})
          xp.RecordAttempt('alchemy',103,'d1');xp.RecordOutput({itemID=40,quantity=2,castGUID='d1'})
          assert(xp.Progress('alchemy',1).complete and xp.Progress('alchemy',3).complete)
          assert(run.finished,'normally consumed allocations must remain fulfilled')
        ''')

    def test_borrowed_random_surplus_is_debited_when_the_wrong_consumer_spends_it(self):
        self.configure_split_material_obligations()
        self.lua.execute('''
          -- A late high-yield receipt supplies the future quota without another cast.
          xp.VerifyOutput('alchemy',1,10,4)
          assert(xp.Progress('alchemy',3).reusedOutputs==2)
          xp.RecordAttempt('alchemy',102,'b1');xp.RecordOutput({itemID=30,quantity=2,castGUID='b1'})
          xp.RecordAttempt('alchemy',102,'b2');xp.RecordOutput({itemID=30,quantity=2,castGUID='b2'})
          local later=xp.Progress('alchemy',3)
          assert(not later.complete and later.reusedOutputs==0 and later.remainingOutputs==2)
        ''')

    def test_replenishing_a_stolen_quota_restores_it_without_changing_actual_history(self):
        self.configure_split_material_obligations()
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'c');xp.RecordOutput({itemID=10,quantity=2,castGUID='c'})
          xp.RecordAttempt('alchemy',102,'b1');xp.RecordOutput({itemID=30,quantity=2,castGUID='b1'})
          xp.RecordAttempt('alchemy',102,'b2');xp.RecordOutput({itemID=30,quantity=2,castGUID='b2'})
          xp.RecordAttempt('alchemy',101,'replacement')
          local later=xp.Progress('alchemy',3)
          assert(later.complete and later.pendingOutputs==1 and later.actualOutputs==2 and later.guaranteedOutputs==4)
          xp.RecordOutput({itemID=10,quantity=3,castGUID='replacement'})
          later=xp.Progress('alchemy',3)
          assert(later.complete and later.pendingOutputs==0 and later.actualOutputs==5)
        ''')

    def test_manual_verification_resolves_pending_output_without_inventing_casts(self):
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'one');xp.VerifyOutput('alchemy',1,10,3)
          local p=xp.Progress('alchemy',1)
          assert(p.pendingOutputs==0 and p.actualOutputs==3 and p.casts==1)
        ''')

    def configure_topup(self, finite=None):
        self.lua.execute('''
          local producer={profession='alchemy',spell=102,item=20,count=1,mats={{30,2}},learn=1,yellow=1,green=1,grey=1,cooldown=false}
          local originalCapture=ns.ProfEconomy.Capture
          ns.ProfEconomy.Capture=function(slug,opts,tick)
            if opts and opts.snapshot then return originalCapture(slug,opts,tick)end
            return ns.ProfEconomy.Index({recipes={producer},professions=skills,known={['alchemy:102']=true},
              prices={[30]=5},offers={},auctionSupply={}})
          end
          for i=1,3 do xp.RecordAttempt('alchemy',101,'miss'..i)end
          function pumpAll()
            for i=1,500 do
              xp.Pump('alchemy')
              local result=xp.GetSupplement('alchemy')
              if result and not result.inFlight then return result end
            end
            error('supplement did not finish')
          end
        ''')
        if finite is not None:
            self.lua.execute(f'''
              local capture=ns.ProfEconomy.Capture
              ns.ProfEconomy.Capture=function(slug,opts,tick)
                local s=capture(slug,opts,tick)
                if not (opts and opts.snapshot)then s.auctionSupply[30]={{quantity={finite},complete=true}}end
                return s
              end
            ''')

    def test_real_recursive_topup_inserts_grey_producer_and_keeps_base_cost(self):
        self.configure_topup()
        self.lua.execute('''
          local state=xp.CalculateSupplement('alchemy');assert(state.inFlight)
          local result=pumpAll();assert(result.feasible and result.appended)
          assert(result.total==20 and result.mats[1].id==30 and result.mats[1].count==4)
          assert(run.plan.total==90 and #run.plan.executionSteps==2)
          assert(run.plan.executionSteps[1][3]==102 and run.plan.executionSteps[1].requiredOutputs[20]==2)
          assert(run.progressVersion>0 and run.attemptsDone==3)
        ''')

    def test_topup_cannot_exceed_shared_observed_auction_quantity(self):
        self.configure_topup(finite=3)
        self.lua.execute('''
          xp.CalculateSupplement('alchemy');local result=pumpAll()
          assert(not result.feasible and not result.appended)
          assert(#run.plan.executionSteps==1 and run.plan.total==90 and run.attemptsDone==3)
        ''')

    def test_repeated_topup_reserves_previous_supplement_materials(self):
        self.configure_topup()
        self.lua.execute('''
          xp.CalculateSupplement('alchemy');local first=pumpAll()
          assert(first.total==20 and first.appended)
          xp.RecordAttempt('alchemy',102,'powder1');xp.RecordOutput({itemID=20,quantity=1,castGUID='powder1'})
          xp.RecordAttempt('alchemy',102,'powder2');xp.RecordOutput({itemID=20,quantity=1,castGUID='powder2'})
          xp.RecordAttempt('alchemy',101,'still-no-skill');bag[20]=1
          assert(xp.Progress('alchemy').extraCrafts==1)
          xp.CalculateSupplement('alchemy');local second=pumpAll()
          assert(second.total==10 and second.appended,
            'second topup reused material already reserved by the first topup')
          assert(second.mats[1].id==30 and second.mats[1].count==2)
        ''')

    def test_cast_during_topup_invalidates_the_old_delta(self):
        self.configure_topup()
        self.lua.execute('''
          xp.CalculateSupplement('alchemy');xp.RecordAttempt('alchemy',101,'late-craft')
          local result=pumpAll();assert(result.status=='stale' and not result.appended)
          assert(#run.plan.executionSteps==1 and run.attemptsDone==4)
        ''')

    def test_history_keeps_real_counts_when_new_plan_starts(self):
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'old1');xp.RecordOutput({itemID=10,quantity=3,castGUID='old1'})
          local previous=run.planID;run=xp.StartNew('alchemy',fixture())
          local history=xp.GetHistory('alchemy');assert(#history==2 and history[1]==run)
          local totals=xp.GetRecipeTotals('alchemy',previous)
          assert(totals[1].casts==1 and totals[1].confirmedOutputs[10]==3)
          assert(xp.GetRecipeTotals('alchemy')[1].casts==0)
        ''')

    def test_topup_leaves_pending_base_auction_demand_reserved(self):
        self.configure_topup(finite=5)
        self.lua.execute('''
          local future=fixture().executionSteps[1];future.segmentID='future';future[3]=103;future.recipe.spell=103
          future.recipe.mats={{30,1}};future[4]=2;future.expectedCrafts=2
          run.plan.executionSteps[2]=future
          run.plan.mats[#run.plan.mats+1]={id=30,count=2,source='ah'}
          xp.CalculateSupplement('alchemy');local result=pumpAll()
          assert(not result.feasible and not result.appended)
        ''')

    def test_continuation_replays_actual_cast_order_after_a_topup_insertion(self):
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'original-consumer')
          local producer=fixture().executionSteps[1];producer.segmentID='topup-producer';producer[3]=102
          producer.recipe.spell=102;producer.item=20;producer.recipe.item=20;producer.recipe.mats={{30,1}}
          producer.requiredOutputs={[20]=2};producer.goalSkill=nil;producer.expectedGain=0
          table.insert(run.plan.executionSteps,1,producer)
          xp.RecordAttempt('alchemy',102,'new-producer');xp.RecordOutput({itemID=20,quantity=5,castGUID='new-producer'})
          xp.RecordAttempt('alchemy',101,'new-consumer');bag[20]=99
          assert(xp.GetContinuation('alchemy')[20]==4,
            'casts before production consumed a future topup output')
        ''')

    def test_repeated_recalculate_keeps_the_validated_carry_source(self):
        self.lua.execute('''
          local p=fixture();local consumer=fixture().executionSteps[1];consumer.segmentID='consumer'
          consumer[3]=102;consumer.recipe.spell=102;consumer.recipe.mats={{10,1}}
          p.executionSteps[2]=consumer;run=xp.StartNew('alchemy',p)
          xp.RecordAttempt('alchemy',101,'made');xp.RecordOutput({itemID=10,quantity=3,castGUID='made'});bag[10]=3
          local first,id=xp.PrepareRecalculate('alchemy');local second,again=xp.PrepareRecalculate('alchemy')
          assert(first[10]==3 and second[10]==3 and again==id)
          bag[10]=1;local third=xp.PrepareRecalculate('alchemy');assert(third[10]==1)
        ''')

    def test_cumulative_output_verification_does_not_restore_consumed_unknown_items(self):
        self.lua.execute('''
          local p=fixture();local consumer=fixture().executionSteps[1];consumer.segmentID='consumer'
          consumer[3]=102;consumer.recipe.spell=102;consumer.recipe.mats={{10,2}}
          p.executionSteps[2]=consumer;run=xp.StartNew('alchemy',p)
          xp.RecordAttempt('alchemy',101,'unconfirmed1')
          xp.RecordAttempt('alchemy',102,'consumed-before-verification')
          xp.RecordAttempt('alchemy',101,'unconfirmed2')
          xp.VerifyOutput('alchemy',1,10,6);bag[10]=99
          assert(xp.GetContinuation('alchemy')[10]==4,
            'cumulative manual total restored the two units already consumed')
        ''')


if __name__ == "__main__":
    unittest.main()
