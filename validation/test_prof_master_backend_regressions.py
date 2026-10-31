"""Master purchasing/knowledge contracts in the shared native route backend."""
import unittest
from test_prof_native_data import native_runtime
import test_prof_route_plans as routes


class NativeBackendRegressions(unittest.TestCase):
    def test_known_recipe_keeps_positive_evidence_from_all_client_readers(self):
        lua=native_runtime()
        lua.execute('''
          C_SpellBook={IsSpellKnown=function()return false end}
          IsSpellKnown=function()return false end
          observedKnown={[7751]=true}
          assert(ns.ProfEconomy.Known(7751), 'an unsupported spell-book false masked the recipe')
          assert(not ns.ProfEconomy.Known(7752))
          -- A specialization false remains authoritative; its tri-state reader
          -- intentionally does not share recipe fallback semantics.
          assert(ns.ProfEconomy.SpecializationKnown(7751)==false)
        ''')

    def test_maxed_native_cooking_is_a_completed_goal_without_an_optimization_claim(self):
        lua=native_runtime()
        lua.execute('''
          selected='cooking'
          local r=ns.ProfRouteSolver.Compute('cooking',{start=300,target=300,autoCraftTools=false})
          assert(r.targetReached and r.alreadyAtTarget and #r.steps==0 and #r.executionSteps==0)
          assert(not r.inputModelOptimal and not r.optimal)
          local s=ns.ProfEconomy.Capture('cooking',{start=1,target=2,autoCraftTools=false})
          assert(s.vendorItems[2678], 'native cooking supplier quote was lost')
          assert(not s.vendorOnlyItems, 'NPC availability must not prohibit AH comparison')
          observedKnown={[2540]=true}
          s=ns.ProfEconomy.Capture('cooking',{start=1,target=2,autoCraftTools=false})
          s.recipes={ns.ProfEconomy.FindRecipe('cooking',2540)};s=ns.ProfEconomy.Index(s)
          r=ns.ProfRouteSolver.Compute('cooking',{snapshot=s,start=1,target=2,autoCraftTools=false})
          assert(r.targetReached and not r.alreadyAtTarget and #r.steps==1 and r.steps[1][3]==2540)
        ''')

    def test_native_trainer_recipe_does_not_require_its_reference_pattern(self):
        lua=native_runtime()
        lua.execute('''
          local E=ns.ProfEconomy
          local r=E.FindRecipe('alchemy',2334)
          assert(r.formula==2554 and E.LearningSource(r)=='trainer')
          assert(E.FormulaFor(r,{known={},prices={},noFormula=true})==nil)
          assert(ns.ProfRecipes.alchemy.rows[1], 'catalogue was not loaded')
        ''')

    def test_native_item_taught_recipe_adds_its_pattern_once_and_known_recipe_does_not(self):
        lua=native_runtime()
        lua.execute('''
          selected='cooking'
          local E=ns.ProfEconomy
          local recipe=E.FindRecipe('cooking',7751)
          assert(recipe.formula==6325 and E.LearningSource(recipe)~='trainer')
          local s={recipes={recipe},professions={cooking={cur=1,max=300}},known={},prices={[6291]=7},
            offers={},formulaOffers={[6325]={{npcID=5494,price=25,quantity=1,unlimited=true,
              stock=-1,maxStock=-1,stockStatus='unlimited'}}},auctionSupply={[6291]={quantity=20}},
            toolGoals={},specializationContext={}}
          local r=ns.ProfRouteSolver.Compute('cooking',{snapshot=s,start=1,target=3,noFormula=true,
            autoCraftTools=false,cpuLimitMs=1000})
          assert(r.targetReached and #r.formulas==1)
          local f=r.formulas[1]
          assert(f.id==6325 and f.source=='vendor' and f.npcID==5494 and f.count==1 and f.cost==25)
          assert(f.stock==-1 and f.stockStatus=='unlimited' and r.total==39)
          s.known={['cooking:7751']=true}
          r=ns.ProfRouteSolver.Compute('cooking',{snapshot=s,start=1,target=3,noFormula=true,
            autoCraftTools=false,cpuLimitMs=1000})
          assert(r.targetReached and #r.formulas==0 and r.total==14)
        ''')

    def test_default_formula_stock_policy_rejects_unknown_as_well_as_limited_stock(self):
        lua=native_runtime()
        lua.execute('''
          local E=ns.ProfEconomy
          local recipe={profession='alchemy',spell=999,key='alchemy:999',formula=1000,
            source={drops={{npc='Reference drop'}}}}
          local s={known={},prices={},noFormula=true,allowLimitedFormulas=false,
            formulaOffers={[1000]={{npcID=9,price=30,quantity=1,unlimited=false,
              stockUnknown=true,stockStatus='unknown'}}}}
          local f=E.FormulaFor(recipe,s)
          assert(not f.usable and f.stockUnknown and not f.limited)
          s.allowLimitedFormulas=true;f=E.FormulaFor(recipe,s)
          assert(f.usable and not f.costComplete and f.source=='vendor')
          assert(f.sources.drops[1].npc=='Reference drop', 'procurement erased acquisition provenance')
        ''')


