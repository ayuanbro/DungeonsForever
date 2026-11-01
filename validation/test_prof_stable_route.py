"""Stable leveling ranks actual green attempts before money, retaining dependencies."""
import unittest
import test_prof_route_plans as fixtures
import test_prof_ui_fusion as ui


class StableRouteTests(unittest.TestCase):
    def setUp(self):
        fixtures.NativeRoutePlansTests.setUp(self)
        self.lua.execute('''
          function stableFixture()
            local s=fixture();local green=s.recipes[1]
            green.yellow=1;green.green=1;green.grey=100
            local orange=ns.ProfEconomy.Copy(green)
            orange.spell=102;orange.item=12;orange.mats={{13,1}}
            orange.yellow=100;orange.green=200;orange.grey=300
            s.recipes[2]=orange;s.known['alchemy:102']=true
            s.prices={[11]=1,[13]=100};return s
          end
          function counts(result)
            local t={};for _,st in ipairs(result.executionSteps)do t[st[3]]=(t[st[3]] or 0)+st[4]end;return t
          end
          function solve(s,target,scheme)
            return ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=target,scheme=scheme or 'stable'})
          end
        ''')

    def test_prefers_costlier_orange_route_over_cheap_green(self):
        self.lua.execute('''
          local stable=solve(stableFixture(),3)
          local cheapest=solve(stableFixture(),3,'cheapest')
          assert(stable.targetReached and stable.scheme=='stable' and stable.greenLevelCrafts==0)
          assert(counts(stable)[102]==2 and not counts(stable)[101] and stable.total==200)
          assert(counts(cheapest)[101]>0 and cheapest.total<stable.total)
        ''')

    def test_green_bridge_is_allowed_then_switches_to_orange(self):
        self.lua.execute('''
          local s=stableFixture();s.recipes[2].learn=2
          local r=solve(s,3);local n=counts(r)
          assert(r.targetReached and n[101]==2 and n[102]==1 and r.greenLevelCrafts==2)
        ''')

    def test_all_green_fallback_and_current_material_model_are_preserved(self):
        self.lua.execute('''
          local s=stableFixture();s.recipes[2]=nil
          local r=solve(s,3);assert(r.targetReached and r.greenLevelCrafts>0)
          local n=counts(r)[101];assert(r.mats[1].count==n and r.total==n)
        ''')

    def test_required_green_material_crafts_are_not_banned_or_scored_as_leveling(self):
        self.lua.execute('''
          local s=stableFixture();s.recipes[2].mats={{10,2}}
          local r=solve(s,3);local n=counts(r)
          assert(r.targetReached and n[101]==2 and n[102]==1 and r.greenLevelCrafts==0)
          local producer=r.executionSteps[1]
          assert(producer.requiredOutputs[10]==2 and producer.allocations[1].count==2)
          assert(r.total==2 and r.mats[1].count==2)
        ''')

    def test_same_stability_compares_purchase_cost_and_does_not_chase_profit(self):
        self.lua.execute('''
          local s=stableFixture();s.recipes[1].yellow=100;s.recipes[1].green=200;s.recipes[1].grey=300
          s.prices[12]=10000;s.sellPrices={[10]=0,[12]=0}
          s.auctionSupply={[12]={quantity=100,observedAt=1000,complete=true,ownerExcluded=true,source='client-auction-results'}}
          local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=3,scheme='stable',
            recoveryEnabled=true,recoveryFeePercent=0})
          assert(r.targetReached and counts(r)[101]==2 and not counts(r)[102] and r.total==2)
        ''')

    def test_skeleton_reload_preserves_scheme_counts_and_green_warning(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()
            local s=stableFixture();s.recipes[2].learn=2;return ns.ProfEconomy.Index(s)
          end
          opts={start=1,target=3,scheme='stable'};original=finish('alchemy',opts)
        ''')
        self.load((fixtures.ROOT/'Core/ProfRoutePlans.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local restored=finish('alchemy',opts)
          assert(restored.fromSkeleton and restored.scheme=='stable')
          assert(restored.greenLevelCrafts==original.greenLevelCrafts and restored.total==original.total)
          local a,b=counts(original),counts(restored);assert(a[101]==b[101] and a[102]==b[102])
        ''')


class StableRouteUITests(unittest.TestCase):
    boot=ui.ProfessionUIFusionTests.boot
    def setUp(self):self.boot('zhCN')

    def test_scheme_is_selectable_scoped_and_does_not_use_old_strategy_shortcut(self):
        self.lua.execute('''
          local ra=ns.ProfRouteAuto;local found=false
          for _,name in ipairs(ra.SchemeOrder())do if name=='stable' then found=true end end
          assert(found and ra.SchemeLabel('stable')=='稳定升级')
          PD.SetRouteScheme('stable')
          assert(PD.SettingRaw('autoScheme','alchemy')=='stable')
          assert(PD.SettingRaw('autoScheme','enchanting')=='cheapest')
          local r=finish('alchemy',ra.OptionsFor('alchemy',1))
          assert(r.scheme=='stable' and r.greenLevelCrafts==0 and r.searchTermination~='strategy_complete')
        ''')


if __name__=='__main__':unittest.main()
