"""Master HUD geometry with real execution/shopping logic, using offline widgets."""
import unittest
import test_prof_ui_fusion as ui
import test_prof_hud_voice as voice


class MasterHUDLayoutTests(unittest.TestCase):
    def boot(self, locale):
        ui.ProfessionUIFusionTests.boot(self, getattr(self,'test_locale',locale))
        self.lua.execute('''
          ns.huiTheme='hui'
          ns.hui.layer={L0={.10,.11,.12},L1={.20,.21,.22},L2={.30,.31,.32},L3={.40,.41,.42}}
          ns.hui.BuildRoundedBG=function(frame,radius,color)
            frame.roundedBackground={radius=radius,color=color};return {}
          end
          ns.hui.SkinShadow=function(frame,...)frame.shadow={...}end
        ''')

    setUp = voice.HUDVoiceTests.setUp

    def test_master_material_layers_and_card_controls(self):
        self.lua.execute('''
          assert(pf.f.width==375 and pf.f.roundedBackground.radius==6)
          assert(pf.f.roundedBackground.color[1]==.10 and pf.f.roundedBackground.color[4]==.95)
          assert(pf.f.card.roundedBackground.color[1]==.20 and pf.f.shop.roundedBackground.color[1]==.20)
          assert(pf.f.shadow[1]==16 and pf.f.shadow[2]==.55 and pf.f.shadow[3]==6)
          assert(pf.f.verifyBtn.parent==pf.f.card and pf.f.nowBtn.parent==pf.f.card)
          assert(pf.f.verifyBtn.points[1][2]==pf.f.card and pf.f.verifyBtn.points[1][5]==-30)
          assert(#pf.f.btns==3 and pf.f.craftBtn==nil and pf.f.vendorShop==nil and pf.f.shopProc==nil)
          assert(pf.f.card.points[1][5]==-82 and not pf.f.card2.visible)
        ''')

    def test_long_purchase_details_never_widen_hud(self):
        self.lua.execute('''
          local full=string.rep('LONG PURCHASE DETAIL ',80)
          pf.ShoppingSourceText=function()return full end
          pf.ShoppingSourceDetail=function()return full end
          run.plan.executionSteps[1].recipe.mats={{11,175}}
          run.plan.mats={{id=11,count=175,source='ah',vendor=true,npcID=9,unit=3,cost=525}}
          ns.AuctionBridge={GetAuctionSupply=function()return {quantity=175}end}
          pf.InvalidateRoute();pf.showShop=true
          for i=1,4 do pf.Paint() end
          assert(pf.f.width==375 and pf.f.shop.width==351 and pf.wide==nil)
          assert(pf.f.card.width==351 and run.currentIndex==1 and run.plan.mats[1].count==175)
          assert(pf.ProcureStart==nil and pf.f.shopProc==nil)
          pf.showShop=false;pf.Paint();assert(pf.f.width==375 and not pf.f.shop.visible)
        ''')

    def test_current_target_and_output_counts_are_visible(self):
        self.lua.execute('''
          assert(pf.f.skill.text:find('1',1,true) and pf.f.skill.text:find('2',1,true))
          assert(pf.f.card.crafts.text:find('/已生产',1,true))
          assert(pf.f.card.crafts.text:find('/可制造',1,true))
          assert(pf.f.card.chipLearn.visible and pf.f.card.chipSrc.visible)
          assert(pf.f.card.chipLearn.lab.text==ns.L['已学'])
          assert(pf.f.card.chipSrc.lab.text==ns.L['训练师'])
        ''')

    def test_navigation_and_return_preserve_frozen_execution(self):
        self.lua.execute('''
          pf.Skip();assert(pf.f.card.__step==2 and run.currentIndex==1)
          assert(pf.f.nowBtn.visible and pf.f.nowBtn.points[1][2]==pf.f.card)
          assert(pf.f.nowBtn.points[1][5]==-59)
          pf.f.nowBtn.scripts.OnClick();assert(pf.f.card.__step==1 and run.currentIndex==1)
          assert(pf.f.width==375 and #sounds==0)
        ''')

    def test_unlearned_combat_and_expiry_status_are_visible_and_recover_in_three_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                self.test_locale=locale;self.setUp()
                self.lua.execute('''
                  local learned=PD.ProfLearned
                  local oldProgress=xp.Progress
                  PD.ProfLearned=function()return{}end;pf.Paint()
                  assert(not pf.f.skill.visible and pf.f.noLearn.visible)
                  xp.Progress=function()error('status paint accessed execution progress')end
                  xp.IsCombatPaused=function()return true end;pf.Paint()
                  assert(pf.f.skill.visible and not pf.f.noLearn.visible and not pf.f.seg.visible)
                  assert(pf.f.skill.width==355 and pf.f.skill.text==ns.L['战斗中暂停追踪'])
                  assert(pf.f.rankHint.statusDetail==ns.L['战斗中暂停追踪，脱战后自动恢复。'])
                  assert(not pf.f.capWarn.visible and pf.f.rankHint.visible)
                  xp.IsCombatPaused=function()return false end;follow.autoTrackSuspended='inactive';pf.Paint()
                  assert(pf.f.skill.visible and pf.f.skill.text==ns.L['追踪已自动结束'])
                  assert(pf.f.rankHint.statusDetail==ns.L['48 小时无制作，追踪已自动结束。'])
                  follow.autoTrackSuspended=nil;xp.Progress=oldProgress;pf.Paint()
                  assert(not pf.f.skill.visible and pf.f.noLearn.visible and pf.f.seg.visible)
                  assert(pf.f.rankHint.statusTitle==nil)
                  PD.ProfLearned=learned;pf.Paint()
                  assert(pf.f.skill.visible and not pf.f.noLearn.visible and pf.f.skill.width<355)
                  assert(run.currentIndex==1 and #sounds==0)
                ''')

    def shopping_widgets(self):
        self.lua.execute('''
          function paintUpvalue(wanted)
            for i=1,100 do local name,value=debug.getupvalue(pf.Paint,i)
              if name==wanted then return value end
              if not name then break end
            end
            error('missing paint widget '..wanted)
          end
          tips={};GameTooltip={SetOwner=function()end,ClearLines=function()tips={}end,
            AddLine=function(_,text)tips[#tips+1]=text end,Show=function()end,Hide=function()end}
          ns.ProfHost.DG.ItemName=function()return 'Very long material name that needs abbreviation',true end
          ns.ProfVendorNames={[9]='A Very Long Named Merchant'}
          ns.ProfVendors={[9]={map=42,x=12,y=34}}
          PD.MarkVendorLoc=function(loc)marked=loc end
          run.plan.executionSteps[1].recipe.mats={{11,175}}
          run.plan.mats={{id=11,count=175,source='vendor',npcID=9,unit=3,cost=525,unlimited=true}}
          pf.InvalidateRoute();pf.showShop=true;pf.Paint()
          names=paintUpvalue('rowsShop');missing=paintUpvalue('rowsShopMissPill')
          sources=paintUpvalue('rowsShopSrcPill')
        ''')

    def test_shopping_long_names_use_master_ellipsis_and_vendor_hint_keeps_details(self):
        self.shopping_widgets()
        self.lua.execute('''
          assert(names[1].text:find('…',1,true) and sources[1].fs.text:find('…',1,true))
          assert(sources[1].__row.srcFull=='A Very Long Named Merchant')
          sources[1].scripts.OnEnter(sources[1])
          assert(tips[1]=='A Very Long Named Merchant')
          assert(tips[2]==ns.L['点击在地图上标出该商人'])
          assert(tips[3]:find('175',1,true))
          sources[1].scripts.OnMouseUp(sources[1],'LeftButton')
          assert(marked==ns.ProfVendors[9])
          ns.ProfVendors={};sources[1].scripts.OnEnter(sources[1])
          assert(tips[2]==ns.L['该商人的位置暂未收录'])
          assert(pf.f.width==375 and run.currentIndex==1)
        ''')

    def test_large_missing_badge_is_measured_instead_of_clamped(self):
        self.shopping_widgets()
        self.lua.execute('''
          run.plan.executionSteps[1].recipe.mats={{11,100000}}
          run.plan.mats[1].count=100000;pf.InvalidateRoute();pf.Paint()
          assert(missing[1].width>56)
          assert(missing[1].width>=PD.TextW(missing[1].fs.text,14)+10)
          assert(pf.f.width==375 and run.currentIndex==1)
        ''')

    def test_short_pattern_badge_preserves_exact_acquisition_in_tooltip(self):
        self.lua.execute('''
          local full='Teaching item owned'
          PD.LevelSrc=function()return full,'No purchase is needed','owned'end
          pf.Paint()
          assert(pf.f.card.chipSrc.lab.text==ns.L['图纸'])
          tips={};GameTooltip={SetOwner=function()end,ClearLines=function()tips={}end,
            AddLine=function(_,text)tips[#tips+1]=text end,Show=function()end,Hide=function()end}
          pf.f.card.chipSrc.scripts.OnEnter(pf.f.card.chipSrc)
          assert(tips[1]==full and tips[2]=='No purchase is needed')
        ''')


if __name__ == '__main__':unittest.main()
