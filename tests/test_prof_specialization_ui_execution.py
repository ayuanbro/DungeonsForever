"""Specialization choices, quest execution and stale-route boundaries in Lua 5.1."""
import unittest

import test_prof_execution as execution_fixture
import test_prof_execution_hud as hud_fixture
import test_prof_ui_regressions as ui_fixture

ROOT = execution_fixture.ROOT
LuaRuntime = execution_fixture.LuaRuntime

QUEST_PLAN = r'''
specialized=false
ns.ProfEconomy.SpecializationKnown=function(id) return id==20222 and specialized or false end
skills.engineering={cur=200,max=300,primary=true}
function questPlan()
 local producer={200,200,101,3,segmentID='producer',profession='engineering',expectedCrafts=3,
   expectedGain=0,goalSkill=200,attemptLimit=3,outputMin=2,outputMax=2,requiredOutputs={[10]=6},
   materialMinCrafts=3,allocations={{itemID=10,count=6,consumerID='quest'}},
   recipe={spell=101,item=10,count=2,outputMin=2,outputMax=2,mats={{20,1}},profession='engineering',grey=300}}
 local goal={id='goblin',abilityID=20222,questID=3639,minSkill=200,minLevel=30,
   npcID=8126,npcName='Nixx',zone='Tanaris',x=52.5,y=27.3,prerequisiteQuestIDs={3638},inputs={{10,6}}}
 local quest={200,200,0,0,segmentID='quest',profession='engineering',kind='specialization_quest',
   quest=goal,abilityID=20222,questID=3639,requiredOutputs={},allocations={},recipe={spell=0,mats=goal.inputs}}
 local segments={producer,quest}
 return {planVersion=2,executionVersion=1,planID='engineering:quest',feasible=true,status='complete',
   steps=segments,executionSteps=segments,mats={{id=20,count=3,source='ah'}},formulas={},total=3}
end
function finishProduction()
 for i=1,3 do
   xp.RecordAttempt('engineering',101,'c'..i)
   xp.RecordOutput({itemID=10,quantity=2,castGUID='c'..i})
 end
 xp.Sync('engineering')
end
'''


class SpecializationExecutionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(execution_fixture.MOCKS)
        self.load = self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        for name in ("ProfEconomy", "ProfRouteSolver", "ProfExecution"):
            self.load(str(ROOT / "Core" / (name + ".lua")))
        self.lua.execute("ns.ProfEconomy.Professions=function() return skills end; initialize(); xp=ns.ProfExecution")
        self.lua.execute(QUEST_PLAN)
        self.lua.execute("run=xp.Bind('engineering',questPlan())")

    def test_skill_or_quest_event_does_not_complete_entry_quest(self):
        self.lua.execute(r'''
          finishProduction();assert(run.currentIndex==2)
          skills.engineering.cur=300;xp.Sync('engineering')
          xp.eventFrame.OnEvent(xp.eventFrame,'QUEST_TURNED_IN',3639)
          local p=xp.Progress('engineering')
          assert(p.skillMet and not p.complete and run.currentIndex==2)
          assert(p.directMaterials[1].id==10 and p.directMaterials[1].count==6 and p.remainingCrafts==0)
          assert(not xp.RecordAttempt('engineering',0,'fake-quest-cast'))
          specialized=true;xp.eventFrame.OnEvent(xp.eventFrame,'SPELLS_CHANGED')
          assert(run.finished and xp.Progress('engineering',2).complete)
        ''')

    def test_unknown_ability_does_not_finish_and_actual_unlock_is_idempotent(self):
        self.lua.execute(r'''
          finishProduction();ns.ProfEconomy.SpecializationKnown=function()return nil end
          xp.Sync('engineering');assert(not xp.Progress('engineering',2).complete)
          ns.ProfEconomy.SpecializationKnown=function()return true end
          xp.Sync('engineering');local version=run.progressVersion
          xp.Sync('engineering');assert(run.progressVersion==version and run.finished)
        ''')

    def test_later_loss_of_acquired_specialization_invalidates_frozen_run(self):
        self.lua.execute(r'''
          run.plan.specializationPolicy={actualAbilities={}}
          ns.ProfRouteAuto={SpecializationPlanChanged=function(plan)
            local abilities=plan and plan.specializationPolicy and plan.specializationPolicy.actualAbilities or {}
            return abilities[20222]==true and not specialized
          end}
          finishProduction();specialized=true;xp.Sync('engineering')
          assert(run.finished and run.plan.specializationPolicy.actualAbilities[20222])
          assert(xp.Bind('engineering',run.plan)==run)
          specialized=false
          local rebound,reason=xp.Bind('engineering',run.plan)
          assert(not rebound and reason=='specializationChanged')
        ''')

    def test_handin_consumes_same_output_once_and_preserves_producer_credit(self):
        self.lua.execute(r'''
          finishProduction();bag[10]=100
          assert(xp.GetContinuation('engineering')[10]==6)
          specialized=true;xp.Sync('engineering')
          assert(xp.GetContinuation('engineering')[10]==nil)
          assert(xp.Progress('engineering',1).complete and run.finished)
          assert(run.materialLedger.consumed[10]==6)
          xp.Sync('engineering');assert(run.materialLedger.consumed[10]==6)
          local totals=xp.GetRecipeTotals('engineering')
          assert(#totals==1 and totals[1].spell==101)
        ''')

    def test_reload_retains_quest_consumption(self):
        self.lua.execute("finishProduction();specialized=true;xp.Sync('engineering');bag[10]=100")
        self.load(str(ROOT / "Core/ProfExecution.lua"))
        self.lua.execute(r'''
          initialize();xp=ns.ProfExecution;run=xp.GetRun('engineering')
          assert(run.finished and xp.Progress('engineering',2).complete)
          assert(xp.GetContinuation('engineering')[10]==nil)
        ''')

    def test_external_handin_resolves_task_quota_without_fake_crafts(self):
        self.lua.execute(r'''
          specialized=true;xp.Sync('engineering')
          local producer=xp.Progress('engineering',1)
          assert(producer.complete and run.finished and producer.resolvedByQuestOutputs==6)
          assert(producer.casts==0 and producer.actualOutputs==0 and producer.confirmedOutputs==0)
          assert(run.attemptsDone==0 and next(xp.GetContinuation('engineering'))==nil)
        ''')

    def test_partial_route_production_plus_external_handin_counts_only_real_output(self):
        self.lua.execute(r'''
          xp.RecordAttempt('engineering',101,'partial')
          xp.RecordOutput({itemID=10,quantity=2,castGUID='partial'});bag[10]=100
          specialized=true;xp.Sync('engineering')
          local producer=xp.Progress('engineering',1)
          assert(producer.complete and producer.resolvedByQuestOutputs==4)
          assert(producer.casts==1 and producer.actualOutputs==2)
          assert(xp.GetContinuation('engineering')[10]==nil)
        ''')

    def test_external_handin_keeps_other_consumer_quota(self):
        self.lua.execute(r'''
          local plan=questPlan();local producer=plan.executionSteps[1]
          producer.requiredOutputs[10]=10;producer.expectedCrafts=5;producer[4]=5
          producer.allocations[2]={itemID=10,count=4,consumerID='other'}
          table.insert(plan.executionSteps,{200,201,102,1,segmentID='other',profession='engineering',
            expectedGain=1,goalSkill=201,recipe={spell=102,mats={{10,4}},learn=1,yellow=300,green=300,grey=300},
            requiredOutputs={},allocations={}})
          run=xp.StartNew('engineering',plan);specialized=true;xp.Sync('engineering')
          local progress=xp.Progress('engineering',1)
          assert(progress.resolvedByQuestOutputs==6 and progress.remainingOutputs==4 and not progress.complete)
          xp.RecordAttempt('engineering',101,'after');xp.RecordOutput({itemID=10,quantity=4,castGUID='after'})
          xp.Sync('engineering');bag[10]=100
          assert(xp.Progress('engineering',1).complete and run.currentIndex==3)
          assert(xp.GetContinuation('engineering')[10]==4,'handin consumed future output')
        ''')

    def test_task_only_upstream_quota_is_released_without_inventing_stock(self):
        self.lua.execute(r'''
          local plan=questPlan()
          table.insert(plan.executionSteps,1,{200,200,103,3,segmentID='upstream',profession='engineering',
            expectedCrafts=3,expectedGain=0,goalSkill=200,item=20,outputMin=1,outputMax=1,
            requiredOutputs={[20]=3},allocations={{itemID=20,count=3,consumerID='producer'}},
            recipe={spell=103,item=20,count=1,outputMin=1,outputMax=1,mats={{30,1}}}})
          run=xp.StartNew('engineering',plan);specialized=true;xp.Sync('engineering')
          assert(run.finished)
          local upstream=xp.Progress('engineering',1)
          assert(upstream.resolvedByQuestOutputs==3 and upstream.casts==0 and upstream.actualOutputs==0)
          assert(next(xp.GetContinuation('engineering'))==nil)
        ''')

    def test_task_release_does_not_cancel_still_needed_leveling(self):
        self.lua.execute(r'''
          local plan=questPlan();local producer=plan.executionSteps[1]
          producer.expectedGain=1;producer.goalSkill=201;producer[2]=201
          producer.recipe.learn=1;producer.recipe.yellow=300;producer.recipe.green=300
          run=xp.StartNew('engineering',plan);specialized=true;xp.Sync('engineering')
          local progress=xp.Progress('engineering',1)
          assert(progress.materialDone and not progress.skillDone and not progress.complete)
          assert(progress.remainingCrafts==1 and progress.casts==0)
        ''')

    def test_task_supplement_does_not_create_fake_spell_or_replace_plan(self):
        self.lua.execute(r'''
          finishProduction();local before=run.plan
          local result,reason=xp.CalculateSupplement('engineering')
          assert(result==nil and reason=='specialization_quest_pending')
          assert(run.plan==before and run.currentIndex==2)
        ''')

    def test_supplement_cannot_reuse_future_quest_deliveries(self):
        self.lua.execute(r'''
          local plan=questPlan()
          table.insert(plan.executionSteps,2,{200,201,102,0,segmentID='level',profession='engineering',
            expectedCrafts=0,expectedGain=1,goalSkill=201,attemptLimit=0,requiredOutputs={},allocations={},
            recipe={spell=102,item=11,count=1,outputMin=1,outputMax=1,
              learn=1,yellow=300,green=300,grey=300,mats={{10,1}},profession='engineering'}})
          run=xp.StartNew('engineering',plan);finishProduction();bag[10]=100
          assert(run.currentIndex==2 and xp.GetContinuation('engineering')[10]==6)
          ns.ProfEconomy.Capture=function()return {known={}}end
          local checked=false
          ns.ProfRouteSolver.ProcureMany=function(_,demands,opts)
            checked=true;assert(demands[10]==1)
            assert((opts.executionInventory[10] or 0)==0,'quest deliveries were reused for topup')
            return {feasible=false,status='infeasible'}
          end
          xp.CalculateSupplement('engineering');xp.Pump('engineering');assert(checked)
        ''')

    def test_stale_frozen_run_and_supplement_cannot_be_rebound(self):
        self.lua.execute(r'''
          ns.ProfRouteAuto={
            SpecializationPlanChanged=function()return true end,
            ValidateSpecializationPlan=function()
              return {status='recalculate_required',feasible=false,diagnostics={{code='specializationChanged'}}}
            end}
          local old=run.plan
          local rebound,reason=xp.Bind('engineering',questPlan())
          assert(not rebound and reason=='specializationChanged' and run.plan==old)
          assert(xp.GetSupplement('engineering').status=='recalculate_required')
          local result,why=xp.CalculateSupplement('engineering')
          assert(not result and why=='specializationChanged')
        ''')

    def test_recalculate_gate_cannot_restore_existing_run(self):
        self.lua.execute(r'''
          local rebound,reason=xp.Bind('engineering',{status='recalculate_required',
            diagnostics={{code='specializationChanged'}}})
          assert(not rebound and reason=='specializationChanged')
        ''')


