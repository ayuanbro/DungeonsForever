"""Exercise profession-scoped settings and First Aid's fixed-only entry points."""
import unittest

import test_prof_ui_fusion as ui_fixture


class ScopedSettingsFixedTests(unittest.TestCase):
    def setUp(self):
        ui_fixture.ProfessionUIFusionTests.boot(self, 'zhCN')

    def test_mode_scheme_and_purchase_options_do_not_change_other_professions(self):
        self.lua.execute('''
          local db=DungeonsForeverDB.prof
          db.autoScheme='cheapest';db.recoveryEnabled=false;db.autoAllowBindOnPickupFormulas=false
          PD.cur='alchemy'
          PD.SetSettingRaw('autoRoute',false)
          PD.SetSettingRaw('autoAllowBindOnPickupFormulas',true)
          PD.SetSettingRaw('autoBuyLimitedFormulas',true)
          PD.SetSettingRaw('autoCraftTools',false)
          PD.SetSettingRaw('autoFromCurrent',false)
          local calls={}
          ns.ProfRouteAuto.Recalculate=function(slug,opts)calls[#calls+1]={slug,opts}end
          PD.SetRouteScheme('crafts');PD.SetRecoveryEnabled(true);PD.SetRecoveryFee(8)
          assert(db.autoRoute==true and db.autoScheme=='cheapest' and db.recoveryEnabled==false)
          assert(PD.Setting('autoRoute','enchanting') and PD.SettingRaw('autoScheme','enchanting')=='cheapest')
          assert(not PD.Setting('autoAllowBindOnPickupFormulas','enchanting') and not PD.Setting('autoBuyLimitedFormulas','enchanting'))
          assert(PD.Setting('autoAllowBindOnPickupFormulas','alchemy'))
          assert(PD.Setting('autoCraftTools','enchanting') and PD.Setting('autoFromCurrent','enchanting'))
          assert(not PD.Setting('recoveryEnabled','enchanting') and PD.SettingRaw('recoveryFeePercent','enchanting')==5)
          PD.cur='enchanting'
          assert(not PD.Setting('autoRoute','alchemy') and PD.SettingRaw('autoScheme','alchemy')=='crafts')
          assert(PD.Setting('recoveryEnabled','alchemy') and PD.SettingRaw('recoveryFeePercent','alchemy')==8)
          for _,call in ipairs(calls)do assert(call[1]=='alchemy')end
        ''')

    def test_background_options_use_requested_profession_instead_of_visible_profession(self):
        self.lua.execute('''
          PD.cur='enchanting'
          DungeonsForeverDB.prof.lvTarget.enchanting=225
          PD.SetSettingRaw('autoScheme','crafts','alchemy')
          PD.SetSettingRaw('autoOnlyAH',false,'alchemy')
          PD.SetSettingRaw('autoAllowBindOnPickupFormulas',true,'alchemy')
          PD.SetSettingRaw('autoAllowCurrencyFormulas',true,'alchemy')
          PD.SetSettingRaw('recoveryFeePercent',9,'alchemy')
          PD.SetSettingRaw('autoBuyLimitedFormulas',true,'alchemy')
          local opts=PD.BuildLvOpts('alchemy',2)
          assert(opts.scheme=='crafts' and opts.target==3 and opts.start==2)
          assert(not opts.onlyAH and opts.noFormula==nil and opts.recoveryFeePercent==9)
          assert(opts.allowBindOnPickupFormulas and opts.allowCurrencyFormulas)
          assert(opts.allowLimitedFormulas)
          local other=PD.BuildLvOpts('enchanting',10)
          assert(other.scheme=='cheapest' and other.target==225 and other.start==10)
          assert(other.onlyAH and other.noFormula==nil and not other.allowLimitedFormulas)
          assert(not other.allowBindOnPickupFormulas and not other.allowCurrencyFormulas)
        ''')

    def test_first_aid_never_starts_a_solver_despite_legacy_automatic_settings(self):
        self.lua.execute('''
          PD.cur='first-aid'
          DungeonsForeverDB.prof.autoRoute=true;DungeonsForeverDB.prof.autoScheme='cheapest'
          ns.ProfRouteSolver.NewJob=function()error('First Aid must not start a search')end
          ns.ProfRouteSolver.Compute=function()error('First Aid must not compute a route')end
          assert(not PD.Setting('autoRoute') and PD.SettingRaw('autoScheme')=='fixed')
          PD.SetSettingRaw('autoRoute',true);PD.SetRouteScheme('crafts')
          assert(not PD.Setting('autoRoute') and PD.SettingRaw('autoScheme')=='fixed')
          local ra=ns.ProfRouteAuto
          for _,method in ipairs({'Get','Compute','Recalculate'})do
            local result=assert(ra[method]('first-aid',{target=3}))
            assert(result.mode=='fixed' and result.scheme=='fixed' and #result.steps==1)
          end
          PD.RowsLeveling({});assert(PD.autoSnapshot.mode=='fixed')
          assert(not PD.lvSummary.auto and not ra.HasWork('first-aid') and not PD.RecalcNeeded())
          local buttons=PD.LevelTool()
          for _,button in ipairs(buttons)do assert(button.key~='recalc')end
        ''')

    def test_other_profession_edits_do_not_mark_an_unchanged_result_stale(self):
        self.lua.execute('''
          local opts=PD.BuildLvOpts('alchemy',1)
          local original=finish('alchemy',opts)
          assert(not original.stale)
          PD.cur='enchanting'
          PD.SetSettingRaw('autoScheme','crafts')
          PD.SetSettingRaw('recoveryEnabled',true)
          PD.SetSettingRaw('recoveryFeePercent',10)
          PD.SetSettingRaw('autoBuyLimitedFormulas',true)
          local same=ns.ProfRouteAuto.Get('alchemy',PD.BuildLvOpts('alchemy',1))
          assert(same==original and not same.stale and not same.settingsChanged)
        ''')

    def test_fixed_summary_copies_authored_rows_and_clips_quantity(self):
        self.lua.execute('''
          local raw=ns.ProfLeveling.alchemy.steps[1]
          local sum=assert(ns.ProfRouteAuto.FixedPlan('alchemy',{target=2,recoveryEnabled=false}))
          assert(sum.mode=='fixed' and sum.clipped and #sum.steps==1)
          assert(sum.steps[1]~=raw and sum.steps[1][2]==2 and sum.steps[1][4]==1)
          assert(raw[2]==3 and raw[4]==2 and raw.cost==nil and raw.mats==nil)
          local empty=assert(ns.ProfRouteAuto.FixedPlan('alchemy',{target=1}))
          assert(#empty.steps==0 and #empty.mats==0)
        ''')

    def test_fixed_npc_purchase_defaults_to_full_packs_without_optional_optimization(self):
        self.lua.execute('''
          ns.ProfLeveling.alchemy.sold={11}
          ns.VendorPriceDB={GetPrice=function(id)if id==11 then return 2 end end,
            GetOffers=function(id)if id==11 then return {{npcID=1,price=10,unit=2,
              quantity=5,unlimited=true,purchasable=true}}end return {}end}
          ns.ProfRouteAuto.Invalidate()
          local sum=ns.ProfRouteAuto.FixedPlan('alchemy',{target=3,recoveryEnabled=false})
          assert(#sum.mats==1 and sum.mats[1][1]==11 and sum.mats[1][2]==5)
          assert(sum.mats[1].need==2 and sum.mats[1].bundleSize==5)
          assert(sum.mats[1].source=='vendor' and sum.mats[1].npcID==1)
          assert(sum.total==10 and sum.vendorTotal==10 and sum.ahTotal==0)
          ns.ProfRecipes.alchemy.rows[1][13]={400}
          ns.ProfEconomy.FormulaFor=function(recipe,context)
            assert(context.profession=='alchemy' and context.noFormula==nil)
            return {id=400,spell=101,cost=50,source='vendor',costComplete=true,usable=true}
          end
          local withPattern=ns.ProfRouteAuto.FixedPlan('alchemy',{target=3,recoveryEnabled=false})
          assert(withPattern.total==60 and withPattern.formulasTotal==50)
          assert(withPattern.vendorTotal==60 and withPattern.ahTotal==0)
        ''')


if __name__=='__main__':
    unittest.main()
