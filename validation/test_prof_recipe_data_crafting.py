"""Protect the dev generated Data boundary while exercising fused logic."""
from pathlib import Path
import subprocess
import unittest

from test_prof_native_data import native_runtime,ROOT

BASELINE='942a0ca1ae6478dabad4b0885f7abf4011338cc2'


class DevDataPreservationTests(unittest.TestCase):
    def test_every_data_path_and_source_matches_the_original_dev_tree(self):
        expected=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,'--','Core/Data'],cwd=ROOT,text=True).splitlines()
        actual=[p.relative_to(ROOT).as_posix()for p in (ROOT/'Core/Data').rglob('*')if p.is_file()]
        self.assertEqual(sorted(actual),sorted(expected))
        for name in expected:
            with self.subTest(path=name):
                original=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT)
                self.assertEqual((ROOT/name).read_bytes().replace(b'\r\n',b'\n'),original.replace(b'\r\n',b'\n'))

    def test_toc_data_entries_and_locale_loading_rules_are_unchanged(self):
        original=subprocess.check_output(['git','show',BASELINE+':DungeonsForever.toc'],cwd=ROOT).decode('utf-8-sig')
        def data_lines(text):return [line for line in text.splitlines()if line.startswith('Core\\Data\\')]
        self.assertEqual(data_lines((ROOT/'DungeonsForever.toc').read_text(encoding='utf-8-sig')),data_lines(original))

    def test_starting_thresholds_and_mining_yield_retain_dev_values_in_three_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            lua=native_runtime(locale)
            for profession,spell in (('blacksmithing',2660),('leatherworking',2152),('tailoring',2963)):
                with self.subTest(locale=locale,profession=profession):
                    self.assertEqual(lua.eval('ns.ProfEconomy.FindRecipe')(profession,spell)['learn'],1)
            self.assertEqual(lua.eval('ns.ProfEconomy.FindRecipe')('mining',1213638)['count'],2)

    def test_reference_only_recipes_do_not_enter_the_live_candidate_tables(self):
        lua=native_runtime()
        for profession,spell in (('first-aid',3275),('blacksmithing',1224631),('leatherworking',1224615),('tailoring',1224607),('cooking',1225758)):
            with self.subTest(profession=profession,spell=spell):
                self.assertIsNone(lua.eval('ns.ProfEconomy.FindRecipe')(profession,spell))

    def test_real_gray_smelting_still_supplies_materials_without_skill_gain(self):
        lua=native_runtime()
        lua.execute('''
          selected='mining'
          ns.ProfModule.ProfLearned=function()return {mining={cur=165,max=300}}end
          local E=ns.ProfEconomy;E.EnsureClientRuntime();observedKnown[3569]=true
          ns.ProfRecipeRuntime[3569]={learned=true,cooldown=false,cooldownVerified=true}
          local snapshot=E.Capture('mining',{start=165,target=166,autoCraftTools=false,recoveryEnabled=false})
          assert(snapshot.byKey['mining:3569'])
          snapshot.prices[3859]=nil;snapshot.nonAuctionable[3859]=true
          local result=ns.ProfRouteSolver.Procure(snapshot,3859,1,
            {learnedOnly=true,autoCraftTools=false,recoveryEnabled=false,cpuLimitMs=1000})
          assert(result.feasible and result.total==2 and #result.executionSteps==1)
          assert(result.executionSteps[1][3]==3569 and result.executionSteps[1].expectedGain==0)
        ''')


if __name__=='__main__':unittest.main()
