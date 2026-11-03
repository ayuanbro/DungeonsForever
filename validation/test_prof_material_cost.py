"""Route costs value all ingredients; only procurement deducts current stock."""
import unittest

import test_prof_solver_fusion as solver
import test_prof_reserve as reserve
from test_prof_native_data import native_runtime, ROOT


class MaterialCostRouteTests(unittest.TestCase):
    setUp = solver.ProfessionSolverFusionTests.setUp

    def test_owned_expensive_material_does_not_win_against_cheaper_recipe(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1}})
          local b=recipe('alchemy',102,20,1,{{12,1}})
          local s=snapshot({a,b},{[11]=100,[12]=7})
          for _,scheme in ipairs({'cheapest','stable'})do
            for _,inventory in ipairs({{}, {[11]=99}, {[12]=99}})do
              local r=solve('alchemy',s,4,{scheme=scheme,executionInventory=inventory})
              assert(r.targetReached and r.total==21,tostring(r.total))
              assert(countCrafts(r,101)==0 and countCrafts(r,102)==3)
              assert(bought(r,12)==3 and next(r.seedInventory)==nil)
              for _,a in ipairs(r.actions)do assert(a.type~='seed')end
            end
          end
        ''')

    def test_learning_and_material_prices_are_compared_together(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1}})
          local b=recipe('alchemy',102,20,1,{{12,1}})
          a.formula=501;b.formula=502
          local s=snapshot({a,b},{[11]=100,[12]=2})
          s.known={};s.formulaOffers={
            [501]={{npcID=1,price=1,quantity=1,unlimited=true,verified=true}},
            [502]={{npcID=2,price=10,quantity=1,unlimited=true,verified=true}}}
          local r=solve('alchemy',s,4,{executionInventory={[11]=99,[12]=99}})
          assert(r.targetReached and r.total==16,tostring(r.total))
          assert(r.formulasTotal==10 and r.matTotal==6 and #r.formulas==1)
          assert(countCrafts(r,101)==0 and countCrafts(r,102)==3)
        ''')

    def test_nested_inputs_are_priced_once_without_free_seed_inputs(self):
        self.lua.execute('''
          local make=recipe('mining',201,20,2,{{11,1}},1,1)
          local level=recipe('alchemy',101,10,1,{{20,1}})
          local s=snapshot({make,level},{[11]=6,[20]=100})
          local a=solve('alchemy',s,3)
          local b=solve('alchemy',s,3,{executionInventory={[11]=99,[20]=99}})
          assert(a.targetReached and b.targetReached and a.total==6 and b.total==6)
          assert(countCrafts(a,201)==1 and countCrafts(b,201)==1)
          assert(countCrafts(b,101)==2 and bought(b,11)==1 and bought(b,20)==0)
        ''')

    def test_existing_stock_cannot_hide_missing_material_prices(self):
        self.lua.execute('''
          local s=snapshot({recipe('alchemy',101,10,1,{{11,1}})},{})
          local r=solve('alchemy',s,2,{executionInventory={[11]=999}})
          assert(not r.targetReached and not r.feasible)
          local missing=false
          for _,d in ipairs(r.diagnostics)do if d.item==11 then missing=true end end
          assert(missing,'owned ingredients hid a missing cost input')
        ''')

    def test_procurement_still_deducts_stock_and_does_not_rebuy_it(self):
        self.lua.execute('''
          local s=snapshot({},{[11]=7})
          local r,j=ns.ProfRouteSolver.Procure(s,11,3,{executionInventory={[11]=2}})
          assert(not j.error and r.feasible and r.total==7 and bought(r,11)==1)
          assert(r.seedInventory[11]==2 and #r.seedAllocations==1)
        ''')


