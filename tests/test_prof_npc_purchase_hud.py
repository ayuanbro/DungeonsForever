"""NPC preparation tasks through the real HUD and persistent execution service.

Bag fixtures verify task readiness only; full procurement and AH exports remain
the selected plan quantities. These tests do not claim live game validation.
"""
import unittest

import test_prof_execution_hud as hud_tests
import test_prof_follow as follow_tests


class NPCPurchaseHUDTests(unittest.TestCase):
    make_runtime = hud_tests.ExecutionHUDTests.make_runtime

    def setUp(self):
        self.lua = self.make_runtime()
        self.lua.execute('''
          function startNPCPlan()
            setPlan({makeStep(150,155,101,5)})
            currentResult.mats={{id=10,count=3,source='vendor'},
              {id=10,count=5,source='npc'}, {id=10,count=99,source='ah'},
              {id=11,count=4,source='vendor',vendor=true}}
            currentResult.formulas={{id=12,count=1,source='vendor',vendor=true}}
            ns.ProfFollow.Sync();ns.ProfFollow.Build();ns.ProfFollow.f:Show()
          end
          function npcTask()
            local mode,steps,res=ns.ProfFollow.GetRoute('alchemy',followState.skill)
            return ns.ProfFollow.GetNPCPurchaseTask(followState,mode,steps,res)
          end
          bag[10]=2;bag[11]=0;bag[12]=0
          startNPCPlan()
        ''')

    def test_first_step_aggregates_selected_npc_materials_and_keeps_full_purchases(self):
        self.lua.execute('''
          ns.ProfFollow.Paint()
          local f=ns.ProfFollow.f;local task=npcTask()
          assert(f.npcQuest.shown and not f.card.shown)
          assert(f.npcQuest.head.text=='先向NPC购买材料')
          assert(f.seg.text=='自动计算 · 步骤 1 / 2')
          assert(task.total==2 and task.need==12 and task.have==2)
          assert(task.rows[1].id==10 and task.rows[1].need==8,
            'same-item NPC batches were not summed or AH quantity leaked in')
          assert(f.npcQuest.summary.text=='采购进度：0/2种 · 2/12件')
          assert(f.npcQuest.rows[1].count.text=='随身 2/8')
          local purchases=ns.ProfFollow.GetPurchases(followState)
          assert(#purchases==5 and purchases[1].need==3 and purchases[2].need==5)
          assert(purchases[3].need==99 and purchases[4].need==4)
          assert(purchases[5].formula and purchases[5].need==1)
          assert(followState.step==1 and ns.ProfExecution.GetRun('alchemy').attemptsDone==0)
        ''')

    def test_each_completed_item_stays_checked_after_consumption_then_advances(self):
        self.lua.execute('''
          bag[10]=8;ns.ProfFollow.Paint()
          assert(npcTask().ready==1)
          bag[10]=0;ns.ProfFollow.Paint()
          assert(npcTask().ready==1 and npcTask().rows[1].have==8)
          bag[11]=4;ns.ProfFollow.Paint()
          assert(npcTask().complete and not ns.ProfFollow.f.npcQuest.shown)
          assert(ns.ProfFollow.f.card.shown and ns.ProfFollow.f.seg.text=='自动计算 · 步骤 2 / 2')
          bag[11]=0;ns.ProfFollow.Paint()
          assert(npcTask().complete and not ns.ProfFollow.f.npcQuest.shown,
            'craft consumption revived the completed NPC task')
          assert(ns.ProfFollow.GetPurchases(followState)[4].need==4)
        ''')

    def test_browsing_next_shows_first_recipe_and_return_restores_purchase_task(self):
        self.lua.execute('''
          ns.ProfFollow.Paint();ns.ProfFollow.Skip()
          local f=ns.ProfFollow.f
          assert(f.card.shown and not f.npcQuest.shown)
          assert(f.card.name.text=='Spell101' and f.seg.text=='自动计算 · 步骤 2 / 2')
          assert(f.nowBtn.shown and followState.step==1)
          f.nowBtn.scripts.OnClick()
          assert(f.npcQuest.shown and not f.card.shown and ns.ProfFollow.view==0)
          ns.ProfFollow.Prev()
          assert(ns.ProfFollow.view==0 and f.npcQuest.shown)
        ''')

    def test_bank_inventory_cannot_complete_carried_purchase_task(self):
        self.lua.execute('''
          C_Item.GetItemCount=function(id,includeBank)
            assert(includeBank==false,'NPC task counted bank inventory')
            return bag[id] or 0
          end
          ns.ProfFollow.Paint();assert(not npcTask().complete)
        ''')

    def test_background_search_keeps_task_but_new_execution_plan_resets_it(self):
        self.lua.execute('''
          bag[10]=8;bag[11]=4;ns.ProfFollow.Paint()
          local key=npcTask().key
          currentResult.revision=2;currentResult.total=1
          bag[10]=0;bag[11]=0;ns.ProfFollow.Sync();ns.ProfFollow.Paint()
          assert(npcTask().key==key and npcTask().complete,
            'a background candidate replaced frozen NPC task progress')
          ns.ProfFollow.view=1;ns.ProfFollow.npcPurchaseScroll=7
          assert(ns.ProfExecution.StartNew('alchemy',currentResult))
          ns.ProfFollow.Sync();ns.ProfFollow.Paint()
          assert(npcTask().key~=key and not npcTask().complete)
          assert(ns.ProfFollow.f.npcQuest.shown and ns.ProfFollow.view==0 and ns.ProfFollow.npcPurchaseScroll==0)
        ''')

    def test_completion_persists_across_reload_and_profession_switch(self):
        self.lua.execute('''
          bag[10]=8;bag[11]=4;ns.ProfFollow.Paint()
          assert(npcTask().complete)
          ns.ProfFollow.Toggle('mining');ns.ProfFollow.Toggle('alchemy')
        ''')
        saved = self.lua.eval("savedLiteral(DungeonsForeverDB)")
        restored = self.make_runtime(saved)
        restored.execute('''
          bag[10]=0;bag[11]=0
          ns.ProfFollow.Sync();ns.ProfFollow.Build();ns.ProfFollow.f:Show();ns.ProfFollow.Paint()
          local mode,steps,res=ns.ProfFollow.GetRoute('alchemy',followState.skill)
          local task=ns.ProfFollow.GetNPCPurchaseTask(followState,mode,steps,res)
          assert(task.complete and ns.ProfFollow.f.card.shown and not ns.ProfFollow.f.npcQuest.shown)
        ''')

    def test_old_execution_already_crafted_does_not_gain_new_preparation_block(self):
        self.lua.execute('''
          event('UNIT_SPELLCAST_SUCCEEDED','player','already-started',101)
          ns.ProfFollow.Paint()
          assert(npcTask().complete and not ns.ProfFollow.f.npcQuest.shown)
          assert(ns.ProfExecution.GetRun('alchemy').attemptsDone==1)
        ''')

    def test_invalid_plan_never_exposes_old_purchase_task(self):
        self.lua.execute('''
          ns.ProfFollow.Paint();assert(ns.ProfFollow.f.npcQuest.shown)
          currentResult={planVersion=2,revision=2,feasible=false,status='recalculate_required',steps={}}
          ns.ProfFollow.Sync();ns.ProfFollow.Paint()
          assert(not ns.ProfFollow.f.npcQuest.shown)
          assert(ns.ProfFollow.GetNPCPurchaseTask(followState,'auto',{},currentResult)==nil)
        ''')

    def test_bag_events_refresh_progress_and_many_materials_can_be_scrolled(self):
        self.lua.execute('''
          currentResult.mats={}
          for id=1,20 do currentResult.mats[#currentResult.mats+1]={id=id,count=5,source='vendor'};bag[id]=0 end
          assert(ns.ProfExecution.StartNew('alchemy',currentResult));ns.ProfFollow.Sync();ns.ProfFollow.Paint()
          local f=ns.ProfFollow.f
          assert(f.npcQuest.rows[1].name.text=='[ ] Item1')
          f.npcQuest.scripts.OnMouseWheel(f.npcQuest,-4)
          assert(f.npcQuest.rows[1].name.text=='[ ] Item5')
          assert(f.npcQuest.rows[16].name.text=='[ ] Item20')
          bag[20]=5;f.scripts.OnEvent(f,'BAG_UPDATE_DELAYED')
          assert(npcTask().ready==1 and f.npcQuest.rows[16].count.text=='随身 5/5')
        ''')

    def test_pure_ah_plan_has_no_preparation_step(self):
        self.lua.execute('''
          setPlan({makeStep(150,155,101,5)})
          assert(ns.ProfExecution.StartNew('alchemy',currentResult));ns.ProfFollow.Sync();ns.ProfFollow.Paint()
          assert(npcTask()==nil and not ns.ProfFollow.f.npcQuest.shown)
          assert(ns.ProfFollow.f.card.shown and ns.ProfFollow.f.seg.text=='自动计算 · 步骤 1 / 1')
        ''')

    def test_existing_automatic_first_aid_requires_manual_fixed_plan_migration(self):
        self.lua.execute('''
          ns.ProfLeveling['first-aid']={steps={{1,50,101,49}}}
          skills['first-aid']={cur=1,max=300}
          setPlan({makeStep(1,50,101,49)});currentResult.mode='auto'
          local run={slug='first-aid',plan=currentResult,progress={},planID='old-aid-auto',currentIndex=1}
          local character=DungeonsForeverDB.prof.execution['Test-Realm']
          character.runs[run.planID]=run;character.active['first-aid']=run.planID
          run.progress['saved-fact']={casts=3}
          followState.slug='first-aid';followState.skill=1
          local mode,steps,res=ns.ProfFollow.GetRoute('first-aid',1)
          assert(mode=='fixed' and #steps==0 and res.status=='recalculate_required')
          assert(res.message=='急救已改为固定路线，请重新计算。')
          ns.ProfFollow.Sync();ns.ProfFollow.Paint()
          assert(not ns.ProfFollow.f.card.shown and not ns.ProfFollow.f.npcQuest.shown)
          assert(ns.ProfFollow.f.finish.text=='急救已改为固定路线，请重新计算。')
          assert(ns.ProfExecution.GetRun('first-aid')==run and run.progress['saved-fact'].casts==3)
        ''')

    def test_fixed_recalculation_resets_task_and_supplement_has_independent_quantities(self):
        self.lua.execute('''
          settings.autoRoute=false;currentResult.mode='fixed'
          assert(ns.ProfExecution.StartNew('alchemy',currentResult));ns.ProfFollow.Sync()
          bag[10]=8;bag[11]=4;ns.ProfFollow.Paint()
          local key=npcTask().key;assert(npcTask().complete)
          local run=ns.ProfExecution.GetRun('alchemy')
          run.supplement={planVersion=2,status='complete',feasible=true,mats={{id=11,count=20,source='vendor'}}}
          bag[10]=0;bag[11]=0;ns.ProfFollow.shopKind='supplement';ns.ProfFollow.Paint()
          assert(npcTask().key==key and npcTask().complete)
          assert(ns.ProfFollow.GetPurchases(followState,'supplement')[1].need==20)
          assert(ns.ProfExecution.StartNew('alchemy',currentResult));ns.ProfFollow.Sync();ns.ProfFollow.Paint()
          assert(npcTask().key~=key and not npcTask().complete and npcTask().rows[2].need==4)
        ''')

    def test_large_counts_and_localized_labels_keep_columns_inside_the_card(self):
        self.lua.execute('''
          currentResult.mats={{id=10,count=123456789,source='vendor'}}
          assert(ns.ProfExecution.StartNew('alchemy',currentResult));ns.ProfFollow.Sync()
          ns.ProfModule.TextW=function(text) return #text*7 end
          for _,label in ipairs({'随身 %d/%d','隨身 %d/%d','In bags %d/%d',
              'Very long localized carried quantity %d/%d'}) do
            ns.L['随身 %d/%d']=label
            ns.ProfFollow.Paint()
            local card=ns.ProfFollow.f.npcQuest;local row=card.rows[1]
            assert(row.count.text==string.format(label,2,123456789))
            assert(row.count.width>=108 and row.name.width>0)
            assert(row.count.width+row.name.width+8<=card.width-16)
            assert(row.name.point[5]==row.count.point[5])
          end
        ''')


