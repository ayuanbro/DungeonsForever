"""Lua loading, asynchronous publication and client-first recipe integration."""
import os
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

for p in (Path(os.environ.get("TEMP", "/tmp"))/"df-lua-runtime", Path.home()/"AppData/Local/Temp/df-lua-runtime"):
    sys.path.insert(0,str(p))
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]
MOCKS=r'''
ns={LoadForeverPages=true,L=setmetatable({}, {__index=function(_,k) return k end})}
frames={}; queue={}; timers={}
function CreateFrame()
  local f={events={}}; function f:RegisterEvent(e) self.events[e]=true end
  function f:SetScript(k,v) self[k]=v end
  frames[#frames+1]=f; return f
end
C_Timer={After=function(_,fn) timers[#timers+1]=fn end}
ns.IdleJobs={Add=function(fn) queue[#queue+1]=fn end}
function time() return 1000 end
function UnitName() return 'Test' end
function GetRealmName() return 'Realm' end
function fixture()
  return {recipes={{profession='alchemy',spell=101,item=10,count=1,learn=1,yellow=20,green=30,grey=40,mats={{11,1}},cooldown=false}},
    inventory={},professions={alchemy={cur=1,max=300}},known={['alchemy:101']=true},prices={[11]=7}}
end
function finish(slug,opts)
  local r=ns.ProfRouteAuto.Get(slug,opts)
  for i=1,100 do
    ns.ProfRouteAuto.Pump(slug)
    r=ns.ProfRouteAuto.Get(slug,opts)
    if r.status~='searching' then return r end
  end
  error('job did not finish')
end
'''

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.load=self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        for name in ("ProfEconomy.lua","ProfRouteSolver.lua","ProfRouteAuto.lua"):
            self.load(str(ROOT/"Core"/name))

    def test_get_only_schedules_work_and_returns_pending_snapshot(self):
        self.lua.execute("""
          local o={snapshot=fixture(),start=1,target=2}
          local r=ns.ProfRouteAuto.Get('alchemy',o)
          assert(r.status=='searching' and not r.feasible and #queue==1)
          assert(ns.ProfRouteAuto.Get('alchemy',o)==r and #queue==1)
          r=finish('alchemy',o)
          assert(r.feasible and r.total==7 and r.status=='complete' and r.revision>0)
        """)

    def test_cancel_resume_and_invalidation_do_not_publish_old_results(self):
        self.lua.execute("""
          local ra=ns.ProfRouteAuto
          local o={snapshot=fixture(),start=1,target=2}
          local updates={}; ra.OnPlanChanged(function(slug,r) if r then updates[#updates+1]=r end end)
          ra.Get('alchemy',o); ra.Cancel('alchemy')
          assert(ra.Get('alchemy',o).status=='stopped')
          ra.Pump('alchemy'); ra.Continue('alchemy')
          local done=finish('alchemy',o); assert(done.feasible and done.total==7)
          local oldPump=queue[1]
          ra.Invalidate()
          assert(ra.Get('alchemy',o)==done and done.stale,'ordinary invalidation discarded saved route')
          local pending=ra.Recalculate('alchemy',o); assert(pending.status=='searching')
          local n=#updates; oldPump(); assert(#updates==n,'stale generation published')
          assert(ra.Get('alchemy',o)==pending)
          assert(finish('alchemy',o).revision>done.revision)
        """)

    def test_cache_keys_include_recipe_policies_and_secondary_option(self):
        self.lua.execute("""
          local s=fixture(); local a={snapshot=s,start=1,target=2}
          local b={snapshot=s,start=1,target=2,exclusions={['alchemy:101']='ban'}}
          assert(finish('alchemy',a).feasible)
          local r=finish('alchemy',b); assert(not r.feasible)
          assert(ns.ProfRouteAuto.Get('alchemy',a).feasible,'other option job was cancelled')
          local c={snapshot=s,start=1,target=2,allowSecondaryLeveling=true}
          assert(ns.ProfRouteAuto.Get('alchemy',c).status=='searching')
        """)

    def test_finished_result_cannot_be_reopened_by_cancel_continue(self):
        self.lua.execute("""
          local ra=ns.ProfRouteAuto; local o={snapshot=fixture(),start=1,target=2}
          local r=finish('alchemy',o); assert(r.searchComplete)
          ra.Cancel('alchemy'); ra.Continue('alchemy'); ra.Pump('alchemy')
          assert(ra.Get('alchemy',o)==r and r.status=='complete')
        """)

    def live_capture_fixture(self):
        self.lua.execute("""
          captures=0; livePrice=7; liveSkill=1
          ns.ProfEconomy.Capture=function(slug,opts)
            captures=captures+1; local s=fixture()
            s.prices[11]=livePrice; s.professions.alchemy.cur=liveSkill
            return ns.ProfEconomy.Index(s)
          end
        """)

    def test_live_route_reuses_quote_until_explicit_recalculate(self):
        self.live_capture_fixture()
        self.lua.execute("""
          local ra=ns.ProfRouteAuto; local o={start=1,target=2}
          local r=finish('alchemy',o); assert(r.total==7 and captures==1)
          local jobs=#queue; livePrice=99; liveSkill=2
          ra.Invalidate('prices')
          local cached=ra.Get('alchemy',{start=2,target=2})
          assert(cached==r and cached.total==7 and cached.start==1 and cached.stale)
          assert(#queue==jobs and captures==1,'opening or input events restarted calculation')
          ra.Recalculate('alchemy',o)
          local fresh=finish('alchemy',o)
          assert(fresh.total==99 and captures==2 and not fresh.stale)
        """)

    def test_saved_route_restores_after_module_reload_without_scanning(self):
        self.live_capture_fixture()
        self.lua.execute("""
          savedOptions={start=1,target=2}; original=finish('alchemy',savedOptions)
          assert(DungeonsForeverDB.prof.routeCache['Test-Realm'].active.alchemy)
          jobsBeforeReload=#queue
          livePrice=99; liveSkill=2
        """)
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute("""
          local r=ns.ProfRouteAuto.Get('alchemy',{start=2,target=2})
          assert(r.cached and r.total==7 and r.start==1 and r.status=='complete')
          assert(captures==1 and #queue==jobsBeforeReload)
          assert(#r.actions>0 and #r.steps==1 and #r.executionSteps==1)
        """)

    def test_old_empty_failure_recalculates_once_without_discarding_valid_cached_routes(self):
        self.live_capture_fixture()
        self.lua.execute('''
          local r=finish('alchemy',{start=1,target=2})
          local cache=DungeonsForeverDB.prof.routeCache['Test-Realm']
          local old=cache.routes[cache.active.alchemy].result
          old.steps={};old.executionSteps={};old.feasible=false;old.targetReached=false
          old.status='incomplete';old.emptyResultRevision=nil
        ''')
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute('''
          assert(ns.ProfRouteAuto.Get('alchemy',{start=1,target=2}).status=='searching')
          local r=finish('alchemy',{start=1,target=2})
          assert(r.targetReached and #r.steps==1 and captures==2 and r.emptyResultRevision==2)
        ''')
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
          assert(r.cached and #r.steps==1 and captures==2)
        ''')

    def legacy_vendor_cache_fixture(self):
        self.lua.execute('''
          captures=0
          ns.ProfEconomy.Capture=function()
            captures=captures+1
            local s=fixture();s.prices[11]=70
            s.vendorItems={[11]=true};s.vendorSuppliers={[11]={{npcID=77}}}
            s.offers={[11]=ns.ProfItemPrices and ns.ProfItemPrices.GetOffers(11)
              or {{npcID=77,price=7,quantity=1,unlimited=true,reference=true,source='wowhead-forever'}}}
            return ns.ProfEconomy.Index(s)
          end
          local r=finish('alchemy',{start=1,target=2})
          assert(r.vendorQuoteRevision==4 and r.total==7 and r.costComplete)
          local cache=DungeonsForeverDB.prof.routeCache['Test-Realm']
          oldVendorCache=cache.routes[cache.active.alchemy].result
          oldVendorCache.vendorQuoteRevision=2
          oldVendorCache.mats[1].quoteSource='wowhead-forever'
          jobsBeforeVendorReload=#queue
          ns.DB=function() return DungeonsForeverDB end
        ''')

    def install_synthetic_vendor_quote_fixture(self):
        self.lua.execute('''
          ns.ProfItemsMeta={schemaVersion=2,sources={csv={sha256='quotes-a'}}}
          ns.ProfItems={[11]={item_id=11,VendorStackCount=1,offers={
            [77]={npc_id=77,cost_copper=3,cost_text='3c',stock=-1,price_source='wowhead'}}}}
        ''')
        self.load(str(ROOT/'Core'/'ProfItemPrices.lua'))

    def test_old_npc_quotes_require_manual_recalculation_without_publishing_old_amounts(self):
        self.legacy_vendor_cache_fixture()
        self.install_synthetic_vendor_quote_fixture()
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
          assert(r.cached and r.vendorQuoteRevision==4 and r.stale and r.staleReason=='vendor-quotes')
          assert(r.status=='recalculate_required' and not r.feasible and r.total==0 and r.vendorTotal==0)
          assert(#r.steps==0 and #r.actions==0 and #r.mats==0)
          assert(#r.diagnostics==1 and r.diagnostics[1].code=='vendorQuoteChanged')
          assert(ns.ProfEconomy.DiagnosticText(r.diagnostics[1]):find('请重新计算',1,true))
          assert(captures==1 and #queue==jobsBeforeVendorReload,'opening recaptured or queued a route search')
          assert(oldVendorCache.vendorQuoteRevision==2 and oldVendorCache.total==7 and #oldVendorCache.steps==1)
          assert(oldVendorCache.mats[1].quoteSource=='wowhead-forever','historical execution data changed')
          ns.ProfRouteAuto.Recalculate('alchemy',{start=1,target=2})
          local fresh=finish('alchemy',{start=1,target=2})
          assert(fresh.total==3 and fresh.costComplete and fresh.referencePrices and #fresh.diagnostics==0)
          assert(fresh.vendorQuoteRevision==4 and fresh.vendorQuoteData=='quotes-a' and not fresh.stale and captures==2)
        ''')

    def test_old_npc_quotes_without_bundled_price_still_wait_for_manual_recalculation(self):
        self.legacy_vendor_cache_fixture()
        self.load(str(ROOT/'Core'/'ProfItemPrices.lua'))
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
          assert(r.cached and r.total==0 and r.vendorQuoteRevision==4 and r.status=='recalculate_required')
          assert(#r.diagnostics==1 and r.diagnostics[1].code=='vendorQuoteChanged')
          assert(not r.costComplete and captures==1 and #queue==jobsBeforeVendorReload)
        ''')

    def test_rejected_bundled_offer_cannot_restore_an_old_npc_quote(self):
        for rejection in ('stock=0', 'currency_kind="item"', 'currency_id=0'):
            with self.subTest(rejection=rejection):
                self.setUp()
                self.legacy_vendor_cache_fixture()
                self.install_synthetic_vendor_quote_fixture()
                self.lua.execute('''
                  ns.ProfItems[11].offers[77].'''+rejection+'''
                ''')
                self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
                self.lua.execute('''
                  local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
                  assert(r.diagnostics[1].code=='vendorQuoteChanged' and r.total==0 and r.vendorQuoteRevision==4)
                  assert(r.status=='recalculate_required' and #r.mats==0)
                  assert(captures==1 and #queue==jobsBeforeVendorReload)
                ''')

    def test_ah_only_cached_route_is_not_reset_by_npc_price_migration(self):
        self.legacy_vendor_cache_fixture()
        self.install_synthetic_vendor_quote_fixture()
        self.lua.execute('''
          oldVendorCache.mats[1].source='ah';oldVendorCache.mats[1].vendor=false
          oldVendorCache.vendorTotal=0;oldVendorCache.ahTotal=7
          for _,action in ipairs(oldVendorCache.actions) do
            if action.type=='buy' then action.source='ah' end
          end
        ''')
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
          assert(r.cached and r.total==7 and #r.steps==1 and r.status=='complete')
          assert(#r.diagnostics==0 and r.ahTotal==7 and r.vendorTotal==0)
          assert(captures==1 and #queue==jobsBeforeVendorReload)
        ''')

    def test_old_npc_quote_gate_does_not_depend_on_vendor_module_initialization(self):
        self.legacy_vendor_cache_fixture()
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
          assert(r.cached and r.diagnostics[1].code=='vendorQuoteChanged' and r.total==0)
          assert(r.vendorQuoteRevision==4 and captures==1 and #queue==jobsBeforeVendorReload)
        ''')
        self.install_synthetic_vendor_quote_fixture()
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
          assert(r.vendorQuoteRevision==4 and r.diagnostics[1].code=='vendorQuoteChanged' and r.total==0)
          assert(captures==1 and #queue==jobsBeforeVendorReload)
        ''')

    def test_current_provider_npc_route_restores_without_recapturing(self):
        self.legacy_vendor_cache_fixture()
        self.lua.execute('''
          oldVendorCache.vendorQuoteRevision=4
          oldVendorCache.mats[1].quoteSource='wowhead-forever'
        ''')
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
          assert(r.cached and r.total==7 and r.costComplete and r.vendorQuoteRevision==4)
          assert(r.status=='complete' and #r.steps==1 and #r.diagnostics==0)
          assert(captures==1 and #queue==jobsBeforeVendorReload)
        ''')

    def test_changed_prof_items_hash_gates_current_npc_plan_and_keeps_history(self):
        self.legacy_vendor_cache_fixture()
        self.install_synthetic_vendor_quote_fixture()
        self.lua.execute('''
          oldVendorCache.vendorQuoteRevision=4
          oldVendorCache.vendorQuoteData='quotes-a'
          ns.ProfItemsMeta.sources.csv.sha256='quotes-b'
          DungeonsForeverDB.prof.execution={history={{result=oldVendorCache,craftsDone=2}}}
        ''')
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
          assert(r.cached and r.vendorQuoteRevision==4 and r.vendorQuoteData=='quotes-b')
          assert(r.status=='recalculate_required' and not r.feasible and r.total==0)
          assert(r.stale and r.staleReason=='vendor-quotes' and #r.steps==0 and #r.mats==0)
          assert(r.diagnostics[1].code=='vendorQuoteChanged')
          assert(captures==1 and #queue==jobsBeforeVendorReload,'hash migration started a search')
          assert(oldVendorCache.vendorQuoteData=='quotes-a' and oldVendorCache.total==7 and #oldVendorCache.steps==1)
          local history=DungeonsForeverDB.prof.execution.history[1]
          assert(history.result==oldVendorCache and history.craftsDone==2)
          ns.ProfRouteAuto.Recalculate('alchemy',{start=1,target=2})
          local fresh=finish('alchemy',{start=1,target=2})
          assert(fresh.total==3 and fresh.vendorQuoteData=='quotes-b' and captures==2)
        ''')

    def test_changed_prof_items_hash_marks_pure_ah_plan_stale_without_gating(self):
        self.lua.execute("ns.ProfItemsMeta={schemaVersion=2,sources={csv={sha256='quotes-a'}}}")
        self.live_capture_fixture()
        self.lua.execute('''
          local r=finish('alchemy',{start=1,target=2})
          assert(r.vendorQuoteRevision==4 and r.vendorQuoteData=='quotes-a' and r.ahTotal==7)
          local cache=DungeonsForeverDB.prof.routeCache['Test-Realm']
          oldAhCache=cache.routes[cache.active.alchemy].result
          jobsBeforeHashReload=#queue
          ns.ProfItemsMeta.sources.csv.sha256='quotes-b';livePrice=99
        ''')
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
          assert(r.cached and r.vendorQuoteRevision==4 and r.status=='complete' and r.feasible)
          assert(r.total==7 and r.ahTotal==7 and r.vendorTotal==0 and #r.steps==1)
          assert(r.stale and r.staleReason=='vendor-quotes' and #r.diagnostics==0)
          assert(captures==1 and #queue==jobsBeforeHashReload)
          assert(oldAhCache.vendorQuoteData=='quotes-a' and not oldAhCache.stale)
          ns.ProfRouteAuto.Recalculate('alchemy',{start=1,target=2})
          local fresh=finish('alchemy',{start=1,target=2})
          assert(fresh.total==99 and fresh.vendorQuoteData=='quotes-b' and not fresh.stale and captures==2)
        ''')

    def test_changed_prof_items_hash_gates_empty_failure_until_manual_recalculation(self):
        for status in ('incomplete', 'infeasible', 'error'):
            with self.subTest(status=status):
                self.setUp()
                self.lua.execute("ns.ProfItemsMeta={schemaVersion=2,sources={csv={sha256='quotes-a'}}}")
                self.live_capture_fixture()
                self.lua.execute('''
                  finish('alchemy',{start=1,target=2})
                  local cache=DungeonsForeverDB.prof.routeCache['Test-Realm']
                  oldEmptyCache=cache.routes[cache.active.alchemy].result
                  oldEmptyCache.steps={};oldEmptyCache.executionSteps={};oldEmptyCache.actions={}
                  oldEmptyCache.mats={};oldEmptyCache.formulas={};oldEmptyCache.total=0
                  oldEmptyCache.vendorTotal=0;oldEmptyCache.ahTotal=0
                  oldEmptyCache.feasible=false;oldEmptyCache.targetReached=false
                  oldEmptyCache.emptyResultRevision=nil
                  jobsBeforeHashReload=#queue
                  ns.ProfItemsMeta.sources.csv.sha256='quotes-b'
                ''')
                self.lua.globals().oldEmptyCache.status = status
                self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
                self.lua.execute('''
                  local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
                  assert(r.cached and r.status=='recalculate_required' and r.total==0)
                  assert(r.vendorQuoteRevision==4 and r.vendorQuoteData=='quotes-b')
                  assert(r.diagnostics[1].code=='vendorQuoteChanged')
                  assert(captures==1 and #queue==jobsBeforeHashReload,'empty failure auto-recalculated after hash change')
                  assert(oldEmptyCache.vendorQuoteData=='quotes-a' and oldEmptyCache.emptyResultRevision==nil)
                  ns.ProfRouteAuto.Recalculate('alchemy',{start=1,target=2})
                  local fresh=finish('alchemy',{start=1,target=2})
                  assert(fresh.feasible and fresh.total==7 and captures==2 and fresh.vendorQuoteData=='quotes-b')
                ''')

    def test_old_npc_formula_quote_also_requires_manual_recalculation(self):
        self.legacy_vendor_cache_fixture()
        self.lua.execute('''
          oldVendorCache.vendorTotal=0
          oldVendorCache.mats={}
          oldVendorCache.actions={}
          oldVendorCache.formulas={{id=99,cost=50,source='vendor'}}
        ''')
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
          assert(r.status=='recalculate_required' and r.total==0 and #r.formulas==0)
          assert(r.diagnostics[1].code=='vendorQuoteChanged')
          assert(captures==1 and #queue==jobsBeforeVendorReload)
        ''')

    def test_changed_settings_and_exclusions_wait_for_manual_apply(self):
        self.live_capture_fixture()
        self.lua.execute("""
          local ra=ns.ProfRouteAuto; local o={start=1,target=2}
          local r=finish('alchemy',o); local jobs=#queue
          ns.ProfEconomy.SetPolicy('alchemy','alchemy',101,'ban',true)
          ns.ProfEconomy.ApplyPolicies('alchemy')
          local changed={start=1,target=2,exclusions={['alchemy:101']='ban'}}
          assert(ra.Get('alchemy',changed)==r and r.settingsChanged and r.stale)
          assert(captures==1 and #queue==jobs)
          ra.Recalculate('alchemy',changed)
          local blocked=finish('alchemy',changed)
          assert(not blocked.feasible and captures==2)
          assert(ra.Get('alchemy',changed)==blocked,'infeasible cache restarted itself')
        """)
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute("""
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2,exclusions={['alchemy:101']='ban'}})
          assert(r.cached and not r.feasible and r.status~='searching' and captures==2)
        """)

    def test_saved_routes_are_character_scoped(self):
        self.live_capture_fixture()
        self.lua.execute("""
          local ra=ns.ProfRouteAuto; local o={start=1,target=2}
          assert(finish('alchemy',o).total==7)
          UnitName=function() return 'Other' end; livePrice=11
          assert(ra.Get('alchemy',o).status=='searching')
          assert(finish('alchemy',o).total==11 and captures==2)
          UnitName=function() return 'Test' end
          assert(ra.Get('alchemy',o).total==7)
          assert(DungeonsForeverDB.prof.routeCache['Other-Realm'].active.alchemy)
        """)

    def test_invalidation_while_searching_preserves_job_and_marks_published_input_stale(self):
        self.live_capture_fixture()
        self.lua.execute("""
          local ra=ns.ProfRouteAuto; local o={start=1,target=2}
          local pending=ra.Get('alchemy',o); local n=#queue
          ra.Invalidate('recipe')
          assert(ra.Get('alchemy',o)==pending and #queue==n)
          local r=finish('alchemy',o)
          assert(r.feasible and r.stale and r.staleReason=='recipe' and captures==1)
        """)

    def test_explicit_recalculation_cannot_receive_old_task_publication(self):
        self.live_capture_fixture()
        self.lua.execute("""
          local ra=ns.ProfRouteAuto; local o={start=1,target=2}
          ra.Get('alchemy',o); local old=queue[1]
          local replacement=ra.Recalculate('alchemy',o)
          local updates=0; ra.OnPlanChanged(function() updates=updates+1 end)
          assert(old()); assert(updates==0 and ra.Get('alchemy',o)==replacement)
          assert(finish('alchemy',o).total==7 and captures==1)
        """)

    def test_synthetic_snapshots_never_persist_or_cross_contaminate(self):
        self.lua.execute("""
          local a=fixture(); local b=fixture(); b.prices[11]=99
          assert(finish('alchemy',{snapshot=a,start=1,target=2}).total==7)
          assert(finish('alchemy',{snapshot=b,start=1,target=2}).total==99)
          local d=DungeonsForeverDB and DungeonsForeverDB.prof and DungeonsForeverDB.prof.routeCache
          assert(not d or not d['Test-Realm'] or next(d['Test-Realm'].routes)==nil)
        """)

    def test_old_cached_route_models_are_rejected_before_display(self):
        self.live_capture_fixture()
        self.lua.execute("""
          DungeonsForeverDB={prof={routeCache={['Test-Realm']={version=1,
            routes={old={slug='alchemy',result={total=900,status='complete'}}},active={alchemy='old'}}}}}
          local o={start=1,target=2}; local pending=ns.ProfRouteAuto.Get('alchemy',o)
          assert(pending.status=='searching','old duplicate-step route was displayed')
          local r=finish('alchemy',o)
          assert(r.total==7 and r.routeModel==3)
          assert(DungeonsForeverDB.prof.routeCache['Test-Realm'].version==3)
        """)
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute("""
          local d=DungeonsForeverDB.prof.routeCache['Test-Realm']
          d.routes[d.active.alchemy].result.routeModel=1
          assert(ns.ProfRouteAuto.Get('alchemy',{start=1,target=2}).status=='searching',
            'mislabelled old record bypassed snapshot-model check')
          assert(finish('alchemy',{start=1,target=2}).routeModel==3 and captures==2)
        """)

    def test_missing_legacy_route_is_cached_as_infeasible(self):
        self.lua.execute("""
          ns.EnsureProfRecipes=function() return {} end
          local ra=ns.ProfRouteAuto; local o={start=1,target=2,scheme='matcost'}
          local r=ra.Get('alchemy',o)
          assert(r and not r.feasible and r.status=='infeasible')
          assert(ra.Get('alchemy',o)==r)
        """)
        self.load(str(ROOT/'Core'/'ProfRouteAuto.lua'))
        self.lua.execute("""
          ns.EnsureProfRecipes=function() error('saved unavailable route should not rescan') end
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2,scheme='matcost'})
          assert(r.cached and r.status=='infeasible')
        """)

    def test_capture_tracks_verified_vendor_supply_separately_from_known_price(self):
        self.load(str(ROOT/'Core'/'ProfItemPrices.lua'))
        self.lua.execute("""
          ns.ProfEconomy.Professions=function() return {alchemy={cur=1,max=75,primary=true}} end
          ns.ProfRecipes={alchemy={rows={{101,10,1,'','','',1,20,30,40,false,{{11,2}}}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          UnitFactionGroup=function() return 'Alliance' end
          UnitLevel=function() return 30 end
          ns.ProfItems={
            [11]={item_id=11,VendorStackCount=1,offers={
              [123]={npc_id=123,cost_copper=3,stock=-1,side='a',price_source='client'}}},
            [10]={item_id=10,VendorStackCount=1,offers={
              [456]={npc_id=456,cost_copper=4,stock=1,side='a',price_source='client'}}}}
          local getOffers=ns.ProfItemPrices.GetOffers
          ns.ProfItemPrices.GetOffers=function(id,ctx)
            assert(ctx.allowVendorCache==nil and ctx.requireObservedPrice==nil)
            assert(ctx.character=='Test-Realm' and ctx.faction=='A' and ctx.level==30 and ctx.professions.alchemy.cur==1)
            return getOffers(id,ctx)
          end
          local s=ns.ProfEconomy.Capture('alchemy',{})
          assert(s.vendorItems[11] and not s.vendorItems[10])
          assert(s.vendorSuppliers[11][1].npcID==123 and s.offers[11][1].source=='client')
          assert(s.vendorSuppliers[11][1].availabilityVerified and s.offers[11][1].verifiedAt==nil)
        """)

    def test_missing_prof_items_has_no_suppliers_and_uses_ah(self):
        self.load(str(ROOT/'Core'/'ProfItemPrices.lua'))
        self.lua.execute('''
          local function forbidden() error('runtime NPC purchase API was called') end
          GetMerchantItemInfo=forbidden;GetMerchantNumItems=forbidden;GetMerchantItemLink=forbidden
          C_MerchantFrame={GetItemInfo=forbidden}
          local marketPrice=9
          Auctionator={API={v1={GetAuctionPriceByItemID=function() return marketPrice end,
            GetVendorPriceByItemID=forbidden,GetVendorPrice=forbidden}}}
          C_Item={GetItemSellPrice=function(id) if id==10 then return 2 end end}
          DungeonsForeverDB={profVendorOffers={[2320]={old={itemID=2320,npcID=1313,
            price=0,quantity=1,source='merchant',unlimited=true,available=true}}}}
          ns.ProfEconomy.Professions=function() return {alchemy={cur=1,max=75,primary=true}} end
          ns.ProfRecipes={alchemy={rows={{101,10,1,'','','',1,20,30,40,false,{{2320,3}}}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          ns.ProfLeveling={alchemy={}}
          UnitFactionGroup=function() return 'Alliance' end
          local e=ns.ProfEconomy.Capture('alchemy',{})
          assert(not e.vendorItems[2320] and #e.offers[2320]==0 and e.prices[2320]==9)
          assert(not e.vendorSuppliers[2320],'missing ProfItems invented an NPC supplier')
          assert(#ns.ProfItemPrices.GetSuppliers(2320)==0)
          assert(ns.ProfItemPrices.GetPrice(2320)==nil,'missing NPC price became zero')
          local sum=ns.ProfRouteAuto.SummarizeSteps({{1,2,101,1}},'alchemy')
          assert(sum.completeCost and sum.total==27 and sum.ahTotal==27 and sum.vendorTotal==0)
          assert(not sum.mats[1].vendor and sum.mats[1].source=='ah' and not sum.mats[1].unpriced)
          assert(sum.mats[1].count==3 and sum.mats[1].unit==9)
          assert(sum.mats[1].quoteSource==nil,'AH or removed static quote became an NPC price')
          assert(ns.ProfRouteAuto.AHPriceOf(2320)==9,'AH market integration was removed')
          assert(sum.productNPC==2 and sum.productAH==9 and ns.ProfRouteAuto.NPCSellPriceOf(10)==2,
            'NPC sell revenue or auction product value was removed with purchase prices')
          marketPrice=13
          assert(ns.ProfRouteAuto.AHPriceOf(2320)==9,'AH cache stopped retaining its quote')
          ns.ProfRouteAuto.Invalidate('test')
          assert(ns.ProfRouteAuto.AHPriceOf(2320)==13,'AH cache no longer refreshes')
        ''')

    def test_drafts_are_per_character_and_only_apply_on_recalculate(self):
        self.lua.execute("""
          local e=ns.ProfEconomy
          e.SetPolicy('alchemy','mining',101,'ban',true)
          assert(e.GetPolicies('alchemy')['mining:101']==nil)
          e.ApplyPolicies('alchemy'); assert(e.GetPolicies('alchemy')['mining:101']=='ban')
          e.ResetPolicies('alchemy'); assert(e.GetPolicies('alchemy')['mining:101']=='ban')
          e.ApplyPolicies('alchemy'); assert(e.GetPolicies('alchemy')['mining:101']==nil)
          e.SetPolicy('alchemy','mining',101,'level',false)
          UnitName=function() return 'Other' end
          assert(e.GetPolicies('alchemy')['mining:101']==nil)
        """)

    def test_recipe_and_trainer_events_are_not_lost_when_coalesced(self):
        self.lua.execute("""
          local e=ns.ProfEconomy; local a,b=0,0
          e.ScanRecipes=function() a=a+1 end; e.ScanTrainer=function() b=b+1 end
          local f=frames[1]
          f.OnEvent(f,'TRADE_SKILL_LIST_UPDATE'); f.OnEvent(f,'TRAINER_SHOW')
          assert(#timers==1); timers[1](); assert(#queue==1)
          assert(queue[1]()); assert(a==1 and b==1)
        """)

    def test_fixed_summary_uses_catalogue_fallback_and_prefers_client(self):
        self.lua.execute("""
          ns.ProfRecipes={alchemy={rows={{101,10,99,'','','',1,2,3,4,false,{{11,99}}}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          ns.ProfLeveling={alchemy={}}
          local st={{1,2,101,1}}
          local sum=ns.ProfRouteAuto.SummarizeSteps(st,'alchemy')
          assert(#sum.mats==1 and sum.mats[1][1]==11 and sum.mats[1][2]==99)
          ns.ProfRecipeRuntime={[101]={mats={{12,3}},count=2,item=14}}
          st={{1,2,101,1}}; sum=ns.ProfRouteAuto.SummarizeSteps(st,'alchemy')
          assert(#sum.mats==1 and sum.mats[1][1]==12 and sum.mats[1][2]==3)
        """)

    def test_modern_schematic_is_preferred_over_old_reagent_and_yield_api(self):
        self.lua.execute("""
          C_TradeSkillUI={GetRecipeInfo=function() return {learned=true} end,
            GetRecipeSchematic=function() return {quantityMin=2,quantityMax=2,outputItemID=12,
              reagentSlotSchematics={{quantityRequired=3,reagents={{itemID=14}}}}} end,
            GetRecipeNumItemsProduced=function() return 99,99 end,
            GetRecipeNumReagents=function() return 1 end,
            GetRecipeReagentInfo=function() return 'stale',1,99 end,
            GetRecipeReagentItemLink=function() return 'item:999' end,
            GetRecipeOutputItemData=function() return {hyperlink='item:12'} end}
          local r=ns.ProfEconomy.ReadRecipe(101)
          assert(r.count==2 and r.item==12 and #r.mats==1 and r.mats[1][1]==14 and r.mats[1][2]==3)
          C_TradeSkillUI.GetRecipeSchematic=function() return nil end
          r=ns.ProfEconomy.ReadRecipe(101); assert(r.count==99 and r.mats[1][1]==999,'unavailable schematic did not use supported legacy API')
        """)

    def test_legacy_craft_recipe_reads_actual_enchant_inputs(self):
        self.lua.execute("""
          GetNumCrafts=function() return 1 end
          GetCraftInfo=function() return 'TestEnchant','','optimal' end
          GetSpellInfo=function(name) return name,nil,nil,nil,nil,nil,101 end
          GetCraftNumReagents=function() return 1 end
          GetCraftReagentInfo=function() return 'ActualDust',1,3 end
          GetCraftReagentItemLink=function() return 'item:14' end
          GetCraftItemLink=function() return 'enchant:101' end
          ns.ProfEconomy.ScanCrafts()
          local r=ns.ProfRecipeRuntime[101]
          assert(r.learned and r.mats[1][1]==14 and r.mats[1][2]==3)
        """)

    def test_unlearned_profession_uses_reference_when_client_cannot_read(self):
        self.lua.execute("""
          ns.ProfRecipes={mining={rows={{2657,2840,1,'Smelting','','',1,25,47,70,false,{{2770,1}},nil,{skill=1}}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          ns.ProfEconomy.Professions=function() return {} end
          C_Item={GetItemCount=function() return 0 end}
          C_TradeSkillUI={GetRecipeInfo=function() return nil end,GetRecipeSchematic=function() return nil end}
          local s=ns.ProfEconomy.Capture('mining',{})
          local r=s.recipes[1]
          assert(not r.clientPending and not r.clientUnavailable)
          assert(r.mats[1][1]==2770 and r.mats[1][2]==1 and r.count==1)
          assert(r.materialSource=='catalogue' and r.outputSource=='catalogue' and r.dataSource=='catalogue')
          assert(s.professions.mining.unlearned)
        """)

    def test_resolver_overrides_each_known_field_without_discarding_other_reference_fields(self):
        self.lua.execute("""
          local e=ns.ProfEconomy
          local seed={profession='blacksmithing',spell=101,item=10,count=1,mats={{11,2}},tools={5956}}
          ns.ProfRecipeRuntime={[101]={mats={{12,3}},learned=false}}
          local r=e.ResolveRecipe(seed)
          assert(r.item==10 and r.count==1 and r.mats[1][1]==12 and r.tools==nil)
          assert(r.dataSource=='mixed' and r.materialSource=='client' and r.outputSource=='catalogue')
          assert(seed.mats[1][1]==11,'resolver mutated reference data')
          ns.ProfRecipeRuntime[101]={count=2,item=14,mats={{12,4}},toolsKnown=true,tools={}}
          r=e.ResolveRecipe(seed)
          assert(r.count==2 and r.item==14 and r.tools==nil and not r.clientPending)
          assert(r.dataSource=='client' and r.toolSource==nil)
        """)

    def test_schematic_read_does_not_require_recipe_info_api(self):
        self.lua.execute("""
          C_TradeSkillUI={GetRecipeSchematic=function() return {quantityMin=2,quantityMax=2,outputItemID=14,
            reagentSlotSchematics={{quantityRequired=3,reagents={{itemID=12}}}}} end}
          local r=ns.ProfEconomy.ReadRecipe(101)
          assert(r.available and r.count==2 and r.mats[1][1]==12)
          local report=ns.ProfEconomy.APICapabilities()
          assert(not report.functions['C_TradeSkillUI.GetRecipeInfo'])
          assert(report.functions['C_TradeSkillUI.GetRecipeSchematic'])
          assert(report.reads['C_TradeSkillUI.GetRecipeSchematic'].successes==1)
        """)

    def test_empty_or_failing_client_reads_retain_catalogue_and_diagnostic_evidence(self):
        self.lua.execute("""
          C_TradeSkillUI={GetRecipeInfo=function() error('not loaded') end,GetRecipeSchematic=function() return nil end}
          assert(ns.ProfEconomy.ReadRecipe(101)==nil)
          local r=ns.ProfEconomy.ResolveRecipe({spell=101,item=10,count=1,mats={{11,2}}},'alchemy')
          assert(not r.clientPending and not r.clientUnavailable)
          local report=ns.ProfEconomy.APIReport()
          assert(report:find('GetRecipeInfo: available; data=0, empty=0, errors=1',1,true))
          assert(report:find('GetRecipeSchematic: available; data=0, empty=1, errors=0',1,true))
          assert(DungeonsForeverDB.prof.economy['Test-Realm'].apiReport)
        """)

    def test_authoritative_roster_only_filters_its_matching_profession(self):
        self.lua.execute("""
          local e=ns.ProfEconomy
          e.Professions=function() return {alchemy={cur=1,max=75,primary=true}} end
          C_TradeSkillUI={GetAllRecipeIDs=function() return {101,102} end,
            GetBaseProfessionInfo=function() return {professionID=171} end,
            IsDataSourceChanging=function() return false end,IsTradeSkillReady=function() return true end,
            GetRecipeInfo=function(id) return {learned=id==101} end}
          e.ScanRecipes()
          local seed={spell=103,item=10,count=1,mats={{11,2}}}
          assert(e.ResolveRecipe(seed,'alchemy').clientUnavailable)
          assert(not e.ResolveRecipe(seed,'blacksmithing').clientUnavailable)
          seed.spell=102; assert(not e.ResolveRecipe(seed,'alchemy').clientUnavailable)
          GetBuildInfo=function() return 'new','build' end
          e.APIReport()
          seed.spell=103; assert(not e.ResolveRecipe(seed,'alchemy').clientUnavailable,'old build roster survived')
        """)

    def test_partial_learned_only_or_changing_roster_never_proves_absence(self):
        self.lua.execute("""
          local e=ns.ProfEconomy
          e.Professions=function() return {alchemy={cur=1,max=75,primary=true}} end
          C_TradeSkillUI={GetAllRecipeIDs=function() return {101} end,
            GetBaseProfessionInfo=function() return {professionID=171} end,
            IsDataSourceChanging=function() return false end,
            GetRecipeInfo=function() return {learned=true} end}
          e.ScanRecipes()
          local seed={spell=103,item=10,count=1,mats={{11,2}}}
          assert(not e.ResolveRecipe(seed,'alchemy').clientUnavailable)
          C_TradeSkillUI.GetRecipeInfo=function() return {learned=false} end
          C_TradeSkillUI.IsDataSourceChanging=function() return true end
          e.ScanRecipes(); assert(not e.ResolveRecipe(seed,'alchemy').clientUnavailable)
          C_TradeSkillUI.GetAllRecipeIDs=function() return nil end
          e.ScanRecipes(); assert(not e.ResolveRecipe(seed,'alchemy').clientUnavailable)
        """)

    def test_client_unavailable_stays_blocked_but_valid_variable_range_uses_minimum(self):
        self.lua.execute("""
          local seed={spell=101,item=10,count=1,mats={{11,2}}}
          ns.ProfRecipeRuntime={[101]={available=false}}
          local r=ns.ProfEconomy.ResolveRecipe(seed,'alchemy')
          assert(r.clientUnavailable and r.verified==false)
          C_TradeSkillUI={GetRecipeInfo=function() return {learned=true} end,
            GetRecipeSchematic=function() return {quantityMin=1,quantityMax=3,outputItemID=10,reagentSlotSchematics={}} end}
          r=ns.ProfEconomy.ReadRecipe(101)
          assert(r.variableOutput and r.count==1 and r.outputMin==1 and r.outputMax==3)
          r=ns.ProfEconomy.ResolveRecipe(seed,'alchemy')
          assert(not r.outputConflict and r.count==1 and r.outputBasis=='minimum' and r.outputSource=='client')
        """)

    def test_reference_fallback_does_not_clear_cooldown(self):
        self.lua.execute("""
          ns.ProfRecipeMeta={[101]={cooldown=true}}
          local r=ns.ProfEconomy.ResolveRecipe({spell=101,item=10,count=1,mats={{11,2}}},'alchemy')
          assert(r.cooldown and r.materialSource=='catalogue')
          C_Spell={GetSpellBaseCooldown=function() return 0 end}
          C_TradeSkillUI={GetRecipeInfo=function() return {learned=true,hasCooldown=true} end,
            GetRecipeCooldown=function() return 0,false end}
          r=ns.ProfEconomy.ReadRecipe(101)
          assert(r.cooldown and r.cooldownVerified,'ready/base-zero API erased a real recipe cooldown')
          ns.ProfRecipeRuntime[101]={cooldown=false}
          assert(ns.ProfEconomy.ResolveRecipe({spell=101,item=10,count=1,mats={{11,2}}},'alchemy').cooldown,
            'unverified base-zero observation erased reference cooldown')
        """)

    def test_partial_schematic_falls_back_field_by_field_to_client_legacy_api(self):
        self.lua.execute('''
          C_TradeSkillUI={GetRecipeInfo=function() return {recipeID=101,learned=false} end,
            GetRecipeSchematic=function() return {quantityMin=0,quantityMax=0,outputItemID=0,
              reagentSlotSchematics={{quantityRequired=0,reagents={{itemID=11}}}}} end,
            GetRecipeNumItemsProduced=function() return 2,2 end,
            GetRecipeNumReagents=function() return 1 end,
            GetRecipeReagentItemLink=function() return 'item:11' end,
            GetRecipeReagentInfo=function() return 'Material',1,3 end}
          local rt=ns.ProfEconomy.ReadRecipe(101)
          assert(rt.count==2 and rt.mats[1][1]==11 and rt.mats[1][2]==3)
          local r=ns.ProfEconomy.ResolveRecipe({spell=101,item=10,count=5,mats={{12,7}}},'alchemy')
          assert(r.count==2 and r.mats[1][1]==11 and r.outputSource=='client' and not r.clientPending)
        ''')

    def test_unlearned_empty_api_sentinels_keep_existing_catalogue_materials(self):
        self.lua.execute('''
          C_TradeSkillUI={GetRecipeInfo=function() return {recipeID=101,learned=false} end,
            GetRecipeSchematic=function() return {quantityMin=0,reagentSlotSchematics={}} end,
            GetRecipeNumReagents=function() return 0 end,GetRecipeReagentInfo=function() end}
          ns.ProfEconomy.ReadRecipe(101)
          local r=ns.ProfEconomy.ResolveRecipe({spell=101,item=10,count=3,mats={{11,2}}},'alchemy')
          assert(r.count==3 and r.outputSource=='catalogue' and r.mats[1][1]==11 and r.mats[1][2]==2)
          assert(r.materialSource=='catalogue' and not r.clientPending)
        ''')

    def test_old_random_marker_uses_reference_until_range_is_read_then_fixed_read_clears_it(self):
        self.lua.execute('''
          local seed={spell=101,item=10,count=3,mats={{11,2}}}
          ns.ProfRecipeRuntime={[101]={variableOutput=true}}
          local r=ns.ProfEconomy.ResolveRecipe(seed,'engineering')
          assert(r.count==3 and r.outputBasis=='reference' and not r.outputConflict and not r.clientPending)
          C_TradeSkillUI={GetRecipeInfo=function() return {recipeID=101,learned=false} end,
            GetRecipeSchematic=function() return {quantityMin=2,quantityMax=4,outputItemID=10} end}
          ns.ProfEconomy.ReadRecipe(101)
          r=ns.ProfEconomy.ResolveRecipe(seed,'engineering')
          assert(r.count==2 and r.outputMin==2 and r.outputMax==4 and r.outputBasis=='minimum')
          C_TradeSkillUI.GetRecipeSchematic=function() return {} end
          C_TradeSkillUI.GetRecipeNumItemsProduced=function() return 2,2 end
          ns.ProfEconomy.ReadRecipe(101)
          r=ns.ProfEconomy.ResolveRecipe(seed,'engineering')
          assert(r.count==2 and not r.variableOutput and not r.outputConflict)
        ''')

    def test_foreign_recipe_id_cannot_overwrite_current_reference(self):
        self.lua.execute('''
          C_TradeSkillUI={GetRecipeInfo=function() return {recipeID=999,learned=true} end,
            GetRecipeSchematic=function() return {quantityMin=100,outputItemID=999} end}
          assert(ns.ProfEconomy.ReadRecipe(101)==nil)
          local r=ns.ProfEconomy.ResolveRecipe({spell=101,item=10,count=3,mats={{11,2}}},'alchemy')
          assert(r.item==10 and r.count==3 and r.materialSource=='catalogue')
        ''')

    def test_invalid_recipe_ids_do_not_query_api_and_positive_known_spell_overrides_false_cache(self):
        self.lua.execute('''
          C_TradeSkillUI={GetRecipeInfo=function() error('invalid recipe lookup') end}
          assert(ns.ProfEconomy.ReadRecipe(nil)==nil and ns.ProfEconomy.ReadRecipe(0)==nil)
          ns.ProfRecipeRuntime={[101]={learned=false}}
          C_Spell={IsSpellKnown=function(spell) return spell==101 end}
          assert(ns.ProfEconomy.Known(101) and not ns.ProfEconomy.Known(102))
        ''')

    def test_existing_guide_starting_threshold_is_fallback_and_actual_client_skill_wins(self):
        self.lua.execute('''
          ns.ProfLeveling={enchanting={rinfo={[7418]={learn=1,yellow=1,green=5,grey=25}}}}
          local seed={spell=7418,item=10,count=1,learn=20,yellow=20,green=22,grey=25,mats={{11,1}}}
          local r=ns.ProfEconomy.ResolveRecipe(seed,'enchanting')
          assert(r.learn==1 and r.skillSource=='guide' and r.mats[1][1]==11)
          ns.ProfRecipeRuntime={[7418]={learn=20}}
          r=ns.ProfEconomy.ResolveRecipe(seed,'enchanting')
          assert(r.learn==20 and r.skillSource=='client')
        ''')

    def test_complete_catalogues_use_reference_recipes_with_priced_materials_without_profession_api(self):
        for filename in ('Data/Data_ProfRecipes.lua','Data/Data_ProfLeveling.lua','Data/Data_ProfMining.lua',
                         'Data/Data_ProfItems.lua','Data/Data_ProfFormulaQuests.lua','ProfItemPrices.lua'):
            self.load(str(ROOT/'Core'/filename))
        self.lua.execute('''
          ns.DB=function() return DungeonsForeverDB end
          ns.ProfEconomy.Professions=function() return {engineering={cur=60,max=75,primary=true}} end
          ns.ProfRouteAuto.AHPriceOf=function() return 1000 end
          for _,case in ipairs({{'engineering',60,225},{'enchanting',1,225}}) do
            local r,j=ns.ProfRouteSolver.Compute(case[1],{start=case[2],target=case[3],maxNodes=1})
            assert(not j.error and #r.steps>0 and r.targetReached,case[1]..':'..tostring(r.plannedTo))
            assert(not r.referenceRoute and not r.pricePending and r.completeCost)
            local seen={};for _,step in ipairs(r.steps) do
              local key=step.profession..':'..step[3];assert(not seen[key],'repeated summary '..key);seen[key]=true
            end
            local segments={};for _,step in ipairs(r.executionSteps) do
              assert(step.segmentID and not segments[step.segmentID],'missing or repeated segment')
              segments[step.segmentID]=true
              assert(step.recipe.mats and step[4]>0)
            end
            for _,m in ipairs(r.mats) do assert(not m.unpriced) end
          end
        ''')

    def test_trainer_observation_allows_new_recipe_and_overrides_roster_omission(self):
        self.lua.execute("""
          local e=ns.ProfEconomy
          e.APIReport()
          local d=DungeonsForeverDB.prof.economy['Test-Realm']
          d.recipeRosters={alchemy={complete=true,ids={[102]=true}}}
          ns.ProfRecipeRuntime={[101]={trainerObserved=true,available=true}}
          local seed={spell=101,item=10,count=1,mats={{11,2}},isNew=true,availabilityUnknown=true}
          local r=e.ResolveRecipe(seed,'alchemy')
          assert(r.learnSource=='trainer' and r.clientAvailable and r.verified)
          assert(not r.clientUnavailable and not r.availabilityUnknown)
        """)

    def test_valid_client_materials_repair_missing_reference_materials(self):
        self.lua.execute("""
          ns.ProfRecipeRuntime={[101]={mats={{12,3}},count=2,item=14,learn=5}}
          local row={101,10,1,'','','',nil,10,20,30,false,nil}
          local r=ns.ProfEconomy.Normalize(row,'alchemy','rows')
          assert(r and r.learn==5 and r.mats[1][1]==12 and r.count==2)
          assert(ns.ProfEconomy.Normalize({101,10,1},'alchemy','rows')==nil,'missing skill thresholds were guessed')
        """)

    def test_zero_legacy_reagent_sentinel_never_erases_known_reference_inputs(self):
        self.lua.execute("""
          C_TradeSkillUI={GetRecipeInfo=function() return nil end,GetRecipeSchematic=function() return nil end,
            GetRecipeNumReagents=function() return 0 end,GetRecipeReagentInfo=function() return nil end}
          local e=ns.ProfEconomy
          local rt=e.ReadRecipe(101)
          assert(not rt.mats and not rt.available)
          local r=e.ResolveRecipe({spell=101,item=12,count=1,mats={{10,5}}},'alchemy')
          assert(r.mats[1][1]==10 and r.mats[1][2]==5 and r.materialSource=='catalogue')
          rt.mats={}; rt.available=true
          r=e.ResolveRecipe({spell=101,item=12,count=1,mats={{10,5}}},'alchemy')
          assert(r.mats[1][2]==5,'resolver trusted an unproven old zero-input cache')
          e.ReadRecipe(101)
          assert(not rt.mats and not rt.available,'old unproven empty cache survived')
        """)

    def test_empty_schematic_placeholders_are_not_recipe_evidence(self):
        self.lua.execute("""
          C_TradeSkillUI={GetRecipeInfo=function() return {} end,
            GetRecipeSchematic=function() return {reagentSlotSchematics={}} end,
            GetRecipeNumReagents=function() return 0 end,GetRecipeReagentInfo=function() return nil end}
          local e=ns.ProfEconomy; local rt=e.ReadRecipe(101)
          assert(not rt.mats and not rt.available)
          local r=e.ResolveRecipe({spell=101,item=12,count=1,mats={{10,5}}},'alchemy')
          assert(r.mats[1][2]==5 and r.materialSource=='catalogue')
          C_TradeSkillUI.GetRecipeSchematic=function() return {} end
          rt=e.ReadRecipe(101); assert(not rt.mats and not rt.available)
        """)

    def test_zero_reagents_are_valid_for_positively_observed_recipe(self):
        self.lua.execute("""
          C_TradeSkillUI={GetRecipeInfo=function() return {learned=true} end,
            GetRecipeNumReagents=function() return 0 end,GetRecipeReagentInfo=function() return nil end}
          local rt=ns.ProfEconomy.ReadRecipe(101)
          assert(rt.available and rt.mats and #rt.mats==0)
          C_TradeSkillUI.GetRecipeInfo=function() return nil end
          rt=ns.ProfEconomy.ReadRecipe(101)
          assert(rt.mats and #rt.mats==0,'verified cached zero-input recipe was lost')
        """)

    def test_enchant_scroll_is_not_mistaken_for_learning_formula(self):
        self.lua.execute("""
          ns.ProfRecipes={enchanting={enchants={{'Name','','','',1,10,20,30,{{99,99}},nil,false,false,{},101,14}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          ns.ProfRecipeKeys={'enchanting'}
          ns.ProfEconomy.Professions=function() return {enchanting={cur=1,max=300,primary=true}} end
          C_Item={GetItemCount=function() return 0 end}
          C_TradeSkillUI={GetRecipeInfo=function() return {learned=true} end,
            GetRecipeNumItemsProduced=function() return 1,1 end,
            GetRecipeItemLink=function() return 'item:14' end,
            GetRecipeNumReagents=function() return 1 end,
            GetRecipeReagentItemLink=function() return 'item:12' end,
            GetRecipeReagentInfo=function() return 'Actual',1,2 end}
          local s=ns.ProfEconomy.Capture('enchanting',{})
          assert(#s.recipes==1 and s.recipes[1].item==14 and s.recipes[1].formula==nil)
          assert(s.recipes[1].mats[1][1]==12 and s.recipes[1].mats[1][2]==2)
        """)

    def test_trainer_observation_reads_availability_and_skill_but_never_fees(self):
        self.lua.execute("""
          ns.EnsureProfRecipes=function() return {} end
          ns.ProfRecipeKeys={}
          GetSpellInfo=function() return 'Mining' end
          GetNumTrainerServices=function() return 1 end
          GetTrainerServiceInfo=function() return 'Mining','','available' end
          GetTrainerServiceSpellID=function() return 2576 end
          GetTrainerServiceCost=function() error("tuition must never be read") end
          GetTrainerServiceLevelReq=function() return 10 end
          GetTrainerServiceSkillReq=function() return 'Mining',50 end
          ns.ProfEconomy.ScanTrainer()
          local d=DungeonsForeverDB.prof.economy['Test-Realm']
          assert(d.rankCosts==nil and d.trainerCosts==nil and d.rankRequirements==nil)
          assert(d.learningRequirements[2576].level==10 and d.learningRequirements[2576].skill==50)
          assert(ns.ProfRecipeRuntime[2576].trainerObserved)
        """)

    def test_trainer_rank_fallback_uses_client_spell_name_and_subtext(self):
        self.lua.execute("""
          ns.EnsureProfRecipes=function() return {} end; ns.ProfRecipeKeys={}
          C_Spell={GetSpellName=function(id) if id==2575 or id==2576 then return 'Mining' end end,
            GetSpellSubtext=function(id) return id==2575 and 'Apprentice' or 'Journeyman' end}
          GetNumTrainerServices=function() return 1 end
          GetTrainerServiceInfo=function() return 'Mining','Journeyman','available' end
          ns.ProfEconomy.ScanTrainer()
          local d=DungeonsForeverDB.prof.economy['Test-Realm']
          assert(d.rankCosts==nil and d.trainerCosts==nil)
          assert(ns.ProfRecipeRuntime[2576].trainerObserved)
        """)

    def test_capture_ignores_bags_bank_tuition_tools_and_already_known_formula_prices(self):
        self.lua.execute("""
          local e=ns.ProfEconomy
          e.Professions=function() return {alchemy={cur=1,max=75,primary=true}} end
          ns.ProfRecipes={alchemy={rows={{101,10,1,'','','',1,20,30,40,false,{{11,2}},{99},{skill=1}}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          ns.ProfRecipeMeta={[101]={tools={5956}}}
          e.Have=function() error('material stock must never be read') end
          C_Item={GetItemCount=function() error('bags/bank must never be read') end}
          C_TradeSkillUI={GetRecipeInfo=function() return {learned=true} end,
            GetRecipeTools=function() error('tools must never be read') end,
            GetRecipeRequirements=function() error('tool requirements must never be read') end}
          e.APIReport()
          local d=DungeonsForeverDB.prof.economy['Test-Realm']
          d.trainerCosts={[101]=500}; d.rankCosts={alchemy={[150]=1000}}
          d.rankRequirements={alchemy={[150]={level=99}}}
          local requested={}
          ns.ProfRouteAuto.AHPriceOf=function(id) requested[id]=true; return 7 end
          ns.ProfItemPrices={GetOffers=function(id) return {} end}
          local s=e.Capture('alchemy',{})
          assert(next(s.inventory)==nil and not s.inventoryUnknown)
          assert(s.trainingCosts==nil and s.rankCosts==nil and s.rankRequirements==nil)
          assert(requested[10] and requested[11] and not requested[99] and not requested[5956])
          assert(s.recipes[1].tools==nil and not s.recipes[1].toolsUnknown)
          assert(not frames[1].events.BAG_UPDATE_DELAYED and not frames[1].events.PLAYERBANKSLOTS_CHANGED,
            'bag/bank activity still invalidates material-only routes')
        """)

    def test_injected_snapshot_cannot_restore_removed_cost_or_inventory_model(self):
        self.lua.execute("""
          local input=fixture(); input.inventory={[11]=900}
          input.inventoryUnknown=true; input.trainingCosts={[101]=500}
          input.rankCosts={alchemy={[150]=1000}}; input.stations={forge=true}
          input.learningRequirements={[101]={level=99}}
          local s=ns.ProfEconomy.Capture('alchemy',{snapshot=input})
          assert(next(s.inventory)==nil and not s.inventoryUnknown)
          assert(not s.trainingCosts and not s.rankCosts and not s.stations and not s.learningRequirements)
        """)

    def test_fixed_route_includes_formula_cost_but_excludes_tool_injection(self):
        self.lua.execute("""
          ns.ProfRecipes={enchanting={rows={{101,10,1,'','','',1,20,30,40,false,{{11,2}},{99},{skill=1}}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          ns.ProfLeveling={enchanting={}}
          Auctionator={API={v1={GetAuctionPriceByItemID=function(_,id)
            return id==11 and 7 or 3
          end}}}
          local sum=ns.ProfRouteAuto.SummarizeSteps({{1,2,101,1}},'enchanting')
          assert(sum.total==17 and sum.matTotal==14 and #sum.formulas==1 and sum.formulasTotal==3)
          local r=ns.ProfRouteAuto.Compute('enchanting',{start=1,target=2,scheme='matcost',noFormula=true})
          assert(#r.steps==1 and r.steps[1][3]==101,'removed tool recipe was injected')
          assert(r.total==17 and r.formulasTotal==3)
        """)

    def test_removed_formula_option_does_not_change_async_cache(self):
        self.lua.execute("""
          local s=fixture(); local a={snapshot=s,start=1,target=2,noFormula=false}
          local b={snapshot=s,start=1,target=2,noFormula=true}
          assert(ns.ProfRouteAuto.Get('alchemy',a)==ns.ProfRouteAuto.Get('alchemy',b))
          ns.ProfModule={Setting=function(k) return k=='autoNoFormula' end}
          assert(ns.ProfRouteAuto.OptionsFor('alchemy').noFormula==nil)
        """)

    def test_fixed_route_prof_items_rounds_shared_packs_and_keeps_source(self):
        self.load(str(ROOT/'Core'/'ProfItemPrices.lua'))
        self.lua.execute("""
          ns.ProfRecipes={alchemy={rows={{101,10,1,'','','',1,20,30,40,false,{{11,3}}}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          ns.ProfLeveling={alchemy={}}
          ns.ProfItems={[11]={item_id=11,VendorStackCount=5,offers={
            [1313]={npc_id=1313,cost_copper=18,stock=-1,price_source='wowhead'}}}}
          local steps={{1,2,101,1,cost=999},{2,3,101,1,cost=999}}
          local sum=ns.ProfRouteAuto.SummarizeSteps(steps,'alchemy')
          assert(sum.priced and sum.completeCost and sum.costComplete and sum.referencePrices)
          assert(sum.total==36 and sum.matTotal==36 and sum.vendorTotal==36 and sum.ahTotal==0)
          local mat=sum.mats[1]
          assert(#sum.mats==1 and mat.id==11 and mat.count==10 and mat[2]==10 and mat.need==6)
          assert(mat.unit==18/5 and mat.bundleSize==5 and mat.bundlePrice==18 and mat.cost==36)
          assert(mat.vendor and mat.source=='vendor' and mat.npcID==1313 and mat.reference)
          assert(mat.quoteSource=='wowhead' and mat.priceBasis=='Data_ProfItems')
          assert(mat.verifiedAt==nil and mat.url=='https://www.wowhead.com/forever/npc=1313' and not mat.estimated)
          assert(steps[1].cost==18 and steps[2].cost==18)
          assert(steps[1][3]==101 and steps[2][3]==101 and steps[1][4]==1 and steps[2][4]==1)
          assert(not steps[1].unpriced and #sum.formulas==0 and sum.formulasTotal==0)
          ns.ProfRecipes.alchemy.rows[1][12]={{11,2}}
          sum=ns.ProfRouteAuto.SummarizeSteps(steps,'alchemy')
          assert(sum.total==18 and sum.mats[1].count==5 and sum.mats[1].need==4)
          assert(steps[1].cost==18 and steps[2].cost==0,'reused pack was charged twice')
        """)

    def test_fixed_route_chooses_lowest_prof_items_npc_bundle_price(self):
        self.load(str(ROOT/'Core'/'ProfItemPrices.lua'))
        self.lua.execute("""
          ns.ProfRecipes={alchemy={rows={{101,10,1,'','','',1,20,30,40,false,{{11,6}}}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          ns.ProfLeveling={alchemy={}}
          ns.ProfItems={[11]={item_id=11,VendorStackCount=5,offers={
            [1]={npc_id=1,cost_copper=40,stock=-1,price_source='client'},
            [2]={npc_id=2,cost_copper=15,stock=-1,price_source='client'}}}}
          local materialAuctionReads=0
          Auctionator={API={v1={GetAuctionPriceByItemID=function(_,id)
            if id==11 then materialAuctionReads=materialAuctionReads+1;return 100 end
            return 1
          end}}}
          local sum=ns.ProfRouteAuto.SummarizeSteps({{1,2,101,1}},'alchemy')
          assert(materialAuctionReads>=1,'NPC quotation prevented an AH price comparison')
          assert(sum.total==30 and sum.vendorTotal==30 and sum.ahTotal==0)
          local mat=sum.mats[1]
          assert(mat.npcID==2 and mat.count==10 and mat.need==6 and mat.unit==3)
          assert(mat.quoteSource=='client' and mat.reference and sum.completeCost)
        """)

    def test_fixed_route_unpriced_supplier_metadata_does_not_block_auction_purchase(self):
        self.load(str(ROOT/'Core'/'ProfItemPrices.lua'))
        self.lua.execute("""
          ns.ProfRecipes={alchemy={rows={{101,10,1,'','','',1,20,30,40,false,{{11,2}}}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          ns.ProfLeveling={alchemy={}}
          ns.ProfItems={[11]={item_id=11,VendorStackCount=1,offers={
            [1313]={npc_id=1313,stock=-1,price_source='client'}}}}
          local auctionQueries={}
          Auctionator={API={v1={GetAuctionPriceByItemID=function(_,id)
            auctionQueries[id]=true; return id==11 and 9 or 1
          end}}}
          local steps={{1,2,101,1}}
          local sum=ns.ProfRouteAuto.SummarizeSteps(steps,'alchemy')
          assert(sum.priced and sum.completeCost and sum.total==18 and sum.ahTotal==18 and sum.vendorTotal==0)
          assert(auctionQueries[11],'supplier metadata blocked AH pricing without an NPC quotation')
          local mat=sum.mats[1]
          assert(not mat.vendor and mat.source=='ah' and not mat.unpriced and mat.unit==9)
          assert(mat.count==2 and mat.need==2 and steps[1].cost==18 and not steps[1].unpriced)
        """)

    def test_fixed_route_zero_cost_packs_and_auction_materials_share_consistent_totals(self):
        self.load(str(ROOT/'Core'/'ProfItemPrices.lua'))
        self.lua.execute("""
          ns.ProfRecipes={alchemy={rows={{101,10,1,'','','',1,20,30,40,false,{{11,3},{12,2}}}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          ns.ProfLeveling={alchemy={}}
          ns.ProfItems={[11]={item_id=11,VendorStackCount=4,offers={
            [1313]={npc_id=1313,cost_copper=0,stock=-1,price_source='client'}}}}
          Auctionator={API={v1={GetAuctionPriceByItemID=function(_,id) return id==12 and 7 or 1 end}}}
          local steps={{1,2,101,1},{2,3,101,1}}
          local sum=ns.ProfRouteAuto.SummarizeSteps(steps,'alchemy')
          assert(sum.completeCost and sum.total==28 and sum.vendorTotal==0 and sum.ahTotal==28)
          assert(steps[1].cost==14 and steps[2].cost==14)
          local mat
          for _,m in ipairs(sum.mats) do if m.id==11 then mat=m end end
          assert(mat.count==8 and mat.need==6 and mat.cost==0 and not mat.unpriced)
        """)

    def test_legacy_schemes_do_not_overspend_finite_ah_when_npc_alternative_exists(self):
        self.load(str(ROOT/'Core'/'ProfItemPrices.lua'))
        self.lua.execute("""
          ns.ProfRecipes={alchemy={rows={
            {101,20,1,'','','',1,20,30,40,false,{{11,1}}},
            {102,21,1,'','','',1,20,30,40,false,{{12,1}}}}}}
          ns.EnsureProfRecipes=function()return ns.ProfRecipes end
          ns.ProfItems={[11]={item_id=11,VendorStackCount=1,offers={
            [7]={npc_id=7,stock=-1,cost_copper=10,price_source='client'}}}}
          Auctionator={API={v1={GetAuctionPriceByItemID=function(_,id)return ({[11]=1,[12]=5})[id]end}}}
          ns.AuctionBridge={GetAuctionSupply=function(id)if id==11 then return {quantity=1,complete=true}end end}
          for _,scheme in ipairs({'matcost','crafts','optim'})do
            local r=ns.ProfRouteAuto.Compute('alchemy',{start=1,target=4,scheme=scheme})
            assert(r.targetReached and r.feasible and r.total==11,scheme)
            local used=0;for _,m in ipairs(r.mats)do if m.id==11 and m.source=='ah'then used=used+m.count end end
            assert(used==1 and r.supplyConstrained,scheme..' overspent auction quantity')
            local cost=0;for _,step in ipairs(r.steps)do cost=cost+step.cost end
            assert(cost==r.total and r.vendorQuoteRevision==4,scheme..' total/stamp mismatch')
          end
        """)

    def test_fixed_route_uses_finite_ah_remainder_or_whole_npc_packs(self):
        self.load(str(ROOT/'Core'/'ProfItemPrices.lua'))
        self.lua.execute("""
          ns.ProfRecipes={alchemy={rows={{101,20,1,'','','',1,20,30,40,false,{{11,6}}}}}}
          ns.EnsureProfRecipes=function()return ns.ProfRecipes end
          ns.ProfItems={[11]={item_id=11,VendorStackCount=4,offers={
            [7]={npc_id=7,stock=-1,cost_copper=37,price_source='client'}}}}
          Auctionator={API={v1={GetAuctionPriceByItemID=function(_,id)if id==11 then return 10 end end}}}
          for _,limit in ipairs({0,1,2,10})do
            ns.AuctionBridge={GetAuctionSupply=function(id)if id==11 then return {quantity=limit,complete=true}end end}
            local steps={{1,2,101,1}}
            local r=ns.ProfRouteAuto.SummarizeSteps(steps,'alchemy')
            local bought=0;for _,m in ipairs(r.mats)do if m.source=='ah'then bought=bought+m.count end end
            assert(bought<=limit and r.total==(limit<2 and 74 or 57),'invalid finite pack allocation')
            assert(#steps==1 and steps[1][4]==1 and steps[1].cost==r.total,'fixed guide changed or costs diverged')
            assert(r.supplyComplete and r.vendorQuoteRevision==4)
          end
        """)

    def test_fixed_route_reserves_formula_ah_copy_before_material_purchase(self):
        self.load(str(ROOT/'Core'/'ProfItemPrices.lua'))
        self.lua.execute("""
          ns.ProfRecipes={alchemy={rows={{101,20,1,'','','',1,20,30,40,false,{{11,2}},{11},{}}}}}
          ns.EnsureProfRecipes=function()return ns.ProfRecipes end
          ns.ProfItems={[11]={item_id=11,VendorStackCount=1,offers={
            [7]={npc_id=7,stock=-1,cost_copper=10,price_source='client'}}}}
          Auctionator={API={v1={GetAuctionPriceByItemID=function(_,id)if id==11 then return 1 end end}}}
          ns.AuctionBridge={GetAuctionSupply=function(id)if id==11 then return {quantity=2,complete=true}end end}
          local steps={{1,2,101,1}}
          local r=ns.ProfRouteAuto.SummarizeSteps(steps,'alchemy')
          assert(r.total==12 and r.formulasTotal==1 and r.formulas[1].source=='ah')
          local ah=r.formulas[1].count
          for _,m in ipairs(r.mats)do if m.source=='ah'then ah=ah+m.count end end
          assert(ah==2 and r.vendorTotal==10 and r.ahTotal==2 and r.supplyComplete)
          assert(steps[1].cost==r.total)
        """)

    def test_legacy_schemes_reject_bound_auction_materials_and_rinfo_exclusions(self):
        self.lua.execute("""
          ns.ProfRecipes={alchemy={rows={{101,20,1,'','','',1,20,30,40,false,{{11,1}}}}}}
          ns.EnsureProfRecipes=function()return ns.ProfRecipes end
          Auctionator={API={v1={GetAuctionPriceByItemID=function()return 7 end}}}
          C_Item={GetItemInfo=function()return 'Bound',nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,1 end}
          for _,scheme in ipairs({'matcost','crafts','optim'})do
            local r=ns.ProfRouteAuto.Compute('alchemy',{start=1,target=2,scheme=scheme})
            assert(not r.targetReached and not r.feasible and #r.steps==0 and r.status=='infeasible',scheme)
          end
          C_Item=nil
          ns.ProfRecipes.alchemy.rows={}
          ns.ProfLeveling={alchemy={rinfo={[101]={makes=20,count=1,learn=1,yellow=20,green=30,grey=40,mats={{11,1}}}}}}
          for _,scheme in ipairs({'matcost','crafts','optim'})do
            local r=ns.ProfRouteAuto.Compute('alchemy',{start=1,target=2,scheme=scheme,exclusions={['alchemy:101']='ban'}})
            assert(#r.steps==0 and not r.feasible,scheme..' ignored rinfo exclusion')
          end
        """)

    def test_profession_api_preserves_primary_slots_and_handles_sparse_results(self):
        self.lua.execute("""
          GetProfessions=function() return 1,nil,3 end
          GetProfessionInfo=function(i)
            if i==1 then return 'Engineering',1,60,75,nil,nil,202 end
            if i==3 then return 'Cooking',1,191,225,nil,nil,185 end
          end
          local p=ns.ProfEconomy.Professions()
          assert(p.engineering.cur==60 and p.engineering.primary)
          assert(p.cooking.cur==191 and not p.cooking.primary)
        """)

    def test_mining_catalogue_and_manual_gap_registry(self):
        self.load(str(ROOT/"Core"/"Data"/"Data_ProfRecipes.lua"))
        self.load(str(ROOT/"Core"/"Data"/"Data_ProfLeveling.lua"))
        self.load(str(ROOT/"Core"/"Data"/"Data_ProfMining.lua"))
        self.lua.execute("""
          local rows=ns.ProfRecipes.mining.rows; assert(#rows==15)
          local seen={}; for _,r in ipairs(rows) do assert(not seen[r[1]]);seen[r[1]]=true; assert(r[2]~=12360) end
          assert(ns.ProfRecipeMeta[1306126].station=='moltenFoundry')
          assert(rows[1][3]==1 and rows[3][3]==2,'spell effect display was treated as output quantity')
          assert(not ns.ProfRecipeMeta[2657].outputConflict and ns.ProfRecipeMeta[1213638].outputConflict)
          local gaps={}; for _,s in ipairs(ns.ProfLeveling.mining.steps) do if s.checkpoint then gaps[#gaps+1]=s end end
          assert(#gaps==2 and gaps[1][1]==140 and gaps[1][2]==155 and gaps[2][1]==185 and gaps[2][2]==300)
        """)

    def test_material_model_migration_removes_obsolete_costs_but_keeps_rules(self):
        self.lua.execute('''
          DungeonsForeverDB={prof={autoNoFormula=true,shopOnlyMiss=true,economy={['Test-Realm']={
            policies={alchemy={['alchemy:101']='ban'}},trainerCosts={[101]=999},
            rankCosts={alchemy={[150]=999}},rankRequirements={alchemy={[150]={level=50}}},
            recipes={[101]={mats={{11,2}},count=1,item=10,tools={5956},toolsKnown=true}}
          }}}}
          assert(ns.ProfEconomy.GetPolicies('alchemy')['alchemy:101']=='ban')
          local d=DungeonsForeverDB.prof.economy['Test-Realm']
          assert(d.materialModel==1 and d.trainerCosts==nil and d.rankCosts==nil and d.rankRequirements==nil)
          assert(d.recipes[101].tools==nil and d.recipes[101].toolsKnown==nil)
          assert(d.recipes[101].mats[1][2]==2 and d.recipes[101].item==10)
          assert(DungeonsForeverDB.prof.autoNoFormula==nil and DungeonsForeverDB.prof.shopOnlyMiss==nil)
        ''')

class SourceValidationTests(unittest.TestCase):
    def test_all_lua_sources_compile_in_lua51(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        compile=lua.eval("function(s,n) local f,e=loadstring(s,n); return f~=nil,e end")
        for path in [*ROOT.joinpath('Core').rglob('*.lua'),*ROOT.joinpath('Locales').rglob('*.lua'),*ROOT.joinpath('Libs').rglob('*.lua')]:
            ok,error=compile(path.read_text(encoding='utf-8-sig'),str(path))
            self.assertTrue(ok,f'{path}: {error}')

    def test_toc_and_xml_files_exist_and_new_load_order_is_valid(self):
        toc=ROOT.joinpath('DungeonsForever.toc').read_text(encoding='utf-8-sig')
        paths=[]
        for line in toc.splitlines():
            line=line.strip()
            if not line or line.startswith('#'): continue
            rel=line.split(' [',1)[0].replace('\\','/')
            self.assertTrue((ROOT/rel).is_file(),rel); paths.append(rel)
        self.assertLess(paths.index('Core/Data/enUS/Data_ProfRecipes.lua'),paths.index('Core/Data/Data_ProfMining.lua'))
        for a,b in [('Core/ProfEconomy.lua','Core/ProfRouteSolver.lua'),('Core/ProfRouteSolver.lua','Core/ProfRouteAuto.lua'),('Core/ProfRouteAuto.lua','Core/ProfessionUI.lua'),('Core/ProfessionUI.lua','Core/ProfFollow.lua')]:
            self.assertLess(paths.index(a),paths.index(b))
        for path in ROOT.joinpath('Libs').rglob('*.xml'):
            tree=ET.parse(path)
            for element in tree.iter():
                file=element.attrib.get('file')
                if file:
                    rel=file.replace('\\','/')
                    self.assertTrue((path.parent/rel).is_file() or (ROOT/rel).is_file(),f'{path}: {file}')

if __name__=='__main__': unittest.main()
