"""Real route ledgers keep finite AH top-ups and NPC receipts in agreement."""
import unittest

import test_prof_route_plans as routes


class MixedStockLedgerTests(unittest.TestCase):
    def setUp(self):
        routes.NativeRoutePlansTests.setUp(self)
        self.lua.execute('''
          function checkPurchaseLedger(r,stock)
            local cash,vendor,auction=0,0,0
            local used,inventory,receipts={}, {}, {}
            local function key(id,source,npc,size)
              return id..':'..source..':'..tostring(npc or 0)..':'..tostring(size or 1)
            end
            for _,a in ipairs(r.actions)do
              if a.type=='buy' or a.type=='formula' then
                cash=cash+a.cost
                if a.source=='vendor' then vendor=vendor+a.cost else auction=auction+a.cost end
                if a.source=='ah' then used[a.item]=(used[a.item] or 0)+a.count end
              end
              if a.type=='buy' then
                local k=key(a.item,a.source,a.npcID,a.bundleSize)
                receipts[k]=receipts[k] or {count=0,cost=0}
                receipts[k].count=receipts[k].count+a.count;receipts[k].cost=receipts[k].cost+a.cost
                inventory[a.item]=(inventory[a.item] or 0)+a.count
                if a.source=='vendor' then assert(a.count%(a.bundleSize or 1)==0)end
              elseif a.type=='craft' then
                for _,m in ipairs(a.inputs or {})do
                  inventory[m[1]]=(inventory[m[1]] or 0)-m[2]
                  assert(inventory[m[1]]>=0,'a route consumed a material before acquiring it')
                end
                for _,p in ipairs(a.outputs or {})do inventory[p[1]]=(inventory[p[1]] or 0)+p[2]end
              end
            end
            assert(r.total==cash and r.vendorTotal==vendor and r.ahTotal==auction)
            assert(r.total==r.vendorTotal+r.ahTotal)
            local shop=0
            for _,m in ipairs(r.mats)do
              local k=key(m.id,m.source,m.npcID,m.bundleSize)
              local a=receipts[k];assert(a and a.count==m.count and a.cost==m.cost)
              assert(m[1]==m.id and m[2]==m.count and m.vendor==(m.source=='vendor'))
              shop=shop+m.cost;receipts[k]=nil
            end
            assert(next(receipts)==nil,'an acquisition disappeared from the shopping list')
            for _,f in ipairs(r.formulas)do shop=shop+f.cost end
            assert(shop==r.total)
            for id,quantity in pairs(stock or {})do assert((used[id] or 0)<=quantity)end
            local route=0
            for _,step in ipairs(r.steps)do route=route+(step.cost or 0)end
            assert(math.abs(route-r.total)<1e-7,'route rows disagree with purchase receipts')
            return used
          end
        ''')

    def test_every_strategy_matches_independent_pack_enumeration_and_receipts(self):
        self.lua.execute('''
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim'})do
            for _,need in ipairs({3,4,5,7})do
              local expected=math.huge
              for ah=0,2 do for three=0,4 do for four=0,4 do
                if ah+three*3+four*4>=need then expected=math.min(expected,ah+three*7+four*9)end
              end end end
              local s=fixture();s.prices[11]=1
              s.auctionSupply={[11]={quantity=2}}
              s.offers={[11]={
                {npcID=7,price=7,quantity=3,unlimited=true},
                {npcID=8,price=9,quantity=4,unlimited=true}}}
              local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=need+1,
                scheme=scheme,autoCraftTools=false,recoveryEnabled=false})
              assert(r.targetReached and r.total==expected and r.purchaseVerified,scheme..':'..need)
              local used=checkPurchaseLedger(r,{[11]=2})
              if need==3 then assert((used[11] or 0)==0,'using cheap AH must not force a more expensive whole pack')end
              if need==4 or need==5 or need==7 then
                assert(r.ahTotal>0 and r.vendorTotal>0 and #r.mats==2,'mixed sources were not split into receipts')
              end
            end
          end
        ''')

    def test_unknown_or_invalid_stock_stays_unknown_instead_of_becoming_zero(self):
        self.lua.execute('''
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim'})do
            for _,supply in ipairs({{}, {[11]={quantity=0,complete=false}},
              {[11]={quantity=0,source='auctionator-history'}},
              {[11]={quantity=0,source='client-auction-results',complete=true,ownerExcluded=true,
                observedAt=1,expiresAt=2}}})do
              local s=fixture();s.stamp=1000;s.prices[11]=1;s.auctionSupply=supply
              s.auctionSupplyStatus={[11]='expired'}
              s.offers={[11]={{npcID=7,price=7,quantity=1,unlimited=true}}}
              local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=5,
                scheme=scheme,autoCraftTools=false,recoveryEnabled=false})
              assert(r.targetReached and r.ahTotal==4 and r.vendorTotal==0)
              assert(r.auctionSupplyUnknown==1 and not r.supplyComplete and not r.purchaseVerified)
              assert(not r.inputModelOptimal and not r.optimal and #r.auctionSupplyShortages==0)
              assert(r.mats[1].source=='ah' and r.mats[1].availableCount==nil
                and not r.mats[1].supplyObserved and r.mats[1].supplyStatus=='expired')
              checkPurchaseLedger(r)
            end
          end
        ''')

    def test_unpurchasable_npc_cannot_hide_a_known_auction_shortage(self):
        self.lua.execute('''
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim'})do
            for _,offer in ipairs({
              {npcID=7,price=7,quantity=1,unlimited=true,purchasable=false},
              {npcID=7,price=7,quantity=1,unlimited=true,available=false},
              {npcID=7,price=7,quantity=1,unlimited=true,faction='H'},
              {npcID=7,price=7,quantity=1,unlimited=true,hasExtendedCost=true},
              {npcID=7,quantity=1,unlimited=true}
            })do
              local s=fixture();s.faction='A';s.prices[11]=1;s.auctionSupply={[11]={quantity=2}}
              s.offers={[11]={offer}}
              local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=5,
                scheme=scheme,autoCraftTools=false,recoveryEnabled=false})
              assert(not r.targetReached and not r.supplyComplete and not r.purchaseVerified)
              assert(r.auctionSupplyUnknown==0 and #r.auctionSupplyShortages==1)
              local d=r.auctionSupplyShortages[1]
              assert(d.item==11 and d.required>0 and d.available==0)
              assert(r.vendorTotal==0 and r.ahTotal<=2)
              checkPurchaseLedger(r,{[11]=2})
            end
          end
        ''')

    def test_formula_and_material_share_stock_with_best_global_source_choice(self):
        self.lua.execute('''
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim'})do
            for _,formulaVendor in ipairs({true,false})do
              local s=fixture();s.known={};s.recipes[1].formula=11;s.prices[11]=1
              s.stamp=1000;s.auctionSupply={[11]={quantity=2,observedAt=900,complete=true,
                ownerExcluded=true,source='client-auction-results'}}
              s.offers={[11]={{npcID=7,price=7,quantity=1,unlimited=true}}}
              s.formulaOffers={[11]=formulaVendor and {{npcID=8,price=2,quantity=1,unlimited=true}} or {}}
              local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4,
                noFormula=false,scheme=scheme,autoCraftTools=false,recoveryEnabled=false})
              assert(r.targetReached and r.purchaseVerified and #r.formulas==1)
              local f=r.formulas[1]
              if formulaVendor then
                assert(f.source=='vendor' and f.cost==2 and r.total==11,
                  'a cheap auction pattern must not waste the cheaper material stock')
              else
                assert(f.source=='ah' and f.cost==1 and r.total==16)
                assert(f.supplyRequired==2 and f.availableCount==2)
              end
              local used=checkPurchaseLedger(r,{[11]=2})
              assert(used[11]==2,'pattern and materials did not share the finite stock')
            end
          end
        ''')


if __name__ == '__main__':
    unittest.main()
