"""Pattern-channel settings, acquisition displays and live execution contracts."""
import unittest

import test_prof_ui_fusion as ui


class RecipeSettingsV2Tests(unittest.TestCase):
    def setUp(self):
        ui.ProfessionUIFusionTests.boot(self, 'zhCN')
        self.lua.execute('PD.Wrap=function(text)return {text}end')

    def test_retired_saved_values_and_supplied_options_do_not_filter_routes(self):
        self.lua.execute('''
          local old={'autoLearnedOnly','autoAllowUnknownLearning','autoSkipUnpricedFormulas','autoNoFormula'}
          local db=DungeonsForeverDB.prof
          db.professionSettings={alchemy={}}
          for _,key in ipairs(old)do
            db[key]=true;db.professionSettings.alchemy[key]=true
            assert(PD.SettingRaw(key,'alchemy')==nil and PD.SETTING_DEF[key]==nil)
          end
          local opts=PD.BuildLvOpts('alchemy',1)
          assert(opts.learnedOnly==nil and opts.noFormula==nil and opts.allowUnknownLearning==nil and opts.skipUnpricedFormulas==nil)
          assert(not opts.allowLimitedFormulas and not opts.allowBindOnPickupFormulas and not opts.allowCurrencyFormulas)
          local result=finish('alchemy',{snapshot=fixture(),start=1,target=3,
            learnedOnly=true,noFormula=true,allowUnknownLearning=true,skipUnpricedFormulas=true})
          assert(result.targetReached)
          local rows={};PD.RowsSettings(rows)
          for _,row in ipairs(rows)do
            for _,key in ipairs(old)do assert(row.togKey~=key)end
          end
        ''')

    def test_general_and_currency_settings_keep_scoped_preferences_and_explain_overlap(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            with self.subTest(locale=locale):
                ui.ProfessionUIFusionTests.boot(self, locale)
                self.lua.execute('PD.Wrap=function(text)return {text}end')
                self.lua.execute('''
                  PD.SetSettingRaw('autoAllowCurrencyFormulas',true,'alchemy')
                  local a=ns.ProfRouteAuto.OptionsFor('alchemy',1)
                  local b=ns.ProfRouteAuto.OptionsFor('enchanting',1)
                  assert(a.allowCurrencyFormulas and not a.allowBindOnPickupFormulas)
                  assert(not b.allowCurrencyFormulas and not b.allowBindOnPickupFormulas)
                  local rows={};PD.RowsSettings(rows)
                  for _,name in ipairs({'允许NPC限量销售图纸','允许非金币获取的拾取绑定图纸','允许通货兑换图纸'})do
                    local found=false
                    for _,row in ipairs(rows)do if row.text==ns.L[name] then found=true end end
                    assert(found,name)
                    if GetLocale()=='enUS'then assert(ns.L[name]~=name,name)end
                  end
                  PD.SetSettingRaw('autoAllowBindOnPickupFormulas',true,'alchemy')
                  rows={};PD.RowsSettings(rows)
                  local currencyRow
                  for _,row in ipairs(rows)do
                    if row.togKey=='autoAllowCurrencyFormulas'then currencyRow=row end
                  end
                  assert(currencyRow and not currencyRow.disabled)
                  assert(currencyRow.help[3][1]==ns.L['默认关闭；任一开关开启即可规划兑换。合格拍卖行报价不受此开关限制。'])
                  assert(currencyRow.help[4][1]==ns.L['金币加通货或物品也属于兑换；仅此项开启不放行掉落或任务，限量NPC仍受限量开关约束。'])
                  assert(PD.SettingRaw('autoAllowCurrencyFormulas','alchemy')==true)
                  PD.SetSettingRaw('autoAllowCurrencyFormulas',false,'alchemy')
                  rows={};PD.RowsSettings(rows)
                  a=ns.ProfRouteAuto.OptionsFor('alchemy',1)
                  assert(a.allowBindOnPickupFormulas and not a.allowCurrencyFormulas)
                  PD.SetSettingRaw('autoAllowBindOnPickupFormulas',false,'alchemy')
                  assert(PD.SettingRaw('autoAllowCurrencyFormulas','alchemy')==false)
                ''')

    def test_gold_plus_single_currency_is_displayed_as_an_exchange_with_all_costs(self):
        self.lua.execute('''
          ns.ProfRouteAuto.MoneyStr=function(value)return 'gold:'..tostring(value)end
          local offer={id=9,npcID=9,price=300,currencies={{id=7,count=2}},costItems={{id=8,count=3}}}
          local text=PD.FormulaCostText(offer)
          assert(text:find('Item7 ×2',1,true) and text:find('Item8 ×3',1,true) and text:find('gold:300',1,true))
          PD.VendorLines=function()return {}end;PD.FormulaAuctionLine=function()end
          PD.VendorAct=function()end
          local route={kind='item',teachingItemID=88,acquisition={vendors={offer}}}
          local recipe={spell=101,formula=88,profession='alchemy',learningInfo={routes={route}}}
          local card=PD.LearningOriginCard(recipe,{allowed=true,route=route})
          assert(card.kind=='currency' and card.text==ns.L['图纸 · 通货兑换'])
        ''')

    def test_pending_acquisition_has_a_label_unknown_cost_and_no_auction_scan_item(self):
        self.lua.execute('''
          PD.DropEntries=function()return {}end;PD.VendorListOf=function()return {}end
          local e={id=88,spell=101,source='acquire',acquisitionKind='currency',acquisitionPending=true,
            usable=true,costComplete=false,unpriced=true,acquisitionOffers={{currencyID=7,currencyAmount=2}}}
          local data={formulas={e}};local rows={};PD.RowsFormulaShop(rows,data)
          local found=false
          for _,row in ipairs(rows)do if row.it and row.it[1]==88 then
            found=true
            assert(row.tag.text==ns.L['通货兑换'])
            assert(row.right2==ns.L['获取或兑换总成本未确认'])
            assert(row.lines[#row.lines][1]:find('×2',1,true))
          end end
          assert(found and e.cost==nil and #PD.RouteSupplyItems(data)==0)
          assert(PD.FormulaBlockedText(e)==nil)
        ''')

    def test_mixed_exchange_keeps_known_gold_and_unpriced_costs_visible(self):
        self.lua.execute('''
          ns.ProfRouteAuto.MoneyStr=function(value)return 'gold:'..tostring(value)end
          PD.DropEntries=function()return {}end;PD.VendorListOf=function()return {}end
          local e={id=88,spell=101,source='acquire',acquisitionKind='currency',acquisitionPending=true,
            cost=50,knownGoldCost=50,usable=true,costComplete=false,unpriced=true,
            acquisitionOffers={{price=50,currencies={{id=7,count=2}},costItems={{id=8,count=3}}}}}
          for _,mode in ipairs({'limited','unknown'})do
          e.limited=mode=='limited';e.stockUnknown=mode=='unknown';e.availabilityUncertain=true
          local rows={};PD.RowsFormulaShop(rows,{formulas={e}})
          local found=false
          for _,row in ipairs(rows)do if row.it and row.it[1]==88 then
            found=true
            assert(row.tag.text==ns.L['通货兑换'])
            assert(row.right2=='gold:50 · '..ns.L['获取或兑换总成本未确认'])
            local costs=row.lines[#row.lines][1]
            assert(costs:find('gold:50',1,true) and costs:find('Item7 ×2',1,true) and costs:find('Item8 ×3',1,true))
            local warning=ns.L[mode=='limited' and '限量商人报价仅作参考，不能保证到访时有货。' or '商人库存：性质尚未核实']
            local warned=false;for _,line in ipairs(row.lines)do if line[1]==warning then warned=true end end
            assert(warned,'the acquisition quote lost its stock warning')
          end end
          assert(found and e.acquisitionPending and not e.costComplete)
          end
        ''')

    def test_disabled_bound_acquisition_rechecks_newly_owned_pattern(self):
        self.lua.execute('''
          local E,XP=ns.ProfEconomy,ns.ProfExecution
          ns.IsForever=true;E.RouteRecipeEligibility=function()return true end
          local ready=false;local calls=0
          E.SelectLearningRoute=function(recipe,snapshot,state,remaining,source,pricing)
            assert(not pricing.allowBindOnPickupFormulas and not pricing.allowCurrencyFormulas)
            calls=calls+1
            local quote={id=88,source=ready and 'owned' or 'none',usable=ready}
            return ready,not ready and 'bindOnPickupFormulaDisabled' or nil,{quote=quote}
          end
          local plan={learningPolicyFingerprint=E.LearningPolicyFingerprint and E.LearningPolicyFingerprint()}
          local step={spell=101,recipe=fixture().recipes[1]}
          local ok,reason=XP.ValidateLearning(plan,'alchemy',step)
          assert(not ok and reason=='bindOnPickupFormulaDisabled')
          ready=true
          assert(XP.ValidateLearning(plan,'alchemy',step) and calls==2)
        ''')

    def test_acquisition_pending_is_rechecked_after_inventory_changes(self):
        self.lua.execute('''
          local E,XP=ns.ProfEconomy,ns.ProfExecution
          ns.IsForever=true;E.RouteRecipeEligibility=function()return true end
          local ready=false;local calls=0
          E.SelectLearningRoute=function()
            calls=calls+1;return true,nil,{quote={source=ready and 'owned' or 'acquire',acquisitionPending=not ready}}
          end
          local plan={learningPolicyFingerprint=E.LearningPolicyFingerprint and E.LearningPolicyFingerprint()}
          local step={spell=101,recipe=fixture().recipes[1]}
          local ok,reason=XP.ValidateLearning(plan,'alchemy',step)
          assert(not ok and reason=='formulaAcquisitionPending')
          ready=true
          assert(XP.ValidateLearning(plan,'alchemy',step) and calls==2)
          ready=false
          assert(not XP.ValidateLearning(plan,'alchemy',step) and calls==3)
        ''')

    def test_formula_stock_invalidates_cache_when_material_stock_is_off(self):
        self.lua.execute('''
          local E,RA=ns.ProfEconomy,ns.ProfRouteAuto
          PD.SetSettingRaw('autoConsiderAuctionSupply',false,'alchemy')
          local revision=1;local stock={quantity=2,observedAt=1000,complete=true,ownerExcluded=true,source='client-auction-results'}
          ns.AuctionBridge={SupplyRevision=function()return revision end,GetAuctionSupply=function()return stock end}
          local before=RA.QuoteSig('alchemy');revision=2;assert(before~=RA.QuoteSig('alchemy'))
          local s=fixture();s.known={};s.considerAuctionSupply=false;s.recipes[1].formula=88
          s.stamp=1000;s.auctionSupply={[88]=E.Copy(stock)};s=E.Index(s)
          local result={formulas={{id=88,source='ah'}},mats={}}
          RA.StampSupply(result,s)
          assert(result.formulaAuctionSupplyInputs[88].quantity==2 and result.formulas[1].considerAuctionSupply)
          stock.quantity=1;assert(E.AuctionSupplyChanged(result))
        ''')

    def test_solver_retains_unknown_acquisition_cost_without_inventing_gold(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local s=fixture();s.known={};s.recipes[1].formula=88
          E.FormulaFor=function(r)
            return {id=88,recipeKey=r.key,spell=r.spell,source='acquire',usable=true,
              acquisitionKind='drop',acquisitionPending=true,costComplete=false,unpriced=true}
          end
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim'})do
            local result=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=2,scheme=scheme})
            assert(result.targetReached and #result.formulas==1,scheme)
            assert(result.formulas[1].source=='acquire' and result.formulas[1].cost==nil)
            assert(not result.costComplete and not result.formulaComplete and result.total==7)
            assert(not result.optimal and not result.inputModelOptimal)
          end
          ns.ProfRecipes.alchemy.rows[1][13]={88}
          local fixed=ns.ProfRouteAuto.FixedPlan('alchemy',{snapshot=s,start=1,target=2,recoveryEnabled=false})
          assert(#fixed.steps==1 and #fixed.formulas==1 and fixed.formulas[1].cost==nil)
          assert(fixed.costComplete==false and fixed.completeCost==false and fixed.formulaComplete==false)
          assert(not fixed.optimal and not fixed.inputModelOptimal)
        ''')

    def test_mixed_exchange_gold_is_budgeted_once_in_all_routes(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local s=fixture();s.known={};s.recipes[1].formula=88
          E.FormulaFor=function(r)
            return {id=88,recipeKey=r.key,spell=r.spell,source='acquire',usable=true,
              cost=50,knownGoldCost=50,npcID=9,acquisitionKind='currency',acquisitionPending=true,
              costComplete=false,unpriced=true,acquisitionOffers={{npcID=9,price=50,currencyID=7,currencyAmount=2}}}
          end
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim'})do
            local result=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=2,scheme=scheme})
            assert(result.targetReached and #result.formulas==1,scheme)
            assert(result.formulas[1].source=='acquire' and result.formulas[1].cost==50)
            assert(not result.costComplete and not result.formulaComplete and result.total==57)
            assert(result.vendorTotal==50 and result.ahTotal==7,scheme..':'..tostring(result.vendorTotal)..':'..tostring(result.ahTotal))
            assert(not result.optimal and not result.inputModelOptimal)
          end
          ns.ProfRecipes.alchemy.rows[1][13]={88}
          local fixed=ns.ProfRouteAuto.FixedPlan('alchemy',{snapshot=s,start=1,target=2,recoveryEnabled=false})
          assert(#fixed.formulas==1 and fixed.formulas[1].cost==50)
          assert(fixed.total==57 and fixed.vendorTotal==50 and fixed.ahTotal==7)
          assert(fixed.costComplete==false and fixed.completeCost==false and fixed.formulaComplete==false)
          assert(not fixed.optimal and not fixed.inputModelOptimal)
        ''')


if __name__ == '__main__':
    unittest.main()
