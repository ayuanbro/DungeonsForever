"""Leveling navigation, purchase settings, and bounded recipe descriptions."""
import unittest

import test_prof_ui_regressions as fixture

ROOT = fixture.ROOT


class LevelingNavigationTests(unittest.TestCase):
    def setUp(self):
        fixture.ProfessionUIRegressions.setUp(self)
        self.lua.execute('''
          PD.Setting=function(k)return k=='autoRoute' or k=='recoveryEnabled' end
          PD.RoutePairContext=function()return nil end
          PD.RequestRender=function()end
          ns.ProfExecution={GetRun=function()return {archived=false} end,
            GetHistory=function()return {{}} end}
        ''')

    def test_pages_are_exclusive_and_operations_do_not_look_selected(self):
        self.lua.execute('''
          for _,page in ipairs({'page_route','page_shop','page_supplement','page_history','exclusions'})do
            local _,click=PD.LevelTool();click(page)
            local buttons=PD.LevelTool();local active,actions=0,false
            for _,b in ipairs(buttons)do
              if b.role=='tab' then
                assert(not actions,'navigation mixed into operations')
                if b.on then active=active+1;assert(b.key==page)end
              else
                actions=true
                if b.key=='recovery' then
                  assert(b.role=='toggle' and b.text=='回血模式 · 开')
                else assert(b.role=='action')end
              end
            end
            assert(active==1,'page selection is not exclusive')
          end
          local _,click=PD.LevelTool();click('page_shop')
          assert(not PD.exclusionsOpen and PD.autoPage=='shop')
        ''')

    def test_hidden_exclusion_page_does_not_remove_current_selection(self):
        self.lua.execute('''
          for _,slug in ipairs({'alchemy','poisons'})do
            PD.cur=slug;PD.exclusionsOpen=true;PD.autoPage='shop'
            PD.Setting=function()return false end
            local active=0
            for _,b in ipairs(PD.LevelTool())do
              if b.role=='tab' and b.on then active=active+1;assert(b.key=='page_shop')end
            end
            assert(active==1)
            assert(not PD.exclusionsOpen)
          end
        ''')

    def test_unavailable_history_or_supplies_returns_to_route(self):
        self.lua.execute('''
          ns.ProfExecution={}
          for _,page in ipairs({'history','supplement'})do
            PD.autoPage=page
            local active=0
            for _,b in ipairs(PD.LevelTool())do
              if b.role=='tab' and b.on then active=active+1;assert(b.key=='page_route')end
            end
            assert(active==1 and PD.autoPage=='route')
          end
        ''')

    def test_settings_default_off_and_explain_auction_alternative(self):
        source=(ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        start=source.index('PD.SETTING_DEF =')
        self.lua.execute(source[start:source.index('local function ProfDB(',start)])
        self.lua.execute('''
          assert(PD.SETTING_DEF.autoBuyLimitedFormulas==false)
          PushHead=function()end;PushGap=function()end
          PD.SettingRaw=function()return 'cheapest'end
          for _,slug in ipairs({'alchemy','poisons','enchanting','engineering'})do
            PD.cur=slug;local rows={};PD.RowsSettings(rows);local found=false
            for _,r in ipairs(rows)do if r.togKey=='autoBuyLimitedFormulas' then
              found=true;assert(r.help[2][1]:find('默认关闭',1,true))
              assert(r.help[2][1]:find('拍卖行',1,true))
            end end
            assert(found)
          end
        ''')

    def test_finished_search_explains_limit_and_stops_saying_background(self):
        self.lua.execute('''
          local plan={status='complete',budgetLimited=true,searchTermination='cpu_limit',
            searchCpuLimitMs=5000,searchCpuMs=5001,expanded=6,initialTotal=100,total=80}
          assert(PD.PlanStatusText(plan)=='已达计算时限 · 已保留路线')
          assert(PD.PlanSearchLimitText(plan):find('5 秒',1,true))
          assert(PD.PlanSearchLimitText(plan):find('不能证明最优',1,true))
          plan.searchTermination='node_limit'
          assert(PD.PlanStatusText(plan)=='已达比较上限 · 已保留路线')
          assert(not PD.PlanSearchLimitText(plan):find('秒',1,true))
          plan.searchState={status='complete',expanded=6,bestNetTotal=50,recoveryOptimized=true,
            budgetLimited=true,searchTermination='cpu_limit',searchCpuLimitMs=5000}
          assert(PD.PlanStatusText(plan)=='已达计算时限 · 已保留路线')
          assert(PD.PlanProgressText(plan)=='已比较 6 个状态；本轮找到的最低预计净支出 50')
          plan.searchState.status='searching'
          assert(PD.PlanProgressText(plan):find('后台当前',1,true))
        ''')

    def test_formula_setting_change_reports_its_own_recalculation_reason(self):
        self.lua.execute('''
          assert(PD.PlanStatusText({status='recalculate_required',
            diagnostics={{code='formulaPolicyChanged'}}})=='限量图纸购买设置已变化，请重新计算路线。')
        ''')

    def test_long_description_stays_in_name_column_and_tooltip_keeps_full_text(self):
        source=(ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        start=source.index('function PD.FitRecipeCols(')
        self.lua.execute(source[start:source.index('-- ── 配方页难度四段色条',start)])
        hui=(ROOT/'Core/Hui.lua').read_text(encoding='utf-8-sig')
        self.lua.execute(hui[:hui.index('ns.hui.CharStep = HCharStep')],'Test',self.lua.globals().ns)
        self.lua.execute('''
          PD.TextW=ns.hui.TextW;PD.Fit=ns.hui.Fit
          PD.RECIPE_NAME_MIN=110;PD.RECIPE_NAME_MAX=160;PD.RECIPE_NAME_PAD=16
          PD.RECIPE_PADL=32;PD.RECIPE_BADGE_W=26;PD.REC_AH_W=60;PD.REC_COST_W=60
          PD.DiffBarW=function()return 80 end
          PD.SyncRows=function()return 10 end;PD.FinishSpecMats=function()end
          for _,width in ipairs({640,800,1000})do
            PD.MAT_ROW_W=width
            for _,description in ipairs({string.rep('触发后恢复生命值并提高法术效果。',12),
                string.rep('Restores health and increases spell effects. ',12)})do
              local row={text='Restoration',sub=description,is_new=true,lines={{description}}}
              PD.FitRecipeCols({row})
              assert(PD.TextW(row.text,13)<=row.nameWidth)
              assert(PD.TextW(row.sub,11)+PD.RECIPE_BADGE_W<=row.subWidth)
              assert(PD.RECIPE_PADL+row.subWidth<=PD.MAT_X-8)
              assert(row.lines[1][1]==description,'tooltip lost the full description')
            end
          end
        ''')


if __name__=='__main__':
    unittest.main()
