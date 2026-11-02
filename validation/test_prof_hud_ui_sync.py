"""HUD refresh and profession toolbar geometry against real Lua entry points.

Recorded anchors cover the supplied route/shop overlap; no game pixels are
asserted. Route selection, execution progress and specialization stay unchanged.
"""
import unittest
import test_prof_hud_voice as voice
import test_prof_ui_fusion as ui
from test_prof_issue4 import WIDGETS


class HUDStateSyncTests(unittest.TestCase):
    boot = ui.ProfessionUIFusionTests.boot
    setUp = voice.HUDVoiceTests.setUp

    def visible_page(self):
        self.lua.execute('''
          PD.built=true;PD.page=recordedWidget()
          PD.page.IsVisible=function()return true end
          renders=0;button=recordedWidget();pf.PaintButton(button,'alchemy')
          PD.RequestRender=function()
            renders=renders+1;pf.PaintButton(button,'alchemy')
          end
        ''')

    def test_close_and_reopen_refresh_button_without_advancing_execution(self):
        self.visible_page()
        self.lua.execute('''
          local planID=run.planID;local step=run.currentIndex
          assert(button.selected)
          pf.f.xBtn.scripts.OnClick()
          assert(not pf.f:IsShown() and not button.selected)
          assert(renders==1)
          pf.Toggle('alchemy')
          assert(pf.f:IsShown() and button.selected and renders==2)
          pf.Toggle('alchemy')
          assert(not pf.f:IsShown() and not button.selected and renders==3)
          assert(run.planID==planID and run.currentIndex==step and #sounds==0)
        ''')

    def test_async_build_cancel_and_completion_refresh_button(self):
        self.visible_page()
        self.lua.execute('''
          local frame=pf.f;pf.f=nil;pf.building=true
          pf.Toggle('alchemy')
          assert(follow.hidden and not button.selected and renders==1)
          pf.building=false
          pf.Build=function()pf.building=true end
          pf.Toggle('alchemy')
          assert(pf.onBuilt)
          pf.f=frame;pf.onBuilt()
          assert(button.selected and renders==2)
        ''')

    def test_hidden_or_unbuilt_page_does_not_request_render(self):
        self.visible_page()
        self.lua.execute('''
          PD.page.IsVisible=function()return false end
          pf.Toggle('alchemy');assert(renders==0)
          PD.page.IsVisible=function()return true end;PD.built=false
          pf.Toggle('alchemy');assert(renders==0)
        ''')

    def test_output_and_conversion_popup_share_font_styling(self):
        self.lua.execute('''
          StaticPopupDialogs={};styled=0;popups={}
          ns.SkinPopupFont=function(frame)styled=styled+1;frame.styled=true end
          StaticPopup_Show=function(key,_,__,data)
            local frame=recordedWidget();frame.editBox=recordedWidget();frame.data=data
            frame.editBox.HighlightText=function()end
            frame.editBox.SetFocus=function()end
            StaticPopupDialogs[key].OnShow(frame);popups[#popups+1]=frame
          end
          pf.f.verifyBtn.scripts.OnClick()
          assert(styled==1 and popups[1].styled and popups[1].editBox:GetText()=='0')
          xp.Progress=function()return {outputItem=10,index=1,manualConversion=true,remainingConversions=4}end
          pf.f.verifyBtn.scripts.OnClick()
          assert(styled==2 and popups[2].styled and popups[2].editBox:GetText()=='4')
          assert(run.attemptsDone==nil or run.attemptsDone==0)
        ''')


