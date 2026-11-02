"""Reserve budgets: native solver, procurement, frozen execution and shopping."""
import math
import unittest
import test_prof_route_plans as lifecycle
import test_prof_ui_fusion as ui

HELPERS = r'''
function reserveFixture(nested)
 local s=fixture();s.considerAuctionSupply=false
 local r=s.recipes[1];r.yellow=1;r.green=1;r.grey=100
 if nested then
  s.recipes[2]={profession='mining',spell=201,item=11,count=2,mats={{12,1}},learn=1,yellow=1,green=1,grey=1}
  s.professions.mining={cur=300,max=300};s.known['mining:201']=true;s.prices={[11]=100,[12]=7}
 end
 return s
end
function reserveSolve(s,mode)
 local r,j=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s or reserveFixture(),start=1,target=3,reserveMode=mode or 'ample'})
 assert(not j.error,tostring(j.error));assert(r.reserve,'missing final reserve')
 return r,j
end
function sameBase(a,b)
 assert(a.total==b.total and a.crafts==b.crafts and #a.executionSteps==#b.executionSteps)
 for i,s in ipairs(a.executionSteps)do
  local t=b.executionSteps[i]
  for k=1,4 do assert(s[k]==t[k])end
  assert(s.profession==t.profession)
  for id,n in pairs(s.requiredOutputs)do assert(t.requiredOutputs[id]==n)end
 end
end
'''


