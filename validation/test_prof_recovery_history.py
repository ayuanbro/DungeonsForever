import unittest

import test_prof_profit_priority as profit
import test_prof_ui_fusion as ui
from test_prof_stock_persistence import StockPersistenceTests, plain, ROOT


NOTICE = '回血暂按历史数据估算；请使用 Auctionator 完整扫描一次拍卖行，再重新计算路线。'


class RecoveryHistoryTests(unittest.TestCase):
    def setUp(self):
        profit.ProfitPriorityTests.setUp(self)
        self.lua.execute('''
          function history(q,stamp)
            return {quantity=q,observedAt=stamp or 900,complete=false,source='auctionator-history'}
          end
          function historyFixture()
            local s=profitFixture();s.auctionSupply={};s.auctionSupplyHistory={[10]=history(100)}
            return s
          end
        ''')

    def test_history_estimate_changes_recovery_choice_but_not_purchase_objective(self):
        self.lua.execute('''
          local r=solve(historyFixture(),4);local c=counts(r)
          local q=r.recoverySnapshot.quotes[10]
          assert(c[101]==3 and not c[102] and r.recoveryTotal==1500 and r.netTotal==-1200)
          assert(q.source=='ah' and q.supplyEstimated and not q.supplyReliable)
          assert(q.supplySource=='auctionator-history' and q.complete==false)
          assert(r.recoveryEstimated and r.saleOutputs[1].supplyEstimated)
          r=solve(historyFixture(),4,false,false);c=counts(r)
          assert(c[102]==3 and not c[101] and not r.recoveryEstimated)
        ''')

    def test_memory_including_zero_and_low_stock_always_wins_over_history(self):
        self.lua.execute('''
          for _,quantity in ipairs({0,20,40,100}) do
            local s=historyFixture()
            s.auctionSupply[10]={quantity=quantity,observedAt=1000,complete=true,
              ownerExcluded=true,source='client-auction-results'}
            local q=ns.ProfRecovery.Capture(s,{recoveryEnabled=true,recoveryFeePercent=0}).quotes[10]
            assert(q.quantity==quantity and q.supplyReliable and not q.supplyEstimated)
            assert(q.source==(quantity>=40 and 'ah' or 'npc'))
          end
        ''')

    def test_expired_or_incomplete_recovery_observation_uses_history(self):
        self.lua.execute('''
          clock=200000
          for _,bad in ipairs({'expired','incomplete','own','future'}) do
            local s=historyFixture();local v={quantity=1,observedAt=200000,complete=true,
              ownerExcluded=true,source='client-auction-results'}
            if bad=='expired' then v.observedAt=1000
            elseif bad=='incomplete' then v.complete=false
            elseif bad=='own' then v.ownerExcluded=false
            else v.observedAt=200001 end
            s.auctionSupply[10]=v
            local q=ns.ProfRecovery.Capture(s,{recoveryEnabled=true,recoveryFeePercent=0}).quotes[10]
            assert(q.quantity==100 and q.supplyEstimated and not q.supplyReliable and q.source=='ah')
          end
        ''')

    def test_invalid_history_is_not_a_recovery_valuation(self):
        self.lua.execute('''
          local bad={history(-1),history(1.5),history(math.huge),history(0/0),history('100'),
            history(100,1001),history(100,0),history(100,-1),history(100,math.huge)}
          bad[#bad+1]={quantity=100,observedAt=900,source='client-auction-results'}
          for _,entry in ipairs(bad) do
            local s=historyFixture();s.auctionSupplyHistory[10]=entry
            local q=ns.ProfRecovery.Capture(s,{recoveryEnabled=true,recoveryFeePercent=0}).quotes[10]
            assert(q.source=='npc' and not q.supplyEstimated and not q.supplyReliable)
          end
        ''')

    def test_history_keeps_quantity_price_fee_and_discount_thresholds(self):
        self.lua.execute('''
          for _,quantity in ipairs({0,39,40}) do
            local s=historyFixture();s.auctionSupplyHistory[10]=history(quantity)
            local q=ns.ProfRecovery.Capture(s,{recoveryEnabled=true,recoveryFeePercent=5,residualMass=true}).quotes[10]
            assert(q.quantity==quantity and q.supplyEstimated)
            assert(q.unit==(quantity>=40 and 332 or 0))
          end
          local s=historyFixture();s.prices[10]=100
          local q=ns.ProfRecovery.Capture(s,{recoveryEnabled=true,recoveryFeePercent=0}).quotes[10]
          assert(q.source=='npc')
          s=historyFixture();q=ns.ProfRecovery.Capture(s,{recoveryEnabled=true}).quotes[10]
          assert(q.source=='npc')
          s=historyFixture();s.nonAuctionable={[10]=true}
          q=ns.ProfRecovery.Capture(s,{recoveryEnabled=true,recoveryFeePercent=0}).quotes[10]
          assert(q.source=='npc' and q.bound)
        ''')

    def test_profit_priority_limit_still_applies_with_history(self):
        self.lua.execute('''
          local r=solve(historyFixture(),26);local c=counts(r)
          assert(r.targetReached and c[101]==20 and c[102]==5 and r.recoveryEstimated)
          assert(r.recoveryTotal==10000 and r.priorityTotal==-7750)
        ''')

    def test_history_never_becomes_formula_stock_or_material_limit(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local s=historyFixture()
          s.prices[400]=50;s.auctionSupplyHistory[400]=history(100)
          s.auctionSupplyHistory[11]=history(1)
          local q=E.FormulaFor({key='alchemy:999',profession='alchemy',spell=999,formula=400,source={}},s)
          assert(not q.usable and q.reason=='formulaAuctionSupplyUnknown')
          assert(E.FormulaAuctionSupplyOf(s,400)==nil and E.AuctionSupplyOf(s,11)==nil)
          local r=solve(s,4)
          assert(r.targetReached and counts(r)[101]==3 and not r.purchaseVerified)
          assert(s.auctionSupply[10]==nil and s.auctionSupply[11]==nil and s.auctionSupply[400]==nil)
          s.auctionSupply[11]={quantity=1,observedAt=1000,complete=true,
            ownerExcluded=true,source='client-auction-results'}
          s.auctionSupplyHistory[11]=history(999)
          r=solve(s,4)
          assert(r.targetReached and (counts(r)[101] or 0)<=1)
        ''')

    def test_captured_history_is_not_requeried_mid_calculation(self):
        self.lua.execute('''
          ns.AuctionBridge={GetAuctionSupplyHistory=function()error('snapshot consulted live history')end,
            GetAuctionSupply=function()error('snapshot consulted live scan')end}
          local s=historyFixture();local r=solve(s,4)
          assert(r.recoveryEstimated and r.recoveryTotal==1500)
          local q=r.recoverySnapshot.quotes[10]
          s.auctionSupplyHistory[10].quantity=0
          assert(q.quantity==100 and q.source=='ah')
        ''')

    def test_change_detection_reads_live_history_and_detects_new_memory_scan(self):
        self.lua.execute('''
          local s=historyFixture();local r=solve(s,4);local current
          C_Item={GetItemSellPrice=function()return 0 end}
          ns.ProfRouteAuto.AHPriceOf=function(id)return s.prices[id]end
          ns.AuctionBridge={GetAuctionSupply=function(id)return id==10 and current or nil end,
            GetAuctionSupplyHistory=function(id)return s.auctionSupplyHistory[id]end}
          local opts={recoveryEnabled=true,recoveryFeePercent=0,residualMass=false}
          assert(not ns.ProfRecovery.Changed(r,opts))
          current={quantity=0,observedAt=1000,complete=true,ownerExcluded=true,source='client-auction-results'}
          assert(ns.ProfRecovery.Changed(r,opts))
          assert(r.recoverySnapshot.quotes[10].quantity==100 and r.recoveryTotal==1500)
        ''')

    def test_frozen_execution_keeps_its_valuation_until_explicit_recalculation(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function(_,opts)
            local s=ns.ProfEconomy.Index(historyFixture());ns.ProfRecovery.Capture(s,opts);return s
          end
          local opts={start=1,target=4,recoveryEnabled=true,recoveryFeePercent=0}
          local r=finish('alchemy',opts);local run=assert(ns.ProfExecution.Bind('alchemy',r))
          local frozen=run.plan
          assert(frozen.recoveryEstimated and frozen.recoverySnapshot.quotes[10].supplyEstimated)
          ns.AuctionBridge={GetAuctionSupply=function()return nil end,GetAuctionSupplyHistory=function()return nil end}
          assert(ns.ProfRouteAuto.Get('alchemy',opts)==frozen and frozen.recoveryTotal==1500)
          assert(DungeonsForeverDB.prof.auctionFullScan==nil)
        ''')


