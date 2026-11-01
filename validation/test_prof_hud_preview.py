import unittest
import test_prof_hud_voice as voice


class HUDPreviewTests(unittest.TestCase):
    boot=voice.HUDVoiceTests.boot
    setUp=voice.HUDVoiceTests.setUp

    def test_preview_keeps_missing_current_step_and_uses_separate_material_widgets(self):
        self.lua.execute('''
          local a,b=pf.f.card,pf.f.card2
          assert(a.visible and b.visible and a.__step==1 and b.__step==2)
          assert(a.__rowsMat~=b.__rowsMat and a.__rowsMat[1]~=b.__rowsMat[1])
          assert(a.__rowsMat[1].text:find('0/1',1,true))
          assert(b.__rowsMat[1].text:find('0/2',1,true))
          assert(b.srcTag.text:find('下一步预览',1,true))
          assert(run.currentIndex==1 and #sounds==0)
        ''')

    def test_manual_browsing_and_last_step_show_one_card(self):
        self.lua.execute('''
          pf.Skip();assert(not pf.f.card2.visible and run.currentIndex==1)
          pf.Prev();assert(pf.f.card2.visible)
          advance();assert(pf.f.card.__step==2 and not pf.f.card2.visible)
          assert(countSound('item')==1)
        ''')

    def test_manual_task_preview_has_no_crafting_action(self):
        self.lua.execute('''
          local next=run.plan.executionSteps[2]
          next.kind='specialization_quest';next[3]=0
          next.quest={questID=42,abilityID=99,inputs={{11,2}}}
          pf.InvalidateRoute();pf.Paint()
          assert(pf.f.card2.visible and pf.f.card2.__spell==nil)
          assert(pf.f.card.__step==1 and run.currentIndex==1 and #sounds==0)
        ''')


if __name__=='__main__':unittest.main()
