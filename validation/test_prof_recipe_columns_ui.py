"""Long recipe content must stay within native column and tooltip boundaries."""
import unittest
import os
from pathlib import Path
import test_prof_ui_fusion as ui
from test_prof_issue4 import WIDGETS

ROOT=ui.ROOT


class RecipeColumnsUITests(unittest.TestCase):
    def setUp(self):
        ui.ProfessionUIFusionTests.boot(self,'zhCN')
        self.lua.execute(WIDGETS)
        self.lua.execute('''
          ns.ProfHost.MakeFS=recordedWidget;CreateFrame=recordedWidget
          function recipeRow()
            local r=recordedRow();r.mn={};r.mz={};r.mcnt={};r:SetWidth(900)
            function r.b:GetPoint(i)return unpack(self.points[i] or {})end
            return r
          end
        ''')
        source=Path(os.environ.get('DF_RECIPE_UI_SOURCE',ROOT/'Core/ProfessionUI.lua'))
        self.load(source.read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          PD=ns.ProfModule
          PD.TextW=function(text)return #text*6 end
          PD.Fit=function(text,size,width)
            if #text*6<=width then return text end
            return text:sub(1,math.max(0,math.floor(width/6)-3))..'...'
          end
          PD.SyncRows=function()return 100 end
          PD.WireTipZone=function()end;PD.QualCached=function()end
          PD.ItemName=function(id)return 'Material '..id,true end
        ''')

    def test_name_and_material_budgets_never_intersect_even_with_large_prices(self):
        self.lua.execute('''
          local name=string.rep('Long recipe ',20)
          local list={{text=name,sub=string.rep('Long description ',20),
            costStr=string.rep('999',30),ahStr='1234567 gold'}}
          PD.FitRecipeCols(list)
          local s=list[1];assert(s.recipeCols and s._fullText==name and s.tipTitle==name)
          assert(PD.TextW(s.text)<=PD.MAT_X-8-PD.RECIPE_PADL)
          assert(PD.MAT_W>=0)
          local r=recipeRow();r.b:SetPoint('BOTTOMLEFT',r,'BOTTOMLEFT',32,4)
          PD.BoundRecipeColumns(r,s,32)
          assert(32+r.a.width<=PD.MAT_X-8 and 32+r.b.width<=PD.MAT_X-8)
          assert(r.e.width+8<=PD.REC_COST_W and r.c2.width+8<=PD.REC_AH_W)
          assert(r.d.width<=PD.DiffBarW()+PD.REC_COST_W-8)
        ''')

    def test_render_measurement_overflow_keeps_complete_material_tooltip(self):
        self.lua.execute('''
          local r=recipeRow();PD.MAT_X=160
          r.__spec={_mats={{1,2},{2,20},{3,100},{4,1},{5,9}}}
          local segs={{id=1,cnt=2,text=string.rep('material one ',6)},
            {id=2,cnt=20,text='material two'}}
          PD.PaintMatSegs(r,segs,nil,90)
          assert(r.f.width<=90 and r.f:IsShown())
          assert(r.mz[1]:IsShown() and r.mz[1].__it==nil)
          assert(#r.mz[1].__tipLines==6,'overflow tooltip lost hidden reagents')
          PD.ClearMatSegs(r)
          PD.PaintMatSegs(r,{{id=1,cnt=2,text='small'}},nil,90)
          assert(r.f.width==30 and r.mz[1].__it[1]==1 and r.mcnt[1]:IsShown())
          PD.ClearMatSegs(r);PD.PaintMatSegs(r,segs,nil,0)
          assert(not r.mz[1]:IsShown(),'zero-width column kept an interactive overlay')
        ''')

    def test_source_and_description_are_bounded_after_inline_links(self):
        self.lua.execute('''
          PD.MAT_X=170;PD.REC_COST_W=100;PD.REC_AH_W=90
          local r=recipeRow();r.b:SetPoint('BOTTOMLEFT',r,'BOTTOMLEFT',190,4)
          r.b:SetText('description');r.d:SetText(string.rep('prefix',30))
          PD.BoundRecipeColumns(r,{dval='a very long vendor name'},32)
          assert(r.b.text=='' and r.b.width==1)
          assert(r.d.width+r.dv.width<=PD.DiffBarW()+PD.REC_COST_W-8)
        ''')


if __name__=='__main__':unittest.main()
