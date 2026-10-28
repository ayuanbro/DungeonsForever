"""Learning paths use the same eligibility, acquisition and frozen price facts.

These are Lua 5.1 consumer tests. Native addon fixtures are a runtime baseline,
never an input to the source collector or its generated records.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "validation"))
from test_prof_native_data import native_runtime


class LearningSourceRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.lua = native_runtime()
        self.lua.execute("""
          ns.IsForever=true
          learningRecords={};sourceLookups=0
          ns.ProfLearningSources={meta={schema=1,product='wowf',build='1.60.1.99999',fingerprint='fixture-1'},
            Get=function(slug,spell)
              sourceLookups=sourceLookups+1
              return learningRecords[slug..':'..spell]
            end}
          function sourceRecord(slug,spell,routes)
            local info={profession=slug,spell=spell,routes=routes,coverage='partial',missingReasons={'entityMissing'}}
            learningRecords[slug..':'..spell]=info;return info
          end
          function trainer(id,cost,conditions)
            return {id=id,kind='trainer',status='confirmed',conditionsKnown=true,
              trainingCost=cost,conditions=conditions or {}}
          end
          function itemPath(id,item,conditions,acquisition)
            return {id=id,kind='item',teachingItemID=item,status='confirmed',conditionsKnown=true,
              conditions=conditions or {},acquisition=acquisition or {coverage='partial',conditions={}}}
          end
          function input(slug)
            return {known={},professions={[slug]={cur=300,max=300}},specializationAbilities={},
              classID=4,raceID=1,level=60,faction='A',prices={},formulaOffers={},offers={},
              nonAuctionable={},completedQuests={},reputations={},ownedTeachingItems={},
              allowLimitedFormulas=false,noFormula=false}
          end
        """)

    def test_missing_or_corrupt_supplement_does_not_revive_unknown_native_routes(self):
        self.lua.execute("""
          ns.ProfLearningSources=nil
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',7183)
          local ok,reason,detail=E.RouteRecipeEligibility(r,input('alchemy'))
          assert(not ok and reason=='learningDataMissing' and detail.status=='unknown')
          ns.ProfLearningSources={meta={schema=999,product='wowf'},Get=function()error('invalid provider ran')end}
          assert(not E.RouteRecipeEligibility(E.FindRecipe('alchemy',7183),input('alchemy')))
          local snap=input('alchemy');snap.known[r.key]=true
          assert(E.RouteRecipeEligibility(r,snap))
        """)

    def test_known_item_link_and_price_do_not_confirm_missing_learning_requirements(self):
        self.lua.execute("""
          sourceRecord('blacksmithing',2671,{{id='item:5577',kind='item',teachingItemID=5577,
            status='unknown',conditionsKnown=false,conditions={}}})
          local E=ns.ProfEconomy;local r=E.FindRecipe('blacksmithing',2671);local snap=input('blacksmithing')
          snap.prices[5577]=1
          local ok,reason=E.RouteRecipeEligibility(r,snap)
          assert(not ok and reason=='learningDataMissing')
          local quote=E.FormulaFor(r,snap)
          assert(not quote.usable and quote.reason=='learningDataMissing' and quote.cost==nil)
        """)

    def test_known_recipe_keeps_explicit_client_crafting_unavailability(self):
        self.lua.execute("""
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',7183);local snap=input('alchemy')
          snap.known[r.key]=true
          assert(E.RouteRecipeEligibility(r,snap))
          r.clientUnavailable=true
          local ok,reason=E.RouteRecipeEligibility(r,snap)
          assert(not ok and reason=='clientUnavailable')
        """)

    def test_confirmed_alternative_trainer_ignores_a_missing_book(self):
        self.lua.execute("""
          sourceRecord('blacksmithing',2671,{{id='item:5577',kind='item',teachingItemID=5577,
            status='unknown',conditionsKnown=false,conditions={}},trainer('trainer:2671',55)})
          local E=ns.ProfEconomy;local r=E.FindRecipe('blacksmithing',2671);local snap=input('blacksmithing')
          snap.prices[5577]=1
          local ok,reason,d=E.RouteRecipeEligibility(r,snap)
          assert(ok and d.routeId=='trainer:2671' and d.quote.id==nil and d.quote.source=='trainer')
          assert(d.quote.cost==55 and d.quote.learningRouteId==d.routeId)
          local quote=E.FormulaFor(r,snap)
          assert(quote.cost==55 and quote.source=='trainer' and quote.id==nil)
        """)

    def test_price_selection_and_purchase_policy_share_the_selected_learning_path(self):
        self.lua.execute("""
          sourceRecord('alchemy',7183,{trainer('trainer:7183',100),itemPath('book:7183',900001)})
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',7183);local snap=input('alchemy')
          snap.prices[900001]=25
          local ok,_,d=E.RouteRecipeEligibility(r,snap)
          assert(ok and d.routeId=='book:7183' and d.quote.cost==25 and d.quote.source=='ah')
          assert(E.FormulaFor(r,snap).learningRouteId==d.routeId)
          snap.noFormula=true
          ok,_,d=E.RouteRecipeEligibility(r,snap)
          assert(ok and d.routeId=='trainer:7183' and d.quote.cost==100)
        """)

    def test_fast_price_options_keep_live_character_facts_and_purchase_policy(self):
        self.lua.execute("""
          sourceRecord('alchemy',7183,{trainer('trainer:7183',100),itemPath('book:7183',900001,
            {{kind='classIDs',values={4}},{kind='reputation',factionID=529,value=6}})})
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',7183)
          UnitClass=function()return 'Rogue','ROGUE',4 end
          C_Reputation={GetFactionDataByID=function(id)assert(id==529);return {reaction=6}end}
          ns.ProfRouteAuto.AHPriceOf=function(id)return id==900001 and 3 or nil end
          local quote=E.FormulaFor(r,{profession='alchemy',noFormula=false})
          assert(quote.source=='ah' and quote.cost==3)
          quote=E.FormulaFor(r,{profession='alchemy',noFormula=true})
          assert(quote.source=='trainer' and quote.cost==100)
        """)

    def test_one_trainer_requirement_does_not_block_an_independent_book(self):
        self.lua.execute("""
          sourceRecord('alchemy',7183,{itemPath('book:7183',900001,{{kind='level',value=40}})})
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',7183);local snap=input('alchemy')
          r.trainerObserved=true;r.trainerAvailable=false;r.learningRequirements={level=60,skill=300}
          snap.level=40;snap.prices[900001]=13
          local ok,_,d=E.RouteRecipeEligibility(r,snap)
          assert(ok and d.routeId=='book:7183' and d.quote.cost==13)
        """)

    def test_owned_book_bypasses_acquisition_only_not_learning_reputation(self):
        self.lua.execute("""
          sourceRecord('alchemy',7183,{itemPath('book:7183',900001,
            {{kind='reputation',factionID=529,value=6}},
            {coverage='partial',conditions={{kind='quest',value=9}}})})
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',7183);local snap=input('alchemy')
          snap.ownedTeachingItems[900001]=1;snap.completedQuests[9]=false;snap.reputations[529]=6
          local ok,_,d=E.RouteRecipeEligibility(r,snap)
          assert(ok and d.quote.source=='owned' and d.quote.cost==0)
          snap.reputations[529]=5
          local reason;ok,reason=E.RouteRecipeEligibility(r,snap)
          assert(not ok and reason=='reputationRequired')
          snap.known[r.key]=true;assert(E.RouteRecipeEligibility(r,snap))
        """)

    def test_unknown_trainer_fee_is_not_free(self):
        self.lua.execute("""
          sourceRecord('alchemy',7183,{trainer('trainer:7183')})
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',7183);local snap=input('alchemy')
          local ok,_,d=E.RouteRecipeEligibility(r,snap)
          assert(ok and d.quote.cost==nil and not d.quote.usable and not d.quote.costComplete)
          local f=E.FormulaFor(r,snap);assert(not f.usable and f.reason=='learningPriceUnknown')
        """)

    def test_non_auctionable_book_cannot_use_an_auction_quote(self):
        self.lua.execute("""
          sourceRecord('alchemy',7183,{itemPath('book:7183',900001,{},
            {coverage='partial',conditions={},nonAuctionable=true})})
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',7183);local snap=input('alchemy')
          snap.prices[900001]=1
          local f=E.FormulaFor(r,snap)
          assert(not f.usable and f.cost==nil and f.source=='unknown')
          assert(snap.nonAuctionable[900001]==nil,'source projection mutated immutable input')
        """)

    def test_existing_trainer_value_and_observation_precede_auxiliary_quote(self):
        self.lua.execute("""
          sourceRecord('alchemy',7183,{trainer('trainer:7183',50)})
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',7183);local snap=input('alchemy')
          r.trainingCost=42
          local quote=E.FormulaFor(r,snap);assert(quote.cost==42)
          r.learningRequirements={trainingCost=17}
          quote=E.FormulaFor(r,snap);assert(quote.cost==17)
          assert(snap.prices[7183]==nil)
        """)

    def test_supplier_price_does_not_confirm_missing_access_conditions(self):
        self.lua.execute("""
          sourceRecord('alchemy',7183,{itemPath('book:7183',900001,{},
            {status='confirmed',coverage='partial',conditionsKnown=true,conditions={},
             vendors={{id=99,price=21,quantity=1,stock=-1,conditions={}}}})})
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',7183);local snap=input('alchemy')
          snap.noFormula=true
          local quote=E.FormulaFor(r,snap)
          assert(quote and not quote.usable and quote.cost==nil)
          assert(snap.formulaOffers[900001]==nil)
        """)

    def test_identified_supplier_quote_requires_its_own_conditions(self):
        self.lua.execute("""
          sourceRecord('alchemy',7183,{itemPath('book:7183',900001,{},
            {status='confirmed',coverage='partial',conditionsKnown=true,conditions={},
             vendors={{id=99,price=21,quantity=1,stock=-1,conditionsKnown=true,
               conditions={{kind='reputation',factionID=529,value=6}}}}})})
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',7183);local snap=input('alchemy')
          snap.noFormula=true;snap.reputations[529]=5
          local f=E.FormulaFor(r,snap);assert(not f.usable)
          snap.reputations[529]=6;f=E.FormulaFor(r,snap)
          assert(f.usable and f.source=='vendor' and f.npcID==99 and f.cost==21)
          assert(snap.formulaOffers[900001]==nil)
        """)

    def test_shared_book_costs_once_for_several_teaching_relations(self):
        self.lua.execute("""
          sourceRecord('alchemy',7183,{itemPath('book:7183',900001)})
          sourceRecord('alchemy',2334,{itemPath('book:2334',900001)})
          local E=ns.ProfEconomy;local a=E.FindRecipe('alchemy',7183);local b=E.FindRecipe('alchemy',2334)
          local snap=input('alchemy');snap.prices[900001]=73
          local rows,cost,complete=E.CollectFormulas({{recipe=a,spell=7183,count=1},
            {recipe=b,spell=2334,count=1}},'alchemy',snap)
          assert(#rows==1 and cost==73 and complete and #rows[1].recipes==2)
        """)

    def test_search_state_exhausted_auction_chooses_trainer_and_prepaid_shared_book_stays_free(self):
        self.lua.execute("""
          sourceRecord('alchemy',7183,{trainer('trainer:7183',100),itemPath('book:7183',900001)})
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',7183);local snap=input('alchemy')
          snap.prices[900001]=25
          snap.auctionSupply={[900001]={quantity=1,complete=true,ownerExcluded=true,source='fixture'}}
          local state={skill={alchemy=300},learned={},specializationAbilities={},ahUsed={[900001]=1},formulaPaid={}}
          local ok,_,d=E.RouteRecipeEligibility(r,snap,state)
          assert(ok and d.quote.source=='trainer' and d.quote.cost==100)
          state.formulaPaid[900001]=true
          ok,_,d=E.RouteRecipeEligibility(r,snap,state)
          assert(ok and d.routeId=='book:7183' and d.quote.cost==0 and d.quote.prepaid)
        """)

    def test_native_threshold_wins_without_mutating_generated_conditions(self):
        self.lua.execute("""
          local info=sourceRecord('engineering',8895,{trainer('trainer:8895',20,
            {{kind='skill',professionID=202,value=225},{kind='ability',value=20222}})})
          local E=ns.ProfEconomy;local r=E.FindRecipe('engineering',8895);local snap=input('engineering')
          snap.professions.engineering.cur=130;snap.specializationAbilities[20222]=true
          local ok,_,d=E.RouteRecipeEligibility(r,snap,{skill={engineering=130},specializationAbilities={[20222]=true}})
          assert(ok and r.learn==130 and d.numericConflicts[1].retainedValue==130)
          assert(info.routes[1].conditions[1].value==225)
        """)

    def test_character_failures_and_source_unknowns_are_distinct(self):
        self.lua.execute("""
          local E=ns.ProfEconomy;local snap=input('alchemy')
          sourceRecord('alchemy',7183,{trainer('trainer:7183',1,{{kind='classIDs',values={8}}})})
          local r=E.FindRecipe('alchemy',7183);local ok,reason=E.RouteRecipeEligibility(r,snap)
          assert(not ok and reason=='characterClassRequired')
          snap.classID=nil;ok,reason=E.RouteRecipeEligibility(r,snap)
          assert(not ok and reason=='clientDataPending')
          sourceRecord('alchemy',7183,{trainer('trainer:7183',1,
            {{kind='abilityRaceMask0',value='18446744072387644493'}})})
          r=E.FindRecipe('alchemy',7183);ok,reason=E.RouteRecipeEligibility(r,snap)
          assert(not ok and reason=='learningDataMissing')
        """)

    def test_injected_learning_snapshot_never_queries_live_character_or_prices(self):
        self.lua.execute("""
          sourceRecord('alchemy',7183,{itemPath('book:7183',900001,
            {{kind='classIDs',values={4}},{kind='raceIDs',values={1}},
             {kind='reputation',factionID=529,value=6},{kind='quest',value=9}})})
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',7183);local snap=input('alchemy')
          snap.reputations[529]=6;snap.completedQuests[9]=true;snap.prices[900001]=11
          local function unexpected()error('frozen input queried live state')end
          UnitClass=unexpected;UnitRace=unexpected;UnitLevel=unexpected;IsPlayerSpell=unexpected
          C_QuestLog={IsQuestFlaggedCompleted=unexpected};C_Reputation={GetFactionDataByID=unexpected}
          ns.ProfRouteAuto.AHPriceOf=unexpected
          ns.VendorPriceDB=ns.VendorPriceDB or {}
          ns.VendorPriceDB.GetFormulaOffers=unexpected
          local ok,_,d=E.RouteRecipeEligibility(r,snap)
          assert(ok and d.quote.cost==11)
          snap.reputations=nil
          local reason;ok,reason=E.RouteRecipeEligibility(r,snap)
          assert(not ok and reason=='clientDataPending')
        """)

    def test_only_referenced_observations_are_captured_and_changed_events_invalidate(self):
        self.lua.execute("""
          sourceRecord('alchemy',7183,{trainer('trainer:7183',2,
            {{kind='reputation',factionID=529,value=6},{kind='quest',value=9}})})
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',7183);local snap=input('alchemy')
          snap.recipes={r};local rank,done=5,false;local repReads,questReads=0,0
          C_Reputation={GetFactionDataByID=function(id)assert(id==529);repReads=repReads+1;return {reaction=rank}end}
          C_QuestLog={IsQuestFlaggedCompleted=function(id)assert(id==9);questReads=questReads+1;return done end}
          E.CaptureLearningFacts(snap)
          assert(repReads==1 and questReads==1 and snap.reputations[529]==5 and snap.completedQuests[9]==false)
          local initial=E.LearningObservationFingerprint();local revision=E.ClientStore().clientInputRevision or 0
          assert(not E.RefreshLearningObservations('UPDATE_FACTION'))
          assert(E.LearningObservationFingerprint()==initial)
          rank=6;E.QueueLearningObservationEvent('UPDATE_FACTION')
          assert(E.LearningObservationFingerprint()==initial,'event did synchronous character work')
          assert(E.RefreshLearningObservations())
          assert(E.LearningObservationFingerprint()~=initial and E.ClientStore().clientInputRevision==revision+1)
          assert(snap.reputations[529]==5,'frozen reputation was rewritten by event')
          done=true;assert(E.RefreshLearningObservations('QUEST_TURNED_IN'))
          assert(snap.completedQuests[9]==false)
        """)

    def test_known_capture_does_not_expand_learning_records_and_first_aid_keeps_native_path(self):
        self.lua.execute("""
          local E=ns.ProfEconomy
          IsPlayerSpell=function()return true end
          local snap=E.Capture('alchemy',{target=2,autoCraftTools=false,recoveryEnabled=false})
          assert(#snap.recipes>0 and sourceLookups==0)
          local r={profession='first-aid',spell=3275,key='first-aid:3275',dataSource='catalogue',learn=1,mats={{2589,1}}}
          local ok=E.RouteRecipeEligibility(r,{known={},professions={['first-aid']={cur=1,max=75}},specializationAbilities={}})
          assert(ok)
          assert(E.ProfessionSlug(40)=='poisons')
        """)

    def test_compact_provider_views_materialize_once_without_losing_named_snapshot_fields(self):
        self.lua.execute("""
          local shared={{kind='reputation',factionID=529,value=6}};local calls=0
          local view=setmetatable({7183,shared},{__index=function(t,k)
            if k=='spell' then return t[1] elseif k=='conditions' then return t[2] end
          end,__profLearningMaterialize=function(t)
            calls=calls+1;return {spell=t[1],conditions=t[2]}
          end})
          local result=ns.ProfEconomy.Copy({a=view,b=view,other=shared})
          assert(calls==1 and result.a==result.b and result.a.spell==7183)
          assert(result.a.conditions==result.other and getmetatable(result.a)==nil)
          assert(result.a.conditions~=shared and view.spell==7183)
        """)

    def test_level_and_required_other_profession_change_context_revision_once(self):
        self.lua.execute("""
          local E=ns.ProfEconomy
          assert(not E.UpdateLearningContext(60,{alchemy={cur=100,max=300},engineering={cur=50,max=75}}))
          local initial=E.LearningObservationFingerprint()
          assert(not E.UpdateLearningContext(60,{engineering={cur=50,max=75},alchemy={cur=100,max=300}}))
          assert(E.LearningObservationFingerprint()==initial)
          assert(E.UpdateLearningContext(61,{alchemy={cur=100,max=300},engineering={cur=50,max=75}}))
          local level=E.LearningObservationFingerprint();assert(level~=initial)
          assert(E.UpdateLearningContext(61,{alchemy={cur=100,max=300},engineering={cur=51,max=75}}))
          assert(E.LearningObservationFingerprint()~=level)
        """)


if __name__ == "__main__":
    unittest.main()