class RecoveryHistoryReloadTests(unittest.TestCase):
    def boot(self, saved=None):
        helper=StockPersistenceTests()
        lua=helper.boot(saved=saved,stamp=86500)
        for name in ('ProfPolicies','ProfRouteAuto','ProfEssences','ProfSolverCapture','ProfRecovery','ProfRouteSolver'):
            lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                        (ROOT/'Core'/(name+'.lua')).read_text(encoding='utf-8-sig'))
        lua.execute('''
          ns.ProfRecipes={alchemy={rows={{101,10,1,'',nil,nil,1,100,200,300,false,{{11,1}}}}}}
          IsPlayerSpell=function()return true end;UnitLevel=function()return 60 end
          C_Item={GetItemSellPrice=function()return 2 end}
          Auctionator.API={v1={GetAuctionPriceByItemID=function(_,id)return id==10 and 500 or 7 end}}
          Auctionator.Constants={SCAN_DAY_0=86400}
          Auctionator.Database.db={['10']={h={['0']=500},a={['0']=100},m=500}}
          function Auctionator.Database:GetPriceHistory(key)
            assert(type(key)=='string')
            local item=self.db[key];local rows={}
            for day,n in pairs(item and item.a or {})do rows[#rows+1]={rawDay=day,available=n}end
            return rows
          end
          function capture()
            return ns.ProfEconomy.Capture('alchemy',{start=1,target=3,autoCraftTools=false,
              considerAuctionSupply=true,recoveryEnabled=true,recoveryFeePercent=5})
          end
        ''')
        return lua

    def test_scan_then_relogin_uses_saved_market_instead_of_daily_history(self):
        lua=self.boot()
        lua.execute('''
          beginFull(2);sendFull({rawRow(11,8,56,'Seller'),rawRow(10,20,6000,'Seller')});finishFull()
          local s=capture();local q=s.recovery.quotes[10]
          assert(q.quantity==20 and q.source=='npc' and q.supplyReliable and not q.supplyEstimated)
          assert(DungeonsForeverDB.prof.auctionFullScan.items[10].q>0 and DungeonsForeverDB.prof.auctionReplicateGate==nil)
        ''')
        fresh=self.boot(plain(lua.globals().DungeonsForeverDB))
        fresh.execute('''
          local s=capture();local q=s.recovery.quotes[10]
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==20 and s.auctionSupply[10].quantity==20)
          assert(q.quantity==20 and q.source=='npc' and q.supplyReliable and not q.supplyEstimated)
          assert(ns.ProfEconomy.FormulaAuctionSupplyOf(s,10).quantity==20)
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=3,autoCraftTools=false,
            recoveryEnabled=true,recoveryFeePercent=5})
          assert(r.targetReached and not r.recoveryEstimated and r.recoveryTotal==4)
          assert(r.purchaseVerified and r.auctionSupplyUnknown==0)
          beginFull(2);sendFull({rawRow(11,8,56,'Seller'),rawRow(10,40,12000,'Seller')});finishFull()
          s=capture();q=s.recovery.quotes[10]
          assert(q.quantity==40 and q.unit==285 and q.supplyReliable and not q.supplyEstimated)
          assert(DungeonsForeverDB.prof.auctionFullScan.items[10].q>0 and DungeonsForeverDB.prof.auctionReplicateGate==nil)
        ''')


