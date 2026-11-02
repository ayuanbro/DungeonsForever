"""Reported formula purchases against shipped data and native fixed-route/UI code.

Offline Lua 5.1 checks; stock listings are not live merchant observations.
"""
import unittest

from test_prof_native_data import ROOT
from test_prof_production_learning_ui import production_ui_runtime


class FormulaPurchaseReportTests(unittest.TestCase):
    def setUp(self):
        self.lua = production_ui_runtime()
        self.lua.execute('''
          CreateFrame=function()return {RegisterEvent=function()end,SetScript=function()end}end
          C_Timer={After=function()end}
        ''')
        self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                         (ROOT/'Core/ProfRouteAuto.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          ns.ProfRouteAuto.AHPriceOf=function(id)
            if id==13501 or id==6056 then return nil end
            return 59460
          end
          ns.ProfRouteAuto.NPCSellPriceOf=function()return 1 end
          ns.AuctionBridge={GetAuctionSupply=function()
            return {quantity=2,observedAt=time(),complete=true,ownerExcluded=true,source='client-auction-results'}
          end}
          PD.Wrap=function(text)return {text}end
          PD.Fit=function(text)return text end
          PD.DropEntries=function()return {}end;PD.VendorEntries=function()return {}end
          function purchaseRows(entry)
            local rows={};PD.RowsFormulaShop(rows,{formulas={entry}})
            local item;for _,row in ipairs(rows)do if row.it then item=row;break end end
            return rows,assert(item)
          end
        ''')

    def test_bound_major_mana_market_priority_in_fast_exact_fixed_and_shopping_views(self):
        self.lua.execute('fastCompute=ns.ProfRouteAuto.Compute;ns.ProfRouteAuto.AHPriceOf=function()return 1 end')
        self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                         (ROOT/'Core/ProfRoutePlans.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',17580)
          local s=E.Capture('alchemy',{start=295,target=296})
          for _,candidate in ipairs(s.recipes)do
            if candidate.spell~=17580 then E.SetPolicy('alchemy',candidate.profession,candidate.spell,'ban',false)end
          end
          s.policies=E.GetPolicies('alchemy')
          s.recipes={r};s.byKey={};s.byItem={};s.known={};s.professions.alchemy={cur=295,max=300}
          s=E.Index(s);assert(s.nonAuctionable[13501])
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim'})do
            for _,compute in ipairs({fastCompute,ns.ProfRouteAuto.Compute})do
              local result=compute('alchemy',{snapshot=s,start=295,target=296,scheme=scheme,recoveryEnabled=false})
              assert(result.targetReached and #result.formulas==1,scheme)
              local q=result.formulas[1]
              assert(q.id==13501 and q.source=='ah' and q.cost==1 and q.usable)
              local _,row=purchaseRows(q)
              assert(row.tag.text==ns.L['拍卖行'] and not PD.FormulaBlockedText(q))
              assert(result.formulaAuctionSupplyInputs[13501].quantity==2)
            end
          end
          local fixed=ns.ProfRouteAuto.FixedPlan('alchemy',{snapshot=s,target=300,recoveryEnabled=false})
          local found=false
          for _,q in ipairs(fixed.formulas)do if q.id==13501 then
            found=true;assert(q.source=='ah' and q.cost==1 and q.usable)
            local _,row=purchaseRows(q);assert(not PD.FormulaBlockedText(q))
          end end
          assert(found)
        ''')

    def test_major_mana_is_an_unlimited_three_gold_vendor_purchase_for_all_current_classes(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local r=E.FindRecipe('alchemy',17580)
          assert(r.formula==13501 and r.learn==295)
          assert(#r.learningInfo.missingReasons==0)
          for _,class in ipairs({1,2,3,4,5,7,8,9,11})do
            UnitClass=function()return 'Class','CLASS',class end
            local q=assert(E.FormulaFor(r,{noFormula=true,allowLimitedFormulas=false,
              allowBindOnPickupFormulas=false,allowCurrencyFormulas=false}))
            assert(q.usable and q.source=='vendor' and q.npcID==11278)
            assert(q.cost==30000 and q.vendorPrice==30000 and q.unlimited and not q.limited)
            assert(not q.ahPrice,'a bound teaching item became auctionable')
            local _,row=purchaseRows(q)
            assert(row.tag.text==ns.L['NPC购买'] and not PD.FormulaBlockedText(q))
          end
          local plan=ns.ProfRouteAuto.FixedPlan('alchemy',{target=300,noFormula=true,
            allowBindOnPickupFormulas=false,allowCurrencyFormulas=false,recoveryEnabled=false})
          local found=false
          for _,q in ipairs(plan.formulas)do if q.id==13501 then
            found=true;assert(q.usable and q.unlimited and q.cost==30000)
          end end
          assert(found,'fixed guide lost its major-mana formula')
        ''')

    def test_real_auction_quotes_are_used_when_settings_allow_them(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          for _,spell in ipairs({6618,17554})do
            local r=E.FindRecipe('alchemy',spell)
            local q=E.FormulaFor(r,{noFormula=false,allowLimitedFormulas=false})
            assert(q.usable and q.source=='ah' and q.cost==59460 and q.vendorPrice>0)
            local _,row=purchaseRows(q)
            assert(row.tag.text==ns.L['拍卖行'] and not PD.FormulaBlockedText(q))
            for _,line in ipairs(row.lines)do
              assert(not line[1]:find('没有可靠购买来源',1,true))
            end
          end
        ''')

    def test_missing_recent_stock_keeps_known_quotes_and_explains_the_actual_block(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          ns.AuctionBridge.GetAuctionSupply=function()return nil end
          local q=E.FormulaFor(E.FindRecipe('alchemy',17554),{noFormula=true,allowLimitedFormulas=false})
          assert(not q.usable and q.blocked and q.reason=='formulaAuctionSupplyUnknown')
          assert(q.ahPrice==59460 and q.vendorPrice==13684 and q.cost==nil)
          local rows,row=purchaseRows(q)
          assert(row.tag.text==ns.L['尚无购买来源'])
          local warning=PD.FormulaBlockedText(q)
          assert(warning:find('缺少最近的可购数量',1,true))
          assert(not warning:find('只使用商人有定价的图纸',1,true))
          assert(not warning:find('没有可靠购买来源',1,true))
          assert(not warning:find('拍卖行没有报价',1,true))
          local inline,tooltip=false,false
          for _,r in ipairs(rows)do if r.text==warning then inline=true end end
          for _,line in ipairs(row.lines)do if line[1]==warning then tooltip=true end end
          assert(inline and tooltip)
          local allowed=E.FormulaFor(E.FindRecipe('alchemy',17554),{noFormula=true,allowLimitedFormulas=true})
          assert(allowed.usable and allowed.source=='vendor' and allowed.cost==13684 and allowed.limited)
        ''')

    def test_missing_learning_details_preserve_quotes_without_authorizing_purchase(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local r=E.FindRecipe('alchemy',17554)
          r.learningRoutes={};r.learningInfo={profession='alchemy',spell=17554,coverage='partial',
            missingReasons={'unsupportedPlayerCondition'},routes={{id='unresolved',kind='item',teachingItemID=13478,
              status='unknown',conditionsKnown=false,conditions={{kind='playerCondition',value=123}},acquisition={nonAuctionable=false}}}}
          local q=E.FormulaFor(r,{noFormula=false,allowLimitedFormulas=true})
          assert(not q.usable and q.reason=='learningDataMissing' and q.cost==nil)
          assert(q.ahPrice==59460 and q.vendorPrice==13684 and q.limited)
          assert(q.source=='unknown' and not q.vendor and not q.npcID)
          local _,row=purchaseRows(q)
          assert(row.tag.text==ns.L['学习资料待补全'])
          local warning=PD.FormulaBlockedText(q)
          assert(warning:find('附加学习条件尚未解读',1,true))
          assert(not warning:find('没有可靠购买来源',1,true))
          r.learningInfo.routes[1].acquisition.nonAuctionable=true
          assert(E.FormulaFor(r,{noFormula=false}).ahPrice==59460)
        ''')

    def test_empty_frozen_quotes_do_not_read_live_prices_for_blocked_learning(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local r=E.FindRecipe('alchemy',17554)
          r.learningRoutes={};r.learningInfo={profession='alchemy',spell=17554,routes={},missingReasons={'sourceMissing'}}
          ns.ProfRouteAuto.AHPriceOf=function()error('read live auction')end
          ns.VendorPriceDB.GetFormulaOffers=function()error('read live merchant')end
          local q=E.FormulaFor(r,{known={},prices={},formulaOffers={},offers={},learningSourcesRequired=true})
          assert(not q.usable and q.cost==nil and q.ahPrice==nil and q.vendorPrice==nil)
        ''')

    def test_ordinary_profession_class_field_does_not_block_valid_market_quote(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local r=E.FindRecipe('alchemy',17554)
          r.learningConstraints={{kind='classIDs',values={8}}}
          local q=E.FormulaFor(r,{noFormula=false,allowLimitedFormulas=false})
          assert(q.usable and q.source=='ah' and q.cost==59460 and q.vendorPrice==13684)
          local _,row=purchaseRows(q)
          assert(row.tag.text==ns.L['拍卖行'])
          assert(PD.FormulaBlockedText(q)==nil)
        ''')

    def test_retired_vendor_only_policy_cannot_exclude_an_available_auction_recipe(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local r=E.FindRecipe('alchemy',17554)
          local snapshot={known={},prices={[13478]=59460},formulaOffers={},offers={},
            noFormula=true,learningSourcesRequired=true,ownedTeachingItems={},stamp=1000,
            auctionSupply={[13478]={quantity=2,observedAt=900,complete=true,
              ownerExcluded=true,source='client-auction-results'}}}
          local q=E.FormulaFor(r,snapshot)
          assert(q.usable and q.source=='ah' and q.cost==59460)
          local _,row=purchaseRows(q)
          assert(row.tag.text==ns.L['拍卖行'] and not PD.FormulaBlockedText(q))
          snapshot.noFormula=false
          q=E.FormulaFor(r,snapshot)
          assert(q.usable and q.source=='ah' and q.cost==59460)
        ''')


if __name__=='__main__':
    unittest.main()
