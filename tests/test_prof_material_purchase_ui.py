"""Ordinary material quotes display a bundle price without supplier identity."""
import unittest

import test_prof_follow as follow_fixture
import test_prof_ui_regressions as ui_fixture

ROOT=ui_fixture.ROOT


class MaterialShoppingPresentation(unittest.TestCase):
    def setUp(self):
        ui_fixture.ProfessionUIRegressions.setUp(self)
        source=(ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        start=source.index('function PD.RowsAutoShop(')
        self.lua.execute(source[start:source.index('function PD.ShopImport(',start)])
        self.lua.execute('''
          PD.COL_LW=600;PD.SEC_GAP=8;PD.SEC_PAD=4;C_GOLD={1,1,0}
          PD.Fit=function(text)return text end
          PushHead=function(rows,text,col)rows[#rows+1]={kind='head',text=text,col=col}end
          PushGap=function()end;CountUnpriced=function()return 0 end
          ns.ProfVendors=setmetatable({},{__index=function()error('material display requested a supplier map')end})
          function hasLine(lines,text)
            for _,line in ipairs(lines)do if line[1]==text then return true end end
            return false
          end
        ''')

    def test_material_price_and_bundle_display_without_supplier_identity(self):
        self.lua.execute('''
          for _,source in ipairs({'vendor','npc'})do
            for _,oldID in ipairs({false,0,777})do
              local material={id=11,count=10,need=7,cost=40,unit=4,bundleSize=5,bundlePrice=20,
                source=source,npcID=oldID or nil,priceSource='client'}
              local rows={};PD.RowsAutoShop(rows,{planVersion=2,status='complete',feasible=true,
                total=40,vendorTotal=40,ahTotal=0,mats={material}})
              local found=false
              for _,row in ipairs(rows)do if row.it then
                found=true;assert(row.tag.text=='NPC购买')
                assert(row.right=='×10 · 4' and row.right2=='40')
                assert(hasLine(row.lines,'需要：7') and hasLine(row.lines,'每组 5 件 · 20'))
                assert(not row.act,'ordinary material gained a supplier map action')
                for _,line in ipairs(row.lines)do
                  assert(not line[1]:find('商人 NPC',1,true),'material tooltip showed supplier identity')
                  assert(not line[1]:find('军需官',1,true),'material tooltip invented a quartermaster')
                  assert(not line[1]:find('限量',1,true),'material tooltip imposed supplier stock rules')
                end
              end end
              assert(found,'anonymous material quote disappeared from shopping list')
            end
          end
        ''')

    def test_missing_anonymous_purchase_price_is_not_reported_as_missing_auction(self):
        self.lua.execute('''
          local rows={};PD.RowsAutoShop(rows,{planVersion=2,status='complete',feasible=true,
            total=0,vendorTotal=0,ahTotal=0,mats={{id=11,count=5,source='vendor',unpriced=true}}})
          for _,row in ipairs(rows)do if row.it then
            assert(hasLine(row.lines,'NPC购买价格尚未配置。'))
            assert(not hasLine(row.lines,'价格未知（Auctionator 无记录）'))
          end end
        ''')

    def test_fishing_copy_explains_item_prices_in_each_supported_locale(self):
        source=(ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        self.assertNotIn('鱼类自行钓取；其他材料只使用不限量商人货物。',source)
        self.assertIn('鱼类自行钓取；其他材料按物品购买价计算。',source)
        for locale in ('zhCN','zhTW','enUS'):
            self.lua.globals().testLocale=locale
            self.lua.execute('GetLocale=function()return testLocale end')
            for path in ('zhCN',locale):
                self.lua.execute((ROOT/'Locales'/f'{path}.lua').read_text(encoding='utf-8-sig'),'Test',self.lua.globals().ns)
            text=self.lua.eval("ns.L['鱼类自行钓取；其他材料按物品购买价计算。']")
            self.assertNotIn('不限量',text)
            self.assertNotIn('unlimited',text)


class MaterialHUDPresentation(unittest.TestCase):
    def setUp(self):
        follow_fixture.FollowIntegrationTests.setUp(self)
        self.lua.execute('PD=ns.ProfModule;L=ns.L;RA=ns.ProfRouteAuto;RA.MoneyStr=tostring;format=string.format')
        source=(ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        start=source.index('function PD.VendorPriceSourceText(')
        self.lua.execute(source[start:source.index('function PD.FormulaStockText(',start)])
        self.lua.execute('''
          local original=makeFrame
          trackedFrames={}
          makeFrame=function()
            local frame=original();trackedFrames[#trackedFrames+1]=frame;return frame
          end
          ns.ProfHost.DG.ShowItemTip=function(_,_,lines)capturedTip=lines end
          function hasLine(lines,text)
            for _,line in ipairs(lines or{})do if line[1]==text then return true end end
            return false
          end
        ''')

    def test_hud_source_pill_retains_anonymous_bundle_quote(self):
        self.lua.execute('''
          currentResult.steps={{150,151,101,1,actionID='a1',profession='alchemy'}}
          currentResult.mats={{id=11,count=10,source='vendor',unit=4,cost=40,
            bundleSize=5,bundlePrice=20,priceSource='client'},{id=12,count=2,source='ah'}}
          local purchases=ns.ProfFollow.GetPurchases(followState)
          assert(#purchases==2 and purchases[1].npcID==nil)
          assert(purchases[1].source=='vendor' and purchases[1].bundleSize==5 and purchases[1].bundlePrice==20)
          ns.ProfFollow.Build();ns.ProfFollow.f:Show();ns.ProfFollow.showShop=true
          ns.ProfFollow.Sync();ns.ProfFollow.Paint()
          local found=false
          for _,frame in ipairs(trackedFrames)do
            if frame.__purchase and frame.__purchase.id==11 then
              assert(frame.fs.text=='NPC购买')
              frame.scripts.OnEnter(frame)
              assert(hasLine(capturedTip,'每组 5 件 · 20'))
              for _,line in ipairs(capturedTip)do assert(not line[1]:find('商人 NPC',1,true))end
              found=true
            end
          end
          assert(found,'anonymous vendor material has no HUD source pill')
        ''')


if __name__=='__main__':
    unittest.main()
