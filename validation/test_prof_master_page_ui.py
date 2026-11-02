"""Master profession-page presentation with current execution and purchasing.

Native Lua entry points generate rows, handle clicks and decide visibility;
recorded widgets check placement without claiming in-game pixel verification.
"""
import unittest
import test_prof_ui_fusion as ui
from test_prof_issue4 import WIDGETS


class MasterProfessionPageTests(unittest.TestCase):
    boot = ui.ProfessionUIFusionTests.boot

    def setUp(self):
        self.boot('zhCN')
        self.lua.execute(WIDGETS)

    def build_jump(self):
        source = (ui.ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        start = source.index('    PD.JUMP_W = 104')
        end = source.index('    coroutine.yield()', start)
        self.lua.execute('''
          PD.page=recordedWidget();PD.hudBtn=recordedWidget();PD.hudBtn:Show()
          local page,hudBtn,L=PD.page,PD.hudBtn,ns.L
          local function NewButton(parent,text,width,height,font)
            local b=recordedWidget(parent);b:SetSize(width,height);b:SetText(text);b.fontSize=font
            return b
          end
          local function SetButtonSelected()end
        ''' + source[start:end])
        self.lua.execute('''
          PD.scroll=recordedWidget();PD.scroll:SetHeight(200)
          PD.scroll.offset=0
          function PD.scroll:GetVerticalScroll()return self.offset end
          function PD.scroll:SetVerticalScroll(n)self.offset=n end
          PD.child=recordedWidget();PD.child:SetHeight(1000)
        ''')

    def test_jump_visibility_and_native_click_follow_real_execution_row(self):
        self.build_jump()
        self.lua.execute('''
          local b=PD.jumpBtn;local anchor=b.points[1]
          assert(b:GetWidth()==104 and b.fontSize==13 and not b:IsShown())
          assert(anchor[1]=='TOPRIGHT' and anchor[2]==PD.hudBtn and anchor[3]=='TOPLEFT')
          assert(anchor[4]==-PD.TOOL_GAP and anchor[5]==0)
          PD.curRows={};assert(not PD.UpdateJumpButton() and not b:IsShown())
          -- Frozen material obligation wins even when its skill range is old.
          skills.alchemy.cur=150
          PD.curRows={{lvstep=true,sbLo=100,sbHi=200,__gtop=0,__gh=48},
            {lvstep=true,trackCur=true,sbLo=1,sbHi=50,__gtop=500,__gh=48}}
          assert(PD.CurrentSegRow()==2 and PD.UpdateJumpButton() and b:IsShown())
          b.scripts.OnClick()
          assert(PD.scroll.offset==496 and PD.__scrollV==496)
          assert(PD.UpdateJumpButton() and not b:IsShown())
          PD.scroll.offset=0;PD.UpdateJumpButton();assert(b:IsShown())
          for _,page in ipairs({'shop','log','recovery'})do
            PD.autoPage=page;PD.UpdateJumpButton();assert(not b:IsShown())
          end
          PD.autoPage='route';PD.setOpen=true;PD.UpdateJumpButton();assert(not b:IsShown())
          PD.setOpen=false;PD.exclusionsOpen=true;PD.UpdateJumpButton();assert(not b:IsShown())
          PD.exclusionsOpen=false;PD.curRows={};PD.UpdateJumpButton();assert(not b:IsShown())
        ''')

    def test_render_updates_visibility_and_reflows_only_when_button_changes(self):
        self.build_jump()
        self.lua.execute('''
          PD.built=true;PD.LV_TILE_H=64;PD.rows={};PD.page:Show()
          for _,name in ipairs({'PickNav','PickTabs','PlaceSettingsToggles','RequestRows',
            'WarmNames','PaintToolProgress','PaintToolStale','UpdateVScroll'})do PD[name]=function()end end
          PD.PaintLvTiles=function()return 72 end
          local row={lvstep=true,trackCur=true,sbLo=1,sbHi=3,__gtop=500,__gh=48}
          PD.RowsLeveling=function(rows)if PD.autoPage=='route' then rows[1]=row end end
          PD.PaintRows=function(rows)PD.curRows=rows end
          local layouts=0
          PD.PaintTool=function()return PD.jumpBtn:IsShown() and 64 or 32 end
          PD.Layout=function()layouts=layouts+1 end
          PD.Render();assert(PD.jumpBtn:IsShown() and layouts==2)
          PD.Render();assert(PD.jumpBtn:IsShown() and layouts==3)
          PD.__scrollV=496;PD.Render();assert(not PD.jumpBtn:IsShown() and layouts==5)
          PD.__scrollV=0;PD.Render();assert(PD.jumpBtn:IsShown())
          PD.autoPage='shop';PD.Render();assert(not PD.jumpBtn:IsShown())
          PD.autoPage='route';row.trackCur=nil;skills.alchemy.cur=100
          PD.Render();assert(not PD.jumpBtn:IsShown(),'empty current-step lookup left a jump button')
        ''')

    def test_shopping_header_import_uses_current_profession_and_keeps_grouping(self):
        self.lua.execute('''
          PD.Wrap=function(text)return {text}end;PD.autoPage='shop'
          assert(PD.shopGroup==false);PD.shopGroup=true
          local imported,groups=nil,0
          ns.ProfFollow={ImportShoppingList=function(slug)imported=slug end}
          local group=PD.PushTripGroups
          PD.PushTripGroups=function(rows,data)groups=groups+1;return group(rows,data)end
          local data={mode='auto',planVersion=2,status='complete',feasible=true,targetReached=true,
            completeCost=true,total=14,ahTotal=14,considerAuctionSupply=false,
            mats={{id=11,count=2,cost=14,unit=7,source='ah',considerAuctionSupply=false}}}
          local rows={};PD.RowsAutoShop(rows,data)
          local head=rows[1]
          assert(head.kind=='head' and head.noHover and groups==1)
          assert(#head.segs==2)
          local importKey,imports,groupToggle=nil,0,false
          for _,entry in ipairs(head.segs)do
            if entry.key=='import_list' then importKey=entry.key;imports=imports+1 end
            if entry.key=='shop_group' then groupToggle=true end
            assert(not entry.key:find('procure_',1,true))
          end
          assert(imports==1 and groupToggle)
          local list,click=PD.LevelTool()
          for _,button in ipairs(list)do
            assert(button.key~='import_list' and button.key~='jump_current' and button.key~='shop_group')
          end
          click(importKey)
          assert(imported=='alchemy' and PD.shopGroup==true)
          PD.cur='enchanting';click(importKey);assert(imported=='enchanting')
          assert(PD.impBtn==nil)
        ''')

    def test_native_archived_summary_and_status_colors_keep_execution_facts(self):
        for state, color in (('completed', (.49,.82,.63)), ('stale', (.90,.74,.36)),
                             ('cancel', (.90,.50,.50))):
            with self.subTest(state=state):
                self.setUp()
                self.lua.globals().caseState=state
                self.lua.globals().expectedColor=self.lua.table_from(color)
                self.lua.execute('''
                  local plan=finish('alchemy',{snapshot=fixture(),start=1,target=3})
                  local xp=ns.ProfExecution
                  local run=assert(xp.StartNew('alchemy',plan))
                  xp.RecordAttempt('alchemy',101,'master-log')
                  xp.RecordOutput({itemID=10,quantity=1,castGUID='master-log'})
                  if caseState=='stale' then run.plan.stale=true;run.plan.staleReason='skill' end
                  xp.End('alchemy',caseState=='completed' and 'completed' or 'cancel')
                  assert(run.status=='archived')
                  local summary=xp.GetSummary('alchemy',run.planID)
                  assert(summary.casts==1 and summary.planned==2)
                  if caseState=='stale' then assert(summary.stale) end
                  local rows={};PD.RowsCraftLog(rows)
                  local head=rows[1]
                  assert(head.kind=='head' and head.subFs==12)
                  assert(head.right:find('1/2',1,true))
                  local rendered=recordedRow();PD.BindRow(rendered,head,24)
                  assert(rendered.c:GetText()==head.right and rendered.c.font[2]==12)
                  assert(rendered.c.points[1][1]=='RIGHT')
                  local card
                  for _,row in ipairs(rows)do if row.kind=='exgrid' then
                    for _,entry in ipairs(row.cards)do if not entry.it then card=entry end end
                  end end
                  assert(card and card.name==format(ns.L['%d 步 · %s→%s'],summary.total,
                    tostring(summary.startSkill),tostring(summary.target)))
                  for i=1,3 do assert(card.color[i]==expectedColor[i]) end
                  -- The archived source remains protected by continuation.
                  assert(not xp.CanRemove('alchemy',run.planID))
                  card.act(nil,'RightButton');assert(xp.Get('alchemy',run.planID)==run)
                ''')


if __name__ == '__main__':
    unittest.main()
