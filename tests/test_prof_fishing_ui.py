"""Fish route controls, source separation and real map actions (mocked UI)."""
import unittest
import test_prof_ui_regressions as fixture
from test_prof_ui_regressions import ROOT


class FishingUITests(unittest.TestCase):
    def setUp(self):
        fixture.ProfessionUIRegressions.setUp(self)
        self.lua.execute('''
          config={};ProfDB=function()return config end
          PD.ROW_H=34;PD.ROW_H1=20
          D={pro={cooking={name='Cooking'}}}
          DG.ZoneName=function(id)return 'Zone'..id end
          PushHead=function(rows,text)rows[#rows+1]={text=text}end
          PushGap=function()end
          PD.RequestRender=function()renders=(renders or 0)+1 end
        ''')
        source=(ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        for start,end in (
            ('function PD.CookingFishingMode(', 'function PD.CycleRouteScheme('),
            ('function PD.FishingAreaName(', '-- ── 采集升级路线'),
        ):
            a=source.index(start)
            self.lua.execute(source[a:source.index(end,a+len(start))])

    def test_cooking_mode_button_preserves_global_scheme_and_other_professions(self):
        self.lua.execute('''
          PD.cur='cooking';config.autoScheme='crafts';config.autoRoute=false
          local tools,click=PD.LevelTool();local found=false
          for _,tool in ipairs(tools)do if tool.key=='cooking_fishing'then found=true end end
          assert(found);click('cooking_fishing')
          assert(PD.CookingFishingMode() and config.cookingRoute=='fishing')
          assert(config.autoScheme=='crafts' and not config.autoRoute)
          assert(not PD.CookingFishingMode('alchemy'))
          tools,click=PD.LevelTool();click('cooking_fishing')
          assert(not PD.CookingFishingMode() and config.cookingRoute=='standard')
        ''')

    def test_area_without_coordinates_opens_map_and_never_invents_waypoint(self):
        self.lua.execute('''
          C_Map={OpenWorldMap=function(id)opened=id end}
          PD.MarkMapPoint=function()error('no invented coordinate')end
          local rows={};PD.RowsFishAreas(rows,{{id=6291,count=4,areas={
            {zoneID=12,mapID=1429,minSkill=1,noGetaway=25,name='Pond'}}}})
          local area=rows[2]
          assert(area.text=='钓鱼区域：Pond' and area.sub:find('最低钓鱼技能 1',1,true))
          assert(area.sub:find('不脱钩技能 25',1,true) and area.act)
          area.act();assert(opened==1429)
        ''')

    def test_verified_area_coordinates_keep_waypoint_action(self):
        self.lua.execute('''
          PD.MarkMapPoint=function(map,x,y)point={map,x,y}end
          PD.ShowFishingArea({mapID=1446,x=66,y=22})
          assert(point[1]==1446 and point[2]==66 and point[3]==22)
        ''')

    def test_fishing_route_uses_recommended_water_and_no_guaranteed_skill_claim(self):
        self.lua.execute('''
          ns.ProfFishingRoutes={fishingSteps={{from=25,to=150,fishIDs={6289},
            areas={{zoneID=1519,mapID=1453,name='City',minSkill=1,noGetaway=75}}}}}
          local rows={};assert(PD.RowsFishingLevelRoute(rows,50))
          local active,map=false,false
          for _,r in ipairs(rows)do
            assert(not (r.text or ''):find('下竿必涨',1,true))
            if r.right=='◆ 推荐当前就练这一档'then active=true end
            if r.act then map=true end
          end
          assert(active and map)
        ''')

    def test_own_fish_and_vendor_ingredients_never_enter_auction_import(self):
        self.lua.execute('''
          ns.AuctionBridge={DoImport=function(_,items)imported=items end}
          PD.ShopImport({planVersion=2,scheme='fishing',mats={{id=2678,count=5,source='vendor',vendor=true}},
            fishMaterials={{id=6291,count=20,source='fishing'}},
            formulas={{id=6325,count=1,source='ah'}}})
          assert(#imported==1 and imported[1].name=='Item6325')
        ''')


if __name__=='__main__':
    unittest.main()
