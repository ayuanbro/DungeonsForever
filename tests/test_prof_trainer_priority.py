"""Observed trainer teaching takes priority over an alternative teaching item."""
import unittest

from test_prof_runtime import LuaRuntime, MOCKS, ROOT


class TrainerPriorityTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.load = self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        for name in ("ProfEconomy.lua", "ProfRouteSolver.lua", "ProfRouteAuto.lua"):
            self.load(str(ROOT / "Core" / name))
        self.lua.execute("""
          E=ns.ProfEconomy
          function recipe(id)
            return {profession='blacksmithing',spell=id or 101,item=20,count=1,
              learn=1,yellow=10,green=10,grey=10,mats={{11,1}},formula=99,cooldown=false,catalogue=true}
          end
          function snapshot(r,abilities)
            return {recipes={r},known={},prices={[11]=7},
              professions={blacksmithing={cur=1,max=300}},specializationAbilities=abilities or {}}
          end
          function trainer(id,status,ability)
            ns.ProfSpecializations=ns.ProfSpecializations or {}
            ns.ProfSpecializations[id]={status=status or 'pending',hasPending=status~='confirmed',routes={
              {kind='trainer',trainerObserved=true,status=status or 'pending',requiredAbility=ability or 0},
              {kind='item',itemID=99,status='pending',requiredAbility=0}}}
          end
          function solve(s,opts)
            opts=opts or {};opts.snapshot=s;opts.start=opts.start or 1;opts.target=opts.target or 2
            local result,job=ns.ProfRouteSolver.Compute('blacksmithing',opts)
            assert(not job.error,tostring(job.error));return result
          end
        """)

    def load_real_recipe(self):
        for name in ("Data_ProfRecipes.lua", "Data_ProfSpecializations.lua"):
            self.load(str(ROOT / "Core" / "Data" / name))

    def test_real_glimmering_copper_boots_keep_item_relation_but_use_trainer(self):
        self.load_real_recipe()
        self.lua.execute("""
          local raw
          for _,row in ipairs(ns.ProfRecipes.blacksmithing.rows) do
            if row[1]==1252231 then raw=row;break end
          end
          assert(raw and raw[2]==250482 and raw[13][1]==251334)
          local evidence=ns.ProfSpecializations[1252231]
          assert(evidence.status=='pending' and evidence.routes[1].trainerObserved==true)
          local r=E.FindRecipe('blacksmithing',1252231)
          assert(r.item==250482 and r.formula==251334 and r.learnSource=='trainer')
          assert(E.LearningSource(raw)=='trainer')
          assert(E.FormulaFor(r,{known={},prices={}})==nil,
            'an observed trainer recipe still requires the unpriced teaching item')
          assert(raw[13][1]==251334,'source relation was destroyed to hide the formula')
          assert(not r.clientAvailable,'website teaching evidence fabricated client availability')
        """)

    def test_real_recipe_can_be_planned_without_formula_quote_or_purchase(self):
        self.load_real_recipe()
        self.lua.execute("""
          local r=E.FindRecipe('blacksmithing',1252231)
          local s={recipes={r},known={},prices={[2840]=2,[10938]=3,[2318]=4},
            professions={blacksmithing={cur=35,max=300}},specializationAbilities={}}
          local plan=solve(s,{start=35,target=36})
          assert(plan.targetReached and plan.feasible and plan.total==24)
          assert(plan.formulasTotal==0 and #plan.formulas==0 and #plan.steps==1)
          assert(plan.steps[1][3]==1252231 and r.formula==251334)
          for _,action in ipairs(plan.actions) do
            assert(action.type~='formula','trainer path purchased a teaching item')
          end
          for _,material in ipairs(plan.mats) do assert(material.id~=251334) end
        """)

    def test_positive_evidence_is_read_from_each_supported_recipe_shape(self):
        self.lua.execute("""
          trainer(101)
          for _,r in ipairs({{spell=101},{spellID=101},{101}}) do
            assert(E.LearningSource(r)=='trainer')
          end
          assert(E.LearningSource({spell=102,learnSource='trainer'})=='trainer')
          assert(E.LearningSource({spell=103,trainerObserved=true})=='trainer')
          assert(E.LearningSource({spell=101,learnSource='catalogue'})=='trainer')
          assert(E.LearningSource(nil)==nil and E.LearningSource(101)==nil)
        """)

    def test_without_positive_teaching_evidence_formula_stays_required(self):
        self.lua.execute("""
          for _,evidence in ipairs({
            {routes={}},
            {status='pending',routes={{kind='trainer',status='pending',requiredAbility=0}}},
            {routes={{kind='trainer',status='confirmed',requiredAbility=0}}},
            {routes={{kind='item',status='confirmed',itemID=99,requiredAbility=0}}},
            {routes={{kind='trainer',status='pending',trainerObserved=false,requiredAbility=0}}}
          }) do
            ns.ProfSpecializations={[101]=evidence}
            local r=recipe();local f=E.FormulaFor(r,snapshot(r))
            assert(E.LearningSource(r)~='trainer')
            assert(f and f.id==99 and not f.usable and f.reason=='formulaUnavailable')
            assert(not solve(snapshot(r)).feasible)
          end
          ns.ProfSpecializations=nil
          assert(E.FormulaFor(recipe(),{known={},prices={}}).blocked)
        """)

    def test_leveling_guide_membership_does_not_invent_trainer_evidence(self):
        self.lua.execute("""
          ns.ProfLeveling={blacksmithing={learn={101},rinfo={
            [101]={learn=1,yellow=10,green=10,grey=10}}}}
          local r=E.ResolveRecipe(recipe())
          assert(E.LearningSource(r)~='trainer')
          assert(E.FormulaFor(r,snapshot(r)).blocked)
          assert(not solve(snapshot(r)).targetReached)
        """)

    def test_observed_trainer_does_not_query_formula_market_or_merchants(self):
        self.lua.execute("""
          trainer(101)
          ns.ProfItemPrices={GetFormulaOffers=function()error('unneeded formula quote')end}
          local prices=setmetatable({}, {__index=function()error('unneeded formula market price')end})
          assert(E.FormulaFor(recipe(),{known={},prices=prices})==nil)
          assert(recipe().formula==99)
        """)

    def test_trainer_path_selects_its_own_specialization_requirement(self):
        self.lua.execute("""
          trainer(101,'confirmed',9787)
          ns.ProfSpecializations[101].routes[2]={kind='item',itemID=99,status='confirmed',requiredAbility=9788}
          local r=recipe();r.learningRoute='item'
          local ok,why,detail=E.LearningEligibility(r,snapshot(r,{[9788]=true,[9787]=false}))
          assert(not ok and why=='specializationRequired' and detail.requiredAbility==9787)
          assert(E.LearningEligibility(r,snapshot(r,{[9787]=true,[9788]=false})))
          assert(not solve(snapshot(r,{[9788]=true,[9787]=false})).targetReached)
          assert(solve(snapshot(r,{[9787]=true,[9788]=false})).targetReached)
        """)

    def test_static_trainer_evidence_does_not_clear_explicit_client_unavailable(self):
        self.lua.execute("""
          trainer(101)
          ns.ProfRecipeRuntime={[101]={available=false}}
          local r=E.ResolveRecipe(recipe())
          assert(r.learnSource=='trainer' and r.clientUnavailable and not r.clientAvailable)
          local s=snapshot(r);s.known['blacksmithing:101']=true
          local ok,why=E.LearningEligibility(r,s)
          assert(not ok and why=='clientUnavailable')
          assert(not solve(s).targetReached)
        """)

    def test_static_trainer_evidence_preserves_complete_client_roster_absence(self):
        self.lua.execute("""
          trainer(103)
          E.Professions=function()return {blacksmithing={cur=1,max=75,primary=true}}end
          C_TradeSkillUI={GetAllRecipeIDs=function()return {101,102}end,
            GetBaseProfessionInfo=function()return {professionID=164}end,
            IsDataSourceChanging=function()return false end,IsTradeSkillReady=function()return true end,
            GetRecipeInfo=function(id)return {learned=id==101}end}
          E.ScanRecipes()
          local r=E.ResolveRecipe(recipe(103))
          assert(r.learnSource=='trainer' and r.clientUnavailable)
          assert(not solve(snapshot(r)).feasible)
        """)

    def test_positive_client_trainer_observation_overrides_catalogue_formula(self):
        self.lua.execute("""
          ns.ProfRecipeRuntime={[101]={trainerObserved=true,available=true}}
          local seed=recipe();seed.learnSource='catalogue'
          local r=E.ResolveRecipe(seed)
          assert(r.learnSource=='trainer' and r.formula==99 and r.clientAvailable)
          assert(not r.clientUnavailable and E.FormulaFor(r,snapshot(r))==nil)
          assert(solve(snapshot(r)).targetReached)
          assert(seed.learnSource=='catalogue' and seed.formula==99)
          assert(E.LearningSource({spellID=101})=='trainer')
        """)

    def test_user_ban_still_excludes_observed_trainer_recipe(self):
        self.lua.execute("""
          trainer(101)
          local r=recipe()
          assert(solve(snapshot(r)).targetReached)
          local plan=solve(snapshot(r),{exclusions={['blacksmithing:101']='ban'}})
          assert(not plan.targetReached and not plan.feasible and #plan.steps==0)
          assert(plan.formulasTotal==0)
        """)

    def test_old_learning_policy_requires_manual_recalculation_without_erasing_history(self):
        self.lua.execute("""
          trainer(101)
          local s=snapshot(recipe());local opts={target=2,snapshot=s}
          local route=ns.ProfRouteAuto
          local fresh=route.StampSpecializations(solve(s),'blacksmithing',opts,s)
          assert(fresh.specializationPolicy.fingerprint:sub(1,2)=='2:')
          assert(not route.SpecializationPlanChanged(fresh,'blacksmithing',opts))
          assert(route.ValidateSpecializationPlan(fresh,'blacksmithing',opts)==fresh)
          local old=E.Copy(fresh)
          old.specializationPolicy.fingerprint=old.specializationPolicy.fingerprint:gsub('^2:','1:',1)
          assert(route.SpecializationPlanChanged(old,'blacksmithing',opts))
          local gated=route.ValidateSpecializationPlan(old,'blacksmithing',opts)
          assert(gated.status=='recalculate_required' and gated.stale and not gated.feasible)
          assert(#gated.steps==0 and #gated.formulas==0 and #gated.mats==0)
          assert(#old.steps==1 and old.total==7 and old.targetReached,
            'validation rewrote the saved execution history')
        """)


if __name__ == '__main__':
    unittest.main()
