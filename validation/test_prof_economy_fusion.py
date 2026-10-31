"""Behavioral checks for the dev profession input / client observation fusion."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".pipeline-runtime" / "lib"))
from lupa.lua51 import LuaRuntime


class EconomyFusionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            ns={LoadForeverPages=true,L=setmetatable({}, {__index=function(_,k)return k end})}
            DungeonsForeverDB={prof={}}
            function UnitName()return "Test" end
            function GetRealmName()return "Realm" end
            function UnitLevel()return 60 end
            function UnitFactionGroup()return "Alliance" end
            function time()return 1000 end
            function GetBuildInfo()return "1.60.1",70338 end
            function IsPlayerSpell()return false end
            ns.ProfModule={ProfLearned=function()return {alchemy={cur=1,max=75},enchanting={cur=10,max=75}}end}
            ns.ProfRecipes={alchemy={rows={{100,200,1,"",nil,nil,1,10,20,30,nil,{{300,2}}}}}}
            ns.ProfLeveling={alchemy={rinfo={}}}
            ns.ProfRouteAuto={AHPriceOf=function()return 999 end}
        """)
        for path in ("Core/ProfPolicies.lua", "Core/ProfGates.lua", "Core/ProfSolverCapture.lua", "Core/ProfClientScan.lua"):
            self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)", (ROOT / path).read_text(encoding="utf-8"))

    def run_lua(self, code):
        self.lua.execute(code)

    def test_client_materials_and_random_yield_use_guaranteed_minimum(self):
        self.run_lua("""
            ns.ProfEconomy.EnsureClientRuntime()
            ns.ProfRecipeRuntime[100]={mats={{301,3}},item=201,count=2,outputMin=2,outputMax=5,variableOutput=true,learned=true}
            local r=ns.ProfEconomy.FindRecipe('alchemy',100)
            assert(r.mats[1][1]==301 and r.mats[1][2]==3)
            assert(r.item==201 and r.count==2 and r.outputMax==5 and r.outputBasis=='minimum')
            assert(ns.ProfRecipes.alchemy.rows[1][12][1][1]==300)
        """)

    def test_empty_and_zero_sentinel_reads_preserve_reference_recipe(self):
        self.run_lua("""
            C_TradeSkillUI={GetRecipeNumReagents=function()return 0 end,GetRecipeReagentInfo=function()end,
                GetRecipeNumItemsProduced=function()return 0,0 end}
            ns.ProfEconomy.ReadRecipe(100)
            local r=ns.ProfEconomy.FindRecipe('alchemy',100)
            assert(r.mats[1][1]==300 and r.count==1 and not r.clientUnavailable)
        """)

    def test_foreign_book_never_overwrites_own_recipe(self):
        self.run_lua("""
            C_TradeSkillUI={IsTradeSkillLinked=function()return true end,
                GetRecipeInfo=function()return {recipeID=100,learned=true}end,
                GetRecipeSchematic=function()return {quantityMin=9,quantityMax=9}end}
            assert(ns.ProfEconomy.ReadRecipe(100)==nil)
            assert(ns.ProfEconomy.FindRecipe('alchemy',100).count==1)
        """)

    def test_learning_uses_simulated_specialization_and_trainer_requirements(self):
        self.run_lua("""
            ns.ProfSpecializations={[100]={2,20219}}
            local E=ns.ProfEconomy
            local r={spell=100,profession='alchemy',key='alchemy:100',learningRequirements={level=30,skill=20}}
            local snap={level=60,professions={alchemy={cur=1}},known={},specializationAbilities={[20219]=false}}
            local ok,why=E.LearningEligibility(r,snap,{skill={alchemy=10},specializationAbilities={}})
            assert(not ok and why=='skillRequired')
            ok,why=E.LearningEligibility(r,snap,{skill={alchemy=20},specializationAbilities={[20219]=true}})
            assert(ok and why==nil)
            snap.level=10
            ok,why=E.LearningEligibility(r,snap,{skill={alchemy=20},specializationAbilities={[20219]=true}})
            assert(not ok and why=='characterLevelRequired')
        """)

    def test_formula_uses_frozen_prices_and_finite_stock(self):
        self.run_lua("""
            local E=ns.ProfEconomy
            local r={spell=100,profession='alchemy',key='alchemy:100',formula=400}
            local snap={known={},prices={[400]=50},offers={},formulaOffers={[400]={{npcID=1,price=60,quantity=1,unlimited=true}}},
                stamp=1000,auctionSupply={[400]={quantity=2,observedAt=900,complete=true,
                  ownerExcluded=true,source='client-auction-results'}},allowLimitedFormulas=false}
            local f=E.FormulaFor(r,snap)
            assert(f.source=='ah' and f.cost==50)
            f=E.FormulaFor(r,snap,0)
            assert(f.source=='vendor' and f.cost==60)
            snap.prices[400]=nil;snap.formulaOffers[400]={}
            f=E.FormulaFor(r,snap)
            assert(not f.usable and f.cost==nil)
        """)

    def test_formula_bundle_is_not_divided_into_one_item_purchase(self):
        self.run_lua("""
            local E=ns.ProfEconomy
            local r={spell=100,profession='alchemy',key='alchemy:100',formula=400}
            local snap={known={},prices={[400]=50},stamp=1000,
                auctionSupply={[400]={quantity=2,observedAt=900,complete=true,
                  ownerExcluded=true,source='client-auction-results'}},
                formulaOffers={[400]={{npcID=1,price=80,quantity=2,unlimited=true}}}}
            assert(E.FormulaFor(r,snap).source=='ah')
            snap.prices={}
            local f=E.FormulaFor(r,snap)
            assert(f.source=='vendor' and f.cost==80 and f.count==2)
        """)

    def test_limited_formula_requires_explicit_policy(self):
        self.run_lua("""
            local E=ns.ProfEconomy
            local r={spell=100,profession='alchemy',key='alchemy:100',formula=400}
            local snap={known={},prices={},allowLimitedFormulas=false,
                formulaOffers={[400]={{npcID=1,price=20,quantity=1,limited=true,unlimited=false}}}}
            local f=E.FormulaFor(r,snap)
            assert(not f.usable and f.reason=='limitedFormulaDisabled')
            snap.allowLimitedFormulas=true
            f=E.FormulaFor(r,snap)
            assert(f.usable and f.availabilityUncertain)
        """)

    def test_snapshot_is_deep_copied_and_never_refreshes_live_supply(self):
        self.run_lua("""
            local E=ns.ProfEconomy
            ns.AuctionBridge={GetAuctionSupply=function()error('live read')end,SupplyFresh=function()error('live read')end}
            local input={recipes={{profession='alchemy',spell=100,learn=1,yellow=2,green=3,grey=4,mats={{300,2}}}},
                professions={alchemy={cur=1,max=75}},known={},prices={},auctionSupply={[300]={quantity=2}},toolGoals={},specializationContext={}}
            local out=E.Capture('alchemy',{snapshot=input})
            out.recipes[1].mats[1][2]=99
            assert(input.recipes[1].mats[1][2]==2)
            assert(out.auctionSupply[300].quantity==2 and out.coverageComplete==false)
            assert(type(E.Copy(nil))=='table')
        """)

    def test_supply_counts_formulas_and_materials_together(self):
        self.run_lua("""
            local E=ns.ProfEconomy
            local res={mats={{id=400,count=2,source='ah'}},formulas={{id=400,count=1,source='ah'}}}
            E.SummarizeAuctionSupply(res,{considerAuctionSupply=true,prices={[400]=1,[401]=1},auctionSupply={[400]={quantity=2,complete=true,ownerExcluded=true}}})
            assert(res.formulas[1].supplyLimited and res.supplyComplete==false)
            assert(res.auctionSupplyInputs[401]==false)
        """)

    def test_classic_book_observation_is_used_by_capture(self):
        self.run_lua("""
            GetNumTradeSkills=function()return 1 end
            GetTradeSkillInfo=function()return 'Potion','optimal' end
            GetTradeSkillRecipeLink=function()return 'spell:100' end
            GetTradeSkillItemLink=function()return 'item:201' end
            GetTradeSkillNumMade=function()return 2,4 end
            GetTradeSkillNumReagents=function()return 1 end
            GetTradeSkillReagentItemLink=function()return 'item:301' end
            GetTradeSkillReagentInfo=function()return 'Reagent',nil,3 end
            ns.ProfEconomy.ScanRecipes()
            local s=ns.ProfEconomy.Capture('alchemy',{target=10,autoCraftTools=false})
            assert(s.byKey['alchemy:100'].count==2)
            assert(s.byKey['alchemy:100'].mats[1][1]==301)
            assert(s.coverageComplete==false)
        """)

    def test_unknown_specialization_is_diagnosed_without_fabricating_a_block(self):
        self.run_lua("""
            ns.ProfSpecializations={[100]={4,20219}}
            local ok,why,detail=ns.ProfEconomy.LearningEligibility({spell=100,profession='alchemy'},
                {known={},specializationAbilities={}},{skill={alchemy=20},specializationAbilities={}})
            assert(ok and not why and detail.status=='unknown')
        """)


    def test_roster_from_guild_or_learned_only_book_cannot_prove_absence(self):
        self.run_lua("""
            C_TradeSkillUI={GetAllRecipeIDs=function()return {100}end,
                GetRecipeInfo=function()return {recipeID=100,learned=true}end,
                GetBaseProfessionInfo=function()return {professionID=171}end,
                IsDataSourceChanging=function()return false end,IsTradeSkillReady=function()return true end}
            ns.ProfEconomy.ScanRecipes()
            local d=ns.ProfEconomy.ClientStore()
            assert(not d.recipeRosters or not d.recipeRosters.alchemy)
            C_TradeSkillUI.IsTradeSkillGuild=function()return true end
            C_TradeSkillUI.GetRecipeInfo=function()return {recipeID=100,learned=false}end
            ns.ProfEconomy.ScanRecipes()
            assert(not d.recipeRosters or not d.recipeRosters.alchemy)
        """)

    def test_full_owned_roster_can_mark_a_missing_recipe_unavailable(self):
        self.run_lua("""
            ns.ProfRecipes.alchemy.rows[2]={101,202,1,'',nil,nil,1,10,20,30,nil,{{300,2}}}
            C_TradeSkillUI={GetAllRecipeIDs=function()return {100}end,
                GetRecipeInfo=function()return {recipeID=100,learned=false}end,
                GetBaseProfessionInfo=function()return {professionID=171}end,
                IsDataSourceChanging=function()return false end,IsTradeSkillReady=function()return true end}
            ns.ProfEconomy.ScanRecipes()
            assert(ns.ProfEconomy.ClientStore().recipeRosters.alchemy.complete)
            assert(ns.ProfEconomy.FindRecipe('alchemy',101).clientUnavailable)
        """)

    def test_real_specialization_api_namespace_is_resolved(self):
        self.run_lua("""
            C_SpellBook={IsSpellKnown=function(id)return id==20219 end}
            ns.ProfGates.Invalidate()
            assert(ns.ProfGates.Abilities()[20219]==true)
        """)


if __name__ == '__main__':
    unittest.main()
