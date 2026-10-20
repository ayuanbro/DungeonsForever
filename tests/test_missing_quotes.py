"""Missing auction quotes require priced material production by the target profession."""
import unittest

from test_prof_solver import FIXTURES, LuaRuntime, ROOT


class MissingQuoteTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURES)
        load = self.lua.eval("function(path) assert(loadfile(path))('DungeonsForever',ns) end")
        load(str(ROOT / "Core" / "ProfEconomy.lua"))
        load(str(ROOT / "Core" / "ProfRouteSolver.lua"))
        self.lua.execute(r'''
          function noUnknownPurchases(r)
            assert(r.costComplete and r.completeCost and not r.pricePending)
            for _,a in ipairs(r.actions) do
              if a.type=='buy' then assert(not a.unpriced,'unquoted purchase entered route') end
            end
          end
          function flatRecipe(prof,spell,item,mats,learn,grey,count)
            local r=recipe(prof,spell,item,count or 1,mats,learn or 1,grey or 10)
            r.yellow=r.grey; r.green=r.grey
            return r
          end
        ''')

    def test_first_seed_completes_multilayer_own_profession_with_one_search_node(self):
        self.lua.execute(r'''
          local raw=flatRecipe('alchemy',101,10,{{11,3}},1,1,2)
          local middle=flatRecipe('alchemy',102,12,{{10,2},{13,1}},1,1)
          local root=flatRecipe('alchemy',103,20,{{12,1}},1,4)
          local s=snapshot({raw,middle,root},{[11]=7,[13]=5})
          local r,j=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=s,start=1,target=4,maxNodes=1,referenceFallback=true})
          assert(not j.error and r.feasible and r.targetReached)
          noUnknownPurchases(r)
          assert(r.total==78 and r.ahTotal==78 and r.vendorTotal==0,tostring(r.total))
          assert(r.initialTotal==78,'priced material recursion was deferred until frontier search')
          assert(countCrafts(r,101)==3 and countCrafts(r,102)==3 and countCrafts(r,103)==3)
          local bought={}; for _,m in ipairs(r.mats) do bought[m.id]=m.count end
          assert(bought[11]==9 and bought[13]==3 and not bought[10] and not bought[12])
        ''')

    def test_unpriced_leaf_abandons_recipe_and_selects_priced_alternative(self):
        self.lua.execute(r'''
          local blocked=flatRecipe('alchemy',101,20,{{99,1}},1,4)
          local usable=flatRecipe('alchemy',102,21,{{11,1}},1,4)
          local r=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=snapshot({blocked,usable},{[11]=9}),start=1,target=4,maxNodes=1})
          assert(r.feasible and r.targetReached and r.total==27)
          noUnknownPurchases(r)
          assert(countCrafts(r,101)==0 and countCrafts(r,102)==3)
        ''')

    def test_unpriced_unmakeable_material_gives_no_executable_route(self):
        self.lua.execute(r'''
          local root=flatRecipe('alchemy',101,20,{{99,1}},1,3)
          local r,j=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=snapshot({root},{}),start=1,target=3,referenceFallback=true})
          assert(not j.error and not r.feasible and not r.targetReached)
          assert(#r.steps==0 and #r.mats==0)
        ''')

    def test_secondary_profession_does_not_replace_missing_auction_quote(self):
        self.lua.execute(r'''
          local producer=flatRecipe('mining',101,10,{{11,1}},1,1)
          local blocked=flatRecipe('alchemy',201,20,{{10,1}},1,4)
          local usable=flatRecipe('alchemy',202,21,{{12,1}},1,4)
          for _,joint in ipairs({false,true}) do
            local s=snapshot({producer,blocked,usable},{[11]=3,[12]=7})
            local r=ns.ProfRouteSolver.Compute('alchemy',{
              snapshot=s,start=1,target=4,allowSecondaryLeveling=joint,maxNodes=1})
            assert(r.feasible and r.targetReached and r.total==21)
            noUnknownPurchases(r)
            assert(countCrafts(r,101)==0 and countCrafts(r,201)==0 and countCrafts(r,202)==3)
          end
        ''')

    def test_priced_material_can_still_use_cheaper_current_secondary_profession(self):
        self.lua.execute(r'''
          local producer=flatRecipe('mining',101,10,{{11,1}},1,1)
          local root=flatRecipe('alchemy',201,20,{{10,1}},1,4)
          local s=snapshot({producer,root},{[10]=30,[11]=3})
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4})
          assert(r.feasible and r.targetReached and r.total==9)
          noUnknownPurchases(r)
          assert(countCrafts(r,101)==3 and countCrafts(r,201)==3)
        ''')

    def test_vendor_quoted_material_can_still_use_cheaper_secondary_production(self):
        self.lua.execute(r'''
          local producer=flatRecipe('mining',101,10,{{11,1}},1,1)
          local root=flatRecipe('alchemy',201,20,{{10,1}},1,4)
          local s=snapshot({producer,root},{[11]=3})
          s.vendorItems={[10]=true}
          s.offers={[10]={{unlimited=true,price=20,quantity=1,npcID=1313,reference=true}}}
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4})
          assert(r.feasible and r.targetReached and r.total==9)
          noUnknownPurchases(r)
          assert(countCrafts(r,101)==3 and countCrafts(r,201)==3)
          assert(r.vendorTotal==0 and r.ahTotal==9)
        ''')

    def test_invalid_vendor_quote_does_not_unlock_secondary_production_or_byproducts(self):
        self.lua.execute(r'''
          for _,invalid in ipairs({'available','faction','currency','extended','limited','purchasable','negative'}) do
            local a=flatRecipe('mining',101,10,{{11,1}},1,2)
            local b=flatRecipe('mining',102,12,{{13,1}},2,2)
            local blocked=flatRecipe('alchemy',201,20,{{12,1},{10,1}},1,2)
            local usable=flatRecipe('alchemy',202,21,{{14,1}},1,2)
            local s=snapshot({a,b,blocked,usable},{[11]=3,[12]=100,[13]=1,[14]=7})
            s.professions.mining={cur=1,max=300}; s.faction='A'
            s.vendorItems={[10]=true}
            local o={unlimited=true,price=1,quantity=1,npcID=1313}
            if invalid=='available' then o.available=false
            elseif invalid=='faction' then o.faction='H'
            elseif invalid=='currency' then o.currencyID=99
            elseif invalid=='extended' then o.hasExtendedCost=true
            elseif invalid=='limited' then o.unlimited=false
            elseif invalid=='purchasable' then o.purchasable=false
            elseif invalid=='negative' then o.price=-1 end
            s.offers={[10]={o}}
            local r=ns.ProfRouteSolver.Compute('alchemy',{
              snapshot=s,start=1,target=2,allowSecondaryLeveling=true})
            assert(r.feasible and r.targetReached and r.total==7,invalid)
            noUnknownPurchases(r)
            assert(countCrafts(r,201)==0 and countCrafts(r,202)==1,invalid)
          end
        ''')

    def test_missing_quote_material_can_mix_two_own_integer_production_methods(self):
        self.lua.execute(r'''
          local two=flatRecipe('alchemy',101,10,{{11,1}},1,1,2)
          local three=flatRecipe('alchemy',102,10,{{12,1}},1,1,3)
          local root=flatRecipe('alchemy',201,20,{{10,5}},1,2)
          local r=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=snapshot({two,three,root},{[11]=7,[12]=9}),start=1,target=2})
          assert(r.feasible and r.targetReached and r.total==16,tostring(r.total))
          noUnknownPurchases(r)
          assert(countCrafts(r,101)==1 and countCrafts(r,102)==1 and countCrafts(r,201)==1)
          for _,m in ipairs(r.mats) do assert(m.id~=10) end
        ''')

    def test_joint_secondary_leveling_byproduct_cannot_supply_unquoted_main_material(self):
        self.lua.execute(r'''
          for _,alternative in ipairs({false,true}) do
            local a=flatRecipe('mining',101,10,{{11,1}},1,2)
            local b=flatRecipe('mining',102,12,{{13,1}},2,2)
            local root=flatRecipe('alchemy',201,20,{{12,1},{10,1}},1,2)
            local rs={a,b,root}
            if alternative then rs[#rs+1]=flatRecipe('alchemy',202,21,{{14,1}},1,2) end
            local s=snapshot(rs,{[11]=3,[12]=100,[13]=1,[14]=7})
            s.professions.mining={cur=1,max=300}
            local r,j=ns.ProfRouteSolver.Compute('alchemy',{
              snapshot=s,start=1,target=2,allowSecondaryLeveling=true})
            assert(not j.error)
            if alternative then
              assert(r.feasible and r.targetReached and r.total==7)
              noUnknownPurchases(r)
              assert(countCrafts(r,201)==0 and countCrafts(r,202)==1)
            else
              assert(not r.feasible and not r.targetReached and #r.steps==0)
            end
          end
        ''')

    def test_higher_skill_own_recipe_does_not_qualify_secondary_byproduct_inventory(self):
        self.lua.execute(r'''
          local a=flatRecipe('mining',101,10,{{11,1}},1,2)
          local b=flatRecipe('mining',102,12,{{13,1}},2,2)
          local own=flatRecipe('alchemy',103,10,{{15,1}},100,100)
          local blocked=flatRecipe('alchemy',201,20,{{12,1},{10,1}},1,2)
          local usable=flatRecipe('alchemy',202,21,{{14,1}},1,2)
          local s=snapshot({a,b,own,blocked,usable},{[11]=3,[12]=100,[13]=1,[14]=7,[15]=6})
          s.professions.mining={cur=1,max=300}
          local r=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=s,start=1,target=2,allowSecondaryLeveling=true})
          assert(r.feasible and r.targetReached and r.total==7)
          noUnknownPurchases(r)
          assert(countCrafts(r,103)==0 and countCrafts(r,201)==0 and countCrafts(r,202)==1)
        ''')

    def test_unquoted_secondary_byproduct_is_preserved_but_own_material_is_consumed(self):
        self.lua.execute(r'''
          local a=flatRecipe('mining',101,10,{{11,1}},1,2)
          local b=flatRecipe('mining',102,12,{{13,1}},2,2)
          local own=flatRecipe('alchemy',103,10,{{15,1}},1,1)
          local root=flatRecipe('alchemy',201,20,{{12,1},{10,1}},1,2)
          local s=snapshot({a,b,own,root},{[11]=3,[12]=100,[13]=1,[15]=6})
          s.professions.mining={cur=1,max=300}
          local r=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=s,start=1,target=2,allowSecondaryLeveling=true})
          assert(r.feasible and r.targetReached and r.total==10,tostring(r.total))
          noUnknownPurchases(r)
          assert(countCrafts(r,101)==1 and countCrafts(r,102)==1 and countCrafts(r,103)==1)
          assert(countCrafts(r,201)==1 and r.inventory[10]==1)
          local foreign,ownID,rootAction
          for _,a in ipairs(r.actions) do
            if a.type=='craft' and a.spell==101 then foreign=a.id end
            if a.type=='craft' and a.spell==103 then ownID=a.id end
            if a.type=='craft' and a.spell==201 then rootAction=a end
          end
          assert(foreign and ownID and rootAction)
          local usesOwn=false
          for _,id in ipairs(rootAction.dependencies) do
            assert(id~=foreign,'unusable byproduct entered the dependency graph')
            usesOwn=usesOwn or id==ownID
          end
          assert(usesOwn,'missing-quote material was not linked to its real own-profession producer')
          for _,step in ipairs(r.steps) do
            if step[3]==101 then assert(step.role=='level') end
            if step[3]==103 then assert(step.role=='material') end
          end
        ''')

    def test_missing_quote_material_producer_respects_ban_and_cooldown(self):
        self.lua.execute(r'''
          for _,restriction in ipairs({'ban','cooldown','cooldownUnknown','clientUnavailable'}) do
            local producer=flatRecipe('alchemy',101,10,{{11,1}},1,1)
            local blocked=flatRecipe('alchemy',201,20,{{10,1}},1,4)
            local usable=flatRecipe('alchemy',202,21,{{12,1}},1,4)
            local opts={start=1,target=4,maxNodes=1}
            if restriction=='ban' then opts.exclusions={['alchemy:101']='ban'}
            else producer[restriction]=true end
            opts.snapshot=snapshot({producer,blocked,usable},{[11]=3,[12]=7})
            local r=ns.ProfRouteSolver.Compute('alchemy',opts)
            assert(r.feasible and r.targetReached and r.total==21,restriction)
            noUnknownPurchases(r)
            assert(countCrafts(r,101)==0 and countCrafts(r,201)==0 and countCrafts(r,202)==3)
          end
        ''')

    def test_level_only_exclusion_allows_necessary_missing_quote_material_batches(self):
        self.lua.execute(r'''
          local producer=flatRecipe('alchemy',101,10,{{11,1}},1,1,2)
          local root=flatRecipe('alchemy',201,20,{{10,1}},1,4)
          local r=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=snapshot({producer,root},{[11]=3}),start=1,target=4,maxNodes=1,
            exclusions={['alchemy:101']='level'}})
          assert(r.feasible and r.targetReached and r.total==6)
          noUnknownPurchases(r)
          assert(countCrafts(r,101)==2 and countCrafts(r,201)==3)
        ''')

    def test_colored_material_crafting_gains_follow_dependency_order(self):
        self.lua.execute(r'''
          local producer=flatRecipe('alchemy',101,10,{{11,1}},1,5)
          local root=flatRecipe('alchemy',201,20,{{10,1},{12,1}},1,5)
          local r=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=snapshot({producer,root},{[11]=3,[12]=7}),start=1,target=5,maxNodes=1,
            exclusions={['alchemy:101']='level'}})
          assert(r.feasible and r.targetReached and r.total==20)
          noUnknownPurchases(r)
          assert(countCrafts(r,101)==2 and countCrafts(r,201)==2 and r.finalSkills.alchemy==5)
          assert(#r.steps==2 and #r.executionSteps==4)
          assert(r.steps[1][3]==101 and r.steps[1].role=='both')
          local order={101,201,101,201}
          for i,step in ipairs(r.executionSteps) do
            assert(step[3]==order[i] and step[1]==i and step[2]==i+1)
          end
          assert(#r.steps[1].segments==2 and #r.steps[2].segments==2)
        ''')

    def test_not_yet_learnable_material_recipe_cannot_supply_missing_quote(self):
        self.lua.execute(r'''
          local producer=flatRecipe('alchemy',101,10,{{11,1}},10,10)
          local blocked=flatRecipe('alchemy',201,20,{{10,1}},1,4)
          local usable=flatRecipe('alchemy',202,21,{{12,1}},1,4)
          local r=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=snapshot({producer,blocked,usable},{[11]=3,[12]=7}),start=1,target=4,maxNodes=1})
          assert(r.feasible and r.targetReached and r.total==21)
          noUnknownPurchases(r)
          assert(countCrafts(r,101)==0 and countCrafts(r,201)==0 and countCrafts(r,202)==3)
        ''')

    def test_unpriced_cycle_cannot_justify_route(self):
        self.lua.execute(r'''
          local a=flatRecipe('alchemy',101,10,{{12,1}},1,1)
          local b=flatRecipe('alchemy',102,12,{{10,1}},1,1)
          local blocked=flatRecipe('alchemy',201,20,{{10,1}},1,4)
          local usable=flatRecipe('alchemy',202,21,{{11,1}},1,4)
          local r,j=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=snapshot({a,b,blocked,usable},{[11]=7}),start=1,target=4,maxNodes=1})
          assert(not j.error and r.feasible and r.targetReached and r.total==21)
          noUnknownPurchases(r)
          assert(countCrafts(r,101)==0 and countCrafts(r,102)==0 and countCrafts(r,201)==0)
        ''')

    def test_verified_vendor_reference_is_usable_without_any_auction_quote(self):
        self.lua.execute(r'''
          local root=flatRecipe('alchemy',101,20,{{11,1}},1,4)
          local s=snapshot({root},{})
          s.vendorItems={[11]=true}; s.vendorSuppliers={[11]={{npcID=1313}}}
          s.offers={[11]={{unlimited=true,price=20,quantity=5,npcID=1313,
            reference=true,estimated=true,source='wowhead-forever',priceBasis='wowhead-reference'}}}
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4,maxNodes=1})
          assert(r.feasible and r.targetReached and r.total==20 and r.vendorTotal==20 and r.ahTotal==0)
          noUnknownPurchases(r)
          assert(#r.mats==1 and r.mats[1].vendor and r.mats[1].source=='vendor' and r.mats[1].count==5)
        ''')

    def test_unknown_vendor_price_is_not_free_and_does_not_fall_back_to_auction(self):
        self.lua.execute(r'''
          local blocked=flatRecipe('alchemy',101,20,{{10,1}},1,4)
          local usable=flatRecipe('alchemy',102,21,{{11,1}},1,4)
          local s=snapshot({blocked,usable},{[10]=1,[11]=7})
          s.vendorItems={[10]=true}; s.vendorSuppliers={[10]={{npcID=1313}}}
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4,maxNodes=1})
          assert(r.feasible and r.targetReached and r.total==21)
          noUnknownPurchases(r)
          assert(countCrafts(r,101)==0 and countCrafts(r,102)==3)
          for _,m in ipairs(r.mats) do assert(m.id~=10) end
        ''')

    def test_unknown_vendor_price_can_use_fully_priced_own_material_recipe(self):
        self.lua.execute(r'''
          local producer=flatRecipe('alchemy',101,10,{{11,2}},1,1)
          local root=flatRecipe('alchemy',201,20,{{10,1}},1,4)
          local s=snapshot({producer,root},{[10]=1,[11]=7})
          s.vendorItems={[10]=true}; s.vendorSuppliers={[10]={{npcID=1313}}}
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4,maxNodes=1})
          assert(r.feasible and r.targetReached and r.total==42)
          noUnknownPurchases(r)
          assert(countCrafts(r,101)==3 and countCrafts(r,201)==3)
          assert(#r.mats==1 and r.mats[1].id==11)
        ''')

    def test_no_auction_quote_can_use_known_zero_gold_vendor_price(self):
        self.lua.execute(r'''
          local root=flatRecipe('alchemy',101,20,{{11,1}},1,4)
          local s=snapshot({root},{})
          s.vendorItems={[11]=true}; s.offers={[11]={{unlimited=true,price=0,quantity=5,npcID=1313}}}
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4,maxNodes=1})
          assert(r.feasible and r.targetReached and r.total==0)
          noUnknownPurchases(r)
          assert(#r.mats==1 and r.mats[1].source=='vendor' and r.mats[1].count==5)
        ''')

    def test_every_published_prefix_has_only_priced_purchases(self):
        self.lua.execute(r'''
          local producer=flatRecipe('alchemy',101,10,{{11,2}},1,1)
          local blocked=flatRecipe('alchemy',201,20,{{99,1}},1,5)
          local usable=flatRecipe('alchemy',202,21,{{10,1}},1,5)
          local j=ns.ProfRouteSolver.NewJob('alchemy',{
            snapshot=snapshot({producer,blocked,usable},{[11]=7}),start=1,target=5,maxNodes=1})
          local published=0
          for _=1,10000 do
            local done=ns.ProfRouteSolver.Run(j,1000)
            if j.result and #j.result.steps>0 then
              published=published+1; noUnknownPurchases(j.result)
              assert(countCrafts(j.result,201)==0)
            end
            if done then break end
          end
          assert(not j.error and published>0 and j.result.targetReached and j.result.total==56)
        ''')

    def test_initial_missing_quote_chain_avoids_exponential_seed_comparisons(self):
        # A deterministic CPU counter makes this a bounded search regression,
        # independent of machine speed. Equivalent producer alternatives should
        # not consume the entire budget before the first feasible route appears.
        self.lua.execute(r'''
          local clock=0
          debugprofilestop=function() clock=clock+0.1; return clock end
          local rs={}
          for i=1,14 do for choice=1,2 do
            rs[#rs+1]=flatRecipe('alchemy',100+i*2+choice,10+i,{{9+i,1}},1,1)
          end end
          rs[#rs+1]=flatRecipe('alchemy',999,999,{{24,1}},1,3)
          local r,j=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=snapshot(rs,{[10]=1}),start=1,target=2,maxNodes=1})
          assert(not j.error and r.feasible and r.targetReached,
            'seed exhausted budget before publishing a priced material chain')
          noUnknownPurchases(r)
          assert(r.total==1)
        ''')


if __name__ == "__main__":
    unittest.main()
