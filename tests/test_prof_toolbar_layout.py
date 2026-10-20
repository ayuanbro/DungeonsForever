"""Check the real toolbar placement against visible HUD/import hit rectangles."""
import os
from pathlib import Path
import sys
import unittest

for path in (Path(os.environ.get("TEMP", "/tmp")) / "df-lua-runtime",
             Path.home() / "AppData/Local/Temp/df-lua-runtime"):
    sys.path.insert(0, str(path))
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class ProfessionToolbarLayoutTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(r'''
          PD={RIGHT_X=180,RIGHT_W=800,LIST_PAD=8,BODY_TOP=46,TOOL_H=22,
              TOOL_GAP=8,TOOL_BODY_GAP=8,TOOL_MAX=20,tab='leveling',page={},
              CARD_INSET=8,CARD_TOP=8,BODY_BOT=16}
          C_WHITE={1,1,1};C_GOLD={1,.82,0};C_GREY={.5,.5,.5};Unpack=unpack
          SetOutline=function()end
          function PD.TextW(text,fs)
            local size,i=0,1
            while i<=#text do
              local byte=text:byte(i)
              if byte<128 then size=size+fs*.55;i=i+1
              else size=size+fs;i=i+(byte<224 and 2 or byte<240 and 3 or 4)end
            end
            return size
          end
          function PD.Fit(text,fs,width)
            if PD.TextW(text,fs)<=width then return text end
            local i=1
            while i<=#text do
              local byte=text:byte(i)
              local step=byte<128 and 1 or byte<224 and 2 or byte<240 and 3 or 4
              if PD.TextW(text:sub(1,i+step-1)..'...',fs)>width then break end
              i=i+step
            end
            return text:sub(1,i-1)..'...'
          end
          PD.SearchReserve=function()return PD.tab=='recipe' and 190 or 0 end
          function frame(text,shown)
            return {
              text=text or '',shown=shown or false,points={},width=100,height=22,
              SetSize=function(self,w,h)self.width=w;self.height=h end,
              SetWidth=function(self,w)self.width=w end,
              GetWidth=function(self)return self.width end,
              GetText=function(self)return self.text end,
              SetText=function(self,text)self.text=text end,
              ClearAllPoints=function(self)self.points={}end,
              SetPoint=function(self,...)self.points[#self.points+1]={...}end,
              IsShown=function(self)return self.shown end,
              Show=function(self)self.shown=true end,
              Hide=function(self)self.shown=false end,
              EnableMouse=function()end,
              GetFontString=function()return {SetTextColor=function()end}end,
            }
          end
          PD.WarnChip=function(bt)
            if not bt.__warn then bt.__warn=frame();bt.__warn.width=26 end
            return bt.__warn
          end
          PD.hudBtn=frame('工程学升级HUD',true)
          PD.impBtn=frame('一键导入购物清单',true)
          PD.toolBtns={}
          for i=1,PD.TOOL_MAX do PD.toolBtns[i]=frame()end
          PD.scroll=frame();PD.listCard=frame();PD.divider=frame()
          function actionList(english,extra)
            local labels=english and {'Route','Shopping list','Recalculate','Supplies',
              'Calculate supplies','Crafting history','Manage exclusions','Stop optimizing'}
              or {'路线','购物清单','重新计算','补料清单','计算补料','制作记录','管理排除','停止优化'}
            local out={}
            for i,label in ipairs(labels)do out[#out+1]={key=tostring(i),text=label}end
            if extra then
              out[#out+1]={key='partner',text=english and 'Partner profession' or '搭配专业'}
              out[#out+1]={key='restore',text=english and 'Restore all' or '全部恢复'}
              out[#out+1]={key='fishing',text=english and 'Fishing route' or '纯钓鱼'}
            end
            return out
          end
          function assertLayout()
            local boxes={}
            for _,bt in ipairs(PD.toolBtns)do
              if bt:IsShown()then
                local p=assert(bt.points[1]);local w=bt.width
                if bt.__warn and bt.__warn:IsShown()then w=w+28 end
                boxes[#boxes+1]={x=p[4],y=-p[5],w=w,h=bt.height,key=bt.__key}
              end
            end
            for _,key in ipairs({'hudBtn','impBtn'})do
              local bt=PD[key]
              if bt and bt:IsShown()then
                local p=assert(bt.points[1])
                boxes[#boxes+1]={x=p[4],y=-p[5],w=bt.width,h=bt.height,key=key}
              end
            end
            local bottom=0
            for i,a in ipairs(boxes)do
              assert(a.x>=PD.RIGHT_X and a.x+a.w<=PD.RIGHT_X+PD.RIGHT_W-PD.LIST_PAD+.001,
                'toolbar control escaped content width: '..tostring(a.key))
              bottom=math.max(bottom,a.y+a.h)
              for j=i+1,#boxes do
                local b=boxes[j]
                assert(not(a.x<b.x+b.w and b.x<a.x+a.w and a.y<b.y+b.h and b.y<a.y+a.h),
                  'overlapping toolbar controls: '..tostring(a.key)..' / '..tostring(b.key))
              end
            end
            assert(-PD.scroll.points[1][5]>bottom,'list starts above the last toolbar control')
            return boxes
          end
          function paint(list,yoff)
            yoff=yoff or 46
            local height=PD.PaintTool(list,function()end,yoff)
            PD.Layout(yoff+height)
            assertLayout()
            return height
          end
        ''')
        source = (ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        for start, end in (
            ('PD.TOOL_MIN_W, PD.TOOL_MAX_W =', '-- ── 升级页信息卡'),
            ('function PD.Layout(', 'PD.SWEEP_AT ='),
        ):
            a = source.index(start)
            self.lua.execute(source[a:source.index(end, a + len(start))])

    def test_shop_actions_wrap_before_import_and_hud(self):
        self.lua.execute('''
          local list=actionList(false)
          list[#list+1]={key='head',plain=true,text='1 → 225 自动路线（材料采购）'}
          paint(list)
          assert(PD.toolRows>=2,'eight actions were squeezed behind fixed controls')
          assert(PD.toolBtns[8].__key=='8' and PD.toolBtns[8]:IsShown())
        ''')

    def test_languages_professions_and_narrow_widths_never_overlap(self):
        self.lua.execute('''
          for _,width in ipairs({900,760,540,320,128})do
            for _,name in ipairs({'工程学升级HUD','裁缝升级HUD','急救升级HUD',
              'Engineering Leveling HUD','Blacksmithing Leveling HUD','烹飪升級HUD'})do
              PD.RIGHT_W=width
              PD.hudBtn:SetText(name)
              PD.impBtn:SetText(name:find('HUD',1,true) and 'Import shopping list' or '一键导入购物清单')
              paint(actionList(true,true))
              PD.impBtn:SetText('一鍵匯入購物清單')
              paint(actionList(false,true))
            end
          end
        ''')

    def test_right_actions_can_take_separate_rows_and_left_buttons_skip_full_rows(self):
        self.lua.execute('''
          PD.RIGHT_W=200
          PD.hudBtn:SetText('Blacksmithing Leveling HUD')
          PD.impBtn:SetText('Import shopping list')
          paint({{key='stop',text='Stop optimizing'}})
          assert(PD.hudBtn.points[1][5]>PD.impBtn.points[1][5])
          assert(PD.toolBtns[1].points[1][5]<PD.impBtn.points[1][5])
          assert(PD.toolRows==3)
        ''')

    def test_import_visibility_releases_width_and_list_height(self):
        self.lua.execute('''
          PD.RIGHT_W=420
          local list={{key='route',text='路线'},{key='shop',text='购物清单'},
            {key='recalc',text='重新计算'}}
          local crowded=paint(list);assert(PD.toolRows==2)
          PD.impBtn:Hide()
          local released=paint(list);assert(PD.toolRows==1 and released<crowded)
        ''')

    def test_fixed_controls_keep_list_clear_even_without_left_actions(self):
        self.lua.execute('''
          PD.RIGHT_W=200
          PD.hudBtn:SetText('Blacksmithing Leveling HUD')
          PD.impBtn:SetText('Import shopping list')
          paint({})
          assert(PD.toolRows==2)
          PD.hudBtn=nil
          paint({})
          assert(PD.toolRows==1,'standalone import was skipped with a missing HUD button')
        ''')

    def test_recipe_search_reserve_and_tab_offset_are_preserved(self):
        self.lua.execute('''
          PD.tab='recipe';PD.hudBtn:Hide();PD.impBtn:Hide();PD.RIGHT_W=420
          local list={{key='same',text='Route'}}
          paint(list,0)
          local recipeY=PD.toolBtns[1].points[1][5]
          assert(PD.toolBtns[1].points[1][4]+PD.toolBtns[1].width<=
            PD.RIGHT_X+PD.RIGHT_W-PD.LIST_PAD-190)
          PD.tab='leveling'
          paint(list,46)
          assert(PD.toolBtns[1].points[1][5]==recipeY-46,'cached anchor retained another tab offset')
        ''')

    def test_long_plain_title_includes_warning_hit_area_in_its_width(self):
        self.lua.execute('''
          PD.RIGHT_W=320
          local list=actionList(false)
          list[#list+1]={key='head',plain=true,text=string.rep('Very long route description ',10),
            warn={{'Keep this warning accessible'}}}
          paint(list)
          local bt=PD.toolBtns[#list]
          assert(bt.__warn:IsShown())
          assert(bt.width+28<=PD.RIGHT_W-PD.LIST_PAD)
          assert(bt:GetText()~=list[#list].text,'unbounded route title was not fitted')
        ''')

    def test_repaint_restores_fitted_action_width_after_profession_label_refresh(self):
        self.lua.execute('''
          PD.RIGHT_W=200
          local full='Blacksmithing Leveling HUD'
          PD.hudBtn:SetText(full);paint(actionList(true))
          local fitted=PD.hudBtn:GetText()
          assert(fitted~=full)
          PD.hudBtn:SetText(full);PD.hudBtn:SetWidth(PD.TextW(full,13)+22)
          paint(actionList(true))
          assert(PD.hudBtn:GetText()==fitted and PD.hudBtn:GetWidth()<=192)
        ''')


if __name__ == '__main__':
    unittest.main()