class SharedPurchasingRegressions(unittest.TestCase):
    setUp=routes.NativeRoutePlansTests.setUp

    def test_cheaper_npc_purchases_keep_stock_metadata_in_every_strategy(self):
        self.lua.execute('''
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim'}) do
            local s=fixture();s.vendorOnlyItems={[11]=true}
            s.prices[11]=20
            s.offers={[11]={{npcID=7,price=15,quantity=5,unlimited=true,limited=false,
              stock=-1,maxStock=-1,stockUnknown=false,stockStatus='unlimited'}}}
            local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=2,scheme=scheme,
              autoCraftTools=false})
            assert(r.targetReached and r.vendorTotal==15 and r.ahTotal==0,scheme)
            local m=r.mats[1]
            assert(m.id==11 and m.source=='vendor' and m.npcID==7 and m.count==5,scheme)
            assert(m.unlimited==true and m.limited==false and m.stock==-1 and m.maxStock==-1
              and m.stockUnknown==false and m.stockStatus=='unlimited',scheme..' lost supplier stock')
            assert(not r.vendorOnlyItems)
            for _,a in ipairs(r.actions) do
              if a.type=='buy' then assert(a.source=='vendor' and a.unlimited==true and a.stock==-1)end
            end
          end
        ''')

    def test_old_vendor_source_hint_does_not_block_quoted_auction_fallback(self):
        self.lua.execute('''
          local s=fixture();s.vendorOnlyItems={[11]=true};s.prices[11]=1;s.offers={}
          local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=2,autoCraftTools=false})
          assert(r.targetReached and r.ahTotal==1 and r.vendorTotal==0)
          assert(r.mats[1].id==11 and r.mats[1].source=='ah')
        ''')

    def test_old_cost_policy_requires_recalculation_without_claiming_settings_changed(self):
        self.lua.execute('''
          local E,ra=ns.ProfEconomy,ns.ProfRouteAuto
          E.Capture=function()return E.Index(fixture())end
          local opts={start=1,target=3,autoCraftTools=false}
          local r=finish('alchemy',opts)
          assert(r.procurementPolicyVersion==ns.ProfRouteSolver.ProcurementPolicyVersion)
          local id=r.planID;r.procurementPolicyVersion=2
          r=ra.Get('alchemy',opts)
          assert(r.planID==id and r.stale and r.staleReason=='procurement-policy' and not r.settingsChanged)
          ra.Recalculate('alchemy',opts);r=finish('alchemy',opts)
          assert(r.planID~=id and not r.stale and not r.settingsChanged)
        ''')

    def test_auction_price_and_stock_changes_invalidate_npc_material_comparison(self):
        self.lua.execute('''
          local E,ra=ns.ProfEconomy,ns.ProfRouteAuto
          ns.ProfModule={ProfLearned=function()return skills end}
          ns.ProfRecipes={alchemy={rows={{101,10,1,'',nil,nil,1,100,200,300,false,{{11,1}}}}}}
          ns.ProfLeveling={alchemy={sold={11}}}
          IsPlayerSpell=function()return true end
          local auctionPrice,auctionQuantity=10,100
          ra.AHPriceOf=function(id)if id==11 then return auctionPrice end end
          ns.VendorPriceDB={GetOffers=function(id)
            if id==11 then return {{npcID=7,price=7,quantity=1,unlimited=true}}end
            return {}
          end}
          ns.AuctionBridge={GetAuctionSupply=function(id)
            if id==11 then return {quantity=auctionQuantity,observedAt=clock,complete=true,
              ownerExcluded=true,source='client-auction-results'}end
          end}
          local opts={start=1,target=3,autoCraftTools=false,recoveryEnabled=false,considerAuctionSupply=true}
          local r=finish('alchemy',opts);local id=r.planID
          assert(r.targetReached and r.ahTotal==0 and r.vendorTotal==14)
          assert(r.auctionPriceInputs[11]==10 and r.auctionSupplyInputs[11].quantity==100)
          auctionPrice=2
          r=ra.Get('alchemy',opts)
          assert(r.planID==id and r.stale and not r.settingsChanged)
          ra.Recalculate('alchemy',opts);r=finish('alchemy',opts)
          assert(r.ahTotal==4 and r.vendorTotal==0)
          id=r.planID;auctionQuantity=1
          r=ra.Get('alchemy',opts)
          assert(r.planID==id and r.stale and not r.settingsChanged)
          ra.Recalculate('alchemy',opts);r=finish('alchemy',opts)
          assert(r.ahTotal==2 and r.vendorTotal==7)
          auctionQuantity=3;opts.recoveryEnabled=true;ra.Recalculate('alchemy',opts);r=finish('alchemy',opts)
          assert(r.auctionPriceInputs[11]==2 and r.auctionSupplyInputs[11].quantity==3,
            'market comparison lost its input quotes')
        ''')


if __name__=='__main__':unittest.main()
