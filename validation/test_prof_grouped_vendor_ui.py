"""Actual route rows aggregate progress; vendor details use their schema normalizers."""
import unittest
import test_prof_ui_fusion as ui


class GroupedVendorUITests(unittest.TestCase):
    setUp=ui.ProfessionUIFusionTests.setUp
    boot=ui.ProfessionUIFusionTests.boot

    def test_grouped_rows_show_combined_progress_without_changing_execution(self):
        self.lua.execute('''
          local snapshot={recipes={
            {profession='alchemy',spell=101,item=10,count=1,mats={{11,1}},
              learn=1,yellow=100,green=200,grey=300,cooldown=false},
            {profession='alchemy',spell=102,item=20,count=1,mats={{10,1},{12,1}},
              learn=1,yellow=100,green=200,grey=300,cooldown=false}},
            professions={alchemy={cur=1,max=300}},known={['alchemy:101']=true,['alchemy:102']=true},
            prices={[11]=2,[12]=3},auctionSupply={[11]={quantity=5},[12]={quantity=5}},coverageComplete=true}
          local sequence={}
          for i=1,5 do
            sequence[#sequence+1]={0,0,101,1,profession='alchemy'}
            sequence[#sequence+1]={0,0,102,1,profession='alchemy'}
          end
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(snapshot)end
          local plan=ns.ProfRouteSolver.Compute('alchemy',{snapshot=snapshot,start=1,target=11,
            fixedSteps=sequence,autoCraftTools=false,recoveryEnabled=false})
          assert(#plan.steps==2 and #plan.executionSteps==10)
          local xp=ns.ProfExecution
          local run=assert(xp.Bind('alchemy',plan))
          ns.ProfTrack.Rebase=function()error('grouped view must not rebase execution')end
          local function paint()
            PD.Wrap=function(text)return{text}end
            ns.ProfRouteAuto.Get=function()return xp.GetPlan('alchemy')end
            local rows={};PD.RowsLeveling(rows)
            local crafts={};for _,row in ipairs(rows)do if row.lvstep then crafts[#crafts+1]=row end end
            assert(#crafts==2 and crafts[1].trackCur and not crafts[2].trackCur)
            return crafts
          end
          paint()
          for index=1,2 do
            local step=plan.executionSteps[index];local guid='ui:'..index
            assert(xp.RecordAttempt('alchemy',step[3],guid))
            assert(xp.RecordOutput({itemID=step.item,quantity=1,castGUID=guid}))
            skills.alchemy.cur=step[2];xp.Sync('alchemy')
          end
          local rows=paint()
          assert(rows[1].cnt=='1/5' and rows[2].cnt=='1/5')
          assert(run.currentIndex==3 and #run.plan.executionSteps==10)
          assert(#run.steps==10 and run.plan.executionSteps[2][3]==102)
        ''')

    def test_material_five_tuples_and_pattern_eight_tuples_keep_correct_stock_and_price(self):
        self.lua.execute('''
          ns.ProfMaterialSupplyMeta={schemaVersion=2,fingerprint='fixture',verifiedAt='fixture'}
          ns.ProfFormulaOffersMeta={schemaVersion=1,source='fixture'}
          ns.EnsureProfMaterialSupply=function()return {[3371]={101,100,5,1,99999,102,120,6,3,123456}}end
          ns.EnsureProfFormulaOffers=function()return {[400]={201,200,2,1,12,1,0,0,
            202,0,-1,3,14,1,42,3}}end
          ns.EnsureProfSources=function()return {[3371]={v={{id=101,name='Vendor A'}}}}end
        ''')
        self.load((ui.ROOT/'Core/ProfSupply.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local rows=assert(PD.VendorOffersOf(3371));assert(#rows==2)
          assert(rows[1].npcID==101 and rows[1].price==100 and rows[1].pack==5)
          assert(rows[2].npcID==102 and rows[2].price==120 and rows[2].pack==6)
          for _,row in ipairs(rows)do
            assert(row.unlimited and not row.limited and not row.stockUnknown)
            assert(row.area==nil and row.cur==nil,'raw tag became a zone or currency')
          end
          rows=assert(PD.VendorOffersOf(400));assert(#rows==2)
          assert(rows[1].npcID==201 and rows[1].price==200 and rows[1].limited==2 and rows[1].area==12)
          assert(rows[2].npcID==202 and rows[2].unlimited and rows[2].cur==42 and rows[2].amt==3)
          PD.MyVendorSide=function()return nil end
          PD.VendorName=function(o)return 'Vendor '..o.npcID end
          PD.CampZoneName=function(id)return 'Zone '..id end
          PD.CurrencyOf=function()return 'Token' end
          local lines={};PD.VendorBlockLines(lines,400)
          local text='';for _,line in ipairs(lines)do text=text..line[1]..'\\n'end
          assert(text:find(ns.L['商人库存：限量刷新'],1,true))
          assert(text:find(ns.L['商人库存：固定售卖（不限量）'],1,true))
        ''')


if __name__=='__main__':unittest.main()
