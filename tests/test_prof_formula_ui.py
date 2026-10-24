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
          PD.TextW=function(s,fs)return #s*fs end
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

    def test_drop_summary_is_only_shown_once_and_retains_source_tooltip(self):
        source=(ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        begin=source.index('function PD.SourceParts(')
        self.lua.execute(source[begin:source.index('function PD.SourceText(',begin)])
        self.lua.execute('''
          PD.DropLines=function()return{{'Caretaker Weston · 30%'}}end
          local rows={};PD.RowsFormulaShop(rows,{formulas={{id=99,spell=101,profession='alchemy',
            source='ah',cost=20,ahPrice=20,sources={skill=190,drops={{id=1},{id=2},{id=3}}}}}})
          local drops,skills=0,0
          for _,row in ipairs(rows)do
            if row.text and row.text:find('掉落 3 处',1,true)then
              drops=drops+1
              assert(row.text=='掉落 3 处 · 精确坐标未收录')
              assert(row.lines[1][1]=='Caretaker Weston · 30%')
            end
            if row.text=='技能 190' then skills=skills+1 end
          end
          assert(drops==1 and skills==1,'shopping source rows duplicated or lost')
        ''')

    def test_limited_formula_has_visible_tag_even_when_bought_at_auction(self):
        self.lua.execute('''
          for _,selected in ipairs({'vendor','ah'})do
            local rows={};PD.RowsFormulaShop(rows,{formulas={{id=99,spell=101,
              profession='alchemy',cost=7,source=selected,limited=true,sources={}}}})
            local found=false
            for _,row in ipairs(rows)do if row.it then
              assert(row.tag.text:find('限量刷新',1,true),'limited formula has no visible stock tag')
              found=true
            end end
            assert(found)
          end
        ''')

    def test_drop_regions_are_visible_without_inventing_npc_coordinates(self):
        self.lua.execute('''
          local rows={};PD.RowsFormulaShop(rows,{formulas={{id=99,spell=101,profession='alchemy',
            source='ah',cost=20,sources={drops={{npc='A',zone='千针石林'},
              {npc='B',zone='阿拉希高地'},{npc='C',zone='千针石林'}}}}}})
          local found=false
          for _,row in ipairs(rows)do if row.text and row.text:find('掉落 3 处',1,true)then
            found=true
            assert(row.text=='掉落 3 处 · 千针石林 / 阿拉希高地 · 精确坐标未收录')
            assert(not row.act,'region name was mistaken for NPC coordinates')
          end end
          assert(found)
        ''')

    def test_long_formula_name_keeps_limited_badge_and_quantity_inside_row(self):
        hui=(ROOT/'Core/Hui.lua').read_text(encoding='utf-8-sig')
        self.lua.execute(hui[:hui.index('ns.hui.CharStep = HCharStep')],'Test',self.lua.globals().ns)
        self.lua.execute('''
          PD.TextW=ns.hui.TextW;PD.Fit=ns.hui.Fit
          DG.ItemName=function()return string.rep('A very long recipe name ',8)end
          for _,labels in ipairs({{'NPC购买','限量刷新'},{'NPC purchase','Limited, restocking'}})do
            L['NPC购买']=labels[1];L['限量刷新']=labels[2]
            for _,width in ipairs({280,340,440})do
              PD.splitLW=width
              local rows={};PD.RowsFormulaShop(rows,{formulas={{id=99,spell=101,
                profession='alchemy',cost=7,count=12,source='vendor',limited=true,sources={}}}})
              for _,row in ipairs(rows)do if row.it then
                local used=32+PD.TextW(row.text,13)+14+PD.TextW(row.tag.text,10)
                  +8+PD.TextW(row.right,12)+6
                assert(used<=width,'formula name overlaps limited badge or purchase quantity')
                assert(row.right=='×12' and row.tag.text:find(labels[2],1,true))
              end end
            end
          end
        ''')

    def test_partial_route_progress_remains_visible_after_search_finishes(self):
        self.lua.execute('''
          for _,status in ipairs({'complete','incomplete','infeasible'})do
            local plan={planVersion=2,partial=true,start=151,target=225,plannedTo=152,
              status='incomplete',searchState={status=status,budgetLimited=true}}
            assert(PD.PlanStatusText(plan)=='已计算至 152；后续路线待补全',
              'terminal optimization status hid incomplete saved route')
            plan.searchState.status='searching'
            assert(PD.PlanStatusText(plan)=='后台优化中')
          end
        ''')

    def test_non_joint_legacy_plan_does_not_report_changed_partner(self):
        self.lua.execute('''
          local text=PD.PlanStatusText({status='recalculate_required',
            diagnostics={{code='professionChanged'}}})
          assert(text=='专业学习状态或旧路线规则已变化，请重新计算路线。')
          assert(not text:find('搭配专业',1,true))
        ''')

    def test_budget_exhaustion_and_purchase_uncertainty_do_not_claim_missing_route_data(self):
        self.lua.execute('''
          for _,nested in ipairs({true,false})do
            local plan={status='incomplete',targetReached=false,budgetLimited=true}
            if nested then plan.searchState={status='incomplete',budgetLimited=true}end
            assert(PD.PlanStatusText(plan)=='本轮计算已结束，尚未找到完整路线。')
            plan.targetReached=true
            assert(PD.PlanStatusText(plan)=='路线已到目标；采购资料尚未全部核实。')
            plan.targetReached=false;plan.budgetLimited=false;plan.searchState=nil
            assert(PD.PlanStatusText(plan)=='资料或价格不完整')
          end
        ''')

    def test_saved_english_quote_uses_matching_localized_recipe_vendor_name(self):
        self.lua.execute('''
          local old={vendors={{id=7,name='Schema Seller'},{id=8,name='Untranslated Seller'}}}
          local original={vendors={{id=7,name='配方商人'},{id=999,name='其他商人'}}}
          local rows={};PD.RowsFormulaShop(rows,{formulas={{id=99,spell=101,profession='alchemy',
            count=1,cost=7,source='vendor',unlimited=true,sources=old,recipe={source=original},
            vendorOffers={{npcID=7,name='Schema Seller',price=7,quantity=1,unlimited=true}}}}})
          local name=false
          for _,row in ipairs(rows)do if row.it then
            for _,line in ipairs(row.lines)do
              if line[1]=='配方商人：7 · 固定售卖（不限量）' then name=true end
              assert(not line[1]:find('Schema Seller',1,true))
            end
          end end
          assert(name,'saved quote tooltip kept English despite matching localized NPC ID')
          local display=PD.FormulaDisplaySource({sources=old,recipe={source=original}})
          assert(#display.vendors==2 and display.vendors[1].name=='配方商人')
          assert(display.vendors[2].name=='Untranslated Seller')
          assert(old.vendors[1].name=='Schema Seller','display mutated frozen source data')
        ''')

    def test_untranslated_vendor_uses_its_real_name_without_duplicate_original_name(self):
        self.lua.execute('''
          GetLocale=function()return 'zhCN' end
          local rows={};PD.RowsFormulaShop(rows,{formulas={{id=99,spell=101,profession='alchemy',
            count=1,cost=7,source='vendor',unlimited=true,
            sources={vendors={{id=7,name='No verified locale name'}}},
            vendorOffers={{npcID=7,name='No verified locale name',npcNameCanonical='No verified locale name',
              npcNameUntranslated=true,price=7,quantity=1,unlimited=true}}}}})
          local compact,canonical=false,false
          for _,row in ipairs(rows)do if row.it then
            for _,line in ipairs(row.lines)do
              if line[1]=='No verified locale name：7 · 固定售卖（不限量）' then compact=true end
              if line[1]=='原文名称：No verified locale name' then canonical=true end
            end
          end end
          assert(compact and not canonical,'real vendor name was hidden or repeated')
        ''')

    def test_saved_numbered_vendor_recovers_canonical_name_for_tooltip_and_map_sources(self):
        self.lua.execute('''
          GetLocale=function()return 'zhCN'end
          local entry={id=99,spell=101,profession='alchemy',count=1,cost=7,source='vendor',
            unlimited=true,sources={vendors={{id=7,name='商人 NPC #7',zone='地区'}}},
            vendorOffers={{npcID=7,name='商人 NPC #7',npcNameCanonical='Gorhak',
              npcNameUntranslated=true,price=7,quantity=1,unlimited=true}}}
          local display=PD.FormulaDisplaySource(entry)
          assert(display.vendors[1].name=='Gorhak')
          assert(entry.sources.vendors[1].name=='商人 NPC #7','display rewrote frozen source data')
          local rows={};PD.RowsFormulaShop(rows,{formulas={entry}})
          local found=false
          for _,row in ipairs(rows)do if row.it then
            for _,line in ipairs(row.lines)do
              if line[1]=='Gorhak：7 · 固定售卖（不限量）'then found=true end
              assert(not line[1]:find('商人 NPC #7',1,true))
              assert(not line[1]:find('原文名称：Gorhak',1,true))
            end
          end end
          assert(found)
          assert(PD.LocalizedVendorName(7,'#7','Gorhak')=='Gorhak')
          assert(PD.LocalizedVendorName(7,'Vendor NPC #7','Gorhak')=='Gorhak')
          assert(PD.LocalizedVendorName(7,'  ','Gorhak')=='Gorhak')
          L['Gorhak']='已有译名'
          assert(PD.FormulaDisplaySource(entry).vendors[1].name=='已有译名')
          assert(PD.LocalizedVendorName(7,nil)=='商人 NPC #7')
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
