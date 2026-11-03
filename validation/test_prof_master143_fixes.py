"""Regression coverage for the four reviewed master 1.9.43 profession fixes.

Runs the real Lua modules with deterministic game events; no client files change.
"""
import unittest
import test_prof_execution_fusion as execution
import test_prof_route_plans as routes
import test_prof_ui_fusion as ui
import test_prof_auction_supply as stock
import test_prof_auctionator_full_scan as scans

ROOT = execution.ROOT


class RemainingDemandTests(unittest.TestCase):
    def setUp(self):
        self.lua = execution.LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(execution.MOCKS)
        self.load = self.lua.eval("function(s)assert(loadstring(s))('DungeonsForever',ns)end")
        self.load((ROOT/'Core/ProfExecution.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          initialize();xp=ns.ProfExecution;plan=fixture()
          plan.executionSteps[2]={3,6,102,3,segmentID='consumer',profession='alchemy',recipe=recipes[102],
            item=11,goalSkill=6,expectedGain=3,expectedCrafts=3,attemptLimit=3,outputMin=2,requiredOutputs={}}
          plan.executionSteps[1].allocations={{consumerID='consumer',itemID=10,count=6}}
          function start()run=xp.Bind('alchemy',plan);xp.Sync('alchemy')end
        ''')

    def test_overtaken_producer_waits_for_materials_still_needed_by_consumer(self):
        self.lua.execute('''
          skills.alchemy.cur=4;start()
          local p=xp.Progress('alchemy',1)
          assert(p.skillDone and not p.materialDone and not p.complete and p.remainingOutputs==6)
          assert(run.currentIndex==1)
          bag[10]=6;xp.Sync('alchemy')
          assert(xp.Progress('alchemy',1).complete and run.currentIndex==2)
        ''')

    def test_pure_leveling_does_not_require_expected_cast_count(self):
        self.lua.execute('''
          plan.executionSteps[1].requiredOutputs={};skills.alchemy.cur=3;start()
          assert(run.currentIndex==2 and xp.Progress('alchemy',1).casts==0)
        ''')

    def test_met_consumer_goal_releases_input_demand_and_invalidates_skill_cache(self):
        self.lua.execute('''
          skills.alchemy.cur=4;start();assert(xp.Progress('alchemy',1).remainingOutputs==6)
          skills.alchemy.cur=6;xp.Sync('alchemy')
          local p=xp.Progress('alchemy',1)
          assert(p.remainingOutputs==0 and p.complete and run.finished and p.casts==0)
          assert(run.plan.executionSteps[1].requiredOutputs[10]==6,'frozen quota was rewritten')
          assert(run.plan.executionSteps[1].allocations[1].count==6)
          skills.alchemy.cur=4;xp.Sync('alchemy')
          assert(xp.Progress('alchemy',1).remainingOutputs==6 and run.currentIndex==1)
        ''')

    def test_consumer_required_outputs_remain_even_after_all_skill_goals(self):
        self.lua.execute('''
          plan.executionSteps[2].requiredOutputs={[11]=4};skills.alchemy.cur=7;start()
          assert(xp.Progress('alchemy',1).remainingOutputs==4 and run.currentIndex==1)
          bag[11]=2;xp.Sync('alchemy')
          assert(xp.Progress('alchemy',1).remainingOutputs==2)
          bag[11]=4;xp.Sync('alchemy')
          assert(xp.Progress('alchemy',1).remainingOutputs==0 and run.finished)
          bag[11]=0;xp.Sync('alchemy')
          assert(xp.Progress('alchemy',1).remainingOutputs==4 and run.currentIndex==1)
        ''')

    def test_release_only_the_finished_consumers_share(self):
        self.lua.execute('''
          local next=ns.ProfEconomy.Copy(plan.executionSteps[2]);next.segmentID='later';next.goalSkill=9;next[2]=9
          plan.executionSteps[3]=next
          local first=plan.executionSteps[1];first.requiredOutputs[10]=12;first.expectedCrafts=6;first[4]=6
          first.allocations[2]={consumerID='later',itemID=10,count=6}
          skills.alchemy.cur=6;bag[10]=2;start()
          assert(xp.Progress('alchemy',1).remainingOutputs==4 and run.currentIndex==1)
        ''')

    def test_cross_profession_demand_uses_consumers_own_skill(self):
        self.lua.execute('''
          plan.executionSteps[2].profession='mining';plan.executionSteps[2].recipe.profession='mining'
          skills.alchemy.cur=300;skills.mining.cur=1;start()
          assert(xp.Progress('alchemy',1).remainingOutputs==6 and run.currentIndex==1)
          skills.mining.cur=6;xp.Sync('alchemy')
          assert(xp.Progress('alchemy',1).remainingOutputs==0 and run.finished)
        ''')

    def test_unknown_consumer_skill_or_inventory_cannot_discharge_required_output(self):
        self.lua.execute('''
          plan.executionSteps[2].profession='mining';skills.mining.cur=nil;skills.alchemy.cur=4;start()
          assert(xp.Progress('alchemy',1).remainingOutputs==6 and run.currentIndex==1)
          C_Item.GetItemCount=function()error('inventory unavailable')end
          xp.Sync('alchemy');local p=xp.Progress('alchemy',1)
          assert(p.inventoryUnknown and not p.complete and run.currentIndex==1)
        ''')

    def test_tool_output_and_uncompleted_quest_stay_required(self):
        self.lua.execute('''
          plan.executionSteps[2]=nil
          plan.executionSteps[1].tool=true;plan.executionSteps[1].requiredOutputs={[10]=1}
          plan.executionSteps[1].allocations={{consumerID='tool:10',itemID=10,count=1}}
          skills.alchemy.cur=300;start()
          assert(xp.Progress('alchemy',1).remainingOutputs==1 and not run.finished)
          xp.End('alchemy')
          plan.executionSteps[1].tool=nil;plan.executionSteps[1].requiredOutputs={[10]=6}
          plan.executionSteps[1].allocations={{consumerID='quest',itemID=10,count=6}}
          plan.executionSteps[2]={1,1,0,0,segmentID='quest',profession='alchemy',kind='specialization_quest',
            quest={abilityID=123,inputs={{10,6}}},expectedGain=0,requiredOutputs={}}
          run=xp.StartNew('alchemy',plan)
          assert(xp.Progress('alchemy',1).remainingOutputs==6 and not run.finished)
          ns.ProfEconomy.SpecializationKnown=function(id)return id==123 end;xp.Sync('alchemy')
          assert(run.finished and xp.Progress('alchemy',1).remainingOutputs==0)
        ''')

    def test_release_propagates_up_multilevel_material_chain(self):
        self.lua.execute('''
          local last={6,9,103,2,segmentID='last',profession='alchemy',item=12,goalSkill=9,expectedGain=3,
            expectedCrafts=2,attemptLimit=2,requiredOutputs={},recipe={spell=103,item=12,count=1,mats={{11,2}},learn=1}}
          plan.executionSteps[2].requiredOutputs={[11]=4}
          plan.executionSteps[2].allocations={{consumerID='last',itemID=11,count=4}}
          plan.executionSteps[3]=last;skills.alchemy.cur=9;start()
          assert(run.finished and xp.Progress('alchemy',1).remainingOutputs==0)
          assert(xp.Progress('alchemy',2).remainingOutputs==0 and run.attemptsDone==0)
        ''')

    def test_reload_rederives_release_from_frozen_plan_without_saving_projection(self):
        self.lua.execute('skills.alchemy.cur=6;start();assert(run.finished)')
        self.load((ROOT/'Core/ProfExecution.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          initialize();xp=ns.ProfExecution;run=xp.GetRun('alchemy')
          assert(xp.Progress('alchemy',1).remainingOutputs==0 and run.finished)
          assert(run.plan.executionSteps[1].requiredOutputs[10]==6 and run.attemptsDone==0)
        ''')

    def test_consumed_materials_and_released_demand_do_not_invent_bag_stock(self):
        self.lua.execute('''
          skills.alchemy.cur=4;start();xp.RecordAttempt('alchemy',102,'consumer-once')
          assert(xp.Progress('alchemy',1).remainingOutputs==4)
          skills.alchemy.cur=6;xp.Sync('alchemy');local p=xp.Progress('alchemy',1)
          assert(p.complete and p.remainingOutputs==0 and p.casts==0 and p.actualOutputs==0)
          assert(xp.GetContinuation('alchemy')[10]==nil and run.attemptsDone==1)
        ''')

    def test_repeated_hud_reads_reuse_demand_cache_until_skill_changes(self):
        self.lua.execute('''
          skills.alchemy.cur=4;start();local before=xp.PerformanceCounters().creditBuilds
          for i=1,20 do xp.GetProgressAll('alchemy')end
          assert(xp.PerformanceCounters().creditBuilds==before)
          skills.alchemy.cur=6;xp.GetProgressAll('alchemy')
          assert(xp.PerformanceCounters().creditBuilds==before+1)
        ''')

    def test_conversion_materials_are_kept_until_their_consumer_is_done(self):
        self.lua.execute('''
          plan.executionSteps[1]={1,1,0,2,segmentID='convert',profession='alchemy',kind='essence_conversion',
            conversion={inputItemID=20,inputCount=1,outputItemID=10,outputCount=3},item=10,
            expectedGain=0,expectedCrafts=2,outputMin=3,requiredOutputs={[10]=6},
            allocations={{consumerID='consumer',itemID=10,count=6}}}
          skills.alchemy.cur=4;start()
          assert(not xp.Progress('alchemy',1).complete and run.currentIndex==1)
          skills.alchemy.cur=6;xp.Sync('alchemy')
          assert(xp.Progress('alchemy',1).remainingOutputs==0 and run.finished and run.attemptsDone==0)
        ''')


class CompleteMarketTests(unittest.TestCase):
    def setUp(self):
        stock.AuctionSupplyBridgeTests.setUp(self)
        self.lua.execute(scans.SOURCE_MOCK)
        self.lua.execute('''
          ns.IsForever=true
          Auctionator.Config={Options={REPLICATE_SCAN='replicate'},Get=function()return true end}
          event('ADDON_LOADED','Auctionator')
        ''')

    def test_full_scan_keeps_formulas_enchant_materials_and_unloaded_professions(self):
        self.lua.execute('''
          ns.ProfRecipes={alchemy={rows={{101,10,1,'','','',1,100,200,300,false,{{11,1}},{12,1}}}}}
          for _,setting in ipairs({false,true}) do
            DungeonsForeverDB.prof.recoveryEnabled=setting
            ns.ProfModule={Setting=function(k)return DungeonsForeverDB.prof[k]==true end}
            beginFull(4);sendFull({rawRow(11,8,56,'Seller'),rawRow(12,2,14,'Seller'),
              rawRow(10940,10,50,'Seller'),rawRow(9999,3,21,'Seller')});finishFull()
            local b=ns.AuctionBridge
            assert(b.ReplicateScanReady()==true)
            for id,q in pairs({[11]=8,[12]=2,[10940]=10,[9999]=3}) do assert(b.GetAuctionSupply(id).quantity==q) end
            assert(b.GetAuctionSupply(8888).quantity==0)
            assert(DungeonsForeverDB.prof.auctionFullScan.items~=nil and #requests==0)
          end
        ''')

    def test_filtered_old_batch_is_unknown_until_new_complete_scan(self):
        self.lua.execute('''
          local b=ns.AuctionBridge;local _,gate=b.ObserveReplicateMode()
          ns.ProfModule={Setting=function(k)return k=='recoveryEnabled' end}
          DungeonsForeverDB.prof.auctionFullScan={v=1,c=true,t=clock,mk='Realm:Alliance',ob='Player',
            rg=gate.generation,rs=gate.scanSerial,items={[11]={q=8,p=7}}}
          assert(b.GetAuctionSupply(12)==nil and b.ReplicateScanReady()==false)
          beginFull(1);sendFull({rawRow(12,2,14,'Seller')});finishFull()
          assert(b.ReplicateScanReady()==true and b.GetAuctionSupply(12).quantity==2)
        ''')

    def test_mode_switch_and_failed_scan_keep_previous_success(self):
        self.lua.execute('''
          local b=ns.AuctionBridge
          beginFull(1);sendFull({rawRow(12,2,14,'Seller')});finishFull()
          Auctionator.Config.Get=function()return false end
          assert(b.ReplicateScanReady()==true and b.GetAuctionSupply(12).quantity==2)
          Auctionator.Config.Get=function()return true end
          assert(b.ReplicateScanReady()==true)
          beginFull(1);Auctionator.EventBus:Emit(Auctionator.FullScan.Events.ScanFailed)
          assert(b.ReplicateScanReady()==true and b.GetAuctionSupply(12).quantity==2)
          beginFull(1);sendFull({rawRow(12,1,7,'Seller')});finishFull()
          assert(b.ReplicateScanReady()==true and b.GetAuctionSupply(12).quantity==1)
        ''')

    def test_inventory_two_day_expiry_is_independent_of_prices(self):
        self.load((ROOT/'Core/ProfRouteAuto.lua').read_text(encoding='utf-8-sig'))
        self.load((ROOT/'Core/AuctionatorBridge.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          ns.ProfModule={Setting=function(k)return k=='recoveryEnabled' end}
          beginFull(1);sendFull({rawRow(12,2,14,'Seller')});finishFull()
          assert(ns.ProfRouteAuto.MaxStaleSeconds()==48*3600)
        ''')
        self.lua.execute('''
          local b=ns.AuctionBridge;clock=clock+2*86400
          assert(b.ReplicateScanReady()==true and b.GetAuctionSupply(12).quantity==2)
          clock=clock+1
          assert(b.ReplicateScanReady()==false and b.GetAuctionSupply(12)==nil)
        ''')


class UnifiedSupplyTests(unittest.TestCase):
    setUp = routes.NativeRoutePlansTests.setUp

    def test_live_route_entry_points_require_a_complete_scan(self):
        self.lua.execute("""
          ns.IsForever=true;ns.AuctionBridge={ReplicateScanReady=function()return false,'replicateScanRequired'end}
          ns.ProfEconomy.Capture=function()error('blocked calculation captured inputs')end
          local ra=ns.ProfRouteAuto
          for _,f in ipairs({ra.Get,ra.Compute,ra.Recalculate}) do
            for _,supply in ipairs({false,true})do
              local r=f('alchemy',{start=1,target=3,considerAuctionSupply=supply})
              assert(r.status=='recalculate_required' and r.diagnostics[1].code=='replicateScanRequired')
            end
          end
          assert(not ra.HasWork('alchemy'))
        """)

    def test_search_and_resume_stop_when_scan_becomes_unavailable(self):
        self.lua.execute("""
          ns.IsForever=true;local ready=true
          ns.AuctionBridge={ReplicateScanReady=function()return ready,'replicateScanRequired'end}
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end
          local ra=ns.ProfRouteAuto;ra.Get('alchemy',{start=1,target=3})
          assert(ra.HasWork('alchemy'));ready=false
          ra.Pump('alchemy')
          assert(ra.Peek('alchemy').searchTermination=='replicate_scan_required')
          assert(ra.Continue('alchemy')==false and not ra.HasWork('alchemy'))
          ready=true;ra.Continue('alchemy')
          assert(finish('alchemy',{start=1,target=3}).targetReached)
        """)

    def test_historical_estimate_cannot_become_frozen_or_live_material_budget(self):
        self.lua.execute('''
          local e=ns.ProfEconomy
          ns.AuctionBridge={SupplyEstimate=function()error('historical quantity used as purchase budget')end}
          local context={considerAuctionSupply=true,prices={[11]=7},auctionSupply={},stamp=1000}
          assert(e.AuctionSupplyOf(context,11)==nil and e.FormulaAuctionSupplyOf(context,11)==nil)
          assert(e.AuctionSupplyOf(nil,11)==nil)
        ''')


class EnchantSourceTests(unittest.TestCase):
    def boot(self, locale):
        ui.ProfessionUIFusionTests.boot(self,locale)
        self.load((ROOT/'Core/Data/Data_ProfRecipes.lua').read_text(encoding='utf-8-sig'))
        if locale != 'zhCN':
            self.load((ROOT/'Core/Data'/locale/'Data_ProfRecipes.lua').read_text(encoding='utf-8-sig'))
        self.load((ROOT/'Core/Data/Data_ProfFormulaOffers.lua').read_text(encoding='utf-8-sig'))
        self.load((ROOT/'Core/ProfSourceMerge.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          PD.cur='enchanting';PD.tab='recipe';PD.toolKey='all';ns.IsForever=true
          ns.ProfHost.DG.ItemIcon=function()return '?'end
          ns.EnsureProfNPCLocs=function()return {}end
        ''')

    def test_all_master_source_filters_reach_enchants_in_all_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                self.boot(locale)
                self.lua.execute('''
                  local d=ns.ProfRecipes.enchanting;local counts=PD.CurCounts(d)
                  for _,key in ipairs({PD.SRC_TRAINER_KEY,PD.SRC_DROP_KEY,PD.SRC_VENDOR_KEY,PD.SRC_UNKNOWN_KEY,PD.SRC_NIP_KEY}) do
                    PD.moneyKey=key;PD.RecipeTool(d)
                    local list=PD.RecipeList(1000)
                    assert(#list==(counts[key] or 0),tostring(key)..':'..#list..'/'..tostring(counts[key]))
                    assert(PD.ScanRecipe()==nil,'regular recipe counter hid enchants')
                    if #list>0 then
                      local rows={};PD.RowsRecipe(rows);local n=0
                      for _,r in ipairs(rows)do if r.kind=='row' then n=n+1 end end
                      assert(n==#list,'page rendering lost source-filtered rows')
                    end
                  end
                  assert(PD.SETTING_DEF.preciseRecovery==nil)
                ''')

    def test_source_filter_keeps_name_search_and_master_buttons(self):
        self.boot('zhCN')
        self.lua.execute('''
          PD.moneyKey=PD.SRC_TRAINER_KEY
          local list=PD.RecipeList(1000);assert(#list>0)
          PD.searchQ=string.lower(list[1].text)
          local rows={};PD.RowsRecipe(rows);local n=0
          for _,r in ipairs(rows)do if r.spell then assert(PD.SearchHit(r));n=n+1 end end
          assert(n>0)
          PD.searchQ='no-such-enchant';rows={};PD.RowsRecipe(rows)
          for _,r in ipairs(rows)do assert(not r.spell)end
          local buttons=PD.RecipeTool(ns.ProfRecipes.enchanting);local hasSource=false
          for _,b in ipairs(buttons)do if b.key==PD.DD_MONEY then hasSource=true;assert(b.on and b.dd)end end
          assert(hasSource)
        ''')

    def test_currency_filter_combines_enchants_and_favor_rewards(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                self.boot(locale)
                self.lua.execute('''
                  local d=ns.ProfRecipes.enchanting;local counts=PD.CurCounts(d)
                  for _,entry in ipairs(PD.RecipeCurItems(d))do
                    if type(entry.v)=='number' then
                      PD.moneyKey=entry.v;PD.RecipeTool(d)
                      local list=PD.RecipeList(1000)
                      assert(#list==counts[entry.v],tostring(entry.v)..':'..#list..'/'..counts[entry.v])
                    end
                  end
                ''')


if __name__ == '__main__':
    unittest.main()
