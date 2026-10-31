"""Default native procurement/HUD contracts and full-scan quantity edge cases.

No game directory is accessed. Client observations are explicit test inputs.
"""
import unittest
import test_prof_auctionator_full_scan as full_scan
import test_prof_vendor_regressions as vendor
from test_prof_native_data import native_runtime, ROOT


class FullScanFallbackFieldsTests(unittest.TestCase):
    setUp = full_scan.AuctionatorFullScanTests.setUp
    source = full_scan.AuctionatorFullScanTests.source

    def test_optional_full_owner_and_item_id_fields_use_valid_fallbacks(self):
        self.source()
        self.lua.execute('''
          local seller=rawRow(11,5,35,'Seller')
          seller.auctionInfo[15]='';seller.auctionInfo[17]=0
          local mine=rawRow(11,100,100,'Player')
          mine.auctionInfo[15]=''
          beginFull(2);sendFull({seller,mine});finishFull()
          local q=ns.AuctionBridge.GetAuctionSupply(11)
          assert(q and q.quantity==5 and q.ownerExcluded and q.complete)
          assert(ns.AuctionBridge.GetAuctionSupply(12).quantity==0)
          assert(#requests==0)
        ''')

    def test_ambiguous_owner_or_conflicting_positive_item_id_stays_unknown(self):
        self.source()
        self.lua.execute('''
          local ownerless=rawRow(11,5,35,nil)
          ownerless.auctionInfo[15]='';ownerless.auctionInfo[12]='Bidder'
          beginFull(1);sendFull({ownerless});finishFull()
          local b=ns.AuctionBridge
          assert(b.GetAuctionSupply(11)==nil and b.GetAuctionSupplyStatus(11)=='incomplete')
          local conflict=rawRow(11,5,35,'Seller');conflict.auctionInfo[17]=12
          beginFull(1);sendFull({conflict});finishFull()
          assert(b.GetAuctionSupply(11)==nil and b.GetAuctionSupply(12)==nil)
          assert(#requests==0)
        ''')


class CachedVendorRestrictionTests(unittest.TestCase):
    setUp = vendor.VendorRegressionTests.setUp

    def test_vendor_price_cache_cannot_revive_an_explicitly_blocked_supplier(self):
        self.lua.execute('''
          Auctionator={API={v1={GetVendorPriceByItemID=function()return 1 end}}}
          local bad=observed();bad.purchasable=false;save(bad)
          local ctx={reputationKey='72:4',allowVendorCache=true}
          assert(#ns.VendorPriceDB.GetSuppliers(3371,ctx)==0)
          for _,o in ipairs(ns.VendorPriceDB.GetOffers(3371,ctx))do
            assert(o.priceOnly or o.npcID~=1313,'cache revived an unpurchasable NPC')
          end
          bad=observed();bad.requirements={questID=123};save(bad)
          ctx.quests={[123]=false}
          assert(#ns.VendorPriceDB.GetSuppliers(3371,ctx)==0)
          for _,o in ipairs(ns.VendorPriceDB.GetOffers(3371,ctx))do
            assert(o.priceOnly or o.npcID~=1313,'cache bypassed a known access restriction')
          end
        ''')

    def test_unavailable_formula_remains_visible_but_not_buyable(self):
        self.lua.execute('''
          local bad=observed();bad.available=false;bad.formulaPrice=18;save(bad)
          local offers=ns.VendorPriceDB.GetFormulaOffers(3371,{reputationKey='72:4'})
          assert(#offers==1 and offers[1].source=='merchant')
          assert(offers[1].unlimited and offers[1].npcID==1313)
          assert(offers[1].available==false and offers[1].priceUsable==false)
        ''')


class NativeProfessionPurchasingMatrixTests(unittest.TestCase):
    def test_default_routes_keep_npc_costs_and_hud_leaves_without_optional_optimization(self):
        cases=(
            ('alchemy',7183,1,3371),
            ('blacksmithing',6517,85,3466),
            ('enchanting',7421,1,6217),
            ('engineering',3924,50,2880),
            ('leatherworking',2149,1,2320),
            ('tailoring',2387,1,2320),
            ('cooking',8604,1,2678),
        )
        for locale in ('zhCN','zhTW','enUS'):
            for slug,spell,level,npc_item in cases:
                with self.subTest(locale=locale,profession=slug):
                    lua=native_runtime(locale)
                    lua.globals().selected=slug;lua.globals().knownSpell=spell
                    lua.globals().startSkill=level;lua.globals().npcItem=npc_item
                    lua.execute('''
                      ns.ProfRouteAuto.AHPriceOf=function()return 1000000 end
                      ns.ProfModule.ProfLearned=function()return {[selected]={cur=startSkill,max=300}}end
                      observedKnown={[knownSpell]=true}
                      ns.ProfHost={DG={},Unpack=unpack}
                      C_Item={GetItemCount=function()return 0 end}
                      ns.AuctionBridge={GetAuctionSupply=function()return {quantity=100000,observedAt=1000,
                        complete=true,ownerExcluded=true,source='client-auction-results'}end}
                    ''')
                    lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                                (ROOT/'Core/ProfFollow.lua').read_text(encoding='utf-8-sig'))
                    lua.execute('''
                      local E,S=ns.ProfEconomy,ns.ProfRouteSolver
                      local s=E.Capture(selected,{start=startSkill,target=startSkill+1,autoCraftTools=false})
                      s.recipes={E.FindRecipe(selected,knownSpell)};s=E.Index(s)
                      local p=S.Compute(selected,{snapshot=s,start=startSkill,target=startSkill+1,
                        autoCraftTools=false,recoveryEnabled=false,cpuLimitMs=500})
                      assert(p.targetReached and p.steps[1][3]==knownSpell)
                      local expected,quantity,cost={},0,0
                      for _,m in ipairs(p.mats)do
                        if m.source=='vendor'then
                          assert(m.npcID and m.unlimited and m.priceSource~='auction')
                          expected[m.id]=(expected[m.id] or 0)+m.count
                          cost=cost+m.cost
                          if m.id==npcItem then quantity=quantity+m.count end
                        end
                      end
                      assert(quantity>0 and p.vendorTotal==cost and p.total==p.vendorTotal+p.ahTotal)
                      assert(#p.formulas==0,'a learned recipe acquired another pattern')
                      local hud=ns.ProfFollow.VendorPurchases(selected,p)
                      local seen={}
                      for _,m in ipairs(hud)do
                        assert(expected[m.id]==m.need and m.missing==m.need and m.npcID)
                        seen[m.id]=true
                      end
                      for id in pairs(expected)do assert(seen[id],'HUD lost a planned NPC purchase')end
                    ''')


if __name__=='__main__':unittest.main()
