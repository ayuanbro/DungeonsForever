"""Fixed first-aid navigation and the default profession-tool policy."""
import unittest

import test_prof_scheme_ui as scheme_fixture
import test_prof_execution_ui as execution_fixture
import test_prof_ui_regressions as ui_fixture


class FixedFirstAidUITests(unittest.TestCase):
    def setUp(self):
        scheme_fixture.SchemeUITests.setUp(self)

    def test_first_aid_mode_and_scheme_stay_fixed_with_global_auto_enabled(self):
        self.lua.execute('''
          PD.cur='first-aid';config.autoRoute=true;config.autoScheme='crafts'
          PD.lvSummary={auto=false,priced=true,total=50,target=225}
          PD.PaintLvTiles()
          assert(PD.lvTiles.mode.val.text=='固定路线')
          assert(PD.lvTiles.mode.scripts.OnClick==nil)
          assert(PD.lvTiles.scheme.scripts.OnClick==nil and not PD.lvTiles.scheme.shown)
          PD.CycleRouteScheme()
          assert(config.autoRoute and config.autoScheme=='crafts')
          assert(invalidates==0 and renders==0 and sounds==0)
        ''')

    def test_first_aid_navigation_uses_fixed_recalculation_and_no_search_controls(self):
        self.lua.execute('''
          PD.cur='first-aid';config.autoRoute=true;PD.exclusionsOpen=true
          PD.autoSnapshotSlug=PD.cur;PD.autoSnapshot={status='searching'}
          PD.RoutePairContext=function()error('first aid requested a partner')end
          local buttons,click=PD.LevelTool()
          for _,button in ipairs(buttons)do
            assert(button.key~='exclusions' and button.key~='partner' and button.key~='stop_search')
          end
          assert(not PD.exclusionsOpen)
          local clears,recalculated,refreshed=0,0,0
          RA.ClearFixedSummary=function(slug)assert(slug=='first-aid');clears=clears+1 end
          FixedShopData=function(target)return {mode='fixed',target=target,total=12}end
          ns.ProfExecution={GetRun=function()return nil end,
            PlanRecalculated=function(slug,plan)
              assert(slug=='first-aid' and plan.mode=='fixed' and plan.total==12)
              recalculated=recalculated+1
            end}
          -- LevelTool captures the current execution module for the click handler.
          _,click=PD.LevelTool()
          ns.ProfFollow={RefreshRoute=function(slug)assert(slug=='first-aid');refreshed=refreshed+1 end}
          click('recalc')
          assert(clears==1 and recalculated==1 and refreshed==1)
          assert(config.autoRoute,'first aid changed the shared automatic preference')
        ''')

    def test_first_aid_recalc_archives_old_auto_run_and_preserves_craft_facts(self):
        self.lua.execute("assert(loadfile(...))('DungeonsForever',ns)",
                         str(ui_fixture.ROOT / 'Core/ProfExecution.lua'))
        self.lua.execute('''
          PD.cur='first-aid';config.autoRoute=true;config.autoScheme='crafts'
          local E,XP=ns.ProfEconomy,ns.ProfExecution
          E.CharacterKey=function()return 'Test-Realm'end
          E.Professions=function()return {['first-aid']={cur=1,max=75}}end
          E.Gain=function()return 1 end
          local function step(id,spell)
            return {1,3,spell,2,profession='first-aid',segmentID=id,item=10,
              goalSkill=3,expectedGain=2,expectedCrafts=2,attemptLimit=2,
              requiredOutputs={},materialMinCrafts=0,allocations={},
              outputMin=1,outputMax=1,
              recipe={spell=spell,item=10,count=1,mats={},learn=1,yellow=20,green=30,grey=40}}
          end
          local oldStep=step('old-auto',101)
          local old=XP.Bind('first-aid',{planVersion=2,executionVersion=1,mode='fixed',
            status='complete',feasible=true,revision=1,steps={oldStep},executionSteps={oldStep}})
          assert(old and XP.RecordAttempt('first-aid',101,'legacy-cast'))
          assert(XP.RecordOutput({itemID=10,quantity=1,castGUID='legacy-cast'},'structured'))
          -- Emulate a pre-upgrade saved automatic plan. The current service
          -- correctly refuses to create a new automatic first-aid run.
          old.plan.mode='auto'
          local oldID=old.planID
          assert(old.attemptsDone==1 and XP.GetRecipeTotals('first-aid',oldID)[1].confirmedOutputs[10]==1)
          local newStep=step('new-fixed',102)
          FixedShopData=function(target)
            return {mode='fixed',executionVersion=1,status='complete',feasible=true,revision=2,
              target=target,total=12,steps={newStep},executionSteps={newStep}}
          end
          local prepared,cleared=0,0
          local prepare=XP.PrepareRecalculate
          XP.PrepareRecalculate=function(slug)
            assert(slug=='first-aid');prepared=prepared+1;return prepare(slug)
          end
          RA.ClearFixedSummary=function(slug)assert(slug=='first-aid');cleared=cleared+1 end
          local _,click=PD.LevelTool();click('recalc')
          local active=XP.GetRun('first-aid')
          assert(prepared==1 and cleared==1,'old automatic execution was not archived before fixed recalc')
          assert(active~=old and active.plan.mode=='fixed' and active.plan.executionSteps[1][3]==102)
          assert(active.attemptsDone==0 and old.status=='archived' and old.archiveReason=='recalculate')
          assert(old.attemptsDone==1 and old.plan.mode=='auto' and old.plan.executionSteps[1][3]==101)
          local totals=XP.GetRecipeTotals('first-aid',oldID)
          assert(totals[1].casts==1 and totals[1].confirmedOutputs[10]==1)
          assert(#XP.GetHistory('first-aid')==2)
          assert(config.autoRoute and config.autoScheme=='crafts','migration changed shared automatic settings')
        ''')


