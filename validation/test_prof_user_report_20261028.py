"""Reported profession UI regressions against actual Lua entry points.

Widget measurements are mocked. This is not a claim about in-game pixels.
"""
import unittest
import test_prof_ui_fusion as ui
import test_prof_execution_fusion as execution

ROOT = ui.ROOT


class ProfessionReportUITests(unittest.TestCase):
    setUp = ui.ProfessionUIFusionTests.setUp
    boot = ui.ProfessionUIFusionTests.boot

    def test_shopping_and_route_never_insert_the_unrelated_trainer_paragraph(self):
        self.lua.execute('''
          PD.RowsRankReminder=function()error('unexpected trainer paragraph')end
          PD.RowsAutoShop=function()end
          for _,page in ipairs({'route','shop'})do
            PD.autoPage=page;PD.RowsLeveling({})
            local opts=ns.ProfRouteAuto.OptionsFor('alchemy',1);opts.target=3
            finish('alchemy',opts);PD.RowsLeveling({})
          end
        ''')

    def test_maxed_cooking_explains_why_there_are_no_upgrade_steps(self):
        self.lua.execute('''
          PD.Wrap=function(text)return {text}end
          ns.ProfLeveling.cooking={steps={}};skills.cooking={cur=300,max=300}
          PD.cur='cooking';PD.autoPage='route'
          local p={planVersion=2,status='complete',targetReached=true,alreadyAtTarget=true,
            start=300,target=300,steps={},mats={},feasible=true,total=0,completeCost=true,
            inputModelOptimal=true,catalogueCoverageComplete=false}
          ns.ProfRouteAuto.Get=function()return p end
          local rows={};PD.RowsLeveling(rows)
          assert(PD.PlanStatusText(p)==format(ns.L['已达到目标等级 %d，无需继续升级。'],300))
          assert(PD.lvSummary.alreadyAtTarget and #rows>=2)
          assert(not PD.PlanNoUpgradeNeeded({status='complete',targetReached=true,start=300,target=300,
            steps={{300,300,1,1}}}),'required tool work was hidden')
        ''')

    def test_trainer_pattern_reference_does_not_create_a_world_drop_purchase_badge(self):
        self.load((ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          PD=ns.ProfModule;PD.cur='alchemy'
          PD.DropLines=function()return {}end;PD.VendorLines=function()return {}end
          PD.FormulaAuctionLine=function()end
          local raw={2334,2458,1,'',nil,nil,50,80,100,120,false,{}, {2554}, {drops={{npc='Reference'}}}}
          local trainer={spell=2334,profession='alchemy',formula=2554,learnSource='trainer'}
          local card=PD.CardOf(raw,nil,trainer,'alchemy')
          assert(card.kind=='trainer' and card.fid==nil)
          local actualPattern={spell=999,profession='alchemy',formula=400,learnSource='formula',source=raw[14]}
          card=PD.CardOf(raw,nil,actualPattern,'alchemy')
          assert(card.kind=='drop' and card.fid==400,'a genuine pattern source disappeared')
        ''')

    def test_current_material_warning_only_describes_an_active_followed_step(self):
        self.lua.execute('''
          PD.Wrap=function(text)return {text}end;PD.RowsRecoveryDetail=function()end
          PD.shopGroup=false
          local active=false
          ns.ProfFollow={Following=function()return active end,SupplementNeeds=function()
            return {items={{id=765,lack=9}},basis='bags'} end}
          local function warning(rows)
            for _,row in ipairs(rows)do
              if row.text and row.text:find('Item765',1,true)then return row.text end
            end
          end
          local data={mode='auto',mats={},total=0,priced=true,feasible=true}
          local rows={};PD.RowsAutoShop(rows,data);assert(not warning(rows))
          active=true;rows={};PD.RowsAutoShop(rows,data)
          assert(warning(rows)==format(ns.L['当前制作步骤背包还缺：%s'],'Item765 ×9'))
          ns.ProfFollow.SupplementNeeds=function()end
          rows={};PD.RowsAutoShop(rows,data);assert(not warning(rows))
        ''')

    def test_mixed_and_unknown_vendor_stock_keep_distinct_labels(self):
        self.lua.execute('''
          PD.Wrap=function(text)return {text}end
          PD.DropEntries=function()return {}end;PD.DropLines=function()return {{'drop-reference'}}end
          PD.VendorEntries=function()return {}end;PD.VendorLines=function()return {}end
          local mixed={unlimited=true,limited=true}
          assert(PD.FormulaStockChip(mixed).text==ns.L['不限量+限量'])
          assert(PD.FormulaStockText(mixed)==ns.L['商人库存：固定售卖及限量刷新'])
          local entry={id=400,count=1,cost=20,source='vendor',stockUnknown=true,
            sources={drops={{npc='Reference'}}},vendorOffers={{npcID=1,price=20,quantity=1,
              unlimited=false,stockUnknown=true,stockStatus='unknown'}}}
          local rows={};PD.RowsFormulaShop(rows,{formulas={entry}})
          local formula
          for _,row in ipairs(rows)do if row.it and row.it[1]==400 then formula=row end end
          assert(formula and entry.sources.vendors==nil,'render mutated the frozen acquisition data')
          local drop,unknown=false,false
          for _,line in ipairs(formula.lines)do
            if line[1]=='drop-reference'then drop=true end
            if line[1]:find(ns.L['库存性质尚未核实'],1,true)then unknown=true end
            assert(not line[1]:find(ns.L['限量刷新'],1,true),'unknown was called limited')
          end
          assert(drop and unknown)
        ''')

    def test_genuine_unlearned_formula_remains_in_both_shop_layouts(self):
        self.lua.execute('''
          PD.Wrap=function(text)return {text}end;PD.RowsRecoveryDetail=function()end
          PD.DropEntries=function()return {}end;PD.DropLines=function()return {}end
          PD.VendorEntries=function()return {}end;PD.VendorLines=function()return {}end
          local data={mode='auto',total=50,priced=true,feasible=true,mats={},formulasTotal=50,
            formulas={{id=400,count=1,cost=50,source='vendor',unlimited=true,
              vendorOffers={{npcID=1,price=50,quantity=1,unlimited=true}}}}}
          for _,group in ipairs({false,true})do
            PD.shopGroup=group;local rows={};PD.RowsAutoShop(rows,data)
            local found=false
            for _,row in ipairs(rows)do if row.it and row.it[1]==400 then found=true end end
            assert(found,'formula hidden by shopping layout')
          end
        ''')

    def test_grouped_materials_preserve_vendor_stock_information(self):
        self.lua.execute('''
          PD.Wrap=function(text)return {text}end
          local data={mats={{id=3371,count=5,unit=3,cost=15,npcID=1,source='vendor',vendor=true,
            bundleSize=5,unlimited=true}}}
          local groups=PD.TripGroups(data)
          assert(groups[1].items[1].unlimited and groups[1].items[1].bundleSize==5)
          local rows={};PD.PushTripGroups(rows,data)
          local found=false
          for _,row in ipairs(rows)do
            if row.it and row.it[1]==3371 then
              for _,line in ipairs(row.lines)do
                if line[1]==ns.L['商人库存：固定售卖（不限量）']then found=true end
              end
            end
          end
          assert(found)
        ''')

    def test_new_status_messages_are_available_in_all_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                self.boot(locale)
                self.lua.execute('''
                  for _,key in ipairs({'已达到目标等级 %d，无需继续升级。',
                    '如需查看全程路线，可在设置中关闭「从当前技能开始计算」。',
                    '当前制作步骤背包还缺：%s','采购规则已更新，请重新计算路线。'})do
                    assert(rawget(ns.L,key),key)
                  end
                ''')


class ProfessionReportBagTests(unittest.TestCase):
    setUp=execution.ExecutionFusionTests.setUp
    load=execution.ExecutionFusionTests.load
    load_follow=execution.ExecutionFusionTests.load_follow

    def test_sufficient_market_supply_does_not_count_as_carried_materials(self):
        self.load_follow()
        self.lua.execute('''
          ns.AuctionBridge={GetAuctionSupply=function()return {quantity=1000}end}
          C_Item.GetItemCount=function(id,bank)assert(bank==false);return bag[id] or 0 end
          bag[20]=0;local need=pf.SupplementNeeds('alchemy')
          assert(need and need.basis=='bags' and need.items[1].lack==3)
          bag[20]=3;assert(pf.SupplementNeeds('alchemy')==nil)
        ''')

    def test_unreadable_item_counts_do_not_create_a_false_missing_warning(self):
        self.load_follow()
        self.lua.execute('''
          C_Item.GetItemCount=function()error('not readable')end;GetItemCount=nil
          assert(pf.SupplementNeeds('alchemy')==nil)
        ''')


if __name__=='__main__':unittest.main()
