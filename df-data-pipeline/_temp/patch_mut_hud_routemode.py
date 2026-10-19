# -*- coding: utf-8 -*-
"""给 df_mut_check.py 补 3 条「升级 HUD 路线模式」变异（2026-10-11）。

锚点全在 Core/ProfFollow.lua（LF），避开中文以免疫 bytes 字面量的编码坑；
每条断言各自唯一命中（见 _hud_routemode_smoke.py 的静态断言）。
"""
import io

P = "_temp/df_mut_check.py"
s = io.open(P, encoding="utf-8", newline="").read()
assert "\r\n" not in s
if "MUT_HUD_ROUTEMODE_OFF" in s:
    print("SKIP (已插过)")
    raise SystemExit(0)

DEFS = '''# ㊿ 升级 HUD 路线模式（2026-10-11 用户：「专业升级 hud 里面的数据需要根据路线模式进行切换」）。
#   HUD 的数据源随专业页「固定路线 / 自动计算」模式切换（routeFor），自动不可用即回落固定。
#   守护点：① 自动门禁不许失效（永远固定）；② 段标必须带模式前缀；③ 配方查找表必须并 rinfo。
MUT_HUD_ROUTEMODE_OFF = ('Core/ProfFollow.lua', (
    b'    if PD and PD.Setting and PD.Setting("autoRoute") and RA and RA.Available() then\\n',
    b'    if false then  -- MUT: auto gate off (HUD always fixed)\\n'))
MUT_HUD_SEG_NO_MODE = ('Core/ProfFollow.lua', (
    ('    f.seg:SetText(((mode == "auto") and L["自动计算"] or L["固定路线"]) .. " · "\\n'
     '                  .. format(L["段落 %d / %d"], vi, #steps))\\n').encode('utf-8'),
    '    f.seg:SetText(format(L["段落 %d / %d"], vi, #steps))  -- MUT: no mode prefix\\n'.encode('utf-8')))
MUT_HUD_RINFO_GONE = ('Core/ProfFollow.lua', (
    (b'        local lv = LV[slug]\\n'
     b'        if lv and type(lv.rinfo) == "table" then\\n'
     b'            for spell, ri in pairs(lv.rinfo) do\\n'
     b'                if not c[spell] then c[spell] = ri end\\n'
     b'            end\\n'
     b'        end\\n'),
    b'-- MUT: rinfo not merged into the recipe lookup\\n'))

MUTATIONS = ['''

REG = '''    # ㊿ 升级 HUD 路线模式（2026-10-11 用户）
    ('升级 HUD：自动门禁失效（永远固定路线）', MUT_HUD_ROUTEMODE_OFF),
    ('升级 HUD：段标掉模式前缀（数据换了看不出）', MUT_HUD_SEG_NO_MODE),
    ('升级 HUD：配方查找表不并 rinfo（附魔段「材料未收录」）', MUT_HUD_RINFO_GONE),
]'''

assert s.count("MUTATIONS = [") == 1
s = s.replace("MUTATIONS = [", DEFS, 1)

# 注册：插到 MUTATIONS 列表末尾（原 ㉚ 两条之后）
assert s.count("\n]\n\n\ndef file_is_crlf(") == 1
s = s.replace("\n]\n\n\ndef file_is_crlf(",
              "\n" + REG + "\n\n\ndef file_is_crlf(", 1)

io.open(P, "w", encoding="utf-8", newline="").write(s)
assert "\r\n" not in s
print("patched df_mut_check.py")
