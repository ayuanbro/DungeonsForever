"""Candidate undo through the native solver, execution owner and page."""
import unittest
import test_prof_route_plans as fixtures
ROOT=fixtures.ROOT
import test_prof_ui_fusion as ui


class CandidateRevertTests(unittest.TestCase):
    def setUp(self):
        fixtures.NativeRoutePlansTests.setUp(self)
        self.lua.execute('''
          price=7
          ns.ProfEconomy.Capture=function(slug,opts)
            local s=fixture();s.prices[11]=price;s.executionInventory=opts.executionInventory
            s.recipes[1].profession=slug;s.professions={[slug]={cur=1,max=300}}
            s.known={[slug..':101']=true};return ns.ProfEconomy.Index(s)
          end
          ra=ns.ProfRouteAuto;xp=ns.ProfExecution;opts={start=1,target=3}
        ''')

    def test_restore_cancels_pending_callbacks_and_persists_only_restored_skeleton(self):
        self.lua.execute('''
          local old=finish('alchemy',opts)
          ra.Recalculate('alchemy',opts);local callback=queue[#queue]
          assert(xp.IsPreparing('alchemy') and ra.HasPlanPrev('alchemy'))
          local restored=assert(ra.RevertPlan('alchemy',opts))
          assert(restored~=old and restored.planID==old.planID and restored.total==14)
          assert(ra.Get('alchemy',opts)==restored and ra.Peek('alchemy')==restored)
          assert(not ra.HasWork('alchemy') and callback()==true)
          ra.Continue('alchemy');assert(not ra.HasWork('alchemy'))
          assert(not ra.HasPlanPrev('alchemy') and not ra.RevertPlan('alchemy',opts))
          local db=DungeonsForeverDB.prof.routePlans.characters['Test-Realm']
          local entry=db.routes[db.active.alchemy]
          assert(entry.skeleton.planID==old.planID and entry.result==nil)
          for _,f in ipairs(frames)do if f.events.PLAYER_LOGOUT then f.OnEvent(f,'PLAYER_LOGOUT')end end
          assert(db.routes[db.active.alchemy].skeleton.planID==old.planID)
        ''')

    def test_latest_backup_per_profession_is_independent(self):
        self.lua.execute('''
          local first=finish('alchemy',opts);local other=finish('enchanting',opts)
          ra.Recalculate('alchemy',opts);local second=finish('alchemy',opts)
          ra.Recalculate('alchemy',opts);finish('alchemy',opts)
          ra.Recalculate('enchanting',opts);finish('enchanting',opts)
          assert(ra.RevertPlan('alchemy',opts).planID==second.planID)
          assert(ra.HasPlanPrev('enchanting'))
          assert(ra.RevertPlan('enchanting',opts).planID==other.planID)
          assert(not ra.HasPlanPrev('alchemy'))
        ''')

    def test_market_and_settings_freshness_checked_without_replacing_steps(self):
        self.lua.execute('''
          local old=finish('alchemy',opts)
          old.auctionPriceInputs={[11]=7};ra.AHPriceOf=function()return price end
          ra.Recalculate('alchemy',opts);finish('alchemy',opts);price=9
          local r=ra.RevertPlan('alchemy',opts)
          assert(r.stale and r.staleReason=='prices' and r.total==14)
          assert(r.executionSteps[1][3]==old.executionSteps[1][3])
          ra.Recalculate('alchemy',opts);finish('alchemy',opts)
          r=ra.RevertPlan('alchemy',{start=1,target=4})
          assert(r.stale and r.staleReason=='settings' and r.target==3)
        ''')

    def test_explicit_recipe_invalidation_reaches_backup(self):
        self.lua.execute('''
          finish('alchemy',opts);ra.Recalculate('alchemy',opts);finish('alchemy',opts)
          ra.Invalidate('recipes')
          local r=ra.RevertPlan('alchemy',opts)
          assert(r.stale and r.staleReason=='recipes')
        ''')

    def test_active_execution_and_continuation_cannot_be_undone(self):
        self.lua.execute('''
          finish('alchemy',opts);ra.Recalculate('alchemy',opts)
          local candidate=finish('alchemy',opts);assert(ra.HasPlanPrev('alchemy'))
          local run=assert(xp.Bind('alchemy',candidate))
          assert(not ra.HasPlanPrev('alchemy') and not ra.RevertPlan('alchemy',opts))
          local frozen=run.plan
          ra.Recalculate('alchemy',opts)
          assert(not ra.HasPlanPrev('alchemy') and not ra.RevertPlan('alchemy',opts))
          assert(run.plan==frozen)
          finish('alchemy',opts);xp.End('alchemy')
          ra.Recalculate('alchemy',opts);finish('alchemy',opts)
          assert(not ra.HasPlanPrev('alchemy') and not ra.RevertPlan('alchemy',opts))
        ''')

    def test_backup_preserves_native_metadata_without_aliasing(self):
        self.lua.execute('''
          local old=finish('alchemy',opts);local row=old.executionSteps[1]
          row.allocations={{consumerID='consumer',itemID=10,count=2}}
          row.quest={questID=42};row.conversion={inputItemID=55,outputItemID=56}
          row.profession='enchanting'
          ra.Recalculate('alchemy',opts)
          row.allocations[1].count=99;row.quest.questID=99
          local r=ra.RevertPlan('alchemy',opts);local s=r.executionSteps[1]
          assert(s.allocations[1].count==2 and s.quest.questID==42)
          assert(s.profession=='enchanting' and s.conversion.outputItemID==56)
        ''')

    def test_reload_discards_backup_and_rebuilds_restored_candidate(self):
        self.lua.execute('''
          original=finish('alchemy',opts);ra.Recalculate('alchemy',opts);finish('alchemy',opts)
          assert(ra.RevertPlan('alchemy',opts))
          ra.SavePlanPrev('alchemy');assert(ra.HasPlanPrev('alchemy'));price=9
        ''')
        self.load((ROOT/'Core/ProfRoutePlans.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          ra=ns.ProfRouteAuto;assert(not ra.HasPlanPrev('alchemy'))
          local restored=finish('alchemy',opts)
          assert(restored.planID==original.planID and restored.total==18 and restored.fromSkeleton)
        ''')

    def test_no_initial_or_synthetic_backup(self):
        self.lua.execute('''
          ra.Recalculate('alchemy',opts);assert(not ra.HasPlanPrev('alchemy'))
          finish('alchemy',opts)
          local synthetic={start=1,target=3,snapshot=fixture()}
          ra.Recalculate('alchemy',synthetic);finish('alchemy',synthetic)
          assert(not ra.HasPlanPrev('alchemy'))
        ''')

    def test_skeleton_result_construction_can_yield_before_finishing(self):
        self.lua.execute('''
          original=finish('alchemy',opts);price=9
        ''')
        self.load((ROOT/'Core/ProfRoutePlans.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          ra=ns.ProfRouteAuto
          local solver=ns.ProfRouteSolver;local result=solver.Result
          local yielded=false
          solver.Result=function(job,state,status)
            if job.opts.routeSkeleton and state and not yielded then
              yielded=true;coroutine.yield('work')
            end
            return result(job,state,status)
          end
          local restored=finish('alchemy',opts)
          assert(yielded and restored.fromSkeleton and restored.targetReached)
          assert(restored.total==18 and #restored.mats==1 and restored.mats[1].count==2)
        ''')


class CandidateRevertUITests(unittest.TestCase):
    boot=ui.ProfessionUIFusionTests.boot

    def setUp(self):
        self.boot('zhCN')

    def test_page_recalculate_then_revert_updates_facade_and_page(self):
        self.lua.execute('''
          local opts=PD.BuildLvOpts('alchemy',1)
          local old=finish('alchemy',opts);PD.RowsLeveling({})
          local _,click=PD.LevelTool();click('recalc');PD.RowsLeveling({})
          assert(PD.HasPlanPrev())
          assert(PD.RevertPlan() and not PD.HasPlanPrev())
          assert(PD.autoSnapshot.planID==old.planID and not PD.forceExact)
          PD.RowsLeveling({})
          assert(PD.autoSnapshot==ns.ProfRouteAuto.Get('alchemy',opts))
          assert(PD.autoSnapshot.planID==old.planID and not ns.ProfRouteAuto.HasWork('alchemy'))
        ''')


if __name__=='__main__':
    unittest.main()
