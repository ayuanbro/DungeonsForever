"""Poison guide parity with master 698b48d, independent of ordinary planning."""
import json
import subprocess
import unittest
from pathlib import Path

import audit_prof_vendor_routes as audit
import test_prof_first_aid_ui as ui

ROOT = Path(__file__).resolve().parents[1]
MASTER = '698b48d'


def source(path):
    return subprocess.check_output(['git', 'show', f'{MASTER}:{path}'], cwd=ROOT).decode('utf-8-sig')


def load(lua, code):
    lua.execute("assert(loadstring(...))('DungeonsForever',ns)", code)


def normalized(value):
    return json.loads(json.dumps(audit.plain(value)))


def runtime(locale='zhCN', master=False, auction=10000):
    lua = audit.runtime(locale)
    lua.globals().testAuction = auction
    lua.execute('''
      selected='poisons';currentSkill=100
      ns.ProfModule.ProfLearned=function()return {poisons={cur=currentSkill,max=300}}end
      ns.ProfModule.Setting=function()return false end
      ns.ProfModule.SettingRaw=function()return false end
      ns.ProfHost.DG.ItemName=function(id)return tostring(id),true end
      ns.AuctionBridge={DoImport=function(_,items)imported=items end}
      Auctionator.API.v1.GetAuctionPriceByItemID=function()return testAuction end
      ns.ProfRouteAuto.Invalidate()
    ''')
    if master:
        load(lua, source('Core/ProfRouteAuto.lua'))
    return lua