class SpecializationPageTests(unittest.TestCase):
    def setUp(self):
        ui_fixture.ProfessionUIRegressions.setUp(self)
        source = (ROOT / "Core/ProfessionUI.lua").read_text(encoding="utf-8-sig")
        a = source.index("function PD.StepName(")
        self.lua.execute(source[a:source.index("function PD.PolicyMode(", a)])
        self.lua.execute(r'''
          PushHead=function(rows,text)rows[#rows+1]={text=text}end;PushGap=function()end
          PD.RequestRender=function()renders=(renders or 0)+1 end
          PD.SettingRaw=function()return 'cheapest'end
          D={pro={engineering={name='Engineering'},alchemy={name='Alchemy'}}}
          SpellName=function(id)return 'Spell'..id end
        ''')

    def test_engineering_default_none_choice_is_character_scoped(self):
        self.lua.execute(r'''
          PD.cur='engineering';local E=ns.ProfEconomy
          assert(E.GetEngineeringSpecialization()=='none')
          local rows={};PD.RowsSettings(rows);local goblin
          for _,row in ipairs(rows)do if row.text=='○ 地精工程学'then goblin=row end end
          assert(goblin and goblin.act);goblin.act()
          assert(E.GetEngineeringSpecialization()=='goblin' and renders==1)
          UnitName=function()return 'Other'end
          assert(E.GetEngineeringSpecialization()=='none')
          UnitName=function()return 'Test'end
          assert(E.GetEngineeringSpecialization()=='goblin')
        ''')

    def test_other_profession_settings_do_not_offer_engineering_choice(self):
        self.lua.execute(r'''
          PD.cur='alchemy';local rows={};PD.RowsSettings(rows)
          for _,row in ipairs(rows)do assert(row.text~='工程专精计划（本角色）')end
        ''')

    def test_settings_identify_actual_branch_and_conflicting_selection(self):
        self.lua.execute(r'''
          PD.cur='engineering';local E=ns.ProfEconomy
          E.GetEngineeringSpecializationContext=function()return {actual='gnomish',selectionConflict=true}end
          local rows={};PD.RowsSettings(rows);local actual,conflict,off=false,false,false
          for _,row in ipairs(rows)do
            actual=actual or row.text=='当前专精：侏儒工程学'
            conflict=conflict or row.text=='所选专精与已学专精不同；请调整选择后重新计算。'
            off=off or row.text=='● 不开启新专精'
          end
          assert(actual and conflict and off)
        ''')

    def test_task_presentation_is_not_a_mining_checkpoint(self):
        self.lua.execute(r'''
          local st={200,200,0,0,kind='specialization_quest',quest={abilityID=20222,
            questID=3639,npcID=8126,npcName='Nixx',zone='Tanaris',x=52.5,y=27.3}}
          assert(PD.StepRole(st)=='专精入门任务')
          assert(PD.StepName(st)=='地精工程学入门任务')
          assert(PD.SpecializationQuestSource(st):find('Nixx',1,true))
          assert(PD.SpecializationQuestSource(st):find('#3639',1,true))
          assert(PD.StepRole({1,100,0,0})=='实地采矿')
        ''')

    def test_task_source_localizes_names_and_reads_live_quest_status(self):
        self.lua.execute(r'''
          L.Nixx='Localized NPC';L.Tanaris='Localized zone';L.Work='Localized quest'
          local st={kind='specialization_quest',quest={npcName='Nixx',zone='Tanaris',
            questName='Work',questID=3639,prerequisiteQuestIDs={3638},questProgress={readyForTurnIn=true}}}
          assert(PD.SpecializationQuestSource(st)=='Localized NPC · Localized zone · 《Localized quest》 #3639')
          assert(PD.SpecializationQuestPrerequisites(st)=='先完成前置任务并与导师对话：#3638')
          ns.ProfEconomy.SpecializationQuestProgress=function()return {inLog=true,readyForTurnIn=false}end
          assert(PD.SpecializationQuestProgressText(st)=='任务已接取')
          ns.ProfEconomy.SpecializationQuestProgress=function()return {readyForTurnIn=true}end
          assert(PD.SpecializationQuestProgressText(st)=='任务可交付')
          ns.ProfEconomy.SpecializationQuestProgress=function()return {}end
          assert(PD.SpecializationQuestProgressText(st)==nil)
        ''')

    def test_stale_import_callback_rechecks_specialization(self):
        self.lua.execute(r'''
          PD.cur='engineering';imports=0;ns.AuctionBridge={DoImport=function()imports=imports+1 end}
          local data={planVersion=2,feasible=true,mats={{id=10,count=3,source='ah'}}}
          local changed=false
          RA.ValidateSpecializationPlan=function(plan)
            if changed then return {status='recalculate_required',feasible=false}end
            return plan
          end
          PD.ShopImport(data);assert(imports==1)
          changed=true;PD.ShopImport(data);assert(imports==1)
          assert(data.feasible==true and data.mats[1].count==3)
        ''')

    def test_fixed_gap_status_and_empty_blocked_list_are_distinct(self):
        self.lua.execute(r'''
          assert(PD.PlanStatusText({specializationBlocked={{spell=1}},feasible=false})==
            '固定攻略存在专精缺口，请切换自动计算。')
          assert(PD.PlanStatusText({specializationBlocked={},status='complete'})~=
            '固定攻略存在专精缺口，请切换自动计算。')
        ''')


