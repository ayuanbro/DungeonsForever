"""Per-profession audit of self-fished cooking, gathering, fixed routes and HUD."""
from pathlib import Path
import unittest

import test_prof_route_plans as route_fixture

ROOT=Path(__file__).resolve().parents[1]


class SpecialRouteFixture(unittest.TestCase):
    def setUp(self):
        fixture=route_fixture.NativeRoutePlansTests()
        fixture.setUp()
        self.lua,self.load=fixture.lua,fixture.load
        for name in ("ProfFishing","ProfGathering"):
            self.load((ROOT/"Core"/(name+".lua")).read_text(encoding="utf-8-sig"))

    def data(self):
        for name in ("Data_Professions","Data_ProfLeveling","Data_ProfRecipes","Data_ProfGathering","Data_ProfMining","Data_ProfFishingRoutes"):
            self.load((ROOT/"Core"/"Data"/(name+".lua")).read_text(encoding="utf-8-sig"))

    def fishing(self):
        self.lua.execute(r'''
          function cook(spell,learn,grey,formula)
            return {profession='cooking',spell=spell,key='cooking:'..spell,item=500+spell,count=2,
              mats={{6291,1},{999,1}},learn=learn or 1,yellow=100,green=200,grey=grey or 300,
              cooldown=false,trainerAvailable=true,formula=formula}
          end
          function fishInput(recipes)
            local snap={recipes=recipes or {cook(101)},professions={cooking={cur=1,max=300}},known={},
              prices={[999]=1},offers={[999]={{unlimited=true,available=true,purchasable=true,price=11,quantity=5,reference=true}}},
              formulaOffers={},auctionSupply={},coverageComplete=true}
            for _,r in ipairs(snap.recipes)do snap.known[r.key]=true end
            return {snapshot=snap,start=1,target=4,scheme='fishing',recoveryEnabled=false,
              fishingData={fish={[6291]={areas={{zoneID=12,minSkill=1,noGetaway=25}},catchRate=.6,restrictionsVerified=true}}},
              cookingGuide={{from=1,to=4,spell=101}}}
          end
          function computeFish(opts)return ns.ProfRouteAuto.ComputeFishing('cooking',opts)end
        ''')

    def follow(self,slug="mining"):
        self.lua.execute(r'''
          ns.ProfHost={DG={ZoneName=function(id)return 'Zone '..id end},Unpack=unpack}
          ns.ProfModule={ProfLearned=function()return skills end,Setting=function(k)return k=='autoRoute'end,
            SettingRaw=function(k)if k=='autoScheme'then return 'cheapest'end end,
            GatherMode=function()return 'gather'end}
        ''')
        self.load((ROOT/"Core"/"ProfFollow.lua").read_text(encoding="utf-8-sig"))
        self.lua.execute("for _,fn in ipairs(callbacks)do fn()end;callbacks={};pf=ns.ProfFollow;pf.Build=function()end")


