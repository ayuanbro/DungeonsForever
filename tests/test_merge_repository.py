"""Preserve upstream data and keep local pipeline caches out of Git."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(os.environ.get("TEMP", "/tmp")) / "df-lua-runtime"))
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class MergedDataTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("ns={IsTitan=true,LoadForeverPages=true}; function GetLocale() return 'zhCN' end")
        self.load = self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")

    def data(self, *names):
        for name in names:
            self.load(str(ROOT / "Core" / "Data" / (name + ".lua")))

    def test_upstream_dungeon_routes_and_quest_locations_coexist(self):
        self.data("Data_DungeonQuests", "Data_Route", "Data_QuestStartNpc", "Data_QuestStartLoc", "Data_QuestEndNpc", "Data_NPCLoc")
        self.lua.execute("""
            assert(next(ns.DungeonRoute) and next(ns.DungeonRouteNote))
            assert(next(ns.DungeonQuestExtInfo) and next(ns.DungeonQuestStartNpc))
            assert(ns.DungeonQuestStartLoc[132][1] == 266)
            assert(ns.DungeonQuestEndNpc[96984][1] == 2410)
            assert(ns.NPCLoc[269127] and ns.QuestPreNpcID[95663] == 2787)
            local found={}
            for _,rows in pairs(ns.DungeonQuests) do
                for _,q in ipairs(rows) do found[q[1]]=q end
            end
            for _,id in ipairs({96800,97287,92459,92432,92434}) do assert(found[id],id) end
            assert(found[95682][9][1] == 95663)
            assert(found[96395][2] ~= 'A' and found[96403][2] ~= 'A')
        """)

    def test_upstream_class_rotation_macros_and_quest_chains_remain(self):
        self.data("Data_ClassCombat", "Data_ClassQuest")
        self.lua.execute("""
            assert(next(ns.ClassCombat.rotation) and next(ns.ClassCombat.macros))
            assert(#ns.ClassQuestChains.WARRIOR > 0 and #ns.ClassQuestChains.DRUID > 0)
            assert(next(ns.ClassQuestInfo) and next(ns.ClassQuestItemName))
        """)

    def test_upstream_black_market_and_new_collectibles_remain(self):
        self.data("Data_CollectionMounts", "Data_CollectionPets", "Data_NameOverrides")
        self.lua.execute("""
            local mounts,pets={},{}
            for _,r in pairs(ns.CollectionMounts) do mounts[r[1]]=r end
            for _,r in pairs(ns.CollectionPets) do pets[r[1]]=r end
            assert(mounts[23720][4] == 'bmah')
            for _,id in ipairs({286756,286727,286724}) do
                assert(mounts[id] and ns.NameOverrides.item[id],id)
            end
            for _,id in ipairs({98550,275818,229368}) do
                assert(pets[id] and ns.NameOverrides.item[id],id)
            end
        """)

    def test_gear_quest_sources_keep_updated_faction_compatibility(self):
        self.data("Data_Gear")
        self.lua.globals().ns.EnsureGearData()
        self.lua.execute("""
            assert(next(ns.GearSrcQ) and next(ns.GearSrcQLv))
            assert(ns.GearQuestRace[96403] == nil)
            assert(ns.GearQuestRace[96800] == 'a')
        """)


class GitIgnoreTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("git") and (ROOT / ".git").exists(), "requires the Git checkout")
    def test_pipeline_caches_are_ignored_and_sources_and_generated_data_are_retained(self):
        paths = [
            ".implementation-backup/20261017-professions/Core/ProfRouteAuto.lua",
            "tests/__pycache__/test_prof_runtime.cpython-312.pyc",
            "df-prof-pipeline-v1.0/_temp/_fc/cache/index.html",
            "df-prof-pipeline-v1.0/_temp/_fc/reports/audit.json",
            "df-prof-pipeline-v1.0/_temp/_fc/i18n/batch_A.txt",
            "df-prof-pipeline-v1.0/_temp/_fc/i18n/zh_A.txt",
            "df-prof-pipeline-v1.0/Core/Data/Data_ProfRecipes.lua",
            "df-prof-pipeline-v1.0/Core/Data/Data_ProfItems.lua",
            "df-prof-pipeline-v1.0/_temp/_fc/data/DataProfItems.csv",
            "df-prof-pipeline-v1.0/_temp/fc_prof_items.py",
            "df-prof-pipeline-v1.0/_temp/fc_gen.py",
            "df-prof-pipeline-v1.0/_temp/_fc/data/vendor_loc.json",
            "df-prof-pipeline-v1.0/_temp/_fc/i18n/zh.json",
            "df-prof-pipeline-v1.0/_temp/questie/questie_forever.json",
            "Core/Data/Data_ProfRecipes.lua",
            "Core/Data/Data_ClassQuest.lua",
            "Media/textures/route_dot.tga",
            "tests/test_prof_runtime.py",
        ]
        result = subprocess.run(
            ["git", "--no-optional-locks", "check-ignore", "--no-index", "-z", "--stdin"],
            input=("\0".join(paths) + "\0").encode("utf-8"), cwd=ROOT,
            capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        ignored = set(result.stdout.decode("utf-8").rstrip("\0").split("\0"))
        self.assertEqual(ignored, set(paths[:4]))

    def test_pipeline_keeps_scripts_and_required_inputs_in_its_own_root(self):
        pipeline = ROOT / "df-prof-pipeline-v1.0"
        for rel in [
            "README.md", "run.bat", "_temp/fc_update.py", "_temp/fc_gen.py",
            "_temp/tools/wow_stub.lua", "_temp/_fc/data/index.json",
            "_temp/_fc/data/vendor_loc.json", "_temp/_fc/i18n/zh.json",
            "_temp/questie/questie_forever.json", "_temp/_wago_AreaTable_zh.csv",
        ]:
            self.assertTrue((pipeline / rel).is_file(), rel)

    def test_canonical_pipeline_contains_maintenance_and_unified_steps(self):
        pipeline = ROOT / 'df-data-pipeline'
        for rel in ('_temp/fc_update.py', '_temp/fc_pipeline.py', '_temp/fc_pipeline_common.py',
                    '_temp/fc_prof_items.py', '_temp/fc_refresh_specializations.py',
                    '_temp/fc_locales.py', '_temp/_fc/maintenance/professions.json',
                    '_temp/_fc/maintenance/locales.json', 'requirements.txt'):
            self.assertTrue((pipeline / rel).is_file(), rel)

    def test_archived_entrypoint_fails_without_touching_the_commit_marker(self):
        marker = ROOT / 'df-data-pipeline/_temp/_fc/cache/.pipeline-state/current.json'
        before = marker.read_bytes() if marker.exists() else None
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'df-prof-pipeline-v1.0/_temp/fc_update.py'),
                                 '--apply', '--offline'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('archived and disabled', result.stderr)
        self.assertIn('df-data-pipeline', result.stderr)
        self.assertEqual(marker.read_bytes() if marker.exists() else None, before)


if __name__ == "__main__":
    unittest.main()