class RecoveryHistoryUITests(unittest.TestCase):
    def test_three_locales_label_historical_estimate_without_current_stock_claim(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                fixture=ui.ProfessionUIFusionTests();fixture.boot(locale)
                fixture.lua.execute('''
                  PD.Wrap=function(text)return {text}end
                  local key='回血暂按历史数据估算；请使用 Auctionator 完整扫描一次拍卖行，再重新计算路线。'
                  assert(rawget(ns.L,key))
                  local q={id=10,unit=475,count=2,revenue=950,source='ah',quantity=100,
                    observedAt=900,supplyEstimated=true,supplyReliable=false,supplySource='auctionator-history'}
                  local src={recoveryEstimated=true,recoveryTotal=950,recoveryAssumesAllSold=true,
                    total=14,netTotal=-936,saleOutputs={q},recoverySnapshot={feePercent=5,quotes={[10]=q}}}
                  PD.lvSummary={};PD.CopyRecoverySummary(src)
                  assert(PD.lvSummary.recoveryEstimated)
                  local rows={};PD.RowsRecoveryDetail(rows,src)
                  local notices,historyLines=0,0
                  for _,r in ipairs(rows)do
                    if r.text==ns.L[key] then notices=notices+1 end
                    for _,line in ipairs(r.lines or {})do
                      if line[1]==format(ns.L['历史观测数量：%d（仅用于回血估算）'],100)then historyLines=historyLines+1 end
                      assert(line[1]~=format(ns.L['观测可售 %d 件（超出部分按卖店价）'],100))
                    end
                  end
                  assert(notices==1 and historyLines==1)
                  src.recoveryEstimated=nil;q.supplyEstimated=false;q.supplyReliable=true
                  rows={};PD.RowsRecoveryDetail(rows,src);PD.CopyRecoverySummary(src)
                  assert(PD.lvSummary.recoveryEstimated==nil)
                  for _,r in ipairs(rows)do assert(r.text~=ns.L[key])end
                ''')


if __name__=='__main__':
    unittest.main()
