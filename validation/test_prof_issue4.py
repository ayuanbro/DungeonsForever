"""Issue #4 regressions against native Lua 5.1 code, without a WoW client.

Widget records check anchors and entry-point integration, not game pixels.
"""
import unittest
import test_prof_ui_fusion as ui

ROOT = ui.ROOT

WIDGETS = r'''
function recordedWidget()
 local w={points={},scripts={},visible=false,width=0,height=20,text=''}
 function w:ClearAllPoints()self.points={}end
 function w:SetPoint(...)self.points[#self.points+1]={...}end
 function w:SetAllPoints(other)self.points={{'TOPLEFT',other},{'BOTTOMRIGHT',other}}end
 function w:SetSize(x,y)self.width=x;self.height=y end
 function w:SetWidth(x)self.width=x end
 function w:SetHeight(y)self.height=y end
 function w:GetWidth()return self.width end
 function w:GetHeight()return self.height end
 function w:SetText(text)self.text=text or ''end
 function w:GetText()return self.text end
 function w:GetFont()return 'font',13 end
 function w:GetStringWidth()return #self.text*6 end
 function w:GetStringHeight()return 14 end
 function w:SetScript(k,fn)self.scripts[k]=fn end
 function w:Show()self.visible=true end
 function w:Hide()self.visible=false end
 function w:SetShown(on)self.visible=not not on end
 function w:IsShown()return self.visible end
 function w:IsMouseOver()return false end
 function w:CreateTexture()return recordedWidget()end
 return setmetatable(w,{__index=function(_,k)
  if k:match('^Set') or k:match('^Enable') or k:match('^Register') then return function()end end
 end})
end
function recordedRow()
 local r=recordedWidget();r.blk={}
 for name in ('a b c c2 d e f dv h1 h2 h3 h4 h5 h6 icon icon2 icon3 icon4 hsTot hsOwn hsCraft hsGap tagFs tagChip sep bT bB bL bR'):gmatch('%S+')do
  r[name]=recordedWidget()
 end
 return r
end
'''


