"""Native HUD voice integration: real execution transitions, recorded widgets/audio."""
import unittest
import test_prof_ui_fusion as ui
from test_prof_issue4 import WIDGETS

ROOT = ui.ROOT


class HUDVoiceTests(unittest.TestCase):
    boot = ui.ProfessionUIFusionTests.boot

    def setUp(self):
        self.boot('zhCN')
        self.lua.execute(WIDGETS)
        self.lua.execute(r'''
          sounds={};messages={};SlashCmdList={};knownRecipe=true
          PlaySoundFile=function(path,channel)sounds[#sounds+1]={path=path,channel=channel}end
          DEFAULT_CHAT_FRAME={AddMessage=function(_,message)messages[#messages+1]=message end}
          C_Spell={IsSpellKnown=function()return knownRecipe end}
          local base=recordedWidget
          function recordedWidget(...)
            local w=base(...)
            function w:Hide()
              local shown=self.visible;self.visible=false
              if shown and self.scripts.OnHide then self.scripts.OnHide(self)end
            end
            function w:GetTextColor()return 0.7,0.7,0.7,1 end
            function w:GetFontString()return self end
            function w:SetVertexColor(...)self.color={...}end
            return w
          end
          CreateFrame=recordedWidget
          ns.ProfHost.MakeFS=recordedWidget;ns.ProfHost.NewButton=recordedWidget
          ns.ProfHost.SetButtonSelected=function(w,on)w.selected=on end
          ns.ProfHost.DG.ItemIcon=function()return '?'end
          ns.ProfHost.DG.ItemLink=function(id)return 'Item'..tostring(id)end
          rankTasks={};ns.ProfRanks={NextStep=function(slug)return rankTasks[slug]end}
          DungeonsForeverDB.prof.lvTarget.alchemy=300
          local rec=fixture().recipes[1];rec.learnSource='trainer'
          local first={1,2,101,1,segmentID='first',profession='alchemy',item=10,recipe=rec,
            goalSkill=2,expectedGain=1,expectedCrafts=1,attemptLimit=1,outputMin=1,requiredOutputs={}}
          local second=ns.ProfEconomy.Copy(first)
          second[1]=2;second[2]=4;second[4]=2;second.segmentID='second'
          second.goalSkill=4;second.expectedGain=2;second.expectedCrafts=2;second.attemptLimit=2
          xp=ns.ProfExecution
          run=assert(xp.Bind('alchemy',{planID='voice-plan',executionVersion=1,planVersion=2,
            start=1,target=4,feasible=true,status='complete',executionSteps={first,second},
            steps={first,second},mats={},formulas={},total=3}))
          follow={slug='alchemy',skill=1,step=1,t0=1000}
          DungeonsForeverDB.prof.follow={['Test-Realm']=follow}
          function advance()
            xp.RecordAttempt('alchemy',101,'first-cast')
            skills.alchemy.cur=2;xp.eventFrame.OnEvent(xp.eventFrame,'SKILL_LINES_CHANGED')
          end
          function capTask(slug,skill,cap)
            skills[slug]={cur=skill,max=cap}
            rankTasks[slug]={profession=slug,due=true,state={known=true,skill=skill,maxSkill=cap}}
          end
          function countSound(kind)
            local names={cap='prof_skill_cap',item='prof_next_item',on='prof_voice_on',nol='prof_not_learned'}
            local n=0;for _,sound in ipairs(sounds)do
              assert(sound.channel=='Master')
              if sound.path:find(names[kind]..'.ogg',1,true)then n=n+1 end
            end;return n
          end
        ''')
        self.load((ROOT / 'Core/ProfFollow.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          for _,fn in ipairs(callbacks)do fn()end;callbacks={}
          pf=ns.ProfFollow;pf.Build()
          for i=1,100 do
            if pf.f then break end
            local pending=timers;timers={};for _,fn in ipairs(pending)do fn()end
          end
          assert(pf.f,'native HUD construction failed')
          pf.f:Show();pf.Paint()
        ''')

    def test_first_paint_and_manual_card_browsing_do_not_announce_next_item(self):
        self.lua.execute('''
          assert(#sounds==0)
          pf.Skip();pf.Prev();pf.Paint();assert(#sounds==0)
          assert(run.currentIndex==1 and follow.step==1)
        ''')

    def test_actual_execution_advance_announces_once_across_repaints(self):
        self.lua.execute('''
          advance();assert(run.currentIndex==2)
          assert(countSound('item')==1)
          for i=1,5 do pf.Sync();pf.Paint()end
          assert(#sounds==1)
        ''')

    def test_material_obligation_keeps_the_current_step_even_after_skill_gain(self):
        self.lua.execute('''
          run.plan.executionSteps[1].requiredOutputs={[10]=1}
          advance();assert(run.currentIndex==1 and #sounds==0)
          bag[10]=1;xp.eventFrame.OnEvent(xp.eventFrame,'BAG_UPDATE_DELAYED')
          assert(run.currentIndex==2 and countSound('item')==1)
        ''')

    def test_new_execution_and_candidate_publication_do_not_announce_next_item(self):
        self.lua.execute('''
          advance();sounds={}
          local plan=ns.ProfEconomy.Copy(run.plan)
          plan.planID='replacement';run=assert(xp.StartNew('alchemy',plan))
          pf.InvalidateRoute();pf.Sync();pf.Paint();assert(#sounds==0)
          ns.ProfRouteAuto.Invalidate('prices');pf.RefreshRoute('alchemy');assert(#sounds==0)
        ''')

    def test_manual_navigation_step_is_not_announced_as_a_recipe(self):
        self.lua.execute('''
          run.plan.executionSteps[2].navigationOnly=true
          advance();assert(run.currentIndex==2 and #sounds==0)
        ''')

    def test_rank_reminder_does_not_speak_until_the_real_cap_is_reached(self):
        self.lua.execute('''
          capTask('alchemy',50,75);pf.Paint();assert(#sounds==0)
          capTask('alchemy',75,75);pf.Paint();pf.Paint()
          assert(countSound('cap')==1)
          capTask('alchemy',76,150);pf.Paint();assert(#sounds==1)
          capTask('alchemy',150,150);pf.Paint();assert(countSound('cap')==2)
        ''')

    def test_no_cap_warning_when_no_rank_upgrade_is_needed_or_cap_is_unknown(self):
        self.lua.execute('''
          skills.alchemy={cur=300,max=300};pf.Paint();assert(#sounds==0)
          rankTasks.alchemy={profession='alchemy',due=true,state={known=false,skill=75,maxSkill=75}}
          pf.Paint();assert(#sounds==0)
        ''')

    def test_partner_profession_cap_is_scoped_and_deduplicated(self):
        self.lua.execute('''
          run.plan.executionSteps[1].profession='enchanting'
          capTask('enchanting',75,75);pf.Paint();pf.Paint()
          assert(countSound('cap')==1)
          run.plan.executionSteps[1].profession='alchemy';pf.Paint()
          run.plan.executionSteps[1].profession='enchanting';pf.Paint()
          assert(countSound('cap')==2)
        ''')

    def test_changing_profession_resets_step_and_cap_identity(self):
        self.lua.execute('''
          capTask('alchemy',75,75);pf.Paint();assert(countSound('cap')==1)
          local plan=ns.ProfEconomy.Copy(run.plan);plan.planID='enchanting-voice'
          for _,seg in ipairs(plan.executionSteps)do seg.profession='enchanting';seg.goalSkill=100 end
          skills.enchanting={cur=75,max=75}
          assert(xp.Bind('enchanting',plan))
          follow.slug='enchanting';follow.step=1;follow.skill=75
          DungeonsForeverDB.prof.lvTarget.enchanting=300
          capTask('enchanting',75,75);pf.InvalidateRoute();pf.Paint()
          assert(countSound('cap')==2 and countSound('item')==0)
        ''')

    def test_cap_warning_takes_priority_over_next_item(self):
        self.lua.execute('''
          capTask('alchemy',2,2);advance();pf.Paint()
          assert(countSound('cap')==1 and countSound('item')==0)
        ''')

    def test_hidden_hud_does_not_play_or_replay_missed_transitions(self):
        self.lua.execute('''
          pf.f:Hide();advance();pf.Paint();assert(#sounds==0)
          pf.f:Show();pf.Paint();assert(#sounds==0)
        ''')

    def test_mute_button_persists_only_preference_and_does_not_queue_old_audio(self):
        self.lua.execute('''
          local button=pf.f.muteBtn
          assert(button and not button.selected)
          button.scripts.OnClick();assert(DungeonsForeverDB.prof.muteCue and button.selected)
          advance();capTask('alchemy',75,75);pf.Paint();assert(#sounds==0)
          SlashCmdList.DUNGEONSFOREVERVOICE('cap');assert(#sounds==0)
          button.scripts.OnClick();assert(not DungeonsForeverDB.prof.muteCue and not button.selected)
          assert(countSound('on')==1)
          pf.Paint();assert(#sounds==1)
          for key in pairs(DungeonsForeverDB.prof)do
            assert(not tostring(key):find('cueState',1,true))
          end
          assert(follow.__lastStep==nil and follow.__capSaid==nil)
        ''')

    def test_trial_commands_reuse_all_four_master_recordings(self):
        self.lua.execute('''
          assert(SLASH_DUNGEONSFOREVERVOICE1=='/dfvoice' and SLASH_DUNGEONSFOREVERVOICE2=='/df语音')
          for _,command in ipairs({'cap','下一件','3','未学'})do SlashCmdList.DUNGEONSFOREVERVOICE(command)end
          assert(#sounds==4)
          for _,kind in ipairs({'cap','item','on','nol'})do assert(countSound(kind)==1)end
          timers={};sounds={};SlashCmdList.DUNGEONSFOREVERVOICE('')
          assert(countSound('cap')==1 and #timers==1)
          timers[1]();assert(countSound('item')==1)
        ''')

    def test_clicking_unlearned_trainer_recipe_plays_reminder(self):
        self.lua.execute('''
          knownRecipe=false
          pf.f.card.scripts.OnMouseUp(pf.f.card,'LeftButton')
          assert(countSound('nol')==1)
          knownRecipe=true;pf.f.card.scripts.OnMouseUp(pf.f.card,'LeftButton')
          assert(countSound('nol')==1)
        ''')

    def test_formula_unknown_and_manual_steps_do_not_get_trainer_audio(self):
        self.lua.execute('''
          knownRecipe=false
          for _,source in ipairs({'item','quest','unknown'})do
            run.plan.executionSteps[1].recipe.learnSource=source
            pf.f.card.scripts.OnMouseUp(pf.f.card,'LeftButton')
          end
          run.plan.executionSteps[1].recipe.learnSource='trainer'
          run.plan.executionSteps[1].navigationOnly=true
          pf.f.card.scripts.OnMouseUp(pf.f.card,'LeftButton');assert(#sounds==0)
        ''')

    def test_audio_api_unavailable_or_throwing_does_not_break_hud_or_commands(self):
        self.lua.execute('''
          PlaySoundFile=nil;SlashCmdList.DUNGEONSFOREVERVOICE('cap')
          PlaySoundFile=function()error('client audio unavailable')end
          advance();pf.Paint();SlashCmdList.DUNGEONSFOREVERVOICE('nol')
          assert(#sounds==0 and run.currentIndex==2)
        ''')

    def test_mute_survives_module_reload_while_runtime_cue_state_does_not(self):
        self.lua.execute('DungeonsForeverDB.prof.muteCue=true;advance()')
        self.load((ROOT / 'Core/ProfFollow.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          pf=ns.ProfFollow;pf.Build()
          for i=1,100 do
            if pf.f then break end
            local pending=timers;timers={};for _,fn in ipairs(pending)do fn()end
          end
          pf.f:Show();pf.Paint()
          assert(pf.f.muteBtn.selected and #sounds==0)
        ''')


if __name__ == '__main__':
    unittest.main()
