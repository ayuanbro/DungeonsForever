"""Selected scheme controls redraw independently of the saved route snapshot."""
import unittest

import test_prof_ui_regressions as fixture


class SchemeUITests(unittest.TestCase):
    def setUp(self):
        fixture.ProfessionUIRegressions.setUp(self)
        self.lua.execute('''
          config={autoScheme='matcost',autoRoute=true}
          ProfDB=function()return config end
          PD.SETTING_DEF={autoScheme='cheapest'}
          PD.Setting=function(key)return config[key] and true or false end
          PD.tab='leveling';PD.setOpen=false
          PD.IsGatherRoute=function()return false end
          PD.LvTarget=function()return 225 end
          PD.RIGHT_W=900;PD.LIST_PAD=8;PD.LV_TILE_GAP=8
          PD.RIGHT_X=10;PD.BODY_TOP=20;PD.LV_TILE_H=40
          PD.page={}
          Unpack=unpack;C_WHITE={1,1,1};C_GOLD={1,.82,0}
          PD.PaintTileBorder=function()end
          PD.TipTile=function(tile,lines)tile.lines=lines end
          function field()
            return {SetText=function(self,text)self.text=text end,
              SetTextColor=function(self,...)self.color={...}end}
          end
          function tile()
            return {label=field(),val=field(),scripts={},
              SetScript=function(self,key,fn)self.scripts[key]=fn end,
              SetWidth=function(self,width)self.width=width end,
              GetWidth=function(self)return self.width end,
              ClearAllPoints=function()end,SetPoint=function()end,
              Show=function(self)self.shown=true end,
              Hide=function(self)self.shown=false end}
          end
          PD.lvTiles={mode=tile(),scheme=tile(),cost=tile(),target=tile(),snap=tile()}
          invalidates,renders,sounds=0,0,0
          RA.Invalidate=function()invalidates=invalidates+1 end
          RA.Recalculate=function()error('scheme click recalculated the route')end
          RA.Compute=function()error('scheme click computed a replacement route')end
          PD.RequestRender=function()renders=renders+1;PD.PaintLvTiles()end
          ns.PlaySound=function()sounds=sounds+1 end
          function hasLine(lines,text)
            for _,line in ipairs(lines)do if line[1]==text then return true end end
            return false
          end
          pendingText='已保存路线；数据或设置已变化，点击重新计算更新。'
          optimisticText='乐观计数：花费按卖店价值粗算，不是拍卖行行情'
          function assertSelection(scheme)
            assert(PD.lvTiles.scheme.val.text==RA.SchemeLabel(scheme),
              'scheme card still displays the saved route scheme')
            local highlighted=0
            for i,key in ipairs(RA.SchemeOrder())do
              local line=PD.lvTiles.scheme.lines[i]
              if line[2]==1 and line[3]==.82 and line[4]==0 then
                highlighted=highlighted+1;assert(key==scheme,'wrong scheme highlighted')
              end
            end
            assert(highlighted==1,'selected scheme has no unique tooltip highlight')
          end
        ''')
        source = (fixture.ROOT / 'Core/ProfRouteAuto.lua').read_text(encoding='utf-8-sig')
        a = source.index('local SCHEME_ORDER =')
        self.lua.execute(source[a:source.index('-- ── 拍卖行价格插件可用性与价格层', a)])
        source = (fixture.ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        for start, end in (
            ('function PD.SettingRaw(', '-- 采集页子模式'),
            ('function PD.PaintLvTiles(', 'function PD.Layout('),
        ):
            a = source.index(start)
            self.lua.execute(source[a:source.index(end, a + len(start))])

    def test_repeated_clicks_redraw_selected_scheme_without_replacing_cached_route(self):
        self.lua.execute('''
          local steps={{1,225,101,20}}
          local plan={scheme='matcost',total=100,steps=steps}
          PD.lvSummary={auto=true,autoSetting=true,ahOK=true,scheme=plan.scheme,
            total=plan.total,priced=true,target=225,planVersion=2,status='complete'}
          local summary=PD.lvSummary
          PD.PaintLvTiles();assertSelection('matcost')
          assert(not hasLine(PD.lvTiles.scheme.lines,pendingText))
          for i,selected in ipairs({'crafts','optim','cheapest','matcost','crafts'})do
            PD.lvTiles.scheme.scripts.OnClick()
            assert(config.autoScheme==selected);assertSelection(selected)
            assert(invalidates==i and renders==i and sounds==i)
            assert(PD.lvSummary==summary and summary.scheme=='matcost' and summary.total==100)
            assert(plan.scheme=='matcost' and plan.total==100 and plan.steps==steps)
            assert(PD.lvTiles.cost.val.text=='100' and PD.lvTiles.cost.val.color[1]==1)
            assert(not hasLine(PD.lvTiles.cost.lines,optimisticText),
              'pending optimistic selection relabeled the saved material cost')
            assert(hasLine(PD.lvTiles.scheme.lines,pendingText)==(selected~='matcost'))
          end
        ''')

    def test_legacy_optimistic_result_keeps_cost_and_snapshot_meaning(self):
        self.lua.execute('''
          config.autoScheme='cheapest'
          PD.lvSummary={auto=true,autoSetting=true,ahOK=true,scheme='optim',
            total=321,priced=true,snapshotAge=75,target=225}
          PD.PaintLvTiles();assertSelection('cheapest')
          assert(PD.lvTiles.cost.val.text=='321')
          assert(PD.lvTiles.cost.val.color[1]==C_GREY[1])
          assert(hasLine(PD.lvTiles.cost.lines,optimisticText))
          assert(PD.lvTiles.snap.val.text=='乐观计数 · 不依赖价格插件')
          assert(hasLine(PD.lvTiles.scheme.lines,pendingText),
            'legacy cached route does not explain that the new selection needs recalculation')
          assert(PD.lvSummary.scheme=='optim' and PD.lvSummary.total==321)
        ''')

    def test_fixed_mode_shows_saved_preference_without_pending_route_warning(self):
        self.lua.execute('''
          config.autoRoute=false;config.autoScheme='crafts'
          PD.lvSummary={auto=false,autoSetting=false,priced=true,total=50,target=225}
          PD.PaintLvTiles();assertSelection('crafts')
          assert(not hasLine(PD.lvTiles.scheme.lines,pendingText))
          assert(PD.lvTiles.scheme.scripts.OnClick==PD.CycleRouteScheme)
          assert(invalidates==0 and renders==0 and sounds==0)
        ''')

    def test_missing_preference_uses_default_even_with_another_cached_scheme(self):
        self.lua.execute('''
          config.autoScheme=nil
          PD.lvSummary={auto=true,autoSetting=true,ahOK=true,scheme='matcost',
            total=50,priced=true,target=225}
          PD.PaintLvTiles();assertSelection('cheapest')
          assert(config.autoScheme==nil and PD.lvSummary.scheme=='matcost')
        ''')

    def test_fishing_mode_keeps_own_label_and_disables_scheme_cycle(self):
        self.lua.execute('''
          PD.cur='cooking';config.cookingRoute='fishing';config.autoScheme='crafts'
          PD.lvSummary={auto=true,autoSetting=true,ahOK=true,scheme='fishing',
            total=50,priced=true,target=225,planVersion=2,status='complete'}
          PD.PaintLvTiles()
          assert(PD.lvTiles.scheme.label.text=='路线方案')
          assert(PD.lvTiles.scheme.val.text=='鱼类路线')
          assert(PD.lvTiles.scheme.scripts.OnClick==nil)
          assert(#PD.lvTiles.scheme.lines==3)
          assert(not hasLine(PD.lvTiles.scheme.lines,pendingText))
          PD.CycleRouteScheme()
          assert(config.autoScheme=='crafts' and config.cookingRoute=='fishing')
          assert(invalidates==0 and renders==0 and sounds==0)
        ''')


if __name__ == '__main__':
    unittest.main()
