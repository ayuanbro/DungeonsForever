"""Recipe-source hover details and preserved procurement/map behavior."""
import unittest

import test_prof_ui_regressions as ui_fixture
from test_prof_ui_regressions import ROOT


class RecipeSourceTests(unittest.TestCase):
    def setUp(self):
        ui_fixture.ProfessionUIRegressions.setUp(self)
        self.lua.execute('''
          UnitFactionGroup=function()return 'Alliance' end
          GetLocale=function()return 'zhCN' end
          ns.ProfItems={};ns.ProfVendors={[7]={12,1415,50,60},[8]={14,1416,30,40}}
          ns.AreaMap={[12]=1415,[14]=1416}
          GetAreaInfo=function(id)return ({[12]='艾尔文森林',[14]='杜隆塔尔'})[id] end
          C_Map={GetMapInfo=function(id)return {name='Map'..id} end}
          RA.AHPriceOf=function(id)return auctionPrices and auctionPrices[id]end
          local names={[99]='测试图纸',[123]='布料'}
          GetItemInfo=function(id)
            local name=names[id]
            if name then return name,'item:'..id,1,1,1,'','',1,'',456 end
          end
          GetItemIcon=function(id)return names[id] and 456 end
          DG.RequestItem=function(id)requestedItem=id end
          DG.ItemName=function(id)return names[id] or ('物品 #'..id),names[id]~=nil end
          DG.ItemIcon=function(id)return names[id] and 456 end
          C_CurrencyInfo={GetCurrencyInfo=function(id)
            if id==77 then return{name='荣誉奖章',iconFileID=789}end
          end}
          PD.VendorAct=function(src)return function(zone)vendorClicked=src;clickedZone=zone end end
          PD.VendorListOf=function(src)return src and src.vendors or{} end
          PD.VendorEntries=function(src)
            local out={}
            for _,v in ipairs(src.vendors or{})do
              if ns.ProfVendors[v.id] then out[#out+1]={loc=ns.ProfVendors[v.id],name=v.name}end
            end
            return out
          end
          PD.DropAct=function(src)return function(zone)dropClicked=src;clickedZone=zone end end
          PD.DropLines=function(src)
            local lines={}
            for _,drop in ipairs(src.drops or{})do
              lines[#lines+1]={'掉落：'..drop.npc..' · '..drop.zone}
            end
            return lines
          end
          PD.VendorLines=function()return{}end
          PD.SourceText=function()return '' end
          PD.CampZoneName=function(id,fallback)return GetAreaInfo(id) or fallback end
          function schema(id,values,quantity,npc)
            npc=npc or 7
            local raw={npc_id=npc,name_en='Seller',zone_id=12,side='n',stock=-1,
              cost_copper=37,cost_text='37c',price_source='client'}
            for key,value in pairs(values or{})do raw[key]=value end
            local item=ns.ProfItems[id] or {item_id=id,VendorStackCount=quantity or 1,offers={}}
            item.offers[npc]=raw;ns.ProfItems[id]=item
            return raw
          end
          function hasLine(lines,text)
            for _,line in ipairs(lines)do
              if line[1] and line[1]:find(text,1,true)then return true end
            end
            return false
          end
          function noProvenance(lines)
            for _,line in ipairs(lines)do
              assert(not line[1]:find('客户端数据',1,true))
              assert(not line[1]:find('参考资料',1,true))
              assert(not line[1]:find('客户端与参考资料',1,true))
            end
          end
        ''')
        self.lua.execute((ROOT / 'Core/ProfItemPrices.lua').read_text(encoding='utf-8-sig'),
                         'Test', self.lua.globals().ns)

    def test_dual_sources_have_independent_labels_tooltips_and_existing_actions(self):
        self.lua.execute('''
          schema(99)
          auctionPrices={[99]=55,[10]=900}
          local src={vendors={{id=7,name='本地商人',zone='艾尔文森林'}},
            drops={{id=70,npc='稀有怪',zone='西部荒野'}}}
          local dropAct=PD.DropAct(src)
          local parts=PD.FormulaSourceSegments(99,src,dropAct)
          assert(#parts==2 and parts[1].text=='图纸.掉落' and parts[2].text=='图纸.商人')
          local drops,vendors=parts[1].lines(),parts[2].lines()
          assert(hasLine(drops,'55') and hasLine(drops,'稀有怪') and hasLine(drops,'西部荒野'))
          assert(not hasLine(drops,'本地商人'))
          assert(hasLine(vendors,'55') and hasLine(vendors,'本地商人'))
          assert(not hasLine(vendors,'稀有怪'))
          assert(parts[1].act==dropAct)
          parts[1].act('drop-zone');assert(dropClicked==src and clickedZone=='drop-zone')
          parts[2].act('vendor-zone');assert(vendorClicked and clickedZone=='vendor-zone')
          noProvenance(drops);noProvenance(vendors)
          local plain=PD.FormulaSourceSegments(99,src)
          assert(not plain[1].act,'ordinary drop row gained a map action')
        ''')

    def test_formula_price_is_lazy_and_uses_formula_instead_of_output_item(self):
        self.lua.execute('''
          local src={drops={{npc='怪物',zone='地区'}}}
          auctionPrices={[10]=900}
          local part=PD.FormulaSourceSegments(99,src)[1]
          assert(hasLine(part.lines(),'暂无拍卖行价格'))
          auctionPrices[99]=55
          local lines=part.lines()
          assert(hasLine(lines,'拍卖行：55') and not hasLine(lines,'900'))
          auctionPrices[99]=88
          assert(hasLine(part.lines(),'拍卖行：88'),'hover retained an old auction price')
        ''')

    def test_drop_details_preserve_percentage_units_and_the_existing_source_limit(self):
        source = (ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        begin = source.rindex('function PD.DropLines(')
        end = source.index('-- ── 商人选择弹窗', begin)
        self.lua.execute(source[begin:end])
        self.lua.execute('''
          PD.DropEntries=function()return{{loc={1,2,3,4}}}end
          local drops={{npc='Guaranteed',zone='Dungeon',chance=100},
            {npc='World drop',zone='Zone',chance=0.1},
            {npc='Rare',zone='Zone',chance=37.9}}
          for i=4,9 do drops[i]={npc='Other'..i,zone='Zone'}end
          local lines=PD.FormulaSourceLines(99,{drops=drops},'drop')
          assert(hasLine(lines,'100%') and not hasLine(lines,'10000%'))
          assert(hasLine(lines,'0.1%') and hasLine(lines,'37.9%'))
          assert(hasLine(lines,'Other8') and not hasLine(lines,'Other9'))
          assert(not hasLine(lines,'点击：在地图上标记该 NPC'))
          local clickable=PD.FormulaSourceLines(99,{drops=drops},'drop',true)
          assert(hasLine(clickable,'点击：在地图上标记该 NPC'))
        ''')

    def test_vendor_hover_has_localized_name_faction_zone_and_bundle_price(self):
        self.lua.execute('''
          schema(99,{side='Alliance'},4)
          local src={vendors={{id=7,name='本地商人',zone='艾尔文森林',side='a'}}}
          local lines=PD.FormulaSourceLines(99,src,'vendor')
          assert(hasLine(lines,'本地商人'))
          assert(hasLine(lines,'联盟') and hasLine(lines,'艾尔文森林'))
          assert(hasLine(lines,'价格：37') and hasLine(lines,'每组 4 件'))
          noProvenance(lines)
        ''')

    def test_untranslated_raw_seller_retains_its_canonical_name(self):
        self.lua.execute('''
          schema(99,{name_en='Dala Fairmaw'})
          local lines=PD.FormulaSourceLines(99,nil,'vendor')
          assert(hasLine(lines,'商人 NPC #7'))
          assert(hasLine(lines,'原文名称：Dala Fairmaw'))
        ''')

    def test_unknown_vendor_details_and_currency_api_fallback_do_not_invent_values(self):
        self.lua.execute(r'''
          local raw=schema(99)
          raw.side=nil;raw.zone_id=nil;raw.cost_copper=nil;raw.cost_text=nil
          ns.ProfVendors={}
          local lines=PD.FormulaSourceLines(99,{vendors={{id=7,name='本地商人'}}},'vendor')
          assert(hasLine(lines,'阵营未知') and hasLine(lines,'地区未知') and hasLine(lines,'价格未知'))
          C_CurrencyInfo=nil
          GetCurrencyInfo=function(id)return '旧接口通货',0,'Interface\\Icons\\INV_Misc_Coin_01' end
          local text=PD.FormulaCostText({hasExtendedCost=true,currencyKind='currency',
            currencyID=77,currencyAmount=2})
          assert(text:find('旧接口通货',1,true))
          assert(text:find('|TInterface\\Icons\\INV_Misc_Coin_01:14:14|t',1,true))
          assert(not text:find('Interface\\Icons\\Interface',1,true))
          GetCurrencyInfo=nil
          local offer={hasExtendedCost=true,currencyKind='currency',currencyID=77,currencyAmount=2}
          assert(PD.FormulaCostText(offer):find('通货 #77',1,true))
          C_CurrencyInfo={GetCurrencyInfo=function()return{name='稍后到货通货',iconFileID=987}end}
          local refreshed=PD.FormulaCostText(offer)
          assert(refreshed:find('稍后到货通货',1,true) and refreshed:find('987',1,true))
        ''')

    def test_single_multiple_and_unknown_vendor_maps_keep_current_behavior(self):
        source = (ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        for start, end in (('function PD.VendorListOf(', 'function PD.CampZoneName('),
                           ('function PD.VendorEntries(', 'function PD.DropEntries(')):
            begin = source.index(start)
            self.lua.execute(source[begin:source.index(end, begin)])
        self.lua.execute('''
          PD.MarkVendorLoc=function(loc)markedCall=true;marked=loc end
          PD.HideVendorPick=function()hidden=true end
          PD.VendorPickToggle=function(zone,entries)pickerZone=zone;pickerEntries=entries end
          PD.VendorAct({vendors={{id=7,name='一个商人',side='a'}}})('first')
          assert(marked==ns.ProfVendors[7] and hidden)
          PD.VendorAct({vendors={{id=7,name='一个商人',side='a'},
            {id=8,name='另一个商人'}}})('second')
          assert(pickerZone=='second' and #pickerEntries==2)
          markedCall=false;marked='old'
          PD.VendorAct({vendors={{id=9,name='无坐标'}}})('third')
          assert(markedCall and marked==nil)
          local filtered=PD.VendorListOf({vendors={{id=7,side='a'},{id=8,side='h'}}})
          assert(#filtered==1 and filtered[1].id==7)
        ''')

    def test_display_cost_supports_currency_item_exchange_and_safe_id_fallback(self):
        self.lua.execute('''
          local currency=PD.FormulaCostText({costCopper=5,hasExtendedCost=true,currencyKind='currency',
            currencyID=77,currencyAmount=3,quantity=1})
          assert(currency:find('5',1,true) and currency:find('荣誉奖章',1,true))
          assert(currency:find('789',1,true) and currency:find('3',1,true))
          local item=PD.FormulaCostText({hasExtendedCost=true,currencyKind='item',currencyID=123,currencyAmount=2})
          assert(item:find('布料',1,true) and item:find('456',1,true) and item:find('2',1,true))
          local missing=PD.FormulaCostText({hasExtendedCost=true,currencyKind='currency',currencyID=700,currencyAmount=4})
          assert(missing:find('通货 #700',1,true) and missing:find('4',1,true))
          local missingItem=PD.FormulaCostText({hasExtendedCost=true,currencyKind='item',currencyID=701,currencyAmount=6})
          assert(missingItem:find('物品 #701',1,true) and missingItem:find('6',1,true))
          assert(PD.FormulaCostText({}):find('价格未知',1,true))
        ''')

    def test_item_exchange_names_refresh_after_client_data_arrives_without_render(self):
        self.lua.execute('''
          local ready=false
          DG.ItemName=function(id)
            if id==777 and ready then return '延迟加载物品',true end
            return '暂时没有客户端数据',false
          end
          DG.ItemIcon=function(id)return ready and 456 or 134400 end
          PD.ItemName=function()error('negative page memo must not be reused')end
          local offer={hasExtendedCost=true,currencyKind='item',currencyID=777,currencyAmount=3}
          assert(PD.FormulaCostText(offer):find('物品 #777',1,true))
          assert(requestedItem==777)
          ready=true
          local text=PD.FormulaCostText(offer)
          assert(text:find('延迟加载物品',1,true) and text:find('456',1,true))
        ''')

    def test_special_cost_display_does_not_make_a_gold_procurement_offer(self):
        self.lua.execute('''
          schema(99,{currency_kind='currency',currency_id=77,currency_amount=3})
          assert(#ns.ProfItemPrices.GetFormulaOffers(99)==0)
          local src={vendors={{id=7,name='本地商人',zone='艾尔文森林'}}}
          local lines=PD.FormulaSourceLines(99,src,'vendor')
          assert(hasLine(lines,'荣誉奖章') and hasLine(lines,'789'))
          assert(#ns.ProfItemPrices.GetFormulaOffers(99)==0)
          assert(#ns.ProfItemPrices.GetOffers(99)==0)
        ''')

    def test_recipe_adapters_hide_provenance_and_keep_formula_versus_output_ids(self):
        self.lua.execute('''
          schema(99)
          local src={formulaID=99,vendors={{id=7,name='本地商人'}}}
          local row={101,10,1,'','','',1,10,15,20,false,{{11,3}},{99},src}
          local recipe=PD.RecipeSpec(row)
          assert(#recipe.sourceSegments==1 and recipe.sourceSegments[1].text=='图纸.商人')
          assert(not recipe.right2 or not recipe.right2:find('客户端数据',1,true))
          noProvenance(recipe.tipExtra())
          local enchant={'name','display','slot','',1,10,15,20,{{11,3}},src,false,nil,nil,102,10}
          local en=PD.EnchantSpec(enchant)
          assert(#en.sourceSegments==1 and en.sourceSegments[1].text=='图纸.商人')
          noProvenance(en.tipExtra())
          local crafted={101,10,1,1,10,15,20,{{11,3}},99}
          local c=PD.CraftedSpec(crafted)
          assert(#c.sourceSegments==1 and c.sourceSegments[1].text=='图纸.商人')
          noProvenance(c.tipExtra())
          local trainer=PD.RecipeSpec({102,10,1,'','','',1,10,15,20,false,{{11,3}}})
          assert(trainer.right2=='训练师')
        ''')

    def test_enchant_without_formula_id_keeps_known_vendor_label_and_map_action(self):
        self.lua.execute('''
          local src={vendors={{id=7,name='附魔商人',zone='艾尔文森林',side='a'}}}
          local enchant={'name','display','slot','',1,10,15,20,{{11,3}},src,false,nil,nil,7443,10}
          local spec=PD.EnchantSpec(enchant)
          assert(spec.sourceSegments and #spec.sourceSegments==1)
          local part=spec.sourceSegments[1]
          assert(part.text=='图纸.商人' and part.act)
          local lines=part.lines()
          assert(hasLine(lines,'附魔商人') and hasLine(lines,'艾尔文森林'))
          assert(hasLine(lines,'暂无拍卖行价格') and hasLine(lines,'价格未知'))
          part.act('vendor-zone')
          assert(vendorClicked and vendorClicked.vendors[1].id==7 and clickedZone=='vendor-zone')
          assert(#ns.ProfItemPrices.GetFormulaOffers(nil)==0)
        ''')

    def test_vendor_without_npc_id_preserves_display_without_price_or_location(self):
        source = (ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        begin = source.index('function PD.VendorEntries(')
        self.lua.execute(source[begin:source.index('function PD.DropEntries(', begin)])
        self.lua.execute('''
          local src={vendors={{name='仅名称商人',zone='远方地区'}}}
          local segments=PD.FormulaSourceSegments(99,src)
          assert(segments and #segments==1 and segments[1].text=='图纸.商人')
          local lines=segments[1].lines()
          assert(hasLine(lines,'仅名称商人') and hasLine(lines,'远方地区'))
          assert(hasLine(lines,'价格未知') and hasLine(lines,'暂无拍卖行价格'))
          assert(not hasLine(lines,'点击：在地图上标记该 NPC'))
          PD.MarkVendorLoc=function(loc)markedCall=true;marked=loc end
          PD.HideVendorPick=function()end
          PD.VendorPickToggle=function()error('unknown NPC gained a map picker')end
          segments[1].act('zone')
          assert(markedCall and marked==nil)
          assert(#ns.ProfItemPrices.GetFormulaOffers(99)==0)
        ''')


class RecipeSourceLocaleTests(unittest.TestCase):
    def test_new_labels_and_cost_details_follow_all_three_client_locales(self):
        for locale, drop, vendor, currency in (
            ('zhCN', '图纸.掉落', '图纸.商人', '通货 #77'),
            ('zhTW', '圖紙.掉落', '圖紙.商人', '通貨 #77'),
            ('enUS', 'Pattern.Drop', 'Pattern.Vendor', 'Currency #77'),
        ):
            with self.subTest(locale=locale):
                lua = ui_fixture.LuaRuntime(unpack_returned_tuples=True)
                lua.execute('ns={};GetLocale=function()return "' + locale + '" end')
                ns = lua.globals().ns
                lua.execute((ROOT / 'Locales/zhCN.lua').read_text(encoding='utf-8-sig'), 'Test', ns)
                if locale != 'zhCN':
                    lua.execute((ROOT / ('Locales/' + locale + '.lua')).read_text(encoding='utf-8-sig'),
                                'Test', ns)
                self.assertEqual(ns.L['图纸.掉落'], drop)
                self.assertEqual(ns.L['图纸.商人'], vendor)
                self.assertEqual(lua.eval('string.format')(ns.L['通货 #%d'], 77), currency)


class RecipeSourcePoolTests(unittest.TestCase):
    def setUp(self):
        ui_fixture.ProfessionUIRegressions.setUp(self)
        self.lua.execute('''
          function sourceFrame()
            return {shown=false,text='',scripts={},points={},
              SetText=function(self,text)self.text=text end,
              SetWordWrap=function()end,
              Show=function(self)self.shown=true end,
              Hide=function(self)self.shown=false end,
              ClearAllPoints=function(self)self.points={}end,
              SetPoint=function(self,...)self.points[#self.points+1]={...}end,
              RegisterForClicks=function()end,
              EnableMouseWheel=function()end,
              SetScript=function(self,event,callback)self.scripts[event]=callback end}
          end
          MakeFS=sourceFrame;CreateFrame=sourceFrame
          PD.SetRowHover=function()end
          GameTooltip={lines={},SetOwner=function()end,
            ClearLines=function(self)self.lines={}end,
            AddLine=function(self,text)self.lines[#self.lines+1]=text end,
            Show=function(self)self.shown=true end,Hide=function(self)self.shown=false end}
          DG.ItemShiftClick=function(zone)shiftZone=zone end
          DG.WheelScroll=function()scrolled=true end
          PD.HideVendorPick=function()pickerHidden=true end
        ''')
        source = (ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        for start, end in (('function PD.WireTipZone(', '-- ── 配方页「锚点分段链」'),
                           ('function PD.ClearMatSegs(', '-- 摆材料分段链：')):
            begin = source.index(start)
            self.lua.execute(source[begin:source.index(end, begin)])

    def test_dual_to_single_to_other_page_clears_stale_tooltips_actions_and_text(self):
        self.lua.execute('''
          local row={}
          local current='first'
          local segments={{text='图纸.掉落',lines=function()return{{current}}end,it={99}},
            {text='图纸.商人',lines=function()return{{'vendor'}}end,act=function()clicked=true end}}
          PD.PaintRecipeSources(row,segments)
          assert(#row.__recipeSources==2)
          local drop,vendor=row.__recipeSources[1],row.__recipeSources[2]
          assert(drop.text.shown and vendor.text.shown and drop.zone.shown and vendor.zone.shown)
          drop.zone.scripts.OnEnter(drop.zone);assert(GameTooltip.lines[1]=='first')
          current='updated'
          drop.zone.scripts.OnEnter(drop.zone);assert(GameTooltip.lines[1]=='updated')
          vendor.zone.scripts.OnClick(vendor.zone,'LeftButton');assert(clicked)
          drop.zone.scripts.OnClick(drop.zone,'LeftButton');assert(shiftZone==drop.zone)
          drop.zone.scripts.OnMouseWheel(drop.zone,1);assert(scrolled and pickerHidden)
          PD.PaintRecipeSources(row,{{text='图纸.商人',lines=function()return{{'new'}}end}})
          assert(row.__recipeSources[1]==drop and row.__recipeSources[2]==vendor)
          assert(drop.text.text=='图纸.商人' and not drop.zone.__act and not drop.zone.__it)
          assert(not vendor.text.shown and vendor.text.text=='' and not vendor.zone.shown)
          assert(not vendor.zone.__tipLines and not vendor.zone.__act and not vendor.zone.__it)
          PD.ClearMatSegs(row)
          for _,part in ipairs(row.__recipeSources)do
            assert(not part.text.shown and part.text.text=='' and not part.zone.shown)
            assert(not part.zone.__tipLines and not part.zone.__act and not part.zone.__it and not part.zone.__tipExtra)
          end
        ''')


if __name__ == '__main__':
    unittest.main()