class SelfFishedCookingAuditTests(SpecialRouteFixture):
    def setUp(self):
        super().setUp()
        self.fishing()

    def test_nonfish_material_must_have_unlimited_vendor_quote(self):
        self.lua.execute("local o=fishInput();o.snapshot.offers={};local r=computeFish(o);assert(not r.feasible and #r.steps==0)")

    def test_limited_or_extended_cost_nonfish_material_is_rejected(self):
        self.lua.execute(r'''
          for _,mode in ipairs({'limited','currency','unavailable'})do
            local o=fishInput();local offer=o.snapshot.offers[999][1]
            if mode=='limited'then offer.unlimited=false elseif mode=='currency'then offer.currencyID=1 else offer.available=false end
            assert(not computeFish(o).feasible,mode)
          end
        ''')

    def test_pack_cost_is_charged_and_output_count_is_preserved(self):
        self.lua.execute(r'''
          local r=computeFish(fishInput())
          assert(r.feasible and r.targetReached and r.crafts==3 and r.total==11,tostring(r.total))
          assert(#r.mats==1 and r.mats[1].id==999 and r.mats[1].count==5 and r.mats[1].need==3)
          assert(r.steps[1].cost==11 and r.executionSteps[1].recipe.count==2)
          assert(r.fishMaterials[1].id==6291 and r.fishMaterials[1].count==3)
          assert(r.actions[1].outputs[1][2]==6 and not r.inventory)
        ''')

    def test_shared_vendor_pack_leftovers_are_not_bought_twice(self):
        self.lua.execute(r'''
          local o=fishInput({cook(101,1,2),cook(102,2,300)})
          o.cookingGuide={{from=1,to=2,spell=101},{from=2,to=4,spell=102}}
          local r=computeFish(o);assert(#r.steps==2 and r.total==11)
          assert(r.steps[1].cost==11 and r.steps[2].cost==0)
        ''')

    def test_learned_only_and_exclusions_are_enforced(self):
        self.lua.execute(r'''
          local o=fishInput();o.learnedOnly=true;o.snapshot.known={};assert(not computeFish(o).feasible)
          o=fishInput();o.exclusions={['cooking:101']='ban'};assert(not computeFish(o).feasible)
        ''')

    def test_client_unavailable_and_pending_recipe_are_rejected(self):
        self.lua.execute(r'''
          for _,field in ipairs({'clientUnavailable','clientPending','outputConflict','cooldownUnknown'})do
            local o=fishInput();o.snapshot.recipes[1][field]=true;assert(not computeFish(o).feasible,field)
          end
        ''')

    def test_unknown_seasonal_and_night_restrictions_are_not_filled_in(self):
        self.lua.execute(r'''
          for _,field in ipairs({'unknown','season','night','uncertain'})do
            local o=fishInput();local fish=o.fishingData.fish[6291]
            if field=='unknown'then fish.restrictionsVerified=nil else fish[field]=true end
            local r=computeFish(o);assert(not r.feasible,field)
          end
        ''')

    def test_reference_fish_list_stays_reference_instead_of_client_verified(self):
        self.lua.execute(r'''
          local o=fishInput();o.fishingData.fish[6291].restrictionsVerified=nil
          o.fishingData.fishingSteps={{from=1,to=300,fishIDs={6291}}}
          local r=computeFish(o);assert(r.feasible and r.fishingReference)
          assert(o.fishingData.fish[6291].restrictionsVerified==nil)
        ''')

    def test_unpurchasable_unlearned_teaching_item_blocks_recipe(self):
        self.lua.execute(r'''
          local recipe=cook(101);recipe.formula=888;recipe.trainerAvailable=nil;recipe.learnSource='item'
          local o=fishInput({recipe});o.snapshot.known={}
          local r=computeFish(o);assert(not r.feasible)
        ''')

    def test_teaching_item_charged_once_across_multiple_recipes(self):
        self.lua.execute(r'''
          local a,b=cook(101,1,2),cook(102,2,300)
          a.formula=888;b.formula=888;a.trainerAvailable=nil;b.trainerAvailable=nil
          a.learnSource='item';b.learnSource='item'
          local o=fishInput({a,b});o.snapshot.known={};o.snapshot.prices[888]=7
          o.cookingGuide={{from=1,to=2,spell=101},{from=2,to=4,spell=102}}
          local r=computeFish(o)
          assert(r.feasible and #r.formulas==1 and r.formulasTotal==7 and r.total==18,tostring(r.total))
        ''')

    def test_target_is_clipped_without_injecting_gathered_fish(self):
        self.lua.execute(r'''
          local o=fishInput();o.target=2;local r=computeFish(o)
          assert(r.target==2 and r.steps[1][2]==2 and r.fishMaterials[1].count==1)
          for _,m in ipairs(r.mats)do assert(m.id~=6291)end
          for _,action in ipairs(r.actions)do assert(action.type=='craft' and action.inputs[1][1]==6291)end
          assert(ns.ProfRouteAuto.ComputeFishing('alchemy',o)==nil)
        ''')


