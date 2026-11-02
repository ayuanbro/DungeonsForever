"""Master fishing list retains every stage, water and map action."""
import unittest
import test_prof_ui_fusion as ui
ROOT=ui.ROOT

class FishingRouteUITests(unittest.TestCase):
    setUp=ui.ProfessionUIFusionTests.setUp
    boot=ui.ProfessionUIFusionTests.boot

    def guide(self):
        self.load((ROOT/'Core/Data/Data_ProfFishingRoutes.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute("PD.cur='fishing';PD.Wrap=function(text)return {text}end")

    def test_master_list_preserves_stages_water_details_and_current_range(self):
        self.guide()
        self.lua.execute(LUA_LIST)

    def test_water_rows_keep_map_actions(self):
        self.guide()
        self.lua.execute(LUA_MAP)

    def test_master_fishing_labels_are_translated_in_all_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            self.boot(locale);self.guide()
            self.lua.execute(LUA_LOCALE)

LUA_LIST=r'''
local rows={};assert(PD.RowsFishingLevelRoute(rows,25))
local stages,waters,active=0,0,0
for _,r in ipairs(rows)do
 assert(r.kind~='fishstage' and r.kind~='fishwaters')
 if r.kind=='row' and r.text:find(' – ',1,true) then
  stages=stages+1;assert(r.sub and r.lines)
  if r.nameColor then active=active+1;assert(r.text:find('25',1,true))end
 elseif r.kind=='row' and r.text:find('钓鱼区域：',1,true) then
  waters=waters+1;assert(r.sub and #r.lines==3)
 end
end
assert(stages==4 and waters==17 and active==1,tostring(stages)..'/'..waters..'/'..active)
rows={};PD.RowsFishingLevelRoute(rows,300);active=0
for _,r in ipairs(rows)do
 if r.kind=='row' and r.nameColor then active=active+1;assert(r.text:find('300',1,true))end
end
assert(active==1)
'''

LUA_MAP=r'''
ns.AreaMap={[12]=1429,[215]=1412,[14]=1411,[141]=1438}
C_Map={OpenWorldMap=function(id)opened=id end}
local rows={};PD.RowsFishingLevelRoute(rows,1)
for _,r in ipairs(rows)do if r.act then r.act();break end end
assert(opened==1429)
'''

LUA_LOCALE=r'''
local rows={};assert(PD.RowsFishingLevelRoute(rows,nil))
for _,k in ipairs({'钓鱼升级路线（优先推荐水域）','◆ 推荐当前就练这一档',
 '成功钓获鱼类可提升技能；技能越高，通常需要更多次成功钓获。'})do assert(ns.L[k] and ns.L[k]~='',k)end
'''

if __name__=='__main__':unittest.main()
