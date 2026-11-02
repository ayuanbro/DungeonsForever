"""Route notices must describe the visible profession and current render."""
import unittest
import test_prof_ui_fusion as ui
import test_prof_hud_ui_sync as toolbar
import test_prof_reserve as reserve


class RouteWarningScopeTests(unittest.TestCase):
    boot = ui.ProfessionUIFusionTests.boot

    def setUp(self):
        self.boot('zhCN')
        self.lua.execute('''
          local opts=ns.ProfRouteAuto.OptionsFor('alchemy',1);opts.target=3
          shown=finish('alchemy',opts);shown.scheme='stable'
          shown.considerAuctionSupply=false;shown.diagnostics={};shown.blockingDiagnostics={}
          shown.reserve={mode='ample',confidence=.95,total=100,coverageComplete=true,complete=true,
            steps={{extraCrafts=3,requiredOutputs={[10]=3}}},diagnostics={{code='quote',itemID=10}}}
          ns.ProfReserve=ns.ProfReserve or {};ns.ProfReserve.Label=function()return 'reserve' end
          ns.ProfRouteAuto.Get=function()return shown end
          PD.StepName=function()return 'ALCHEMY-ONLY' end
          PD.ItemName=function(id)return id==10 and 'ALCHEMY-ONLY' or ('Item'..id),true end
          PD.built=true;PD.page=widget();PD.scroll=widget();PD.rows={};PD.LV_TILE_H=64
          for _,name in ipairs({'PickNav','PickTabs','Layout','PaintRows','PlaceSettingsToggles',
            'RequestRows','WarmNames','PaintToolProgress','PaintToolStale','UpdateVScroll'})do
            PD[name]=function()end
          end
          PD.PaintLvTiles=function()return 0 end
          PD.PaintTool=function(list)painted=list;return 0 end
          ns.ProfLeveling.enchanting={steps={{1,3,101,2}}}
          function button(key)
            for _,entry in ipairs(painted or {})do if entry.key==key then return entry end end
          end
          function tooltipContains(key,needle)
            local b=button(key)
            for _,line in ipairs(b and b.tip or {})do
              if tostring(line[1]):find(needle,1,true)then return true end
            end
            return false
          end
          function noForeignNotices()
            assert(not button('supply_warn'),'foreign warning icon survived')
            assert(not tooltipContains('page_route','ALCHEMY-ONLY'),'foreign reserve text survived')
          end
        ''')

    def test_first_render_after_switch_has_no_previous_profession_warning(self):
        self.lua.execute('''
          shown.reserve.complete=false;PD.Render();assert(button('supply_warn'))
          assert(tooltipContains('supply_warn','ALCHEMY-ONLY'))
          PD.cur='enchanting'
          shown={slug='enchanting',status='recalculate_required',planVersion=2,steps={}}
          PD.Render();noForeignNotices()
          assert(not ns.ProfExecution.GetActive('enchanting'))
        ''')

    def test_no_plan_and_empty_route_hide_icon_even_with_old_snapshot(self):
        self.lua.execute('''
          shown.reserve.complete=false;PD.Render();assert(button('supply_warn'))
          shown=nil;PD.Render();noForeignNotices()
          shown={slug='alchemy',status='searching',planVersion=2,steps={},auctionSupplyUnknown=5}
          PD.Render();noForeignNotices()
        ''')

    def test_prerequisite_pages_hide_notices_even_if_old_steps_remain(self):
        self.lua.execute('''
          for _,status in ipairs({'selection_required','recalculate_required'})do
            shown.status='complete';shown.reserve.complete=false
            PD.Render();assert(button('supply_warn'))
            shown.status=status;PD.Render();noForeignNotices()
          end
        ''')

    def test_normal_reserve_information_does_not_fill_route_hover_or_warning(self):
        self.lua.execute('''
          PD.Render()
          assert(not button('supply_warn'),'normal route information became an alarm')
          assert(not tooltipContains('page_route','ALCHEMY-ONLY'))
          assert(not tooltipContains('page_route','模型覆盖目标'))
          assert(not ns.ProfExecution.GetActive('alchemy'),'rendering started tracking')
        ''')

    def test_current_candidate_warning_shows_without_starting_tracking(self):
        self.lua.execute('''
          shown.reserve.complete=false;PD.Render()
          assert(tooltipContains('supply_warn','备用材料缺少报价'))
          assert(tooltipContains('supply_warn','请更新价格后重新计算'))
          assert(not tooltipContains('supply_warn','模型覆盖目标'))
          assert(not tooltipContains('supply_warn','备用预算'))
          assert(not tooltipContains('supply_warn','建议预制备用'))
          assert(not ns.ProfExecution.GetActive('alchemy'))
          shown.reserve.complete=true;PD.Render()
          assert(not button('supply_warn'),'resolved warning survived another render')
        ''')

    def test_current_route_supply_warning_is_kept(self):
        self.lua.execute('''
          shown.considerAuctionSupply=true;shown.auctionSupplyUnknown=2
          PD.Render();assert(tooltipContains('supply_warn','数量未知'))
          shown.considerAuctionSupply=false;PD.Render();assert(not button('supply_warn'))
        ''')

    def test_changed_snapshot_identity_cannot_reuse_old_notes(self):
        self.lua.execute('''
          shown.reserve.complete=false;PD.RowsLeveling({})
          PD.autoSnapshot=ns.ProfEconomy.Copy(shown)
          painted=PD.LevelTool();noForeignNotices()
          PD.autoSnapshot=shown;PD.cur='enchanting';PD.autoSnapshotSlug='enchanting'
          painted=PD.LevelTool();noForeignNotices()
        ''')

    def test_log_and_unknown_profession_clear_route_notes(self):
        self.lua.execute('''
          PD.RowsLeveling({});assert(PD.warnNotes)
          PD.autoPage='log';PD.RowsLeveling({});assert(PD.warnNotes==nil)
          PD.autoPage='route';PD.cur='alchemy';PD.RowsLeveling({});assert(PD.warnNotes)
          PD.cur='not-a-profession';PD.RowsLeveling({});assert(PD.warnNotes==nil)
        ''')

    def test_reserve_quote_warning_is_grouped_and_does_not_claim_unknown_stock(self):
        self.lua.execute('''
          local lines=PD.ReserveWarningLines({mode='ample',complete=false,coverageComplete=true,
            diagnostics={{code='quote',itemID=10},{code='quote',itemID=10},{code='supply',itemID=10},
              {code='supply',itemID=11},{code='supply',itemID=11}}})
          assert(#lines==2)
          assert(lines[1]:find('ALCHEMY-ONLY',1,true) and lines[1]:find('更新价格',1,true))
          assert(lines[2]:find('Item11',1,true) and lines[2]:find('补充货源',1,true))
          assert(not lines[2]:find('ALCHEMY-ONLY',1,true),'missing price was reported as a stock shortage')
        ''')

    def test_reserve_quantity_warnings_name_the_problem_and_next_action(self):
        self.lua.execute('''
          for _,case in ipairs({{'variable_output','产量不固定','按实际缺口补料'},
            {'grey','技能范围','重新计算'},{'skill','技能范围','重新计算'},
            {'budget','数量未算完整','重新计算'},{'provenance','需求未算全','重新计算'},
            {'dependency','需求未算全','按实际缺口补料'}})do
            local lines=PD.ReserveWarningLines({mode='ample',complete=false,coverageComplete=false,
              diagnostics={{code=case[1],itemID=10}}})
            assert(#lines==1 and lines[1]:find('ALCHEMY-ONLY',1,true))
            assert(lines[1]:find(case[2],1,true) and lines[1]:find(case[3],1,true))
          end
          local lines=PD.ReserveWarningLines({mode='ample',complete=false,coverageComplete=false})
          assert(#lines==1 and lines[1]:find('检查购物清单',1,true))
          assert(#PD.ReserveWarningLines({mode='off',complete=false})==0)
        ''')

    def test_many_repeated_items_are_bounded_and_warning_does_not_mutate_plan(self):
        self.lua.execute('''
          local data={mode='ample',confidence=.95,total=42,complete=false,diagnostics={}}
          for id=10,19 do
            for i=1,20 do data.diagnostics[#data.diagnostics+1]={code='quote',itemID=id}end
          end
          local lines=PD.ReserveWarningLines(data)
          assert(#lines==1 and lines[1]:find('等 10 种物品',1,true))
          assert(not lines[1]:find('Item13',1,true))
          assert(data.total==42 and data.confidence==.95 and #data.diagnostics==200)
        ''')

    def test_generic_route_explanations_stay_out_of_actual_warning(self):
        self.lua.execute('''
          shown.reserve.complete=false;shown.specBlocked=4;PD.Render()
          assert(tooltipContains('page_route','已按本角色专精过滤'))
          assert(not tooltipContains('supply_warn','已按本角色专精过滤'))
          assert(tooltipContains('supply_warn','备用材料缺少报价'))
          shown.blockingDiagnostics={{code='learningDataMissing'}};PD.Render()
          assert(tooltipContains('supply_warn','请在配方页核对上述限制'))
        ''')


