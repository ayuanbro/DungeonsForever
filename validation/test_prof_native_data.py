"""Current dev data enters the fused Lua route pipeline in all shipped locales.

The simulated client proves source/schema integration, not in-game availability.
No recipe or material facts are fabricated to fill gaps in the dev data.
"""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.pipeline-runtime'/'lib'))
from lupa.lua51 import LuaRuntime

DATA=[
    'Data_Professions.lua','Data_ProfRecipes.lua','Data_ProfLeveling.lua',
    'Data_ProfSpecializations.lua','Data_ProfSpecializationQuests.lua','Data_ProfTools.lua',
]
DOMAIN=[
    'ProfPolicies.lua','ProfGates.lua','ProfSolverCapture.lua','ProfLearning.lua','ProfClientScan.lua',
    'ProfEssences.lua','ProfRecovery.lua','ProfRouteSolver.lua',
]


def native_runtime(locale='zhCN'):
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute("""
      ns={LoadForeverPages=true,L=setmetatable({}, {__index=function(_,k)return k end})}
      DungeonsForeverDB={prof={}}
      selected='alchemy'; observedKnown={}
      function UnitName()return 'NativeTest'end
      function GetRealmName()return 'Realm'end
      function UnitLevel()return 60 end
      function UnitFactionGroup()return 'Alliance'end
      function IsPlayerSpell(id)return observedKnown[id]==true end
      function time()return 1000 end
      function GetBuildInfo()return '1.60.1',70338 end
      ns.ProfRouteAuto={AHPriceOf=function()return 1 end}
      ns.ProfModule={ProfLearned=function()return {[selected]={cur=1,max=75}}end}
    """)
    lua.globals().testLocale=locale
    lua.execute("function GetLocale()return testLocale end")
    files=[ROOT/'Core'/'Data'/f for f in DATA]
    if locale!='zhCN':
        files.extend(ROOT/'Core'/'Data'/locale/f for f in ('Data_Professions.lua','Data_ProfRecipes.lua','Data_ProfLeveling.lua'))
    files.append(ROOT/'Core'/'Data'/'Data_ProfMining.lua')
    files.extend(ROOT/'Core'/f for f in DOMAIN)
    for path in files:
        lua.execute("assert(loadstring(...))('DungeonsForever',ns)",path.read_text(encoding='utf-8'))
    return lua


