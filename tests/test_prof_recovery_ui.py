"""Frozen recovery amounts, settings and all route displays in Lua 5.1 mocks."""
import unittest

import test_prof_ui_regressions as ui
import test_prof_material_purchase_ui as material
import test_prof_execution_hud as hud

ROOT = ui.ROOT
SOURCE = (ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')


def load_block(lua, start, end):
    pos = SOURCE.index(start)
    lua.execute(SOURCE[pos:SOURCE.index(end, pos + len(start))])


class RecoverySettingsTests(unittest.TestCase):
    def setUp(self):
        ui.ProfessionUIRegressions.setUp(self)
        load_block(self.lua, 'PD.SETTING_DEF =', 'local function ProfDB(')
        self.lua.execute(r'''
          config={autoScheme='crafts',autoRoute=true}
          ProfDB=function()return config end
          invalidates=0;renders=0
          RA.Invalidate=function()invalidates=invalidates+1 end
          RA.Recalculate=function()error('setting edit started a search')end
          RA.Compute=RA.Recalculate
          PD.RequestRender=function()renders=renders+1 end
          ns.PlaySound=function()end
          StaticPopupDialogs={};StaticPopup_Show=function(key)openedPopup=key end
        ''')
        load_block(self.lua, 'function PD.Setting(k)', '-- Cooking keeps')

    def test_default_enabled_toggle_preserves_other_scheme_and_requires_recalc(self):
        self.lua.execute(r'''
          assert(PD.Setting('recoveryEnabled'))
          PD.CookingFishingMode=function()return true end
          local buttons,click=PD.LevelTool();local toggle
          for _,button in ipairs(buttons)do if button.key=='recovery'then toggle=button end end
          assert(toggle and toggle.on)
          click('recovery')
          assert(not config.recoveryEnabled and config.autoScheme=='crafts')
          assert(invalidates==1 and renders==1)
          click('recovery')
          assert(config.recoveryEnabled and invalidates==2)
        ''')

    def test_fee_accepts_manual_zero_decimal_and_automatic_reset(self):
        self.lua.execute(r'''
          for _,v in ipairs({'0','5.5','100'})do
            assert(PD.SetRecoveryFee(v));assert(config.recoveryFeePercent==tonumber(v))
          end
          assert(PD.SetRecoveryFee('  ') and config.recoveryFeePercent==nil)
          assert(PD.SetRecoveryFee(nil) and config.recoveryFeePercent==nil)
          assert(invalidates==5)
        ''')

    def test_invalid_fee_keeps_prior_snapshot_and_override(self):
        self.lua.execute(r'''
          config.recoveryFeePercent=5
          for _,v in ipairs({'-1','101','hello','nan','inf'})do
            assert(not PD.SetRecoveryFee(v))
            assert(config.recoveryFeePercent==5 and invalidates==0)
          end
          PD.ShowRecoveryFeePopup()
          assert(openedPopup=='DUNGEONSFOREVER_RECOVERY_FEE')
          local dialog=StaticPopupDialogs[openedPopup]
          local frame={editBox={GetText=function()return 'oops'end}}
          assert(dialog.OnAccept(frame)==true)
          frame.editBox.GetText=function()return ''end
          assert(dialog.OnAccept(frame)==false and config.recoveryFeePercent==nil)
          assert(invalidates==1)
        ''')

    def test_fixed_recalc_refreshes_reference_and_execution_without_auto_search(self):
        self.lua.execute(r'''
          config.autoRoute=false;PD.LvTarget=function()return 3 end
          PD.CookingFishingMode=function()return false end
          cleared,archived,rebound=0,0,0
          RA.ClearFixedSummary=function(slug)assert(slug=='alchemy');cleared=cleared+1 end
          FixedShopData=function(target)assert(target==3);return {mode='fixed',total=200}end
          ns.ProfExecution={GetRun=function()return {plan={mode='fixed'}}end,
            PrepareRecalculate=function()archived=archived+1 end,
            PlanRecalculated=function(slug,plan)assert(plan.total==200);rebound=rebound+1 end}
          local _,click=PD.LevelTool();click('recalc')
          assert(cleared==1 and archived==1 and rebound==1 and renders==1)
        ''')


class RecoveryDisplayTests(unittest.TestCase):
    def setUp(self):
        material.MaterialShoppingPresentation.setUp(self)
        self.lua.execute(r'''
          RA.AHPriceOf=function()error('display read a live sale quote')end
          PD.RowsFormulaShop=function()end
          plan={planVersion=2,status='complete',feasible=true,scheme='cheapest',
            recoveryRevision=1,total=100,purchaseTotal=100,recoveryTotal=42,netTotal=58,
            productAH=99999,productNPC=88888,recoveryMissing=1,
            recoverySnapshot={enabled=true,feePercent=5,feeSource='auctionator-reference'},
            mats={},formulas={},saleOutputs={{id=20,count=200,source='ah',revenue=42,cost=100}}}
          function texts(rows)
            local out={};for _,row in ipairs(rows)do out[#out+1]=row.text or row[1] or ''end
            return table.concat(out,'\n')
          end
        ''')

    def test_shop_shows_frozen_totals_all_sold_assumption_and_selected_channel(self):
        self.lua.execute(r'''
          local rows={};PD.RowsAutoShop(rows,plan);local t=texts(rows)
          assert(t:find('采购支出：100',1,true))
          assert(t:find('假设全部成交的预计回血：42',1,true))
          assert(t:find('预计净支出：58',1,true))
          assert(t:find('拍卖手续费：5%（Auctionator 参考）',1,true))
          assert(t:find('1 种剩余产物售价缺失',1,true))
          assert(t:find('Item20 ×200',1,true))
          assert(not t:find('99999',1,true) and not t:find('净赚',1,true))
          local found=false
          for _,row in ipairs(rows)do
            if row.text=='Item20 ×200' then
              assert(row.sub=='推荐拍卖（扣手续费）' and row.right=='42');found=true
            end
          end
          assert(found)
        ''')

    def test_missing_revision_does_not_invent_zero_recovery_or_net_profit(self):
        self.lua.execute(r'''
          local lines=PD.RecoveryLines({total=100,productAH=999})
          assert(#lines==1 and lines[1][1]=='旧路线尚无回血快照，请重新计算。')
          plan.netTotal=-58
          assert(PD.RecoveryLines(plan,true)[3][1]=='预计净支出：-58')
        ''')

    def test_intermediate_and_mixed_costs_use_recursive_allocation(self):
        self.lua.execute(r'''
          local pure={cost=20,productionCost=20,attributedCost=0,transferredCost=20,recoveryTotal=0}
          local mixed={cost=20,productionCost=20,attributedCost=8,transferredCost=12,recoveryTotal=6}
          assert(PD.StepCostText(pure)=='成本转入下游')
          assert(PD.StepCostText(mixed)=='8')
          local lines=PD.StepRecoveryLines(mixed)
          assert(lines[1][1]=='实际制作成本：20')
          assert(lines[2][1]=='转入下游成本：12')
          assert(lines[3][1]=='最终归属成本：8')
          assert(lines[4][1]=='自身剩余产物预计回血：6')
        ''')

    def test_step_tooltip_audits_sale_quantity_remainder_origins_and_channels(self):
        self.lua.execute(r'''
          local step={productionCost=20,attributedCost=8,transferredCost=12,recoveryTotal=6,
            consumedCount=6,saleCount=4,naturalRemainder=1,levelingRemainder=3,
            recoveryOutputs={{id=20,count=2,source='ah',unit=2,revenue=4},
              {id=21,count=1,source='npc',unit=2,revenue=2},
              {id=22,count=1,source='unknown',unit=0,revenue=0,missing=true}}}
          local t=texts(PD.StepRecoveryLines(step))
          assert(t:find('最终可出售 4 件：制材自然余量 1；额外升级产物 3。',1,true))
          assert(t:find('Item20 ×2 · 推荐拍卖（扣手续费） · 净单价 2 · 预计回血 4',1,true))
          assert(t:find('Item21 ×1 · 推荐卖给 NPC · 净单价 2 · 预计回血 2',1,true))
          assert(t:find('Item22 ×1 · 售价缺失，未计回血 · 净单价 价格未知',1,true))
        ''')

    def test_zero_cost_intermediate_still_reports_downstream_transfer(self):
        self.lua.execute(r'''
          local pure={productionCost=0,attributedCost=0,transferredCost=0,consumedCount=10,saleCount=0}
          assert(PD.StepCostText(pure)=='成本转入下游')
          pure.saleCount=4
          assert(PD.StepCostText(pure)=='0')
          assert(PD.StepCostText({productionCost=0,consumedCount=0,saleCount=0,attributedCost=0})=='0')
        ''')

    def test_copy_summary_uses_recovery_fields_for_fixed_and_legacy_modes(self):
        load_block(self.lua, 'function PD.CopyPlanSummary(', 'function PD.StepRecipe(')
        self.lua.execute(r'''
          for _,version in ipairs({false,2})do
            plan.planVersion=version or nil;PD.lvSummary={total=100}
            PD.CopyPlanSummary(plan)
            assert(PD.lvSummary.recoverySnapshot==plan.recoverySnapshot)
            assert(PD.lvSummary.netTotal==58 and PD.lvSummary.recoveryTotal==42)
            assert(PD.lvSummary.saleOutputs==plan.saleOutputs)
          end
        ''')

    def test_recovery_objective_labels_net_savings_and_never_claims_optimum_on_budget(self):
        self.lua.execute(r'''
          assert(PD.PlanStatusText({recoveryRevision=1,recoveryOptimized=true,optimal=true,supplyComplete=true})=='当前模型内预计净支出最优')
          assert(PD.PlanStatusText({recoveryRevision=1,recoveryOptimized=true,status='complete',optimal=true,budgetLimited=true})=='本轮计算已结束 · 已保留路线')
          assert(PD.PlanStatusText({recoveryRevision=1,recoveryOptimized=true,optimal=true,stale=true})=='已保存路线；数据或设置已变化，点击重新计算更新。')
          assert(PD.PlanStatusText({recoveryOptimized=true,optimal=true})=='旧路线尚无回血快照，请重新计算。')
          local progress=PD.PlanProgressText({recoveryOptimized=true,expanded=5,initialTotal=100,netSavings=40,savings=0})
          assert(progress=='已比较 5 个状态；较初始方案预计净支出降低 40')
        ''')

    def test_three_locales_cover_recovery_copy_and_placeholders(self):
        keys = [
            '假设全部成交的预计回血：%s', '预计净支出：%s', '回血模式',
            '成本转入下游', '拍卖手续费：%s%%（%s）',
            '%d 种剩余产物售价缺失，暂不计回血；已知零售价按零计算。',
            '最终可出售 %s 件：制材自然余量 %s；额外升级产物 %s。',
            '%s ×%s · %s · 净单价 %s · 预计回血 %s',
        ]
        for locale in ('zhCN', 'zhTW', 'enUS'):
            self.lua.globals().testLocale = locale
            self.lua.execute('GetLocale=function()return testLocale end')
            for language in ('zhCN', locale):
                self.lua.execute((ROOT / 'Locales' / f'{language}.lua').read_text(encoding='utf-8-sig'), 'Test', self.lua.globals().ns)
            for key in keys:
                self.assertIsNotNone(self.lua.eval('rawget')(self.lua.globals().ns.L, key), (locale, key))


class RecoveryHUDTests(unittest.TestCase):
    def setUp(self):
        self.lua = hud.ExecutionHUDTests.make_runtime(self)
        self.lua.execute(r'''
          PD=ns.ProfModule;RA=ns.ProfRouteAuto;L=ns.L;format=string.format
          RA.MoneyStr=tostring
        ''')
        load_block(self.lua, 'function PD.PlanCostText(', 'function PD.CopyPlanSummary(')

    def test_hud_renders_same_frozen_three_totals_before_current_step(self):
        self.lua.execute(r'''
          skills.alchemy.cur=60;followState.skill=60
          setPlan({makeStep(60,75,101,15)})
          currentResult.recoveryRevision=1;currentResult.purchaseTotal=100
          currentResult.recoveryTotal=42;currentResult.netTotal=58
          currentResult.recoverySnapshot={feePercent=5,feeSource='manual'}
          ns.ProfFollow.Sync();ns.ProfFollow.Build()
          local f=ns.ProfFollow.f;f.recovery.text.GetStringHeight=function()return 45 end
          f:Show();ns.ProfFollow.Paint()
          assert(f.recovery:IsShown())
          assert(f.recovery.text.text=='采购支出：100\n假设全部成交的预计回血：42\n预计净支出：58')
          local headBottom=-f.recovery.point[5]+f.recovery.height
          assert(-f.card.point[5]>=headBottom+8,'recovery text covers step card')
          assert(#f.recovery.lines>3,'fee and assumptions are missing from HUD tooltip')
        ''')

    def test_frozen_hud_revalidates_fee_and_preserves_original_amounts(self):
        self.lua.execute(r'''
          skills.alchemy.cur=60;followState.skill=60
          setPlan({makeStep(60,75,101,15)})
          currentResult.recoveryRevision=1;currentResult.recoveryTotal=42;currentResult.netTotal=58
          currentResult.recoverySnapshot={feePercent=5,feeSource='manual'}
          ns.ProfFollow.Sync()
          DungeonsForeverDB.prof.recoveryEnabled=false
          DungeonsForeverDB.prof.recoveryFeePercent=15
          RA.ValidateRecovery=function(result,opts)
            assert(opts.recoveryEnabled==false and opts.recoveryFeePercent==15)
            result.stale=true;return result
          end
          ns.ProfFollow.Build();local f=ns.ProfFollow.f;f:Show();ns.ProfFollow.Paint()
          assert(f.recovery.text.text:find('预计净支出：58',1,true))
          assert(f.recovery.lines[#f.recovery.lines][1]=='已保存路线；数据或设置已变化，点击重新计算更新。')
        ''')

    def test_fixed_hud_keeps_summary_blocked_before_normalization(self):
        self.lua.execute(r'''
          settings.autoRoute=false
          RA.FixedSummary=function()return {status='recalculate_required',feasible=false,steps={}}end
          ns.ProfExecution.NormalizePlan=function()error('blocked fixed plan was normalized')end
          ns.ProfFollow.Sync();ns.ProfFollow.Build()
          local f=ns.ProfFollow.f;f:Show();ns.ProfFollow.Paint()
          assert(not f.card:IsShown() and f.finish:IsShown())
        ''')


if __name__ == '__main__':
    unittest.main()
