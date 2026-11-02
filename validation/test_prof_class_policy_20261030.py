"""Ordinary professions ignore class fields; real poison recipes require Rogue.

Injected stale class fields exercise the policy. Recipe, teaching item and
specialization facts come from the shipped provider, unchanged by these tests.
"""
import unittest
import test_prof_source_facts_20261030 as facts


class ProfessionClassPolicyTests(unittest.TestCase):
    def setUp(self):
        facts.SourceFactsTests.setUp(self)
        self.lua.execute('''
          function staleClassFields()
            return {{kind='classIDs',values={8}},{kind='classIDs'},
              {kind='classMask',value=0},{kind='classMask',value=-1},
              {kind='itemClassMask',value=0},{kind='itemClassMask',value=128},
              {kind='abilityClassMask',value='18446744073709551615'}}
          end
          function appendClassFields(conditions)
            conditions=conditions or {}
            for _,c in ipairs(staleClassFields())do conditions[#conditions+1]=c end
            return conditions
          end
        ''')

    def test_real_ordinary_professions_ignore_class_fields_at_every_source_layer(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          UnitClass=function()error('ordinary profession must not query character class')end
          for _,case in ipairs({{'alchemy',7183},{'blacksmithing',2660},{'leatherworking',2149},
            {'tailoring',2963},{'engineering',3918},{'enchanting',7418},{'cooking',2538}})do
            local r=E.Copy(E.FindRecipe(case[1],case[2]));assert(r.learningInfo)
            r.learningConstraints=staleClassFields()
            for _,route in ipairs(r.learningInfo.routes)do
              route.conditions=appendClassFields(route.conditions)
              local a=route.acquisition
              if a then
                a.conditions=appendClassFields(a.conditions)
                for _,o in ipairs(a.vendors or {})do o.conditions=appendClassFields(o.conditions)end
                for _,q in ipairs(a.quests or {})do q.conditions=appendClassFields(q.conditions)end
              end
            end
            local s=factsInput(case[1],false,false,false);s.classID=nil
            local ok,reason=E.SelectLearningRoute(r,s)
            assert(ok,case[1]..':'..tostring(reason))
          end
        ''')

    def test_market_priority_keeps_two_recent_items_and_ignores_class_and_binding_fields(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local r=E.Copy(E.FindRecipe('cooking',1249957))
          assert(r.formula==249879 and r.learningInfo.routes[1].acquisition.nonAuctionable)
          r.learningConstraints=staleClassFields()
          r.learningInfo.routes[1].conditions=appendClassFields(r.learningInfo.routes[1].conditions)
          local s=factsInput('cooking',false,false,false);s.classID=nil;market(s,249879)
          local ok,reason,d=E.SelectLearningRoute(r,s)
          assert(ok,tostring(reason));assert(d.quote.source=='ah' and d.quote.cost==1)
          s.auctionSupply[249879].quantity=1
          assert(not E.SelectLearningRoute(r,s),'class policy removed the auction quantity threshold')
          s.auctionSupply[249879].quantity=2;s.stamp=3000
          assert(not E.SelectLearningRoute(r,s),'stale auction observation was accepted')
          s.stamp=1000;s.prices[249879]=nil
          assert(not E.SelectLearningRoute(r,s),'missing auction price was accepted')
          s.allowBindOnPickupFormulas=true
          ok,reason,d=E.SelectLearningRoute(r,s)
          assert(ok and d.quote.acquisitionKind=='drop',tostring(reason))
        ''')

    def test_all_26_real_poisons_require_rogue_even_when_known_or_owned(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local count=0
          for spell,info in ns.ProfLearningSources.Each('poisons')do
            count=count+1;local r=E.FindRecipe('poisons',spell);assert(r)
            for _,class in ipairs({1,4,8})do for _,learned in ipairs({false,true})do
              local s=factsInput('poisons',true,true,true);s.classID=class;s.known[r.key]=learned
              for _,route in ipairs(info.routes)do if route.teachingItemID then
                market(s,route.teachingItemID);s.ownedTeachingItems[route.teachingItemID]=1
              end end
              local ok,reason=E.SelectLearningRoute(r,s)
              if class~=4 then
                assert(not ok and reason=='poisonRogueRequired',tostring(spell)..':'..tostring(reason))
                assert(not E.FormulaFor(r,s).usable)
              elseif learned then assert(ok,tostring(spell)..':'..tostring(reason))
              else assert(reason~='poisonRogueRequired',tostring(spell))end
            end end
          end
          assert(count==26,tostring(count))
        ''')

    def test_real_poison_book_market_path_is_available_to_rogue_only(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local r=E.FindRecipe('poisons',25347)
          local s=factsInput('poisons',false,false,false);market(s,21302)
          local ok,reason,d=E.SelectLearningRoute(r,s)
          assert(ok,tostring(reason));assert(d.quote.source=='ah' and d.quote.id==21302)
          s.classID=1;ok,reason=E.SelectLearningRoute(r,s)
          assert(not ok and reason=='poisonRogueRequired')
        ''')

    def test_legacy_catalogue_class_only_fields_do_not_become_unknown_conditions(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;ns.IsForever=false
          local r=E.FindRecipe('alchemy',7183);r.learningConstraints=staleClassFields()
          r.learningSourcesRequired=nil;r.learningInfo=nil
          local s=factsInput('alchemy',false,false,false);s.classID=nil
          local ok,reason=E.RouteRecipeEligibility(r,s)
          assert(ok,tostring(reason))
        ''')

    def test_poison_gate_does_not_depend_on_route_masks_or_live_state_in_a_snapshot(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local r=E.FindRecipe('poisons',25347)
          r.learningInfo=nil;r.learningRoutes={};r.learningConstraints={}
          local s=factsInput('poisons',false,false,false);s.known[r.key]=true;s.classID=1
          local ok,reason=E.SelectLearningRoute(r,s)
          assert(not ok and reason=='poisonRogueRequired')
          UnitClass=function()error('frozen snapshot queried live class')end
          s.classID=nil;ok,reason=E.SelectLearningRoute(r,s)
          assert(not ok and reason=='clientDataPending')
          s.classID=4;assert(E.SelectLearningRoute(r,s))
          s.classID=1;ns.IsForever=false;r.learningSourcesRequired=nil
          ok,reason=E.RouteRecipeEligibility(r,s)
          assert(not ok and reason=='poisonRogueRequired')
          local q=E.FormulaFor(r,s)
          assert(not q.usable and q.reason=='poisonRogueRequired')
        ''')

    def test_engineering_and_leather_specializations_still_override_market_admission(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          for _,case in ipairs({{'engineering',15628,11828,20222},
            {'leatherworking',19050,15726,10656},{'leatherworking',19059,15732,10658},
            {'leatherworking',19062,15735,10660}})do
            local r=E.FindRecipe(case[1],case[2]);r.learningConstraints=staleClassFields()
            local s=factsInput(case[1],false,false,false);s.classID=nil;market(s,case[3])
            s.specializationAbilities[case[4]]=false
            local ok,reason=E.SelectLearningRoute(r,s)
            assert(not ok and reason=='specializationRequired',tostring(reason))
            s.specializationAbilities[case[4]]=true
            ok,reason=E.SelectLearningRoute(r,s);assert(ok,tostring(reason))
            if case[1]=='engineering' then
              s.engineeringSpecialization='gnomish'
              ok,reason=E.SelectLearningRoute(r,s)
              assert(not ok and reason=='specializationRequired')
            end
          end
        ''')


if __name__ == '__main__':
    unittest.main()