class ReserveTests(unittest.TestCase):
    def setUp(self):
        lifecycle.NativeRoutePlansTests.setUp(self)
        self.load((lifecycle.ROOT/'Core/ProfReserve.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(HELPERS)

    def test_hitting_time_matches_independent_binomial_tail(self):
        self.lua.execute('ns.ProfEconomy.Gain=function()return .5 end')
        fn=self.lua.eval('function(c)return ns.ProfReserve.Attempts({learn=1},1,11,c)end')
        for confidence in (.9,.95,.99):
            expected=next(n for n in range(10,100) if sum(math.comb(n,k) for k in range(10,n+1))/2**n>=confidence)
            self.assertEqual(fn(confidence),expected)

    def test_orange_zero_grey_unknown_and_bounded_work(self):
        self.lua.execute('''
          local r=fixture().recipes[1]
          assert(ns.ProfReserve.Attempts(r,1,10,.95)==9)
          assert(ns.ProfReserve.Attempts(r,300,301,.95)==nil)
          r.yellow=1;r.green=1
          local n,reason=ns.ProfReserve.Attempts(r,1,10,.95,function()return false end)
          assert(n==nil and reason=='budget')
          local p=reserveSolve(fixture());assert(p.reserve.total==0 and p.reserve.steps[1].extraCrafts==0)
        ''')

    def test_modes_preserve_base_route_cost_and_recovery(self):
        self.lua.execute('''
          local off=reserveSolve(nil,'off');local standard=reserveSolve(nil,'standard');local ample=reserveSolve()
          sameBase(off,standard);sameBase(off,ample)
          assert(off.reserve.total==0 and #off.reserve.mats==0)
          assert(ample.reserve.steps[1].extraCrafts>=standard.reserve.steps[1].extraCrafts)
          assert(standard.reserve.total>0 and ample.reserve.coverageComplete and ample.reserve.complete)
          assert(ample.recoveryTotal==off.recoveryTotal and ample.netTotal==off.netTotal)
        ''')

    def test_failure_budget_is_shared_across_route(self):
        self.lua.execute('''
          local gain=ns.ProfEconomy.Gain;ns.ProfEconomy.Gain=function()return .5 end
          local r={profession='alchemy',spell=101,item=10,count=1,mats={{11,1}},learn=1}
          local s={professions={alchemy={cur=1,max=300}},prices={[11]=1},considerAuctionSupply=false}
          local plan={slug='alchemy',start=1,actions={},executionSteps={}}
          for i=1,2 do
            local id='s'..i
            plan.actions[#plan.actions+1]={type='buy',id='b'..i,item=11,count=2,cost=2,source='ah'}
            plan.actions[#plan.actions+1]={type='craft',id=id,inputs={{11,2}},outputs={{10,2}}}
            plan.executionSteps[i]={i,i+1,101,2,segmentID=id,actionIDs={id},profession='alchemy',recipe=r,
              expectedGain=1,goalSkill=i+1,expectedCrafts=2,item=10,outputMin=1}
          end
          local reserve=ns.ProfReserve.Build(plan,s,{reserveMode='ample'})
          assert(reserve.steps[1].extraCrafts==4 and reserve.steps[2].extraCrafts==4)
          assert((1-.5^6)^2>=.95)
          ns.ProfEconomy.Gain=gain
        ''')

    def test_nested_reserve_reuses_producer_and_pack_surplus_once(self):
        self.lua.execute('''
          local r=reserveSolve(reserveFixture(true));local producer,consumer=r.executionSteps[1],r.executionSteps[2]
          assert(producer.profession=='mining' and producer.reserve.extraCrafts>0)
          assert(consumer.reserve.extraCrafts>0)
          local prepared=producer.reserve.requiredOutputs[11]
          assert(prepared==consumer.reserve.extraCrafts)
          local spare=producer[4]*2-producer.requiredOutputs[11]
          assert(producer.reserve.extraCrafts==math.ceil(math.max(0,prepared-spare)/2))
          assert(#r.reserve.materials==1 and r.reserve.materials[1].id==12)
          assert(r.reserve.materials[1].count==producer.reserve.extraCrafts)
        ''')

    def test_certain_orange_steps_do_not_spend_the_failure_budget(self):
        self.lua.execute('''
          ns.ProfEconomy.Gain=function(r)return r.certain and 1 or .5 end
          local r=reserveSolve(nil,'off');local a=r.executionSteps[1]
          a[1]=1;a[2]=2;a.goalSkill=2;a.expectedGain=1;a[4]=2;a.expectedCrafts=2
          local orange=ns.ProfEconomy.Copy(a)
          orange.segmentID='orange';orange.profession='mining';orange.recipe.certain=true
          orange[4]=1;orange.expectedCrafts=1;orange.recipe.mats={};orange.actionIDs={}
          r.executionSteps[2]=orange
          local reserve=ns.ProfReserve.Build(r,reserveFixture(),{reserveMode='ample'})
          assert(reserve.steps[1].extraCrafts==3 and reserve.steps[2].extraCrafts==0)
        ''')

    def test_vendor_pack_surplus_reduces_extra_purchase_budget(self):
        self.lua.execute('''
          local s=reserveFixture();s.prices={};s.offers={[11]={{npcID=1,price=10,quantity=10,unlimited=true}}}
          local r=reserveSolve(s);local extra=r.reserve.steps[1].extraCrafts
          assert(extra>0 and r.mats[1].count==10)
          assert(r.reserve.materials[1].count==extra)
          assert(r.reserve.total==0 and r.reserve.materials[1].spare==extra)
        ''')

    def test_limited_auction_budget_does_not_take_base_or_formula_stock(self):
        self.lua.execute('''
          local s=reserveFixture();s.considerAuctionSupply=true
          s.auctionSupply={[11]={quantity=5,complete=true,observedAt=1000,source='client-auction-results',ownerExcluded=true}}
          local r=reserveSolve(s);assert(r.total==35 and r.targetReached)
          assert(not r.reserve.complete and r.reserve.materials[1].uncovered>0)
          assert(r.reserve.steps[1].extraCrafts>0)
        ''')

    def test_reserve_quotes_remain_frozen(self):
        self.lua.execute('''
          local r,j=reserveSolve();local old=r.reserve.total
          j.snap.prices[11]=7000
          local fresh=ns.ProfReserve.Build(r,j.snap,{reserveMode='ample'})
          assert(fresh.total==old and r.total==35)
        ''')

    def test_seed_inventory_offsets_only_unallocated_surplus(self):
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=reserveFixture(),start=1,target=3,
            executionInventory={[11]=7},reserveMode='ample'})
          assert(r.total==0 and r.reserve.steps[1].extraCrafts==3)
          assert(r.reserve.materials[1].count==3 and r.reserve.materials[1].spare==2)
          assert(r.reserve.total==7 and r.reserve.materials[1].purchaseNeed==1)
        ''')

    def test_missing_reserve_quote_does_not_make_base_route_infeasible(self):
        self.lua.execute('''
          local s=reserveFixture();s.prices={}
          local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=3,
            executionInventory={[11]=5},reserveMode='ample'})
          assert(r.feasible and r.targetReached and r.total==0)
          assert(not r.reserve.complete and not r.reserve.priced and r.reserve.total==nil)
        ''')

    def test_frozen_reserve_and_spent_allowance_survive_executor_reload(self):
        self.lua.execute('''
          local r=reserveSolve();local run=ns.ProfExecution.StartNew('alchemy',r)
          for i=1,r.executionSteps[1][4]+1 do ns.ProfExecution.RecordAttempt('alchemy',101,'cast'..i)end
          frozenID=run.planID;frozenLimit=ns.ProfExecution.Progress('alchemy',1).attemptLimit
        ''')
        self.load((lifecycle.ROOT/'Core/ProfExecution.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          assert(ns.ProfExecution.GetRun('alchemy').planID==frozenID)
          local p=ns.ProfExecution.Progress('alchemy',1)
          assert(p.reserveRemaining==2 and p.attemptLimit==frozenLimit)
        ''')

    def test_reserve_finalization_can_yield_without_publishing_an_empty_result(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(reserveFixture())end
          local original=ns.ProfReserve.Build;local called=0
          ns.ProfReserve.Build=function(...)
            called=called+1;coroutine.yield('reserve_test');return original(...)
          end
          local result=finish('alchemy',{start=1,target=3,reserveMode='ample'})
          assert(result.status=='complete' and result.total==35 and result.reserve.total==21)
          assert(called==1 and not ns.ProfRouteAuto.HasWork('alchemy'))
        ''')

    def test_later_output_cannot_erase_earlier_reserve_purchase(self):
        self.lua.execute('''
          local plan={reserve={mode='ample'},executionSteps={
            {1,2,1,1,segmentID='first',recipe={mats={{11,1}}},reserve={extraCrafts=2}},
            {2,3,2,1,segmentID='later',item=11,outputMin=1,recipe={mats={{12,1}},item=11,count=1},reserve={extraCrafts=2}}}}
          local need=ns.ProfReserve.Remaining(plan)
          assert(need[11]==2 and need[12]==2)
        ''')

    def test_formula_uses_the_same_auction_budget_but_gets_no_buffer(self):
        self.lua.execute('''
          local plan,job=reserveSolve(nil,'off')
          plan.actions[#plan.actions+1]={type='formula',id='formula',item=11,count=1,cost=7,source='ah'}
          job.snap.considerAuctionSupply=true;job.snap.auctionSupply={[11]={quantity=6,complete=true}}
          local reserve=ns.ProfReserve.Build(plan,job.snap,{reserveMode='ample'})
          assert(reserve.materials[1].purchaseNeed==3 and reserve.materials[1].uncovered==3)
          assert(reserve.total==21 and not reserve.complete)
        ''')

    def test_conversion_reserve_uses_original_conversion_and_whole_units(self):
        self.lua.execute('''
          local s=fixture();s.professions={enchanting={cur=1,max=300}};s.essenceConversions=true
          s.recipes={{profession='enchanting',spell=101,item=10,count=1,mats={{10938,1}},learn=1,yellow=1,green=1,grey=100}}
          s.known={['enchanting:101']=true};s.prices={[10938]=10,[10939]=2};s.considerAuctionSupply=false
          local r,j=ns.ProfRouteAuto.Compute('enchanting',{snapshot=s,start=1,target=4,reserveMode='ample'})
          assert(not j.error,tostring(j.error));assert(r.reserve and r.reserve.complete)
          local extra=false
          for _,seg in ipairs(r.executionSteps)do
            if seg.kind=='essence_conversion' and seg.reserve.extraCrafts>0 then
              extra=true;assert(seg.reserve.extraCrafts==math.floor(seg.reserve.extraCrafts))
            end
          end
          assert(extra)
          for _,m in ipairs(r.reserve.materials)do assert(m.id==10939)end
        ''')

    def test_preparation_does_not_change_base_quantities_and_can_be_skipped(self):
        self.lua.execute('''
          skills.mining={cur=300,max=300}
          local r=reserveSolve(reserveFixture(true));local original=r.executionSteps[1].requiredOutputs[11]
          local run=assert(ns.ProfExecution.StartNew('alchemy',r));local a=run.plan.executionSteps[1]
          assert(a.requiredOutputs[11]==original and a.reserve.requiredOutputs[11]>0)
          local p=ns.ProfExecution.Progress('alchemy',1)
          assert(p.requiredOutputs==original+a.reserve.requiredOutputs[11])
          assert(ns.ProfExecution.SkipReserve('alchemy'))
          assert(ns.ProfExecution.Progress('alchemy',1).requiredOutputs==original)
          assert(r.executionSteps[1].requiredOutputs[11]==original)
        ''')

    def test_reserve_allowance_is_spent_without_replenishing_and_stops_at_goal(self):
        self.lua.execute('''
          local r=reserveSolve();local run=assert(ns.ProfExecution.StartNew('alchemy',r));local seg=run.plan.executionSteps[1]
          local extra=seg.reserve.extraCrafts;bag[11]=100
          for i=1,seg[4] do ns.ProfExecution.RecordAttempt('alchemy',101,'base'..i)end
          local p=ns.ProfExecution.Progress('alchemy',1)
          assert(p.reserveRemaining==extra and not p.exhausted)
          assert(ns.ProfExecution.SafeCraftCount('alchemy',seg.segmentID,100)==extra)
          ns.ProfExecution.RecordAttempt('alchemy',101,'extra1')
          p=ns.ProfExecution.Progress('alchemy',1);assert(p.reserveRemaining==extra-1)
          skills.alchemy.cur=3;assert(ns.ProfExecution.Progress('alchemy',1).complete)
          assert(ns.ProfExecution.SafeCraftCount('alchemy',seg.segmentID,100)==0)
        ''')

    def test_future_base_inventory_is_protected_from_extra_crafts(self):
        self.lua.execute('''
          local r=reserveSolve();local a=r.executionSteps[1]
          local b=ns.ProfEconomy.Copy(a);b.segmentID='future';b[1]=3;b[2]=4;b.goalSkill=4;b[3]=102;b.recipe.spell=102
          b[4]=2;b.expectedCrafts=2;b.reserve={extraCrafts=0,requiredOutputs={},allocations={}}
          r.executionSteps[2]=b
          local run=assert(ns.ProfExecution.StartNew('alchemy',r));a=run.plan.executionSteps[1]
          bag[11]=1
          assert(ns.ProfExecution.SafeCraftCount('alchemy',a.segmentID,10)==1,'missing later purchases blocked base work')
          for i=1,a[4] do ns.ProfExecution.RecordAttempt('alchemy',101,'base'..i)end
          bag[11]=2
          assert(ns.ProfExecution.SafeCraftCount('alchemy',a.segmentID,10)==0)
          bag[11]=3;assert(ns.ProfExecution.SafeCraftCount('alchemy',a.segmentID,10)==1)
        ''')

    def test_manual_supplement_does_not_restore_spent_reserve(self):
        self.lua.execute('''
          local r=reserveSolve();local xp=ns.ProfExecution;local run=xp.StartNew('alchemy',r)
          local seg=run.plan.executionSteps[1];local limit=xp.Progress('alchemy',1).attemptLimit
          for i=1,limit do xp.RecordAttempt('alchemy',101,'spent'..i)end
          local capture=ns.ProfEconomy.Capture;run.plan.executionOptions={recoveryEnabled=false}
          ns.ProfEconomy.Capture=function(slug,opts,tick)
            local input=ns.ProfEconomy.Copy(opts);input.snapshot=input.snapshot or reserveFixture()
            return capture(slug,input,tick)
          end
          local supplement=assert(xp.CalculateSupplement('alchemy'))
          for i=1,1000 do if not supplement.inFlight then break end;xp.Pump('alchemy')end
          assert(supplement.appended and supplement.extraCrafts>0)
          local p=xp.Progress('alchemy',seg.segmentID)
          assert(p.reserveRemaining==0 and p.baseRemaining==supplement.extraCrafts)
          bag[11]=100
          assert(xp.SafeCraftCount('alchemy',seg.segmentID,100)==supplement.extraCrafts)
          local need=ns.ProfReserve.Remaining(run.plan,{[seg.segmentID]=limit})
          assert((need[11] or 0)==0)
          xp.SkipReserve('alchemy')
          p=xp.Progress('alchemy',seg.segmentID)
          assert(p.baseRemaining==supplement.extraCrafts and p.reserveRemaining==0)
        ''')

    def test_stopping_partly_spent_reserve_removes_only_unused_allowance(self):
        self.lua.execute('''
          local r=reserveSolve();local xp=ns.ProfExecution;local run=xp.StartNew('alchemy',r)
          local seg=run.plan.executionSteps[1]
          for i=1,seg[4]+1 do xp.RecordAttempt('alchemy',101,'spent'..i)end
          xp.SkipReserve('alchemy');local p=xp.Progress('alchemy',seg.segmentID)
          assert(p.reserveRemaining==0 and p.baseRemaining==0 and p.attemptLimit==seg[4]+1)
          xp.SkipReserve('alchemy');assert(xp.Progress('alchemy',seg.segmentID).attemptLimit==p.attemptLimit)
        ''')

    def test_next_card_cannot_take_materials_from_an_unfinished_earlier_step(self):
        self.lua.execute('''
          local r=reserveSolve();local a=r.executionSteps[1]
          local b=ns.ProfEconomy.Copy(a);b.segmentID='next';b[3]=102;b.recipe.spell=102
          b[4]=2;b.expectedCrafts=2;b.reserve={extraCrafts=0,requiredOutputs={},allocations={}}
          r.executionSteps[2]=b
          local run=assert(ns.ProfExecution.StartNew('alchemy',r));b=run.plan.executionSteps[2]
          bag[11]=a[4]
          assert(ns.ProfExecution.SafeCraftCount('alchemy',b.segmentID,10)==0)
          bag[11]=a[4]+1
          assert(ns.ProfExecution.SafeCraftCount('alchemy',b.segmentID,10)==1)
        ''')

    def test_skeleton_keeps_only_mode_and_rebuilds_reserve(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(reserveFixture())end
          opts={start=1,target=3,reserveMode='ample'};original=finish('alchemy',opts)
          local db=DungeonsForeverDB.prof.routePlans.characters['Test-Realm']
          local skel=db.routes[db.active.alchemy].skeleton
          assert(skel.options.reserveMode=='ample' and skel.reserve==nil and skel.steps[1].reserve==nil)
        ''')
        self.load((lifecycle.ROOT/'Core/ProfRoutePlans.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local restored=finish('alchemy',opts);assert(restored.fromSkeleton)
          sameBase(original,restored);assert(restored.reserve.total==original.reserve.total)
        ''')

    def test_mode_change_rebuilds_same_route_without_changing_active_run(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(reserveFixture())end
          local opts={start=1,target=3,reserveMode='ample'}
          local before=finish('alchemy',opts);local run=ns.ProfExecution.StartNew('alchemy',before)
          local frozen=run.plan.reserve.total
          ns.ProfRouteAuto.ChangeReserveMode('alchemy','off')
          finish('alchemy',{start=1,target=3,reserveMode='off'})
          local after=ns.ProfRouteAuto.Peek('alchemy')
          sameBase(before,after);assert(after.reserve.mode=='off')
          assert(run.plan.reserve.total==frozen and run.plan.reserve.mode=='ample')
        ''')


class ReserveShoppingTests(unittest.TestCase):
    def setUp(self):
        ui.ProfessionUIFusionTests.boot(self,'zhCN')
        self.load((lifecycle.ROOT/'Core/ProfSolverCapture.lua').read_text(encoding='utf-8-sig'))
        self.load((lifecycle.ROOT/'Core/ProfReserve.lua').read_text(encoding='utf-8-sig'))
        self.load((lifecycle.ROOT/'Core/ProfFollow.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(HELPERS)
        self.lua.execute('''
          ns.ProfFollow.Paint=function()end
          ns.ProfEconomy.Known=function()return true end
          ns.AuctionBridge={DoImport=function(_,items)imported=items end}
        ''')

    def test_bag_is_deducted_once_from_base_plus_reserve(self):
        self.lua.execute('''
          local r=reserveSolve();bag[11]=6
          local list=ns.ProfFollow.ShoppingForPlan('alchemy',r);assert(#list==1)
          local row=list[1]
          assert(row.baseNeed==5 and row.reserveNeed==3 and row.need==8)
          assert(row.purchaseCount==2 and row.baseMissing==0 and row.reserveMissing==2)
          assert(row.purchaseCost==14)
          local rows={};PD.RowsReserveShopping(rows,r)
          local found=false;for _,x in ipairs(rows)do if x.purchaseCount==2 then found=true end end;assert(found)
        ''')

    def test_prepared_intermediates_do_not_trigger_raw_material_refill(self):
        self.lua.execute('''
          skills.mining={cur=300,max=300}
          local r=reserveSolve(reserveFixture(true));local run=ns.ProfExecution.StartNew('alchemy',r)
          local a=run.plan.executionSteps[1]
          bag[11]=a.requiredOutputs[11]+a.reserve.requiredOutputs[11]
          ns.ProfExecution.Sync('alchemy')
          assert(run.currentIndex==2)
          local rows=ns.ProfFollow.ShoppingForPlan('alchemy',run.plan)
          for _,row in ipairs(rows)do assert(row.id~=12 or row.purchaseCount==0,'prepared stock was bought again')end
        ''')

    def test_used_allowance_does_not_restore_full_shopping_buffer(self):
        self.lua.execute('''
          local r=reserveSolve();local run=ns.ProfExecution.StartNew('alchemy',r)
          local seg=run.plan.executionSteps[1]
          for i=1,seg[4]+1 do ns.ProfExecution.RecordAttempt('alchemy',101,'use'..i)end
          bag[11]=2
          local rows=ns.ProfFollow.ShoppingForPlan('alchemy',run.plan)
          assert(#rows==1 and rows[1].reserveNeed==2 and rows[1].purchaseCount==0)
        ''')

    def test_settings_are_profession_scoped_and_shopping_renders_both_modes(self):
        self.lua.execute('''
          assert(PD.SettingRaw('autoReserveMode','alchemy')=='ample')
          PD.SetSettingRaw('autoReserveMode','off','alchemy')
          assert(PD.SettingRaw('autoReserveMode','mining')=='ample')
          local rows={};PD.RowsSettings(rows)
          local found=false;for _,row in ipairs(rows)do if row.text=='备料余量' then found=true;assert(row.act)end end;assert(found)
          for _,slug in ipairs({'first-aid','poisons'})do
            PD.cur=slug;local fixedRows={};PD.RowsSettings(fixedRows)
            for _,row in ipairs(fixedRows)do assert(row.text~='备料余量')end
          end
          PD.cur='alchemy'
          local r=reserveSolve()
          for _,group in ipairs({false,true})do PD.shopGroup=group;PD.RowsAutoShop({},r)end
        ''')

    def test_seed_funded_reserve_shows_zero_to_buy_and_unknown_inventory_stays_unknown(self):
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=reserveFixture(),start=1,target=3,
            executionInventory={[11]=8},reserveMode='ample'})
          bag[11]=8
          local list=ns.ProfFollow.ShoppingForPlan('alchemy',r)
          assert(#list==1 and list[1].purchaseCount==0 and list[1].baseNeed==5 and list[1].reserveNeed==3)
          C_Item.GetItemCount=function()return nil end
          list=ns.ProfFollow.ShoppingForPlan('alchemy',r)
          assert(list[1].inventoryUnknown and list[1].purchaseCount==nil)
        ''')

    def test_auction_import_uses_combined_shortage_without_duplicate_base_rows(self):
        self.lua.execute('''
          local r=reserveSolve();ns.ProfExecution.StartNew('alchemy',r);bag[11]=6
          ns.ProfFollow.ImportShoppingList('alchemy','Alchemy')
          assert(#imported==1 and imported[1].need==2)
        ''')


if __name__=='__main__':unittest.main()