class SpecializationHUDTests(unittest.TestCase):
    def setUp(self):
        self.lua = hud_fixture.ExecutionHUDTests.make_runtime(self)
        self.lua.execute(QUEST_PLAN)
        self.lua.execute(r'''
          xp=ns.ProfExecution
          ns.ProfData.pro.engineering={name='Engineering'}
          ns.ProfLeveling.engineering={steps={{1,300,101,299}}}
          ns.ProfRecipes.engineering={rows={}}
          followState.slug='engineering';followState.skill=200
          currentResult=questPlan()
        ''')

    def test_hud_task_shows_handin_requirements_and_no_crafting_controls(self):
        self.lua.execute(r'''
          ns.ProfFollow.Sync();finishProduction();ns.ProfFollow.Sync()
          ns.ProfFollow.Build();ns.ProfFollow.f:Show();ns.ProfFollow.Paint()
          local f=ns.ProfFollow.f
          assert(f.card.name.text=='地精工程学入门任务')
          assert(f.card.crafts.text=='交付任务物品 · #3639')
          assert(f.card.progress[1].text:find('Nixx',1,true))
          assert(f.card.progress[2].text=='需要工程学 200、角色等级 30')
          assert(not f.craftBtn.shown and not f.suppBtn.shown and not f.verifyBtn.shown)
          assert(f.card.__mats[1][1]==10 and f.card.__mats[1][2]==6)
          assert(followState.step==2)
          specialized=true;ns.ProfFollow.Sync();ns.ProfFollow.Paint()
          assert(followState.step==3 and f.finish.shown)
        ''')

    def test_hud_learned_marker_uses_shared_recipe_knowledge(self):
        self.lua.execute(r'''
          C_Spell.IsSpellKnown=function()return false end
          ns.ProfEconomy.Known=function(id)return id==101 end
          ns.ProfFollow.Sync();ns.ProfFollow.Build();ns.ProfFollow.f:Show();ns.ProfFollow.Paint()
          assert(ns.ProfFollow.f.card.srcTag.text:find('已学习',1,true))
          ns.ProfEconomy.Known=function()return false end
          C_Spell.IsSpellKnown=function()return true end
          ns.ProfFollow.Paint()
          assert(not ns.ProfFollow.f.card.srcTag.text:find('已学习',1,true))
        ''')

    def test_ready_to_turn_in_is_visible_without_completing_quest(self):
        self.lua.execute(r'''
          ns.ProfFollow.Sync();finishProduction();ns.ProfFollow.Sync()
          ns.ProfEconomy.SpecializationQuestProgress=function()return {readyForTurnIn=true}end
          ns.ProfFollow.Build();ns.ProfFollow.f:Show();ns.ProfFollow.Paint()
          assert(ns.ProfFollow.f.card.crafts.text:find('任务可交付',1,true))
          assert(not xp.Progress('engineering',2).complete and followState.step==2)
        ''')

    def test_fixed_specialization_gap_blocks_follow_and_procurement(self):
        self.lua.execute(r'''
          settings.autoRoute=false
          ns.ProfRouteAuto.FilterFixedSpecializations=function(_,steps)
            return {},{{spell=101,from=1,to=300}},false
          end
          local mode,steps,view=ns.ProfFollow.GetRoute('engineering',200)
          assert(mode=='auto' and #steps==0 and view.feasible==false)
          assert(view.message=='固定攻略存在专精缺口，请切换自动计算。')
          assert(#ns.ProfFollow.GetPurchases(followState)==0)
        ''')

    def test_selected_quest_blocks_fixed_even_without_specialized_recipe(self):
        self.lua.execute(r'''
          settings.autoRoute=false
          ns.ProfRouteAuto.FilterFixedSpecializations=function(_,steps)return steps,{},true end
          local _,steps,view=ns.ProfFollow.GetRoute('engineering',200)
          assert(#steps==0 and view.status=='recalculate_required')
        ''')

    def test_changed_frozen_plan_cannot_override_current_guard(self):
        self.lua.execute(r'''
          ns.ProfFollow.Sync();local frozen=xp.GetPlan('engineering')
          ns.ProfRouteAuto.ValidateSpecializationPlan=function(plan)
            if plan==frozen then return {planVersion=2,status='recalculate_required',feasible=false,steps={}}end
            return plan
          end
          local _,steps,view=ns.ProfFollow.GetRoute('engineering',200)
          assert(#steps==0 and view.status=='recalculate_required')
          assert(xp.GetPlan('engineering')==frozen)
          assert(#ns.ProfFollow.GetPurchases(followState)==0)
        ''')


if __name__ == "__main__":
    unittest.main()
