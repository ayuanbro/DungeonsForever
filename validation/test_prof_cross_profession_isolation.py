"""Cross-profession route state must never reuse another profession's data."""
import unittest
from pathlib import Path
import test_prof_route_plans as fixtures


class CrossProfessionIsolation(unittest.TestCase):
    def setUp(self):
        fixtures.NativeRoutePlansTests.setUp(self)

    def test_cache_signature_contains_profession_and_old_foreign_cache_is_ignored(self):
        self.lua.execute(r"""
          local ra=ns.ProfRouteAuto
          local opts={start=1,target=3,scheme='cheapest'}
          local alchemy=ra.PlanSig('alchemy',opts)
          local smith=ra.PlanSig('blacksmithing',opts)
          assert(alchemy~=smith,'professions must not share persisted cache keys')
          -- A legacy cache record with an alien profession must never be reused.
          local o={start=1,target=3,scheme='cheapest'}
          local first=ra.Get('alchemy',o)
          local key='Test-Realm'
          local c=DungeonsForeverDB.prof.routePlans.characters[key]
          assert(c,'missing per-character persisted cache')
          if c then
            c.routes['legacy-foreign']={slug='blacksmithing',model=1,
              result={slug='blacksmithing',steps={{1,3,102,2}},status='complete'}}
            c.active.tailoring='legacy-foreign'
            local current=ra.Get('tailoring',o)
            assert(not current or current.slug~='blacksmithing')
          end
        """)

    def test_async_solver_callback_uses_captured_profession_key(self):
        source=(fixtures.ROOT/'Core'/'ProfessionUI.lua').read_text(encoding='utf-8-sig')
        self.assertIn('local runSerial = PD.solverRunSerial',source)
        self.assertIn('if not isCurrent(j) then return end',source)
        self.assertIn('PD.autoSnapshotSlug = slug',source)
        self.assertIn('PD.autoKey = requestKey',source)
        self.assertIn('if res and res.slug and res.slug~=PD.cur then res=nil end',source)


if __name__ == '__main__':
    unittest.main()
