"""Selected purchasing sources remain authoritative throughout the native UI/HUD."""
import unittest

import test_prof_ui_fusion as ui
import test_prof_issue4 as issue4


class PurchaseSourceAuthorityUITests(unittest.TestCase):
    setUp = ui.ProfessionUIFusionTests.setUp
    boot = ui.ProfessionUIFusionTests.boot

    def test_explicit_auction_source_overrides_legacy_vendor_flag_and_keeps_stock(self):
        self.lua.execute('''
          local entry={id=11,count=2,cost=2,source='ah',vendor=true,npcID=99,
            availableCount=20,supplyObserved=true,supplyComplete=true,supplyRequired=2}
          assert(PD.PurchaseSource(entry)==ns.L['拍卖行'])
          assert(PD.TagInkOf(entry)==PD.TAG_INK.ah)
          assert(PD.AuctionSupplyText(entry):find('20',1,true))
          assert(#PD.AuctionSupplyLines(entry)>0)
          assert(PD.PurchaseSource({source='unknown',vendor=true})==ns.L['尚无购买来源'])
          assert(PD.PurchaseSource({vendor=true})==ns.L['NPC购买'])
          assert(PD.PurchaseSource({sourceType='auction',vendor=true})==ns.L['拍卖行'])
          local unknown={id=11,source='ah',vendor=true,supplyObserved=false}
          local head,detail=PD.PlanSupplyParts({auctionSupplyUnknown=1,mats={unknown}})
          assert(head and detail:find('Item11',1,true))
        ''')

    def test_grouping_preserves_selected_source_and_npc_without_requoting(self):
        self.lua.execute('''
          ns.VendorPriceDB={GetOffers=function()error('display must not reselect a supplier')end}
          local vendor={id=11,count=5,source='vendor',npcID=7,unit=2,cost=10,
            unlimited=true,bundleSize=5}
          local auction={id=12,count=2,source='ah',vendor=true,npcID=8,cost=2}
          local mixed={id=13,count=3,source='mixed',npcID=8,cost=6}
          local missing={id=14,count=1,source='unknown',vendor=true,npcID=8}
          local noLocation={id=15,count=1,source='vendor',cost=5}
          local data={mats={vendor,auction,mixed,missing,noLocation}}
          local groups,ah,other=PD.TripGroups(data)
          assert(#groups==1 and groups[1].npcID==7 and groups[1].total==10)
          assert(groups[1].items[1].bundleSize==5 and groups[1].items[1].unlimited)
          assert(#ah==1 and ah[1]==auction and #other==3)
          PD.Wrap=function(text)return{text}end
          PD.ProcureActive=function()return nil end
          local rows={};PD.PushTripGroups(rows,data)
          local found={}
          for _,row in ipairs(rows)do
            if row.it then found[row.it[1]]=row end
          end
          assert(found[12].tag.text==ns.L['拍卖行'])
          assert(found[13].tag.text==ns.L['商人']..' / '..ns.L['拍卖行'])
          assert(found[14].tag.text==ns.L['尚无购买来源'])
          assert(found[15].tag.text==ns.L['NPC购买'])
          local text=''
          for _,line in ipairs(found[12].lines)do text=text..tostring(line[1]) end
          assert(text:find(ns.L['本路线选择从拍卖行购买。'],1,true))
          assert(not text:find(ns.L['没有商人直售货源，需要从拍卖行购买。'],1,true))
        ''')

    def test_new_purchasing_explanations_have_all_three_translations(self):
        for locale in ('zhCN','zhTW','enUS'):
            self.boot(locale)
            self.lua.execute('''
              for _,key in ipairs({'NPC也有出售','本路线选择从拍卖行购买。',
                '按本路线选定的货源分组；点击商人条目在地图上定位。'})do
                assert(type(rawget(ns.L,key))=='string' and rawget(ns.L,key)~='')
              end
            ''')


class PurchaseSourceAuthorityHUDTests(unittest.TestCase):
    setUp = issue4.Issue4Tests.setUp
    boot = ui.ProfessionUIFusionTests.boot

    def test_default_hud_displays_and_exports_auction_purchase_for_a_vendor_sold_material(self):
        self.lua.execute('''
          ns.ProfLeveling.alchemy.sold={11}
          allWidgets={};local base=recordedWidget
          recordedWidget=function()
            local widget=base();allWidgets[#allWidgets+1]=widget;return widget
          end
          CreateFrame=recordedWidget
          ns.ProfHost.MakeFS=recordedWidget;ns.ProfHost.NewButton=recordedWidget
          ns.ProfHost.DG.ItemIcon=function()return '?'end
        ''')
        self.load((ui.ROOT/'Core/ProfFollow.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local snapshot=fixture();snapshot.prices[11]=1
          snapshot.auctionSupply={[11]={quantity=30}}
          snapshot.offers={[11]={{npcID=9,price=20,quantity=1,unlimited=true}}}
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(snapshot)end
          local plan=finish('alchemy',{snapshot=snapshot,start=1,target=3,recoveryEnabled=false})
          assert(plan.targetReached and plan.ahTotal==2 and plan.vendorTotal==0,
            tostring(plan.targetReached)..':'..tostring(plan.ahTotal)..':'..tostring(plan.vendorTotal))
          assert(#plan.mats==1 and plan.mats[1].source=='ah')
          -- A legacy availability flag cannot override the selected source.
          plan.mats[1].vendor=true;plan.mats[1].npcID=9
          assert(ns.ProfExecution.Bind('alchemy',plan))
          ns.AuctionBridge={GetAuctionSupply=function()return {quantity=30}end,
            DoImport=function(name,items)imported=items end}
          DungeonsForeverDB.prof.follow={['Test-Realm']={slug='alchemy',skill=1,step=1,t0=1000}}
          local pf=ns.ProfFollow
          pf.Build();pf.f:Show();pf.showShop=true;pf.Paint()
          assert(not pf.procureRes and not pf.f.vendorShop:IsShown())
          local list=pf.ShoppingList('alchemy')
          assert(#list==1 and list[1].source=='ah' and list[1].availableCount==30)
          local stockText=pf.ShoppingSourceText(list[1]);local painted=false
          for _,widget in ipairs(allWidgets)do
            if widget.text==stockText then painted=true end
            assert(widget.text~=ns.L['直售'],'NPC availability became a selected source badge')
          end
          assert(painted,'native default HUD did not paint the Auctionator quantity')
          pf.ImportShoppingList('alchemy','Alchemy')
          assert(#imported==1 and imported[1].name=='Item11' and imported[1].need==2)
        ''')


if __name__=='__main__':
    unittest.main()
