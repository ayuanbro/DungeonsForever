"""Fixed-route cash comparisons must never publish zero-quantity purchases."""
import unittest

import test_prof_item_prices as fixtures


class FixedMaterialPurchase(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.ProfItemPrices()
        fixture.setUp()
        fixture.fixed_routes()
        self.lua = fixture.lua

    def test_equal_cash_prefers_exact_ah_quantity_over_unused_npc_pack(self):
        self.lua.execute('''
          fixedFixture(999100,1)
          material(999100,{price=10,quantity=5})
          local r=ns.ProfRouteAuto.SummarizeSteps({{1,2,101,1}},'alchemy')
          assert(#r.mats==1 and r.mats[1].source=='ah' and r.mats[1].count==1)
          assert(r.total==10 and r.ahTotal==10 and r.vendorTotal==0)
          assert(r.steps[1].cost==r.total)
        ''')

    def test_real_mixed_purchase_retains_both_positive_quantities_and_bundle_cash(self):
        self.lua.execute('''
          fixedFixture(999100,6)
          material(999100,{price=9,quantity=5})
          Auctionator.API.v1.GetAuctionPriceByItemID=function(_,id)return id==999100 and 3 or nil end
          local r=ns.ProfRouteAuto.SummarizeSteps({{1,2,101,1}},'alchemy')
          assert(#r.mats==2 and r.total==12 and r.vendorTotal==9 and r.ahTotal==3)
          for _,m in ipairs(r.mats)do
            assert(m.count>0)
            if m.source=='vendor' then
              assert(m.count==5 and m.bundleSize==5 and m.bundlePrice==9 and m.cost==9)
            else assert(m.source=='ah' and m.count==1 and m.cost==3) end
          end
          assert(r.steps[1].cost==r.total)
        ''')
