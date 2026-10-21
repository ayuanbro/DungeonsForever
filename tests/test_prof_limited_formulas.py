"""Limited formula merchants are opt-in; auction and learned paths stay usable."""
import unittest

from test_prof_runtime import LuaRuntime, MOCKS, ROOT


class LimitedFormulaPolicyTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.load = self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        for name in ('ProfEconomy.lua', 'ProfRouteSolver.lua', 'ProfFishing.lua', 'ProfRouteAuto.lua'):
            self.load(str(ROOT / 'Core' / name))
        self.lua.execute(r'''
          function recipe(spell,item,material,formula)
            return {profession='alchemy',key='alchemy:'..spell,spell=spell,item=item,count=1,
              learn=1,yellow=20,green=20,grey=20,mats={{material,1}},formula=formula,cooldown=false}
          end
          function limitedSnapshot()
            return {recipes={recipe(101,20,11,99),recipe(102,21,12)},known={},
              prices={[11]=1,[12]=10},professions={alchemy={cur=1,max=75}},
              formulaOffers={[99]={{price=2,quantity=1,npcID=7,limited=true,unlimited=false,maxStock=1,stock=1}}}}
          end
          function solveLimited(s,extra)
            local opts=extra or {};opts.snapshot=s;opts.start=1;opts.target=2
            local r,j=ns.ProfRouteSolver.Compute('alchemy',opts)
            assert(not j.error,tostring(j.error));return r
          end
          function liveLimited()
            ns.ProfEconomy.Professions=function()return {alchemy={cur=1,max=75}}end
            ns.ProfEconomy.Known=function()return false end
            ns.ProfRecipes={alchemy={rows={
              {101,20,1,'','','',1,20,20,20,false,{{11,1}},{99},{}},
              {102,21,1,'','','',1,20,20,20,false,{{12,1}},nil,{}}}}}
            ns.EnsureProfRecipes=function()return ns.ProfRecipes end
            ns.ProfRouteAuto.AHPriceOf=function(id)return ({[11]=1,[12]=10})[id]end
            ns.ProfItemPrices={GetFormulaOffers=function(id)
              return id==99 and limitedSnapshot().formulaOffers[99] or {} end}
            Auctionator={API={v1={GetAuctionPriceByItemID=function(_,id)return ({[11]=1,[12]=10})[id]end}}}
          end
        ''')

    def test_default_off_rejects_unpriced_limited_formula_and_chooses_alternative(self):
        self.lua.execute(r'''
          local s=limitedSnapshot();local r=solveLimited(s)
          assert(r.targetReached and r.steps[1][3]==102 and #r.formulas==0 and r.total==10)
          local f=ns.ProfEconomy.FormulaFor(s.recipes[1],s)
          assert(not f.usable and f.reason=='limitedFormulaDisabled' and f.vendorPrice==2)
          assert(not ns.ProfEconomy.AllowLimitedFormulas())
        ''')

    def test_explicit_opt_in_allows_limited_vendor_without_inventing_current_stock(self):
        self.lua.execute(r'''
          local s=limitedSnapshot();s.recipes={s.recipes[1]};s.formulaOffers[99][1].stock=nil
          local r=solveLimited(s,{allowLimitedFormulas=true})
          assert(r.targetReached and r.steps[1][3]==101 and r.total==3)
          assert(r.formulas[1].source=='vendor' and r.formulas[1].availabilityUncertain)
          assert(not r.completeCost and not r.optimal)
        ''')

    def test_auction_price_allows_unknown_or_positive_quantity_but_not_observed_zero(self):
        self.lua.execute(r'''
          local s=limitedSnapshot();s.prices[99]=4
          for _,quantity in ipairs({-1,0,1})do
            s.auctionSupply=quantity>=0 and {[99]={quantity=quantity,source='legacy',complete=true}} or {}
            local r=solveLimited(s)
            if quantity==0 then assert(r.steps[1][3]==102 and #r.formulas==0)
            else assert(r.steps[1][3]==101 and r.total==5 and r.formulas[1].source=='ah')end
          end
        ''')

    def test_unlimited_seller_remains_eligible_when_another_seller_is_limited(self):
        self.lua.execute(r'''
          local s=limitedSnapshot()
          s.formulaOffers[99][2]={price=4,quantity=1,npcID=8,unlimited=true}
          local r=solveLimited(s)
          assert(r.total==5 and r.formulas[1].source=='vendor' and r.formulas[1].npcID==8)
        ''')

    def test_missing_stock_is_not_misclassified_as_a_known_limited_seller(self):
        self.lua.execute(r'''
          local e=ns.ProfEconomy;local s=limitedSnapshot()
          s.formulaOffers[99]={{price=2,quantity=1,npcID=7,unlimited=false,stockUnknown=true,stockStatus='unknown'}}
          local f=e.FormulaFor(s.recipes[1],s)
          assert(f.usable and f.stockUnknown and not f.limited and not f.limitedVendorDisabled)
          for _,evidence in ipairs({{unlimited=false},{limited=true},{stockStatus='limited'},{stock=1},{maxStock=2}})do
            assert(e.LimitedFormulaOffer(evidence))
          end
        ''')

    def test_known_and_explicit_trainer_recipes_do_not_require_formula_purchase(self):
        self.lua.execute(r'''
          local s=limitedSnapshot();s.known['alchemy:101']=true
          local r=solveLimited(s);assert(r.total==1 and #r.formulas==0)
          s.known={};s.recipes[1].learnSource='trainer'
          r=solveLimited(s);assert(r.total==1 and #r.formulas==0)
        ''')

    def test_recursive_material_production_obeys_the_same_formula_policy(self):
        self.lua.execute(r'''
          local s=limitedSnapshot();s.recipes[1].item=10;s.recipes[1].grey=1
          s.recipes[1].yellow=1;s.recipes[1].green=1
          s.recipes[2].mats={{10,1}};s.prices[10]=10
          local off=solveLimited(s)
          assert(off.total==10 and #off.formulas==0)
          local on=solveLimited(s,{allowLimitedFormulas=true})
          assert(on.total==3 and on.formulas[1].source=='vendor')
        ''')

    def test_capture_freezes_setting_and_explicit_false_overrides_saved_true(self):
        self.lua.execute(r'''
          DungeonsForeverDB={prof={autoBuyLimitedFormulas=true}}
          local e=ns.ProfEconomy;local s=limitedSnapshot()
          local frozen=e.Capture('alchemy',{snapshot=s,allowLimitedFormulas=false})
          assert(frozen.allowLimitedFormulas==false)
          assert(not e.FormulaFor(frozen.recipes[1],frozen).usable)
          assert(e.Capture('alchemy',{snapshot=s}).allowLimitedFormulas==true)
          assert(ns.ProfRouteAuto.OptionsFor('alchemy').allowLimitedFormulas==true)
        ''')

    def test_all_reference_scoring_modes_use_explicit_option(self):
        self.lua.execute(r'''
          liveLimited()
          for _,scheme in ipairs({'matcost','crafts','optim'})do
            local ra=ns.ProfRouteAuto
            local off=ra.Compute('alchemy',{start=1,target=2,scheme=scheme,allowLimitedFormulas=false})
            assert(off.steps[1][3]==102 and #off.formulas==0,scheme)
            local on=ra.Compute('alchemy',{start=1,target=2,scheme=scheme,allowLimitedFormulas=true})
            assert(on.steps[1][3]==101 and on.formulas[1].source=='vendor',scheme)
            assert(on.formulaPolicy.allowLimited==true)
          end
        ''')

    def test_fixed_reference_retains_unavailable_formula_without_budgeting_npc_purchase(self):
        self.lua.execute(r'''
          liveLimited();local ra=ns.ProfRouteAuto
          local off=ra.SummarizeSteps({{1,2,101,1}},'alchemy',{allowLimitedFormulas=false})
          assert(off.formulas[1].blocked and off.formulas[1].reason=='limitedFormulaDisabled')
          assert(off.formulaVendorTotal==0 and not off.completeCost)
          local on=ra.SummarizeSteps({{1,2,101,1}},'alchemy',{allowLimitedFormulas=true})
          assert(on.formulaVendorTotal==2 and on.formulas[1].source=='vendor')
          assert(ra.ValidateVendorQuotes(on,{allowLimitedFormulas=true})==on)
          assert(ra.ValidateVendorQuotes(on,{allowLimitedFormulas=false}).status=='recalculate_required')
        ''')

    def test_fishing_snapshot_uses_the_same_formula_source_gate(self):
        self.lua.execute(r'''
          ns.ProfFishingRoutes={fish={[50]={areas={{skill=1,rate=1}}}},cookingSteps={{from=1,to=2,spell=101}}}
          local s=limitedSnapshot();s.recipes={s.recipes[1]}
          local r=s.recipes[1];r.profession='cooking';r.key='cooking:101';r.mats={{50,1}}
          s.professions={cooking={cur=1,max=75},fishing={cur=75,max=75}}
          local p=ns.ProfFishing
          local off=p.Compute({snapshot=s,start=1,target=2,allowLimitedFormulas=false})
          assert(not off.targetReached and #off.steps==0)
          local on=p.Compute({snapshot=s,start=1,target=2,allowLimitedFormulas=true})
          assert(on.targetReached and on.formulaVendorTotal==2)
        ''')

    def test_policy_change_and_legacy_cache_require_manual_recalculation(self):
        self.lua.execute(r'''
          liveLimited();DungeonsForeverDB={prof={autoBuyLimitedFormulas=true}}
          local ra=ns.ProfRouteAuto
          local original=finish('alchemy',{start=1,target=2})
          assert(original.formulas[1].source=='vendor')
          local queued=#queue
          DungeonsForeverDB.prof.autoBuyLimitedFormulas=false
          local gate=ra.Get('alchemy',{start=1,target=2})
          assert(gate.status=='recalculate_required' and #gate.steps==0 and #queue==queued)
          assert(original.formulas[1].source=='vendor','historical plan was mutated')
          original.formulaPolicy=nil
          local old=ra.ValidateVendorQuotes(original)
          assert(old.status=='recalculate_required' and #old.formulas==0)
        ''')

    def test_reload_keeps_policy_block_without_replacing_saved_result(self):
        self.lua.execute(r'''
          liveLimited();DungeonsForeverDB={prof={autoBuyLimitedFormulas=true}}
          local r=finish('alchemy',{start=1,target=2})
          local cache=DungeonsForeverDB.prof.routeCache['Test-Realm']
          savedResult=cache.routes[cache.active.alchemy].result
          DungeonsForeverDB.prof.autoBuyLimitedFormulas=false
          queuedBefore=#queue
        ''')
        self.load(str(ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute(r'''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
          assert(r.status=='recalculate_required' and #queue==queuedBefore)
          assert(savedResult.formulas[1].source=='vendor' and savedResult.formulaPolicy.allowLimited)
        ''')

    def test_changed_setting_cancels_queued_old_job_and_keeps_manual_gate(self):
        self.lua.execute(r'''
          liveLimited();DungeonsForeverDB={prof={autoBuyLimitedFormulas=true}}
          local ra=ns.ProfRouteAuto
          assert(ra.Get('alchemy',{start=1,target=2}).status=='searching')
          local oldPump=queue[1]
          DungeonsForeverDB.prof.autoBuyLimitedFormulas=false
          local gate=ra.Get('alchemy',{start=1,target=2})
          assert(gate.status=='recalculate_required' and #queue==1)
          assert(oldPump()==true)
          assert(ra.Get('alchemy',{start=1,target=2}).status=='recalculate_required' and #queue==1)
        ''')


if __name__ == '__main__':
    unittest.main()
