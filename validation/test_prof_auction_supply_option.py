"""Optional auction quantity limits across routes, saved settings and shopping."""
import unittest

import test_prof_route_plans as routes
import test_prof_ui_fusion as ui
import test_prof_issue4 as hud
import test_prof_audit_special as fishing


class AuctionSupplyOptionRoutes(unittest.TestCase):
    def setUp(self):
        routes.NativeRoutePlansTests.setUp(self)
        self.lua.execute('''
          local stockFixture=fixture
          fixture=function()local s=stockFixture();s.considerAuctionSupply=nil;return s end
        ''')

    def test_default_ignores_zero_finite_and_unknown_stock_for_all_strategies(self):
        self.lua.execute('''
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim'})do
            for _,stock in ipairs({{}, {[11]={quantity=0}}, {[11]={quantity=1}}})do
              local s=fixture();s.auctionSupply=stock
              local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=4,scheme=scheme})
              assert(r.targetReached and r.total==21,scheme)
              assert(r.considerAuctionSupply==false and not r.auctionSupplyUnknown)
              assert(#r.auctionSupplyShortages==0 and next(r.auctionSupplyInputs)==nil)
              assert(r.mats[1].considerAuctionSupply==false and not r.purchaseVerified)
            end
          end
        ''')

    def test_enabling_limits_stock_and_uses_a_more_expensive_alternative(self):
        self.lua.execute('''
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim'})do
            local s=fixture();s.auctionSupply={[11]={quantity=1},[12]={quantity=20}}
            local alt=ns.ProfEconomy.Copy(s.recipes[1]);alt.spell=102;alt.mats={{12,1}}
            s.recipes[2]=alt;s.prices[12]=10;s.known['alchemy:102']=true
            local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=4,
              scheme=scheme,considerAuctionSupply=true})
            assert(r.targetReached and r.total>=27 and r.supplyComplete and r.purchaseVerified)
            for _,m in ipairs(r.mats)do if m.id==11 then assert(m.count<=1)end end
            assert(s.auctionSupply[11].quantity==1,'source snapshot was mutated')
          end
        ''')

    def test_formula_stock_is_mandatory_and_shared_even_when_material_check_is_disabled(self):
        self.lua.execute('''
          local s=fixture();s.known={};s.recipes[1].formula=11
          s.stamp=1000;s.auctionSupply={[11]={quantity=2,observedAt=900,complete=true,
            ownerExcluded=true,source='client-auction-results'}}
          s.offers={[11]={{npcID=7,price=20,quantity=1,unlimited=true}}}
          for _,enabled in ipairs({false,true})do
            local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=3,
              noFormula=false,considerAuctionSupply=enabled})
            local used=0
            for _,a in ipairs(r.actions)do
              if (a.type=='buy' or a.type=='formula') and a.source=='ah' and a.item==11 then used=used+a.count end
            end
            assert(r.targetReached)
            assert(used<=2 and r.total>=34)
          end
        ''')

    def test_capture_freezes_setting_and_explicit_false_overrides_snapshot(self):
        self.lua.execute('''
          local e=ns.ProfEconomy;local enabled=true
          ns.ProfModule={SettingRaw=function(k,slug)
            if k=='autoConsiderAuctionSupply' then assert(slug=='alchemy');return enabled end
          end}
          local source=fixture();source.auctionSupply={[11]={quantity=0}}
          local s=e.Capture('alchemy',{snapshot=source,autoCraftTools=false})
          enabled=false
          assert(e.ConsiderAuctionSupply(s) and e.AuctionSupplyOf(s,11).quantity==0)
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=3,considerAuctionSupply=false})
          assert(r.targetReached and r.total==14 and s.considerAuctionSupply==true)
        ''')

    def test_direct_purchase_options_override_snapshot_policy(self):
        self.lua.execute('''
          local s={prices={[11]=7},auctionSupply={[11]={quantity=0}},considerAuctionSupply=true}
          local ra=ns.ProfRouteAuto
          local rows,total,complete=ra.MaterialPurchases(11,2,{snapshot=s,considerAuctionSupply=false})
          assert(complete and total==14 and rows[1].count==2)
          s.considerAuctionSupply=false
          rows,total,complete=ra.MaterialPurchases(11,2,{snapshot=s,considerAuctionSupply=true})
          assert(not complete and rows[1].availableCount==0)
        ''')

    def test_only_enabled_results_become_stale_after_quantity_changes(self):
        self.lua.execute('''
          local e=ns.ProfEconomy;local ra=ns.ProfRouteAuto
          local source=fixture();source.auctionSupply={[11]={quantity=10}}
          local raw=e.AuctionSupplyOf
          e.AuctionSupplyOf=function(context,id)
            if context then return raw(context,id)end
            return source.auctionSupply[id]
          end
          local capture=e.Capture
          e.Capture=function(slug,opts)
            local input=e.Copy(opts);input.snapshot=source;return capture(slug,input)
          end
          local opts={start=1,target=3,considerAuctionSupply=false}
          local off=finish('alchemy',opts)
          source.auctionSupply[11].quantity=0
          assert(not ra.Get('alchemy',opts).stale and not e.AuctionSupplyChanged(off))
          source.auctionSupply[11].quantity=10;opts.considerAuctionSupply=true
          ra.Recalculate('alchemy',opts);local on=finish('alchemy',opts)
          source.auctionSupply[11].quantity=9
          assert(ra.Get('alchemy',opts).staleReason=='supply' and e.AuctionSupplyChanged(on))
        ''')


