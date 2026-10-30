"""NPC and Auctionator purchases compete by executable total cost, not LV.sold."""
import unittest

import test_prof_route_plans as routes


class CompetingProcurementTests(unittest.TestCase):
    setUp = routes.NativeRoutePlansTests.setUp

    def test_npc_or_auction_wins_by_actual_total_in_every_route_strategy(self):
        self.lua.execute('''
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim'})do
            for _,auctionPrice in ipairs({1,20})do
              local s=fixture();s.vendorOnlyItems={[11]=true}
              s.prices[11]=auctionPrice
              s.offers={[11]={{npcID=7,price=15,quantity=5,unlimited=true,
                stock=-1,maxStock=-1,stockStatus='unlimited'}}}
              s.auctionSupply={[11]={quantity=100,complete=true,source='observed'}}
              local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=3,
                scheme=scheme,autoCraftTools=false,recoveryEnabled=false})
              assert(r.targetReached and r.procurementPolicyVersion==ns.ProfRouteSolver.ProcurementPolicyVersion,scheme)
              if auctionPrice==1 then
                assert(r.total==2 and r.ahTotal==2 and r.vendorTotal==0,scheme)
              else
                assert(r.total==15 and r.ahTotal==0 and r.vendorTotal==15,scheme)
                assert(r.mats[1].count==5 and r.mats[1].unlimited and r.mats[1].stock==-1)
              end
            end
          end
        ''')

    def test_missing_or_unpurchasable_vendor_quote_uses_priced_auction(self):
        self.lua.execute('''
          for _,offer in ipairs({
            {npcID=7,quantity=1,unlimited=true},
            {npcID=7,price=1,quantity=1,unlimited=true,purchasable=false},
            {npcID=7,price=1,quantity=1,unlimited=true,available=false},
            {npcID=7,price=1,quantity=1,unlimited=true,faction='H'},
            {npcID=7,price=1,quantity=1,unlimited=true,hasExtendedCost=true}
          })do
            local s=fixture();s.vendorOnlyItems={[11]=true};s.faction='A'
            s.offers={[11]={offer}};s.prices[11]=3
            s.auctionSupply={[11]={quantity=2,complete=true,source='observed'}}
            local r=ns.ProfRouteSolver.Procure(s,11,2,{recoveryEnabled=false})
            assert(r.feasible and r.total==6 and r.ahTotal==6 and r.vendorTotal==0)
          end
        ''')

    def test_npc_pack_price_is_compared_to_the_requested_auction_quantity(self):
        self.lua.execute('''
          local s=fixture();s.prices[11]=2
          s.offers={[11]={{npcID=7,price=5,quantity=5,unlimited=true}}}
          local S=ns.ProfRouteSolver
          local r=S.Procure(s,11,2,{recoveryEnabled=false})
          assert(r.total==4 and r.ahTotal==4 and r.vendorTotal==0)
          r=S.Procure(s,11,3,{recoveryEnabled=false})
          assert(r.total==5 and r.vendorTotal==5 and r.mats[1].count==5)
          r=S.Procure(s,11,6,{recoveryEnabled=false})
          assert(r.total==7 and r.vendorTotal==5 and r.ahTotal==2,
            'one NPC pack plus one auction item should beat either source alone')
        ''')

    def test_auction_stock_is_shared_and_the_remaining_demand_falls_back_to_npc(self):
        self.lua.execute('''
          local s=fixture();s.prices[11]=1
          s.offers={[11]={{npcID=7,price=7,quantity=1,unlimited=true}}}
          s.auctionSupply={[11]={quantity=2,complete=true,source='observed'}}
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4,
            autoCraftTools=false,recoveryEnabled=false})
          assert(r.targetReached and r.ahTotal==2 and r.vendorTotal==7 and r.total==9)
          local purchased=0
          for _,a in ipairs(r.actions)do
            if a.type=='buy' and a.source=='ah' then purchased=purchased+a.count end
          end
          assert(purchased==2,'auction stock was reused for a later craft')
          s.auctionSupply[11].quantity=0
          r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4,
            autoCraftTools=false,recoveryEnabled=false})
          assert(r.targetReached and r.ahTotal==0 and r.vendorTotal==21)
        ''')

    def test_supplier_dominance_keeps_different_packs_and_reliable_quotes(self):
        self.lua.execute('''
          local s=fixture();s.prices[11]=50
          s.offers={[11]={
            {npcID=7,price=100,quantity=1,unlimited=true},
            {npcID=8,price=20,quantity=1,unlimited=true},
            {npcID=9,price=25,quantity=10,unlimited=true}
          }}
          local S=ns.ProfRouteSolver
          local r=S.Procure(s,11,1,{recoveryEnabled=false})
          assert(r.total==20 and r.vendorTotal==20 and r.mats[1].npcID==8)
          r=S.Procure(s,11,2,{recoveryEnabled=false})
          assert(r.total==25 and r.mats[1].npcID==9 and r.mats[1].count==10)
          assert(#s.offers[11]==3,'search pruning mutated the supplier snapshot')
          s.offers[11]={
            {npcID=7,price=1,quantity=1,unlimited=true,estimated=true},
            {npcID=8,price=20,quantity=1,unlimited=true}
          }
          r=S.Procure(s,11,1,{recoveryEnabled=false})
          assert(r.total==20 and r.costComplete and r.mats[1].npcID==8,
            'an uncertain cheap estimate must not erase a reliable supplier')
        ''')

    def test_partial_auction_stock_does_not_force_an_extra_npc_pack(self):
        self.lua.execute('''
          local s=fixture();s.prices[11]=1
          s.offers={[11]={{npcID=7,price=15,quantity=5,unlimited=true}}}
          s.auctionSupply={[11]={quantity=2,complete=true,source='observed'}}
          local r=ns.ProfRouteSolver.Procure(s,11,7,{recoveryEnabled=false})
          assert(r.feasible and r.total==17 and r.ahTotal==2 and r.vendorTotal==15)
          assert(r.supplyComplete and not r.auctionSupplyShortages[1])
        ''')

    def test_real_nonauctionable_constraint_remains_authoritative(self):
        self.lua.execute('''
          local s=fixture();s.prices[11]=1;s.nonAuctionable={[11]=true}
          s.offers={[11]={{npcID=7,price=15,quantity=5,unlimited=true}}}
          local r=ns.ProfRouteSolver.Procure(s,11,2,{recoveryEnabled=false})
          assert(r.feasible and r.total==15 and r.ahTotal==0)
          s.offers={}
          r=ns.ProfRouteSolver.Procure(s,11,2,{recoveryEnabled=false})
          assert(not r.feasible and r.ahTotal==0)
        ''')

    def test_formula_uses_recent_auction_stock_despite_retired_vendor_only_setting(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local recipe={profession='alchemy',spell=999,key='alchemy:999',formula=1000,
            source={drops={{npc='Reference drop'}}}}
          local s={known={},prices={[1000]=2},vendorOnlyItems={[1000]=true},
            stamp=1000,auctionSupply={[1000]={quantity=2,observedAt=900,complete=true,
              ownerExcluded=true,source='client-auction-results'}},
            formulaOffers={[1000]={{npcID=7,price=30,quantity=1,unlimited=true}}}}
          local f=E.FormulaFor(recipe,s)
          assert(f.usable and f.source=='ah' and f.cost==2)
          s.noFormula=true;f=E.FormulaFor(recipe,s)
          assert(f.usable and f.source=='ah' and f.cost==2)
        ''')


if __name__ == '__main__':
    unittest.main()
