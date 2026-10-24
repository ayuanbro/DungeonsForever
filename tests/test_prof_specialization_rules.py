"""Specialization data and current character knowledge govern learning routes."""
import unittest

from test_prof_runtime import LuaRuntime, MOCKS, ROOT


class SpecializationRuleTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.load = self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        for path in ("Data/Data_ProfSpecializations.lua", "Data/Data_ProfSpecializationQuests.lua", "ProfEconomy.lua"):
            self.load(str(ROOT / "Core" / path))
        self.lua.execute("""
          E=ns.ProfEconomy
          function r(id,formula)
            return {spell=id,profession='engineering',key='engineering:'..id,formula=formula}
          end
          function s(a) return {known={},specializationAbilities=a or {},professions={engineering={cur=200,max=300}}} end
        """)

    def test_modern_known_api_is_preferred_and_absent_is_unknown(self):
        self.lua.execute("""
          assert(E.SpecializationKnown(20219)==nil)
          C_SpellBook={IsSpellKnown=function(id) return id==20219 end}
          IsSpellKnown=function() return true end
          assert(E.SpecializationKnown(20219)==true)
          assert(E.SpecializationKnown(20222)==false)
          assert(E.Known(20219) and not E.Known(20222))
          C_SpellBook.IsSpellKnown=function() error('not ready') end
          assert(E.SpecializationKnown(20222)==true)
          IsSpellKnown=nil
          assert(E.SpecializationKnown(20222)==nil)
          C_SpellBook.IsSpellKnown=function() return false end
          IsLoggedIn=function() return false end
          assert(E.SpecializationKnown(20222)==nil,'pre-login false was treated as unlearned')
        """)

    def test_choices_are_validated_and_scoped_per_character(self):
        self.lua.execute("""
          invalidations=0; ns.ProfRouteAuto={Invalidate=function() invalidations=invalidations+1 end}
          assert(E.GetEngineeringSpecialization()=='none')
          assert(E.SetEngineeringSpecialization('goblin'))
          assert(E.SetEngineeringSpecialization('goblin') and invalidations==1)
          assert(not E.SetEngineeringSpecialization('guess'))
          UnitName=function() return 'Other' end
          assert(E.GetEngineeringSpecialization()=='none')
          UnitName=function() return 'Test' end
          assert(E.GetEngineeringSpecialization()=='goblin')
        """)

    def test_positive_requirement_is_not_bypassed_by_pending_item_route(self):
        self.lua.execute("""
          local recipe=r(12760,221338)
          local ok,why,detail=E.LearningEligibility(recipe,s({[20219]=true,[20222]=false}))
          assert(not ok and why=='specializationRequired' and detail.requiredAbility==20222)
          assert(ns.ProfSpecializations[12760].hasPending)
          assert(E.LearningEligibility(recipe,s({[20222]=true})))
          assert(E.LearningEligibility(recipe,s(),{specializationAbilities={[20222]=true}}))
        """)

    def test_plain_pending_and_absent_recipes_remain_reference_candidates(self):
        self.lua.execute("""
          local ok,why,detail=E.LearningEligibility(r(3963),s())
          assert(ok and why==nil and detail.status=='unknown')
          assert(E.LearningEligibility(r(12720),s()))
          assert(E.LearningEligibility(r(99999999),s()))
        """)

    def test_learned_recipe_bypasses_learning_but_not_client_unavailable(self):
        self.lua.execute("""
          local recipe=r(12760);local snap=s()
          snap.known[recipe.key]=true
          assert(E.LearningEligibility(recipe,snap))
          recipe.clientUnavailable=true
          local ok,why=E.LearningEligibility(recipe,snap)
          assert(not ok and why=='clientUnavailable')
        """)

    def test_other_profession_requirements_and_route_identity_are_used(self):
        self.lua.execute("""
          ns.ProfSpecializations[1]={status='confirmed',routes={
            {kind='item',itemID=100,requiredAbility=9788,status='confirmed'},
            {kind='trainer',requiredAbility=9787,status='confirmed'}}}
          local recipe={spell=1,profession='blacksmithing',formula=100}
          assert(not E.LearningEligibility(recipe,s({[9787]=true})))
          recipe.learnSource='trainer'
          assert(E.LearningEligibility(recipe,s({[9787]=true})))
          recipe.learnSource=nil
          assert(E.LearningEligibility(recipe,s({[9788]=true})))
        """)

    def test_explicit_unrestricted_route_is_distinct_from_unknown_zero(self):
        self.lua.execute("""
          ns.ProfSpecializations[1]={routes={
            {kind='trainer',requiredAbility=20219,status='confirmed'},
            {kind='item',itemID=100,requiredAbility=0,status='pending'}}}
          assert(not E.LearningEligibility(r(1,100),s()))
          ns.ProfSpecializations[1].routes[2].status='confirmed'
          assert(E.LearningEligibility(r(1,100),s()))
          ns.ProfSpecializations[2]={routes={{kind='item',status='conflict'}}}
          local ok,why=E.LearningEligibility(r(2),s())
          assert(not ok and why=='specializationEvidenceConflict')
        """)

    def test_task_config_has_verified_items_faction_and_prerequisite(self):
        self.lua.execute("""
          local function ctx(choice,faction)
            return E.GetEngineeringSpecializationContext({profession='engineering',target=225,
              engineeringSpecialization=choice,snapshot={faction=faction,level=60,specializationAbilities={[20219]=false,[20222]=false}}})
          end
          local g=ctx('goblin','A').goals[1]
          assert(g.questID==3639 and g.npcID==8126 and g.minSkill==200 and g.minLevel==30)
          assert(g.prerequisiteQuestIDs[1]==3638)
          assert(g.inputs[1][1]==4394 and g.inputs[1][2]==20)
          assert(g.inputs[2][1]==10507 and g.inputs[2][2]==20)
          assert(g.inputs[3][1]==4384 and g.inputs[3][2]==5)
          local a,h=ctx('gnomish','A').goals[1],ctx('gnomish','H').goals[1]
          assert(a.questID==3641 and a.npcID==7944 and a.prerequisiteQuestIDs[1]==3640)
          assert(h.questID==3643 and h.npcID==7406 and h.prerequisiteQuestIDs[1]==3642)
          assert(h.inputs[1][1]==10559 and h.inputs[1][2]==6)
          assert(h.inputs[2][1]==4407 and h.inputs[2][2]==1)
          assert(h.inputs[3][1]==4392 and h.inputs[3][2]==2)
          h.inputs[1][2]=999
          assert(ctx('gnomish','H').goals[1].inputs[1][2]==6,'task inputs leaked between captures')
        """)

    def test_task_scope_and_current_opposite_specialization(self):
        self.lua.execute("""
          local o={profession='engineering',target=199,engineeringSpecialization='goblin',
            snapshot={faction='H',level=60,specializationAbilities={[20219]=false,[20222]=false}}}
          assert(#E.GetEngineeringSpecializationContext(o).goals==0)
          o.target=225;o.profession='alchemy'
          assert(#E.GetEngineeringSpecializationContext(o).goals==0)
          o.profession='engineering';o.snapshot.specializationAbilities[20222]=true
          assert(#E.GetEngineeringSpecializationContext(o).goals==0)
          o.snapshot.specializationAbilities[20222]=false;o.snapshot.specializationAbilities[20219]=true
          local c=E.GetEngineeringSpecializationContext(o)
          assert(c.selectionConflict and c.actual=='gnomish' and #c.goals==0)
        """)

    def test_unknown_faction_and_low_level_do_not_create_unconditional_goal(self):
        self.lua.execute("""
          local o={target=225,engineeringSpecialization='gnomish',snapshot={}}
          local g=E.GetEngineeringSpecializationContext(o).goals[1]
          assert(g.blockedReason=='specializationFactionUnknown' and g.abilityUnknown)
          o.snapshot.faction='H';o.snapshot.level=20
          assert(E.GetEngineeringSpecializationContext(o).goals[1].blockedReason=='specializationLevelRequired')
        """)

    def test_quest_completed_is_not_current_specialization_knowledge(self):
        self.lua.execute("""
          UnitFactionGroup=function() return 'Horde' end
          UnitLevel=function() return 60 end
          C_SpellBook={IsSpellKnown=function() return false end}
          C_QuestLog={IsQuestFlaggedCompleted=function() return true end}
          local c=E.GetEngineeringSpecializationContext({target=225,engineeringSpecialization='goblin'})
          assert(c.actual=='none' and not c.abilities[20222])
          assert(c.goals[1].blockedReason=='specializationQuestAlreadyCompleted')
        """)

    def test_injected_snapshot_never_calls_live_ability_or_quest_apis(self):
        self.lua.execute("""
          C_SpellBook={IsSpellKnown=function() error('must not query player') end}
          C_QuestLog={IsQuestFlaggedCompleted=function() error('must not query quests') end}
          UnitFactionGroup=function() error('must not query faction') end
          UnitLevel=function() error('must not query level') end
          local context=E.GetEngineeringSpecializationContext({target=225,snapshot={
            specializationContext={choice='goblin',abilities={[20222]=true}}}})
          assert(context.actual=='goblin' and #context.goals==0)
          local custom={id='fixture',abilityID=20219,inputs={{10559,6}}}
          context=E.GetEngineeringSpecializationContext({snapshot={specializationGoals={custom}}})
          assert(context.goals[1].id=='fixture')
        """)

    def test_live_quest_progress_keeps_unknown_distinct_and_respects_disabled(self):
        self.lua.execute("""
          assert(E.SpecializationQuestProgress({questID=3639}).inLog==nil)
          C_QuestLog={
            IsOnQuest=function(id)assert(id==3639);return true end,
            ReadyForTurnIn=function()return false end,
            IsQuestFlaggedCompleted=function()error('not ready')end,
            IsQuestDisabledForSession=function()return true end}
          local progress=E.SpecializationQuestProgress({questID=3639})
          assert(progress.inLog and progress.readyForTurnIn==false and progress.completed==nil)
          C_SpellBook={IsSpellKnown=function()return false end}
          UnitLevel=function()return 60 end;UnitFactionGroup=function()return 'Horde'end
          local goal=E.GetEngineeringSpecializationContext({target=200,engineeringSpecialization='goblin'}).goals[1]
          assert(goal.blockedReason=='specializationQuestDisabled' and goal.questProgress.inLog)
          assert(E.SpecializationKnown(20222)==false,'quest state cannot grant specialization')
        """)

    def test_policy_fingerprint_does_not_change_when_goal_ability_is_learned(self):
        self.lua.execute("""
          local o={target=225,engineeringSpecialization='goblin',snapshot={faction='H',level=60,
            specializationAbilities={[20219]=false,[20222]=false}}}
          local a=E.GetEngineeringSpecializationContext(o)
          o.snapshot.specializationAbilities[20222]=true
          local b=E.GetEngineeringSpecializationContext(o)
          assert(a.fingerprint==b.fingerprint and a.abilityFingerprint~=b.abilityFingerprint)
          o.engineeringSpecialization='none'
          assert(E.GetEngineeringSpecializationContext(o).fingerprint~=b.fingerprint)
          assert(E.SpecializationFingerprint({specializationContext=b})==b.fingerprint)
        """)

    def test_capture_collects_task_item_quotes_even_without_a_recipe(self):
        self.lua.execute("""
          ns.ProfRecipes={engineering={rows={}}}
          E.SetEngineeringSpecialization('goblin')
          UnitFactionGroup=function() return 'Horde' end
          UnitLevel=function() return 60 end
          C_SpellBook={IsSpellKnown=function() return false end}
          ns.ProfRouteAuto={AHPriceOf=function(id) return id end}
          local snap=E.Capture('engineering',{start=200,target=225})
          assert(#snap.specializationGoals==1 and snap.targetProfession=='engineering')
          for _,id in ipairs({4394,10507,4384}) do assert(snap.prices[id]==id) end
        """)

    def test_formal_toc_loads_learning_evidence_and_quest_data_before_economy(self):
        toc = (ROOT / "DungeonsForever.toc").read_text(encoding="utf-8-sig").replace("\\", "/")
        for name in ("Data_ProfSpecializations.lua", "Data_ProfSpecializationQuests.lua"):
            self.assertLess(toc.index("Core/Data/" + name), toc.index("Core/ProfEconomy.lua"))
        self.assertLess(toc.index("Core/ProfEconomy.lua"), toc.index("Core/ProfRouteSolver.lua"))


if __name__ == "__main__":
    unittest.main()
