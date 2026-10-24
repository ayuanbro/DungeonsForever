"""The profession page exposes supplemental procurement without changing its quote."""
import unittest

import test_prof_ui_regressions as fixture


class ExecutionPageTests(unittest.TestCase):
    def setUp(self):
        fixture.ProfessionUIRegressions.setUp(self)
        source = (fixture.ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        a = source.index('function PD.RowsLeveling(')
        self.lua.execute(source[a:source.index('function PD.FormulaStockText(', a)])
        self.lua.execute('''
          settings={autoRoute=true,autoScheme='cheapest'}
          PD.Setting=function(key)return settings[key] and true or false end
          PD.SettingRaw=function(key)return settings[key]end
          PD.CookingFishingMode=function()return false end
          PD.LvTarget=function()return 3 end
          PD.ProfLearned=function()return {alchemy={cur=1,max=300}}end
          PD.RoutePairContext=function()return nil end
          PD.RowsRoutePartner=function()end
          PD.PlanHasSteps=function(plan)return plan and #(plan.steps or {})>0 end
          PD.CopyPlanSummary=function()end
          PD.RequestRender=function()renders=(renders or 0)+1 end
          PushHead=function(rows,text)rows[#rows+1]={text=text}end
          CountUnpriced=function()return 0 end
          PD.RowsAutoShop=function(rows,data)shopData=data;rows[#rows+1]={text='shop'}end
          PD.PlanDiagnostics=function()end
          LV.alchemy={steps={}}
          plan={planVersion=2,executionVersion=1,scheme='cheapest',feasible=true,
            total=100,steps={{1,3,101,2}}}
          RA.Get=function()return plan end
          RA.OptionsFor=function()return {start=1,target=3}end
          RA.Recalculate=function()error('viewing or calculating supplies replaced the route')end
          run={attemptsDone=4};calculations=0
          ns.ProfExecution={GetRun=function()return run end,
            GetSupplement=function()return supplement end,
            CalculateSupplement=function(_,callback)
              calculations=calculations+1
              if callback then callback(supplement)end
            end}
        ''')

    def test_supplement_navigation_does_not_trigger_procurement(self):
        self.lua.execute('''
          local buttons,click=PD.LevelTool();local found=false
          for _,button in ipairs(buttons)do if button.key=='page_supplement'then found=true end end
          assert(found);click('page_supplement')
          assert(PD.autoPage=='supplement' and calculations==0)
          local rows={};PD.RowsLeveling(rows)
          assert(calculations==0 and shopData==nil)
          local message=false
          for _,row in ipairs(rows)do if (row.text or ''):find('点击「计算补料」',1,true)then message=true end end
          assert(message)
        ''')

    def test_calculate_supplies_is_explicit_and_keeps_the_original_quote(self):
        self.lua.execute('''
          supplement={feasible=true,total=12,mats={{id=11,count=3,cost=12}},status='complete'}
          local _,click=PD.LevelTool();click('calculate_supplement')
          assert(calculations==1 and PD.autoPage=='supplement')
          local rows={};PD.RowsLeveling(rows)
          assert(shopData.mode=='supplement' and shopData.total==12)
          assert(shopData.mats==supplement.mats and supplement.mode==nil)
          assert(PD.lvSummary.isSupplement and PD.lvSummary.total==12)
          assert(plan.total==100)
          click('page_shop');rows={};PD.RowsLeveling(rows)
          assert(shopData==plan and PD.lvSummary.total==100 and not PD.lvSummary.isSupplement)
        ''')

    def test_active_supplies_job_shows_waiting_without_an_importable_shop(self):
        self.lua.execute('''
          PD.autoPage='supplement';supplement={inFlight=true,status='searching',total=0}
          local rows={};PD.RowsLeveling(rows)
          assert(shopData==nil and calculations==0)
          local pending=false
          for _,row in ipairs(rows)do if row.text=='正在计算补料…'then pending=true end end
          assert(pending and plan.total==100)
        ''')

    def test_stale_supplement_is_not_presented_as_a_free_purchase(self):
        self.lua.execute('''
          PD.autoPage='supplement';supplement={feasible=false,stale=true,status='stale',total=0}
          local rows={};PD.RowsLeveling(rows)
          assert(shopData==nil and not PD.lvSummary.priced)
          assert(rows[#rows].text=='进度已变化，请重新计算补料')
        ''')


if __name__ == '__main__':
    unittest.main()
