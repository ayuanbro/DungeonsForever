"""Load the complete native profession page and exercise its row entry points.

Widget/measurement stubs validate Lua integration; they do not assert in-game
appearance, pixel layout, or compatibility of a real client event payload.
"""
import unittest
import test_prof_route_plans as fixtures
ROOT=fixtures.ROOT


UI_MOCKS=r'''
format=string.format
function widget()
 return setmetatable({},{__index=function(t,k)
  if k=='GetStringWidth' then return function()return 60 end end
  return function()return widget()end
 end})
end
UIParent=widget();GameTooltip=widget()
ns.hui={CharStep=function(s,i)return i+1 end,TextW=function(s)return #tostring(s)*6 end}
ns.ProfData={pro={alchemy={name='Alchemy',kind='primary'},mining={name='Mining',kind='primary'},
 ['first-aid']={name='First Aid'},enchanting={name='Enchanting',kind='primary'}},order={'alchemy'}}
ns.ProfLeveling={alchemy={steps={{1,3,101,2}}},['first-aid']={steps={{1,3,101,2}}},mining={steps={{1,3,101,2}}}}
ns.ProfRecipes={alchemy={rows={{101,10,1,'','','',1,100,200,300,false,{{11,1}}}}}}
ns.ProfHost={DG={GUTTER=8,ItemName=function(id)return 'Item'..tostring(id),true end,RequestItem=function()end,
 Q_BADGE_MID_BG={},Q_BADGE_SHARE_BG={},Q_BADGE_PRE_BG={},Q_BADGE_BUY_BG={}},
 MakeFS=widget,NewButton=widget,SetOutline=function()end,SetButtonSelected=function()end,
 Unpack=unpack,CONTENT_W=900,PAGE_INSET=8,ROW_CLASS={},FALLBACK_ICON='?',
 C_GOLD={1,1,1},C_GREY={1,1,1},C_DIM={1,1,1},C_WHITE={1,1,1},C_TEXT={1,1,1}}
ns.OpenPerf={Mark=function()end};ns.PlaySound=function()end
'''