class ReserveShoppingCopyTests(unittest.TestCase):
    setUp = reserve.ReserveShoppingTests.setUp

    def test_shopping_keeps_reserve_quantities_and_budget_without_model_details(self):
        self.lua.execute('''
          local plan=reserveSolve();local steps=plan.executionSteps;bag[11]=2;PD.shopGroup=false
          assert(plan.total==35 and plan.reserve.total==21 and plan.reserve.steps[1].extraCrafts==3)
          local rows={};PD.RowsAutoShop(rows,plan)
          local quantity=false;local summary={}
          for _,row in ipairs(rows)do
            if row.sub=='基础 5 · 备用 3 · 背包 2' then
              assert(row.purchaseCount==6);quantity=true
            end
            if row.col==2 and row.text then summary[#summary+1]=row.text end
            for _,field in ipairs({'text','sub','right','right2'})do
              local text=tostring(row[field] or '')
              assert(not text:find('模型覆盖',1,true) and not text:find('覆盖目标',1,true))
              assert(not text:find('预制备用',1,true) and not text:find('95%%'))
            end
          end
          local text=table.concat(summary)
          assert(quantity)
          assert(text:find(format(ns.L['备用材料预算：%s'],ns.ProfRouteAuto.MoneyStr(21,'copper')),1,true))
          assert(text:find(format(ns.L['基础加备用预算：%s'],ns.ProfRouteAuto.MoneyStr(56,'copper')),1,true))
          assert(plan.executionSteps==steps and plan.total==35 and plan.reserve.total==21)
          assert(plan.reserve.confidence==.95 and plan.reserve.steps[1].extraCrafts==3)
        ''')

    def test_shopping_missing_quote_is_explained_and_unknown_budget_not_zeroed(self):
        self.lua.execute('''
          local plan=reserveSolve();plan.reserve.total=nil;plan.reserve.priced=false
          plan.reserve.complete=false;plan.reserve.diagnostics={{code='quote',itemID=11}}
          local rows={};PD.RowsAutoShop(rows,plan);local summary={}
          for _,row in ipairs(rows)do
            if row.col==2 and row.text then summary[#summary+1]=row.text end
          end
          local text=table.concat(summary)
          assert(text:find(format(ns.L['备用材料预算：%s'],ns.L['价格未知']),1,true))
          assert(text:find('备用材料缺少报价',1,true) and text:find('请更新价格后重新计算',1,true))
          assert(plan.reserve.total==nil)
        ''')


