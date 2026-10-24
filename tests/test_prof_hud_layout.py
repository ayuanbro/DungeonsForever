"""HUD layout using measured mock font metrics; no live client rendering claim."""
import unittest

import test_prof_specialization_ui_execution as specialization_fixture


METRICS = r'''
layoutFrames={}
local originalMakeFrame=makeFrame
function makeFrame()
 local f=originalMakeFrame()
 layoutFrames[#layoutFrames+1]=f
 function f:SetWordWrap(v) self.wordWrap=v end
 function f:SetJustifyH(v) self.justify=v end
 function f:GetStringWidth()
   local width=0
   for c in (self.text or ''):gmatch('[%z\1-\127\194-\244][\128-\191]*') do
     width=width+(self.fontSize or 14)*(#c>1 and 1 or 0.55)
   end
   return width
 end
 function f:GetStringHeight()
   local lines=1
   if self.wordWrap and self.width and self.width>0 then
     lines=math.max(1,math.ceil(self:GetStringWidth()/self.width))
   end
   return lines*(self.fontSize or 14)*1.15
 end
 return f
end
ns.ProfHost.MakeFS=function(parent,size)
 local f=makeFrame();f.parent=parent;f.fontSize=size;return f
end
ns.ProfModule.TextW=function(text,size)
 local f=makeFrame();f.text=text;f.fontSize=size;return f:GetStringWidth()
end
function showQuest()
 ns.ProfFollow.Sync();finishProduction();ns.ProfFollow.Sync()
 ns.ProfFollow.Build();ns.ProfFollow.f:Show();ns.ProfFollow.Paint()
 return ns.ProfFollow.f
end
function box(line,card)
 local p=assert(line.point)
 assert(p[2]==card and p[3]=='TOPLEFT' or p[2]==card and p[3]=='TOPRIGHT')
 local width=line.width or line:GetStringWidth()
 local x=p[4]
 if p[3]=='TOPRIGHT' then x=card.width+x end
 if p[1]=='TOPRIGHT' then x=x-width end
 local height=line:GetStringHeight()
 if not line.wordWrap then assert(width+0.01>=line:GetStringWidth(),'text was clipped') end
 assert(x>=8 and x+width<=card.width-8+0.01,'text escaped card width')
 assert(-p[5]+height<=card.height-6,'text escaped card height')
 return {left=x,right=x+width,top=-p[5],bottom=-p[5]+height}
end
function disjoint(a,b)
 return a.right<=b.left or b.right<=a.left or a.bottom<=b.top or b.bottom<=a.top
end
function assertCardLayout(f)
 local card=f.card
 local lines={card.name,card.range,card.srcTag,card.crafts}
 for _,line in ipairs(card.progress)do if line.shown then lines[#lines+1]=line end end
 local bounds={}
 for _,line in ipairs(lines)do bounds[#bounds+1]=box(line,card)end
 for i,a in ipairs(bounds)do
   for j=i+1,#bounds do assert(disjoint(a,bounds[j]),'HUD text overlapped')end
 end
 for _,line in ipairs(layoutFrames)do
   if line.parent==card and line.text and line.text:find('Item10',1,true) then
     local material=box(line,card)
     for _,a in ipairs(bounds)do assert(disjoint(a,material),'material covered quest text')end
   end
 end
end
'''