class FixedFirstAidShopTests(unittest.TestCase):
    def setUp(self):
        execution_fixture.ExecutionPageTests.setUp(self)

    def test_first_aid_shop_ignores_old_automatic_cache(self):
        self.lua.execute('''
          PD.cur='first-aid';PD.autoPage='shop';LV['first-aid']={steps={}}
          PD.ProfLearned=function()return {['first-aid']={cur=1,max=75}}end
          RA.Get=function()error('first aid read an automatic route')end
          FixedShopData=function(target)return {mode='fixed',target=target,total=12,mats={}}end
          local rows={};PD.RowsLeveling(rows)
          assert(shopData.mode=='fixed' and shopData.total==12)
          assert(not PD.lvSummary.auto and not PD.lvSummary.autoSetting)
        ''')


class ProfessionToolSettingTests(unittest.TestCase):
    def setUp(self):
        ui_fixture.ProfessionUIRegressions.setUp(self)

    def test_default_enabled_and_all_settings_have_pooled_controls(self):
        source=(ui_fixture.ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        a=source.index('PD.SETTING_DEF =')
        self.lua.execute(source[a:source.index('local function ProfDB(',a)])
        self.lua.execute('''
          assert(PD.SETTING_DEF.autoCraftTools==true)
          PushHead=function()end;PushGap=function()end
          PD.SettingRaw=function()return 'crafts'end
          PD.cur='engineering'
          local rows={};PD.RowsSettings(rows);local count,tool=0,nil
          for _,row in ipairs(rows)do if row.togKey then
            count=count+1
            if row.togKey=='autoCraftTools' then tool=row end
          end end
          assert(tool and tool.text=='制造专业工具')
          assert(tool.help[2][1]:find('默认开启',1,true))
          assert(tool.help[3][1]:find('拾取绑定',1,true))
          assert(count<=PD.SETTING_TOG_MAX,'settings exceed the toggle/help pools')
          PD.cur='first-aid';rows={};PD.RowsSettings(rows)
          for _,row in ipairs(rows)do
            assert(row.togKey~='autoRoute' and row.togKey~='autoCraftTools')
          end
        ''')

    def test_tool_step_label_does_not_claim_tools_are_sale_outputs(self):
        source=(ui_fixture.ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        a=source.index('function PD.StepRole(')
        self.lua.execute(source[a:source.index('function PD.StepRange(',a)])
        self.lua.execute('''
          PD.IsSpecializationQuest=function()return false end
          assert(PD.StepRole({[3]=7421,tool=true,tags={leveling=true}})=='专业工具')
        ''')


if __name__=='__main__':
    unittest.main()
