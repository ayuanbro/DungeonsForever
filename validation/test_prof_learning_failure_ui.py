"""Real Forever learning gaps must be named without unrelated stock warnings.

This checks Lua UI rows and status decisions, not live client rendering.
"""
import unittest

from test_prof_production_learning import production_runtime, ROOT
from test_prof_ui_fusion import UI_MOCKS


class LearningFailureUITests(unittest.TestCase):
    def boot(self, locale='zhCN'):
        self.lua = production_runtime(locale)
        load = self.lua.eval("function(s)assert(loadstring(s))('DungeonsForever',ns)end")
        load((ROOT / 'Locales/zhCN.lua').read_text(encoding='utf-8-sig'))
        if locale != 'zhCN':
            load((ROOT / 'Locales' / (locale + '.lua')).read_text(encoding='utf-8-sig'))
        self.lua.execute('savedData={ns.ProfData,ns.ProfRecipes,ns.ProfLeveling}')
        self.lua.execute(UI_MOCKS)
        self.lua.execute('''
          ns.ProfData,ns.ProfRecipes,ns.ProfLeveling=unpack(savedData)
          ns.ProfRouteAuto.MoneyStr=function(n)return tostring(n or 0)end
          ns.ProfRouteAuto.MaxStaleSeconds=function()return 48*3600 end
          GetSpellInfo=function(id)if id==2365 then return '语言药剂' end end
        ''')
        load((ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          PD=ns.ProfModule;PD.cur='alchemy';PD.tab='leveling'
          PD.Wrap=function(t)return {t}end
          PD.ProfLearned=function()return {blacksmithing={cur=57,max=300},herbalism={cur=50,max=300}}end
          ns.AuctionBridge={GetAuctionSupply=function()return {
            quantity=100000,observedAt=1000,complete=true,ownerExcluded=true,
            source='client-auction-results',market=1}
          end}
        ''')

    def setUp(self):
        self.boot()

    def test_real_unknown_origin_with_verified_purchase_is_not_a_learning_blocker(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local r=E.FindRecipe('alchemy',2365)
          local allowed,reason,detail=E.RouteRecipeEligibility(r,nil,{skill={alchemy=100}})
          assert(allowed and detail.quote.source=='ah' and detail.quote.id==2556)
          local p={status='complete',targetReached=true,feasible=true,steps={},mats={},
            formulas={detail.quote},learningBlocked=false,blockingLearningGaps={},auctionSupplyUnknown=0}
          assert(PD.PlanStatusParts(p)~=ns.L['学习资料不足，当前无法到达目标。'])
          assert(PD.PlanSupplyParts(p)==nil,'a fresh verified pattern requested another scan')
          local rows={};PD.RowsLearningBlockers(rows,p)
          assert(#rows==0,'origin metadata was shown as an acquisition blocker')
        ''')

    def test_failed_empty_plan_does_not_scan_unselected_material_candidates(self):
        self.lua.execute('''
          PD.RouteSupplyNeedsRescan=function()error('unselected candidates were inspected')end
          local p={feasible=false,status='infeasible',steps={},mats={},formulas={},
            auctionSupplyUnknown=0,auctionSupplyCandidates={11,22},learningBlocked=true,
            blockingLearningGaps={{spell=7183,missingReasons={'learningSourceMissing'}}}}
          assert(PD.PlanSupplyParts(p)==nil)
          p.mats={{id=11,source='ah',count=2,availableCount=nil}}
          local head,detail=PD.PlanSupplyParts(p)
          assert(head and head:find('1',1,true) and detail,
            'a genuinely selected unknown AH purchase must still warn')
          p.mats={{id=11,source='vendor',count=2}}
          assert(PD.PlanSupplyParts(p)==nil,'NPC purchases required an AH stock scan')
        ''')

    def test_nonblocking_coverage_gap_does_not_override_stock_or_cost_status(self):
        self.lua.execute('''
          local d={code='auctionSupplyLimited',item=11,required=2,available=1}
          local p={planVersion=2,status='incomplete',feasible=false,targetReached=false,
            steps={{1,2,101,1}},plannedTo=2,total=7,completeCost=true,learningComplete=true,
            learningBlocked=false,blockingLearningGaps={},blockingDiagnostics={d},diagnostics={},
            learningGaps={{spell=7183,missingReasons={'learningSourceMissing'}}},
            auctionSupplyShortages={d}}
          assert(PD.PlanStatusParts(p)==ns.ProfEconomy.DiagnosticText(d))
          assert(PD.SnapshotBadgeState(p)=='stock_short')
          assert(PD.PlanCostText(p)=='7')
          local rows={};PD.RowsLearningBlockers(rows,p);assert(#rows==0)
          local tips={};PD.PlanDiagnostics(function(t)tips[#tips+1]=t end,p)
          assert(not table.concat(tips,' '):find('7183',1,true))
          PD.CopyPlanSummary(p)
          assert(PD.lvSummary.learningBlocked==false and #PD.lvSummary.blockingLearningGaps==0)
          assert(PD.lvSummary.blockingDiagnostics==p.blockingDiagnostics)
          assert(PD.PlanStatusParts(PD.lvSummary)==ns.ProfEconomy.DiagnosticText(d))
        ''')

    def test_freshness_warning_only_checks_purchases_and_actual_stock_blockers(self):
        self.lua.execute('''
          local p={feasible=false,stale=true,staleReason='supply',
            auctionSupplyCandidates={22},blockingDiagnostics={{code='learningDataMissing',spell=7183}}}
          ns.AuctionBridge={GetAuctionSupply=function()error('unused candidate stock was checked')end}
          assert(not PD.RouteSupplyNeedsRescan(p))
          assert(PD.PlanCacheText(p)==ns.L['拍卖行库存已更新，点击重新计算即可使用。'])
          ns.AuctionBridge.GetAuctionSupply=function(id)assert(id==11);return nil end
          p.blockingDiagnostics={{code='auctionSupplyLimited',item=11,required=2,available=1}}
          assert(PD.RouteSupplyNeedsRescan(p))
          assert(PD.PlanCacheText(p)==ns.L['请使用 Auctionator 完整扫描一次拍卖行，再重新计算路线。'])
        ''')

    def test_old_failure_rules_notice_has_priority_over_old_learning_classification(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            with self.subTest(locale=locale):
                self.boot(locale)
                self.lua.execute('''
                  local p={planVersion=2,status='incomplete',stale=true,
                    staleReason='diagnostic-policy',diagnosticPolicyChanged=true,
                    learningBlocked=true,blockingLearningGaps={{spell=7183}},
                    targetReached=false,steps={{1,2,101,1}},total=7}
                  assert(PD.PlanStatusParts(p)==ns.L['路线规则已更新，请重新计算。'])
                  assert(PD.PlanCacheText(p)==ns.L['路线规则已更新，请重新计算。'])
                  assert(PD.SnapshotBadgeState(p)=='rules_changed')
                  local rows={};PD.RowsLearningBlockers(rows,p);assert(#rows==0)
                  PD.CopyPlanSummary(p)
                  assert(PD.lvSummary.diagnosticPolicyChanged and PD.lvSummary.staleReason=='diagnostic-policy')
                  assert(PD.PlanStatusParts(PD.lvSummary)==ns.L['路线规则已更新，请重新计算。'])
                  if GetLocale()~='zhCN' then
                    assert(ns.L['路线规则已更新，请重新计算。']~='路线规则已更新，请重新计算。')
                  end
                ''')


if __name__ == '__main__':
    unittest.main()
