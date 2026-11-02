"""Master history retention and crafted-result recovery on the native executor."""
import unittest
import test_prof_execution_fusion as execution


class HistoryRetentionTests(unittest.TestCase):
    setUp = execution.ExecutionFusionTests.setUp
    load = execution.ExecutionFusionTests.load

    def prepare(self):
        self.lua.execute('''
          c=DungeonsForeverDB.prof.track['Test-Realm'];serial=0
          function fresh(facts,opts)
            serial=serial+1;clock=1000+serial
            local plan=fixture();plan.planID='history:'..serial
            local r=assert(xp.StartNew('alchemy',plan,opts))
            if facts then assert(xp.RecordAttempt('alchemy',101,'history-cast:'..serial))end
            return r
          end
        ''')

    def test_empty_unreferenced_archive_is_removed(self):
        self.prepare()
        self.lua.execute('''
          local empty=run;local next=fresh(false)
          assert(not xp.Get('alchemy',empty.planID))
          assert(#xp.GetHistory('alchemy')==1 and xp.GetActive('alchemy')==next)
        ''')

    def test_keep_three_latest_archives_and_current_run_per_profession(self):
        self.prepare()
        self.lua.execute('''
          local other=fixture();other.planID='mining-history'
          local mining=assert(xp.Bind('mining',other))
          local all={};for i=1,8 do all[i]=fresh(true)end
          local history=xp.GetHistory('alchemy');assert(#history==4)
          for i=1,4 do assert(not xp.Get('alchemy',all[i].planID))end
          for i=5,8 do
            local r=xp.Get('alchemy',all[i].planID)
            assert(r and r.attemptsDone==1 and xp.GetRecipeTotals('alchemy',r.planID)[1].casts==1)
          end
          assert(xp.GetActive('alchemy')==all[8] and xp.GetActive('mining')==mining)
        ''')

    def test_referenced_old_archive_survives_limit_then_is_released(self):
        self.prepare()
        self.lua.execute('''
          local source=fresh(true)
          c.preparing.enchanting={sourcePlanID=source.planID}
          for i=1,7 do fresh(true)end
          assert(xp.Get('alchemy',source.planID) and #xp.GetHistory('alchemy')==5)
          c.preparing.enchanting=nil;fresh(true)
          assert(not xp.Get('alchemy',source.planID) and #xp.GetHistory('alchemy')==4)
        ''')

    def test_empty_continuation_keeps_live_bag_then_releases_on_new_execution(self):
        self.prepare()
        self.lua.execute('''
          local empty=fresh(false);xp.End('alchemy','cancel');bag[20]=17
          assert(xp.Get('alchemy',empty.planID) and xp.GetContinuation('alchemy')[20]==17)
          bag[20]=9;assert(xp.GetContinuation('alchemy')[20]==9)
          fresh(false)
          assert(not c.continuation.alchemy and not xp.Get('alchemy',empty.planID))
        ''')

    def test_inherited_source_is_kept_until_empty_child_is_no_longer_needed(self):
        self.prepare()
        self.lua.execute('''
          local source=fresh(true)
          local child=fresh(false,{executionSourcePlanID=source.planID})
          assert(child.inheritedFrom==source.planID and xp.Get('alchemy',source.planID))
          xp.End('alchemy');assert(xp.Get('alchemy',child.planID))
          fresh(true);assert(not xp.Get('alchemy',child.planID))
          for i=1,4 do fresh(true)end
          assert(not xp.Get('alchemy',source.planID))
        ''')

    def test_manual_quest_and_output_facts_are_not_empty(self):
        self.prepare()
        self.lua.execute('''
          local quest=fresh(false);quest.progress[quest.plan.executionSteps[1].segmentID]={casts=0,questCompleted=true,outputs={}}
          local output=fresh(false)
          assert(xp.VerifyOutput('alchemy',1,10,2))
          fresh(false)
          assert(xp.Get('alchemy',quest.planID) and xp.Get('alchemy',output.planID))
          assert(xp.Progress('alchemy',1,nil,output.planID).actualOutputs==2)
        ''')

    def test_pruned_cast_cannot_be_reassigned_to_new_execution(self):
        self.prepare()
        self.lua.execute('''
          fresh(true);for i=1,5 do fresh(true)end
          local current=fresh(false)
          assert(not xp.RecordCraftedResult({itemID=10,quantity=3,castGUID='history-cast:1'}))
          assert(current.attemptsDone==0)
        ''')


