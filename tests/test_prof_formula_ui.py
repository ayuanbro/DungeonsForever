"""Formula shopping presentation and source map actions without a game window."""
import unittest
import test_prof_ui_regressions as ui_fixture
from test_prof_ui_regressions import ROOT


class FormulaUITests(unittest.TestCase):
    def setUp(self):
        ui_fixture.ProfessionUIRegressions.setUp(self)
        source=(ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        for start,end in (
            ('function PD.VendorListOf(', 'function PD.CampZoneName('),
            ('function PD.VendorEntries(', 'function PD.DropEntries('),
            ('function PD.FormulaStockText(', 'function PD.RowsAutoShop('),
        ):
            begin=source.index(start);self.lua.execute(source[begin:source.index(end,begin)])
        self.lua.execute('''
          D={pro={alchemy={name='Alchemy'}}};PD.COL_LW=400;PD.ROW_H=34;PD.ROW_H1=22
          PD.Fit=function(s)return s end;PD.StepName=function(s)return 'Spell'..s[3]end
          PD.DropEntries=function()return{}end;PD.DropLines=function()return{}end
          PD.VendorLines=function()return{}end
          PD.HideVendorPick=function()end
          PD.MarkVendorLoc=function(loc)marked=loc end
          PD.SourceParts=function(src)
            if #(src.vendors or{})>0 then return{{vendor=true,text='Vendor source'}}end
            return{}
          end
          PushHead=function(rows,text)rows[#rows+1]={kind='head',text=text}end
          PushGap=function()end
        ''')

    def test_formula_row_shows_both_prices_stock_recipe_and_clickable_vendor_map(self):
        self.lua.execute('''
          ns.ProfVendors={[7]={1519,1453,50,60}}
          local f={id=99,spell=101,profession='alchemy',count=1,cost=7,source='vendor',
            ahPrice=20,vendorPrice=7,unlimited=true,sources={vendors={{id=7,name='Seller'}}},
            vendorOffers={{npcID=7,price=7,quantity=1,unlimited=true}}}
          local rows={};PD.RowsFormulaShop(rows,{formulas={f}})
          local prices,stock,recipe,action=false,false,false,nil
          for _,r in ipairs(rows)do
            if r.text=='拍卖行：20 · NPC：7' then prices=true end
            if r.text=='商人库存：固定售卖（不限量）' then stock=true end
            if r.sub=='用于配方：Alchemy · Spell101' then recipe=true end
            if r.act then action=r.act end
          end
          assert(prices and stock and recipe and action)
          action();assert(marked==ns.ProfVendors[7])
        ''')

    def test_stock_unknown_is_not_labeled_unlimited(self):
        self.lua.execute('''
          assert(PD.FormulaStockText({stockUnknown=true})=='商人库存：性质尚未核实')
          assert(PD.FormulaStockText({limited=true})=='商人库存：限量刷新')
          local rows={};PD.RowsFormulaShop(rows,{formulas={{id=99,spell=101,profession='alchemy',
            source='ah',cost=20,ahPrice=20,stockUnknown=true,sources={vendors={{id=7,name='Seller'}}}}}})
          for _,r in ipairs(rows)do assert(r.text~='商人库存：固定售卖（不限量）')end
        ''')

    def test_formula_tooltip_shows_each_generated_npc_price_source(self):
        self.lua.execute('''
          assert(PD.VendorPriceSourceText('client')=='购买价格来源：客户端')
          assert(PD.VendorPriceSourceText('wowhead')=='购买价格来源：Wowhead')
          assert(PD.VendorPriceSourceText(nil)==nil and PD.VendorPriceSourceText('unknown')==nil)
          local rows={};PD.RowsFormulaShop(rows,{formulas={{id=99,spell=101,profession='alchemy',
            count=1,cost=7,source='vendor',vendorPrice=7,unlimited=true,sources={},vendorOffers={
              {npcID=7,price=7,quantity=1,unlimited=true,priceSource='client'},
              {npcID=8,price=9,quantity=1,unlimited=true,priceSource='wowhead'}}}}})
          local client,wowhead=false,false
          for _,row in ipairs(rows) do if row.it then
            for _,line in ipairs(row.lines) do
              if line[1]=='购买价格来源：客户端' then client=true end
              if line[1]=='购买价格来源：Wowhead' then wowhead=true end
              assert(not line[1]:find('报价核验：',1,true),'unknown verification date was invented')
            end
          end end
          assert(client and wowhead,'formula tooltip lost an NPC quote source')
        ''')

    def test_unknown_formula_id_and_quest_coordinates_are_not_invented(self):
        self.lua.execute('''
          DG.ItemName=function(id)assert(id,'nil item lookup');return'Item'..id end
          local rows={};PD.RowsFormulaShop(rows,{formulas={{spell=101,profession='alchemy',
            questOnly=true,unpriced=true,blocked=true,usable=false,sources={quests={{id=769,name='Quest'}}}}}})
          local unknown,quest=false,false
          for _,r in ipairs(rows)do
            if r.text=='未知图纸' then unknown=true end
            if r.text=='任务：Quest · 暂无坐标' then quest=true;assert(not r.act)end
          end
          assert(unknown and quest)
        ''')

    def test_formula_import_only_contains_selected_auction_purchases(self):
        self.lua.execute('''
          ns.AuctionBridge={DoImport=function(_,items)imported=items end}
          PD.ShopImport({planVersion=2,mats={},formulas={
            {id=91,count=1,source='ah'}, {id=92,count=1,source='vendor'},
            {id=93,count=1,source='ah',known=true}, {id=94,count=1,source='ah',blocked=true},
            {id=95,count=1,source='ah',unpriced=true},{id=96,count=1,source='ah',vendor=true}}})
          assert(#imported==1 and imported[1].name=='Item91')
        ''')

    def test_fixed_shop_with_only_vendor_formula_has_total_and_no_auction_age_warning(self):
        source=(ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        begin=source.index('function PD.RowsAutoShop(')
        self.lua.execute(source[begin:source.index('-- 材料购物清单导入拍卖行插件',begin)])
        self.lua.execute('''
          C_GOLD={1,1,0};PD.SEC_GAP=8;PD.SEC_PAD=2
          CountUnpriced=function()return 0 end
          local rows={};PD.RowsAutoShop(rows,{mode='fixed',target=20,priced=true,
            total=5,matTotal=0,formulasTotal=5,formulaComplete=true,completeCost=true,
            vendorTotal=5,ahTotal=0,mats={},formulas={{id=99,profession='alchemy',spell=101,
              cost=5,vendorPrice=5,source='vendor',unlimited=true,sources={}}}})
          local found=false
          for _,r in ipairs(rows)do
            if r.text=='图纸支出：5' then found=true end
            assert(r.text~='价格快照年龄未知（Auctionator）','vendor-only formula requested auction age')
          end
          assert(found)
        ''')

    def test_auction_material_and_formula_tips_share_snapshot_quantity_metadata(self):
        source=(ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        begin=source.index('function PD.RowsAutoShop(')
        self.lua.execute(source[begin:source.index('-- 材料购物清单导入拍卖行插件',begin)])
        self.lua.execute('''
          C_GOLD={1,1,0};PD.SEC_GAP=8;PD.SEC_PAD=2;CountUnpriced=function()return 0 end
          local rows={};PD.RowsAutoShop(rows,{planVersion=2,feasible=true,total=25,
            completeCost=true,auctionSupplyUnknown=0,mats={{id=11,count=3,cost=15,unit=5,
              source='ah',availableCount=7,supplyObserved=true,supplyComplete=false}},
            formulas={{id=99,profession='alchemy',spell=101,cost=10,ahPrice=10,source='ah',
              count=1,availableCount=2,supplyObserved=true,supplyComplete=true,sources={}}}})
          local material,formula=false,false
          for _,row in ipairs(rows)do
            for _,line in ipairs(row.lines or{})do
              if line[1]=='拍卖行已读取：7 件（结果未全部读取）；本路线购买 3 件。' then material=true end
              if line[1]=='拍卖行数量快照：2 件；本路线购买 1 件。' then formula=true end
            end
          end
          assert(material and formula)
        ''')


if __name__=='__main__':
    unittest.main()