class MaterialCostShoppingTests(unittest.TestCase):
    setUp = reserve.ReserveShoppingTests.setUp

    def test_backpack_only_changes_pending_purchases_and_keeps_plan_cost(self):
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=fixture(),start=1,target=4,
            executionInventory={[11]=99},reserveMode='off'})
          assert(r.targetReached and r.total==21 and r.matTotal==21)
          assert(r.mats[1].count==3 and next(r.seedInventory)==nil)
          for have=0,4 do
            bag[11]=have
            local rows=ns.ProfFollow.ShoppingForPlan('alchemy',r)
            assert(#rows==1 and rows[1].need==3)
            assert(rows[1].purchaseCount==math.max(0,3-have))
            assert(rows[1].purchaseCost==7*math.max(0,3-have))
            assert(r.total==21 and r.mats[1].count==3)
          end
        ''')

    def test_reserve_and_base_shopping_deduct_backpack_once(self):
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=reserveFixture(),start=1,target=3,
            executionInventory={[11]=7},reserveMode='ample'})
          assert(r.total==35 and r.reserve.total==21)
          assert(r.reserve.materials[1].count==3 and r.reserve.materials[1].spare==0)
          bag[11]=7
          local rows=ns.ProfFollow.ShoppingForPlan('alchemy',r)
          assert(#rows==1 and rows[1].baseNeed==5 and rows[1].reserveNeed==3)
          assert(rows[1].purchaseCount==1 and rows[1].purchaseCost==7)
        ''')

    def test_shopping_page_without_reserve_displays_only_missing_purchases(self):
        for locale in ('zhCN','zhTW','enUS'):
            reserve.ReserveShoppingTests.prepare(self,locale)
            self.lua.execute('''
              local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=fixture(),start=1,target=4,
                executionInventory={[11]=99},reserveMode='off'})
              bag[11]=2
              for _,grouped in ipairs({false,true})do
                PD.shopGroup=grouped
                local rows={};PD.RowsAutoShop(rows,r)
                local purchase,heading=false,false
                for _,row in ipairs(rows)do
                  if row.purchaseSource then
                    assert(row.purchaseCount==1 and row.purchaseCost==7)
                    purchase=true
                  end
                  if row.text==ns.L['当前采购（已扣背包）']then heading=true end
                end
                assert(purchase and heading,'shopping page displayed the full route budget as quantity to buy')
                assert(r.total==21 and r.mats[1].count==3)
              end
            ''')

    def test_owned_intermediate_offsets_raw_shopping_before_execution(self):
        self.lua.execute('''
          local s=fixture();s.considerAuctionSupply=false
          s.recipes[1].mats={{20,1}};s.prices={[20]=100,[12]=2}
          s.recipes[2]={profession='alchemy',spell=102,item=20,count=1,mats={{12,2}},
            learn=1,yellow=1,green=1,grey=1,cooldown=false}
          s.known['alchemy:102']=true
          local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=3,reserveMode='off'})
          assert(r.targetReached and r.total==8 and not ns.ProfExecution.GetRun('alchemy'))
          local steps=ns.ProfEconomy.Copy(r.executionSteps)
          for have=0,2 do
            bag[20]=have
            local rows=ns.ProfFollow.ShoppingForPlan('alchemy',r)
            if have==2 then assert(#rows==0)
            else assert(#rows==1 and rows[1].id==12 and rows[1].purchaseCount==(2-have)*2)end
            assert(r.total==8 and not ns.ProfExecution.GetRun('alchemy'))
            for i,step in ipairs(r.executionSteps)do
              for k=1,4 do assert(step[k]==steps[i][k])end
            end
          end
        ''')

    def test_owned_intermediate_preserves_reserve_and_batch_rounding(self):
        self.lua.execute('''
          local s=reserveFixture(true)
          local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=3,reserveMode='ample'})
          assert(r.targetReached and r.total==21)
          bag[11]=5
          local rows=ns.ProfFollow.ShoppingForPlan('alchemy',r)
          assert(#rows==1 and rows[1].id==12 and rows[1].purchaseCount==2,
            'skipping intermediate batches lost the surplus needed for reserve')
          bag[11]=8
          rows=ns.ProfFollow.ShoppingForPlan('alchemy',r)
          assert(#rows==0,'fully prepared intermediates still requested raw materials')
          assert(r.total==21 and not ns.ProfExecution.GetRun('alchemy'))
        ''')


class NativeEngineeringCostTests(unittest.TestCase):
    def test_real_tool_recipe_and_route_do_not_change_with_copper_inventory(self):
        lua=native_runtime()
        lua.execute('ns.IsForever=true')
        lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
            (ROOT/'Core/Data/Data_ProfLearningSources.lua').read_text(encoding='utf-8-sig'))
        lua.execute('''
          selected='engineering'
          ns.ProfModule.ProfLearned=function()return {engineering={cur=50,max=75}}end
          ns.ProfRouteAuto.AHPriceOf=function(id)return id==2840 and 100 or 1000 end
          function compare(enabled)
            local previous
            for _,inventory in ipairs({{}, {[2840]=61,[4357]=30,[2589]=92}, {[2840]=999}})do
              local r,j=ns.ProfRouteSolver.Compute('engineering',{start=50,target=70,
                autoCraftTools=enabled,executionInventory=inventory,maxNodes=1,cpuLimitMs=4000})
              assert(not j.error and r.targetReached,tostring(j.error))
              if previous then
                assert(r.total==previous.total and #r.executionSteps==#previous.executionSteps)
                for i,step in ipairs(r.executionSteps)do
                  for k=1,4 do assert(step[k]==previous.executionSteps[i][k])end
                end
              end
              previous=r
            end
          end
          compare(false);compare(true)
        ''')


if __name__ == '__main__':
    unittest.main()