class ReserveWarningLocaleTests(unittest.TestCase):
    boot = ui.ProfessionUIFusionTests.boot

    def test_three_locales_have_player_facing_actions_and_plain_settings_help(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                self.boot(locale)
                self.lua.execute('''
                  local text=PD.ReserveWarningLines({mode='ample',complete=false,coverageComplete=false,
                    diagnostics={{code='quote',itemID=10},{code='supply',itemID=11},
                      {code='variable_output',itemID=12},{code='skill',itemID=13},
                      {code='budget',itemID=14},{code='dependency',itemID=15}}})
                  assert(#text==6)
                  for _,line in ipairs(text)do
                    assert(not line:find('95%%') and not line:find('覆盖目标',1,true))
                    if GetLocale()=='enUS' then assert(line:find('%.') and not line:find('备用',1,true)) end
                  end
                  assert(rawget(ns.L,'备用材料只在需要时使用；数量和预算见购物清单。'))
                  local rows={};PD.RowsSettings(rows);local help
                  for _,row in ipairs(rows)do if row.text==ns.L['备料余量']then help=row.help end end
                  assert(help)
                  for _,line in ipairs(help)do assert(not line[1]:find('覆盖目标',1,true))end
                ''')


class ToolbarTooltipScopeTests(unittest.TestCase):
    boot = toolbar.ProfessionToolbarTests.boot
    setup_locale = toolbar.ProfessionToolbarTests.setup_locale
    setUp = toolbar.ProfessionToolbarTests.setUp

    def test_cached_button_updates_and_clears_hover_text_without_layout_change(self):
        self.lua.execute('''
          PD.hudBtn:Hide();PD.impBtn:Hide();PD.UnifyTipFont=function()end
          local list={{key='route',text='Route'}}
          PD.PaintTool(list,function()end,0)
          local b=PD.toolBtns[1];local paintKey=b.__ptk
          list[1].tip={{'CURRENT'}};PD.PaintTool(list,function()end,0)
          assert(b.__ptk==paintKey and b.__tipLines[1][1]=='CURRENT')
          local lines={}
          GameTooltip={SetOwner=function()end,ClearLines=function()lines={}end,
            AddLine=function(_,s)lines[#lines+1]=s end,Show=function()end,Hide=function()end}
          b.scripts.OnEnter(b);assert(lines[1]=='CURRENT')
          list[1].tip={{'REPLACEMENT'}};PD.PaintTool(list,function()end,0)
          b.scripts.OnEnter(b);assert(lines[1]=='REPLACEMENT')
          list[1].tip=nil;PD.PaintTool(list,function()end,0)
          assert(b.__tipLines==nil)
        ''')

    def test_reused_warning_button_does_not_leak_into_plain_button(self):
        self.lua.execute('''
          PD.hudBtn:Hide();PD.impBtn:Hide()
          PD.PaintTool({{key='warn',icon='warning',tip={{'OLD'}}}},function()end,0)
          local b=PD.toolBtns[1];assert(b.__icon:IsShown() and b.__tipLines[1][1]=='OLD')
          PD.PaintTool({{key='track',text='Track',tip={{'TRACK'}}}},function()end,0)
          assert(not b.__icon:IsShown() and b.__tipLines[1][1]=='TRACK')
          PD.PaintTool({{key='route',text='Route'}},function()end,0)
          assert(b.__tipLines==nil)
        ''')


if __name__ == '__main__':
    unittest.main()
