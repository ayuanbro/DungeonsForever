"""The route facade keeps persisted execution separate from search publication."""
import unittest

import test_prof_runtime as fixture


class ExecutionFacadeTests(unittest.TestCase):
    def setUp(self):
        fixture.RuntimeTests.setUp(self)
        fixture.RuntimeTests.live_capture_fixture(self)
        self.load(str(fixture.ROOT / 'Core' / 'ProfExecution.lua'))
        self.lua.execute('''
          ns.ProfEconomy.Professions=function()return {alchemy={cur=liveSkill,max=300}}end
        ''')

    def test_plan_identity_survives_reload_and_changes_only_on_new_calculation(self):
        self.lua.execute('''
          opts={start=1,target=2};original=finish('alchemy',opts)
          assert(original.executionVersion==1 and original.planID)
          planID=original.planID
        ''')
        self.load(str(fixture.ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute('''
          local restored=ns.ProfRouteAuto.Get('alchemy',opts)
          assert(restored.planID==planID and restored.cached)
          ns.ProfRouteAuto.Recalculate('alchemy',opts)
          assert(finish('alchemy',opts).planID~=planID)
        ''')

    def test_active_execution_is_a_frozen_copy_of_search_result(self):
        self.lua.execute('''
          local opts={start=1,target=2};local candidate=finish('alchemy',opts)
          local xp=ns.ProfExecution
          local run=assert(xp.Bind('alchemy',candidate))
          local frozen=assert(xp.GetPlan('alchemy'))
          assert(frozen~=candidate)
          local count=frozen.executionSteps[1][4]
          candidate.executionSteps[1][4]=999;candidate.revision=candidate.revision+1
          assert(ns.ProfRouteAuto.Get('alchemy',opts)==frozen)
          assert(frozen.executionSteps[1][4]==count)
          assert(xp.GetRun('alchemy')==run)
        ''')

    def test_explicit_recalculate_supplies_verified_seed_and_actual_skill(self):
        self.lua.execute('''
          local ra=ns.ProfRouteAuto
          finish('alchemy',{start=1,target=2})
          local prepared=0;local published=0;local captured
          ns.ProfExecution.PrepareRecalculate=function(slug)
            assert(slug=='alchemy');prepared=prepared+1;return {[10]=2},'previous-plan'
          end
          ns.ProfExecution.PlanRecalculated=function()published=published+1 end
          local capture=ns.ProfEconomy.Capture
          ns.ProfEconomy.Capture=function(slug,opts)captured=opts;return capture(slug,opts)end
          liveSkill=7
          ra.Recalculate('alchemy',{start=1,target=8,fromCurrent=false})
          local r=finish('alchemy',{start=1,target=8,fromCurrent=false})
          assert(prepared==1 and published>0)
          assert(captured.executionInventory[10]==2)
          assert(captured.executionSourcePlanID=='previous-plan' and captured.start==7)
          assert(r.start==7 and r.executionOptions.executionSourcePlanID=='previous-plan')
          assert(r.executionOptions.executionInventory[10]==2 and not r.stale)
        ''')

    def test_recalculate_without_crafts_does_not_restore_the_previous_exact_cache(self):
        self.lua.execute('''
          local ra=ns.ProfRouteAuto;local xp=ns.ProfExecution
          local opts={start=1,target=2}
          local original=finish('alchemy',opts)
          local previous=assert(xp.Bind('alchemy',original))
          livePrice=19
          local pending=ra.Recalculate('alchemy',opts)
          assert(ra.Get('alchemy',opts)==pending and pending.status=='searching')
          local fresh=finish('alchemy',opts)
          assert(fresh.planID~=original.planID and fresh.total==19)
          assert(fresh.executionOptions.executionSourcePlanID==previous.planID)
          assert(next(fresh.executionOptions.executionInventory)==nil)
          assert(not fresh.stale and not fresh.settingsChanged)
          local capturesBefore=captures;local queued=#queue
          for i=1,3 do assert(ra.Get('alchemy',{start=1,target=2})==fresh) end
          assert(not fresh.stale and captures==capturesBefore and #queue==queued)
          assert(previous.status=='archived' and previous.attemptsDone==0)
        ''')

    def carried_output_recalculate_fixture(self):
        self.lua.execute('''
          bag={[10]=2}
          function GetItemCount(id)return bag[id] or 0 end
          function fixture()
            return {recipes={
              {profession='alchemy',spell=101,item=10,count=2,outputMin=2,outputMax=2,
                learn=1,yellow=2,green=2,grey=2,mats={{11,1}},cooldown=false},
              {profession='alchemy',spell=102,item=20,count=1,outputMin=1,outputMax=1,
                learn=2,yellow=20,green=30,grey=40,mats={{10,1}},cooldown=false}},
              inventory={},professions={alchemy={cur=liveSkill,max=300}},
              known={['alchemy:101']=true,['alchemy:102']=true},prices={[11]=7}}
          end
          opts={start=1,target=3,fromCurrent=false}
          local ra=ns.ProfRouteAuto;local xp=ns.ProfExecution
          original=finish('alchemy',opts)
          oldRun=assert(xp.Bind('alchemy',original))
          assert(xp.RecordAttempt('alchemy',101,'producer-cast'))
          assert(xp.RecordOutput({itemID=10,quantity=2,castGUID='producer-cast'},'structured'))
          liveSkill=2
          ra.Recalculate('alchemy',opts)
          assert(ra.Get('alchemy',opts).status=='searching')
          fresh=finish('alchemy',opts)
          assert(fresh.planID~=original.planID and fresh.start==2 and fresh.total==0)
          assert(fresh.executionOptions.executionSourcePlanID==oldRun.planID)
          assert(fresh.executionOptions.executionInventory[10]==2 and fresh.seedInventory[10]==2)
          assert(fresh.executionOptions.fromCurrent and fresh.cacheSignature:find('fixed:1',1,true))
          assert(not fresh.stale and not fresh.settingsChanged)
          assert(#fresh.executionSteps==1 and fresh.executionSteps[1][3]==102)
          assert(oldRun.status=='archived' and oldRun.attemptsDone==1)
        ''')

    def test_recalculate_keeps_carried_outputs_and_selected_start_identity(self):
        self.carried_output_recalculate_fixture()
        self.lua.execute('''
          local capturesBefore=captures;local queued=#queue
          local ra=ns.ProfRouteAuto
          assert(ra.Get('alchemy',{start=1,target=3,fromCurrent=false})==fresh)
          assert(not fresh.stale and fresh.total==0 and fresh.seedInventory[10]==2)
          assert(captures==capturesBefore and #queue==queued)
        ''')

    def test_recalculated_carry_route_restores_fresh_after_module_reload(self):
        self.carried_output_recalculate_fixture()
        self.lua.execute('capturesBefore=captures;queuedBefore=#queue;savedID=fresh.planID')
        self.load(str(fixture.ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute('''
          local restored=ns.ProfRouteAuto.Get('alchemy',{start=1,target=3,fromCurrent=false})
          assert(restored.planID==savedID and not restored.stale)
          assert(restored.total==0 and restored.executionOptions.executionSourcePlanID==oldRun.planID)
          assert(restored.executionOptions.executionInventory[10]==2 and restored.seedInventory[10]==2)
          assert(captures==capturesBefore and #queue==queuedBefore)
          local cache=DungeonsForeverDB.prof.routeCache['Test-Realm']
          assert(cache.routes[cache.active.alchemy].result.planID==savedID)
        ''')

    def test_real_settings_changes_still_mark_recalculated_execution_stale(self):
        self.carried_output_recalculate_fixture()
        self.lua.execute('''
          local capturesBefore=captures;local queued=#queue
          local shown=ns.ProfRouteAuto.Get('alchemy',{start=1,target=4,fromCurrent=false})
          assert(shown==fresh and shown.stale and shown.settingsChanged and shown.staleReason=='settings')
          assert(shown.target==3 and shown.seedInventory[10]==2)
          assert(captures==capturesBefore and #queue==queued)
          assert(ns.ProfExecution.GetRun('alchemy').attemptsDone==0)
        ''')

    def test_settings_switch_to_an_exact_cached_route_marks_frozen_execution_stale(self):
        self.lua.execute('''
          local ra=ns.ProfRouteAuto;local xp=ns.ProfExecution
          local alternate=finish('alchemy',{start=1,target=3})
          local opts={start=1,target=2}
          ra.Recalculate('alchemy',opts)
          local original=finish('alchemy',opts)
          assert(xp.Bind('alchemy',original))
          ra.Recalculate('alchemy',opts)
          local fresh=finish('alchemy',opts)
          assert(not fresh.stale and fresh.target==2)
          local capturesBefore=captures;local queued=#queue
          local shown=ra.Get('alchemy',{start=1,target=3})
          assert(shown==fresh and shown.stale and shown.settingsChanged and shown.staleReason=='settings')
          assert(shown.target==2 and shown.total==7 and alternate.total==14)
          assert(captures==capturesBefore and #queue==queued)
          assert(xp.GetRun('alchemy').attemptsDone==0)
        ''')

    def test_synthetic_solver_fixtures_never_start_or_replace_player_execution(self):
        self.lua.execute('''
          ns.ProfExecution.PrepareRecalculate=function()error('synthetic run touched player state')end
          ns.ProfExecution.PlanRecalculated=function()error('synthetic run touched player state')end
          local r=finish('alchemy',{snapshot=fixture(),start=1,target=2})
          assert(r.total==7)
          ns.ProfRouteAuto.Recalculate('alchemy',{snapshot=fixture(),start=1,target=2})
          assert(ns.ProfExecution.GetRun('alchemy')==nil)
        ''')

    def test_old_frozen_npc_plan_cannot_override_a_current_auction_candidate(self):
        self.lua.execute('''
          opts={start=1,target=2};candidate=finish('alchemy',opts)
          local xp=ns.ProfExecution
          frozenRun=assert(xp.Bind('alchemy',candidate));frozen=xp.GetPlan('alchemy')
          frozen.mats[1].source='vendor';frozen.mats[1].vendor=true
          frozen.vendorTotal=7;frozen.ahTotal=0;frozen.vendorQuoteRevision=2
          local capturesBefore=captures;local queued=#queue
          local view=ns.ProfRouteAuto.Get('alchemy',opts)
          assert(view.status=='recalculate_required' and not view.feasible and #view.mats==0)
          assert(view.diagnostics[1].code=='vendorQuoteChanged' and view.total==0)
          assert(xp.GetPlan('alchemy')==frozen and xp.GetRun('alchemy')==frozenRun)
          assert(frozen.total==7 and frozen.vendorQuoteRevision==2 and frozen.mats[1].vendor)
          assert(candidate.mats[1].source=='ah' and captures==capturesBefore and #queue==queued)
        ''')

    def test_old_frozen_npc_plan_is_blocked_when_route_cache_is_missing(self):
        self.lua.execute('''
          opts={start=1,target=2};local candidate=finish('alchemy',opts)
          local xp=ns.ProfExecution;xp.Bind('alchemy',candidate)
          frozen=xp.GetPlan('alchemy');frozen.mats[1].source='vendor'
          frozen.vendorQuoteRevision=2
          DungeonsForeverDB.prof.routeCache=nil
          capturesBefore=captures;queued=#queue
        ''')
        self.load(str(fixture.ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute('''
          local view=ns.ProfRouteAuto.Get('alchemy',opts)
          assert(view.status=='recalculate_required' and #view.steps==0 and #view.mats==0)
          assert(captures==capturesBefore and #queue==queued)
          assert(ns.ProfExecution.GetPlan('alchemy')==frozen and frozen.mats[1].source=='vendor')
        ''')

    def test_fresh_npc_execution_is_valid_until_the_csv_fingerprint_changes(self):
        fixture.RuntimeTests.install_synthetic_vendor_quote_fixture(self)
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()
            local s=fixture();s.prices[11]=70
            s.offers={[11]=ns.ProfItemPrices.GetOffers(11)}
            return ns.ProfEconomy.Index(s)
          end
          opts={start=1,target=2};local candidate=finish('alchemy',opts)
          assert(candidate.total==3 and candidate.vendorQuoteData=='material-supply-v1:supply-a|formula:quotes-a')
          ns.ProfItemsMeta.sources.csv.sha256='quotes-b'
          assert(ns.ProfRouteAuto.Get('alchemy',opts).status=='recalculate_required')
          ns.ProfItemsMeta.sources.csv.sha256='quotes-a'
          assert(ns.ProfRouteAuto.Get('alchemy',opts)==candidate)
          local xp=ns.ProfExecution;assert(xp.Bind('alchemy',candidate))
          local frozen=xp.GetPlan('alchemy');assert(ns.ProfRouteAuto.Get('alchemy',opts)==frozen)
          ns.ProfItemsMeta.sources.csv.sha256='quotes-b'
          local view=ns.ProfRouteAuto.Get('alchemy',opts)
          assert(view.status=='recalculate_required' and view.total==0 and #view.mats==0)
          assert(xp.GetPlan('alchemy')==frozen and frozen.vendorQuoteData=='material-supply-v1:supply-a|formula:quotes-a' and frozen.total==3)
        ''')

    def test_old_npc_supplement_and_binding_are_blocked_without_erasing_history(self):
        self.lua.execute('''
          local candidate=finish('alchemy',{start=1,target=2});local xp=ns.ProfExecution
          local run=assert(xp.Bind('alchemy',candidate))
          local old={feasible=true,total=13,mats={{id=11,count=1,source='vendor'}},vendorQuoteRevision=2}
          run.supplement=old
          local view=xp.GetSupplement('alchemy')
          assert(view.status=='recalculate_required' and not view.feasible and #view.mats==0)
          assert(run.supplement==old and old.total==13 and old.mats[1].source=='vendor')
          local refused,reason=xp.Bind('alchemy',old,{force=true})
          assert(not refused and reason=='vendorQuoteChanged' and xp.GetRun('alchemy')==run)
          run.plan.mats[1].source='vendor';run.plan.vendorQuoteRevision=2
          local auctionSupplement={feasible=true,total=3,mats={{id=11,count=3,source='ah'}}}
          run.supplement=auctionSupplement
          view=xp.GetSupplement('alchemy')
          assert(view.status=='recalculate_required' and #view.mats==0)
          assert(run.supplement==auctionSupplement and auctionSupplement.total==3)
          local queued=#queue;local capturesBefore=captures
          refused,reason=xp.CalculateSupplement('alchemy')
          assert(not refused and reason=='vendorQuoteChanged')
          assert(#queue==queued and captures==capturesBefore and xp.GetPlan('alchemy')==run.plan)
        ''')

    def test_pure_auction_execution_requires_recalculation_after_fingerprint_changes(self):
        self.lua.execute('''
          opts={start=1,target=2};local candidate=finish('alchemy',opts)
          local xp=ns.ProfExecution;assert(xp.Bind('alchemy',candidate))
          local frozen=xp.GetPlan('alchemy')
          ns.ProfItemsMeta={sources={csv={sha256='new-data'}}}
          assert(ns.ProfRouteAuto.VendorQuotesChanged(frozen))
          local view=ns.ProfRouteAuto.Get('alchemy',opts)
          assert(view~=frozen and view.status=='recalculate_required' and #view.mats==0)
          assert(frozen.mats[1].source=='ah' and frozen.total==7)
        ''')

    def test_supplement_recaptures_inputs_instead_of_reusing_a_saved_snapshot(self):
        self.lua.execute('''
          local xp=ns.ProfExecution;local candidate=finish('alchemy',{start=1,target=2})
          local run=assert(xp.Bind('alchemy',candidate))
          run.plan.executionOptions={snapshot={prices={},offers={
            [11]={{npcID=999,price=0,quantity=1,unlimited=true}}}}}
          assert(xp.RecordAttempt('alchemy',101,'extra-test'))
          assert(xp.Progress('alchemy').extraCrafts==1)
          local capture=ns.ProfEconomy.Capture;local recaptured=false
          ns.ProfEconomy.Capture=function(slug,opts,tick)
            if slug=='__purchase' then
              assert(opts.snapshot.prices[11]==7 and not opts.snapshot.offers[11])
              return ns.ProfEconomy.Index(opts.snapshot)
            end
            assert(opts.snapshot==nil,'saved snapshot reached live procurement')
            recaptured=true;return capture(slug,opts,tick)
          end
          assert(xp.CalculateSupplement('alchemy'))
          for i=1,1000 do
            if not xp.GetSupplement('alchemy').inFlight then break end
            xp.Pump('alchemy')
          end
          local result=xp.GetSupplement('alchemy')
          assert(recaptured and not result.inFlight and result.feasible and result.total==7,
            tostring(result.status)..' total='..tostring(result.total)..' error='..
              tostring(result.error or result.diagnostics and result.diagnostics[1] and result.diagnostics[1].detail))
          assert(result.mats[1].source=='ah' and not result.mats[1].vendor)
          assert(result.vendorQuoteRevision==5 and run.plan.executionOptions.snapshot.offers[11][1].price==0)
        ''')


if __name__ == '__main__':
    unittest.main()