class CraftedReceiptTests(unittest.TestCase):
    setUp = execution.ExecutionFusionTests.setUp
    load = execution.ExecutionFusionTests.load

    def test_result_event_without_spell_counts_one_variable_yield_craft(self):
        self.lua.execute('''
          xp.eventFrame.OnEvent(xp.eventFrame,'TRADE_SKILL_ITEM_CRAFTED_RESULT',{itemID=10,quantity=3,eventID=1})
          local p=xp.Progress('alchemy',1)
          assert(p.casts==1 and p.actualOutputs==3 and p.guaranteedOutputs==3 and p.pendingOutputs==0)
          assert(run.materialLedger.consumed[20]==1)
        ''')

    def test_positional_event_and_large_fixed_output_do_not_use_units_as_casts(self):
        self.lua.execute('''
          local seg=run.plan.executionSteps[1];seg.outputMin=200;seg.outputMax=200
          xp.eventFrame.OnEvent(xp.eventFrame,'TRADE_SKILL_ITEM_CRAFTED_RESULT',10,200)
          assert(run.attemptsDone==1 and xp.Progress('alchemy',1).actualOutputs==200)
          assert(run.materialLedger.consumed[20]==1)
        ''')

    def test_fixed_yield_batch_settles_all_pending_casts_and_late_spell_events(self):
        self.lua.execute('''
          local seg=run.plan.executionSteps[1];seg.outputMin=2;seg.outputMax=2
          assert(xp.RecordCraftedResult({itemID=10,quantity=6,eventID='batch'}))
          local p=xp.Progress('alchemy',1)
          assert(p.casts==3 and p.actualOutputs==6 and p.guaranteedOutputs==6 and p.pendingOutputs==0)
          assert(run.materialLedger.consumed[20]==3)
          for i=1,3 do assert(not xp.RecordAttempt('alchemy',101,'late:'..i))end
          assert(run.attemptsDone==3)
          assert(xp.RecordAttempt('alchemy',101,'next-real'))
          assert(run.attemptsDone==4)
        ''')

    def test_guid_result_then_late_spell_and_duplicate_receipts_count_once(self):
        self.lua.execute('''
          local event={itemID=10,quantity=3,castGUID='one',eventID=1}
          assert(xp.RecordCraftedResult(event))
          assert(not xp.RecordAttempt('alchemy',101,'one'))
          assert(xp.RecordCraftedResult(event))
          event.eventID=2;assert(xp.RecordCraftedResult(event))
          assert(xp.RecordOutput({itemID=10,quantity=3,castGUID='one'},'chat'))
          assert(run.attemptsDone==1 and xp.Progress('alchemy',1).actualOutputs==3)
          assert(xp.RecordAttempt('alchemy',101,'next'))
          assert(run.attemptsDone==2)
        ''')

    def test_normal_spell_then_result_does_not_infer_an_extra_cast(self):
        self.lua.execute('''
          assert(xp.RecordAttempt('alchemy',101,'one'))
          assert(xp.RecordCraftedResult({itemID=10,quantity=3,castGUID='one'}))
          assert(run.attemptsDone==1 and xp.Progress('alchemy',1).pendingOutputs==0)
          assert(not xp.RecordCraftedResult({itemID=11,quantity=2,castGUID='one'}))
        ''')

    def test_distinct_guid_does_not_consume_another_live_casts_pending_output(self):
        self.lua.execute('''
          assert(xp.RecordAttempt('alchemy',101,'first'))
          assert(xp.RecordCraftedResult({itemID=10,quantity=3,castGUID='second'}))
          local p=xp.Progress('alchemy',1)
          assert(p.casts==2 and p.actualOutputs==3 and p.guaranteedOutputs==5 and p.pendingOutputs==1)
          assert(xp.RecordCraftedResult({itemID=10,quantity=2,castGUID='first'}))
          assert(not xp.RecordAttempt('alchemy',101,'second'))
          p=xp.Progress('alchemy',1)
          assert(p.casts==2 and p.actualOutputs==5 and p.guaranteedOutputs==5 and p.pendingOutputs==0)
          assert(run.materialLedger.consumed[20]==2)
        ''')

    def test_anonymous_short_duplicate_and_late_spell_are_deduplicated(self):
        self.lua.execute('''
          assert(xp.RecordCraftedResult(10,3));assert(xp.RecordCraftedResult(10,3))
          assert(not xp.RecordAttempt('alchemy',101,'arrived-late'))
          assert(xp.RecordCraftedResult({itemID=10,quantity=3,castGUID='arrived-late'}))
          assert(run.attemptsDone==1 and xp.Progress('alchemy',1).actualOutputs==3)
          clock=1004;assert(xp.RecordCraftedResult(10,2))
          assert(run.attemptsDone==2 and xp.Progress('alchemy',1).actualOutputs==5)
        ''')

    def test_distinct_receipt_ids_are_not_suppressed_by_short_time_guard(self):
        self.lua.execute('''
          assert(xp.RecordCraftedResult({itemID=10,quantity=2,eventID=1}))
          assert(xp.RecordCraftedResult({itemID=10,quantity=3,eventID=2}))
          assert(not xp.RecordAttempt('alchemy',101,'late-b'))
          assert(not xp.RecordAttempt('alchemy',101,'late-a'))
          assert(run.attemptsDone==2 and xp.Progress('alchemy',1).actualOutputs==5)
        ''')

    def test_ambiguous_variable_or_fractional_batch_does_not_invent_counts(self):
        self.lua.execute('''
          local ok,why=xp.RecordCraftedResult(10,6)
          assert(not ok and why=='ambiguous_quantity' and run.attemptsDone==0)
          run.plan.executionSteps[1].outputMax=2
          assert(not xp.RecordCraftedResult(10,7))
          assert(not xp.RecordCraftedResult(10,12))
          assert(run.attemptsDone==0 and xp.Progress('alchemy',1).actualOutputs==0)
        ''')

    def test_guid_identifies_one_cast_even_when_static_yield_is_incomplete(self):
        self.lua.execute('''
          assert(xp.RecordCraftedResult({itemID=10,quantity=9,castGUID='one'}))
          assert(run.attemptsDone==1 and xp.Progress('alchemy',1).actualOutputs==9)
        ''')

    def test_ambiguous_active_professions_require_explicit_owner(self):
        self.lua.execute('''
          local other=fixture();other.planID='mining';other.executionSteps[1].profession='mining'
          local mining=assert(xp.Bind('mining',other))
          local ok,why=xp.RecordCraftedResult(10,2)
          assert(not ok and why=='ambiguous_recipe' and run.attemptsDone==0 and mining.attemptsDone==0)
          assert(xp.RecordCraftedResult({itemID=10,quantity=2,slug='alchemy'}))
          assert(run.attemptsDone==1 and mining.attemptsDone==0)
        ''')

    def test_same_product_from_different_recipes_requires_spell_identity(self):
        self.lua.execute('''
          local plan=fixture();plan.planID='two-recipes'
          local second=fixture().executionSteps[1];second[3]=102;second.segmentID='other'
          plan.executionSteps[2]=second;run=assert(xp.StartNew('alchemy',plan))
          local ok,why=xp.RecordCraftedResult(10,2)
          assert(not ok and why=='ambiguous_recipe')
          assert(xp.RecordCraftedResult({itemID=10,quantity=2,recipeID=101}))
          assert(xp.Progress('alchemy',1).casts==1 and xp.Progress('alchemy',2).casts==0)
        ''')

    def test_manual_steps_invalid_receipts_and_chat_do_not_infer_casts(self):
        self.lua.execute('''
          assert(not xp.RecordCreatedMessage('You create: |Hitem:10|h[X]|h.',1))
          for _,kind in ipairs({'specialization_quest','essence_conversion'})do
            run.plan.executionSteps[1].kind=kind
            assert(not xp.RecordCraftedResult(10,2))
          end
          run.plan.executionSteps[1].kind=nil;run.plan.executionSteps[1].navigationOnly=true
          assert(not xp.RecordCraftedResult(10,2))
          assert(not xp.RecordCraftedResult(10,0));assert(not xp.RecordCraftedResult('bad',2))
          assert(run.attemptsDone==0)
        ''')

    def test_reload_uses_pending_totals_without_an_additional_cast(self):
        self.lua.execute("assert(xp.RecordAttempt('alchemy',101,'before-reload'))")
        self.load('Core/ProfExecution.lua')
        self.lua.execute('''
          initialize();xp=ns.ProfExecution
          assert(xp.RecordCraftedResult({itemID=10,quantity=3,castGUID='before-reload'}))
          assert(xp.RecordCraftedResult({itemID=10,quantity=3,castGUID='before-reload'}))
          assert(not xp.RecordAttempt('alchemy',101,'before-reload'))
          assert(run.attemptsDone==1 and xp.Progress('alchemy',1).actualOutputs==3)
          local c=DungeonsForeverDB.prof.track['Test-Realm']
          assert(not c.pendCast and not c.seenCasts and not c.seenReceipts)
        ''')

    def test_anonymous_reloaded_pending_match_deduplicates_repeated_result(self):
        self.lua.execute("assert(xp.RecordAttempt('alchemy',101,'before-reload'))")
        self.load('Core/ProfExecution.lua')
        self.lua.execute('''
          initialize();xp=ns.ProfExecution
          assert(xp.RecordCraftedResult(10,3));assert(xp.RecordCraftedResult(10,3))
          assert(run.attemptsDone==1 and xp.Progress('alchemy',1).actualOutputs==3)
        ''')

    def test_late_result_for_replaced_execution_keeps_original_owner(self):
        self.lua.execute('''
          local old=run;assert(xp.RecordAttempt('alchemy',101,'old'))
          local plan=fixture();plan.planID='new';run=assert(xp.StartNew('alchemy',plan))
          assert(xp.RecordCraftedResult({itemID=10,quantity=3,castGUID='old'}))
          assert(old.attemptsDone==1 and run.attemptsDone==0)
          assert(xp.Progress('alchemy',1,nil,old.planID).actualOutputs==3)
        ''')


if __name__=='__main__':unittest.main()