class ProfessionToolbarTests(unittest.TestCase):
    boot = ui.ProfessionUIFusionTests.boot

    def setUp(self):
        self.setup_locale('zhCN')

    def setup_locale(self, locale):
        self.boot(locale)
        self.lua.execute(WIDGETS)
        self.lua.execute(r'''
          function buttonWidget()
            local b=recordedWidget();b.font=recordedWidget()
            function b:GetFontString()return self.font end
            function b:HookScript(k,fn)self.scripts[k]=fn end
            return b
          end
          PD.page=recordedWidget();PD.scroll=recordedWidget();PD.listCard=recordedWidget()
          PD.divider=recordedWidget();PD.actDiv=recordedWidget()
          PD.toolBtns={};for i=1,PD.TOOL_MAX do PD.toolBtns[i]=buttonWidget()end
          PD.hudBtn=buttonWidget();PD.hudBtn:SetWidth(130);PD.hudBtn:Show()
          PD.JUMP_W=104;PD.jumpBtn=buttonWidget();PD.jumpBtn:SetSize(104,PD.TOOL_H)
          PD.jumpBtn:SetPoint('TOPRIGHT',PD.hudBtn,'TOPLEFT',-PD.TOOL_GAP,0)
          PD.SearchReserve=function()return 0 end
          PD.TextW=function(text)
            local width=0
            for c in tostring(text):gmatch('[%z\1-\127\194-\244][\128-\191]*')do
              width=width+(#c>1 and 14 or 7)
            end
            return width
          end
          PD.GlowBorder=function()end
          ns.ProfGates={GetChoiceSetting=function()return 'none'end,
            EffectiveChoice=function()return 'none'end,EngineeringChoice=function()return 'none'end}
          PD.cur='engineering';PD.tab='leveling';PD.RecalcNeeded=function()return false end
          PD.RoutePairContext=function()end;PD.warnNotes={}
          PD.PlanSupplyParts=function()end
          function checkLayout(page,width,yoff,jumpShown)
            PD.autoPage=page;PD.RIGHT_W=width;PD.jumpBtn:SetShown(jumpShown and page=='route')
            local list,handler=PD.LevelTool()
            local h=PD.PaintTool(list,handler,yoff)
            PD.Layout(yoff+h)
            local frames={};local eng
            for _,b in ipairs(PD.toolBtns)do if b:IsShown()then
              frames[#frames+1]=b;if b.__key=='eng_spec'then eng=b end
            end end
            for _,b in ipairs({PD.hudBtn,PD.jumpBtn})do if b:IsShown()then frames[#frames+1]=b end end
            assert(eng and eng.__ddArr:IsShown(),'engineering selector missing')
            local contentTop=-PD.scroll.points[1][5]
            local function position(b)
              local p=b.points[1]
              if p[2]==PD.hudBtn then
                local hp=PD.hudBtn.points[1]
                return hp[4]+p[4]-b:GetWidth(),-hp[5]-p[5]
              end
              return p[4],-p[5]
            end
            for i,a in ipairs(frames)do
              local ax,ay=position(a)
              assert(ay>=PD.BODY_TOP+yoff,'stale toolbar vertical offset')
              assert(ay+a:GetHeight()<=contentTop,'route content overlaps toolbar: '..tostring(a.__key))
              assert(ax>=PD.RIGHT_X and ax+a:GetWidth()<=PD.RIGHT_X+width,'button outside panel')
              for j=i+1,#frames do
                local b=frames[j];local bx,by=position(b)
                local hit=ax<bx+b:GetWidth() and bx<ax+a:GetWidth()
                  and ay<by+b:GetHeight() and by<ay+a:GetHeight()
                assert(not hit,'toolbar buttons overlap: '..tostring(a.__key)..' / '..tostring(b.__key))
              end
            end
            return eng
          end
        ''')

    def test_route_selector_wraps_without_overlap_in_three_locales(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            with self.subTest(locale=locale):
                self.setup_locale(locale)
                self.lua.execute('''
                  for _,width in ipairs({900,680,1020})do
                    checkLayout('route',width,76,false);checkLayout('route',width,76,true)
                  end
                ''')

    def test_shop_and_route_switch_keep_hud_and_jump_buttons_clear(self):
        self.lua.execute('''
          for _,width in ipairs({900,680,1020})do
            checkLayout('shop',width,76);checkLayout('route',width,76,true)
          end
        ''')

    def test_cached_toolbar_reanchors_when_summary_offset_changes(self):
        self.lua.execute('''
          checkLayout('route',900,0);checkLayout('route',900,76)
        ''')

    def test_sparse_reused_row_clears_later_text_regions(self):
        self.lua.execute('''
          local r=recordedRow();r.h1=nil;r.h3=nil;r.h2:Show();r.h4:Show();r.h6:Show()
          PD.WipeRow(r,true)
          assert(not r.h2:IsShown() and not r.h4:IsShown() and not r.h6:IsShown())
        ''')

    def test_heading_honors_custom_status_color_and_resets_on_reuse(self):
        self.lua.execute('''
          local r=recordedRow()
          r.c.SetTextColor=function(self,...)self.ink={...}end
          PD.BindRow(r,{kind='head',text='History',right='Active',rightColor={0.1,0.8,0.2}},24)
          assert(r.c.ink[1]==0.1 and r.c.ink[2]==0.8 and r.c.ink[3]==0.2)
          PD.BindRow(r,{kind='head',text='History',right='Archived'},24)
          assert(r.c.ink[1]==ns.ProfHost.C_GREY[1])
        ''')


if __name__ == '__main__':
    unittest.main()