class ProfessionNativeDataTests(unittest.TestCase):
    def test_real_catalogue_and_rinfo_solve_short_sections_in_three_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            lua=native_runtime(locale)
            for profession,spell,item,materials in (
                ('alchemy',7183,5997,{765:1,2447:1,3371:1}),
                ('engineering',3918,4357,{2835:1}),
                ('enchanting',7418,None,{247786:1}),
            ):
                with self.subTest(locale=locale,profession=profession):
                    lua.globals().selected=profession
                    lua.globals().testSpell=spell
                    lua.execute('observedKnown={[testSpell]=true}')
                    recipe=lua.execute('return ns.ProfEconomy.FindRecipe(selected,testSpell)')
                    self.assertEqual(recipe['spell'],spell)
                    self.assertEqual(recipe['item'],item)
                    self.assertEqual(recipe['learn'],1)
                    found={m[1]:m[2] for _,m in recipe['mats'].items()}
                    self.assertEqual(found,materials)
                    # Actual tables are captured again by the real solver, not a
                    # fixture-built snapshot or an assertion on catalogue size.
                    result=lua.execute("""
                      return ns.ProfRouteSolver.Compute(selected,{start=1,target=2,learnedOnly=true,
                        autoCraftTools=false,recoveryEnabled=false,cpuLimitMs=1000})
                    """)[0]
                    self.assertTrue(result['feasible'])
                    self.assertGreater(len(result['steps']),0)
                    self.assertEqual(result['steps'][1][3],spell)
                    self.assertEqual(result['steps'][1][2],2)
                    self.assertFalse(result['catalogueCoverageComplete'])
                    self.assertFalse(result['optimal'])

    def test_first_aid_missing_recipe_data_remains_explicit_without_static_injection(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                lua=native_runtime(locale)
                lua.execute("selected='first-aid'")
                self.assertIsNone(lua.execute("return ns.ProfEconomy.FindRecipe('first-aid',3275)"))
                result=lua.execute("""
                  return ns.ProfRouteSolver.Compute(selected,{start=1,target=2,
                    autoCraftTools=false,recoveryEnabled=false,cpuLimitMs=1000})
                """)[0]
                self.assertFalse(result['feasible'])
                self.assertEqual(len(result['steps']),0)
                self.assertIn(result['status'],('infeasible','incomplete'))
                self.assertGreater(len(lua.execute("return ns.ProfLeveling['first-aid'].steps")),0)

    def test_dev_upgrade_rinfo_precedes_new_generic_enchant_reference(self):
        lua=native_runtime()
        lua.execute("""
          selected='enchanting'
          local E=ns.ProfEconomy
          assert(E.FindRecipe(selected,7418).learn==1)
          local generic
          for _,row in ipairs(ns.ProfRecipes.enchanting.enchants)do if row[14]==7418 then generic=row;break end end
          assert(generic and generic[5]==20)
          local snapshot=E.Capture(selected,{target=2,autoCraftTools=false,recoveryEnabled=false})
          assert(snapshot.byKey['enchanting:7418'].learn==1)
          assert(snapshot.byKey['enchanting:7418'].mats[1][1]==247786)
          -- A positive client observation overrides both static representations.
          E.EnsureClientRuntime()
          ns.ProfRecipeRuntime[7418]={learned=true,learn=3,mats={{2447,4}},validated=true}
          assert(E.FindRecipe(selected,7418).learn==3)
          snapshot=E.Capture(selected,{target=4,autoCraftTools=false,recoveryEnabled=false})
          assert(snapshot.byKey['enchanting:7418'].mats[1][1]==2447)
          assert(snapshot.byKey['enchanting:7418'].learn==3)
          assert(generic[5]==20 and ns.ProfLeveling.enchanting.rinfo[7418].learn==1)
        """)

    def test_real_tool_goals_and_cooldown_classification_are_preserved(self):
        lua=native_runtime()
        lua.execute("""
          selected='enchanting';observedKnown={[7418]=true,[7421]=true}
          local snapshot=ns.ProfEconomy.Capture(selected,{target=6,autoCraftTools=true,recoveryEnabled=false})
          assert(snapshot.toolGoals[1].item==6218 and snapshot.toolGoals[1].spell==7421)
          assert(snapshot.byKey['enchanting:7421'].learn==1)
          local result=ns.ProfRouteSolver.Compute(selected,{start=1,target=6,learnedOnly=true,
              autoCraftTools=true,recoveryEnabled=false,cpuLimitMs=1000})
          assert(result.feasible and #result.executionSteps>0)
          local tool=false
          for _,step in ipairs(result.executionSteps)do if step[3]==7421 then tool=true end end
          assert(tool)
          local transmute=ns.ProfEconomy.FindRecipe('alchemy',11479)
          assert(transmute and transmute.category=='Transmutes')
          assert(transmute.cooldown or transmute.cooldownUnknown)
        """)


    def test_engineering_retains_native_gate_without_reference_only_learning_data(self):
        lua=native_runtime()
        lua.execute("""
          local E=ns.ProfEconomy
          local recipe=E.FindRecipe('engineering',8895)
          assert(recipe and ns.ProfGates.RequiredAbility(8895)==20222)
          local snapshot={known={},level=60,professions={engineering={cur=130,max=225}},
              specializationAbilities={[20219]=false,[20222]=false}}
          local allowed,reason=E.RecipeSpecializationAllowed(recipe,snapshot,
              {skill={engineering=130},specializationAbilities={}})
          assert(not allowed and reason=='specializationRequired')
          local detail
          allowed,reason,detail=E.RecipeSpecializationAllowed(recipe,snapshot,
              {skill={engineering=130},specializationAbilities={[20222]=true}})
          assert(allowed and detail.status=='unknown','native dev does not contain the reference-only 225 skill condition')
          assert(recipe.learn==130 and recipe.learningRoutes==nil and recipe.learningConstraints==nil)
          snapshot.professions.engineering.cur=225
          allowed,reason,detail=E.RecipeSpecializationAllowed(recipe,snapshot,
              {skill={engineering=225},specializationAbilities={[20222]=true}})
          assert(allowed and detail.status=='unknown','incomplete reference coverage must remain explicit')
        """)


if __name__=='__main__':unittest.main()
