"""Exercise profession UI data adapters without rendering a game window."""
import os
from pathlib import Path
import sys
import unittest

for path in (Path(os.environ.get("TEMP", "/tmp")) / "df-lua-runtime",
             Path.home() / "AppData/Local/Temp/df-lua-runtime"):
    sys.path.insert(0, str(path))
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class ProfessionUIRegressions(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(r'''
          ns={LoadForeverPages=true,L=setmetatable({}, {__index=function(_,k) return k end})}
          PD={cur='alchemy'}; L=ns.L; format=string.format; C_GREY={.5,.5,.5}
          RA={Available=function() return false end,
              MatListCost=function() return 0,1 end,
              MoneyStr=tostring}
          DG={ItemName=function(id) return 'Item'..tostring(id) end}
          LV={}; data={rows={}}; RGet=function() return data end
          SpellIcon=function() return 1 end
          PD.ItemName=DG.ItemName
          PD.MatText=function(m) return m and #m>0 and 'materials' or '' end
          PD.MatCol=function(m) return PD.MatText(m),0,0,{} end
          PD.AhPct=function() end
          PD.VendorListOf=function() return {} end
          PD.KitSub=function(s) return s end
          PD.PriceTipLines=function() return {} end
          PD.TierText=function() return '' end
          PD.Setting=function() return false end
          PushText=function(rows,text) rows[#rows+1]={text=text} end
          UnitName=function() return 'Test' end
          GetRealmName=function() return 'Realm' end
        ''')
        self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")(
            str(ROOT / "Core/ProfEconomy.lua"))
        source = (ROOT / "Core/ProfessionUI.lua").read_text(encoding="utf-8-sig")
        for start, end in (
            ("function PD.AuctionatorStatusText()", "PD.CARD_INSET ="),
            ("function PD.RecipeData(", "function PD.EnchantSpec("),
            ("function PD.EnchantSpec(", "-- ---- 配方搜索"),
            ("function PD.RecipeSpec(", "function PD.FavorSpec("),
            ("function PD.StepRecipe(", "function PD.StepName("),
            ("function PD.RawHit(", "-- ★ 本页的「有效分类过滤」"),
            ("function PD.RoutePairContext()", "function PD.PlanDiagnostics("),
            ("function PD.PlanDiagnostics(", "function PD.RowsLeveling("),
            ("function PD.PlanStatusText(", "function PD.CopyPlanSummary("),
            ("function PD.ShopImport(", "-- ── 升级页签工具行"),
            ("function PD.LevelTool(", "function PD.RowsSettings("),
            ("function PD.RowsSettings(", "function PD.PlaceSettingsToggles("),
        ):
            a = source.index(start)
            self.lua.execute(source[a:source.index(end, a + len(start))])

    def test_unlearned_catalogue_materials_remain_visible_and_searchable(self):
        self.lua.execute(r'''
          local row={101,10,2,'','','',1,10,15,20,false,{{11,3}}}
          local spec=PD.RecipeSpec(row)
          assert(spec._mats[1][1]==11 and spec._mats[1][2]==3)
          assert(spec.mats~='客户端数据待读取')
          assert(spec.right2:find('参考资料',1,true))
          assert(PD.RawHit(row,'item11'))
          local crafted={101,10,2,1,10,15,20,{{11,3}}}
          assert(PD.CraftedSpec(crafted)._mats[1][1]==11)
          local enchant={'name','display','slot','',1,10,15,20,{{11,3}},nil,false,nil,nil,102,12}
          assert(PD.EnchantSpec(enchant)._mats[1][1]==11)
        ''')

    def test_unlearned_pair_selector_has_no_default_and_saves_explicit_choice(self):
        self.lua.execute(r'''
          D={pro={alchemy={name='Alchemy'},mining={name='Mining'},engineering={name='Engineering'}}}
          PD.ROW_H=34
          PD.Setting=function(key)return key=='autoSecondaryLeveling' end
          PD.ProfLearned=function()return {mining={cur=125,max=150},engineering={cur=60,max=75}} end
          local renders,recalculations=0,0
          PD.RequestRender=function()renders=renders+1 end
          RA.Recalculate=function()recalculations=recalculations+1 end
          PushGap=function()end
          local context=PD.RoutePairContext()
          assert(context.unlearned and context.requiresPartner and not context.partnerValid)
          local rows={};PD.RowsRoutePartner(rows,context)
          assert(rows[1].text=='请选择搭配的主专业')
          local mining,tailoring
          for _,row in ipairs(rows) do
            assert(row.text~='Alchemy','target profession was selectable as its own partner')
            assert(row.right~='已选择','selector chose a default partner')
            if row.text=='Mining' then mining=row end
            if row.text=='tailoring' then tailoring=row end
          end
          assert(mining and mining.sub=='已学 · 技能 125/150')
          assert(tailoring and tailoring.sub=='未学 · 从 1 开始')
          mining.act()
          assert(ns.ProfEconomy.GetRoutePartner('alchemy')=='mining')
          assert(renders==1 and recalculations==0,'choosing a partner recalculated automatically')
          rows={};PD.RowsRoutePartner(rows,PD.RoutePairContext())
          assert(rows[1].text=='搭配专业：Mining' and rows[1].right=='点击更改')
        ''')

    def test_unlearned_pair_selector_explains_learned_only_exception(self):
        self.lua.execute(r'''
          PD.Setting=function(key)return key=='autoLearnedOnly' end
          local rows={};PD.RowsRoutePartner(rows,{unlearned=true,requiresPartner=false})
          assert(#rows==1 and rows[1].text=='此专业尚未学习，已忽略「仅使用已学习的配方」。')
          rows={};PD.RowsRoutePartner(rows,{unlearned=false,requiresPartner=false})
          assert(#rows==0,'learned profession was advertised as ignoring learned-only')
        ''')

    def test_pair_selector_toolbar_opens_without_recalculating(self):
        self.lua.execute(r'''
          PD.Setting=function(key)return key=='autoRoute' or key=='autoSecondaryLeveling' end
          PD.ProfLearned=function()return {} end
          PD.RequestRender=function()end
          local recalculations=0;RA.Recalculate=function()recalculations=recalculations+1 end
          local buttons,click=PD.LevelTool();local found=false
          for _,button in ipairs(buttons) do if button.key=='partner' then found=true end end
          assert(found)
          PD.exclusionsOpen=true;click('partner')
          assert(PD.partnerPicker=='alchemy' and not PD.exclusionsOpen and recalculations==0)
          click('partner');assert(not PD.partnerPicker and recalculations==0)
        ''')

    def test_reference_steps_with_pending_prices_never_display_free_or_optimal(self):
        self.lua.execute('''
          local plan={steps={{1,2,101,1}},pricePending=true,referenceRoute=true,
            completeCost=false,total=0,status='incomplete',expanded=1}
          assert(PD.PlanStatusText(plan)=='参考路线已生成；材料价格待补全')
          assert(PD.PlanCostText(plan)=='材料价格待补全')
          plan.total=21;assert(PD.PlanCostText(plan)=='≥21')
          assert(PD.PlanProgressText(plan)=='已比较 1 个状态')
          local r={variableOutput=true,count=3,outputBasis='reference'}
          assert(PD.RecipeOutputText(r)=='随机产量范围暂未读取；按已有资料每次 3 件估算。')
        ''')

    def test_client_fields_override_catalogue_independently(self):
        self.lua.execute(r'''
          local row={101,10,2,'','','',1,10,15,20,false,{{11,3}}}
          ns.ProfRecipeRuntime={[101]={mats={{12,4}},item=13}}
          local spec=PD.RecipeSpec(row)
          assert(spec._mats[1][1]==12 and spec.row[2]==13 and spec.row[3]==2)
          assert(spec.right2:find('客户端与参考资料',1,true))
        ''')

    def test_malformed_catalogue_can_still_use_client_materials(self):
        self.lua.execute(r'''
          ns.ProfRecipeRuntime={[101]={mats={{12,4}},item=13,count=2}}
          local row={101,10,1}
          assert(PD.RecipeData(row,'rows').mats[1][1]==12)
        ''')

    def test_only_positive_client_absence_hides_reference_record(self):
        self.lua.execute(r'''
          assert(PD.RecipeVisible(101))
          ns.ProfRecipeRuntime={[101]={available=false}}
          assert(not PD.RecipeVisible(101))
          ns.ProfRecipeRuntime[101]={learned=false}
          assert(PD.RecipeVisible(101))
        ''')

    def test_step_uses_published_snapshot_instead_of_changed_catalogue(self):
        self.lua.execute(r'''
          data.rows={{101,10,1,'','','',1,10,15,20,false,{{11,3}}}}
          local r=PD.StepRecipe({1,2,101,1,recipe={spell=101,item=13,count=2,mats={{12,4}},learn=1}})
          assert(r.mats[1][1]==12 and r.makes==13)
          local fallback=PD.StepRecipe({1,2,101,1})
          assert(fallback[12][1][1]==11)
        ''')

    def test_step_range_uses_actual_batched_execution_range(self):
        self.lua.execute(r'''
          assert(PD.StepRange({60,75,101,15})=='60 – 75')
          local step={60,95,101,13,segments={
            {from=60,to=65,count=5},{from=65,to=68,count=3},{from=90,to=95,count=5}}}
          assert(PD.StepRange(step)=='60 – 95')
        ''')

    def test_execution_roles_distinguish_leveling_and_intermediate_products(self):
        self.lua.execute(r'''
          assert(PD.StepRole({1,2,101,1,role='level'})=='升级')
          assert(PD.StepRole({1,2,101,1,role='material'})=='中间产物')
          assert(PD.StepRole({1,2,101,1,role='both'})=='升级&中间产物')
          assert(PD.StepRole({1,2,101,1,tags={leveling=true,material=true}})=='升级&中间产物')
          assert(PD.StepRole({140,155,0,0,checkpoint=true})=='实地采矿')
          assert(PD.PurchaseSource({source='vendor'})=='NPC购买')
          assert(PD.PurchaseSource({vendor=true,source='ah'})=='NPC购买')
          assert(PD.PurchaseSource({source='ah'})=='拍卖行')
        ''')

    def test_header_renders_exactly_five_requested_columns(self):
        source = (ROOT / "Core/ProfessionUI.lua").read_text(encoding="utf-8-sig")
        a = source.index('    if spec.kind == "lvhead" then')
        b = source.index('    -- 2026-10-11 板条箱/工匠文书页左列表头', a)
        self.lua.execute("BindRouteHeader=function(r,spec) " + source[a:b] + " end")
        self.lua.execute(r'''
          local function text() return setmetatable({}, {__index=function(_,key)
            if key=='SetText' then return function(self,value) self.text=value end end
            return function() end
          end}) end
          Unpack=unpack; PD.HideSkillBar=function() end; PD.PaintCard=function() end
          PD.LV_STEP_X=6; PD.LV_RNG_X=50; PD.LV_NAME_X=180
          PD.LV_COUNT_R=120; PD.LV_COST_R=6
          local row={a=text(),b=text(),c=text(),c2=text(),d=text(),e=text(),f=text()}
          BindRouteHeader(row,{kind='lvhead'})
          assert(row.a.text=='步骤' and row.d.text=='等级范围' and row.e.text=='配方')
          assert(row.c.text=='制作次数' and row.c2.text=='成本')
          assert(row.b.text=='' and row.f.text=='')
        ''')

    def test_provider_npc_quotes_keep_metadata_without_removed_static_price_hints(self):
        source = (ROOT / "Core/ProfessionUI.lua").read_text(encoding="utf-8-sig")
        a = source.index('function PD.CopyPlanSummary(')
        b = source.index('function PD.StepRecipe(', a)
        self.lua.execute(source[a:b])
        a = source.index('function PD.RowsAutoShop(')
        b = source.index('function PD.ShopImport(', a)
        self.lua.execute(source[a:b])
        self.lua.execute(r'''
          PD.COL_LW=600; PD.SEC_GAP=8; PD.SEC_PAD=4
          PD.Fit=function(text) return text end
          PushHead=function(rows,text,col) rows[#rows+1]={kind='head',text=text,col=col} end
          PushGap=function(rows,h,col) rows[#rows+1]={kind='gap',h=h,col=col} end
          CountUnpriced=function() return 0 end
          local data={planVersion=2,total=18,feasible=true,status='complete',referencePrices=true,
            vendorTotal=18,ahTotal=0,mats={{id=11,count=5,cost=18,unit=18/5,
              vendor=true,source='vendor',npcID=1313,bundleSize=5,reference=true,verifiedAt='2026-10-18'}}}
          local rows={}; PD.RowsAutoShop(rows,data)
          local sawMaterial,sawSummary=false,false
          for _,row in ipairs(rows) do
            if row.it then
              sawMaterial=true; assert(row.tag.text=='NPC购买')
              assert(row.right=='×5 · 3.6' and row.right2=='18')
              local hint,verified=false,false
              for _,line in ipairs(row.lines) do
                if line[1]=='插件内置NPC报价（实际价格可能因声望而异）' then hint=true end
                if line[1]=='报价核验：2026-10-18' then verified=true end
              end
              assert(not hint and verified)
            end
            if row.text=='NPC购买价格使用插件内置数据。' then sawSummary=true end
          end
          assert(sawMaterial and not sawSummary)
          assert(PD.PurchasePriceHint==nil)
          D={pro={alchemy={name='Alchemy'}}}
          ns.AuctionBridge={DoImport=function(_,items) imported=items end}
          data.mats[2]={id=12,count=2,source='ah'}
          PD.ShopImport(data)
          assert(#imported==1 and imported[1].name=='Item12')
          PD.CopyPlanSummary(data)
          assert(PD.lvSummary.referencePrices)
          data.mats={{id=11,count=2,cost=0,unit=0,vendor=true,source='vendor',unpriced=true}}
          rows={}; PD.RowsAutoShop(rows,data)
          for _,row in ipairs(rows) do if row.it then
            local unknown=false
            for _,line in ipairs(row.lines) do
              assert(line[1]~='价格未知（Auctionator 无记录）')
              if line[1]=='NPC购买价格尚未配置。' then unknown=true end
            end
            assert(unknown)
          end end
          data.planVersion=nil; data.mode='fixed'; data.priced=true
          rows={}; PD.RowsAutoShop(rows,data)
          local reference=false
          for _,row in ipairs(rows) do
            assert(row.text~='价格快照年龄未知（Auctionator）')
            if row.text=='NPC购买价格使用插件内置数据。' then reference=true end
          end
          assert(not reference,'removed static-price summary is still advertised')
          data.mats[2]={id=12,count=1,cost=0,unit=0,source='ah'}
          data.ahTotal=0; rows={}; PD.RowsAutoShop(rows,data)
          local auctionAge=false
          for _,row in ipairs(rows) do
            if row.text=='价格快照年龄未知（Auctionator）' then auctionAge=true end
          end
          assert(auctionAge,'zero-cost auction entry was misclassified as NPC-only')
        ''')

    def test_route_rows_preserve_execution_order_and_actual_batch_costs(self):
        source = (ROOT / "Core/ProfessionUI.lua").read_text(encoding="utf-8-sig")
        a = source.index('function PD.RowsLeveling(')
        b = source.index('function PD.RowsAutoShop(', a)
        self.lua.execute(source[a:b])
        self.lua.execute(r'''
          PD.cur='alchemy'; LV.alchemy={steps={}}
          D={pro={alchemy={name='Alchemy'},mining={name='Mining'}}}
          PD.LvTarget=function() return 75 end
          PD.ProfLearned=function() return {alchemy={cur=60,max=75},mining={cur=1,max=75}} end
          PD.Setting=function(key) return key=='autoRoute' or key=='autoFromCurrent' end
          PD.SettingRaw=function() return 'cheapest' end
          PD.StepName=function(st) return 'Spell'..st[3] end
          PD.CopyPlanSummary=function() end
          PD.TextW=function(text) return #text*6 end
          PD.Fit=function(text) return text end
          PD.LevelSrc=function() return nil end
          PD.RIGHT_W=900; PD.LIST_PAD=8; PD.LV_FS=13; PD.LV_STEP_X=6
          PD.LV_COL_GAP=16; PD.CARD_PAD=3; PD.TBL_ICON=28
          PD.TBL_RNG_GAP=12; PD.TBL_NAME_GAP=8; PD.TBL_MAT_RPAD=6; PD.TBL_H=42
          PushHead=function(rows,text) rows[#rows+1]={kind='head',text=text} end
          PushGap=function(rows) rows[#rows+1]={kind='gap'} end
          CountUnpriced=function() return 0 end
          local rec={spell=101,item=20,count=1,mats={{10,1}},learn=1,yellow=100,green=120,grey=130}
          local plan={planVersion=2,feasible=true,priced=true,scheme='cheapest',start=60,
            target=75,status='complete',total=300,steps={
              {1,5,101,4,stepIndex=1,profession='mining',role='both',recipe=rec,cost=100},
              {60,75,102,15,stepIndex=2,profession='alchemy',role='level',recipe=rec,cost=200}}}
          RA.Get=function() return plan end
          local rows={}; PD.RowsLeveling(rows)
          local actual={}; for _,row in ipairs(rows) do if row.lvstep then actual[#actual+1]=row end end
          assert(#actual==2 and actual[1].stepIndex==1 and actual[2].stepIndex==2)
          assert(actual[1].rng=='1 – 5' and actual[2].rng=='60 – 75')
          assert(actual[1].card.text=='升级&中间产物' and actual[2].card.text=='升级')
          assert(actual[1].cost=='100' and actual[2].cost=='200')
          assert(actual[1].unit==nil and actual[1].tot==nil and actual[1].blocks==nil)
        ''')

    def test_shop_import_includes_ah_formulas_and_ignores_npc_and_nonpurchase_fees(self):
        self.lua.execute(r'''
          D={pro={alchemy={name='Alchemy'}}}
          ns.AuctionBridge={DoImport=function(_,items) imported=items end}
          PD.ShopImport({planVersion=2,mats={{id=10,count=3,source='ah'},
             {id=11,count=2,source='vendor',vendor=true}},
             formulas={{id=12,count=1,source='ah'}},trainingTotal=100,toolsTotal=200})
          assert(#imported==2 and imported[1].name=='Item10' and imported[1].need==3)
          assert(imported[2].name=='Item12' and imported[2].need==1)
        ''')

    def test_old_shop_callback_cannot_export_after_partner_selection_changes(self):
        self.lua.execute(r'''
          D={pro={alchemy={name='Alchemy'}}}
          local imports=0
          ns.AuctionBridge={DoImport=function(_,items)
            imports=imports+1
            assert(#items==1 and items[1].name=='Item10' and items[1].need==3)
          end}
          local context={unlearned=true,requiresPartner=true,partnerValid=true,partner='mining'}
          PD.RoutePairContext=function()return context end
          local old={planVersion=2,professionPolicy=1,targetUnlearned=true,secondaryProfession='mining',
            feasible=true,mats={{id=10,count=3,source='ah'}}}
          local callback=function()PD.ShopImport(old)end
          callback();assert(imports==1,'matching current pair could not import')
          context={unlearned=true,requiresPartner=true,partnerValid=true,partner='tailoring'}
          callback();assert(imports==1,'old shopping callback exported a different profession pair')
          context={unlearned=true,requiresPartner=true,partnerValid=false}
          callback();assert(imports==1,'shopping callback exported without required partner selection')
          context={unlearned=true,requiresPartner=false,partnerValid=false}
          callback();assert(imports==1,'old joint-upgrade shopping callback exported after joint upgrade was disabled')
        ''')

    def test_route_settings_no_longer_offer_formula_cost_filter(self):
        self.lua.execute(r'''
          PushHead=function() end; PushGap=function() end
          PD.SettingRaw=function() return 'cheapest' end
          local rows={}; PD.RowsSettings(rows)
          local learned=false
          for _,row in ipairs(rows) do
            assert(row.togKey~='autoNoFormula')
            if row.togKey=='autoLearnedOnly' then learned=true end
          end
          assert(learned)
        ''')

    def test_finished_search_does_not_offer_redundant_continue_button(self):
        self.lua.execute(r'''
          PD.Setting=function() return true end
          PD.autoSnapshotSlug='alchemy'; PD.autoSnapshot={status='paused'}
          local buttons=PD.LevelTool()
          for _,button in ipairs(buttons) do
            assert(button.key~='continue_search')
          end
          assert(PD.PlanStatusText(PD.autoSnapshot)=='优化已停止')
          PD.autoSnapshot.status='searching'
          buttons=PD.LevelTool(); local stop=false
          for _,button in ipairs(buttons) do if button.key=='stop_search' then stop=true end end
          assert(stop)
        ''')

    def test_recalculate_is_explicit_and_switching_views_only_redraws(self):
        self.lua.execute(r'''
          local recalcs, invalidates, applies=0,0,0
          PD.Setting=function() return true end
          PD.ProfLearned=function() return {alchemy={cur=60}} end
          PD.RequestRender=function() end
          ns.PlaySound=function() end
          ns.ProfEconomy.ApplyPolicies=function(slug) assert(slug=='alchemy'); applies=applies+1 end
          RA.Invalidate=function() invalidates=invalidates+1 end
          RA.OptionsFor=function(slug,current) return {slug=slug,start=current} end
          RA.Recalculate=function(slug,opts)
            assert(slug=='alchemy' and opts.start==60); recalcs=recalcs+1
          end
          local _,click=PD.LevelTool()
          click('page_shop'); click('page_route')
          assert(recalcs==0 and invalidates==0 and applies==0)
          click('recalc')
          assert(recalcs==1 and applies==1 and invalidates==0)
          assert(PD.PlanCacheText({stale=true}):find('点击重新计算',1,true))
          assert(PD.PlanCacheText({cached=true})==nil)
        ''')

    def test_search_progress_shows_comparisons_and_actual_savings(self):
        self.lua.execute(r'''
          assert(PD.PlanProgressText({})==nil)
          assert(PD.PlanProgressText({expanded=0,status='incomplete'})==nil)
          local text=PD.PlanProgressText({expanded=42,initialTotal=100,total=80})
          assert(text=='已比较 42 个状态；较初始方案节省 20')
          text=PD.PlanProgressText({expanded=100,initialTotal=80,total=80,savings=0})
          assert(text=='已比较 100 个状态；较初始方案节省 0')
        ''')

    def test_frozen_execution_uses_live_search_diagnostics_and_button_status(self):
        source = (ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        start = source.index('function PD.CopyPlanSummary(')
        self.lua.execute(source[start:source.index('function PD.StepRecipe(', start)])
        self.lua.execute(r'''
          PD.Setting=function()return true end
          PD.autoSnapshotSlug='alchemy'
          local frozen={planVersion=2,status='complete',expanded=3,total=100,optimal=true,
            searchState={status='searching',expanded=42,bestTotal=80,running=true}}
          PD.autoSnapshot=frozen
          assert(PD.PlanStatusText(frozen)=='后台优化中')
          assert(PD.PlanProgressText(frozen)=='已比较 42 个状态；后台当前最低支出 80')
          local buttons=PD.LevelTool();local stop=false
          for _,b in ipairs(buttons)do if b.key=='stop_search'then stop=true end end
          assert(stop)
          frozen.status='searching';frozen.searchState.status='complete';frozen.searchState.running=false
          buttons=PD.LevelTool()
          for _,b in ipairs(buttons)do assert(b.key~='stop_search')end
          assert(PD.PlanStatusText(frozen)=='后台优化已结束，继续执行已保存计划。')
          PD.lvSummary={total=100};PD.CopyPlanSummary(frozen)
          assert(PD.lvSummary.searchState==frozen.searchState and PD.lvSummary.total==100)
          frozen.searchState.status='interrupted'
          assert(PD.PlanStatusText(frozen)=='优化已中断；执行计划已保存，可重新计算。')
          assert(frozen.expanded==3 and frozen.total==100)
        ''')

    def test_auction_quantity_snapshots_distinguish_partial_zero_unknown_and_npc(self):
        self.lua.execute(r'''
          local e={source='ah',count=3,availableCount=5,supplyObserved=true,supplyComplete=true}
          assert(PD.AuctionSupplyText(e)=='拍卖行数量快照：5 件；本路线购买 3 件。')
          e.supplyComplete=false
          assert(PD.AuctionSupplyText(e)=='拍卖行已读取：5 件（结果未全部读取）；本路线购买 3 件。')
          e.availableCount=0
          assert(PD.AuctionSupplyText(e)=='拍卖行已读取数量不足：可购 0 件，需要 3 件。')
          e.availableCount=nil;e.supplyObserved=false
          assert(PD.AuctionSupplyText(e)=='拍卖行可购数量未知，当前仅按价格估算。')
          e.vendor=true;assert(PD.AuctionSupplyText(e)==nil)
          assert(PD.AuctionSupplyText({source='ah',count=3})==nil,'old saved entry invented stock')
        ''')

    def test_unread_auction_quantity_does_not_make_known_prices_incomplete(self):
        self.lua.execute(r'''
          local plan={auctionSupplyUnknown=2,total=17,completeCost=true}
          assert(PD.PlanCostText(plan)=='17')
          assert(PD.PlanSupplyText(plan)=='有 2 种拍卖行物品数量未知，暂按价格估算；请在拍卖师处执行一次完整扫描后重新计算。')
          assert(PD.PlanSupplyText({auctionSupplyUnknown=0})==nil)
          assert(PD.PlanSupplyText({})==nil)
        ''')

    def test_optimal_label_requires_confirmed_auction_quantity_when_metadata_exists(self):
        self.lua.execute(r'''
          local plan={optimal=true,status='complete',supplyComplete=false}
          assert(PD.PlanStatusText(plan)=='当前找到的最低支出')
          plan.supplyComplete=true
          assert(PD.PlanStatusText(plan)=='当前价格与期望模型内最优')
          plan.supplyComplete=nil
          assert(PD.PlanStatusText(plan)=='当前价格与期望模型内最优')
        ''')

    def test_auction_supply_failures_only_show_if_the_chosen_route_is_blocked(self):
        self.lua.execute(r'''
          local limited={code='auctionSupplyLimited',item=10}
          ns.ProfEconomy.DiagnosticText=function(d)return d.code end
          local rows={}
          PD.PlanDiagnostics(rows,{feasible=true,steps={{60,75,101,15}},diagnostics={limited}})
          assert(#rows==0,'rejected supply bottleneck covered the alternative route')
          PD.PlanDiagnostics(rows,{feasible=true,partial=true,steps={{60,75,101,15}},
            diagnostics={limited},blockingDiagnostics={limited}})
          assert(#rows==1 and rows[1].text=='auctionSupplyLimited')
        ''')

    def test_search_diagnostics_are_grouped_and_bounded(self):
        self.lua.execute(r'''
          local d={}; for i=1,100 do d[#d+1]={code='excluded',spell=i} end
          d[#d+1]={code='materialUnavailable',item=10}
          local rows={}; PD.PlanDiagnostics(rows,{diagnostics=d})
          assert(#rows==2 and rows[1].text:find('材料',1,true))
          assert(rows[2].text:find('100',1,true))
          rows={}; PD.PlanDiagnostics(rows,{feasible=true,diagnostics=d})
          assert(#rows==1 and not rows[1].text:find('自定义',1,true))
          rows={}; d={}; for i=1,20 do d[#d+1]={code='cause'..i} end
          PD.PlanDiagnostics(rows,{diagnostics=d}); assert(#rows<=6)
        ''')

    def test_selected_route_does_not_display_rejected_candidate_failures(self):
        self.lua.execute(r'''
          local rows={}
          PD.PlanDiagnostics(rows,{feasible=true,steps={{60,75,101,15}},diagnostics={
            {code='materialUnavailable',item=10},{code='outputConflict',spell=102},
            {code='batchDependency',spell=103},{code='skillRequired',spell=104},
            {code='vendorPriceUnknown',detail=11}}})
          assert(#rows==1 and rows[1].text:find('NPC购买价格尚未配置',1,true))
        ''')

    def test_partial_route_only_reports_its_next_stage_blockers_once(self):
        self.lua.execute(r'''
          local rows={}
          local price={code='vendorPriceUnknown',item=11}
          local blocker={code='skillRequired',spell=104}
          PD.PlanDiagnostics(rows,{feasible=true,partial=true,steps={{60,75,101,15}},
            diagnostics={{code='materialUnavailable',item=10},price,blocker},
            blockingDiagnostics={blocker,{code='skillRequired',spell=104},price}})
          assert(#rows==2)
          assert(rows[1].text:find('NPC购买价格尚未配置',1,true))
          assert(rows[2].text:find('另一专业技能不足',1,true))
          for _,row in ipairs(rows) do assert(not row.text:find('同类',1,true)) end
        ''')

    def test_blocked_empty_route_prefers_explicit_blockers(self):
        self.lua.execute(r'''
          local rows={}
          PD.PlanDiagnostics(rows,{feasible=false,steps={},
            diagnostics={{code='materialUnavailable',item=10},{code='outputConflict',spell=102}},
            blockingDiagnostics={{code='levelGap'}}})
          assert(#rows==1 and rows[1].text:find('当前技能区间',1,true))
        ''')

    def test_saved_prefix_remains_displayable_after_a_later_failure(self):
        self.lua.execute(r'''
          assert(not PD.PlanHasSteps(nil))
          assert(not PD.PlanHasSteps({steps={}}))
          local plan={feasible=false,status='incomplete',steps={{60,75,101,15}}}
          assert(PD.PlanHasSteps(plan))
          assert(PD.PlanStatusText(plan):find('可先完成',1,true))
        ''')

    def test_variable_output_hint_uses_range_and_conservative_basis(self):
        self.lua.execute(r'''
          assert(PD.RecipeOutputText({count=2})==nil)
          assert(PD.RecipeOutputText({variableOutput=true,outputMin=0,outputMax=3})==nil)
          local r={count=1,variableOutput=true,outputMin=1,outputMax=3}
          local text=PD.RecipeOutputText(r)
          assert(text:find('1–3',1,true) and text:find('最低产量',1,true))
          local lines=PD.RecipeSourceLines({},r)
          assert(lines[#lines][1]==text)
          local recipe=PD.StepRecipe({recipe=r})
          assert(PD.RecipeOutputText(recipe)==text)
        ''')

    def test_partial_status_never_implies_whole_target_was_planned(self):
        self.lua.execute(r'''
          local status=PD.PlanStatusText({partial=true,plannedTo=75,target=300,status='paused'})
          assert(status:find('75',1,true) and status:find('后续',1,true))
        ''')

    def test_auctionator_loading_and_missing_quotes_are_distinct(self):
        self.lua.execute(r'''
          ns.AuctionBridge={Status=function() return {state='loading',installed=true} end}
          assert(PD.AuctionatorStatusText()=='Auctionator 正在初始化')
          ns.AuctionBridge.Status=function() return {state='ready',installed=true} end
          assert(PD.AuctionatorStatusText():find('价格',1,true))
          ns.AuctionBridge.Status=function() return {state='missing'} end
          assert(PD.AuctionatorStatusText()=='未安装 Auctionator')
        ''')


if __name__ == "__main__":
    unittest.main()
