"""Route input identity, verified recipes and the reported native UI regressions."""
import unittest
import test_prof_ui_fusion as ui
from test_prof_native_data import native_runtime
from test_prof_issue4 import WIDGETS

ROOT=ui.ROOT


class RouteUIRegressions(unittest.TestCase):
    setUp=ui.ProfessionUIFusionTests.setUp
    boot=ui.ProfessionUIFusionTests.boot

    def test_cache_refresh_quote_counter_and_reload_do_not_claim_changed_inputs(self):
        self.lua.execute('''
          local ra=ns.ProfRouteAuto
          price=7;ra.AHPriceOf=function()return price end
          ns.ProfEconomy.Capture=function()
            local s=fixture();s.auctionPriceInputs={[11]=price}
            s.prices[11]=price;return ns.ProfEconomy.Index(s)
          end
          local opts=ra.OptionsFor('alchemy',1);opts.target=3
          saved=finish('alchemy',opts);savedID=saved.planID
          assert(not saved.stale)
          ra.Invalidate();assert(not ra.Get('alchemy',opts).stale)
          ra.QuoteSig=function()return 'different-process-counter' end
          assert(not ra.Get('alchemy',opts).stale)
          saved.stale=true;saved.staleReason='inputs'
          assert(not ra.Get('alchemy',opts).stale,'old cache-clear marker stayed sticky')
        ''')
        self.load((ROOT/'Core/ProfRoutePlans.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local ra=ns.ProfRouteAuto;local opts=ra.OptionsFor('alchemy',1);opts.target=3
          local p=finish('alchemy',opts)
          assert(p.cached and p.planID==savedID and not p.stale)
          price=9;ra.Invalidate()
          assert(ra.Get('alchemy',opts).stale and p.staleReason=='prices')
          price=7;ra.Invalidate()
          assert(not ra.Get('alchemy',opts).stale,'unchanged inputs retained an obsolete marker')
          DungeonsForeverDB.prof.autoCraftTools=false
          opts=ra.OptionsFor('alchemy',1);opts.target=3
          assert(ra.Get('alchemy',opts).stale and p.settingsChanged)
        ''')

    def test_first_noop_client_refresh_does_not_invalidate_the_plan(self):
        self.load((ROOT/'Core/ProfClientScan.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local E=ns.ProfEconomy;local invalidations=0
          ns.ProfRouteAuto.Invalidate=function()invalidations=invalidations+1 end
          E.ScanRecipes=function()end;E.ScanCrafts=function()end
          E.RefreshClientData(true,false,nil,nil,false)
          queue[#queue]()
          assert(invalidations==0,'first no-op scan was treated as changed input')
          E.ScanRecipes=function()
            local d=E.ClientStore();d.clientInputRevision=(d.clientInputRevision or 0)+1
          end
          E.RefreshClientData(true,false,nil,nil,false);queue[#queue]()
          assert(invalidations==1,'actual client recipe change was ignored')
        ''')

    def test_reopening_page_and_closing_auction_house_with_no_changes_are_not_stale(self):
        self.lua.execute('''
          PD.RowsLeveling({})
          local opts=ns.ProfRouteAuto.OptionsFor('alchemy',1);opts.target=3
          local plan=finish('alchemy',opts)
          PD.RowsLeveling({});PD.RowsLeveling({})
          assert(not plan.stale)
          for _,frame in ipairs(frames) do
            if frame.events and frame.events.AUCTION_HOUSE_CLOSED then frame.OnEvent() end
          end
          local pending=timers;timers={};for _,fn in ipairs(pending)do fn()end
          PD.RowsLeveling({})
          assert(not PD.autoSnapshot.stale,'auction close without changes marked the plan stale')
        ''')

    def test_reobserving_the_same_supply_does_not_change_a_route(self):
        self.lua.execute('''
          local current={quantity=10,observedAt=200,source='client-auction-results',complete=true,ownerExcluded=true}
          ns.AuctionBridge={GetAuctionSupply=function()return current end}
          local plan={auctionSupplyInputs={[11]={quantity=10,observedAt=100,
            source='client-auction-results',complete=true,ownerExcluded=true}}}
          assert(not ns.ProfEconomy.AuctionSupplyChanged(plan))
          current.quantity=9;assert(ns.ProfEconomy.AuctionSupplyChanged(plan))
        ''')

    def test_progress_and_stale_notice_never_share_the_header(self):
        self.lua.execute(WIDGETS)
        self.lua.execute('''
          PD.page=recordedWidget();PD.setGear=recordedWidget();PD.setGear:Show()
          PD.__progFs=recordedWidget();PD.__progHolder=recordedWidget()
          PD.__staleFs=recordedWidget();PD.__staleHolder=recordedWidget()
          CreateFrame=recordedWidget
          PD.PaintToolStale('Changed');assert(PD.__staleHolder:IsShown())
          PD.PaintToolProgress('Optimizing',0.43)
          assert(PD.__progHolder:IsShown() and not PD.__staleHolder:IsShown())
          PD.PaintToolStale('Changed');assert(not PD.__staleHolder:IsShown())
          PD.PaintToolProgress(nil,nil);PD.PaintToolStale('Changed')
          assert(not PD.__progHolder:IsShown() and PD.__staleHolder:IsShown())
        ''')

    def test_gather_upgrade_render_never_inserts_the_rank_trainer_block(self):
        self.lua.execute('''
          ns.ProfRanks={NextStep=function()error('gathering rank block should be hidden')end}
          for _,slug in ipairs({'herbalism','mining','skinning'})do
            PD.cur=slug;local rows={};PD.RowsRankReminder(rows,300);assert(#rows==0)
          end
          PD.built=true;PD.page=widget();PD.scroll=widget();PD.LV_TILE_H=64
          for _,name in ipairs({'PickNav','PickTabs','Layout','PaintRows','PlaceSettingsToggles',
            'RequestRows','WarmNames','PaintToolProgress','PaintToolStale','UpdateVScroll'})do
            PD[name]=function()end
          end
          PD.PaintLvTiles=function()return 0 end;PD.PaintTool=function()return 0 end
          PD.RowsRankReminder=function()error('gather route inserted a trainer block')end
          PD.GatherRouteCards=function()return {{name='Gather route'}}end
          for _,slug in ipairs({'herbalism','mining','skinning'})do
            PD.cur=slug;PD.tab='leveling';PD.Render()
            assert(PD.wantGCards and #PD.gcSpec==1 and #PD.specs==0)
          end
        ''')

    def test_cost_badge_distinguishes_working_missing_prices_and_no_route(self):
        self.lua.execute('''
          assert(PD.SnapshotBadgeState({planVersion=2,status='searching',completeCost=false})=='calculating')
          assert(PD.SnapshotBadgeState({planVersion=2,status='infeasible',completeCost=false})=='no_route')
          assert(PD.SnapshotBadgeState({planVersion=2,status='incomplete',completeCost=false})=='incomplete')
          assert(PD.PlanProgressText({status='complete',expanded=50})==nil)
          assert(PD.PlanProgressText({status='infeasible',expanded=1})==nil)
        ''')


class VerifiedPreviewRegressions(unittest.TestCase):
    def test_unlearned_solo_capture_uses_native_catalogue_without_a_trainer_visit(self):
        lua=native_runtime()
        lua.execute('''
          ns.ProfModule.ProfLearned=function()return {blacksmithing={cur=57,max=300}}end
          observedKnown={}
          local E=ns.ProfEconomy
          local s=E.Capture('alchemy',{start=1,target=300,autoCraftTools=false})
          assert(s.routeContext.unlearned and not s.routeContext.requiresPartner)
          assert(#s.recipes>0,'unlearned preview captured an empty catalogue')
          local r=E.FindRecipe('alchemy',7183)
          local allowed,reason,detail=E.RouteRecipeEligibility(r,s)
          assert(allowed and detail.status=='catalogue')
          -- Native eligibility must work without a trainer visit or a learned spell.
          assert(E.RouteRecipeEligibility(r,s))
          s.recipes={r};s=E.Index(s)
          for _,m in ipairs(r.mats)do s.prices[m[1]]=1 end
          local plan=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=75,
            autoCraftTools=false,recoveryEnabled=false,cpuLimitMs=1000})
          assert(plan.targetReached and #plan.steps>0 and plan.completeCost)
        ''')

    def test_unlearned_full_alchemy_does_not_require_transmutation_equipment(self):
        lua=native_runtime()
        lua.execute('''
          ns.ProfModule.ProfLearned=function()return {blacksmithing={cur=57,max=300}}end
          observedKnown={}
          local E=ns.ProfEconomy
          local s=E.Capture('alchemy',{start=1,target=300,autoCraftTools=true,noFormula=true})
          assert(#s.recipes>0 and #s.toolGoals==0)
          assert(not E.HasToolGoals('alchemy',{target=300,autoCraftTools=true}))
          local p=ns.ProfRouteSolver.Compute('alchemy',{start=1,target=300,
            autoCraftTools=true,noFormula=true,recoveryEnabled=false,cpuLimitMs=1000})
          assert(p.targetReached and p.plannedTo==300 and p.completeCost)
          for _,step in ipairs(p.steps)do assert(step[3]~=11459 and step[3]~=17632)end
        ''')

    def test_retired_vendor_only_setting_cannot_block_a_verified_auction_formula(self):
        lua=native_runtime()
        lua.execute('''
          local E=ns.ProfEconomy
          local recipe=E.FindRecipe('alchemy',11459)
          local s={prices={[9303]=100},known={},professions={alchemy={cur=225,max=300}},noFormula=true,
            stamp=1000,auctionSupply={[9303]={quantity=2,complete=true,ownerExcluded=true,
              observedAt=1000,source='client-auction-results'}}}
          local f=E.FormulaFor(recipe,s)
          assert(f.usable and f.source=='ah' and f.cost==100)
          s.formulaOffers={[9303]={{npcID=5594,price=500,quantity=1,unlimited=true}}}
          f=E.FormulaFor(recipe,s);assert(f.usable and f.source=='ah' and f.cost==100)
          s.noFormula=false;f=E.FormulaFor(recipe,s);assert(f.usable and f.source=='ah' and f.cost==100)
        ''')

    def test_all_route_schemes_reject_unknown_learning_and_accept_confirmed_routes(self):
        fixture=RouteUIRegressions();fixture.setUp()
        fixture.load((ROOT/'Core/ProfLearning.lua').read_text(encoding='utf-8-sig'))
        fixture.lua.execute('''
          local E,RA=ns.ProfEconomy,ns.ProfRouteAuto
          E.Capture=function(_,opts)return E.Index(E.Copy(opts.snapshot))end
          local recipe=fixture().recipes[1];recipe.key='alchemy:101'
          recipe.learningRoutes={{kind='trainer',status='pending',conditions={}}}
          E.FindRecipe=function()return recipe end
          local s=fixture();s.known={};s.recipes={recipe}
          local p=RA.Compute('alchemy',{snapshot=s,start=1,target=3,autoCraftTools=false})
          assert(not p.targetReached and #p.steps==0)
          local filtered,blocked=RA.FilterFixedSpecializations('alchemy',{{1,3,101,2}},{snapshot=s})
          assert(#filtered==0 and blocked[1].reason=='learningRequirementsUnknown')
          for _,scheme in ipairs({'matcost','crafts','optim'})do
            local quick=RA.Compute('alchemy',{snapshot=s,start=1,target=3,scheme=scheme,autoCraftTools=false})
            assert(quick and #quick.steps==0,'unknown recipe entered '..scheme)
          end
          recipe.learningRoutes[1].status='confirmed';recipe.learningRoutes[1].conditionsKnown=true
          s=fixture();s.known={};s.recipes={recipe}
          p=RA.Compute('alchemy',{snapshot=s,start=1,target=3,autoCraftTools=false})
          assert(p.targetReached and p.completeCost)
        ''')


if __name__=='__main__':unittest.main()
