"""Real shipped recipes: static source fixes and user procurement switches.

Character state and auction observations are simulated; recipe/source records
are loaded unchanged from the addon. These are not live availability claims.
"""
import unittest
from test_prof_production_learning import production_runtime


class SourceFactsTests(unittest.TestCase):
    def setUp(self):
        self.lua = production_runtime()
        self.lua.execute('''
          function factsInput(slug,bound,currency,limited,side)
            return {known={},prices={},auctionSupply={},formulaOffers={},offers={},nonAuctionable={},
              ownedTeachingItems={},professions={[slug]={cur=300,max=300}},
              allowBindOnPickupFormulas=bound,allowCurrencyFormulas=currency,allowLimitedFormulas=limited,
              faction=side or 'A',classID=4,raceID=1,level=60,stamp=1000,
              completedQuests={},reputations={},specializationAbilities={}}
          end
          function market(s,id)
            s.prices[id]=1;s.auctionSupply[id]={quantity=2,observedAt=1000,complete=true,
              ownerExcluded=true,source='client-auction-results'}
          end
        ''')

    def test_real_currency_all_switches_and_both_factions(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',1251752)
          assert(r.formula==250998)
          for _,b in ipairs({false,true})do for _,c in ipairs({false,true})do
            for _,l in ipairs({false,true})do for _,side in ipairs({'A','H'})do
              local s=factsInput('alchemy',b,c,l,side)
              local ok,reason,d=E.SelectLearningRoute(r,s)
              assert(ok==(b or c),tostring(reason))
              if ok then
                local q=d.quote
                assert(q.source=='acquire' and q.acquisitionKind=='currency')
                assert(q.npcID==(side=='A' and 256729 or 248196),tostring(q.npcID))
                assert(q.acquisitionOffer.faction==side and q.acquisitionOffer.currencyID==3402)
                assert(q.acquisitionOffer.currencyAmount==180 and not q.costComplete)
              end
            end end
          end end
          -- The join must not mutate shared evidence or poison later factions.
          for _,route in ipairs(ns.ProfLearningSources.Get('alchemy',1251752).routes)do
            for _,o in ipairs(route.acquisition.vendors or {})do assert(o.faction==nil)end
          end
        ''')

    def test_real_item_exchange_preserves_payment_type_all_switches(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',17632)
          assert(r.formula==13517)
          for _,b in ipairs({false,true})do for _,c in ipairs({false,true})do
            for _,l in ipairs({false,true})do
              local ok,reason,d=E.SelectLearningRoute(r,factsInput('alchemy',b,c,l))
              assert(ok==(b or c),tostring(reason))
              if ok then
                local q=d.quote;local o=q.acquisitionOffer
                assert(q.npcID==256629 and q.source=='acquire')
                assert(#o.costItems==1 and o.costItems[1].id==263439 and o.costItems[1].count==10)
                assert(#o.currencies==0 and not o.currencyID and q.cost==0 and not q.costComplete)
              end
            end
          end end
        ''')

    def test_real_drop_quest_gold_and_auction_all_switches(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          for _,b in ipairs({false,true})do for _,c in ipairs({false,true})do
            for _,l in ipairs({false,true})do
              for _,case in ipairs({{1249957,249879,'drop'},{1250154,250185,'quest'}})do
                local r=E.FindRecipe('cooking',case[1]);assert(r.formula==case[2])
                local s=factsInput('cooking',b,c,l,'H')
                local ok,reason,d=E.SelectLearningRoute(r,s)
                assert(ok==b,tostring(reason))
                if ok then assert(d.quote.source=='acquire' and d.quote.acquisitionKind==case[3])end
              end
              local r=E.FindRecipe('alchemy',17580);local s=factsInput('alchemy',b,c,l)
              local ok,reason,d=E.SelectLearningRoute(r,s)
              assert(ok,tostring(reason));assert(d.quote.id==13501 and d.quote.source=='vendor')
              assert(d.quote.npcID==11278 and d.quote.unlimited and d.quote.cost==30000)
              r=E.FindRecipe('alchemy',6624);s=factsInput('alchemy',b,c,l)
              market(s,5642)
              ok,reason,d=E.SelectLearningRoute(r,s)
              assert(ok,tostring(reason));assert(d.quote.id==5642 and d.quote.source=='ah')
              s.prices[5642]=10000
              ok,reason,d=E.SelectLearningRoute(r,s)
              assert(ok and d.quote.source==(l and 'vendor' or 'ah'))
              s.auctionSupply[5642].quantity=1
              ok,reason,d=E.SelectLearningRoute(r,s)
              assert(ok==l,tostring(reason))
              if ok then assert(d.quote.source=='vendor' and d.quote.limited)end
            end
          end end
        ''')

    def test_three_supplemental_specialties_cannot_bypass_known_or_planned_choice(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          for _,case in ipairs({{12716,221337,20222},{15628,11828,20222},{15633,11827,20219}})do
            assert(ns.ProfGates.RequiredAbility(case[1])==0)
            for _,learned in ipairs({false,true})do
              observedKnown[case[1]]=learned
              local r=E.FindRecipe('engineering',case[1])
              assert(not learned or r.learningSpecializations and not r.learningInfo)
              local s=factsInput('engineering',true,true,true)
              s.known[r.key]=learned;s.ownedTeachingItems[case[2]]=1
              s.specializationAbilities[case[3]]=false
              local ok,reason=E.SelectLearningRoute(r,s)
              assert(not ok and reason=='specializationRequired')
              s.specializationAbilities[case[3]]=true
              s.engineeringSpecialization=case[3]==20222 and 'gnomish' or 'goblin'
              ok,reason=E.SelectLearningRoute(r,s)
              assert(not ok and reason=='specializationRequired')
              s.engineeringSpecialization=case[3]==20222 and 'goblin' or 'gnomish'
              local d;ok,reason,d=E.SelectLearningRoute(r,s)
              assert(ok,tostring(reason))
              assert(learned and d.status=='learned' or not learned and d.quote.source=='owned')
            end
          end
        ''')

    def test_binding_supplement_preserves_market_precedence_and_unknown(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local r=E.FindRecipe('engineering',1293088)
          assert(r.formula==274049)
          local raw=ns.ProfLearningSources.Get('engineering',1293088).routes[1].acquisition
          assert(raw.nonAuctionable==nil and raw.bindingType==nil)
          local a=r.learningInfo.routes[1].acquisition
          assert(a.bindingType==1 and a.bindOnPickup and a.bindingSource=='wowhead:item-tooltip')
          r=E.Copy(r)
          assert(r.learningInfo.routes[1].acquisition.bindingType==1)
          local s=factsInput('engineering',false,false,false);market(s,274049)
          local ok,reason,d=E.SelectLearningRoute(r,s)
          assert(ok and d.quote.source=='ah')
          s.auctionSupply[274049].quantity=1
          assert(not E.SelectLearningRoute(r,s))
          s.allowCurrencyFormulas=true;assert(not E.SelectLearningRoute(r,s))
          s.allowBindOnPickupFormulas=true
          ok,reason,d=E.SelectLearningRoute(r,s)
          assert(ok,tostring(reason));assert(d.quote.acquisitionKind=='drop')
          r=E.FindRecipe('blacksmithing',2671)
          assert(r.learningInfo.routes[1].teachingItemID==5577 and r.learningInfo.routes[1].acquisition.nonAuctionable==nil)
          s=factsInput('blacksmithing',false,false,false);market(s,5577)
          ok,reason,d=E.SelectLearningRoute(r,s)
          assert(ok,tostring(reason));assert(d.quote.source=='ah')
        ''')

    def test_static_npc_metadata_cache_does_not_cache_character_state(self):
        self.lua.execute('''
          local S=ns.ProfSupply;local a=S.FormulaFacts(250998)
          assert(a==S.FormulaFacts(250998) and a[248196].faction=='H' and a[256729].faction=='A')
          assert(a[248196].currencyID==nil and a[248196].costItems==nil)
        ''')

    def test_real_market_priority_over_every_binding_source_and_switch_combination(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local cases={{'alchemy',1251752,250998},{'alchemy',17632,13517},
            {'alchemy',17580,13501},{'alchemy',6624,5642},{'cooking',1249957,249879},
            {'cooking',1250154,250185},{'engineering',1293088,274049},{'blacksmithing',2671,5577}}
          for _,case in ipairs(cases)do
            for _,b in ipairs({false,true})do for _,c in ipairs({false,true})do
              for _,l in ipairs({false,true})do
                local r=E.FindRecipe(case[1],case[2]);local s=factsInput(case[1],b,c,l)
                market(s,case[3]);s.nonAuctionable[case[3]]=true
                local ok,reason,d=E.SelectLearningRoute(r,s)
                assert(ok,tostring(case[2])..':'..tostring(reason))
                assert(d.quote.source=='ah' and d.quote.cost==1 and not d.quote.acquisitionPending)
                local q=E.FormulaFor(r,s);assert(q.usable and q.source=='ah')
                s.recipes={r};s.known={}
                local result={formulas={q}};E.SummarizeFormulaSupply(result,s)
                assert(result.formulaAuctionSupplyInputs[case[3]].quantity==2)
              end
            end end
          end
        ''')

    def test_all_ten_verified_binding_gaps_are_filled_without_rewriting_provider(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local found={};local count=0
          local expected={[234271]=true,[234272]=true,[238782]=true,[238783]=true,[238784]=true,
            [238785]=true,[238786]=true,[238787]=true,[238788]=true,[274049]=true}
          for _,slug in ipairs({'engineering','enchanting','leatherworking','tailoring','blacksmithing','alchemy'})do
            for spell,raw in ns.ProfLearningSources.Each(slug)do
              for _,route in ipairs(raw.routes)do
                if expected[route.teachingItemID] then
                  assert(route.acquisition.nonAuctionable==nil)
                  for _,r in ipairs(E.GetLearningInfo(slug,spell).routes)do
                    if r.teachingItemID==route.teachingItemID then
                      assert(r.acquisition.bindingType==1 and r.acquisition.nonAuctionable==true)
                      if not found[r.teachingItemID] then count=count+1;found[r.teachingItemID]=true end
                    end
                  end
                end
              end
            end
          end
          assert(count==10,tostring(count))
        ''')


if __name__ == '__main__':
    unittest.main()