class Issue4Tests(unittest.TestCase):
    boot = ui.ProfessionUIFusionTests.boot

    def setUp(self):
        self.boot('zhCN')
        self.lua.execute("ns.DB=function()return DungeonsForeverDB end")
        for name in ('VendorPriceDB', 'ProfFollow'):
            self.load((ROOT / 'Core' / (name + '.lua')).read_text(encoding='utf-8-sig'))
        self.lua.execute(WIDGETS)

    def test_1_recycled_recipe_header_has_one_anchor_per_sort_icon(self):
        self.lua.execute(r'''
          local r=recordedRow()
          for _,name in ipairs({'icon','icon2','icon3'})do r[name]:SetAllPoints(r)end
          PD.BindRow(r,{kind='rechead'},26)
          for _,name in ipairs({'icon','icon2','icon3'})do
            local icon=r[name]
            assert(#icon.points==1 and icon.points[1][1]=='RIGHT',name..' retained an old anchor')
            assert(icon.width==14 and icon.height==14)
          end
          r.hsOwn.__act();assert(PD.recipeSort=='cost')
          r.hsOwn.__act();assert(PD.recipeSortDesc)
          r.hsOwn.__act();assert(PD.recipeSort==nil)
        ''')

    def test_2_track_button_cancels_and_keeps_recorded_attempts(self):
        self.lua.execute(r'''
          local plan=finish('alchemy',{start=1,target=3})
          PD.autoSnapshot=plan;PD.autoSnapshotSlug='alchemy'
          local _,click=PD.LevelTool();click('track')
          local run=assert(ns.ProfTrack.Active('alchemy'))
          assert(ns.ProfExecution.RecordAttempt('alchemy',101,'issue4-cast'))
          local before=ns.ProfTrack.Progress('alchemy',1).casts
          assert(before==1)
          _,click=PD.LevelTool();click('track')
          assert(not ns.ProfTrack.Active('alchemy'))
          assert(run.status~='active' and ns.ProfTrack.Get('alchemy',run.planID))
          assert(ns.ProfExecution.Progress('alchemy',1,nil,run.planID).casts==before)
          local buttons=PD.LevelTool()
          for _,button in ipairs(buttons)do if button.key=='track'then assert(not button.on)end end
        ''')

    def test_3_anonymous_seed_currency_and_drop_only_sources_are_not_npc_purchases(self):
        self.lua.execute(r'''
          local E=ns.ProfEconomy
          local r={profession='alchemy',spell=101,key='alchemy:101',formula=400,source={drops={{npc='Drop boss'}}}}
          local s={known={},prices={},formulaOffers={[400]={
            {price=20,unlimited=true,priceOnly=true},
            {npcID=1,price=0,unlimited=true,currencyID=7},
            {npcID=2,price=0,unlimited=true,hasExtendedCost=true}}}}
          local f=E.FormulaFor(r,s)
          assert(f.source~='vendor' and not f.usable and #f.vendorOffers==0 and #f.sources.drops==1)
          s.prices[400]=50;s.stamp=1000
          s.auctionSupply={[400]={quantity=2,observedAt=900,complete=true,
            ownerExcluded=true,source='client-auction-results'}}
          f=E.FormulaFor(r,s)
          assert(f.source=='ah' and not f.vendor)
          local rows={};PD.RowsFormulaShop(rows,{formulas={f}})
          for _,row in ipairs(rows)do
            assert(not row.tag or row.tag.text~='NPC购买')
          end
          s.formulaOffers[400]={{npcID=3,price=15,quantity=1,unlimited=true}}
          f=E.FormulaFor(r,s)
          assert(f.source=='vendor' and f.npcID==3 and #f.sources.vendors==1)
          assert(f.sources.drops[1].npc=='Drop boss','selected purchase source erased reference acquisition data')
          assert(#r.source.drops==1,'procurement mutated recipe source data')
        ''')

    def test_3_formula_offers_reject_placeholder_and_preserve_real_stock(self):
        self.lua.execute(r'''
          ns.ProfSupply={FormulaList=function()return {
            {npcID=3,price=20,quantity=1,unlimited=false,limited=1,maxStock=1,source='formula-offers',verifiedAt=1},
            {npcID=4,price=21,quantity=1,unlimited=false,limited=1,maxStock=1,source='formula-offers',verifiedAt=1}}
          end}
          local source={vendors={{name='商人',price=10,unlimited=true},
            {id=5,name='Currency vendor',price=0,cur=99,unlimited=true},
            {id=3,name='Real merchant'}}}
          local offers=ns.VendorPriceDB.GetFormulaOffers(400,{},source)
          assert(#offers==2)
          for _,offer in ipairs(offers)do assert(offer.npcID and offer.limited and not offer.unlimited)end
          local f=ns.ProfEconomy.FormulaFor({profession='alchemy',spell=101,formula=400},
            {known={},prices={},formulaOffers={[400]=offers},allowLimitedFormulas=true})
          assert(f.limited and not f.unlimited and f.source=='vendor')
          assert(PD.FormulaStockChip(f).text=='限量刷新')
          assert(PD.FormulaStockChip({unlimited=true,limited=true}).text=='不限量+限量')
        ''')

    def test_3_unpriced_unlearned_formula_is_excluded_from_solver(self):
        self.load((ROOT / 'Core/ProfSolverCapture.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          local s=fixture();s.known={};s.recipes[1].formula=400
          s.formulaOffers={[400]={{price=1,unlimited=true,priceOnly=true}}}
          local result=finish('alchemy',{snapshot=s,start=1,target=3})
          assert(not result.targetReached and result.feasible==false)
          s.known['alchemy:101']=true
          assert(ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=3}).targetReached)
        ''')

    def test_4_page_reopen_and_reload_reuse_saved_plan_without_capture(self):
        self.lua.execute(r'''
          PD.RowsLeveling({})
          local opts=ns.ProfRouteAuto.OptionsFor('alchemy',1);opts.target=3
          savedPlan=finish('alchemy',opts)
          ns.ProfEconomy.Capture=function()error('opening a cached route must not capture')end
          PD.RowsLeveling({});PD.RowsLeveling({})
          assert(PD.autoSnapshot.planID==savedPlan.planID)
        ''')
        self.load((ROOT / 'Core/ProfRoutePlans.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          PD.RowsLeveling({})
          assert(PD.autoSnapshot.cached and PD.autoSnapshot.planID==savedPlan.planID)
        ''')

    def test_3_fixed_and_fast_routes_do_not_use_vendor_price_seeds_for_formulas(self):
        self.lua.execute(r'''
          local r=ns.ProfRecipes.alchemy.rows[1];r[13]={400};r[14]={drops={{npc='Boss'}}}
          ns.VendorPriceSeed={[400]=1}
          ns.ProfEconomy.Known=function()return false end
          local fixed=ns.ProfRouteAuto.SummarizeSteps({{1,3,101,2}},'alchemy',{target=3})
          assert(#fixed.formulas==1 and not fixed.formulas[1].usable and not fixed.formulas[1].vendor)
          assert(fixed.feasible==false)
          -- All purchasing strategies now share the solver; make the captured
          -- fixture reflect the same unlearned drop formula as the native row.
          local capture=ns.ProfEconomy.Capture
          ns.ProfEconomy.Capture=function(...)
            local s=capture(...);s.known={};s.recipes[1].formula=400
            s.recipes[1].source={drops={{npc='Boss'}}};return ns.ProfEconomy.Index(s)
          end
          for _,scheme in ipairs({'crafts','matcost','optim'})do
            local result=ns.ProfRouteAuto.Compute('alchemy',{start=1,target=3,scheme=scheme})
            assert(result and #result.steps==0,scheme..' used an unavailable formula')
          end
          ns.ProfLeveling.alchemy.rinfo={[102]={spell=102,makes=10,count=1,formula=400,
            mats={{11,1}},learn=1,yellow=100,green=200,grey=300,cooldown=false}}
          local normalized=ns.ProfRouteAuto.SummarizeSteps({{1,3,102,2}},'alchemy',{target=3})
          assert(#normalized.formulas==1 and normalized.feasible==false,'normalized fixed recipe lost its formula')
        ''')

    def test_5_cheaper_remote_merchant_competes_with_city_and_auction(self):
        self.load((ROOT / 'Core/ProfSolverCapture.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          ns.ProfVendors={[1]={0,1446,20,20},[2]={0,1453,30,30}}
          local s=fixture();s.prices={[11]=50};s.offers={[11]={
            {npcID=1,price=20,quantity=1,unlimited=true},
            {npcID=2,price=100,quantity=1,unlimited=true}}}
          local result=finish('alchemy',{snapshot=s,start=1,target=3})
          assert(result.targetReached and result.total==40 and result.mats[1].npcID==1)
          local f=ns.ProfEconomy.FormulaFor({profession='alchemy',spell=101,formula=400},
            {known={},prices={},formulaOffers={[400]=s.offers[11]}})
          assert(f.npcID==1 and f.cost==20)
          s.offers[11][1].available=false
          result=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=3})
          assert(result.targetReached and result.total==100 and result.mats[1].source=='ah')
        ''')

    def test_5_reference_city_supplier_is_considered_beside_observed_remote_offer(self):
        self.lua.execute(r'''
          ns.ProfVendors={[1]={0,1446,20,20},[2]={0,1453,30,30}}
          DungeonsForeverDB.profVendorOffers={[11]={{npcID=1,price=1,quantity=1,unlimited=true,
            source='merchant',verifiedAt=1,character='Test-Realm',reputationKey=''}}}
          ns.ProfVendorOffers={[11]={{npcID=2,price=7,quantity=1,unlimited=true,
            source='supply-verified',verifiedAt=1,reference=true,priceVerified=true}}}
          local offers=ns.VendorPriceDB.GetOffers(11)
          assert(#offers==2 and offers[1].npcID==1 and offers[2].npcID==2)
          offers=ns.VendorPriceDB.GetOffers(11,{requireObservedPrice=true})
          assert(#offers==1 and offers[1].npcID==1)
        ''')

    def test_5_whole_pack_cost_competes_before_location_or_unit_price(self):
        self.load((ROOT / 'Core/ProfSolverCapture.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          ns.ProfVendors={[1]={0,1446,20,20},[2]={0,1453,30,30}}
          local s=fixture();s.prices={[11]=5};s.offers={[11]={
            {npcID=1,price=2,quantity=1,unlimited=true},
            {npcID=2,price=10,quantity=10,unlimited=true}}}
          local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=2})
          assert(r.targetReached and r.total==2 and r.mats[1].npcID==1 and r.mats[1].count==1)
          r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=11})
          assert(r.targetReached and r.total==10 and r.mats[1].npcID==2 and r.mats[1].count==10)
        ''')

    def test_6_hud_first_panel_uses_only_actual_missing_vendor_materials(self):
        self.lua.execute(r'''
          local plan=finish('alchemy',{start=1,target=2})
          plan.executionSteps[1].recipe.mats={{11,6},{12,3}}
          plan.mats={{id=11,count=4,source='vendor',npcID=2,cost=4,unit=1,bundleSize=1,unlimited=true},
            {id=11,count=2,source='vendor',npcID=2,cost=2,unit=1,bundleSize=1,unlimited=true},
            {id=12,count=3,source='ah',cost=3,unit=1}}
          plan.formulas={{id=400,count=1,source='vendor'}}
          bag[11]=2
          local list=ns.ProfFollow.VendorPurchases('alchemy',plan)
          assert(#list==1 and list[1].missing==4 and list[1].npcID==2)
          ns.ProfExecution.GetPlan=function()return plan end
          DungeonsForeverDB.prof.follow={['Test-Realm']={slug='alchemy',step=1}}
          local panel=recordedWidget();panel.title=recordedWidget();panel.more=recordedWidget();panel.rows={}
          for i=1,6 do local row=recordedWidget();row.name=recordedWidget();row.source=recordedWidget();panel.rows[i]=row end
          ns.ProfFollow.f=recordedWidget();ns.ProfFollow.f.vendorShop=panel
          local y=ns.ProfFollow.PaintVendorPurchases('alchemy',-82)
          assert(y < -82 and panel:IsShown() and panel.rows[1].name.text:find('×4',1,true))
          bag[11]=6
          assert(ns.ProfFollow.PaintVendorPurchases('alchemy',-82)==-82 and not panel:IsShown())
          bag[11]=0;DungeonsForeverDB.prof.follow['Test-Realm'].step=2
          assert(ns.ProfFollow.PaintVendorPurchases('alchemy',-82)==-82 and not panel:IsShown())
        ''')

    def test_6_native_hud_build_paints_scrollable_vendor_panel_before_craft_card(self):
        self.lua.execute(r'''
          CreateFrame=recordedWidget
          ns.ProfHost.MakeFS=recordedWidget;ns.ProfHost.NewButton=recordedWidget
          ns.ProfHost.DG.ItemIcon=function()return '?'end
        ''')
        self.load((ROOT / 'Core/ProfFollow.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          local plan=finish('alchemy',{start=1,target=2})
          plan.mats={};plan.executionSteps[1].recipe.mats={}
          for i=1,8 do
            plan.mats[i]={id=20+i,count=i,source='vendor',vendor=true,npcID=2,cost=i,unit=1,bundleSize=1,unlimited=true}
            plan.executionSteps[1].recipe.mats[i]={20+i,i}
          end
          assert(ns.ProfExecution.Bind('alchemy',plan))
          local pf=ns.ProfFollow
          DungeonsForeverDB.prof.follow={['Test-Realm']={slug='alchemy',skill=1,step=1,t0=1000}}
          pf.Build();assert(pf.f,'native HUD constructor failed')
          pf.f:Show();pf.Paint()
          assert(pf.f.vendorShop:IsShown() and pf.f.vendorShop.more:IsShown())
          assert(pf.f.card.points[1][5] < pf.f.vendorShop.points[1][5])
          pf.f.vendorShop.scripts.OnMouseWheel(nil,-1)
          assert(pf.vendorScroll==1 and pf.f.vendorShop.rows[1].name.text:find('Item22',1,true))
        ''')

    def test_3_rejected_formula_supplier_cannot_return_through_capture_fallback(self):
        self.load((ROOT / 'Core/ProfSolverCapture.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          ns.ProfRecipes.alchemy.rows[1][13]={400}
          ns.ProfEconomy.Known=function()return false end
          ns.VendorPriceDB.GetFormulaOffers=function()return {}end
          ns.ProfSupply={Ensure=function()end,FormulaList=function()error('rejected suppliers revived')end}
          local snapshot=ns.ProfEconomy.Capture('alchemy',{})
          assert(snapshot.formulaOffers[400] and #snapshot.formulaOffers[400]==0)
        ''')

    def test_7_all_professions_have_due_guidance_and_secondary_directions(self):
        for path in ('Core/Data/Data_ProfTrainers.lua','Core/Data/Data_ProfVendors.lua','Core/ProfRanks.lua'):
            self.load((ROOT / path).read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          ns.EnsureProfTrainers()
          local ranks=ns.ProfRanks
          for _,slug in ipairs({'alchemy','blacksmithing','enchanting','engineering','leatherworking',
            'tailoring','mining','herbalism','skinning','cooking','fishing','first-aid'})do
            for _,pair in ipairs({{50,75},{125,150},{225,225}})do
              local step=ranks.NextStep(slug,300,{skill=pair[1],maxSkill=pair[2],level=60,faction='A'})
              assert(step and step.due and #step.sources>0,slug..':'..pair[1])
              for _,source in ipairs(step.sources)do assert(source.name and source.map and source.x and source.y)end
            end
          end
          local fishing=ranks.NextStep('fishing',300,{skill=125,maxSkill=150,level=60})
          assert(fishing.method=='book' and fishing.sources[1].npcID==2626)
          fishing=ranks.NextStep('fishing',300,{skill=225,maxSkill=225,level=60})
          assert(fishing.sources[1].questID==6607)
          PD.cur='fishing';ranks.NextStep=function()return fishing end
          PD.Wrap=function(text)return {text}end
          local rows={};PD.RowsRankReminder(rows);assert(#rows>2)
          assert(#ns.ProfFollow.RankTasks('fishing',300)==1)
        ''')

    def test_8_engineering_quest_step_never_uses_mining_name_or_role(self):
        self.lua.execute(r'''
          local step={200,200,0,0,kind='specialization_quest',profession='engineering',checkpoint=true}
          assert(PD.StepName(step)=='专精任务' and PD.StepRole(step)=='专精任务')
          assert(PD.StepName({1,50,0,0,navigationOnly=true,name='采药参考'})=='采药参考')
        ''')

    def test_9_long_gathering_zone_names_are_bounded_before_level_labels(self):
        self.lua.execute(r'''
          CreateFrame=recordedWidget;PD.gcRoot=recordedWidget()
          ns.ProfHost.MakeFS=recordedWidget
          ns.ProfGathering={herbalism={{{1},1,{{10,2}}},{{2},15,{{10,3}}}}}
          ns.ProfHost.DG.ZoneName=function()return 'Long zone name'end
        ''')
        self.load((ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          PD=ns.ProfModule;PD.gcRoot=recordedWidget()
          local c=PD.GCEnsure(1)
          PD.ItemIcon=function()return '?'end;PD.QualCached=function()end
          PD.GCFill(c,{kind='route',key='r1',name='1 - 50',icons={},
            places={{zone=1,name=string.rep('Long zone ',30),lv='10 - 20'}}})
          assert(c.places[1].zl.width>0 and c.places[1].zl.width<=PD.GC_COLW/3)
          assert(c.places[1].__name:find('Long zone',1,true))
          local zone=c.places[1].zn;local anchored=false
          for _,point in ipairs(zone.points)do
            if point[1]=='RIGHT' and point[2]==c.places[1].zl and point[4]<0 then anchored=true end
          end
          assert(anchored,'zone name can overlap its level label')
          assert(not c.icon:IsShown() and not c.lv:IsShown())
          PD.cur='herbalism';PD.ProfLearned=function()return {herbalism={cur=20,max=75}}end
          for i=1,3 do
            local cards=PD.GatherRouteCards({});assert(#cards==1 and #cards[1].icons==2)
            assert(#ns.ProfGathering.herbalism[1][1]==1,'render changed the reference gathering table')
          end
        ''')


if __name__ == '__main__':
    unittest.main()
