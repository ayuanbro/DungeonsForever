"""Acquisition policy cases at the real Lua learning/route boundary.

Fixtures describe isolated acquisition alternatives. Specialization tests use
the shipped recipe and learning data; these are offline checks, not live stock.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_pipeline.professions.tests import test_runtime_learning as learning_fixture
from test_prof_production_learning import production_runtime


class LearningChannelsV2Tests(unittest.TestCase):
    def setUp(self):
        learning_fixture.LearningSourceRuntimeTests.setUp(self)
        self.lua.execute("""
          function market(snap,id,price,quantity)
            snap.stamp=1000;snap.prices[id]=price;snap.auctionSupply=snap.auctionSupply or {}
            snap.auctionSupply[id]={quantity=quantity or 2,observedAt=1000,
              complete=true,ownerExcluded=true,source='client-auction-results'}
          end
        """)

    def test_priced_stocked_auction_needs_no_historical_source_confirmation(self):
        self.lua.execute("""
          sourceRecord('blacksmithing',2671,{{id='item:5577',kind='item',teachingItemID=5577,
            status='unknown',conditionsKnown=false,conditions={}}})
          local E=ns.ProfEconomy;local r=E.FindRecipe('blacksmithing',2671)
          local snap=input('blacksmithing');market(snap,5577,73,2)
          snap.allowUnknownLearningSources=false;snap.noUnknownFormula=true;snap.noFormula=true
          snap.learnedOnly=true;snap.considerAuctionSupply=false
          local ok,reason,detail=E.RouteRecipeEligibility(r,snap)
          assert(ok,tostring(reason))
          assert(detail.quote.source=='ah' and detail.quote.cost==73)
          assert(E.FormulaFor(r,snap).learningRouteId==detail.routeId)
        """)

    def test_native_teaching_item_survives_missing_supplement_when_market_is_valid(self):
        self.lua.execute("""
          ns.ProfLearningSources=nil
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',3230)
          assert(r.formula==2553)
          local snap=input('alchemy');market(snap,2553,99,2)
          local ok,reason,detail=E.RouteRecipeEligibility(r,snap)
          assert(ok,tostring(reason));assert(detail.quote.source=='ah' and detail.quote.cost==99)
        """)

    def test_auction_requires_price_and_two_recent_listings_even_without_material_budget(self):
        self.lua.execute("""
          sourceRecord('blacksmithing',2671,{itemPath('book',5577)})
          local E=ns.ProfEconomy;local r=E.FindRecipe('blacksmithing',2671)
          local snap=input('blacksmithing');snap.considerAuctionSupply=false
          market(snap,5577,100,1)
          local ok,reason=E.RouteRecipeEligibility(r,snap)
          assert(not ok and reason=='formulaAuctionSupplyInsufficient',tostring(reason))
          market(snap,5577,100,2);assert(E.RouteRecipeEligibility(r,snap))
          snap.auctionSupply[5577].observedAt=1;snap.stamp=2000
          ok,reason=E.RouteRecipeEligibility(r,snap)
          assert(not ok and reason=='formulaAuctionSupplyUnknown',tostring(reason))
          market(snap,5577,nil,2);assert(not E.RouteRecipeEligibility(r,snap))
        """)

    def test_limited_npc_switch_does_not_disable_auction_and_only_selects_cheaper_npc(self):
        self.lua.execute("""
          sourceRecord('blacksmithing',2671,{itemPath('book',5577,{},
            {status='confirmed',conditionsKnown=true,conditions={},vendors={{id=99,price=50,
              quantity=1,stock=1,conditionsKnown=true,conditions={}}}})})
          local E=ns.ProfEconomy;local r=E.FindRecipe('blacksmithing',2671)
          local snap=input('blacksmithing');market(snap,5577,75,2)
          assert(E.FormulaFor(r,snap).source=='ah')
          snap.allowLimitedFormulas=true
          local quote=E.FormulaFor(r,snap)
          assert(quote.source=='vendor' and quote.cost==50)
          market(snap,5577,50,2);assert(E.FormulaFor(r,snap).source=='ah',
            'equal-price limited stock added risk without saving gold')
          market(snap,5577,25,2);assert(E.FormulaFor(r,snap).source=='ah')
          snap.allowLimitedFormulas=false;snap.auctionSupply={}
          assert(not E.RouteRecipeEligibility(r,snap))
          snap.allowLimitedFormulas=true;assert(E.RouteRecipeEligibility(r,snap))
        """)

    def test_unlimited_npc_needs_neither_limited_nor_auction_permission(self):
        self.lua.execute("""
          sourceRecord('blacksmithing',2671,{itemPath('book',5577,{},
            {status='confirmed',conditionsKnown=true,conditions={},vendors={{id=99,price=50,
              quantity=1,stock=-1,conditionsKnown=true,conditions={}}}})})
          local E=ns.ProfEconomy;local r=E.FindRecipe('blacksmithing',2671)
          local snap=input('blacksmithing');snap.noFormula=true
          local ok,reason,detail=E.RouteRecipeEligibility(r,snap)
          assert(ok,tostring(reason));assert(detail.quote.source=='vendor' and detail.quote.cost==50)
        """)

    def test_unknown_source_coverage_does_not_block_a_concrete_gold_supplier(self):
        self.lua.execute("""
          local E=ns.ProfEconomy
          local function quote(mutate)
            local offer={id=99,price=50,stock=-1,faction='A',status='unknown',
              conditionsKnown=false,conditions={}}
            if mutate then mutate(offer) end
            local route=itemPath('book',5577,{},
              {status='unknown',conditionsKnown=false,conditions={},vendors={offer}})
            route.status='unknown';route.conditionsKnown=false
            sourceRecord('blacksmithing',2671,{route})
            local snap=input('blacksmithing')
            snap.noFormula=true;snap.allowUnknownLearningSources=false
            local r=E.FindRecipe('blacksmithing',2671)
            return E.FormulaFor(r,snap),E.RouteRecipeEligibility(r,snap)
          end
          local q,allowed=quote()
          assert(allowed and q.usable and q.source=='vendor' and q.cost==50,
            'source-coverage labels blocked an identified, priced, unlimited supplier')
          assert(q.count==1 and q.npcID==99,'missing bundle size must default to one')
          for _,mutate in ipairs({
            function(o)o.id=0 end,
            function(o)o.faction='H' end,
            function(o)o.available=false end,
            function(o)o.purchasable=false end,
            function(o)o.priceUsable=false end,
            function(o)o.stock=1 end,
            function(o)o.quantity=0 end,
            function(o)o.conditions={{kind='level',value=61}} end,
            function(o)o.conditions={{kind='abilityRaceMask0',value=1}} end,
            function(o)o.currencies={{id=123,count=1}} end,
            function(o)o.costItems={{id=123,count=1}} end
          })do
            q,allowed=quote(mutate)
            assert(not allowed and not q.usable,'a concrete purchase restriction was ignored')
          end
        """)

    def test_bound_drop_and_quest_require_bound_permission(self):
        for acquisition in (
            "{nonAuctionable=true,dropSourceCount=2,conditions={}}",
            "{nonAuctionable=true,quests={{id=9}},conditions={}}",
        ):
            with self.subTest(acquisition=acquisition):
                self.lua.globals().acquisition_fixture = self.lua.eval(acquisition)
                self.lua.execute("""
                  sourceRecord('blacksmithing',2671,{itemPath('book',5577,{},acquisition_fixture)})
                  local E=ns.ProfEconomy;local r=E.FindRecipe('blacksmithing',2671)
                  local snap=input('blacksmithing')
                  local ok,reason=E.RouteRecipeEligibility(r,snap)
                  assert(not ok and reason=='bindOnPickupFormulaDisabled',tostring(reason))
                  snap.allowCurrencyFormulas=true;assert(not E.RouteRecipeEligibility(r,snap))
                  snap.allowBindOnPickupFormulas=true
                  local detail;ok,reason,detail=E.RouteRecipeEligibility(r,snap)
                  assert(ok,tostring(reason));assert(detail.quote.source=='acquire')
                  assert(detail.quote.acquisitionPending and not detail.quote.costComplete)
                  assert(detail.quote.cost==nil,'unpriced acquisition was converted into free gold')
                """)

    def test_bound_and_currency_switch_truth_table_preserves_narrow_currency_exception(self):
        self.lua.execute("""
          local E=ns.ProfEconomy
          for _,bound in ipairs({false,true})do for _,currency in ipairs({false,true})do
            for _,kind in ipairs({'drop','quest','currency'})do
              local acquisition={nonAuctionable=true,conditions={}}
              if kind=='drop' then acquisition.dropSourceCount=1
              elseif kind=='quest' then acquisition.quests={{id=9,conditions={}}}
              else acquisition.vendors={{id=99,hasExtendedCost=true,currencyID=123,
                stock=-1,conditionsKnown=true,conditions={}}} end
              sourceRecord('blacksmithing',2671,{itemPath('book',5577,{},acquisition)})
              local r=E.FindRecipe('blacksmithing',2671);local snap=input('blacksmithing')
              snap.allowBindOnPickupFormulas=bound;snap.allowCurrencyFormulas=currency
              local expected=bound or (kind=='currency' and currency)
              local ok,reason,detail=E.RouteRecipeEligibility(r,snap)
              assert(ok==expected,kind..' '..tostring(bound)..'/'..tostring(currency)..': '..tostring(reason))
              if expected then
                assert(detail.quote.source=='acquire' and detail.quote.acquisitionKind==kind)
                assert(detail.quote.cost==nil and not detail.quote.costComplete)
                assert(detail.quote.acquisitionPending)
              end
            end
          end end
        """)

    def test_bound_gold_supplier_ignores_nongold_switches_and_still_checks_limited_stock(self):
        self.lua.execute("""
          local E=ns.ProfEconomy
          for _,stock in ipairs({-1,1})do
            sourceRecord('blacksmithing',2671,{itemPath('book',5577,{},
              {nonAuctionable=true,conditions={},vendors={{id=99,price=50,
                stock=stock,conditions={}}}})})
            local r=E.FindRecipe('blacksmithing',2671)
            for _,bound in ipairs({false,true})do for _,currency in ipairs({false,true})do
              local snap=input('blacksmithing')
              snap.allowBindOnPickupFormulas=bound;snap.allowCurrencyFormulas=currency
              local q=E.FormulaFor(r,snap)
              assert(not q.ahPrice,'missing auction price became a purchase')
              if stock==-1 then assert(q.usable and q.source=='vendor' and q.cost==50)
              else
                assert(not q.usable and q.reason=='limitedFormulaDisabled',tostring(q.reason))
                snap.allowLimitedFormulas=true;q=E.FormulaFor(r,snap)
                assert(q.usable and q.source=='vendor' and q.cost==50)
              end
            end end
          end
        """)

    def test_gold_and_exchange_cost_stays_unpriced_acquisition_under_nongold_permission(self):
        self.lua.execute("""
          local E=ns.ProfEconomy
          for _,field in ipairs({'currencyID','hasExtendedCost','currencies','costItems'})do
            local offer={id=99,price=50,stock=-1,conditions={}}
            if field=='currencyID' then offer[field]=123
            elseif field=='hasExtendedCost' then offer[field]=true
            else offer[field]={{id=123,count=2}} end
            sourceRecord('blacksmithing',2671,{itemPath('book',5577,{},
              {nonAuctionable=true,conditions={},vendors={offer}})})
            local r=E.FindRecipe('blacksmithing',2671);local snap=input('blacksmithing')
            local q=E.FormulaFor(r,snap)
            assert(not q.usable and q.reason=='currencyFormulaDisabled',field)
            snap.allowBindOnPickupFormulas=true;q=E.FormulaFor(r,snap)
            assert(q.usable and q.source=='acquire' and q.acquisitionKind=='currency',field)
            assert(q.cost==50 and q.totalCost==50 and q.unpriced and not q.costComplete and q.acquisitionPending,
              'known gold was discarded or the exchange was treated as fully priced')
          end
        """)

    def test_complete_gold_purchase_precedes_a_partial_exchange_quote_and_retains_known_exchange_gold(self):
        self.lua.execute("""
          local E=ns.ProfEconomy
          local exchange=itemPath('exchange',5577,{},
            {nonAuctionable=true,conditions={},vendors={{id=99,price=50,
              currencyID=123,stock=-1,conditions={}}}})
          local gold=itemPath('gold',5578,{},
            {conditions={},vendors={{id=100,price=100,stock=-1,conditions={}}}})
          sourceRecord('blacksmithing',2671,{exchange,gold})
          local r=E.FindRecipe('blacksmithing',2671);local snap=input('blacksmithing')
          snap.allowBindOnPickupFormulas=true
          local q=E.FormulaFor(r,snap)
          assert(q.source=='vendor' and q.id==5578 and q.cost==100 and q.costComplete,
            'a partially priced exchange displaced a complete gold quote')
          sourceRecord('blacksmithing',2671,{exchange})
          r=E.FindRecipe('blacksmithing',2671);q=E.FormulaFor(r,snap)
          assert(q.source=='acquire' and q.cost==50 and q.unpriced and not q.costComplete)
          local rows,total,complete=E.CollectFormulas({{recipe=r,spell=2671,count=5},
            {recipe=r,spell=2671,count=2}},'blacksmithing',snap)
          assert(#rows==1 and total==50 and not complete,
            'the shared book known gold was lost or charged per craft')
          assert(rows[1].cost==50 and rows[1].acquisitionPending and not rows[1].costComplete)
        """)

    def test_recipe_binding_fact_alone_supports_bound_drop_and_currency_channels(self):
        self.lua.execute("""
          local E=ns.ProfEconomy
          for _,kind in ipairs({'drop','currency'})do
            local acquisition={conditions={}}
            if kind=='drop' then acquisition.dropSourceCount=1
            else acquisition.vendors={{id=99,currencyID=123,stock=-1,conditions={}}} end
            sourceRecord('blacksmithing',2671,{itemPath('book',5577,{},acquisition)})
            local r=E.FindRecipe('blacksmithing',2671);r.bindOnPickup=true
            local snap=input('blacksmithing');market(snap,5577,1,20)
            assert(acquisition.nonAuctionable==nil and snap.nonAuctionable[5577]==nil)
            local q=E.FormulaFor(r,snap)
            assert(q.usable and q.source=='ah','binding overrode a valid auction quote')
            snap.prices[5577]=nil
            q=E.FormulaFor(r,snap)
            assert(not q.usable and not q.ahPrice)
            if kind=='drop' then snap.allowBindOnPickupFormulas=true
            else snap.allowCurrencyFormulas=true end
            q=E.FormulaFor(r,snap)
            assert(q.usable and q.source=='acquire' and q.acquisitionKind==kind,
              'recipe binding was ignored for '..kind)
          end
        """)

    def test_currency_requires_an_accessible_in_stock_identified_supplier(self):
        cases = (
            ('opposite faction', "offer.faction='H'"),
            ('invalid NPC', 'offer.id=0'),
            ('level unmet', "offer.conditions={{kind='level',value=61}}"),
            ('reputation unknown', "offer.conditions={{kind='reputation',factionID=529,value=6}}"),
            ('unsupported condition', "offer.conditions={{kind='abilityRaceMask0',value=1}}"),
            ('empty stock', 'offer.stock=0;snap.allowLimitedFormulas=true'),
            ('limited disabled', 'offer.stock=1'),
        )
        for label, mutation in cases:
            with self.subTest(supplier=label):
                self.lua.execute("""
                  offer={id=99,hasExtendedCost=true,currencyID=123,stock=-1,
                    conditionsKnown=true,conditions={}}
                  snap=input('blacksmithing');snap.allowCurrencyFormulas=true
                """)
                self.lua.execute(mutation)
                self.lua.execute("""
                  sourceRecord('blacksmithing',2671,{itemPath('book',5577,{},
                    {nonAuctionable=true,conditions={},vendors={offer}})})
                  local E=ns.ProfEconomy;local r=E.FindRecipe('blacksmithing',2671)
                  local ok,reason=E.RouteRecipeEligibility(r,snap)
                  assert(not ok,'ineligible currency supplier entered the route')
                  assert(not E.FormulaFor(r,snap).usable)
                """)

    def test_currency_unlimited_and_explicitly_enabled_limited_supplier_are_usable(self):
        for stock, allow_limited in ((-1, False), (1, True)):
            with self.subTest(stock=stock, allow_limited=allow_limited):
                self.lua.globals().supplier_stock = stock
                self.lua.globals().limited_permission = allow_limited
                self.lua.execute("""
                  sourceRecord('blacksmithing',2671,{itemPath('book',5577,{},
                    {nonAuctionable=true,conditions={},vendors={{id=99,hasExtendedCost=true,
                      currencyID=123,stock=supplier_stock,conditionsKnown=true,conditions={}}}})})
                  local E=ns.ProfEconomy;local r=E.FindRecipe('blacksmithing',2671)
                  local snap=input('blacksmithing');snap.allowCurrencyFormulas=true
                  snap.allowLimitedFormulas=limited_permission
                  local ok,reason,detail=E.RouteRecipeEligibility(r,snap)
                  assert(ok,tostring(reason))
                  assert(detail.quote.source=='acquire' and detail.quote.acquisitionKind=='currency')
                """)

    def test_currency_permission_does_not_admit_an_unpriced_tradable_exchange(self):
        self.lua.execute("""
          sourceRecord('blacksmithing',2671,{itemPath('book',5577,{},
            {nonAuctionable=false,conditions={},vendors={{id=99,hasExtendedCost=true,
              currencyID=123,stock=-1,conditionsKnown=true,conditions={}}}})})
          local E=ns.ProfEconomy;local r=E.FindRecipe('blacksmithing',2671)
          local snap=input('blacksmithing');snap.allowCurrencyFormulas=true
          assert(not E.RouteRecipeEligibility(r,snap),'currency permission admitted an unpriced tradable book')
          market(snap,5577,25,2)
          local ok,reason,detail=E.RouteRecipeEligibility(r,snap)
          assert(ok,tostring(reason));assert(detail.quote.source=='ah' and detail.quote.cost==25)
        """)

    def test_bound_acquisition_requirements_apply_until_the_book_is_owned(self):
        acquisitions = (
            "{nonAuctionable=true,dropSourceCount=1}",
            "{nonAuctionable=true,vendors={{id=99,stock=-1,currencyID=123,hasExtendedCost=true,conditionsKnown=true,conditions={}}}}",
            "{nonAuctionable=true,status='confirmed',conditionsKnown=true,vendors={{id=99,stock=-1,price=25,quantity=1,conditionsKnown=true,conditions={}}}}",
        )
        for acquisition in acquisitions:
            with self.subTest(acquisition=acquisition):
                self.lua.globals().acquisition_fixture = self.lua.eval(acquisition)
                self.lua.execute("""
                  acquisition_fixture.conditions={{kind='quest',value=9}}
                  sourceRecord('blacksmithing',2671,{itemPath('book',5577,
                    {{kind='reputation',factionID=529,value=6}},acquisition_fixture)})
                  local E=ns.ProfEconomy;local r=E.FindRecipe('blacksmithing',2671)
                  local snap=input('blacksmithing');snap.allowBindOnPickupFormulas=true
                  snap.allowCurrencyFormulas=true;snap.completedQuests[9]=false;snap.reputations[529]=6
                  assert(not E.RouteRecipeEligibility(r,snap),'unmet acquisition condition was ignored')
                  snap.ownedTeachingItems[5577]=1
                  local ok,reason,detail=E.RouteRecipeEligibility(r,snap)
                  assert(ok,tostring(reason));assert(detail.quote.source=='owned' and detail.quote.cost==0)
                  snap.reputations[529]=5
                  ok,reason=E.RouteRecipeEligibility(r,snap)
                  assert(not ok and reason=='reputationRequired','owned book bypassed a learning condition')
                  snap.ownedTeachingItems={};snap.reputations[529]=6;snap.completedQuests[9]=true
                  ok,reason=E.RouteRecipeEligibility(r,snap);assert(ok,tostring(reason))
                """)

    def test_owned_book_bypasses_acquisition_but_retains_learning_conditions(self):
        self.lua.execute("""
          sourceRecord('blacksmithing',2671,{itemPath('book',5577,
            {{kind='reputation',factionID=529,value=6}},
            {nonAuctionable=true,conditions={{kind='quest',value=9}},dropSourceCount=1})})
          local E=ns.ProfEconomy;local r=E.FindRecipe('blacksmithing',2671)
          local snap=input('blacksmithing');snap.ownedTeachingItems[5577]=1
          snap.completedQuests[9]=false;snap.reputations[529]=5
          local ok,reason=E.RouteRecipeEligibility(r,snap)
          assert(not ok and reason=='reputationRequired',tostring(reason))
          snap.reputations[529]=6
          local detail;ok,reason,detail=E.RouteRecipeEligibility(r,snap)
          assert(ok,tostring(reason));assert(detail.quote.source=='owned' and detail.quote.cost==0)
          snap.ownedTeachingItems={};snap.known[r.key]=true
          ok,reason,detail=E.RouteRecipeEligibility(r,snap)
          assert(ok and detail.status=='learned' and E.FormulaFor(r,snap)==nil)
          r.craftingUnavailable=true;ok,reason=E.RouteRecipeEligibility(r,snap)
          assert(not ok and reason=='clientUnavailable')
        """)

    def test_dual_trainer_and_book_choose_lowest_cost_eligible_learning_path(self):
        self.lua.execute("""
          sourceRecord('blacksmithing',2671,{trainer('trainer',100),itemPath('book',5577)})
          local E=ns.ProfEconomy;local r=E.FindRecipe('blacksmithing',2671)
          local snap=input('blacksmithing');market(snap,5577,25,2)
          assert(E.FormulaFor(r,snap).source=='ah')
          market(snap,5577,200,2)
          local quote=E.FormulaFor(r,snap)
          assert(quote.source=='trainer' and quote.cost==100 and quote.id==nil)
          market(snap,5577,25,1);assert(E.FormulaFor(r,snap).source=='trainer')
          local grant=trainer('automatic',0);grant.acquisition={kind='skillGrant'}
          sourceRecord('blacksmithing',2671,{grant,itemPath('book',5577)})
          r=E.FindRecipe('blacksmithing',2671);market(snap,5577,25,2)
          quote=E.FormulaFor(r,snap)
          assert(quote.automatic and quote.cost==0 and quote.id==nil)
          local rows,total=E.CollectFormulas({{recipe=r,spell=2671,count=3}},'blacksmithing',snap)
          assert(#rows==0 and total==0,'automatic learning added a book purchase')
        """)


class ShippedLearningAcquisitionTests(unittest.TestCase):
    def test_real_barbecued_buzzard_wing_uses_trainer_while_bound_book_is_disabled(self):
        lua = production_runtime()
        lua.execute("""
          local E=ns.ProfEconomy;local r=E.FindRecipe('cooking',4094)
          local trainer,book
          for _,route in ipairs(r.learningInfo.routes)do
            if route.kind=='trainer' then trainer=route end
            if route.teachingItemID==4609 then book=route end
          end
          assert(trainer and trainer.trainingCost==500)
          assert(book and book.acquisition.nonAuctionable==true)
          local snap={known={},professions={cooking={cur=300,max=300}},
            specializationAbilities={},classID=4,raceID=1,level=60,faction='A',
            prices={},formulaOffers={},offers={},nonAuctionable={},ownedTeachingItems={},
            completedQuests={},reputations={}}
          local ok,reason,detail=E.RouteRecipeEligibility(r,snap)
          assert(ok,tostring(reason))
          assert(detail.quote.source=='trainer' and detail.quote.id==nil and detail.quote.cost==500)
        """)

    def test_known_recipe_still_respects_an_explicit_incompatible_specialty(self):
        lua = production_runtime()
        lua.execute("""
          local E=ns.ProfEconomy;local r=E.FindRecipe('engineering',8895)
          local snap={known={[r.key]=true},professions={engineering={cur=300,max=300}},
            specializationAbilities={[20222]=false,[20219]=true}}
          local ok,reason=E.RouteRecipeEligibility(r,snap)
          assert(not ok and reason=='specializationRequired','known recipe bypassed incompatible specialty')
          snap.specializationAbilities={}
          local detail;ok,reason,detail=E.RouteRecipeEligibility(r,snap)
          assert(ok and detail.status=='learned','unknown specialty invalidated a known recipe')
        """)

    def test_real_engineering_and_three_leatherworking_specialties_still_gate_auction(self):
        lua = production_runtime()
        cases = (
            ('engineering', 8895, 7192, 20222, 20219),
            ('leatherworking', 19050, 15726, 10656, 10658),
            ('leatherworking', 19059, 15732, 10658, 10660),
            ('leatherworking', 19062, 15735, 10660, 10656),
        )
        for slug, spell, item, required, incompatible in cases:
            with self.subTest(slug=slug, spell=spell):
                lua.globals().test_slug = slug
                lua.globals().test_spell = spell
                lua.globals().test_item = item
                lua.globals().required_spec = required
                lua.globals().incompatible_spec = incompatible
                lua.execute("""
                  local E=ns.ProfEconomy;local r=E.FindRecipe(test_slug,test_spell)
                  assert(r and ns.ProfGates.RequiredAbility(test_spell)==required_spec)
                  local snap={known={},professions={[test_slug]={cur=300,max=300}},
                    specializationAbilities={[required_spec]=false,[incompatible_spec]=true},
                    classID=4,raceID=1,level=60,faction='A',stamp=1000,
                    prices={[test_item]=1},auctionSupply={[test_item]={quantity=5,observedAt=1000,
                      complete=true,ownerExcluded=true,source='client-auction-results'}},
                    formulaOffers={},offers={},nonAuctionable={},ownedTeachingItems={},
                    completedQuests={},reputations={}}
                  local ok,reason=E.RouteRecipeEligibility(r,snap)
                  assert(not ok and reason=='specializationRequired',tostring(reason))
                  snap.ownedTeachingItems[test_item]=1
                  ok,reason=E.RouteRecipeEligibility(r,snap)
                  assert(not ok and reason=='specializationRequired','owned book bypassed specialization')
                  snap.ownedTeachingItems={};snap.specializationAbilities[required_spec]=true
                  snap.specializationAbilities[incompatible_spec]=false
                  local detail;ok,reason,detail=E.RouteRecipeEligibility(r,snap)
                  assert(ok,tostring(reason));assert(detail.quote and detail.quote.usable)
                """)


if __name__ == '__main__':
    unittest.main()
