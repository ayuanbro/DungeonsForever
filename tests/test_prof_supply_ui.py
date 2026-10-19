"""Presentation of durable auction quantities and independent price dates."""
import unittest
import test_prof_ui_regressions as fixture
import test_prof_follow as follow_fixture

ROOT = fixture.ROOT


class PersistedSupplyUITests(unittest.TestCase):
    def setUp(self):
        fixture.ProfessionUIRegressions.setUp(self)
        self.lua.execute('''
          function findLine(lines,text)
            for _,line in ipairs(lines) do
              if line[1]==text then return line end
            end
          end
          time=function()return 1800000000 end
          date=function(_,stamp)return 'date:'..stamp end
        ''')

    def test_saved_quantity_has_source_coverage_and_separate_price_dates(self):
        self.lua.execute('''
          local e={source='ah',count=3,availableCount=5,supplyObserved=true,
            supplySource='client-auction-results',supplyComplete=true,supplyOwnerExcluded=true,
            supplyObservedAt=1799999900,priceObservedAt=1800000000,supplyObservedPrice=10}
          local lines=PD.AuctionSupplyLines(e)
          assert(findLine(lines,'数量观测：date:1799999900'))
          assert(findLine(lines,'拍卖行价格观测：date:1800000000'))
          assert(findLine(lines,'数量来源：客户端拍卖结果'))
          assert(findLine(lines,'扫描范围：完整结果'))
          assert(findLine(lines,'已排除本人拍卖'))
          assert(findLine(lines,'数量观测时最低单价：10'))
          assert(findLine(lines,'最近观测数量不保证当前仍在售，也不保证全部可按最低价格购买。'))
        ''')

    def test_internal_update_is_explicit_estimate_with_unknown_owner_and_coverage(self):
        self.lua.execute('''
          local e={source='ah',count=3,availableCount=5,supplyObserved=true,
            supplySource='auctionator-update',supplyComplete=false,supplyObservedAt=1799999900}
          local lines=PD.AuctionSupplyLines(e)
          assert(PD.AuctionSupplyText(e)=='扫描汇总估计：5 件；本路线购买 3 件。')
          assert(findLine(lines,'数量来源：Auctionator 最近更新（扫描汇总估计）'))
          assert(findLine(lines,'扫描范围：未核实'))
          assert(findLine(lines,'是否包含本人拍卖：未核实'))
          assert(not findLine(lines,'扫描范围：完整结果'))
          assert(findLine(lines,'拍卖行价格观测：观测时间未知'))
        ''')

    def test_age_warning_does_not_remove_saved_quantity_and_ignores_legacy_uptime(self):
        self.lua.execute('''
          local e={source='ah',count=3,availableCount=5,supplyObserved=true,
            supplyObservedAt=1800000000-2*86400}
          local old='数据较旧（超过两天）；仍按保存数量规划，请扫描后更新。'
          assert(not findLine(PD.AuctionSupplyLines(e),old))
          e.supplyObservedAt=e.supplyObservedAt-1
          local lines=PD.AuctionSupplyLines(e)
          assert(findLine(lines,old)[2]==0.95)
          assert(findLine(lines,'拍卖行数量快照：5 件；本路线购买 3 件。'))
          e.supplyObservedAt=500
          assert(findLine(PD.AuctionSupplyLines(e),'数量观测：观测时间未知'))
          assert(not findLine(PD.AuctionSupplyLines(e),old))
          assert(PD.AuctionObservationText(0/0)=='观测时间未知')
        ''')

    def test_history_remains_reference_when_no_current_quantity(self):
        self.lua.execute('''
          local e={source='ah',count=3,supplyObserved=false,
            supplyHistoryQuantity=100,supplyHistoryObservedAt=1799900000}
          local lines=PD.AuctionSupplyLines(e)
          assert(findLine(lines,'拍卖行可购数量未知，当前仅按价格估算。'))
          assert(findLine(lines,'请在拍卖师处执行一次完整扫描，以保存最近数量。'))
          assert(findLine(lines,'Auctionator 当日最高数量：100（仅供参考，不限制路线）'))
          assert(findLine(lines,'历史数量日期：date:1799900000'))
          assert(e.availableCount==nil,'history promoted into a purchase quantity')
        ''')

    def test_route_warning_names_only_unread_selected_auction_purchases(self):
        self.lua.execute('''
          local plan={auctionSupplyUnknown=2,mats={
            {id=10,source='ah',supplyObserved=false,count=3},
            {id=11,source='vendor',vendor=true,count=3},
            {id=12,source='ah',supplyObserved=true,availableCount=5},
            {id=13,source='ah',availableCount=0}},formulas={
            {id=10,source='ah',supplyObserved=false},
            {id=14,source='ah',supplyObserved=false},
            {id=15,source='ah',known=true,supplyObserved=false}}}
          local text=PD.PlanSupplyText(plan)
          assert(text:find('数量未知物品：Item10 / Item14。',1,true))
          assert(not text:find('Item11',1,true) and not text:find('Item12',1,true))
          assert(not text:find('Item13',1,true) and not text:find('Item15',1,true))
          assert(plan.mats[1].supplyObserved==false and plan.mats[1].availableCount==nil)
        ''')

    def test_route_warning_caps_names_and_retains_item_id_when_name_is_unloaded(self):
        self.lua.execute('''
          local plan={auctionSupplyUnknown=5,mats={}}
          for id=1,5 do plan.mats[id]={id=id,source='ah',supplyObserved=false} end
          local text=PD.PlanSupplyText(plan)
          assert(text:find('数量未知物品：Item1 / Item2 / Item3，另有 2 种（详见购物清单）。',1,true))
          PD.ItemName=function()return '暂时没有客户端数据',false end
          plan.auctionSupplyUnknown=1;plan.mats={{id=20,source='ah',supplyObserved=false}}
          assert(PD.PlanSupplyText(plan):find('数量未知物品：#20。',1,true))
          plan.auctionSupplyUnknown=0;assert(PD.PlanSupplyText(plan)==nil)
        ''')

    def test_vendor_formula_alternative_auction_price_has_only_its_price_date(self):
        self.lua.execute('''
          local e={source='vendor',vendor=true,ahPrice=15,priceObservedAt=1799999900,
            availableCount=20,supplyObservedAt=1799999900,supplySource='auctionator-update'}
          local lines=PD.AuctionSupplyLines(e)
          assert(#lines==1 and lines[1][1]=='拍卖行价格观测：date:1799999900')
          e.ahPrice=nil;assert(#PD.AuctionSupplyLines(e)==0)
        ''')

    def test_hud_material_and_formula_hover_share_persisted_route_observations(self):
        follow_fixture.FollowIntegrationTests.setUp(self)
        source=(ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        begin=source.index('function PD.PlanSupplyText(')
        self.lua.execute('PD=ns.ProfModule;L=ns.L;format=string.format;RA={MoneyStr=tostring}')
        self.lua.execute(source[begin:source.index('function PD.PlanHasSteps(',begin)])
        self.lua.execute('''
          time=function()return 1800000000 end
          date=function(_,stamp)return 'date:'..stamp end
          local created={}
          CreateFrame=function()local f=makeFrame();created[#created+1]=f;return f end
          ns.ProfHost.DG.ShowItemTip=function(_,item,extra)
            hoveredID=item[1];hoveredLines=extra
          end
          currentResult.steps={{150,151,101,1,actionID='a1',profession='alchemy',
            recipe={spell=101,item=20,count=1,mats={{10,2}}}}}
          currentResult.mats={{id=10,count=3,source='ah',availableCount=7,supplyObserved=true,
            supplyComplete=false,supplySource='client-auction-results',supplyOwnerExcluded=true,
            supplyObservedAt=1799999900,priceObservedAt=1800000000}}
          currentResult.formulas={{id=12,count=1,source='ah',availableCount=20,supplyObserved=true,
            supplySource='auctionator-update',supplyObservedAt=1799700000,supplyHistoryQuantity=100,
            supplyHistoryObservedAt=1799600000,supplyObservedPrice=10,priceObservedAt=1800000000}}
          ns.ProfFollow.Build();ns.ProfFollow.f:Show();ns.ProfFollow.Sync()
          ns.ProfFollow.showShop=true;ns.ProfFollow.Paint()
          local seen={}
          for _,frame in ipairs(created)do
            local e=frame.__purchase
            if e then
              assert(frame.scripts.OnEnter and frame.scripts.OnLeave)
              frame.scripts.OnEnter(frame)
              assert(hoveredID==e.id)
              local lines={}
              for _,line in ipairs(hoveredLines)do lines[line[1]]=true end
              assert(lines['需要：'..e.need])
              assert(lines['拍卖行价格观测：date:1800000000'])
              if e.id==10 then
                assert(lines['数量观测：date:1799999900'])
                assert(lines['已排除本人拍卖'])
                assert(lines['扫描范围：部分结果，仅代表已读取数量'])
              elseif e.id==12 then
                assert(e.formula and e.availableCount==20)
                assert(lines['扫描汇总估计：20 件；本路线购买 1 件。'])
                assert(lines['数量观测时最低单价：10'])
                assert(lines['数据较旧（超过两天）；仍按保存数量规划，请扫描后更新。'])
                assert(lines['Auctionator 当日最高数量：100（仅供参考，不限制路线）'])
                assert(lines['历史数量日期：date:1799600000'])
              else error('unexpected purchase tooltip') end
              seen[e.id]=true
            end
          end
          assert(seen[10] and seen[12],'material or formula had no HUD source tooltip')
          assert(currentResult.formulas[1].availableCount==20,'HUD changed the saved snapshot')
        ''')

    def test_new_observation_messages_load_in_all_three_locales(self):
        keys=['数量观测：%s','拍卖行价格观测：%s',
              '已有可靠商人报价，点击重新计算更新路线。',
              '数量未知物品：%s。','数量未知物品：%s，另有 %d 种（详见购物清单）。',
              '数据较旧（超过两天）；仍按保存数量规划，请扫描后更新。',
              'Auctionator 当日最高数量：%d（仅供参考，不限制路线）',
              '请在拍卖师处执行一次完整扫描，以保存最近数量。']
        for locale in ('zhCN','zhTW','enUS'):
            self.lua.globals().testLocale=locale
            self.lua.execute('GetLocale=function()return testLocale end')
            self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")(
                str(ROOT/'Locales/zhCN.lua'))
            if locale!='zhCN':
                self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")(
                    str(ROOT/f'Locales/{locale}.lua'))
            for key in keys:
                self.assertIsInstance(self.lua.globals().ns.L[key],str)
                if locale!='zhCN':
                    self.assertNotEqual(self.lua.globals().ns.L[key],key)


if __name__=='__main__':
    unittest.main()
