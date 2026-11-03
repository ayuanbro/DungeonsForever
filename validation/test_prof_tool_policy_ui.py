"""Tool route badges, shopping labels and policy help in the native UI.

Uses actual Lua row builders with widget stubs; this does not claim in-game
visual acceptance or exercise the solver's buy-versus-craft decision.
"""
import unittest

import test_prof_ui_fusion as ui


LOCALES = ('zhCN', 'zhTW', 'enUS')
TOOL_HELP = {
    'zhCN': (
        '自动备齐升级所需的专业工具，已有工具不重复准备。',
        '开启：每种必需工具至少备齐一件；比较购买和制作，购买进入购物清单，制作进入升级路线。',
        '关闭：不额外安排工具准备；工具配方仍可作为普通升级配方参与计算。',
    ),
    'zhTW': (
        '自動備齊升級所需的專業工具，已有工具不重複準備。',
        '開啟：每種必需工具至少備齊一件；比較購買和製作，購買進入購物清單，製作進入升級路線。',
        '關閉：不額外安排工具準備；工具配方仍可作為普通升級配方參與計算。',
    ),
    'enUS': (
        'Prepares the profession tools needed for leveling without replacing tools you already own.',
        'On: prepare at least one of each required tool; compare buying and crafting. '
        'Purchases go on the shopping list; crafts go in the leveling route.',
        'Off: do not add tool preparation; tool recipes can still be considered as normal leveling recipes.',
    ),
}


class ToolPolicyUITests(unittest.TestCase):
    boot = ui.ProfessionUIFusionTests.boot

    def prepare(self, locale):
        self.boot(locale)
        self.lua.execute('''
          PD.Wrap=function(text)return {text}end
        ''')

    def test_tradable_tool_badge_is_omitted_and_other_route_badges_remain(self):
        for locale in LOCALES:
            with self.subTest(locale=locale):
                self.prepare(locale)
                self.lua.execute('''
                  local plan=finish('alchemy',{snapshot=fixture(),start=1,target=3})
                  assert(#plan.steps==1)
                  local step=plan.steps[1]
                  step.tool=true;step.toolItem=10
                  step.tags={leveling=true,material=true};step.role='both'
                  ns.ProfRouteAuto.Get=function()return plan end
                  PD.autoPage='route'
                  local function routeRow(owned,bop)
                    PD.ToolOwned=function()return owned end
                    step.toolBop=bop
                    local rows={};PD.RowsLeveling(rows)
                    local found
                    for _,row in ipairs(rows)do if row.lvstep then
                      assert(not found,'unexpected extra route row');found=row
                    end end
                    return assert(found,'tool craft disappeared from the route')
                  end
                  local tradable=routeRow(false,false)
                  assert(not tradable.toolChip,'tradable tool craft still has a purchase badge')
                  assert(tradable.roleChip.text==ns.L['中间产物'])
                  local owned=routeRow(true,false)
                  assert(owned.toolChip.text==ns.L['已拥有'])
                  assert(owned.roleChip.text==ns.L['中间产物'])
                  local bop=routeRow(false,true)
                  assert(bop.toolChip.text==ns.L['BoP 制作'])
                  assert(bop.roleChip.text==ns.L['中间产物'])
                ''')

    def test_shopping_tool_label_keeps_purchase_source_and_count(self):
        for locale in LOCALES:
            with self.subTest(locale=locale):
                self.prepare(locale)
                self.lua.execute('''
                  PD.shopGroup=false
                  local data={planVersion=2,total=12,vendorTotal=5,ahTotal=7,
                    mats={{id=20,count=1,cost=7,source='ah',tool=true},
                          {id=21,count=1,cost=5,source='vendor',tool=true}}}
                  local rows={};PD.RowsAutoShop(rows,data)
                  local seen={}
                  for _,row in ipairs(rows)do if row.purchaseSource then
                    assert(row.tag.text==ns.L['工具'])
                    assert(row.purchaseCount==1)
                    assert(row.purchaseCost==(row.purchaseSource=='ah' and 7 or 5))
                    local toolHint=false
                    for _,line in ipairs(row.lines or {})do
                      if line[1]==ns.L['这是路线所需的工具，购买或制成后保留使用，不会消耗。'] then
                        toolHint=true
                      end
                    end
                    assert(toolHint,'shopping tool explanation disappeared')
                    seen[row.purchaseSource]=true
                  end end
                  assert(seen.ah and seen.vendor,'a tool purchase source disappeared')
                ''')

    def test_settings_show_buy_or_craft_policy_in_all_three_locales(self):
        for locale in LOCALES:
            with self.subTest(locale=locale):
                self.prepare(locale)
                rows = self.lua.eval('''function()
                  local rows={};PD.RowsSettings(rows)
                  for _,row in ipairs(rows)do
                    if row.togKey=='autoCraftTools' then return row.help end
                  end
                  error('tool policy setting disappeared')
                end''')()
                self.assertEqual(tuple(rows[i][1] for i in (2, 3, 4)), TOOL_HELP[locale])
                if locale != 'zhCN':
                    for key in TOOL_HELP['zhCN']:
                        self.assertIsNotNone(self.lua.eval('function(k)return rawget(ns.L,k)end')(key))


if __name__ == '__main__':
    unittest.main()
