"""Fixed quantities choose real procurement costs without changing authored steps."""
import unittest
import test_prof_ui_fusion as ui


class FixedCompetingSourcesTests(unittest.TestCase):
    setUp=ui.ProfessionUIFusionTests.setUp
    boot=ui.ProfessionUIFusionTests.boot

    def test_auction_wins_even_when_npc_unit_price_is_lower_but_pack_total_is_higher(self):
        self.lua.execute('''
          ns.ProfLeveling.alchemy.sold={11}
          ns.ProfRouteAuto.AHPriceOf=function()return 3 end
          ns.VendorPriceDB={GetPrice=function()return 2 end,GetOffers=function()
            return {{npcID=1,price=10,unit=2,quantity=5,unlimited=true}}end}
          local sum=ns.ProfRouteAuto.FixedPlan('alchemy',{target=3,recoveryEnabled=false})
          assert(#sum.mats==1 and sum.mats[1].source=='ah' and not sum.mats[1].vendor)
          assert(sum.mats[1].count==2 and sum.total==6 and sum.ahTotal==6 and sum.vendorTotal==0)
          assert(sum.steps[1].cost==6,'route row did not reflect the selected purchase cost')
          assert(ns.ProfLeveling.alchemy.steps[1][4]==2)
        ''')

    def test_missing_npc_quote_uses_auction_and_cheaper_available_npc_wins(self):
        self.lua.execute('''
          ns.ProfLeveling.alchemy.sold={11}
          ns.ProfRouteAuto.AHPriceOf=function()return 6 end
          ns.VendorPriceDB={GetPrice=function()return nil end,GetOffers=function()return {}end}
          local ra=ns.ProfRouteAuto
          local auction=ra.FixedPlan('alchemy',{target=3,recoveryEnabled=false})
          assert(auction.total==12 and auction.mats[1].source=='ah' and not auction.mats[1].unpriced)
          ns.VendorPriceDB.GetOffers=function()return {{npcID=1,price=10,quantity=5,unlimited=true}}end
          ra.Invalidate()
          local npc=ra.FixedPlan('alchemy',{target=3,recoveryEnabled=false})
          assert(npc.total==10 and npc.vendorTotal==10 and npc.ahTotal==0)
          assert(npc.mats[1].source=='vendor' and npc.mats[1].count==5)
        ''')

    def test_multiple_npc_packs_and_finite_auction_can_be_mixed(self):
        self.lua.execute('''
          local snapshot={prices={[11]=1},offers={[11]={
            {npcID=1,price=4,quantity=2,unlimited=true},
            {npcID=2,price=6,quantity=3,unlimited=true}}},auctionSupply={[11]={quantity=1}}}
          local list,total,complete=ns.ProfRouteAuto.MaterialPurchases(11,6,{snapshot=snapshot})
          local npc,ah=0,0
          for _,e in ipairs(list)do
            if e.source=='ah'then ah=ah+e.count else npc=npc+e.count end
          end
          assert(complete and total==11 and npc==5 and ah==1)
          list,total,complete=ns.ProfRouteAuto.MaterialPurchases(11,6,{snapshot=snapshot,auctionRemaining={[11]=0}})
          for _,e in ipairs(list)do assert(e.source=='vendor')end
          assert(complete and total==12)
        ''')

    def test_known_shortage_never_becomes_a_complete_fixed_budget(self):
        self.lua.execute('''
          ns.ProfLeveling.alchemy.sold={11}
          local snapshot={prices={[11]=1},offers={},auctionSupply={[11]={quantity=1}}}
          local sum=ns.ProfRouteAuto.FixedPlan('alchemy',{target=3,snapshot=snapshot,recoveryEnabled=false})
          assert(sum.feasible==false and sum.costComplete==false)
          assert(sum.mats[1].source=='ah' and sum.mats[1].unavailable and sum.mats[1].availableCount==1)
          local shortage=false
          for _,d in ipairs(sum.diagnostics)do if d.code=='auctionSupplyLimited'then shortage=true;assert(d.required==2 and d.available==1)end end
          assert(shortage)
        ''')

    def test_snapshot_does_not_read_new_live_quotes_or_inventory(self):
        self.lua.execute('''
          ns.ProfRouteAuto.AHPriceOf=function()error('live price changed')end
          ns.VendorPriceDB={GetOffers=function()error('live supplier changed')end}
          ns.AuctionBridge={GetAuctionSupply=function()error('live inventory changed')end}
          local snap={prices={[11]=3},offers={},auctionSupply={}}
          local list,total,complete=ns.ProfRouteAuto.MaterialPurchases(11,2,{snapshot=snap})
          assert(complete and total==6 and list[1].source=='ah' and list[1].supplyObserved==false)
        ''')

    def test_pattern_and_material_share_the_same_finite_auction_budget(self):
        self.lua.execute('''
          ns.ProfRecipes.alchemy.rows[1][13]={11}
          ns.ProfEconomy.Known=function()return false end
          local snap={prices={[11]=1},offers={},formulaOffers={},known={},noFormula=false,
            stamp=1000,auctionSupply={[11]={quantity=2,observedAt=900,complete=true,
              ownerExcluded=true,source='client-auction-results'}}}
          local sum=ns.ProfRouteAuto.FixedPlan('alchemy',{target=3,snapshot=snap,noFormula=false,recoveryEnabled=false})
          assert(#sum.formulas==1 and sum.formulas[1].source=='ah' and sum.formulasTotal==1)
          assert(sum.feasible==false and sum.mats[1].unavailable and sum.mats[1].availableCount==1)
        ''')

    def test_old_fishing_purchase_policy_requests_recalculation_without_settings_change(self):
        self.lua.execute('''
          local ra=ns.ProfRouteAuto
          ra.ComputeFishing=function()return {planVersion=2,scheme='fishing',fishingRouteRevision=2,
            start=1,target=3,targetReached=true,status='complete',feasible=true,steps={{1,3,101,2}},
            mats={},formulas={},total=0,priced=true}end
          local opts={start=1,target=3,scheme='fishing'}
          local current=ra.Get('cooking',opts)
          assert(current and current.fishingRouteRevision==2 and not current.stale)
          current.fishingRouteRevision=1
          local old=ra.Get('cooking',opts)
          assert(old==current and old.staleReason=='procurement-policy' and not old.settingsChanged)
        ''')

    def test_reliable_npc_quote_is_not_displaced_by_a_cheaper_estimate(self):
        self.lua.execute('''
          local snap={prices={[11]=100},offers={[11]={
            {npcID=1,price=1,quantity=1,unlimited=true,estimated=true},
            {npcID=2,price=20,quantity=1,unlimited=true,reference=true}}},auctionSupply={}}
          local list,total,complete=ns.ProfRouteAuto.MaterialPurchases(11,1,{snapshot=snap})
          assert(complete and total==20 and list[1].npcID==2)
          snap.offers[11]={snap.offers[11][1]}
          list,total,complete=ns.ProfRouteAuto.MaterialPurchases(11,1,{snapshot=snap})
          assert(complete and total==100 and list[1].source=='ah')
        ''')

    def test_live_nonauctionable_item_cannot_use_an_auction_quote(self):
        self.lua.execute('''
          local probes=0
          ns.ProfEconomy.NonAuctionableItem=function(id)probes=probes+1;return id==11 end
          ns.ProfRouteAuto.AHPriceOf=function()return 1 end
          ns.VendorPriceDB={GetOffers=function()return {}end}
          local list,total,complete,reason=ns.ProfRouteAuto.MaterialPurchases(11,1)
          assert(probes==1 and not complete and reason=='materialUnavailable')
          assert(list[1].source~='ah' and list[1].unavailable)
          ns.ProfEconomy.NonAuctionableItem=function()error('frozen snapshot read live binding')end
          list,total,complete=ns.ProfRouteAuto.MaterialPurchases(11,1,{snapshot={prices={[11]=1},offers={},auctionSupply={}}})
          assert(complete and total==1 and list[1].source=='ah')
        ''')

    def test_more_expensive_npc_pattern_can_leave_cheap_auction_stock_for_materials(self):
        self.lua.execute('''
          ns.ProfRecipes.alchemy.rows[1][13]={11}
          ns.ProfEconomy.Known=function()return false end
          local snap={prices={[11]=1},offers={[11]={{npcID=1,price=7,quantity=1,unlimited=true}}},
            formulaOffers={[11]={{npcID=2,price=2,quantity=1,unlimited=true,available=true,purchasable=true}}},
            known={},noFormula=false,auctionSupply={[11]={quantity=1}}}
          local sum=ns.ProfRouteAuto.FixedPlan('alchemy',{target=3,snapshot=snap,noFormula=false,recoveryEnabled=false})
          assert(sum.formulas[1].source=='vendor' and sum.formulasTotal==2)
          assert(sum.total==10 and sum.vendorTotal==9 and sum.ahTotal==1)
          assert(sum.steps[1].cost==10,'step cost '..tostring(sum.steps[1].cost)..' attributed '..tostring(sum.steps[1].attributedCost))
        ''')


if __name__=='__main__':unittest.main()
