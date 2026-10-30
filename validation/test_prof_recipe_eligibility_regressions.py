"""Native pattern eligibility, completed introductions and captured policies."""
import unittest
from test_prof_native_data import native_runtime


class RecipeEligibilityRegressions(unittest.TestCase):
    def setUp(self):
        self.lua=native_runtime()

    def test_a_stale_roster_does_not_hide_a_positively_known_recipe(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          E.EnsureClientRuntime();observedKnown[7183]=true
          E.ClientStore().recipeRosters={alchemy={complete=true,ids={[2334]=true}}}
          local recipe=E.FindRecipe('alchemy',7183)
          assert(not recipe.clientUnavailable)
          local r=ns.ProfRouteSolver.Compute('alchemy',{start=1,target=2,learnedOnly=true,
            autoCraftTools=false,recoveryEnabled=false,noFormula=true})
          assert(r.targetReached and r.steps[1][3]==7183)
          observedKnown[7183]=nil
          assert(E.FindRecipe('alchemy',7183).clientUnavailable,
            'an unlearned recipe absent from a complete roster was revived')
        ''')

    def test_explicit_client_unavailability_remains_a_block(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          E.EnsureClientRuntime();observedKnown[7183]=true
          ns.ProfRecipeRuntime[7183]={available=false,validated=true}
          assert(E.FindRecipe('alchemy',7183).clientUnavailable)
          local r=ns.ProfRouteSolver.Compute('alchemy',{start=1,target=2,learnedOnly=true,
            autoCraftTools=false,recoveryEnabled=false,noFormula=true})
          assert(not r.targetReached)
        ''')

    def test_real_drop_and_limited_patterns_obey_each_explicit_policy(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local drop=E.FindRecipe('alchemy',3230)
          assert(drop.formula==2553)
          local snap=E.Capture('alchemy',{start=1,target=300,autoCraftTools=false,
            noFormula=true,allowLimitedFormulas=false,recoveryEnabled=false})
          snap.auctionSupply[2553]={quantity=2,observedAt=snap.stamp-1,complete=true,
            ownerExcluded=true,source='client-auction-results'}
          local f=E.FormulaFor(drop,snap)
          assert(f.usable and f.source=='ah','retired vendor-only policy still blocks priced tradable drops')
          snap.noFormula=false;f=E.FormulaFor(drop,snap)
          assert(f.usable and f.source=='ah')
          snap.noFormula=true
          local limited=E.FindRecipe('alchemy',6617)
          assert(limited.formula==5640)
          snap.prices[5640]=nil
          f=E.FormulaFor(limited,snap)
          assert(not f.usable and f.reason=='limitedFormulaDisabled')
          snap.allowLimitedFormulas=true;f=E.FormulaFor(limited,snap)
          assert(f.usable and f.source=='vendor' and f.limited and f.cost>0)
          snap.allowLimitedFormulas=false;snap.known[limited.key]=true
          f=E.FormulaFor(limited,snap)
          assert(f.known and f.usable and f.cost==0,
            'known recipes were still required to buy their pattern')
        ''')

    def test_each_crafting_profession_keeps_verified_vendor_patterns(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          for _,slug in ipairs({'alchemy','blacksmithing','enchanting','engineering',
            'leatherworking','tailoring','cooking'})do
            selected=slug
            ns.ProfModule.ProfLearned=function()return {[selected]={cur=1,max=300}}end
            local snap=E.Capture(slug,{start=1,target=300,noFormula=true,
              allowLimitedFormulas=false,autoCraftTools=false,recoveryEnabled=false})
            local state={skill={[slug]=300},learned={},specializationAbilities=snap.specializationAbilities}
            local found
            for _,recipe in ipairs(snap.recipes)do
              local allowed=E.RouteRecipeEligibility(recipe,snap,state)
              local f=E.FormulaFor(recipe,snap)
              if allowed and f and f.usable and f.source=='vendor' and f.unlimited then
                found=recipe
                assert(f.npcID and f.cost>0 and f.vendorOffers[1],slug)
                break
              end
            end
            assert(found,'all verified vendor patterns disappeared from '..slug)
            snap.known[found.key]=true;snap.formulaOffers={};snap.prices={}
            local known=E.FormulaFor(found,snap)
            assert(known.known and known.usable and known.cost==0,slug)
          end
        ''')

    def test_completed_intro_does_not_infer_a_specialization_or_block_ordinary_leveling(self):
        self.lua.execute('''
          selected='engineering';DungeonsForeverDB.prof.engChoice='gnomish'
          local G,E=ns.ProfGates,ns.ProfEconomy
          local opts={profession='engineering',target=300,faction='A',level=60}
          local initial=G.SpecializationContext(opts);local quest=initial.goals[1].questID
          assert(quest and quest>0)
          C_QuestLog={IsQuestFlaggedCompleted=function(id)return id==quest end}
          local context=G.SpecializationContext(opts)
          assert(#context.goals==0 and #context.unresolvedGoals==1 and #context.warnings==1)
          assert(context.warnings[1].code=='specializationQuestAlreadyCompleted')
          assert(context.abilities[20219]==false and G.SpecGoal('engineering',300)==nil)
          local snap=E.Capture('engineering',{start=200,target=300,autoCraftTools=false,
            engineeringSpecialization='gnomish',recoveryEnabled=false})
          assert(#snap.specializationGoals==0)
          local specialized
          for _,recipe in ipairs(snap.recipes)do
            if G.RequiredAbility(recipe.spell)==20219 then specialized=recipe;break end
          end
          assert(specialized)
          local allowed,reason=E.RouteRecipeEligibility(specialized,snap,
            {skill={engineering=300},learned={},specializationAbilities=snap.specializationAbilities})
          assert(not allowed and reason=='specializationRequired')
        ''')

    def test_uncompleted_intro_keeps_its_real_qualification_requirements(self):
        self.lua.execute('''
          DungeonsForeverDB.prof.engChoice='gnomish'
          C_QuestLog={IsQuestFlaggedCompleted=function()return false end}
          local context=ns.ProfGates.SpecializationContext({profession='engineering',target=300,
            faction='A',level=20})
          assert(#context.goals==1 and context.goals[1].blockedReason=='specializationLevelRequired')
          assert(not context.unresolvedGoals and not context.warnings)
        ''')

    def test_capture_reads_the_requested_professions_settings_without_mutating_options(self):
        self.lua.execute('''
          local E,G=ns.ProfEconomy,ns.ProfGates
          ns.ProfModule.cur='tailoring'
          ns.ProfModule.SettingRaw=function(key,slug)
            assert(slug,'capture used the currently selected UI profession')
            if key=='autoCraftTools' or key=='autoBuyLimitedFormulas' then return slug=='engineering' end
          end
          local opts={start=1,target=2,recoveryEnabled=false}
          local alchemy=E.Capture('alchemy',opts)
          assert(not alchemy.allowLimitedFormulas and not alchemy.autoCraftTools)
          local engineering=E.Capture('engineering',opts)
          assert(engineering.allowLimitedFormulas and engineering.autoCraftTools)
          assert(opts.profession==nil and opts.autoCraftTools==nil)
          assert(G.AutoCraftTools('engineering') and not G.AutoCraftTools('alchemy'))
          assert(E.ToolPlanningEnabled(nil,'engineering') and not E.ToolPlanningEnabled(nil,'alchemy'))
        ''')

    
    def test_single_auction_pattern_is_eligible(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local recipe=E.FindRecipe('alchemy',3230)
          assert(recipe.formula==2553)

          local snap=E.Capture('alchemy',{
            start=1,target=300,
            autoCraftTools=false,
            allowLimitedFormulas=false,
            recoveryEnabled=false
          })

          local item=2553
          snap.auctionSupply[item]={
            quantity=1,
            observedAt=snap.stamp-1,
            complete=true,
            ownerExcluded=true,
            source='client-auction-results'
          }

          -- 1 张有效现货，应允许购买
          local one=E.FormulaFor(recipe,snap)
          assert(one and one.usable and one.source=='ah'
            and one.cost>0,
            'one auction copy must be usable')

          -- 0 张现货，不得从拍卖行购买
          snap.auctionSupply[item].quantity=0
          local zero=E.FormulaFor(recipe,snap)
          assert(not zero or not (zero.usable and zero.source=='ah'),
            'zero auction stock must be rejected')

          -- 库存未知，不能假定有现货
          snap.auctionSupply[item]=nil
          local unknown=E.FormulaFor(recipe,snap)
          assert(not unknown or not (unknown.usable and unknown.source=='ah'),
            'unknown stock must not be treated as available')
        ''')


    def test_formula_auction_supply_uses_price_ttl(self):
        self.lua.execute('''
          local E = ns.ProfEconomy
          local observed = 1000
          local snap = {
            prices = {[2553] = 100},
            auctionSupply = {
              [2553] = {
                quantity = 1,
                observedAt = observed,
                expiresAt = observed + 1800,
                source = "client-auction-results",
                complete = true,
                ownerExcluded = true
              }
            }
          }

          snap.stamp = observed + 47 * 3600
          assert(E.FormulaAuctionSupplyOf(snap, 2553))

          snap.stamp = observed + 48 * 3600
          assert(E.FormulaAuctionSupplyOf(snap, 2553))

          snap.stamp = observed + 48 * 3600 + 1
          assert(not E.FormulaAuctionSupplyOf(snap, 2553))
        ''')


if __name__=='__main__':unittest.main()