class FixedNPCPurchaseHUDTests(unittest.TestCase):
    setUp = follow_tests.FixedShoppingPriceTests.setUp

    def test_fixed_route_uses_selected_npc_quantity_and_preserves_ah_export(self):
        self.lua.execute('''
          ns.ProfRecipes.alchemy.rows[1][12]={{10,12}};auctionUnit=3;bag[10]=0
          ns.ProfFollow.Sync();ns.ProfFollow.Build();ns.ProfFollow.f:Show();ns.ProfFollow.Paint()
          local mode,steps,res=ns.ProfFollow.GetRoute('alchemy',1)
          local task=ns.ProfFollow.GetNPCPurchaseTask(followState,mode,steps,res)
          assert(mode=='fixed' and task.rows[1].need==10)
          assert(ns.ProfFollow.f.npcQuest.shown and ns.ProfFollow.f.seg.text=='固定路线 · 步骤 1 / 2')
          importFixed();assert(#imported==1 and imported[1].need==2)
          bag[10]=10;ns.ProfFollow.Paint();bag[10]=0;ns.ProfFollow.Paint()
          assert(task.complete and not ns.ProfFollow.f.npcQuest.shown)
          local purchases=ns.ProfFollow.GetPurchases(followState)
          assert(purchases[1].need+purchases[2].need==12)
        ''')

    def test_first_aid_and_poison_hud_always_use_fixed_steps(self):
        self.lua.execute('''
          settings.autoRoute=true;settings.autoScheme='cheapest'
          for _,slug in ipairs({'first-aid','poisons'}) do
            ns.ProfLeveling[slug]={steps={{1,50,101,49}}}
            local mode,steps=ns.ProfFollow.GetRoute(slug,1)
            assert(mode=='fixed' and #steps==1,'automatic route bypassed fixed-only profession')
          end
        ''')


if __name__ == '__main__':
    unittest.main()
