"""Native loading and generated-data delivery contracts, independent of old exports."""
from pathlib import Path
import os
import subprocess
import sys
import unittest
from data_pipeline.professions.first_aid import native_without_first_aid_update

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / 'Core/Data/Data_ProfLearningSources.lua'
BASE = os.environ.get('DF_DELIVERY_DATA_BASE', 'HEAD')


def lua_runtime():
    try:
        from lupa.lua51 import LuaRuntime
    except ImportError:
        sys.path.insert(0, str(ROOT / '.pipeline-runtime/lib'))
        from lupa.lua51 import LuaRuntime
    return LuaRuntime(unpack_returned_tuples=True)


class DeliveryContractTests(unittest.TestCase):
    def test_existing_data_and_locale_toc_entries_are_unchanged(self):
        files = subprocess.check_output(
            ['git', 'ls-tree', '-r', '--name-only', BASE, '--', 'Core/Data'], cwd=ROOT
        ).decode().splitlines()
        self.assertGreater(len(files), 100)
        for name in files:
            if name == 'Core/Data/Data_ProfLearningSources.lua':
                continue
            expected = subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=ROOT)
            self.assertEqual(native_without_first_aid_update(expected.decode('utf8')),
                             native_without_first_aid_update((ROOT / name).read_text(encoding='utf8')), name)
        original = subprocess.check_output(['git', 'show', BASE + ':DungeonsForever.toc'], cwd=ROOT).decode('utf8')
        current = (ROOT / 'DungeonsForever.toc').read_text(encoding='utf8')
        def entries(text):
            return [line for line in text.splitlines() if line.startswith('Core\\Data\\')
                    and 'Data_ProfLearningSources.lua' not in line]
        self.assertEqual(entries(original), entries(current))
        self.assertEqual(current.count('Core\\Data\\Data_ProfLearningSources.lua'), 1)
        self.assertIn('## SavedVariables: DungeonsForeverDB\n', current)
        self.assertIn('## LoadOnDemand: 0\n', current)

    def test_generated_provider_is_forever_only_and_includes_first_aid(self):
        self.assertTrue(DATA.is_file(), 'Build and include the auxiliary Data before delivery')
        source = DATA.read_text(encoding='utf8')
        for forever in (False, True):
            lua = lua_runtime()
            ns = lua.table(IsForever=forever)
            lua.execute("local source,ns=...; assert(loadstring(source))('DungeonsForever',ns)", source, ns)
            provider = ns['ProfLearningSources']
            if not forever:
                self.assertIsNone(provider)
                continue
            self.assertIsNotNone(provider)
            self.assertEqual(provider['meta']['product'], 'wowf')
            self.assertEqual(provider['meta']['schema'], 1)
            self.assertEqual(provider['AutomaticSkillRank']('first-aid',3275),1)
            self.assertIsNotNone(provider['Get']('first-aid',3275))
            self.assertIsNone(provider['Get']('blacksmithing', -1))
            # The relation exists in fresh DB2, but the missing item's unknown
            # requirements must not become an empty confirmed learning route.
            record = provider['Get']('blacksmithing', 2671)
            self.assertIsNotNone(record)
            matches = [route for route in record['routes'].values()
                       if route['teachingItemID'] == 5577]
            self.assertTrue(matches)
            self.assertTrue(all(route['status'] != 'confirmed' or not route['conditionsKnown']
                                for route in matches))


if __name__ == '__main__':
    unittest.main()
