"""Fishing upgrade hierarchy, grouped water actions and recycled native rows."""
import unittest
import test_prof_ui_fusion as ui
from test_prof_issue4 import WIDGETS

ROOT=ui.ROOT


class FishingRouteUITests(unittest.TestCase):
    setUp=ui.ProfessionUIFusionTests.setUp
    boot=ui.ProfessionUIFusionTests.boot

    def guide(self):
        self.load((ROOT/'Core/Data/Data_ProfFishingRoutes.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute("PD.cur='fishing';PD.Wrap=function(text)return {text}end")

    def test_native_guide_has_distinct_stage_headers_and_preserves_every_water(self):
        self.guide()
        self.lua.execute('''
          local rows={};assert(PD.RowsFishingLevelRoute(rows,25))
          local stages,groups,waters,active=0,0,0,0
          for _,r in ipairs(rows)do
            if r.kind=='fishstage' then
              stages=stages+1;assert(r.h>=60 and #r.fishIDs>0 and not r.sub)
              if r.active then active=active+1;assert(r.text:find('25',1,true))end
              assert(r.lines[3][1]~='','practice instructions were lost')
            elseif r.kind=='fishwaters' then
              groups=groups+1;waters=waters+#r.areas;assert(r.requirements~='')
            else assert(r.kind~='row','water choices fell back to the old text list')end
          end
          assert(stages==4 and groups==5 and waters==17 and active==1)
          rows={};PD.RowsFishingLevelRoute(rows,300);active=0
          for _,r in ipairs(rows)do if r.active then active=active+1;assert(r.text:find('300',1,true))end end
          assert(active==1)
        ''')

    def test_rendered_water_buttons_keep_map_actions_and_recycle_cleanly(self):
        self.lua.execute(WIDGETS)
        self.lua.execute('''
          ns.ProfHost.MakeFS=recordedWidget
          ns.ProfHost.NewButton=function(parent,text,w,h)
            local b=recordedWidget();b:SetText(text);b:SetSize(w,h);return b
          end
          ns.ProfHost.DG.ItemIcon=function(id)return 'item:'..id end
          CreateFrame=recordedWidget
        ''')
        self.load((ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('PD=ns.ProfModule')
        self.guide()
        self.lua.execute('''
          PD.HideSkillBar=function()end;PD.PaintCard=function()end
          local row=recordedRow();row:SetWidth(900)
          local rows={};PD.RowsFishingLevelRoute(rows,1)
          local stage,water
          for _,r in ipairs(rows)do if r.kind=='fishstage' and not stage then stage=r
            elseif r.kind=='fishwaters' and not water then water=r end end
          stage.__gw=900;water.__gw=900
          PD.PaintFishingRouteRow(row,stage,stage.h)
          local f=row.__fishRoute
          assert(f.title.text==stage.text and f.fish[1].itemID==6291 and f.fish[1]:IsShown(),
            tostring(f.title.text)..'/'..tostring(stage.text)..'/'..tostring(f.fish[1].itemID)..'/'..tostring(f.fish[1]:IsShown()))
          ns.AreaMap={[12]=1429,[215]=1412,[14]=1411,[141]=1438}
          C_Map={OpenWorldMap=function(id)opened=id end}
          PD.PaintFishingRouteRow(row,water,water.h)
          assert(not f.fish[1]:IsShown() and f.zones[4]:IsShown())
          f.zones[1].scripts.OnClick(f.zones[1]);assert(opened==1429)
          for _,b in ipairs(f.zones)do assert(b.width>0 and b.width<900/4)end
          PD.PaintFishingRouteRow(row,stage,stage.h)
          assert(not f.zones[1]:IsShown() and f.fish[1]:IsShown())
          local original=f;PD.PaintFishingRouteRow(row,stage,stage.h);assert(row.__fishRoute==original)
          -- Offscreen/recycled rows must not retain custom cards.
          PD.ClearMats=function()end;PD.ClearMatSegs=function()end
          PD.WipeRow(row);assert(not f:IsShown())
        ''')

    def test_stage_labels_are_translated_in_all_shipped_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            self.boot(locale);self.guide()
            self.lua.execute('''
              local rows={};assert(PD.RowsFishingLevelRoute(rows,nil))
              for _,k in ipairs({'钓鱼升级路线','技能范围','当前阶段','推荐水域',
                '按技能查看阶段，点击水域打开地图。'})do assert(rawget(ns.L,k),k)end
            ''')


if __name__=='__main__':unittest.main()
