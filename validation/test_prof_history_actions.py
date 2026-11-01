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
          local old=newrun();local current=newrun()
          assert(not xp.Remove('enchanting',old.planID))
          assert(not xp.Remove('alchemy',current.planID))
          assert(xp.CanRemove('alchemy',old.planID) and xp.Remove('alchemy',old.planID))
          assert(not xp.Get('alchemy',old.planID) and #xp.GetHistory('alchemy')==1)
          assert(xp.GetActive('alchemy')==current and current.attemptsDone==0)
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
          local source=newrun();local current=newrun()
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
          local old=newrun();newrun();local rows={};PD.RowsCraftLog(rows)
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
