"""Profession-specific audit fixtures for alchemy, engineering and enchanting.

These tests load the native dev data and execute Lua 5.1 domain code. Tests
which compare catalogue facts read only the pinned modularization Git objects;
they do not load its module framework into the production addon.
"""
from pathlib import Path
import subprocess
import unittest

try:
    from validation.test_prof_solver_fusion import LuaRuntime, ROOT
except ModuleNotFoundError:
    from test_prof_solver_fusion import LuaRuntime, ROOT

REFERENCE = "ec184e0d83f9d027e518b95eb0b2545699c5aeea"


class CraftingProfessionAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = LuaRuntime(unpack_returned_tuples=True)
        cls.reference.execute('ns={}')
        for path in (
            'AddOns/DungeonsForever/Framework/CatalogCodec.lua',
            'AddOns/DungeonsForever_RecipeData/Data/Data_ProfCatalog.lua',
            'AddOns/DungeonsForever_RecipeData/Domain/ProfCatalog.lua',
        ):
            source = subprocess.check_output(['git', 'show', REFERENCE + ':' + path], cwd=ROOT, text=True, encoding='utf-8')
            cls.reference.execute("assert(loadstring(...))('DungeonsForever',ns)", source)

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(r'''
          ns={LoadForeverPages=true,L=setmetatable({},{__index=function(_,k)return k end})}
          DungeonsForeverDB={prof={}};callbacks={};frames={};known={};prices={};bag={}
          time=function()return 1000 end;UnitName=function()return 'Audit'end
          GetRealmName=function()return 'Realm'end;UnitLevel=function()return 60 end
          UnitFactionGroup=function()return 'Alliance'end
          IsSpellKnown=function(spell)return known[spell]==true end
          skills={alchemy={cur=225,max=300},engineering={cur=200,max=300},enchanting={cur=100,max=300}}
          ns.Init=function(fn)callbacks[#callbacks+1]=fn end
          C_Timer={After=function()end}
          C_Item={GetItemCount=function(id)return bag[id] or 0 end}
          function CreateFrame()
            local f={events={}}
            function f:RegisterEvent(e)self.events[e]=true end
            function f:UnregisterEvent(e)self.events[e]=nil end
            function f:SetScript(k,fn)self[k]=fn end
            frames[#frames+1]=f;return f
          end
          function solveOne(slug,rec,start,target,extra)
            local s={recipes={rec},known={[slug..':'..rec.spell]=true},prices={},
              professions={[slug]={cur=start,max=300}},level=60,faction='A',coverageComplete=true}
            for _,m in ipairs(rec.mats or {})do s.prices[m[1]]=1 end
            local opts=extra or {};opts.snapshot=s;opts.start=start;opts.target=target
            opts.recoveryEnabled=false;opts.autoCraftTools=false
            local result,job=ns.ProfRouteSolver.Compute(slug,opts)
            assert(not job.error,tostring(job.error));return result,job
          end
        ''')
        self.load = self.lua.eval("function(source)assert(loadstring(source))('DungeonsForever',ns)end")
        for name in ("Data_ProfRecipes", "Data_ProfLeveling", "Data_ProfTools", "Data_ProfSpecializations", "Data_ProfSpecializationQuests"):
            self.load((ROOT / "Core" / "Data" / (name + ".lua")).read_text(encoding="utf-8-sig"))
        for name in ("ProfPolicies", "ProfGates", "ProfEssences", "ProfClientScan", "ProfSolverCapture", "ProfLearning", "ProfRecovery", "ProfRouteSolver", "ProfTrack", "ProfExecution"):
            self.load((ROOT / "Core" / (name + ".lua")).read_text(encoding="utf-8-sig"))
        self.lua.execute(r'''
          ns.ProfEconomy.Professions=function()return skills end
          ns.ProfRouteAuto={AHPriceOf=function(id)return prices[id]end}
        ''')

    def test_alchemy_base_zero_does_not_verify_shared_transmute_cooldown(self):
        self.lua.execute(r'''
          ns.ProfRecipeRuntime=ns.ProfRecipeRuntime or {}
          ns.ProfRecipeRuntime[11479]={cooldown=false}
          local rec=ns.ProfEconomy.FindRecipe('alchemy',11479)
          assert(rec and rec.category=='Transmutes')
          assert(rec.cooldownUnknown==true,'unverified zero base cooldown became an unlimited transmute')
          local r=solveOne('alchemy',rec,225,226)
          assert(not r.feasible,'unverified transmute may not supply a leveling route')
        ''')

    def test_verified_zero_and_positive_transmute_cooldowns_remain_distinct(self):
        self.lua.execute(r'''
          ns.ProfRecipeRuntime=ns.ProfRecipeRuntime or {}
          ns.ProfRecipeRuntime[11479]={cooldown=false,cooldownVerified=true}
          local rec=ns.ProfEconomy.FindRecipe('alchemy',11479)
          assert(rec.cooldown==false and not rec.cooldownUnknown)
          assert(solveOne('alchemy',rec,225,226).feasible)
          ns.ProfRecipeRuntime[11479]={cooldown=true,cooldownVerified=true}
          rec=ns.ProfEconomy.FindRecipe('alchemy',11479)
          assert(rec.cooldown==true and not solveOne('alchemy',rec,225,226).feasible)
        ''')

    def test_mooncloth_uses_the_same_unverified_cooldown_guard(self):
        self.lua.execute(r'''
          ns.ProfRecipeRuntime=ns.ProfRecipeRuntime or {}
          local seed={spell=18560,item=14342,count=1,mats={{14256,2}},
            learn=250,yellow=290,green=305,grey=320}
          ns.ProfRecipeRuntime[18560]={cooldown=false}
          local rec=ns.ProfEconomy.Normalize(seed,'tailoring')
          assert(rec.cooldownUnknown==true,'mooncloth bypassed the unverified cooldown guard')
          assert(not solveOne('tailoring',rec,250,251).feasible)
          ns.ProfRecipeRuntime[18560]={cooldown=false,cooldownVerified=true}
          rec=ns.ProfEconomy.Normalize(seed,'tailoring')
          assert(not rec.cooldownUnknown and solveOne('tailoring',rec,250,251).feasible)
        ''')

    def test_goblin_and_faction_specific_gnomish_prerequisites_survive_capture(self):
        self.lua.execute(r'''
          local function goal(choice,faction)
            local snapshot={targetProfession='engineering',faction=faction,level=60,
              specializationAbilities={[20219]=false,[20222]=false}}
            local context=ns.ProfGates.SpecializationContext({profession='engineering',target=201,
              engineeringSpecialization=choice,snapshot=snapshot,faction=faction,level=60})
            return assert(context.goals[1])
          end
          local goblin=goal('goblin','A')
          assert(goblin.questID==3639 and goblin.prerequisiteQuestIDs and goblin.prerequisiteQuestIDs[1]==3638)
          local alliance=goal('gnomish','A');local horde=goal('gnomish','H')
          assert(alliance.questID==3641 and alliance.prerequisiteQuestIDs[1]==3640)
          assert(horde.questID==3643 and horde.prerequisiteQuestIDs[1]==3642)
          goblin.prerequisiteQuestIDs[1]=0
          assert(ns.ProfSpecializationQuests.goblin.prerequisiteQuestIDs[1]==3638,'goal mutated shared source facts')
        ''')

    def test_enchanting_rods_are_prepared_at_resolved_recipe_learning_skill(self):
        self.lua.execute(r'''
          local E=ns.ProfEconomy
          for _,case in ipairs({{7795,100,6339},{13628,150,11130},{13702,200,11145}})do
            local spell,learn,item=unpack(case)
            local rec=assert(E.FindRecipe('enchanting',spell));assert(rec.learn==learn)
            assert(E.HasToolGoals('enchanting',{target=learn+1,autoCraftTools=true}))
            local s={recipes={rec},professions={enchanting={cur=learn,max=300}},known={}}
            E.CaptureToolGoals(s,'enchanting',{target=learn+1,autoCraftTools=true,snapshot=s})
            local matched
            for _,goal in ipairs(s.toolGoals)do if goal.item==item then matched=goal end end
            assert(matched and matched.minSkill==learn,'rod goal retained the old hard-coded threshold for '..spell)
          end
        ''')

    def test_runtime_alchemist_stone_at_300_does_not_block_level_275(self):
        self.lua.execute(r'''
          local E=ns.ProfEconomy
          ns.ProfRecipeRuntime=ns.ProfRecipeRuntime or {};ns.ProfRecipeRuntime[17632]={learn=300}
          local stone=assert(E.FindRecipe('alchemy',17632));assert(stone.learn==300)
          local potion=assert(E.FindRecipe('alchemy',17555))
          local philosopher=assert(E.FindRecipe('alchemy',11459))
          bag[9149]=1
          local s={recipes={stone,potion,philosopher},known={},prices={},
            professions={alchemy={cur=275,max=300}},level=60,faction='A',coverageComplete=true}
          for _,r in ipairs(s.recipes)do s.known[r.key]=true;for _,m in ipairs(r.mats)do s.prices[m[1]]=1 end end
          local result,job=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=s,start=275,target=276,autoCraftTools=true,recoveryEnabled=false})
          assert(not job.error,tostring(job.error))
          assert(result.feasible and result.targetReached,'300-skill stone blocked the 275-to-276 route')
          for _,goal in ipairs(result.toolGoals or {})do assert(goal.item~=13503)end
        ''')

    def test_engineering_task_finishes_only_after_actual_specialization_is_learned(self):
        self.lua.execute(r'''
          local goal=ns.ProfGates.SpecializationContext({profession='engineering',target=200,
            engineeringSpecialization='goblin',faction='A',level=60,
            snapshot={specializationAbilities={[20219]=false,[20222]=false}}}).goals[1]
          local seg={200,200,0,0,kind='specialization_quest',quest=goal,profession='engineering',
            segmentID='goblin-task',goalSkill=200,expectedGain=0,requiredOutputs={},allocations={}}
          local plan={planVersion=2,executionVersion=1,planID='audit:goblin',slug='engineering',
            status='complete',feasible=true,steps={seg},executionSteps={seg},mats={},formulas={}}
          local xp=ns.ProfExecution;local run=assert(xp.Bind('engineering',plan))
          C_QuestLog={ReadyForTurnIn=function()return true end}
          xp.Sync('engineering');assert(not xp.Progress('engineering',1).complete)
          known[20222]=true;ns.ProfGates.Invalidate();xp.Sync('engineering')
          assert(xp.Progress('engineering',1).complete and run.currentIndex==2,
            'learning Goblin Engineering never completed the specialization task')
        ''')

    def test_unknown_gnomish_faction_keeps_a_blocked_specialization_obligation(self):
        self.lua.execute(r'''
          UnitFactionGroup=function()return nil end
          local s={recipes={},known={},professions={engineering={cur=200,max=300}},level=60,
            specializationAbilities={[20219]=false,[20222]=false}}
          local opts={snapshot=s,start=200,target=200,engineeringSpecialization='gnomish',
            autoCraftTools=false,recoveryEnabled=false}
          local context=ns.ProfGates.SpecializationContext({profession='engineering',target=200,
            snapshot=s,engineeringSpecialization='gnomish'})
          assert(context.goals[1] and context.goals[1].blockedReason=='specializationFactionUnknown',
            'unknown faction silently removed the selected specialization task')
          local r,j=ns.ProfRouteSolver.Compute('engineering',opts)
          assert(not j.error,tostring(j.error));assert(not r.targetReached)
        ''')

    def test_specialization_observation_preserves_unknown_and_modern_false(self):
        self.lua.execute(r'''
          assert(type(ns.ProfEconomy.SpecializationKnown)=='function','missing execution observation API')
          C_SpellBook={IsSpellKnown=function()return false end}
          IsSpellKnown=function()return true end
          assert(ns.ProfEconomy.SpecializationKnown(20222)==false)
          C_SpellBook=nil;IsSpellKnown=nil
          assert(ns.ProfEconomy.SpecializationKnown(20222)==nil)
          IsLoggedIn=function()return false end;IsPlayerSpell=function()return true end
          assert(ns.ProfEconomy.SpecializationKnown(20222)==nil)
        ''')

    def test_existing_profession_seed_thresholds_accept_explicit_client_observations(self):
        # These are simulated observations for the runtime override algorithm,
        # not evidence that the current game client uses these requirements.
        normalize = self.lua.eval(r'''function(slug,spell,learn)
          local before=ns.ProfEconomy.FindRecipe(slug,spell)
          assert(before,'expected existing native seed')
          ns.ProfRecipeRuntime=ns.ProfRecipeRuntime or {};ns.ProfRecipeRuntime[spell]={learn=learn}
          return ns.ProfEconomy.FindRecipe(slug,spell).learn
        end''')
        for slug, spell, observed in (('alchemy', 17632, 300), ('engineering', 3918, 20),
                                      ('enchanting', 7421, 5), ('enchanting', 7418, 20)):
            self.assertEqual(normalize(slug, spell, observed), observed)

    def test_learning_algorithm_does_not_inject_reference_facts_into_native_seeds(self):
        self.lua.execute(r'''
          assert(ns.ProfLearningConditions==nil and ns.ProfLearningConditionsMeta==nil)
          local E=ns.ProfEconomy
          assert(E.LearningPolicyFingerprint()=='native-learning:3:dev-data')
          for _,case in ipairs({{'alchemy',17632},{'engineering',3918},{'enchanting',7418}})do
            local recipe=assert(E.FindRecipe(case[1],case[2]))
            assert(recipe.learningRoutes==nil and recipe.learningConstraints==nil)
            assert(recipe.learningConditionSource==nil,'reference provenance was fabricated')
          end
        ''')

    def test_runtime_only_recipe_is_an_explicit_unmigrated_catalogue_boundary(self):
        # Audit evidence: runtime corrections currently enrich existing seeds;
        # they do not import a recipe absent from the dev candidate catalogue.
        self.assertIsNotNone(self.reference.globals().ns.ProfCatalog.GetRecipe(2330, 'alchemy'))
        self.lua.execute(r'''
          assert(ns.ProfEconomy.FindRecipe('alchemy',2330)==nil)
          ns.ProfRecipeRuntime=ns.ProfRecipeRuntime or {}
          ns.ProfRecipeRuntime[2330]={learned=true,available=true,validated=true,learn=1,item=118,count=1,
            mats={{2447,1},{765,1},{3371,1}}}
          local s=ns.ProfEconomy.Capture('alchemy',{target=2,autoCraftTools=false})
          assert(not s.byKey['alchemy:2330'],'update this audit boundary when runtime-only import is implemented')
          assert(s.coverageComplete==false,'partial native catalogue must not claim complete coverage')
        ''')

    def test_engineering_runtime_minimum_yield_controls_recursive_parts_batches(self):
        self.lua.execute(r'''
          ns.ProfRecipeRuntime=ns.ProfRecipeRuntime or {}
          ns.ProfRecipeRuntime[3922]={count=2,outputMin=2,outputMax=3,variableOutput=true}
          local E=ns.ProfEconomy;local recipes={E.FindRecipe('engineering',3922),
            E.FindRecipe('engineering',3924),E.FindRecipe('engineering',3977)}
          assert(recipes[1].count==2 and recipes[1].outputMin==2 and recipes[1].outputMax==3)
          local s={recipes=recipes,known={},professions={engineering={cur=60,max=300}},
            prices={[2840]=2,[2880]=1,[774]=1,[4359]=100,[4361]=100},coverageComplete=true}
          for _,r in ipairs(recipes)do s.known[r.key]=true end
          local r,j=ns.ProfRouteSolver.Procure(s,4405,2,{autoCraftTools=false,recoveryEnabled=false})
          assert(not j.error,tostring(j.error));assert(r.feasible and r.total==14,tostring(r.total))
          local bolts,scopes=0,0
          for _,a in ipairs(r.actions)do if a.type=='craft' then
            if a.spell==3922 then bolts=bolts+a.count elseif a.spell==3977 then scopes=scopes+a.count end
          end end
          assert(bolts==1 and scopes==2,'dependency batching ignored the confirmed minimum yield')
        ''')

    def test_enchant_without_item_output_completes_from_skill_and_cast_facts(self):
        self.lua.execute(r'''
          local rec=assert(ns.ProfEconomy.FindRecipe('enchanting',7418))
          assert(not rec.item and rec.count==0)
          local r=solveOne('enchanting',rec,20,21)
          assert(r.targetReached and #r.saleOutputs==0,'an enchant invented a sellable output')
          skills.enchanting.cur=20
          local xp=ns.ProfExecution;local run=assert(xp.Bind('enchanting',r))
          xp.RecordAttempt('enchanting',7418,'enchant-cast');skills.enchanting.cur=21;xp.Sync('enchanting')
          local progress=xp.Progress('enchanting',1)
          assert(progress.complete and progress.skillDone and progress.materialDone)
          assert(progress.pendingOutputs==0 and run.currentIndex==2)
        ''')


if __name__ == '__main__':
    unittest.main()