class PoisonMasterParityTests(unittest.TestCase):
    def test_poison_data_still_matches_master_in_all_locales(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            current = runtime(locale)
            old = runtime(locale)
            for name in ('Data_Professions.lua', 'Data_ProfRecipes.lua', 'Data_ProfLeveling.lua'):
                path = 'Core/Data/' + (locale + '/' if locale != 'zhCN' else '') + name
                load(old, source(path))
            expression = 'return {ns.ProfData.pro.poisons,ns.ProfRecipes.poisons,ns.ProfLeveling.poisons}'
            self.assertEqual(normalized(current.execute(expression)), normalized(old.execute(expression)), locale)

    def test_authored_steps_costs_and_all_eight_npc_materials_match_master(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            for auction in (None, 1, 10000):
                with self.subTest(locale=locale, auction=auction):
                    current, old = runtime(locale, auction=auction), runtime(locale, True, auction)
                    # Both execute the full native fixed guide; the oracle is
                    # the actual master implementation, not a copied formula.
                    actual = current.execute("return ns.ProfRouteAuto.FixedPlan('poisons',{target=300,recoveryEnabled=false,considerAuctionSupply=true})")
                    expected = old.execute("return ns.ProfRouteAuto.SummarizeSteps(ns.ProfLeveling.poisons.steps,'poisons',{target=300,recoveryEnabled=false})")
                    for field in ('total', 'matTotal', 'vendorTotal', 'ahTotal', 'crafts', 'productAH', 'productNPC', 'productPartial'):
                        self.assertEqual(actual[field], expected[field], field)
                    def shopping(plan):
                        return [(r[1], r[2], r['cost'], r['unit'], r['vendor'], bool(r['unpriced'])) for r in plan['mats'].values()]
                    self.assertEqual(shopping(actual), shopping(expected))
                    self.assertEqual(len(actual['steps']), 13)
                    self.assertEqual(actual['crafts'], 200)
                    self.assertEqual(len(actual['mats']), 8)
                    self.assertTrue(all(r['vendor'] for r in actual['mats'].values()))
                    self.assertIsNone(actual['clientPending'])
                    self.assertIsNone(actual['learningPolicyFingerprint'])
                    self.assertIsNone(actual['supplyComplete'])

    def test_facade_ignores_old_automatic_plans_and_live_learning_gates(self):
        lua = runtime()
        lua.execute('''
          local old={mode='auto',learningPolicyFingerprint='old',steps={{1,300,999,999}}}
          ns.ProfExecution.GetPlan=function()return old end
          ns.ProfEconomy.RouteRecipeEligibility=function()error('poison guide used generic learning gates')end
          ns.ProfEconomy.Normalize=function()error('poison guide normalized native recipes')end
          ns.ProfRouteSolver.Compute=function()error('poison guide started a solver')end
          for _,fn in ipairs({'Get','Compute','Recalculate'})do
            local p=ns.ProfRouteAuto[fn]('poisons',{scheme='cheapest',target=300,recoveryEnabled=false})
            assert(p.mode=='fixed' and p.legacyPoisonGuide and #p.steps==13 and p.ahTotal==0,fn)
          end
          assert(not ns.ProfRouteAuto.HasWork('poisons'))
          assert(ns.ProfExecution.GetPlan('poisons')==old,'old history was changed')
          local p=ns.ProfRouteAuto.FixedPlan('poisons',{target=125,recoveryEnabled=false})
          assert(#p.steps==2 and p.steps[1][4]==25 and p.steps[2][4]==1 and p.clipped)
        ''')

    def test_recipe_route_and_shopping_ui_use_master_poison_records(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            fixture = ui.FirstAidUITests()
            fixture.boot(locale, missing=False)
            lua = fixture.lua
            lua.execute('''
              PD.cur='poisons';PD.ProfLearned=function()return {poisons={cur=100,max=300}}end
              ns.ProfHost.DG.ItemIcon=function()return 134400 end
              ns.EnsureProfSources=function()return {}end
              ns.ProfEconomy.ResolveRecipe=function()error('poison UI used live normalization')end
              ns.ProfEconomy.Normalize=function()error('poison UI used generic normalization')end
              ns.ProfEconomy.RouteRecipeEligibility=function()error('poison UI used generic learning')end
              ns.ProfRecipeRuntime={[8681]={clientUnavailable=true,item=999,count=999,mats={{999,999}}}}
              PD.tab='recipe';local rows={};PD.RowsRecipe(rows)
              local found=0
              for _,r in ipairs(rows)do if r.row then
                found=found+1;assert(r.row[2]~=999 and r._mats[1][1]~=999)
                assert(r.right2==ns.L['训练师'])
                r.tipExtra()
              end end
              assert(found==26,'poison recipes were filtered by new policies')
              PD.tab='leveling';PD.autoPage=nil;rows={};PD.RowsLeveling(rows)
              local steps=0;for _,r in ipairs(rows)do if r.lvstep then steps=steps+1 end end
              assert(steps==13 and not PD.lvSummary.clientPending)
              PD.autoPage='shop';rows={};PD.RowsLeveling(rows)
              local count=0;for _,r in ipairs(rows)do if r.tag and r.it then
                assert(r.tag.text==ns.L['NPC购买']);count=count+1
              end end
              assert(count==8 and PD.lvShopData.ahTotal==0)
            ''')

    def test_hud_remaining_materials_match_master_without_binding_execution(self):
        for skill in (100, 129, 216, 299):
            current, old = runtime(), runtime(master=True)
            load(old, source('Core/ProfFollow.lua'))
            for lua in (current, old):
                lua.globals().currentSkill = skill
                lua.execute('''
                  local pf=ns.ProfFollow;pf.Build=function()end;pf.Paint=function()end
                  ns.ProfExecution.GetRun=function()error('poison HUD used an execution')end
                  ns.ProfExecution.GetPlan=function()error('poison HUD used a frozen plan')end
                  ns.ProfExecution.Bind=function()error('poison HUD bound an execution')end
                  pf.Toggle('poisons');pf.Sync()
                ''')
            # The public current-step deficit uses master skill progression and
            # raw recipe quantities, including the deliberately fixed ranges.
            actual = normalized(current.execute("return ns.ProfFollow.SupplementNeeds('poisons')"))
            expected = normalized(old.execute("return ns.ProfFollow.SupplementNeeds('poisons')"))
            if actual:
                actual.pop('basis', None)
            self.assertEqual(actual, expected, skill)
            current.execute('''
              assert(not ns.ProfFollow.LearningWarning('poisons'))
              ns.ProfFollow.ImportShoppingList('poisons','Poisons')
              assert(imported and #imported>0,'master exports the remaining guide materials')
            ''')


if __name__ == '__main__':
    unittest.main()
