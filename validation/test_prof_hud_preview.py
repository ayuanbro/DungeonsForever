import unittest
import test_prof_hud_voice as voice


class HUDPreviewTests(unittest.TestCase):
    boot=voice.HUDVoiceTests.boot
    setUp=voice.HUDVoiceTests.setUp

    def test_master_card_keeps_missing_current_step_without_future_recipe_panel(self):
        self.lua.execute('''
          local a=pf.f.card
          assert(a.visible and a.__step==1 and not pf.f.card2.visible)
          assert(a.__rowsMat[1].text:find('0/1',1,true))
          assert(a.chipLearn.lab.text==ns.L['已学'] and a.chipSrc.lab.text==ns.L['训练师'])
          assert(run.currentIndex==1 and #sounds==0)
        ''')

    def test_manual_browsing_and_last_step_show_one_card(self):
        self.lua.execute('''
          pf.Skip();assert(pf.f.card.__step==2 and run.currentIndex==1)
          pf.Prev();assert(pf.f.card.__step==1 and not pf.f.card2.visible)
          advance();assert(pf.f.card.__step==2 and not pf.f.card2.visible)
          assert(countSound('item')==1)
        ''')

    def test_manual_task_preview_has_no_crafting_action(self):
        self.lua.execute('''
          local next=run.plan.executionSteps[2]
          next.kind='specialization_quest';next[3]=0
          next.quest={questID=42,abilityID=99,inputs={{11,2}}}
          pf.InvalidateRoute();pf.Paint()
          assert(not pf.f.card2.visible)
          assert(pf.f.card.__step==1 and run.currentIndex==1 and #sounds==0)
          pf.Skip();assert(pf.f.card.__step==2 and pf.f.card.__spell==nil)
          assert(not pf.f.card.chipLearn.visible and run.currentIndex==1)
        ''')

    def overlapping_steps(self):
        self.lua.execute('''
          local next=run.plan.executionSteps[2]
          next[1]=1;next[3]=102
          next.recipe=ns.ProfEconomy.Copy(next.recipe)
          next.recipe.spell=102;next.recipe.item=12;next.item=12
          bag[11]=20
          pf.InvalidateRoute()
        ''')

    def test_overlapping_independent_craft_can_show_second_card_without_reordering(self):
        self.overlapping_steps()
        self.lua.execute('''
          local plan=run.plan;local id=run.planID
          local first,second=plan.executionSteps[1],plan.executionSteps[2]
          pf.Paint()
          assert(pf.f.card.__step==1 and pf.f.card2.visible and pf.f.card2.__step==2)
          assert(pf.f.card2.points[1][5]<pf.f.card.points[1][5])
          assert(run.plan==plan and run.planID==id and run.currentIndex==1 and follow.step==1)
          assert(first[4]==1 and second[4]==2 and #sounds==0)
          pf.Skip();assert(not pf.f.card2.visible and run.currentIndex==1)
          pf.Prev();assert(pf.f.card2.visible and run.currentIndex==1)
        ''')

    def test_second_card_requires_materials_left_after_current_step(self):
        self.overlapping_steps()
        self.lua.execute('''
          bag[11]=2;pf.Paint()
          assert(pf.f.card.visible and pf.f.card.__step==1 and not pf.f.card2.visible)
          bag[11]=0;pf.Paint()
          assert(pf.f.card.visible and not pf.f.card2.visible and run.currentIndex==1)
        ''')

    def test_adjacent_alchemy_ranges_do_not_become_permanent_preview(self):
        self.overlapping_steps()
        self.lua.execute('''
          local first,next=run.plan.executionSteps[1],run.plan.executionSteps[2]
          first[1]=1;first[2]=13;first.goalSkill=13
          next[1]=13;next[2]=20;next.goalSkill=20
          bag[11]=1000;pf.InvalidateRoute();pf.Paint()
          assert(pf.f.card.__step==1 and not pf.f.card2.visible and run.currentIndex==1)
        ''')

    def test_second_card_never_bypasses_material_allocation_or_output_dependency(self):
        self.overlapping_steps()
        self.lua.execute('''
          local first,next=run.plan.executionSteps[1],run.plan.executionSteps[2]
          first.allocations={{consumerID=next.segmentID,itemID=10,count=2}}
          pf.Paint();assert(not pf.f.card2.visible)
          first.allocations={};next.recipe.mats={{10,1}};bag[10]=20
          pf.Paint();assert(not pf.f.card2.visible and run.currentIndex==1)
        ''')

    def test_second_card_never_crosses_task_tool_conversion_or_profession_barrier(self):
        for barrier in ('task','tool','conversion','profession'):
            with self.subTest(barrier=barrier):
                self.setUp();self.overlapping_steps()
                self.lua.globals().barrier=barrier
                self.lua.execute('''
                  local first,next=run.plan.executionSteps[1],run.plan.executionSteps[2]
                  local middle=ns.ProfEconomy.Copy(first);middle.segmentID='barrier'
                  if barrier=='task' then middle.kind='specialization_quest';middle[3]=0
                    middle.quest={questID=42,abilityID=99,inputs={}}
                  elseif barrier=='tool' then middle.tool=true
                  elseif barrier=='conversion' then middle.kind='conversion';middle[3]=0
                  else middle.profession='engineering' end
                  run.plan.executionSteps={first,middle,next};run.plan.steps=run.plan.executionSteps
                  pf.InvalidateRoute();pf.Paint()
                  assert(pf.f.card.__step==1 and not pf.f.card2.visible and run.currentIndex==1)
                ''')


if __name__=='__main__':unittest.main()
