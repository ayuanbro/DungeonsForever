"""Per-profession audit: real dev smithing, leatherworking and tailoring inputs.

These are offline model/source checks. The stubbed client is not game evidence.
"""
from pathlib import Path
import unittest

try:
    from validation.test_prof_native_data import native_runtime, ROOT
except ModuleNotFoundError:
    from test_prof_native_data import native_runtime, ROOT

PROFESSIONS = ('blacksmithing', 'leatherworking', 'tailoring')


def load(lua, name):
    lua.execute("assert(loadstring(...))('DungeonsForever',ns)",(ROOT/name).read_text(encoding='utf-8-sig'))


def audit_runtime(locale='zhCN', route=False):
    lua=native_runtime(locale)
    if not lua.execute('return type(ns.ProfEconomy.LearningPolicyFingerprint)=="function"'):
        load(lua,'Core/ProfLearning.lua')
    if route:
        lua.execute("""
          function CreateFrame()local f={};function f:RegisterEvent()end;function f:SetScript()end;return f end
          C_Timer={After=function()end}
        """)
        load(lua,'Core/ProfRouteAuto.lua')
    return lua


class CraftingBProfessionAuditTests(unittest.TestCase):
    def test_real_starting_recipes_solve_in_each_shipped_locale(self):
        for locale in ('zhCN','zhTW','enUS'):
            lua=audit_runtime(locale)
            for profession,spell,item,material in (
                ('blacksmithing',2660,2862,{2835:1}),
                ('leatherworking',2152,2304,{2318:1}),
                ('tailoring',2963,2996,{2589:2}),
            ):
                with self.subTest(locale=locale,profession=profession):
                    lua.globals().selected=profession
                    lua.globals().testSpell=spell
                    lua.execute('observedKnown={[testSpell]=true}')
                    recipe=lua.execute('return ns.ProfEconomy.FindRecipe(selected,testSpell)')
                    self.assertEqual(recipe['item'],item)
                    self.assertEqual({m[1]:m[2] for _,m in recipe['mats'].items()},material)
                    result=lua.execute("""
                      return ns.ProfRouteSolver.Compute(selected,{start=1,target=2,learnedOnly=true,
                        autoCraftTools=true,recoveryEnabled=false,cpuLimitMs=1000})
                    """)[0]
                    self.assertTrue(result['feasible'])
                    self.assertEqual(result['steps'][1][3],spell)
                    self.assertEqual(result['steps'][1][2],2)
                    self.assertEqual(result['total'],sum(material.values()))
                    self.assertFalse(result['optimal'])

    def test_every_fixed_segment_has_resolved_materials_and_valid_dev_skill_range(self):
        for locale in ('zhCN','zhTW','enUS'):
            lua=audit_runtime(locale)
            for profession in PROFESSIONS:
                with self.subTest(locale=locale,profession=profession):
                    lua.execute("""
                      local profession=...;selected=profession
                      local E=ns.ProfEconomy
                      for index,step in ipairs(ns.ProfLeveling[profession].steps)do
                        local recipe=E.FindRecipe(profession,step[3])
                        assert(recipe,'missing fixed recipe '..step[3])
                        assert(not recipe.clientPending,'unknown material/output '..step[3])
                        assert(recipe.learn<=step[1] and recipe.grey>step[1], 'invalid dev fixed skill '..step[3])
                        assert(type(recipe.mats)=='table' and #recipe.mats>0)
                        for _,mat in ipairs(recipe.mats)do
                          assert(type(mat[1])=='number' and mat[1]>0 and type(mat[2])=='number' and mat[2]>0)
                        end
                        assert(not recipe.cooldown and not recipe.cooldownUnknown, 'cooldown fixed recipe '..step[3])
                      end
                      local snapshot=E.Capture(profession,{start=1,target=2,autoCraftTools=true,recoveryEnabled=false})
                      assert(#snapshot.toolGoals==0,'unrelated tool goals leaked into '..profession)
                    """,profession)

    def test_fixed_routes_reject_client_confirmed_unavailable_recipes(self):
        for profession,spell in (('blacksmithing',2660),('leatherworking',2152),('tailoring',2963)):
            with self.subTest(profession=profession):
                lua=audit_runtime(route=True)
                lua.execute("""
                  local profession,spell=...;selected=profession
                  ns.ProfEconomy.EnsureClientRuntime()
                  ns.ProfRecipeRuntime[spell]={available=false,validated=true}
                  local recipe=ns.ProfEconomy.FindRecipe(profession,spell)
                  assert(recipe.clientUnavailable)
                  local kept,blocked=ns.ProfRouteAuto.FilterFixedSpecializations(profession,{{1,2,spell,1}},{target=2})
                  assert(#kept==0 and #blocked==1,'fixed route ignored client unavailability '..profession)
                  assert(blocked[1].reason=='clientUnavailable')
                """,profession,spell)

    def test_all_smith_and_leather_specialization_families_are_checked(self):
        lua=audit_runtime()
        for profession,spell,ability in (
            ('blacksmithing',9954,9788),('blacksmithing',16995,9787),
            ('blacksmithing',16992,17039),('blacksmithing',16993,17040),('blacksmithing',16994,17041),
            ('leatherworking',19050,10656),('leatherworking',19059,10658),('leatherworking',19062,10660),
        ):
            with self.subTest(profession=profession,spell=spell):
                lua.execute("""
                  local profession,spell,ability=...;local E=ns.ProfEconomy
                  local recipe=assert(E.FindRecipe(profession,spell))
                  assert(ns.ProfGates.RequiredAbility(spell)==ability)
                  local snapshot={known={},level=60,classID=1,raceID=1,
                    professions={[profession]={cur=300,max=300}},specializationAbilities={[ability]=false}}
                  local allowed,reason=E.RecipeSpecializationAllowed(recipe,snapshot,{skill={[profession]=300},specializationAbilities={}})
                  assert(not allowed and reason=='specializationRequired')
                  allowed=E.RecipeSpecializationAllowed(recipe,snapshot,
                    {skill={[profession]=300},specializationAbilities={[ability]=true}})
                  assert(allowed,'matching specialization was incorrectly excluded '..spell)
                """,profession,spell,ability)

    def test_leather_fixed_tribal_recipe_is_not_a_universal_step(self):
        lua=audit_runtime(route=True)
        lua.execute("""
          local target
          for _,step in ipairs(ns.ProfLeveling.leatherworking.steps)do if step[3]==19066 then target=step end end
          assert(target and target[1]==258)
          assert(ns.ProfGates.RequiredAbility(19066)==10660)
          function IsPlayerSpell(id)return false end
          ns.ProfGates.Invalidate()
          local kept,blocked=ns.ProfRouteAuto.FilterFixedSpecializations('leatherworking',{target},{target=300})
          assert(#kept==0 and #blocked==1,'tribal leather step silently became universal')
          assert(blocked[1].reason=='specializationRequired')
        """)

    def test_tailoring_race_and_acquisition_masks_are_native_source_data_gaps(self):
        lua=audit_runtime()
        lua.execute("""
          assert(ns.ProfLearningConditions==nil and ns.ProfLearningConditionsMeta==nil)
          local E=ns.ProfEconomy
          for _,spell in ipairs({1229504,1263425})do
            local recipe=assert(E.FindRecipe('tailoring',spell))
            assert(recipe.learningConstraints==nil and recipe.learningRoutes==nil)
            assert(recipe.learningConditionSource==nil)
            assert(ns.ProfGates.RequiredAbility(spell)==0)
            local allowed,reason,detail=E.LearningEligibility(recipe,{known={},level=60,raceID=1,classID=1,
              professions={tailoring={cur=300,max=300}},specializationAbilities={}})
            assert(allowed and reason==nil and detail.status=='unknown',
              'missing dev restriction data was represented as confirmed eligibility')
          end
        """)

    def test_explicit_synthetic_race_mask_and_unknown_acquisition_mask_algorithm(self):
        lua=audit_runtime()
        # Standalone caller-supplied fixture: these are not native recipe facts.
        lua.execute("""
          local E=ns.ProfEconomy
          local mask={kind='raceMask',value=8589934770}
          local recipe={spell=900001,profession='tailoring',learningConstraints={mask,
            {kind='abilityRaceMask0',text='18446744072387644493'}}}
          local snapshot={known={},level=60,raceID=1,classID=1,
            professions={tailoring={cur=300,max=300}},specializationAbilities={}}
          local allowed,reason,detail=E.LearningEligibility(recipe,snapshot)
          assert(not allowed and reason=='specializationRequired' and detail.status=='blocked')
          snapshot.raceID=2
          allowed,reason,detail=E.LearningEligibility(recipe,snapshot)
          assert(not allowed and reason=='clientDataPending' and detail.status=='unknown',
            'nonzero 64-bit acquisition masks were guessed away')
          local probe={spell=900001,profession='tailoring',_conditionsCheck={mask}}
          assert(E.LearningEligibility(probe,snapshot),'supported race-mask bit should permit race 2')
          snapshot.known['tailoring:900001']=true
          snapshot.raceID=1
          assert(E.LearningEligibility(recipe,snapshot),'positive learned evidence was discarded')
        """)

    def test_explicit_synthetic_64bit_acquisition_mask_keeps_exact_text_and_unknown(self):
        lua=audit_runtime()
        lua.execute("""
          local E=ns.ProfEconomy
          local seed={spell=900003,profession='tailoring',learningConstraints={
            {kind='abilityRaceMask0',text='18446744072387644493'}}}
          local recipe=E.ResolveRecipe(seed,'tailoring')
          local allowed,reason,detail=E.LearningEligibility(recipe,{known={},level=60,raceID=1,classID=1,
            professions={tailoring={cur=300,max=300}},specializationAbilities={}})
          assert(not allowed and reason=='clientDataPending' and detail.status=='unknown')
          local exactText
          for _,condition in ipairs(recipe.learningConstraints)do
            if condition.kind=='abilityRaceMask0'then exactText=condition.text;assert(condition.value==nil)end
          end
          assert(exactText=='18446744072387644493','64-bit evidence lost exact source text')
          recipe.learningConstraints[1].text='changed'
          assert(seed.learningConstraints[1].text=='18446744072387644493','resolver mutated caller conditions')
        """)

    def test_real_formula_items_use_indivisible_vendor_bundles_or_auction(self):
        lua=audit_runtime()
        for profession,spell,formula in (('blacksmithing',2667,2881),('leatherworking',2158,2406),('tailoring',2389,2598)):
            with self.subTest(profession=profession):
                lua.execute("""
                  local profession,spell,formula=...;local E=ns.ProfEconomy
                  local recipe=assert(E.FindRecipe(profession,spell));assert(recipe.formula==formula)
                  local snapshot={known={},prices={[formula]=50},formulaOffers={[formula]={{price=80,quantity=2,unlimited=true}}}}
                  local quote=E.FormulaFor(recipe,snapshot)
                  assert(quote and quote.source=='ah' and quote.cost==50)
                  snapshot.prices={};quote=E.FormulaFor(recipe,snapshot)
                  assert(quote.source=='vendor' and quote.cost==80 and quote.count==2)
                """,profession,spell,formula)

    def test_mooncloth_cooldown_is_excluded_until_positive_client_verification(self):
        lua=audit_runtime()
        lua.execute("""
          local E=ns.ProfEconomy
          local recipe=E.FindRecipe('tailoring',18560)
          assert(recipe and recipe.cooldownUnknown)
          local snapshot={recipes={recipe},known={['tailoring:18560']=true},professions={tailoring={cur=230,max=300}},
            prices={[14256]=1},coverageComplete=false,toolGoals={},specializationContext={}}
          local result=ns.ProfRouteSolver.Compute('tailoring',{snapshot=snapshot,start=230,target=231,
            autoCraftTools=false,recoveryEnabled=false,cpuLimitMs=1000})
          assert(not result.feasible and #result.steps==0)
          E.EnsureClientRuntime()
          ns.ProfRecipeRuntime[18560]={learned=true,cooldown=false,cooldownVerified=true}
          recipe=E.FindRecipe('tailoring',18560)
          assert(recipe.cooldown==false and not recipe.cooldownUnknown)
          snapshot.recipes={recipe}
          result=ns.ProfRouteSolver.Compute('tailoring',{snapshot=snapshot,start=230,target=231,
            autoCraftTools=false,recoveryEnabled=false,cpuLimitMs=1000})
          assert(result.feasible and result.steps[1][3]==18560)
        """)

    def test_alternative_learning_routes_and_frozen_quest_flags_are_respected(self):
        lua=audit_runtime()
        # Independent synthetic routes exercise the generic algorithm; no
        # source projection supplies extra conditions to a native dev recipe.
        lua.execute("""
          local E=ns.ProfEconomy
          local recipe={spell=900005,profession='blacksmithing',formula=900006,learningConstraints={},learningRoutes={
            {kind='item',status='confirmed',conditionsKnown=true,teachingItemID=900006,conditions={{kind='ability',value=9787}}},
            {kind='item',status='confirmed',conditionsKnown=true,teachingItemID=900006,conditions={{kind='ability',value=9788}}},
          }}
          local snapshot={known={},level=60,professions={blacksmithing={cur=100,max=150}},
            specializationAbilities={[9787]=false,[9788]=true}}
          assert(E.LearningEligibility(recipe,snapshot),'alternative valid learning route was dropped')
          recipe.learningRoutes={}
          recipe.learningConstraints={{kind='quest',value=123}}
          C_QuestLog={IsQuestFlaggedCompleted=function()return true end}
          snapshot.completedQuests={[123]=false}
          local allowed=E.LearningEligibility(recipe,snapshot)
          assert(not allowed,'frozen quest flag was overwritten from live state')
          snapshot.completedQuests[123]=true
          assert(E.LearningEligibility(recipe,snapshot))
        """)

    def test_rank_guidance_uses_each_professions_real_cap_and_faction(self):
        lua=audit_runtime()
        load(lua,'Core/Data/Data_ProfTrainers.lua')
        if not lua.execute('return ns.ProfRanks~=nil'):load(lua,'Core/ProfRanks.lua')
        for profession,skill_id in (('blacksmithing',164),('leatherworking',165),('tailoring',197)):
            with self.subTest(profession=profession):
                lua.execute("""
                  local profession,id=...
                  GetProfessions=function()return 1 end
                  GetProfessionInfo=function()return profession,nil,200,150,nil,nil,id end
                  local rank=ns.ProfRanks.NextStep(profession,300)
                  assert(rank and rank.rank==3 and rank.cap==225 and not rank.complete)
                  assert(rank.available and rank.state.maxSkill==150)
                  for _,source in ipairs(rank.sources)do assert(source.faction~='H' and source.map and source.x and source.y)end
                """,profession,skill_id)


if __name__=='__main__':unittest.main()
