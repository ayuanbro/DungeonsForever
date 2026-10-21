"""Each route surface shows a stale notice once and preserves search details."""
import unittest

import test_prof_material_purchase_ui as material
import test_prof_scheme_ui as scheme

ROOT = material.ROOT


class RouteStatusRowsTests(unittest.TestCase):
    def setUp(self):
        material.MaterialShoppingPresentation.setUp(self)
        source = (ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        start = source.index('function PD.RowsLeveling(')
        self.lua.execute(source[start:source.index('function PD.FormulaStockText(', start)])
        self.lua.execute('''
          PD.cur='alchemy';LV.alchemy={steps={}}
          D={pro={alchemy={name='Alchemy'}}}
          PD.LvTarget=function()return 75 end
          PD.ProfLearned=function()return {alchemy={cur=60,max=75}}end
          PD.Setting=function(k)return k=='autoRoute' or k=='autoFromCurrent'end
          PD.SettingRaw=function()return 'cheapest'end
          PD.StepName=function()return 'Recipe'end
          PD.CopyPlanSummary=function()end
          PD.TextW=function(text)return #text*6 end
          PD.Fit=function(text)return text end
          PD.LevelSrc=function()end
          PD.RowsFormulaShop=function()end
          PD.RIGHT_W=900;PD.LIST_PAD=8;PD.LV_FS=13;PD.LV_STEP_X=6
          PD.LV_COL_GAP=16;PD.CARD_PAD=3;PD.TBL_ICON=28
          PD.TBL_RNG_GAP=12;PD.TBL_NAME_GAP=8;PD.TBL_MAT_RPAD=6;PD.TBL_H=42
          plan={planVersion=2,executionVersion=1,feasible=true,priced=true,
            scheme='cheapest',start=60,target=75,status='complete',stale=true,
            total=100,recoveryRevision=1,recoveryTotal=20,netTotal=80,
            recoverySnapshot={feePercent=5,feeSource='manual'},
            mats={},formulas={},steps={{60,75,101,15,cost=100,profession='alchemy',
              recipe={spell=101,item=20,count=1,mats={{10,1}},learn=1,
                yellow=100,green=120,grey=130}}}}
          RA.Get=function()return plan end
          function countText(rows,text)
            local n=0
            for _,r in ipairs(rows)do if r.text==text or r[1]==text then n=n+1 end end
            return n
          end
        ''')

    def test_route_and_shopping_show_one_notice_with_and_without_frozen_search(self):
        self.lua.execute('''
          local warning='已保存路线；数据或设置已变化，点击重新计算更新。'
          for _,frozen in ipairs({false,true})do
            plan.searchState=frozen and {status='complete',budgetLimited=true,
              searchTermination='cpu_limit',searchCpuLimitMs=5000,expanded=138,
              bestNetTotal=80,recoveryOptimized=true} or nil
            for _,page in ipairs({'route','shop'})do
              PD.autoPage=page
              local rows={};PD.RowsLeveling(rows)
              assert(countText(rows,warning)==1,page..' repeats the stale warning')
              assert(countText(rows,'采购支出：100')==1)
              assert(countText(rows,'预计净支出：80')==1)
              if frozen then
                assert(countText(rows,'已达计算时限 · 已保留路线')==1)
                assert(countText(rows,'已比较 138 个状态；本轮找到的最低预计净支出 80')==1)
              end
            end
          end
        ''')

    def test_empty_route_and_fresh_route_do_not_repeat_or_invent_warning(self):
        self.lua.execute('''
          local warning='已保存路线；数据或设置已变化，点击重新计算更新。'
          plan.steps={};local rows={};PD.RowsLeveling(rows)
          assert(countText(rows,warning)==1)
          plan.stale=nil
          rows={};PD.RowsLeveling(rows)
          assert(countText(rows,warning)==0)
          PD.autoPage='shop';rows={};PD.RowsLeveling(rows)
          assert(countText(rows,warning)==0)
        ''')

    def test_standalone_recovery_tooltip_keeps_the_stale_warning(self):
        self.lua.execute('''
          local warning='已保存路线；数据或设置已变化，点击重新计算更新。'
          assert(countText(PD.RecoveryLines(plan),warning)==1)
          assert(countText(PD.RecoveryLines(plan,true),warning)==0)
          assert(countText(PD.RecoveryLines(plan,false,true),warning)==0)
        ''')


class RouteStatusTileTests(unittest.TestCase):
    def setUp(self):
        scheme.SchemeUITests.setUp(self)

    def test_status_tooltip_does_not_repeat_its_title_and_cost_keeps_warning(self):
        self.lua.execute('''
          PD.lvSummary={auto=true,autoSetting=true,ahOK=true,scheme='matcost',
            total=100,priced=true,target=225,planVersion=2,status='complete',stale=true,
            recoveryRevision=1,recoveryTotal=20,netTotal=80,
            recoverySnapshot={feePercent=5,feeSource='manual'}}
          PD.PaintLvTiles()
          local warning='已保存路线；数据或设置已变化，点击重新计算更新。'
          local n=0
          for _,line in ipairs(PD.lvTiles.snap.lines)do if line[1]==warning then n=n+1 end end
          assert(n==1,'status tooltip repeats its title')
          assert(hasLine(PD.lvTiles.cost.lines,warning),'standalone cost lost the warning')
        ''')


if __name__ == '__main__':
    unittest.main()
