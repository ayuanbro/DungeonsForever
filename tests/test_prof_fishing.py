"""Fishing-only cooking routes keep gathered fish out of purchase economics."""
import unittest

from test_prof_runtime import LuaRuntime, MOCKS, ROOT
from test_prof_follow import STUBS as FOLLOW_STUBS


class FishingCookingTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.load = self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        self.lua.execute("""
          ns.DB=function()
            DungeonsForeverDB=DungeonsForeverDB or {prof={}}
            DungeonsForeverDB.prof=DungeonsForeverDB.prof or {}
            return DungeonsForeverDB
          end
        """)
        for path in (
            'Core/Data/Data_ProfRecipes.lua',
            'Core/Data/Data_ProfLeveling.lua',
            'Core/Data/Data_ProfVendorOffers.lua',
            'Core/Data/Data_ProfFishingRoutes.lua',
            'Core/ProfEconomy.lua',
            'Core/ProfRouteSolver.lua',
            'Core/ProfFishing.lua',
            'Core/ProfRouteAuto.lua',
            'Core/VendorPriceDB.lua',
        ):
            self.load(str(ROOT / path))
        self.lua.execute(r'''
          function actualSnapshot(start)
            local s={recipes={},prices={},offers={},known={},
              professions={cooking={cur=start or 1,max=300},fishing={cur=300,max=300}}}
            for _,row in ipairs(ns.EnsureProfRecipes({'cooking'}).cooking.rows) do
              local r=ns.ProfEconomy.Normalize(row,'cooking','rows')
              if r then s.recipes[#s.recipes+1]=r;s.known[r.key]=true end
            end
            return ns.ProfEconomy.Index(s)
          end
          function fishRecipe(spell,mats,learn,grey)
            return {profession='cooking',key='cooking:'..spell,spell=spell,item=90000+spell,
              count=1,mats=mats,learn=learn or 1,yellow=grey or 100,
              green=grey or 100,grey=grey or 100,cooldown=false}
          end
          function fishSnapshot(recipes,prices,offers)
            local s={recipes=recipes,prices=prices or {},offers=offers or {},known={},
              professions={cooking={cur=1,max=300},fishing={cur=300,max=300}}}
            for _,r in ipairs(recipes)do s.known[r.key]=true end
            return ns.ProfEconomy.Index(s)
          end
          function fishSolve(s,start,target,extra)
            local o=extra or {};o.snapshot=s;o.start=start;o.target=target
            return ns.ProfFishing.Compute(o)
          end
          function fishCount(r,id)
            local total=0
            for _,m in ipairs(r.fishMaterials or {})do if m.id==id then total=total+m.count end end
            return total
          end
          function assertFishingSources(r)
            local count=0
            for _,m in ipairs(r.fishMaterials or {})do
              assert(m.source=='fishing' and #m.areas>0,'fish lacks own-fishing source or area')
              assert(m.count>0 and m.count==math.floor(m.count),'noninteger fish count')
              count=count+m.count
            end
            for _,m in ipairs(r.mats or {})do
              assert(m.source=='vendor' and m.vendor,'pure-fishing purchased a nonvendor reagent')
              assert(not ns.ProfFishingRoutes.fish[m.id],'fish became a shopping purchase')
            end
            for _,st in ipairs(r.steps or {})do
              assert(st.profession=='cooking' and #st.fishing>0,'cooking step has no fishing area')
              assert(st[4]>0 and st[4]==math.floor(st[4]),'noninteger crafts')
            end
            assert(count>0 or #(r.steps or {})==0)
          end
        ''')

    def test_actual_forever_catalogue_follows_fishing_guide_through_225(self):
        self.lua.execute('''
          local r=fishSolve(actualSnapshot(1),1,225)
          assert(r.planVersion==2 and r.targetReached and r.feasible)
          assert(r.start==1 and r.target==225 and r.plannedTo==225)
          local expected={7751,7753,7755,20916}
          assert(#r.steps==#expected and #r.executionSteps==#expected)
          for i,spell in ipairs(expected)do assert(r.steps[i][3]==spell,'guide recipe order')end
          assert(r.total==0 and r.ahTotal==0 and r.formulasTotal==0)
          assert(#r.formulas==0 and #r.mats==0 and #r.fishMaterials==4)
          assert(not r.pricePending and r.costComplete)
          assertFishingSources(r)
        ''')

    def test_actual_forever_catalogue_uses_easier_yellowtail_after_225(self):
        self.lua.execute('''
          local r=fishSolve(actualSnapshot(1),1,300)
          assert(r.targetReached and r.feasible and r.plannedTo==300)
          assert(r.steps[#r.steps][3]==18238,'default should use common inland/coastal yellowtail')
          assert(r.steps[#r.steps][1]==225,'high-level fish route did not start at225')
          assert(fishCount(r,4603)>0)
          assert(fishCount(r,13760)==0,'time-sensitive squid should not displace common fish')
          assert(r.ahTotal==0 and #r.mats==0);assertFishingSources(r)
        ''')

    def test_unlearned_factions_without_auctionator_can_buy_required_reference_recipes(self):
        self.lua.execute('''
          Auctionator=nil
          for _,faction in ipairs({'Alliance','Horde'})do
            UnitFactionGroup=function()return faction end
            local r=ns.ProfFishing.Compute({start=1,target=300})
            assert(r.targetReached and r.feasible and #r.steps==5,faction..' '..r.status)
            assert(#r.formulas==5 and r.ahTotal==0 and r.vendorTotal>0)
            assert(r.total==r.formulasTotal and r.matTotal==0)
            local total=0;for _,step in ipairs(r.steps)do total=total+step.cost end
            assert(total==r.total,'formula fees duplicated or not assigned to a step')
            for _,f in ipairs(r.formulas)do assert(f.vendor and f.unlimited and not f.blocked)end
          end
        ''')

    def test_partial_first_orange_interval_needs_only_remaining_crafts(self):
        self.lua.execute('''
          local s=actualSnapshot(1);s.inventory={[6291]=999}
          local r=fishSolve(s,1,35)
          assert(r.targetReached and #r.steps==1 and r.steps[1][3]==7751)
          assert(r.steps[1][1]==1 and r.steps[1][2]==35 and r.steps[1][4]==34)
          assert(fishCount(r,6291)==34,'old bank stock or guide full-count leaked into partial route')
        ''')

    def test_start_inside_guide_interval_does_not_replay_earlier_steps(self):
        self.lua.execute('''
          local r=fishSolve(actualSnapshot(65),65,70)
          assert(r.targetReached and #r.steps==1 and r.steps[1][3]==7753)
          assert(r.steps[1][1]==65 and r.steps[1][2]==70 and r.steps[1][4]==5)
          assert(fishCount(r,6289)==5 and fishCount(r,6291)==0)
        ''')

    def test_expected_yellow_green_crafts_round_once_using_existing_gain_model(self):
        self.lua.execute('''
          local s=actualSnapshot(140);local recipe=s.byKey['cooking:7755']
          local expected=0
          for skill=140,174 do
            expected=expected+1/ns.ProfRouteAuto.Gain(skill,recipe.learn,recipe.yellow,recipe.green,recipe.grey)
          end
          local r=fishSolve(s,140,175)
          assert(r.targetReached and #r.steps==1 and r.steps[1][3]==7755)
          assert(r.steps[1][4]==math.ceil(expected-1e-9),'gain probability changed between route modes')
          assert(fishCount(r,6308)==r.steps[1][4])
        ''')

    def test_only_fixed_vendor_spices_are_purchased_in_integer_packs(self):
        self.lua.execute('''
          local recipe=fishRecipe(7751,{{6291,2},{2678,3}})
          local s=fishSnapshot({recipe},{[6291]=999,[2678]=1},
            {[2678]={{unlimited=true,price=10,quantity=5,npcID=12022}}})
          local r=fishSolve(s,1,4)
          assert(r.targetReached and fishCount(r,6291)==6)
          assert(#r.mats==1 and r.mats[1].id==2678 and r.mats[1].count==10)
          assert(r.matTotal==20 and r.vendorTotal==20 and r.total==20 and r.ahTotal==0)
          assertFishingSources(r)
        ''')

    def test_limited_vendor_spice_and_auction_price_do_not_qualify(self):
        self.lua.execute('''
          local recipe=fishRecipe(7751,{{6291,1},{2678,1}})
          for _,offers in ipairs({{}, {[2678]={{unlimited=false,stock=100,price=1,quantity=1,npcID=7}}}})do
            local r=fishSolve(fishSnapshot({recipe},{[2678]=1},offers),1,4)
            assert(not r.targetReached and #r.steps==0 and #r.mats==0)
          end
        ''')

    def test_client_material_override_to_meat_is_rejected_even_with_price(self):
        self.lua.execute('''
          ns.ProfRecipeRuntime={[7751]={mats={{769,1}},count=1,available=true}}
          local r=fishSolve(actualSnapshot(1),1,35)
          for _,st in ipairs(r.steps)do assert(st[3]~=7751,'static fish recipe ignored actual meat material')end
          assert(#r.mats==0 and r.total==0)
          assertFishingSources(r)
        ''')

    def test_client_quantity_override_controls_fish_requirement(self):
        self.lua.execute('''
          ns.ProfRecipeRuntime={[7751]={mats={{6291,3}},count=2,available=true}}
          local r=fishSolve(actualSnapshot(1),1,4)
          assert(r.targetReached and r.steps[1][4]==3)
          assert(fishCount(r,6291)==9,'static single-fish quantity overrode observed materials')
        ''')

    def test_both_exclusion_modes_prevent_recipe_being_used_for_leveling(self):
        self.lua.execute('''
          for _,mode in ipairs({'ban','level'})do
            local r=fishSolve(actualSnapshot(1),1,35,{exclusions={['cooking:7751']=mode}})
            for _,st in ipairs(r.steps)do assert(st[3]~=7751,'excluded guide recipe used for leveling')end
          end
        ''')

    def test_unknown_quest_only_formula_without_auction_price_blocks_recipe(self):
        self.lua.execute('''
          local recipe=fishRecipe(7751,{{6291,1}})
          recipe.formula=99999;recipe.source={questOnly=true}
          local s=fishSnapshot({recipe});s.known={}
          local r=fishSolve(s,1,4)
          assert(not r.targetReached and #r.steps==0 and #r.mats==0)
          local found=false;for _,d in ipairs(r.diagnostics or {})do
            if d.code=='formulaUnavailable'then found=true end end
          assert(found,'unobtainable formula lost its actionable reason')
        ''')

    def test_formula_purchase_is_once_and_remains_separate_from_fish(self):
        self.lua.execute('''
          local recipe=fishRecipe(7751,{{6291,1}});recipe.formula=99999
          local s=fishSnapshot({recipe},{[99999]=17});s.known={}
          local r=fishSolve(s,1,4)
          assert(r.targetReached and fishCount(r,6291)==3)
          assert(r.total==17 and r.formulasTotal==17 and r.matTotal==0 and r.ahTotal==17)
          assert(#r.formulas==1 and r.formulas[1].id==99999 and r.formulas[1].count==1)
          assert(#r.mats==0 and r.steps[1].cost==17)
        ''')

    def test_self_fished_materials_are_not_a_free_source_for_cheapest_solver(self):
        self.lua.execute('''
          local recipe=fishRecipe(7751,{{6291,1}})
          local r=ns.ProfRouteSolver.Compute('cooking',{
            snapshot=fishSnapshot({recipe}),start=1,target=4})
          assert(not r.targetReached and #r.steps==0 and #r.mats==0)
        ''')

    def test_no_auctionator_or_joint_profession_choice_is_required(self):
        self.lua.execute('''
          Auctionator=nil
          local s=actualSnapshot(1);s.professions.cooking.unlearned=true
          for _,recipe in ipairs(s.recipes)do recipe.formula=nil end
          local r=ns.ProfRouteAuto.Compute('cooking',{scheme='fishing',snapshot=s,
            start=1,target=4,allowSecondaryLeveling=true,learnedOnly=true})
          assert(r.targetReached and r.feasible and r.status~='selection_required')
          assert(fishCount(r,6291)==3 and #r.steps==1)
        ''')

    def live_capture(self):
        self.lua.execute('''
          captures=0
          ns.ProfEconomy.Professions=function()return {cooking={cur=1,max=300},fishing={cur=300,max=300}}end
          ns.ProfFishing.Capture=function()
            captures=captures+1;return actualSnapshot(1)
          end
          ns.ProfEconomy.Capture=function()return actualSnapshot(1)end
        ''')

    def test_cooking_route_setting_selects_fishing_without_changing_other_professions(self):
        self.live_capture()
        self.lua.execute('''
          ns.DB().prof.cookingRoute='fishing';ns.DB().prof.autoScheme='cheapest'
          assert(ns.ProfRouteAuto.OptionsFor('cooking',1).scheme=='fishing')
          assert(ns.ProfRouteAuto.OptionsFor('alchemy',1).scheme=='cheapest')
        ''')

    def test_cached_fishing_route_survives_invalidation_and_module_reload(self):
        self.live_capture()
        self.lua.execute('''
          local ra=ns.ProfRouteAuto
          original=ra.Get('cooking',{scheme='fishing',start=1,target=4})
          assert(original.targetReached and captures==1)
          ra.Invalidate('prices')
          assert(ra.Get('cooking',{scheme='fishing',start=2,target=4})==original)
          assert(original.stale and captures==1,'opening a saved fishing route recalculated it')
        ''')
        self.load(str(ROOT/'Core/ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('cooking',{scheme='fishing',start=2,target=4})
          assert(r.cached and r.scheme=='fishing' and r.targetReached and r.start==1)
          assert(captures==1,'restoring fishing snapshot rescanned recipes')
        ''')

    def test_fishing_and_cheapest_caches_cannot_expose_each_others_material_assumptions(self):
        self.live_capture()
        self.lua.execute('''
          local ra=ns.ProfRouteAuto
          local fishing=ra.Get('cooking',{scheme='fishing',start=1,target=4})
          assert(fishing.targetReached and fishCount(fishing,6291)==3)
          local regular=finish('cooking',{scheme='cheapest',start=1,target=4})
          assert(regular~=fishing and regular.scheme=='cheapest','mode switch exposed free fish as cheapest')
          assert(not regular.targetReached and #regular.steps==0,'unpriced fish became free ordinary materials')
          assert(ra.Get('cooking',{scheme='fishing',start=1,target=4})==fishing)
        ''')


class FishingFollowTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FOLLOW_STUBS)
        loader = self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        loader(str(ROOT / 'Core/AuctionatorBridge.lua'))
        loader(str(ROOT / 'Core/ProfFollow.lua'))

    def test_fishing_plan_only_exports_formula_auction_purchase(self):
        self.lua.execute('''
          settings.cookingRoute='fishing';settings.autoRoute=false
          settings.autoScheme='fishing';followState.slug='cooking'
          currentResult.scheme='fishing';currentResult.feasible=true
          currentResult.steps={{1,4,7751,3,profession='cooking',actionID='fish1'}}
          currentResult.mats={{id=2678,count=5,source='vendor',vendor=true}}
          currentResult.fishMaterials={{id=6291,count=3,source='fishing',areas={{mapID=37}}}}
          currentResult.formulas={{id=6325,count=1,source='ah',cost=20}}
          ns.ProfLeveling.cooking={steps={{1,50,7751,49}}}
          skills.cooking={cur=1,max=75}
          local mode,steps,res=ns.ProfFollow.GetRoute('cooking',1)
          assert(res==currentResult and #steps==1,'cooking fishing mode fell back to fixed guide')
          local p=ns.ProfFollow.GetPurchases(followState)
          assert(#p==3,'HUD omitted fish preparation or formula requirements')
          ns.AuctionBridge.DoImport=function(_,items)exported=items end
          local button=makeFrame();ns.ProfFollow.PaintImportBtn(button,'cooking');button.scripts.OnClick()
          assert(#exported==1 and exported[1].name=='Item6325','HUD exported self-fished fish or vendor spices')
        ''')


if __name__ == '__main__':
    unittest.main()