class GatheringAndFixedAuditTests(SpecialRouteFixture):
    def setUp(self):
        super().setUp()
        self.data()

    def test_all_special_professions_have_explicit_route_coverage(self):
        self.lua.execute(r'''
          for _,slug in ipairs({'cooking','first-aid','poisons','mining'})do assert(ns.ProfLeveling[slug] and #ns.ProfLeveling[slug].steps>0,slug)end
          for _,slug in ipairs({'fishing','herbalism','skinning'})do assert(not ns.ProfLeveling[slug] and ns.ProfGatheringRoutes.HasRoute(slug),slug)end
          for _,slug in ipairs({'camping','comprehension'})do
            assert(ns.ProfData.pro[slug] and not ns.ProfLeveling[slug] and not ns.ProfGatheringRoutes.HasRoute(slug),slug)
          end
        ''')

    def test_real_cooking_reference_uses_all_five_fishing_stages(self):
        self.lua.execute(r'''
          skills.cooking={cur=1,max=300};ns.ProfEconomy.Known=function()return true end
          ns.VendorPriceDB={GetOffers=function()return {{unlimited=true,available=true,purchasable=true,price=1,quantity=1,reference=true}}end,
            GetFormulaOffers=function()return {}end}
          local r=ns.ProfRouteAuto.ComputeFishing('cooking',{start=1,target=300,scheme='fishing',learnedOnly=true,recoveryEnabled=false})
          assert(r.targetReached and r.plannedTo==300 and #r.steps==5 and r.fishingReference)
          local expected={7751,7753,7755,20916,18238}
          for i,spell in ipairs(expected)do assert(r.steps[i][3]==spell)end
          assert(r.crafts==386 and r.total==0 and #r.mats==0)
          for _,fish in ipairs(r.fishMaterials)do assert(fish.count>0 and fish.source=='fishing')end
        ''')

    def test_normal_cooking_and_first_aid_still_use_automatic_solver(self):
        self.lua.execute(r'''
          for _,slug in ipairs({'cooking','first-aid'})do
            local s={recipes={{profession=slug,spell=101,item=10,count=1,mats={{11,1}},
              learn=1,yellow=100,green=200,grey=300,cooldown=false}},
              professions={[slug]={cur=1,max=300}},known={[slug..':101']=true},prices={[11]=7},coverageComplete=true}
            local opts={snapshot=s,start=1,target=2,scheme='cheapest',recoveryEnabled=false}
            local r=ns.ProfRouteAuto.Get(slug,opts);assert(r.status=='searching',slug)
            r=finish(slug,opts);assert(r.feasible and r.targetReached and r.total==7,slug)
          end
        ''')

    def test_gathering_checkpoints_never_invent_materials_or_crafts(self):
        self.lua.execute(r'''
          ns.ProfModule={ProfLearned=function()return {mining={cur=1,max=75},herbalism={cur=1,max=75},skinning={cur=1,max=75},fishing={cur=1,max=75}}end}
          for _,slug in ipairs({'mining','herbalism','skinning','fishing'})do
            local list=assert(ns.ProfGatheringRoutes.Steps(slug,300),slug)
            for _,step in ipairs(list)do
              assert(step[2]<=75 and step[3]==0 and step[4]==0 and step.navigationOnly and step.checkpoint,slug)
              assert(not step.mats and not step.requiredOutputs and not step.item,slug)
            end
          end
        ''')

    def test_missing_cap_does_not_assume_a_final_mining_goal(self):
        self.lua.execute("ns.ProfModule=nil;local list=ns.ProfGatheringRoutes.Steps('mining',300);assert(list and list[#list][2]<300)")

    def test_mining_smelt_reference_preserves_unfunded_field_checkpoints(self):
        self.lua.execute(r'''
          local checkpoints=0
          for _,step in ipairs(ns.ProfLeveling.mining.steps)do
            if step.checkpoint then
              checkpoints=checkpoints+1;assert(step[3]==0 and step[4]==0)
              local p=assert(ns.ProfExecution.NormalizePlan('mining',{mode='fixed',scheme='fixed',steps={step}}))
              local run=assert(ns.ProfExecution.StartNew('mining',p))
              local progress=ns.ProfExecution.Progress('mining',1)
              assert(not progress.complete and #progress.directMaterials==0 and run.plan.executionSteps[1].expectedCrafts==0)
              bag[2772]=999;assert(next(ns.ProfExecution.GetContinuation('mining'))==nil)
              ns.ProfExecution.End('mining','audit')
            end
          end
          assert(checkpoints==2 and ns.ProfGatheringRoutes.Steps('mining',300,{mode='smelt',maxSkill=300})==nil)
        ''')

    def test_gathering_hud_does_not_enter_smelting_solver(self):
        self.lua.execute("skills.mining={cur=1,max=75}")
        self.follow()
        self.lua.execute(r'''
          local calls=0;ns.ProfRouteAuto.Get=function()calls=calls+1;error('gathering entered crafting solver')end
          pf.Toggle('mining');pf.Sync();assert(calls==0 and pf.Following('mining'))
          local list=ns.ProfGatheringRoutes.Steps('mining',300);assert(list[1][3]==0 and list[1][2]==65)
          assert(not ns.ProfExecution.GetRun('mining'),'navigation must not create manufacturing receipts')
        ''')

    def test_fishing_herbalism_skinning_can_open_their_navigation_hud(self):
        self.lua.execute("for _,slug in ipairs({'fishing','herbalism','skinning'})do skills[slug]={cur=1,max=75}end")
        self.follow()
        self.lua.execute("for _,slug in ipairs({'fishing','herbalism','skinning'})do pf.Toggle(slug);assert(pf.Following(slug),slug)end")

    def test_poisons_hud_keeps_page_fixed_strategy(self):
        self.lua.execute("skills.poisons={cur=100,max=300}")
        self.follow("poisons")
        self.lua.execute(r'''
          local calls=0;ns.ProfRouteAuto.Get=function()calls=calls+1;error('poisons must stay fixed')end
          pf.Toggle('poisons');pf.Sync();assert(calls==0 and pf.Following('poisons'))
        ''')

    def test_old_automatic_poisons_execution_is_not_followed_as_fixed(self):
        self.lua.execute("skills.poisons={cur=100,max=300}")
        self.follow("poisons")
        self.lua.execute(r'''
          local recipe={profession='poisons',spell=101,item=10,count=1,mats={{20,1}},learn=100,yellow=200,green=250,grey=300}
          ns.ProfExecution.StartNew('poisons',{mode='auto',scheme='cheapest',executionVersion=1,steps={},
            executionSteps={{100,125,101,25,profession='poisons',segmentID='old-auto',recipe=recipe}},feasible=true})
          pf.Toggle('poisons');pf.Sync()
          assert(pf.pendingPlans.poisons.status=='recalculate_required')
          assert(pf.pendingPlans.poisons.diagnostics[1].code=='fixedOnlyChanged')
        ''')

    def test_first_aid_keeps_dev_auto_policy_and_unknown_fixed_recipe_is_blocked(self):
        self.lua.execute(r'''
          local steps=ns.ProfLeveling['first-aid'].steps
          local old=ns.ProfEconomy.FindRecipe
          ns.ProfEconomy.FindRecipe=function()return nil end
          local filtered,blocked=ns.ProfRouteAuto.FilterFixedSpecializations('first-aid',steps,{target=300})
          assert(#blocked==#steps and #filtered==0)
          ns.ProfEconomy.FindRecipe=old
        ''')

    def test_engineering_task_hud_displays_real_identity_and_does_not_complete_it(self):
        self.follow()
        self.lua.execute(r'''
          local goal={questID=3639,questName='工作成果',prerequisiteQuestIDs={3638},minSkill=200,minLevel=30,
            npcID=8126,npcName='尼克斯·斯普克斯宾',zone='加基森',x=52.53,y=27.3,abilityID=20222,inputs={{10560,20}}}
          local seg={200,200,0,0,segmentID='quest',profession='engineering',kind='specialization_quest',quest=goal}
          C_QuestLog={ReadyForTurnIn=function(id)return id==3639 end,IsOnQuest=function()return true end}
          local info=pf.SpecializationQuestInfo(seg);local text=table.concat(info.lines,'\n')
          assert(info.name=='工作成果' and text:find('3639') and text:find('3638') and text:find('尼克斯'))
          assert(text:find('200') and text:find('30') and text:find('任务可交付'))
          assert(goal.questProgress==nil and goal.abilityID==20222,'display mutated frozen goal facts')
        ''')


if __name__=="__main__":
    unittest.main()
