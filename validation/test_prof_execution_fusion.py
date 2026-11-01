"""Dev execution ledger: frozen routes, current bag continuation, cumulative production and master-style session-only matching."""
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
          bag[10]=6;skills.alchemy.cur=3;xp.Sync('alchemy');local p=t.Progress('alchemy',1)
          assert(p.complete and p.casts==2 and p.outputs==6 and run.currentIndex==2)
        """)

    def test_bag_materials_are_usable_without_production_receipts(self):
        self.lua.execute("xp.RecordAttempt('alchemy',101,'a');bag[10]=200;bag[20]=900;bag[99]=50;local stock=t.ContinueInventory('alchemy');assert(stock[10]==200 and stock[20]==900 and stock[99]==nil);assert(xp.Progress('alchemy',1).actualOutputs==0)")

    def test_continuation_excludes_bank_and_reagent_bank_counts(self):
        self.lua.execute("""
          C_Item.GetItemCount=function(id,bank,uses,reagentBank)
            assert(bank==false and uses==false and reagentBank==false)
            return id==20 and 2 or 0
          end
          local inventory=xp.GetContinuation('alchemy')
          assert(inventory[20]==2 and inventory[10]==nil)
        """)

    def test_candidate_publications_do_not_replace_frozen_plan(self):
        self.lua.execute("""
          xp.RecordAttempt('alchemy',101,'a');local original=run.plan
          local candidate=fixture();candidate.revision=2;candidate.executionSteps[1][4]=99
          assert(t.Bind('alchemy',candidate)==run and run.plan==original and run.newPlanAvailable)
          assert(t.Progress('alchemy',1).casts==1 and original.executionSteps[1][4]==3)
          assert(run.plan==original and original.executionSteps[1][4]==3)
        """)

    def test_continuation_reads_current_bags_without_subtracting_consumption_twice(self):
        self.lua.execute("""
          local p=fixture();local b={1,3,102,1,segmentID='consumer',profession='alchemy',recipe=recipes[102],item=11,
            goalSkill=3,expectedGain=2,expectedCrafts=1,attemptLimit=1,outputMin=2,requiredOutputs={}}
          p.executionSteps[2]=b;run=xp.StartNew('alchemy',p)
          xp.RecordAttempt('alchemy',101,'a');xp.RecordOutput({itemID=10,quantity=3,castGUID='a'})
          xp.RecordAttempt('alchemy',101,'b');xp.RecordOutput({itemID=10,quantity=3,castGUID='b'})
          xp.RecordAttempt('alchemy',102,'consume');bag[10]=3;bag[20]=900
          assert(xp.GetContinuation('alchemy')[10]==3 and xp.GetContinuation('alchemy')[20]==900)
          bag[10]=100;assert(xp.GetContinuation('alchemy')[10]==100);bag[10]=0;assert(xp.GetContinuation('alchemy')[10]==nil)
        """)

    def test_manual_verification_preserves_actual_cast_count(self):
        self.lua.execute("xp.RecordAttempt('alchemy',101,'a');assert(t.VerifyOutput('alchemy',1,10,3));local p=t.Progress('alchemy',1);assert(p.outputs==3 and p.casts==1 and p.pendingOutputs==0)")

    def test_unmatched_receipt_is_not_saved_and_casts_deduplicate_in_memory(self):
        self.lua.execute("""
          assert(not xp.RecordOutput({itemID=10,quantity=3,castGUID='a'}))
          xp.RecordAttempt('alchemy',101,'a')
          assert(t.Progress('alchemy',1).outputs==0,'unmatched output was queued')
          assert(xp.RecordOutput({itemID=10,quantity=3,castGUID='a'}))
          assert(not xp.RecordAttempt('alchemy',101,'a'))
          assert(t.Progress('alchemy',1).casts==1 and t.Progress('alchemy',1).outputs==3)
        """)

    def test_recalculate_uses_fresh_bag_stock_on_each_request(self):
        self.lua.execute("""
          local p=fixture();p.executionSteps[2]={3,4,102,1,segmentID='consumer',profession='alchemy',recipe=recipes[102],item=11,
             goalSkill=4,expectedGain=1,expectedCrafts=1,attemptLimit=1,requiredOutputs={}}
          run=xp.StartNew('alchemy',p);xp.RecordAttempt('alchemy',101,'a');xp.RecordOutput({itemID=10,quantity=3,castGUID='a'})
          bag[10]=20;local inventory,id=xp.PrepareRecalculate('alchemy');assert(inventory[10]==20 and id==run.planID and not xp.GetRun('alchemy'))
          bag[10]=7;local again,source=xp.PrepareRecalculate('alchemy');assert(again[10]==7 and source==id)
        """)

    def test_reload_keeps_same_plan_and_progress(self):
        self.lua.execute("xp.RecordAttempt('alchemy',101,'a');savedID=run.planID")
        self.load("Core/ProfExecution.lua")
        self.lua.execute("initialize();xp=ns.ProfExecution;t=ns.ProfTrack;assert(t.GetRun('alchemy').planID==savedID and t.Progress('alchemy',1).casts==1)")

    def test_inventory_read_failure_does_not_replace_or_archive_the_active_plan(self):
        self.lua.execute("""
          C_Item.GetItemCount=function()error('inventory unavailable')end;GetItemCount=nil
          local inventory,reason=xp.GetContinuation('alchemy')
          assert(inventory==nil and reason=='inventoryUnknown')
          local seed,id,errorCode=xp.PrepareRecalculate('alchemy')
          assert(seed==nil and id==nil and errorCode=='inventoryUnknown')
          assert(xp.GetRun('alchemy')==run and run.status=='active')
          local p=xp.Progress('alchemy',1);assert(p.inventoryUnknown and not p.complete)
        """)

    def test_bag_updates_change_material_progress_without_inventing_crafts(self):
        self.lua.execute("""
          skills.alchemy.cur=3;xp.Sync('alchemy')
          assert(not xp.Progress('alchemy',1).materialDone)
          assert(xp.eventFrame.events.BAG_UPDATE_DELAYED)
          bag[10]=6
          xp.eventFrame.OnEvent(xp.eventFrame,'BAG_UPDATE_DELAYED')
          local p=xp.Progress('alchemy',1)
          assert(p.complete and p.casts==0 and p.actualOutputs==0 and run.currentIndex==2)
          bag[10]=1
          xp.eventFrame.OnEvent(xp.eventFrame,'BAG_UPDATE_DELAYED')
          p=xp.Progress('alchemy',1)
          assert(not p.materialDone and p.remainingOutputs==5 and run.currentIndex==1)
        """)

    def test_same_bag_stack_cannot_fund_two_material_obligations(self):
        self.lua.execute("""
          local p=fixture();local later=fixture().executionSteps[1];later.segmentID='later'
          p.executionSteps[1].requiredOutputs={[10]=2};later.requiredOutputs={[10]=2}
          p.executionSteps[2]=later;run=xp.StartNew('alchemy',p);bag[10]=3
          assert(xp.Progress('alchemy',1).remainingOutputs==0)
          assert(xp.Progress('alchemy',2).remainingOutputs==1)
          assert(xp.Progress('alchemy',1).casts==0 and xp.Progress('alchemy',2).casts==0)
        """)

    def test_completed_consumer_uses_up_its_quota_without_recreating_material_stock(self):
        self.lua.execute("""
          local p=fixture();p.executionSteps[2]={1,3,102,3,segmentID='consumer',profession='alchemy',
            recipe=recipes[102],item=11,goalSkill=3,expectedGain=2,expectedCrafts=3,attemptLimit=3,
            outputMin=2,requiredOutputs={}}
          run=xp.StartNew('alchemy',p)
          for i=1,3 do xp.RecordAttempt('alchemy',102,'consumer:'..i)end
          local progress=xp.Progress('alchemy',1)
          assert(progress.materialDone and progress.actualOutputs==0 and progress.casts==0)
          assert(xp.GetContinuation('alchemy')[10]==nil)
        """)

    def test_completed_quest_releases_the_unused_material_chain_without_craft_history(self):
        self.lua.execute("""
          local p=fixture();local a=p.executionSteps[1]
          a.expectedGain=0;a.requiredOutputs={[10]=2};a.expectedCrafts=1;a[4]=1
          a.allocations={{consumerID='producer',itemID=10,count=2}}
          local producer={1,1,102,1,segmentID='producer',profession='alchemy',recipe=recipes[102],item=11,
            expectedGain=0,expectedCrafts=1,attemptLimit=1,outputMin=2,requiredOutputs={[11]=2},
            allocations={{consumerID='quest',itemID=11,count=2}}}
          local quest={1,1,0,0,segmentID='quest',profession='alchemy',kind='specialization_quest',
            quest={abilityID=123,inputs={{11,2}}},inputs={{11,2}},expectedGain=0,requiredOutputs={}}
          p.executionSteps={a,producer,quest};run=xp.StartNew('alchemy',p)
          assert(not xp.Progress('alchemy',1).materialDone)
          ns.ProfEconomy.SpecializationKnown=function(id)return id==123 end
          xp.Sync('alchemy')
          assert(xp.Progress('alchemy',1).materialDone and xp.Progress('alchemy',2).materialDone)
          assert(xp.Progress('alchemy',3).complete and run.attemptsDone==0)
          for _,record in pairs(run.progress)do assert(record.history==nil)end
        """)

    def test_only_execution_observer_is_registered(self):
        self.lua.execute("assert(not t.frame and xp.eventFrame);xp.eventFrame.OnEvent(xp.eventFrame,'UNIT_SPELLCAST_SUCCEEDED','player','hidden',101);assert(t.Progress('alchemy',1).casts==1)")

    def test_both_interfaces_share_facts_deduplication_and_notifications(self):
        self.lua.execute("""
          local native,legacy=0,0
          xp.OnChanged(function(_,r)assert(r==run);native=native+1 end)
          t.OnChanged(function(_,r)assert(r==run);legacy=legacy+1 end)
          assert(t.GetRun('alchemy')==run and t.OnChanged==xp.OnChanged)
          t.RecordAttempt('alchemy',101,'shared')
          xp.eventFrame.OnEvent(xp.eventFrame,'UNIT_SPELLCAST_SUCCEEDED','player','shared',101)
          t.RecordOutput('alchemy',10,3,'shared')
          xp.RecordOutput({itemID=10,quantity=3,castGUID='shared'})
          assert(xp.Progress('alchemy',1).casts==1 and xp.Progress('alchemy',1).actualOutputs==3)
          assert(native==2 and legacy==2 and #frames==1)
          t.Archive('alchemy','cancel')
          assert(native==3 and legacy==3 and not xp.GetRun('alchemy'))
          assert(xp.Get('alchemy',run.planID)==run and not t.Get('mining',run.planID))
          assert(not xp.GetSummary('mining',run.planID))
        """)

    def test_progress_and_history_reads_do_not_persist_legacy_views(self):
        self.lua.execute("""
          xp.RecordAttempt('alchemy',101,'a');xp.RecordOutput({itemID=10,quantity=3,castGUID='a'})
          for i=1,3 do
            t.GetRun('alchemy');t.History('alchemy');t.ProgressAll('alchemy');t.Summary('alchemy')
            xp.GetProgressAll('alchemy');xp.GetSummary('alchemy')
          end
          assert(run.steps==nil and run.outputs==nil and run.casts==nil and run.target==nil)
          assert(run.plan.executionSteps[1][3]==101 and run.attemptsDone==1)
          xp.End('alchemy','completed')
          local summary=xp.GetSummary('alchemy')
          assert(summary.finished and summary.startSkill==1 and summary.target==3 and summary.casts==1)
          assert(xp.GetRecipeTotals('alchemy',summary.planID)[1].confirmedOutputs[10]==3)
        """)

    def reload_execution(self):
        # SavedVariables rebuilds plain tables; never rely on runtime aliases.
        self.lua.execute("DungeonsForeverDB=ns.ProfEconomy.Copy(DungeonsForeverDB)")
        self.load("Core/ProfExecution.lua")
        self.lua.execute("initialize();xp=ns.ProfExecution;t=ns.ProfTrack;run=xp.GetRun('alchemy')")

    def test_repeated_casts_persist_only_totals_without_matching_payloads(self):
        self.lua.execute("""
          for i=1,120 do
            clock=1000+i
            assert(xp.RecordAttempt('alchemy',101,'cast:'..i))
            assert(xp.RecordOutput({itemID=10,quantity=3,castGUID='cast:'..i,eventID=i}))
          end
          local record=run.progress[run.plan.executionSteps[1].segmentID]
          assert(record.attempts==nil and record.history==nil and record.outputs[10].actual==360)
          clock=clock+16;xp.RefreshObservation()
          assert(record.attempts==nil and record.history==nil and record.outputs[10].actual==360)
          local p=xp.Progress('alchemy',1)
          assert(p.casts==120 and p.actualOutputs==360 and p.pendingOutputs==0)
          assert(run.materialLedger.consumed[20]==120)
          local c=DungeonsForeverDB.prof.track['Test-Realm']
          assert(not c.seen and not c.order and not c.seenCasts and not c.castOrder)
          assert(not c.seenReceipts and not c.receiptOrder and not c.devExecutionMigration)
          assert(not c.receiptWindowVersion and not c.receiptUntil and not c.recentRunIDs and not c.nextAttempt)
          assert(not DungeonsForeverDB.prof.vendorPrices and not DungeonsForeverDB.prof.profVendorOffers)
        """)
        self.reload_execution()
        self.lua.execute("local p=xp.Progress('alchemy',1);assert(p.casts==120 and p.actualOutputs==360);assert(run.materialLedger.consumed[20]==120)")

    def test_reload_keeps_totals_and_uses_master_item_fallback(self):
        self.lua.execute("""
          xp.RecordAttempt('alchemy',101,'a')
          xp.RecordOutput({itemID=10,quantity=3,castGUID='a',eventID=21})
          clock=1004;xp.RecordAttempt('alchemy',101,'b')
        """)
        self.reload_execution()
        self.lua.execute("""
          clock=2000
          assert(xp.RecordOutput({itemID=10,quantity=2,castGUID='b',eventID=22}))
          local p=xp.Progress('alchemy',1)
          assert(p.casts==2 and p.actualOutputs==5 and p.pendingOutputs==0)
          local ok,reason=xp.RecordOutput({itemID=10,quantity=2,castGUID='b',eventID=22})
          assert(ok and reason=='duplicate','same-session receipt ID did not deduplicate')
          assert(xp.RecordAttempt('alchemy',101,'a'),'reload incorrectly restored old GUID deduplication')
          assert(xp.Progress('alchemy',1).casts==3 and xp.Progress('alchemy',1).actualOutputs==5)
        """)
        self.reload_execution()
        self.lua.execute("assert(xp.Progress('alchemy',1).actualOutputs==5)")


    def test_session_matching_has_no_fifteen_second_expiry(self):
        self.lua.execute("""
          assert(xp.RecordAttempt('alchemy',101,'slow'))
          clock=clock+120;xp.RefreshObservation()
          assert(xp.RecordOutput({itemID=10,quantity=3,castGUID='slow'},'chat'))
          assert(xp.RecordOutput({itemID=10,quantity=2,castGUID='slow'},'structured'))
          local p=xp.Progress('alchemy',1)
          assert(p.actualOutputs==2 and p.guaranteedOutputs==2 and p.pendingOutputs==0)
        """)

    def test_pending_cast_cache_keeps_only_the_latest_thirty_two_guids(self):
        self.lua.execute("""
          local p=fixture();p.executionSteps[2]=fixture().executionSteps[1]
          p.executionSteps[2].segmentID='second';run=xp.StartNew('alchemy',p)
          assert(xp.RecordAttempt('alchemy',101,'oldest',1))
          for i=1,31 do assert(xp.RecordAttempt('alchemy',101,'new:'..i,2))end
          assert(xp.RecordOutput({itemID=10,quantity=3,castGUID='oldest'},'chat'))
          assert(xp.Progress('alchemy',1).actualOutputs==3)
          assert(xp.RecordAttempt('alchemy',101,'overflow',2))
          -- The evicted GUID no longer identifies the first step. Like master,
          -- item fallback selects the last recorded matching step instead.
          assert(xp.RecordOutput({itemID=10,quantity=2,castGUID='oldest'},'structured'))
          assert(xp.Progress('alchemy',1).actualOutputs==3)
          assert(xp.Progress('alchemy',2).actualOutputs==2)
        """)

    def test_cast_guid_deduplication_is_bounded_to_five_hundred_twelve(self):
        self.lua.execute("""
          assert(xp.RecordAttempt('alchemy',101,'first'))
          for i=1,511 do assert(xp.RecordAttempt('alchemy',101,'cast:'..i))end
          local ok,why=xp.RecordAttempt('alchemy',101,'first')
          assert(not ok and why=='duplicate')
          assert(xp.RecordAttempt('alchemy',101,'overflow'))
          assert(xp.RecordAttempt('alchemy',101,'first'),'old GUID did not leave the bounded memory cache')
          assert(xp.Progress('alchemy',1).casts==514)
          local record=run.progress[run.plan.executionSteps[1].segmentID]
          assert(record.attempts==nil and record.outputs[10].pending==514)
        """)

    def test_reload_discards_exact_cast_mapping_and_falls_back_by_item(self):
        self.lua.execute("""
          local p=fixture();p.executionSteps[2]=fixture().executionSteps[1]
          p.executionSteps[2].segmentID='second';run=xp.StartNew('alchemy',p)
          assert(xp.RecordAttempt('alchemy',101,'first-step',1))
          assert(xp.RecordAttempt('alchemy',101,'second-step',2))
        """)
        self.reload_execution()
        self.lua.execute("""
          assert(xp.RecordOutput({itemID=10,quantity=3,castGUID='first-step'}))
          assert(xp.Progress('alchemy',1).actualOutputs==0)
          assert(xp.Progress('alchemy',2).actualOutputs==3)
          assert(xp.Progress('alchemy',1).casts==1 and xp.Progress('alchemy',2).casts==1)
        """)

    def test_receipts_without_guid_use_last_item_then_other_pending_item(self):
        self.lua.execute("""
          local p=fixture();p.executionSteps[2]=fixture().executionSteps[1]
          p.executionSteps[2].segmentID='second';run=xp.StartNew('alchemy',p)
          xp.RecordAttempt('alchemy',101,'first',1)
          xp.RecordAttempt('alchemy',101,'second',2)
          assert(xp.RecordOutput({itemID=10,quantity=3,eventID=1},'chat'))
          assert(xp.Progress('alchemy',2).actualOutputs==3 and xp.Progress('alchemy',1).actualOutputs==0)
          assert(xp.RecordOutput({itemID=10,quantity=2,eventID=2},'chat'))
          assert(xp.Progress('alchemy',1).actualOutputs==2 and xp.Progress('alchemy',2).actualOutputs==3)
        """)

    def test_explicit_profession_receipt_does_not_use_another_professions_last_cast(self):
        self.lua.execute("""
          local p=fixture();p.planID='mining';p.executionSteps[1].profession='mining'
          local miner=assert(xp.StartNew('mining',p))
          xp.RecordAttempt('alchemy',101,'alchemy-cast')
          xp.RecordAttempt('mining',101,'mining-cast')
          assert(t.RecordOutput('alchemy',10,3))
          assert(xp.Progress('alchemy',1).actualOutputs==3 and xp.Progress('mining',1).actualOutputs==0)
          assert(t.RecordOutput('mining',10,2))
          assert(xp.Progress('mining',1).actualOutputs==2)
        """)

    def test_manual_total_override_preserves_later_outputs(self):
        self.lua.execute("""
          for i=1,2 do
            xp.RecordAttempt('alchemy',101,'a'..i)
            xp.RecordOutput({itemID=10,quantity=3,castGUID='a'..i})
          end
          assert(xp.VerifyOutput('alchemy',1,10,5))
          xp.RecordAttempt('alchemy',101,'later');xp.RecordOutput({itemID=10,quantity=3,castGUID='later'})
          clock=1016;xp.RefreshObservation()
          local record=run.progress[run.plan.executionSteps[1].segmentID]
          assert(record.history==nil and record.manualOutputs==nil and record.outputs[10].actual==8)
          assert(xp.Progress('alchemy',1).actualOutputs==8 and xp.Progress('alchemy',1).casts==3)
        """)
        self.reload_execution()
        self.lua.execute("assert(xp.Progress('alchemy',1).actualOutputs==8);assert(xp.VerifyOutput('alchemy',1,10,9));assert(xp.Progress('alchemy',1).actualOutputs==9)")

    def test_manual_total_covers_cached_casts_within_the_same_session(self):
        self.lua.execute("""
          xp.RecordAttempt('alchemy',101,'covered')
          assert(xp.VerifyOutput('alchemy',1,10,7))
          xp.RecordAttempt('alchemy',101,'new')
        """)
        self.lua.execute("""
          assert(xp.RecordOutput({itemID=10,quantity=3,castGUID='new'}))
          assert(xp.RecordOutput({itemID=10,quantity=9,castGUID='covered'}))
          local p=xp.Progress('alchemy',1)
          assert(p.casts==2 and p.actualOutputs==10 and p.pendingOutputs==0)
        """)

    def test_structured_receipt_corrects_chat_total_by_delta(self):
        self.lua.execute("""
          xp.RecordAttempt('alchemy',101,'a')
          xp.RecordOutput({itemID=10,quantity=3,castGUID='a'},'chat')
          xp.RecordOutput({itemID=10,quantity=2,castGUID='a'},'structured')
          local p=xp.Progress('alchemy',1)
          assert(p.actualOutputs==2 and p.guaranteedOutputs==2 and p.pendingOutputs==0 and p.outputConflict)
          clock=1016;xp.RefreshObservation()
          assert(run.progress[run.plan.executionSteps[1].segmentID].history==nil)
        """)
        self.reload_execution()
        self.lua.execute("assert(xp.Progress('alchemy',1).actualOutputs==2)")

    def test_consumption_order_does_not_override_observed_bag_stock(self):
        self.lua.execute("""
          local p=fixture();p.executionSteps[2]={1,3,102,1,segmentID='consumer',profession='alchemy',
            recipe=recipes[102],item=11,goalSkill=3,expectedGain=2,expectedCrafts=1,attemptLimit=1,
            outputMin=2,requiredOutputs={}}
          run=xp.StartNew('alchemy',p)
          xp.RecordAttempt('alchemy',102,'before-producer')
          xp.RecordAttempt('alchemy',101,'unconfirmed')
          xp.RecordAttempt('alchemy',102,'consume-unconfirmed')
          xp.VerifyOutput('alchemy',1,10,3)
          xp.RecordAttempt('alchemy',101,'confirmed');xp.RecordOutput({itemID=10,quantity=3,castGUID='confirmed'})
          bag[10]=99
          before=xp.Progress('alchemy',1);carry=xp.GetContinuation('alchemy')[10]
          assert(carry==99,'continuation must use the observed bag quantity')
          clock=1016;xp.RefreshObservation()
          local after=xp.Progress('alchemy',1)
          for _,k in ipairs({'casts','actualOutputs','pendingOutputs','remainingOutputs','materialDone','extraCrafts'}) do
            assert(after[k]==before[k],k)
          end
          assert(xp.GetContinuation('alchemy')[10]==carry)
        """)
        self.reload_execution()
        self.lua.execute("assert(xp.GetContinuation('alchemy')[10]==carry);assert(xp.Progress('alchemy',1).actualOutputs==before.actualOutputs)")

    def test_variable_and_missing_receipts_keep_totals_without_time_expiry(self):
        self.lua.execute("""
          xp.RecordAttempt('alchemy',101,'a');xp.RecordOutput({itemID=10,quantity=3,castGUID='a'},'chat')
          clock=1010;xp.RecordAttempt('alchemy',101,'b')
          clock=1016;xp.RefreshObservation()
          local record=run.progress[run.plan.executionSteps[1].segmentID]
          assert(record.history==nil and record.attempts==nil and record.outputs[10].actual==3)
          assert(xp.RecordOutput({itemID=10,quantity=2,castGUID='b'}))
          xp.RecordAttempt('alchemy',101,'unknown')
          clock=1032;xp.RefreshObservation()
          local p=xp.Progress('alchemy',1)
          assert(p.casts==3 and p.actualOutputs==5 and p.pendingOutputs==1)
          assert(record.history==nil and record.attempts==nil)
          local totals=xp.GetRecipeTotals('alchemy')[1]
          assert(totals.confirmedOutputs[10]==5 and totals.guaranteedOutputs[10]==7)
        """)
        self.reload_execution()
        self.lua.execute("local p=xp.Progress('alchemy',1);assert(p.actualOutputs==5 and p.pendingOutputs==1)")

    def test_stopping_tracking_drops_memory_cache_without_a_background_observer(self):
        self.lua.execute("""
          xp.RecordAttempt('alchemy',101,'pending')
          xp.DisableTracking()
          local record=run.progress[run.plan.executionSteps[1].segmentID]
          assert(record.attempts==nil and record.history==nil)
          assert(not next(xp.eventFrame.events))
          assert(xp.Progress('alchemy',1).pendingOutputs==1)
        """)

    def test_archiving_stops_observation_without_a_receipt_window_timer(self):
        self.lua.execute("""
          timers={};C_Timer={After=function(delay,fn)timers[#timers+1]={due=clock+delay,fn=fn}end}
          xp.RecordAttempt('alchemy',101,'last');xp.End('alchemy','cancel')
          local record=run.progress[run.plan.executionSteps[1].segmentID]
          assert(record.attempts==nil and record.history==nil)
          assert(#timers==0,'archived execution scheduled a receipt-expiry timer')
          assert(not xp.GetRun('alchemy') and not next(xp.eventFrame.events))
          assert(not xp.RecordOutput({itemID=10,quantity=3,castGUID='last'}))
          assert(xp.GetRecipeTotals('alchemy',run.planID)[1].casts==1)
        """)

    def test_execution_can_read_legacy_first_aid_ledger_without_generating_a_route(self):
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
          xp.RecordAttempt('alchemy',101,'first');bag[10]=2;xp.RecordOutput({itemID=10,quantity=2,castGUID='first'})
          xp.RecordAttempt('alchemy',101,'second');bag[10]=4;xp.RecordOutput({itemID=10,quantity=2,castGUID='second'})
          xp.RecordAttempt('alchemy',102,'spend1');bag[10]=2;bag[11]=2;xp.RecordOutput({itemID=11,quantity=2,castGUID='spend1'})
          xp.RecordAttempt('alchemy',102,'spend2');bag[10]=0;bag[11]=4;xp.RecordOutput({itemID=11,quantity=2,castGUID='spend2'})
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
          bag[10]=6;pf.Sync();assert(follow.step==2)
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

    def test_hud_confirms_current_output_without_legacy_interface(self):
        self.load_follow()
        self.lua.execute("""
          ns.ProfTrack=nil
          xp.RecordAttempt('alchemy',101,'native-hud')
          assert(pf.VerifyCurrentOutput(4))
          local p=xp.Progress('alchemy',1)
          assert(p.casts==1 and p.actualOutputs==4 and run.steps==nil)
        """)

    def test_hud_rank_guidance_reads_actual_caps_for_main_and_current_partner(self):
        self.load_follow()
        self.lua.execute("""
          ns.ProfTrainers={};local ranks={
            {cap=75,sk=0,lv=5,zh='初级'}, {cap=150,sk=50,lv=10,zh='中级'},
            {cap=225,sk=125,lv=20,zh='高级'}, {cap=300,sk=200,lv=35,zh='专家级'}}
          ns.ProfTrainers.alchemy={ranks=ranks,list={}};ns.ProfTrainers.mining={ranks=ranks,list={}}
          caps={alchemy=75,mining=75};skillPoints=75;GetProfessions=function()return 1,2 end
          GetProfessionInfo=function(slot)
            local p=slot==1 and 'alchemy' or 'mining';return p,nil,skillPoints,caps[p],nil,nil,slot==1 and 171 or 186
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
          assert(#tasks==0,'rank hint appeared before its reminder threshold')
          skillPoints=125;tasks=pf.RankTasks('alchemy',300,run.plan.executionSteps,1)
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
          run=xp.StartNew('enchanting',p);bag[10938]=0
          assert(not xp.Progress('enchanting',1).complete)
          assert(not xp.RecordAttempt('enchanting',0,'not-a-craft'))
          assert(not xp.ConfirmConversion('enchanting',1,1,'obsolete'))
          assert(xp.ConfirmConversion('enchanting',1,1,run.planID));bag[10938]=3
          local progress=xp.Progress('enchanting',1)
          assert(progress.complete and progress.actualOutputs==3 and run.attemptsDone==0)
          assert(#xp.GetRecipeTotals('enchanting')==0)
          local record=run.progress[run.plan.executionSteps[1].segmentID]
          assert(record.attempts==nil and record.history==nil)
          assert(run.materialLedger.consumed[10939]==1 and run.materialLedger.confirmed[10938]==3)
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
        for name in ("ProfPolicies", "ProfEssences", "ProfGates", "ProfSolverCapture", "ProfRecovery", "ProfRouteSolver", "ProfExecution"):
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

    def test_topup_uses_bag_stock_but_reserves_the_remaining_base_demand(self):
        self.lua.execute("""
          local first=run.plan.executionSteps[1]
          local future=ns.ProfEconomy.Copy(first);future.segmentID='future';future.expectedGain=1
          future.goalSkill=4;future[1]=3;future[2]=4
          run.plan.executionSteps[2]=future
          bag[20]=2
          local returned=xp.CalculateSupplement('alchemy')
          for i=1,5000 do if not returned.inFlight then break end;xp.Pump('alchemy')end
          assert(returned.feasible and returned.appended)
          -- One of the two bag reagents remains reserved for the future step.
          -- The extra two crafts can reuse only the other; make one more for 2c.
          assert(returned.total==2,tostring(returned.total))
          assert(returned.seedInventory[20]==1)
          assert(bag[20]==2,'planning must not mutate the observed inventory')
        """)

    def test_topup_can_be_fully_supplied_by_unrelated_existing_bag_materials(self):
        self.lua.execute("""
          bag[20]=2
          local returned=xp.CalculateSupplement('alchemy')
          for i=1,5000 do if not returned.inFlight then break end;xp.Pump('alchemy')end
          assert(returned.feasible and returned.appended and returned.total==0)
          assert(returned.seedInventory[20]==2 and #returned.mats==0)
        """)


if __name__ == "__main__":
    unittest.main()