class HUDLayoutTests(unittest.TestCase):
    def setUp(self):
        specialization_fixture.SpecializationHUDTests.setUp(self)
        self.lua.execute(METRICS)

    def test_engineering_quest_reserves_separate_header_and_wrapped_details(self):
        self.lua.execute(r'''
          ns.ProfModule.StepRole=function()return '专精入门任务'end
          local goal=currentResult.executionSteps[2].quest
          goal.npcName='尼克斯·斯普克斯宾';goal.zone='塔纳利斯';goal.questName='工作成果'
          local f=showQuest();assertCardLayout(f)
          assert(f.card.srcTag.point[5]<f.card.name.point[5])
          assert(f.card.progress[1].wordWrap and f.card.progress[1]:GetStringHeight()>13*1.15)
          assert(f.card.matOffset>4*18)
        ''')

    def test_long_english_quest_names_and_prerequisites_expand_card(self):
        self.lua.execute(r'''
          ns.L['%s入门任务']='%s Specialization Introduction Quest'
          ns.L['地精工程学']='Goblin Engineering'
          ns.L['专精入门任务']='Engineering specialization introduction quest'
          ns.L['待完成']='Awaiting specialization training'
          ns.ProfModule.StepRole=function()return ns.L['专精入门任务']end
          local goal=currentResult.executionSteps[2].quest
          goal.npcName='Nixx Sprocketspring the Goblin Engineering Trainer'
          goal.zone='Tanaris, Gadgetzan';goal.questName='The Pledge of Secrecy and Show Your Work'
          goal.prerequisiteQuestIDs={3638,3635,3637,3526,3527,3528,3529}
          local f=showQuest();assertCardLayout(f)
          assert(f.card.name:GetStringHeight()>16*1.15)
          assert(f.card.srcTag:GetStringHeight()>14*1.15)
          assert(f.card.progress[3]:GetStringHeight()>13*1.15)
        ''')

    def test_reused_card_returns_to_compact_header_without_stale_offsets(self):
        self.lua.execute(r'''
          ns.ProfModule.StepRole=function()return '专精入门任务'end
          local f=showQuest();local questHeight=f.card.height
          ns.ProfFollow.view=-1;ns.ProfFollow.Paint()
          ns.ProfModule.StepRole=function()return 'L'end
          ns.L['已学习']='OK';ns.L['向训练师学习']='T'
          C_Spell.GetSpellInfo=function()return {name='Bolt'}end
          ns.ProfFollow.Paint();assertCardLayout(f)
          assert(f.card.srcTag.point[1]=='TOPRIGHT' and f.card.srcTag.justify=='RIGHT')
          assert(f.card.srcTag.point[5]==-9 and f.card.crafts.point[5]==-33)
          assert(not f.card.name.wordWrap and f.card.height<questHeight)
        ''')

    def test_missing_material_record_keeps_notice_inside_card(self):
        self.lua.execute(r'''
          local f=showQuest()
          local plan=ns.ProfExecution.GetPlan('engineering')
          plan.executionSteps[2].recipe.mats={}
          ns.ProfFollow.Paint();assertCardLayout(f)
          assert(f.card.matHead.shown)
          box(f.card.matHead,f.card)
        ''')

    def test_search_prefix_stays_preview_until_terminal_plan_is_available(self):
        self.lua.execute(r'''
          local full=questPlan()
          currentResult=questPlan();currentResult.status='searching';currentResult.partial=true
          currentResult.executionSteps={currentResult.executionSteps[1]}
          currentResult.steps=currentResult.executionSteps
          ns.ProfFollow.Sync()
          assert(ns.ProfExecution.GetRun('engineering')==nil,'search prefix froze execution')
          currentResult=full;currentResult.status='searching';ns.ProfFollow.Sync()
          assert(ns.ProfExecution.GetRun('engineering')==nil)
          assert(#select(2,ns.ProfFollow.GetRoute('engineering',200))==2)
          currentResult.status='complete';ns.ProfFollow.Sync()
          assert(#ns.ProfExecution.GetPlan('engineering').executionSteps==2)
        ''')

    def test_unfrozen_quest_preview_still_waits_for_actual_specialization(self):
        self.lua.execute(r'''
          currentResult.status='searching'
          currentResult.executionSteps={currentResult.executionSteps[2]}
          currentResult.steps=currentResult.executionSteps
          ns.ProfFollow.Sync()
          assert(followState.step==1 and not ns.ProfExecution.GetRun('engineering'))
          specialized=true;ns.ProfFollow.Sync();assert(followState.step==2)
        ''')


if __name__ == '__main__':
    unittest.main()