class AuctionSupplyOptionUI(unittest.TestCase):
    setUp = ui.ProfessionUIFusionTests.setUp

    def boot(self, locale):
        ui.ProfessionUIFusionTests.boot(self, locale)
        self.lua.execute('DungeonsForeverDB.prof.autoConsiderAuctionSupply=nil')

    def test_default_scope_persistence_localization_and_setting_row(self):
        for locale in ('zhCN','zhTW','enUS'):
            self.boot(locale)
            self.lua.execute('''
              local key='autoConsiderAuctionSupply'
              assert(PD.SETTING_DEF[key]==false and not PD.Setting(key,'alchemy'))
              assert(not PD.BuildLvOpts('alchemy',1).considerAuctionSupply)
              PD.SetSettingRaw(key,true,'alchemy');PD.cur='enchanting'
              assert(PD.BuildLvOpts('alchemy',1).considerAuctionSupply)
              assert(not PD.BuildLvOpts('enchanting',1).considerAuctionSupply)
              assert(DungeonsForeverDB.prof.professionSettings.alchemy[key]==true)
              PD.cur='alchemy';PD.Wrap=function(text)return {text}end
              local rows={};PD.RowsSettings(rows)
              local count,found=0,false
              for _,row in ipairs(rows)do
                if row.togKey then count=count+1 end
                if row.togKey==key then
                  found=true;assert(row.text==ns.L['考虑拍卖行的销售数量'])
                  assert(rawget(ns.L,'考虑拍卖行的销售数量') and #row.help==4)
                end
              end
              assert(found and count<=PD.SETTING_TOG_MAX)
              PD.SetSettingRaw(key,false,'alchemy');assert(not PD.Setting(key,'alchemy'))
            ''')

    def test_disabled_quantity_hides_rescan_messages_and_changes_cache_key(self):
        self.lua.execute('''
          local opts=PD.BuildLvOpts('alchemy',1)
          local before=PD.PlanKeyOf('alchemy',opts)
          PD.SetSettingRaw('autoConsiderAuctionSupply',true)
          assert(before~=PD.PlanKeyOf('alchemy',PD.BuildLvOpts('alchemy',1)))
          local entry={id=11,source='ah',considerAuctionSupply=false,supplyObserved=false}
          assert(PD.AuctionSupplyText(entry)==nil and #PD.AuctionSupplyLines(entry)==0)
          assert(PD.PlanSupplyText({considerAuctionSupply=false,mats={entry}})==nil)
        ''')

    def test_fixed_material_purchases_ignore_stock_by_default(self):
        self.lua.execute('''
          ns.ProfRouteAuto.AHPriceOf=function()return 7 end
          ns.AuctionBridge={GetAuctionSupply=function()return {quantity=0}end}
          local ra=ns.ProfRouteAuto
          local off=ra.FixedPlan('alchemy',{target=3,recoveryEnabled=false})
          assert(off.total==14 and off.considerAuctionSupply==false and not off.auctionSupplyShortages)
          PD.SetSettingRaw('autoConsiderAuctionSupply',true)
          local on=ra.FixedPlan('alchemy',{target=3,recoveryEnabled=false})
          assert(on.considerAuctionSupply and on.completeCost==false)
          assert(on.diagnostics[1].code=='auctionSupplyLimited' and on.diagnostics[1].item==11)
        ''')


class AuctionSupplyOptionHUD(unittest.TestCase):
    setUp = hud.Issue4Tests.setUp
    boot = ui.ProfessionUIFusionTests.boot

    def test_disabled_frozen_route_does_not_shrink_after_live_stock_drops(self):
        self.lua.execute('''
          local s=fixture();s.considerAuctionSupply=false;s.auctionSupply={[11]={quantity=0}}
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(s)end
          local plan=finish('alchemy',{start=1,target=3,considerAuctionSupply=false})
          assert(plan.targetReached and ns.ProfExecution.Bind('alchemy',plan))
          DungeonsForeverDB.prof.follow={['Test-Realm']={slug='alchemy',skill=1,step=1,t0=1000}}
          ns.AuctionBridge={GetAuctionSupply=function()error('disabled route read live stock')end}
          local row=ns.ProfFollow.ShoppingList('alchemy')[1]
          assert(row.ahCount==2 and row.purchaseCost==14 and not row.auctionUnknown and not row.auctionShortage)
          local text=ns.ProfFollow.ShoppingSourceText(row)
          assert(not text:find(ns.L['库存未知'],1,true))
          PD.SetSettingRaw('autoConsiderAuctionSupply',true)
          assert(ns.ProfFollow.ShoppingList('alchemy')[1].ahCount==2,'frozen plan changed with settings')
        ''')


class AuctionSupplyOptionFishing(unittest.TestCase):
    setUp = fishing.SpecialRouteFixture.setUp

    def test_nonfish_material_stock_is_optional_in_self_fished_routes(self):
        fishing.SpecialRouteFixture.fishing(self)
        self.lua.execute('''
          local opts=fishInput();opts.considerAuctionSupply=false
          opts.snapshot.offers={};opts.snapshot.auctionSupply={[999]={quantity=0}}
          local off=computeFish(opts)
          assert(off.targetReached and off.total==15 and off.considerAuctionSupply==false)
          opts.considerAuctionSupply=true
          local on=computeFish(opts)
          assert(not on.targetReached and on.considerAuctionSupply)
          assert(#on.auctionSupplyShortages==1 and on.auctionSupplyShortages[1].item==999)
        ''')


if __name__ == '__main__':
    unittest.main()
