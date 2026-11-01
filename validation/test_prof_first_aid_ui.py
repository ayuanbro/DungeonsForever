"""First-aid reference rows and material quotes do not invent recipe details."""
import unittest
from test_prof_recipe_data_first_aid import runtime,add_route_and_execution,ROOT,load,FIXED_SPELLS
from test_prof_ui_fusion import UI_MOCKS


class FirstAidUITests(unittest.TestCase):
    def boot(self,locale='zhCN',missing=True):
        self.lua=runtime(locale,missing=missing)
        add_route_and_execution(self.lua)
        self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
            (ROOT/'Core/Data/Data_ProfTrainers.lua').read_text(encoding='utf-8-sig'))
        for language in (['zhCN'] if locale=='zhCN' else ['zhCN',locale]):
            self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                (ROOT/'Locales'/(language+'.lua')).read_text(encoding='utf-8-sig'))
        self.lua.execute('savedNative={ns.ProfData,ns.ProfRecipes,ns.ProfLeveling}')
        self.lua.execute(UI_MOCKS)
        self.lua.execute('''
          ns.ProfData,ns.ProfRecipes,ns.ProfLeveling=unpack(savedNative)
          GetSpellInfo=function(id)return 'Spell'..id end
          Auctionator.API.v1.GetAuctionAgeByItemID=function()return 0 end
        ''')
        load(self.lua,'ProfessionUI')
        self.lua.execute('''
          PD=ns.ProfModule;PD.cur='first-aid';PD.tab='leveling'
          PD.ProfLearned=function()return {['first-aid']={cur=1,max=300}}end
          PD.Wrap=function(t)return {t}end;PD.ScheduleSweep=function()end;PD.WindowShown=function()return true end
          PD.RequestRender=function()end;PD.Fit=function(t)return t end
          DungeonsForeverDB.prof.lvTarget={['first-aid']=300}
        ''')

    def setUp(self):self.boot()

    def test_reference_recipe_tab_has_fourteen_unique_rows_and_no_fabricated_materials(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                self.boot(locale)
                self.lua.execute('''
                  PD.tab='recipe';local rows={};PD.RowsRecipe(rows)
                  local tab=false;for _,key in ipairs(PD.TabsFor('first-aid'))do if key=='recipe'then tab=true end end
                  assert(tab,'reference recipe rows were not reachable from the profession tabs')
                  local count,seen=0,{}
                  for _,r in ipairs(rows)do if r.spell then
                    count=count+1;assert(not seen[r.spell]);seen[r.spell]=true
                    assert(r.right2==ns.L['配方资料待补全'] and r.costVal==nil and r.it==nil and r._mats==nil)
                  end end
                  assert(count==14 and seen[3275] and seen[1259342])
                  for _,r in ipairs(rows)do if r.spell==1244431 then
                    assert(r.right==string.format(ns.L['攻略区间 %d–%d'],55,80))
                  end end
                  assert(ns.ProfRecipes['first-aid']==nil and ns.ProfLeveling['first-aid'].rinfo==nil)
                  PD.searchQ='1259342';rows={};PD.RowsRecipe(rows)
                  count=0;for _,r in ipairs(rows)do if r.spell then count=count+1;assert(r.spell==1259342)end end
                  assert(count==1)
                ''')

    def test_full_guide_quotes_are_visible_without_making_the_route_executable(self):
        self.lua.execute('''
          local p=ns.ProfRouteAuto.FixedPlan('first-aid',{target=300})
          assert(p.referenceOnly and p.referenceShopping and p.referenceQuoted and p.referenceCostComplete)
          assert(not p.priced and p.feasible==false and p.completeCost==false and p.clientPending)
          local total=0;for _,r in ipairs(ns.ProfLeveling['first-aid'].shopping)do total=total+r[2]end
          assert(p.total==total and p.matTotal==total and #p.mats==14 and p.snapshotDays==0)
          local text=PD.PlanCostText(p)
          assert(text:find(ns.L['材料参考价'],1,true) and not text:find('≥',1,true))
          PD.lvSummary={};PD.CopyPlanSummary(p)
          assert(PD.PlanCostText(PD.lvSummary)==text and PD.lvSummary.referenceQuoted)
          assert(PD.SnapshotBadgeState(PD.lvSummary)=='recipe_reference')
          assert(PD.PlanStatusText(p)==ns.L['固定攻略参考；逐配方资料待补全。'])
          local run,reason=ns.ProfExecution.Bind('first-aid',p);assert(not run and reason=='pending')
          assert(PD.AuctionatorStatusText()==ns.L['拍卖行价格可用'])
        ''')

    def test_missing_prices_are_not_zero_and_partial_target_does_not_use_full_shopping(self):
        self.lua.execute('''
          Auctionator.API.v1.GetAuctionPriceByItemID=function()return nil end
          local p=ns.ProfRouteAuto.FixedPlan('first-aid',{target=300})
          assert(p.referenceOnly and not p.referenceQuoted and not p.referenceCostComplete)
          assert(PD.PlanCostText(p)==ns.L['材料价格待补全'])
          local partial=ns.ProfRouteAuto.FixedPlan('first-aid',{target=75})
          assert(partial.referenceOnly and not partial.referenceShopping and #partial.mats==0)
          assert(PD.PlanCostText(partial)==ns.L['配方资料待补全'])
          local rows={};PD.RowsAutoShop(rows,partial)
          for _,r in ipairs(rows)do assert(r.text~=ns.L['没有需要准备的材料。'])end
        ''')

    def test_leveling_page_does_not_mislabel_missing_recipe_details_as_missing_auction_prices(self):
        self.lua.execute('''
          local rows={};PD.RowsLeveling(rows)
          assert(PD.lvSummary.referenceOnly and PD.lvSummary.referenceQuoted)
          assert(PD.PlanCostText(PD.lvSummary):find(ns.L['材料参考价'],1,true))
          for _,line in ipairs(PD.warnNotes or {})do
            assert(line[1]~=ns.L['暂无有效拍卖行价格；请扫描或更新价格。'])
            assert(not line[1]:find('clientDataPending',1,true),'missing recipe data was labeled as a specialization block')
          end
          local steps=0
          for _,row in ipairs(rows)do if row.lvstep then
            steps=steps+1;assert(row.cost==ns.L['配方资料待补全'] and row.src==ns.L['配方资料待补全'])
          end end
          assert(steps==16)
        ''')

    def test_full_shopping_and_cost_tile_show_material_reference_price(self):
        self.lua.execute('''
          local rows={};PD.RowsLeveling(rows)
          local function tile()
            local f=widget();f.label=widget();f.val=widget()
            f.val.SetText=function(self,value)self.text=value end
            return f
          end
          PD.lvTiles={mode=tile(),scheme=tile(),excl=tile(),target=tile(),cost=tile()}
          PD.chipOrder={'mode','scheme','excl','target'}
          PD.LV_TILE_H=60
          PD.PaintTileBorder=function()end;PD.PlaceCards=function()end
          PD.SetBadge=function()end;PD.SetSub=function()end
          PD.TipTile=function(t,lines)t.lines=lines end
          PD.PaintLvTiles()
          assert(PD.lvTiles.cost.val.text:find(ns.L['材料参考价'],1,true))
          for _,line in ipairs(PD.lvTiles.cost.lines)do
            assert(line[1]~=ns.L['暂无有效拍卖行价格；请扫描或更新价格。'])
          end
          PD.autoPage='shop';rows={};PD.RowsLeveling(rows)
          assert(PD.lvSummary.referenceOnly and PD.lvShopData.referenceShopping)
          local found=false
          for _,r in ipairs(rows)do
            if r.text and r.text:find(ns.L['材料参考价'],1,true)then found=true end
            assert(r.text~=ns.L['暂无有效拍卖行价格；请扫描或更新价格。'])
          end
          assert(found,'shopping total discarded the available material quotes')
        ''')

    def test_one_missing_price_keeps_known_cost_visible(self):
        self.lua.execute('''
          Auctionator.API.v1.GetAuctionPriceByItemID=function(_,id)if id~=14047 then return 1 end end
          local p=ns.ProfRouteAuto.FixedPlan('first-aid',{target=300})
          assert(p.referenceQuoted and not p.referenceCostComplete)
          assert(PD.PlanCostText(p):find('≥',1,true))
          local missing=false
          for _,r in ipairs(p.mats)do if r.id==14047 then missing=r.unpriced==true end end
          assert(missing and p.completeCost==false and p.feasible==false)
          assert(ns.ProfExecution.Bind('first-aid',p)==nil)
        ''')

    def test_reference_quotes_keep_enabled_stock_checks(self):
        self.lua.execute('''
          local RA=ns.ProfRouteAuto
          local p=RA.FixedPlan('first-aid',{target=300,considerAuctionSupply=true})
          assert(p.referenceQuoted and not p.referenceCostComplete and p.auctionSupplyUnknown==14)
          ns.AuctionBridge={GetAuctionSupply=function()return {quantity=0,observedAt=1000,
            complete=true,ownerExcluded=true,source='client-auction-results',market=1}end}
          p=RA.FixedPlan('first-aid',{target=300,considerAuctionSupply=true})
          assert(p.referenceQuoted and not p.referenceCostComplete and p.feasible==false)
          for _,r in ipairs(p.mats)do assert(r.unavailable and r.availableCount==0)end
          assert(ns.ProfExecution.Bind('first-aid',p)==nil)
        ''')


if __name__=='__main__':unittest.main()
