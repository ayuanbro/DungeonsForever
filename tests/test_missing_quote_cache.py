"""Reject legacy unquoted route snapshots once while retaining priced results."""
import unittest

from test_prof_runtime import LuaRuntime, MOCKS, ROOT


class MissingQuoteCacheTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.load = self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        for name in ("ProfEconomy.lua", "ProfRouteSolver.lua", "ProfRouteAuto.lua"):
            self.load(str(ROOT / "Core" / name))
        self.lua.execute(r'''
          captures=0
          ns.ProfEconomy.Capture=function()
            captures=captures+1
            return ns.ProfEconomy.Index(fixture())
          end
        ''')

    def migrate(self, marker):
        self.lua.globals().MARKER = marker
        self.lua.execute(r'''
          local r=finish('alchemy',{start=1,target=2})
          assert(r.feasible and r.targetReached and r.total==7 and captures==1)
          local cache=DungeonsForeverDB.prof.routeCache['Test-Realm']
          local old=cache.routes[cache.active.alchemy].result
          if MARKER=='material' then old.mats[1].unpriced=true
          else old[MARKER]=true end
          queueBefore=#queue
        ''')
        self.load(str(ROOT / "Core" / "ProfRouteAuto.lua"))
        self.lua.execute(r'''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
          assert(r.status=='searching' and not r.cached and #queue==queueBefore+1,
            'legacy unquoted result was displayed from the saved cache')
          assert(captures==1,'restoring the tab ran synchronous route search')
          local pending=r
          assert(ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})==pending)
          assert(#queue==queueBefore+1,'pending migration started multiple jobs')
          r=finish('alchemy',{start=1,target=2})
          assert(r.feasible and r.targetReached and r.total==7 and captures==2)
          assert(r.completeCost and not r.pricePending and not r.referenceRoute)
          for _,m in ipairs(r.mats) do assert(not m.unpriced) end
          queueAfter=#queue
        ''')
        self.load(str(ROOT / "Core" / "ProfRouteAuto.lua"))
        self.lua.execute(r'''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
          assert(r.cached and r.feasible and r.targetReached and r.total==7)
          assert(r.completeCost and captures==2 and #queue==queueAfter,
            'a valid priced result restarted its migration on the next tab open')
        ''')

    def test_legacy_price_pending_route_is_recomputed_once(self):
        self.migrate("pricePending")

    def test_legacy_reference_route_is_recomputed_once(self):
        self.migrate("referenceRoute")

    def test_legacy_unpriced_material_is_recomputed_once(self):
        self.migrate("material")


if __name__ == "__main__":
    unittest.main()
