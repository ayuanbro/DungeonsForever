# -*- coding: utf-8 -*-
"""把「升级 HUD 路线模式」静态断言同时补进产物 df_dungeon_check.py 与生成器 mk_df_check.py。

同一段断言文本，插在「四个专业数据文件都在 TOC 里」那条之后（static_guard 内、
早于已知的 apiseg 早崩点，必被执行）。两文件均为 LF；mk_df_check.py 的锚点位于 r\"\"\" 原串内，
插入块内不得含三引号。
"""
import io

BLOCK = """    # ── 专业升级 HUD：数据随「固定路线 / 自动计算」模式切换（2026-10-11）──
    #   HUD 与专业页共用同一套自动路线（routeFor 的 opts 逐项对齐 RowsLeveling），
    #   自动不可用（未开 / 没装 Auctionator / 无价快照）一律回落固定路线。
    #   ⚠️ 注释里不许写出被负向断言盯的标识符形态（段表取法的旧写法）。
    pfhud = open(os.path.join(ADDON, 'Core', 'ProfFollow.lua'), encoding='utf-8',
                 errors='replace').read().replace('\\r\\n', '\\n')
    pf_live = '\\n'.join(l.split('--')[0] for l in pfhud.split('\\n'))
    ck('★★ 升级 HUD 路线模式：routeFor（自动门禁 = 设置开 + Auctionator 可用 + 有价，否则回落固定）',
       'local function routeFor(slug, skill)' in pfhud
       and 'PD.Setting("autoRoute") and RA and RA.Available()' in pfhud
       and 'if res and res.priced then return "auto", res.steps end' in pfhud
       and 'return "fixed", (lv and lv.steps) or nil' in pfhud)
    ck('★★ 升级 HUD 路线模式：自动 opts 与专业页逐项一致（起点 / 三个过滤 / 目标按 slug 取）',
       'PD.Setting("autoFromCurrent")' in pfhud and 'PD.Setting("autoOnlyAH")' in pfhud
       and 'PD.Setting("autoNoFormula")' in pfhud and 'PD.Setting("autoLearnedOnly")' in pfhud
       and 'target = routeTarget(slug)' in pfhud)
    ck('★★ 升级 HUD 路线模式：段落 / 购物 / 浏览全走 routeFor（不许再直读固定路线段表）',
       '#lv.steps' not in pf_live and 'LV[s.slug]' not in pf_live
       and pf_live.count('routeFor(s.slug, s.skill)') == 4)
    ck('★★ 升级 HUD 路线模式：段标带模式前缀（自动计算 / 固定路线，复用既有 L 键）',
       '((mode == "auto") and L["自动计算"] or L["固定路线"])' in pf_live
       and 'format(L["段落 %d / %d"], vi, #steps)' in pf_live)
    ck('★★ 升级 HUD 路线模式：配方查找表并入 rinfo（附魔路线全靠它取材料）',
       'if lv and type(lv.rinfo) == "table" then' in pf_live
       and 'local function recMats(rec) return rec and (rec[12] or rec.mats) or nil end' in pf_live
       and 'local function recItem(rec) return rec and (rec[2] or rec.makes) or nil end' in pf_live
       and 'if mats and #mats > 0 then' in pf_live)
"""

ANCHOR = "       [f for f in _profdata if f not in plines])\n"

for p in ("_temp/df_dungeon_check.py", "_temp/mk_df_check.py"):
    s = io.open(p, encoding="utf-8", newline="").read()
    assert "\r\n" not in s, p
    if "升级 HUD 路线模式：routeFor" in s:
        print("SKIP (已插过): %s" % p)
        continue
    assert s.count(ANCHOR) == 1, (p, s.count(ANCHOR))
    s = s.replace(ANCHOR, ANCHOR + BLOCK, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    assert "\r\n" not in s
    print("patched %s" % p)
