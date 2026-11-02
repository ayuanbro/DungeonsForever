"""Real shipped learning sources drive recipe, route and exclusion labels.

UI widgets and money/name formatting are mocked. These source/consumer checks
do not establish availability in a live game client or rendered pixel layout.
"""
import unittest

from test_prof_native_data import ROOT
from test_prof_production_learning import production_runtime
from test_prof_ui_fusion import UI_MOCKS


def production_ui_runtime():
    lua = production_runtime()
    lua.execute('savedNativeData={recipes=ns.ProfRecipes,leveling=ns.ProfLeveling,prof=ns.ProfData}')
    lua.execute(UI_MOCKS)
    lua.execute('''
      ns.ProfRecipes=savedNativeData.recipes
      ns.ProfLeveling=savedNativeData.leveling
      ns.ProfData=savedNativeData.prof
      ns.ProfRouteAuto.MatListCost=function()return 1,0 end
      ns.ProfRouteAuto.MoneyStr=function(n)return tostring(n) end
      ns.AuctionBridge={GetAuctionSupply=function()return {
        quantity=100000,observedAt=1000,complete=true,ownerExcluded=true,
        source='client-auction-results',market=1}
      end}
    ''')
    lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                (ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig'))
    lua.execute('''
      PD=ns.ProfModule;PD.cur='alchemy';PD.ProfLearned=function()return {}end
      PD.DropLines=function()return {}end;PD.VendorLines=function()return {}end
      PD.FormulaAuctionLine=function()return {'AH quote'}end
      PD.ItemName=function(id)return 'Item'..tostring(id),true end
      PD.KitSub=function()return ''end;PD.AhPct=function()end
      PD.ScheduleSweep=function()end
      function nativeAlchemyRow(spell)
        for _,row in ipairs(ns.ProfRecipes.alchemy.rows)do if row[1]==spell then return row end end
      end
    ''')
    return lua


class ProductionLearningUITests(unittest.TestCase):
    def setUp(self):
        self.lua = production_ui_runtime()

    def test_minor_fortitude_uses_the_selected_trainer_in_all_source_views(self):
        self.lua.execute('''
          ns.ProfRouteAuto.AHPriceOf=function()return 1000 end
          local raw=nativeAlchemyRow(2334)
          assert(raw[13][1]==2554)
          local resolved=PD.RecipeData(raw,'rows','alchemy')
          assert(resolved.learningInfo and resolved.learningInfo.spell==2334)
          local view=PD.RecipeLearningView(resolved,false)
          assert(view.allowed and view.route.kind=='trainer' and view.quote.cost==250)
          local card=PD.CardOf(raw,nil,resolved,'alchemy',false)
          assert(card.kind=='trainer' and card.fid==nil and card.text==ns.L['训练师'])
          assert(PD.LevelSrc(raw,'alchemy')==ns.L['向训练师学习'])
          local spec=PD.RecipeSpec(raw)
          assert(spec.right2==ns.L['训练师'] and spec.dpre==nil and spec.dval==nil)
          assert(spec.src==nil and spec.vlines==nil and spec.row[13]==nil)
          assert(raw[13][1]==2554,'source projection mutated the native recipe record')
        ''')

    def test_route_card_preserves_the_frozen_item_path_when_catalogue_prefers_trainer(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local raw=nativeAlchemyRow(2334)
          local resolved=E.FindRecipe('alchemy',2334)
          local allowed,_,detail=E.SelectLearningRoute(resolved,nil,{skill={alchemy=50}},nil,nil,
            {noFormula=false,considerAuctionSupply=true})
          assert(allowed and detail.route.kind=='item' and detail.quote.id==2554)
          PD.autoSnapshotSlug='alchemy';PD.autoSnapshot={formulas={detail.quote}}
          local card=PD.CardOf(raw,nil,resolved,'alchemy')
          assert(card.kind=='ah' and card.fid==2554,
            'painting a frozen route reselected its learning source')
          assert(PD.LevelSrc(raw,'alchemy',resolved,true)==card.text)
          assert(PD.CardOf(raw,nil,resolved,'alchemy',false).kind=='trainer')
          resolved.selectedLearningRoute=detail.route;resolved.learningQuote=detail.quote
          PD.autoSnapshot=nil
          assert(PD.CardOf(raw,nil,resolved,'alchemy').fid==2554)
        ''')

    def test_unknown_origin_with_verified_auction_price_is_eligible_and_excludable(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local raw=nativeAlchemyRow(2365)
          local resolved=PD.RecipeData(raw,'rows','alchemy')
          assert(PD.RecipeLearningView(resolved,false).allowed)
          local card=PD.CardOf(raw,nil,resolved,'alchemy',false)
          assert(card.kind=='ah' and card.text==ns.L['图纸 · 拍卖行'] and card.fid==2556)
          local warned=false
          for _,line in ipairs(card.lines)do if line[1]==ns.L['学习资料待补全'] then warned=true end end
          assert(not warned,'missing origin incorrectly blocks a verified auction purchase')
          assert(PD.RecipeSpec(raw).right2==ns.L['图纸 · 拍卖行'])
          E.SetPolicy('alchemy','alchemy',2365,'ban',false)
          E.SetPolicy('alchemy','alchemy',2334,'ban',false)
          PD.exReg={slug='alchemy',map={['alchemy:2365']={'alchemy',2365}}}
          local candidates=PD.ExclusionEntries()
          assert(#candidates==2)
          assert(PD.CountBans()==2)
          assert(E.GetPolicies('alchemy',false)['alchemy:2365']=='ban',
            'eligibility reevaluation deleted the saved exclusion')
          local rows={};PD.RowsExclusions(rows)
          local count=0
          for _,row in ipairs(rows)do for _,candidate in ipairs(row.cards or {})do
            count=count+1
          end end
          assert(count==2)
        ''')

    def test_complete_roster_absence_removes_even_a_previously_confirmed_candidate(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          E.SetPolicy('alchemy','alchemy',2334,'ban',false)
          assert(PD.RecipeExclusionEligible('alchemy',2334))
          E.EnsureClientRuntime()
          E.ClientStore().recipeRosters={alchemy={complete=true,ids={[7183]=true}}}
          assert(not PD.RecipeExclusionEligible('alchemy',2334))
          assert(#PD.ExclusionEntries()==0 and PD.CountBans()==0)
          assert(E.GetPolicies('alchemy',false)['alchemy:2334']=='ban')
        ''')


if __name__ == '__main__':
    unittest.main()
