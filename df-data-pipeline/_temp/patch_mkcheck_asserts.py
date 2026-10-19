# -*- coding: utf-8 -*-
"""把 mk_df_check.py（df_dungeon_check.py 的生成器）里同一批断言同步改掉。

背景：注释精简后，断言里用「代码 + 行尾注释」消歧的老写法全部落空。
改法与我直接改 df_dungeon_check.py 时**完全一致**（复合代码锚），保持四处同步。
"""
import io

P = 'mk_df_check.py'
src = io.open(P, encoding='utf-8', newline='').read()

REPS = [
    # ① 探索页筛选钮描边
    ("""'MakeOutline(bt, 1, 0.82, 0)   -- ★ 描边必须显式建' in exui""",
     """'MakeOutline(bt, 1, 0.82, 0)\\n        bt:SetScript("OnEnter", function(self)' in exui"""),
    # ② 营地引导空档 + 摘掉纯注释文本条件
    ("""'PushGap(rows, 6)   -- 引导空档：首卡 bbox 外扩 SEC_PAD 后不越滚动区上缘' in profui""",
     """'    PushGap(rows, 6)\\n    PushHead(rows, L["三档营地物件' in profui"""),
    ("""       and '三档合一卡' in profui\n""", ""),
    # ③ 升级分段行 r.f 收干净
    ("""    #   ⚠️ 必须连 8 空格缩进 + 尾部注释一起查 `r.f:SetText("")`：配方页那一支是同一句的\n    #      4 空格缩进版，短串断言会恒真白测（本项目踩过的坑）。""",
     """    #   ⚠️ 必须连 8 空格缩进 + **紧随的下一句**一起查 `r.f:SetText("")`：配方页那一支是同一句的\n    #      4 空格缩进版，短串断言会恒真白测（本项目踩过的坑）。\n    #      （注释精简后尾注没了，靠下一句 `r.a:ClearAllPoints()` 消歧，强度不变。）"""),
    ("""'        r.f:SetText("")          -- 分段行不再用材料串那颗字体串' in profui""",
     """'        r.f:SetText("")\\n        r.a:ClearAllPoints()' in profui"""),
    # ④ 设置页 setOpen 两处
    ("""'    PD.setOpen = false              -- 点任何子页签都先收起设置页' in profui""",
     """'function PD.SetTab(key)\\n    PD.setOpen = false' in profui"""),
    ("""'        PD.setOpen = false  -- 换专业 = 导航离开设置页' in profui)""",
     """'        PD.tab = "overview"\\n        PD.setOpen = false' in profui)"""),
    # ⑤ iOS 开关摆位
    ("""'    PD.PlaceSettingsToggles(rows)   -- 设置页 iOS 开关摆位（非设置页全收）' in profui""",
     """'    PD.PlaceSettingsToggles(rows)\\n    PD.scroll:SetVerticalScroll(0)' in profui"""),
]

for old, new in REPS:
    c = src.count(old)
    print('  x%d  %s' % (c, old.replace('\n', ' / ')[:78]))
    assert c == 1, '命中数不为 1：%r' % old[:60]
    src = src.replace(old, new, 1)

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('\nmk_df_check.py 已同步 %d 处' % len(REPS))

# 复核：还有没有残留的「代码 + 行尾注释」断言
import re
left = [l for l in src.split('\n') if re.search(r"'[^']*--[^']*' in (exui|profui|src)", l)]
print('残留「代码+注释」断言：%d 处' % len(left))
for l in left:
    print('   ', l.strip()[:100])