class ProfessionUIFusionTests(unittest.TestCase):
    def setUp(self):
        self.boot('zhCN')

    def test_route_progress_callbacks_paint_fraction_and_scope_to_current_profession(self):
        self.lua.execute('''
          for _,fn in ipairs(callbacks)do fn()end;callbacks={}
          PD.built=true;PD.page=widget();ns.PageVisible=function()return true end
          painted={};PD.PaintToolProgress=function(text,fraction)
            painted[#painted+1]={text=text,fraction=fraction}
          end
          local ra=ns.ProfRouteAuto;local sr=ns.ProfSolverRun
          ra.Get('alchemy',{snapshot=fixture(),start=1,target=300})
          local job=sr.Active('alchemy').job
          assert(PD.SolverText()==ns.L['正在准备数据'] and PD.solverFrac>0)
          -- Exercise the real facade dispatcher with controlled search slices.
          ns.ProfRouteSolver.Run=function(j)
            j.progressVersion=(j.progressVersion or 0)+1
            return false
          end
          job.snap={};job.seedSkill=94;ra.Pump('alchemy')
          local p=painted[#painted]
          assert(p.text==format(ns.L['正在推演 %d/%d'],94,300))
          assert(type(p.fraction)=='number' and p.fraction>0 and p.fraction<1)
          job.seedDone=true;job.cpuUsed=3440;ra.Pump('alchemy')
          p=painted[#painted]
          assert(p.text==format(ns.L['正在优化 %d%%'],43) and p.fraction>0)
          job.finalizing=true;ra.Pump('alchemy')
          assert(painted[#painted].text==ns.L['正在整理计算结果…'])
          ra.Cancel('alchemy');assert(PD.SolverText()==nil and PD.solverFrac==nil)
          ra.Continue('alchemy');PD.cur='enchanting'
          assert(PD.SolverText()==nil and PD.solverFrac==nil)
          PD.cur='alchemy';PD.tab='recipe';assert(PD.SolverText()==nil)
        ''')

    def test_legacy_precision_setting_does_not_change_new_route_budget(self):
        self.lua.execute('''
          for _,value in ipairs({false,true}) do
            DungeonsForeverDB.prof.solverRoute=value
            assert(PD.BuildLvOpts('alchemy',1).cpuLimitMs==8000)
          end
          local _,click=PD.LevelTool();click('recalc');PD.RowsLeveling({})
          local job=ns.ProfSolverRun.Active('alchemy').job
          assert(job.cpuLimitMs==8000)
        ''')

    def test_progress_bar_uses_screenshot_geometry_and_hides_when_finished(self):
        self.lua.execute('''
          local function frame()
            local f={shown=false}
            function f:SetSize(w,h)self.w=w;self.h=h end
            function f:GetWidth()return self.w end
            function f:GetFrameLevel()return 1 end
            function f:SetFrameLevel()end
            function f:SetPoint()end;function f:ClearAllPoints()end
            function f:SetAllPoints()end;function f:SetColorTexture()end
            function f:Show()self.shown=true end;function f:Hide()self.shown=false end
            function f:IsShown()return self.shown end
            function f:CreateTexture()return frame()end
            return f
          end
          CreateFrame=frame;PD.page=frame();PD.setGear=frame()
          PD.PaintToolProgress('Progress',0.43)
          assert(PD.__progBar.w==150 and PD.__progBar.h==6)
          assert(PD.__progFill.w==64 and PD.__progBar:IsShown())
          PD.PaintToolProgress(nil,nil)
          assert(not PD.__progHolder:IsShown() and not PD.__progBar:IsShown())
        ''')

    def boot(self,locale):
        fixtures.NativeRoutePlansTests.setUp(self)
        self.lua.execute("GetLocale=function()return '"+locale+"'end")
        self.load((ROOT/'Locales/zhCN.lua').read_text(encoding='utf-8-sig'))
        if locale!='zhCN':self.load((ROOT/'Locales'/(locale+'.lua')).read_text(encoding='utf-8-sig'))
        self.lua.execute(UI_MOCKS)
        self.load((ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          PD=ns.ProfModule;PD.cur='alchemy';PD.tab='leveling'
          PD.WindowShown=function()return true end
          PD.ProfLearned=function()return skills end
          PD.CardOf=function()end;PD.PriceTipLines=function()return{}end
          PD.Fit=function(text)return text end;PD.RequestRender=function()end
          PD.ItemName=function(id)return 'Item'..tostring(id),true end
          DungeonsForeverDB.prof.autoRoute=true
          -- Preserve stock-aware scenarios; default-off behavior has its own suite.
          DungeonsForeverDB.prof.autoConsiderAuctionSupply=true
          DungeonsForeverDB.prof.lvTarget={alchemy=3,['first-aid']=3,mining=3}
          ns.ProfEconomy.Capture=function(slug)
            local s=fixture()
            if slug~='alchemy' then
              s.recipes[1].profession=slug;s.professions={[slug]={cur=1,max=300}}
              s.known={[slug..':101']=true}
            end
            return ns.ProfEconomy.Index(s)
          end
        ''')

    def test_pending_page_and_completed_route_use_the_same_facade(self):
        self.lua.execute('''
          local rows={};PD.RowsLeveling(rows)
          assert(PD.autoSnapshot and PD.autoSnapshot.status=='searching')
          local options=ns.ProfRouteAuto.OptionsFor('alchemy',1);options.target=3
          finish('alchemy',options)
          rows={};PD.RowsLeveling(rows)
          local found=false;for _,row in ipairs(rows)do if row.lvstep then found=true end end
          assert(found and PD.autoSnapshot.total==14)
          assert(PD.lvSummary.planVersion==2 and PD.lvSummary.auto)
        ''')

    def test_first_aid_fixed_and_mining_smelt_policy_are_preserved(self):
        self.lua.execute('''
          PD.cur='first-aid';PD.RowsLeveling({})
          assert(not ns.ProfRouteAuto.HasWork('first-aid'),'first aid started automatic planning')
          assert(PD.autoSnapshot.mode=='fixed' and not PD.lvSummary.auto)
          PD.cur='mining';DungeonsForeverDB.prof.gatherMode='smelt'
          PD.RowsLeveling({})
          assert(not ns.ProfRouteAuto.HasWork('mining'),'smelt enabled automatic planning')
        ''')

    def test_frozen_execution_rows_include_material_only_steps(self):
        self.lua.execute('''
          local options=ns.ProfRouteAuto.OptionsFor('alchemy',1);options.target=3
          local result=finish('alchemy',options)
          assert(ns.ProfExecution.Bind('alchemy',result))
          PD.RowsLeveling({})
          assert(PD.autoSnapshot==ns.ProfExecution.GetPlan('alchemy'))
          assert(#PD.autoSnapshot.executionSteps>0)
        ''')

    def test_three_locale_entry_and_new_route_messages(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                self.boot(locale)
                self.lua.execute('''
                  PD.RowsLeveling({})
                  local options=ns.ProfRouteAuto.OptionsFor('alchemy',1);options.target=3
                  finish('alchemy',options);PD.RowsLeveling({})
                  assert(PD.lvSummary.planVersion==2)
                  if GetLocale()~='zhCN' then
                    for _,key in ipairs({'专业晋级','精华转换','确认转换','手动转换',
                      '填写本次已完成的精华转换次数。','已知输入模型内最优；配方覆盖未确认'}) do
                      assert(rawget(ns.L,key),key)
                    end
                  end
                  local text=PD.StepName({0,0,0,1,kind='essence_conversion',item=10938,
                    conversion={inputItemID=10939,outputItemID=10938}})
                  assert(text:find('Item10939',1,true) and text:find('Item10938',1,true))
                ''')

    def test_profession_files_boot_in_the_actual_main_toc_order(self):
        lua=fixtures.LuaRuntime(unpack_returned_tuples=True)
        lua.execute(fixtures.MOCKS)
        lua.execute(UI_MOCKS)
        load=lua.eval("function(source)assert(loadstring(source))('DungeonsForever',ns)end")
        expected=['ProfPolicies','ProfRouteAuto','ProfessionUI','AuctionatorBridge','ProfFollow',
            'ProfTrack','ProfSupply','ProfSourceMerge','ProfGates','ProfRecovery','VendorPriceDB',
            'ProfEssences','ProfSolverCapture','ProfLearning','ProfClientScan','ProfRanks','ProfRouteSolver','ProfFishing','ProfGathering',
            'ProfExecution','ProfSolverRun','ProfRoutePlans']
        loaded=[]
        for line in (ROOT/'DungeonsForever.toc').read_text(encoding='utf-8-sig').splitlines():
            path=line.split(' [',1)[0].replace('\\','/')
            name=path.rsplit('/',1)[-1].removesuffix('.lua')
            if path.startswith('Core/') and name in expected:
                load((ROOT/path).read_text(encoding='utf-8-sig'));loaded.append(name)
        self.assertEqual(loaded,expected)
        lua.execute('''
          ns.ProfModule.ProfLearned=function()return skills end
          for _,fn in ipairs(callbacks)do fn()end
          assert(ns.ProfExecution and ns.ProfRouteAuto.OnPlanChanged)
          assert(not ns.ProfTrack.frame,'legacy observer registered duplicate crafting events')
          assert(ns.ProfExecution.eventFrame,'native execution observer did not initialize')
          assert(ns.ProfEconomy.ClientInputFrame,'native client observer was not loaded')
        ''')


if __name__=='__main__':unittest.main()
