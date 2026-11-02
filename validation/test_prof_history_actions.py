"""History deletion and estimated cost use the actual frozen execution."""
import unittest
import test_prof_ui_fusion as ui


class HistoryActionsTests(unittest.TestCase):
    boot=ui.ProfessionUIFusionTests.boot

    def setUp(self):
        self.boot('zhCN')
        self.lua.execute('''
          xp=ns.ProfExecution;ra=ns.ProfRouteAuto;opts={start=1,target=3}
          function newrun()
            local r=ra.Compute('alchemy',{snapshot=fixture(),start=1,target=3})
            return assert(xp.StartNew('alchemy',r))
          end
        ''')

    def test_remove_independent_archive_preserves_active_and_other_profession(self):
        self.lua.execute('''
          local old=newrun();assert(xp.RecordAttempt('alchemy',101,'old-cast'));local current=newrun()
          assert(not xp.Remove('enchanting',old.planID))
          assert(not xp.Remove('alchemy',current.planID))
          assert(xp.CanRemove('alchemy',old.planID) and xp.Remove('alchemy',old.planID))
          assert(not xp.Get('alchemy',old.planID) and #xp.GetHistory('alchemy')==1)
          assert(xp.GetActive('alchemy')==current and current.attemptsDone==0)
        ''')

    def broken_run(self):
        self.lua.execute('''
          broken=newrun();assert(xp.RecordAttempt('alchemy',101,'before-plan-loss'))
          broken.plan=nil
        ''')

    def test_missing_plan_does_not_break_leveling_pages_or_other_professions(self):
        self.broken_run()
        self.lua.execute('''
          PD.built=true;PD.page=widget();PD.scroll=widget();PD.rows={};PD.LV_TILE_H=64
          for _,name in ipairs({'PickNav','PickTabs','Layout','PlaceSettingsToggles',
            'RequestRows','WarmNames','PaintToolProgress','PaintToolStale','UpdateVScroll'})do
            PD[name]=function()end
          end
          PD.PaintLvTiles=function()return 0 end
          PD.PaintRows=function(rows)rendered=rows end
          PD.PaintTool=function(list)painted=list;return 0 end
          function trackButton()
            for _,entry in ipairs(painted)do if entry.key=='track' then return entry end end
          end
          for _,page in ipairs({'route','shop','log','recovery'})do
            PD.autoPage=page;PD.Render()
            local button=trackButton()
            assert(button and button.on and button.text==ns.L['结束追踪'])
            assert(#rendered>0 and xp.GetActive('alchemy')==broken)
          end
          PD.cur='enchanting';PD.autoPage='route';PD.Render()
          assert(trackButton().text==ns.L['开始执行'] and not xp.GetActive('enchanting'))
          assert(xp.GetActive('alchemy')==broken and broken.attemptsDone==1)
        ''')

    def test_end_unreadable_execution_allows_recalculation_without_losing_history(self):
        self.broken_run()
        self.lua.execute('''
          local planID=broken.planID;local progress=broken.progress
          local _,click=PD.LevelTool();click('track')
          assert(not xp.GetActive('alchemy') and broken.status=='archived')
          assert(xp.Get('alchemy',planID)==broken and broken.progress==progress)
          local inventory,source,err=xp.PrepareRecalculate('alchemy')
          assert(type(inventory)=='table' and not source and not err)
          click('recalc');PD.RowsLeveling({})
          assert(PD.autoSnapshot and PD.autoSnapshot.status=='searching')
          for i=1,100 do ra.Pump('alchemy');if not ra.HasWork('alchemy') then break end end
          PD.RowsLeveling({})
          assert(PD.autoSnapshot.feasible and #PD.autoSnapshot.steps>0)
          local replacement=newrun()
          assert(replacement~=broken and replacement.plan and replacement.attemptsDone==0)
          assert(xp.Get('alchemy',planID)==broken and broken.attemptsDone==1)
        ''')

    def test_unreadable_history_is_not_reported_as_no_history(self):
        self.broken_run()
        self.lua.execute('''
          local rows={};PD.RowsCraftLog(rows);local text=''
          for _,row in ipairs(rows)do
            assert(row.text~=ns.L['本角色还没有任何制作记录。'])
            if row.kind=='text' then text=text..row.text end
          end
          assert(text==ns.L['这份制作记录的执行计划无法读取；记录已保留。'])
          assert(PD.CraftLogCost('alchemy')==nil)
        ''')

    def test_invalid_execution_cost_tile_reports_plan_problem_with_prices_available(self):
        self.broken_run()
        self.lua.execute('''
          ra.Available=function()return true end
          ra.HasPriceData=function()return true end
          assert(PD.AuctionatorState()=='ok')
          local function tile()
            local f=widget();f.label=widget();f.val=widget()
            f.val.SetText=function(self,value)self.text=value end
            return f
          end
          PD.lvTiles={mode=tile(),scheme=tile(),excl=tile(),target=tile(),cost=tile()}
          PD.chipOrder={'mode','scheme','excl','target'};PD.LV_TILE_H=60
          PD.PaintTileBorder=function()end;PD.PlaceCards=function()end
          PD.SetBadge=function(text)badge=text end;PD.SetSub=function()end
          PD.TipTile=function(t,lines)t.lines=lines end
          for _,page in ipairs({'route','shop','log','recovery'})do
            PD.autoPage=page;PD.RowsLeveling({});PD.PaintLvTiles()
            assert(badge==ns.L['路线待重算'])
            assert(PD.lvTiles.cost.val.text==ns.L['—'])
            local found=false
            for _,line in ipairs(PD.lvTiles.cost.lines)do
              assert(not line[1]:find('扫描',1,true),'plan failure requested an auction scan')
              if line[1]==ns.L['执行计划缺失或无法读取；请结束追踪后重新计算。'] then found=true end
            end
            assert(found)
          end
          local _,click=PD.LevelTool();click('track');click('recalc')
          PD.autoPage='route';PD.RowsLeveling({})
          for i=1,100 do ra.Pump('alchemy');if not ra.HasWork('alchemy') then break end end
          PD.RowsLeveling({});PD.PaintLvTiles()
          -- The fixture has prices but no full-scan quantity certification.
          assert(PD.SnapshotBadgeState(PD.lvSummary)=='stock_unknown')
          assert(badge~=ns.L['路线待重算'] and PD.lvTiles.cost.val.text~=ns.L['—'])
        ''')

    def test_empty_summary_is_not_missing_price_data_but_real_absence_is_reported(self):
        self.lua.execute('''
          ra.Available=function()return true end
          ra.HasPriceData=function()return true end
          assert(PD.SnapshotBadgeText(nil)==nil and PD.SnapshotBadgeText({})==nil)
          assert(PD.SnapshotBadgeState({scheme='cheapest',priced=false})=='incomplete')
          assert(PD.SnapshotBadgeState({planVersion=2,status='recalculate_required',
            diagnostics={{code='historyUnreadable'}}})=='rules_changed')
          ra.HasPriceData=function()return false end
          assert(PD.AuctionatorState()=='noprice')
          assert(PD.SnapshotBadgeText({scheme='cheapest',priced=false})==ns.L['缺少价格快照，请扫描拍卖行'])
        ''')

    def test_invalid_plan_shapes_share_validation_without_conversion(self):
        self.broken_run()
        self.lua.execute('''
          for _,value in ipairs({false,42,'invalid',{},
            {executionVersion=2,steps={}}, {executionSteps=42,steps={}}})do
            broken.plan=value
            local list=PD.LevelTool();local found=false
            for _,b in ipairs(list)do if b.key=='track' then
              assert(b.text==ns.L['结束追踪']);found=true
            end end
            assert(found)
            for _,page in ipairs({'route','shop','log','recovery'})do
              PD.autoPage=page;PD.RowsLeveling({})
            end
            assert(broken.plan==value and PD.CraftLogCost('alchemy')==nil)
          end
        ''')

    def test_unreadable_only_tracking_disables_observation_and_reenables_for_valid_run(self):
        self.broken_run()
        self.lua.execute('''
          local active,receipts=xp.RefreshObservation()
          assert(not active and not receipts)
          assert(not xp.RecordAttempt('alchemy',101,'invalid-plan'))
          assert(broken.attemptsDone==1)
          xp.End('alchemy');newrun()
          active,receipts=xp.RefreshObservation()
          assert(active and receipts and xp.RecordAttempt('alchemy',101,'valid-plan'))
        ''')

    def test_end_and_recalculation_sources_are_protected(self):
        self.lua.execute('''
          local old=newrun();xp.PrepareRecalculate('alchemy')
          assert(not xp.CanRemove('alchemy',old.planID))
          xp.End('alchemy');assert(not xp.Remove('alchemy',old.planID))
          assert(type(xp.GetContinuation('alchemy'))=='table')
        ''')

    def test_archived_inherited_sources_are_protected(self):
        self.lua.execute('''
          local source=newrun();assert(xp.RecordAttempt('alchemy',101,'source-cast'));local current=newrun()
          assert(xp.Get('alchemy',source.planID))
          current.inheritedFrom=source.planID
          assert(not xp.Remove('alchemy',source.planID))
          current.inheritedFrom=nil
          current.plan.executionOptions={executionSourcePlanID=source.planID}
          assert(not xp.Remove('alchemy',source.planID))
        ''')

    def test_deleted_run_cannot_receive_pending_receipt(self):
        self.lua.execute('''
          local old=newrun();assert(xp.RecordAttempt('alchemy',101,'old-cast'))
          local current=newrun();assert(xp.Remove('alchemy',old.planID))
          assert(not xp.RecordOutput({slug='alchemy',itemID=10,quantity=1,castGUID='old-cast'},'structured'))
          assert(current.attemptsDone==0 and not xp.Get('alchemy',old.planID))
        ''')

    def test_right_click_uses_card_identity_and_does_not_delete_on_left_click(self):
        self.lua.execute('''
          local old=newrun();assert(xp.RecordAttempt('alchemy',101,'old-cast'));newrun();local rows={};PD.RowsCraftLog(rows)
          local card
          for _,row in ipairs(rows)do for _,c in ipairs(row.cards or {})do if c.act and c.tips then card=c end end end
          assert(card);PD.cur='enchanting';card.act(nil,'LeftButton')
          assert(xp.Get('alchemy',old.planID))
          card.act(nil,'RightButton');assert(not xp.Get('alchemy',old.planID))
        ''')

    def test_cost_estimate_counts_actual_casts_and_archived_plan(self):
        self.lua.execute('''
          local run=newrun();local cost,casts,planned=PD.CraftLogCost('alchemy')
          assert(cost==0 and casts==0 and planned==2)
          assert(xp.RecordAttempt('alchemy',101,'one'))
          cost,casts,planned=PD.CraftLogCost('alchemy')
          assert(cost==7 and casts==1 and planned==2)
          xp.End('alchemy');assert(PD.CraftLogCost('alchemy')==7)
        ''')

    def test_unknown_cost_is_not_zero_and_recovery_attribution_is_not_recharged(self):
        self.lua.execute('''
          local run=newrun();assert(xp.RecordAttempt('alchemy',101,'one'))
          local st=run.plan.executionSteps[1]
          st.attributedCost=999;st.productionCost=999;st.transferredCost=999
          assert(PD.CraftLogCost('alchemy')==7)
          st.unpriced=true;assert(PD.CraftLogCost('alchemy')==nil)
          st.unpriced=nil;st.cost=nil;assert(PD.CraftLogCost('alchemy')==nil)
        ''')

    def test_self_crafted_material_chain_is_charged_once(self):
        self.lua.execute('''
          local s=fixture();s.recipes[1].yellow=2;s.recipes[1].green=2;s.recipes[1].grey=2
          s.recipes[2]={profession='alchemy',spell=102,item=12,count=1,mats={{10,2}},
            learn=2,yellow=100,green=200,grey=300,cooldown=false}
          s.known['alchemy:102']=true;s.prices[10]=100
          local r=ra.Compute('alchemy',{snapshot=s,start=1,target=3})
          local run=assert(xp.Bind('alchemy',r))
          for _,st in ipairs(run.plan.executionSteps)do run.progress[st.segmentID]={casts=st[4]}end
          local cost=PD.CraftLogCost('alchemy')
          assert(cost==r.total and cost==14)
        ''')


if __name__=='__main__':unittest.main()
