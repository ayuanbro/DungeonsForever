# -*- coding: utf-8 -*-
"""第八刀（rev14）：**纯探针加细**，不动产品行为。

为什么不动产品：13:42 实机把第七刀的前提证伪了。
  · 13:42「点页签 recipe」= 66.0ms，其中 工具P **26.3ms**（比第七刀前的 22.2 还高）。
  · 闸门一开（setter 行同时出现 SetPoint 18 · SetSize 16 · Show 16）那 16 颗工具按钮
    就吃 21~26ms ⇒ **1.3~1.6ms/颗**；而闸门里全是微秒级 setter。
  · 回头读改动前的 `_temp/_bak13_Hui.lua`：TryBuild **早已**被 `tryBuildOnce` 的
    `if not borderFrame then` 守着，而且 `ns.hui.SkinButton` 开头还有 `bt.__huiAction`
    幂等闸、`ns.CreateButton` 一辈子只调一次 ⇒ **「每次 SetSize 都建帧」根本不成立**，
    第七刀在 Hui 上做的是**功能空转**（多了个同义判断，行为不变）。
  · 所以 26.3ms **另有其物**，而闸门里每一样都便宜 ⇒ 只能**实测拆开**（项目铁律：
    不准读代码猜耗时段）。

本补丁（全部只在探针层）：
  A    Core/Hui.lua —— `ns.hui.__tryBuilds` 计数（看 SetSize 钩子到底有没有进 TryBuild）。
  B/C  Core/ProfessionUI.lua —— PD.PaintTool 闸门内部切四刀：
         闸-尺寸(SetSize) / 闸-锚点(ClearAllPoints+SetPoint) / 闸-文本(SetText+描边+色) /
         闸-显示(Show)，外加 闸-合计 兜总数。
       ★ 计时器 **运行期动态取**（PD.__pfT0 / PD.__pfMark），不许加载期抓局部
         （第七刀踩过：抓局部 ⇒ 探针运行期替换失效）。
       ★ 用 pfNow() 起止（桩安全），不用 GetTime()。
  D/E  探针 PF_TB0 入场快照。
  F    PD.__pfT0 / PD.__pfMark 定义。
  G    pfEnd：把「皮按钮边框帧」那行从「sk>0 才打」改成**无条件打印 + rev14 版本号**
       （否则实机看不到它时无法区分「本版没加载」与「加载了但没建帧」），
       并追加一行「工具闸门」四项分解。
  H/I  双 harness 各加 1 条断言（切片 _ptlive 只在 PD.PaintTool 体内，注释已剥）。
  J/K/L 变异定义 + 登记 + DEFAULT_WANT（摘掉闸-尺寸那行 ⇒ 断言必红）。

★ 插入型改动（新串含旧串）⇒ 幂等靠**哨兵串**判，不靠 count(old)。
"""

import sys

HUI = 'Core/Hui.lua'
PROF = 'Core/ProfessionUI.lua'
CHECK = '_temp/df_dungeon_check.py'
MK = '_temp/mk_df_check.py'
MUT = '_temp/df_mut_check.py'
WANT = '_temp/df_check_new_muts.py'

# ────────────────────────────── Core/Hui.lua ──────────────────────────────

OLD_TB = ("            if borderFrame then return end\n"
          "            local w, h = bt:GetWidth() or 0, bt:GetHeight() or 0\n")

NEW_TB = ("            -- ★ 第八刀（rev14）：计数给探针 —— 看工具行闸门里那 16 次 SetSize\n"
          "            --   到底有没有真的走进这条链（第七刀时只能靠猜）。\n"
          "            ns.hui.__tryBuilds = (ns.hui.__tryBuilds or 0) + 1\n"
          "            if borderFrame then return end\n"
          "            local w, h = bt:GetWidth() or 0, bt:GetHeight() or 0\n")

# ────────────────────────── Core/ProfessionUI.lua ──────────────────────────

# B：函数顶部取一次计时器（运行期动态取；探针关时 __pfT0 返回 nil）
OLD_TOP = ("    yoff = yoff or 0\n"
           "    local n = math.min(#list, PD.TOOL_MAX)\n")

NEW_TOP = ("    yoff = yoff or 0\n"
           "    -- ★ 第八刀（rev14）：闸门内部计时。**运行期动态取**（PD.__pfT0/__pfMark 定义在\n"
           "    --   文件尾探针区），探针关时 __pfT0 返回 nil ⇒ 热路径一次取样都不做。\n"
           "    local _T0, _MK = PD.__pfT0, PD.__pfMark\n"
           "    local n = math.min(#list, PD.TOOL_MAX)\n")

# C：闸门内部四刀
OLD_GATE = ("                bt:SetSize(w, PD.TOOL_H)\n"
            "                bt:ClearAllPoints()\n"
            "                bt:SetPoint(\"TOPLEFT\", PD.page, \"TOPLEFT\", PD.RIGHT_X + x,\n"
            "                            -(PD.BODY_TOP + yoff + row * (PD.TOOL_H + PD.TOOL_GAP)))\n"
            "                bt:SetText(text)\n"
            "                SetOutline(bt, def.on and true or false, 1, 0.82, 0)\n"
            "                bt:GetFontString():SetTextColor(Unpack(def.on and C_GOLD or C_GREY))\n"
            "                bt:Show()\n")

NEW_GATE = ("                -- ★★ 第八刀（rev14）：把闸门切成四刀。实机 16 颗 = 21~26ms，\n"
            "                --   而这里每一样按 bench 单价都是微秒级 ⇒ 必须实测找真凶\n"
            "                --   （项目铁律：不准读代码猜耗时段）。_m0 为 nil 时 _MK 会自己早退。\n"
            "                local _m0 = _T0 and _T0()\n"
            "                local _g0 = _m0\n"
            "                bt:SetSize(w, PD.TOOL_H)\n"
            "                if _MK then _MK(\"闸-尺寸\", _m0) end\n"
            "                _m0 = _T0 and _T0()\n"
            "                bt:ClearAllPoints()\n"
            "                bt:SetPoint(\"TOPLEFT\", PD.page, \"TOPLEFT\", PD.RIGHT_X + x,\n"
            "                            -(PD.BODY_TOP + yoff + row * (PD.TOOL_H + PD.TOOL_GAP)))\n"
            "                if _MK then _MK(\"闸-锚点\", _m0) end\n"
            "                _m0 = _T0 and _T0()\n"
            "                bt:SetText(text)\n"
            "                SetOutline(bt, def.on and true or false, 1, 0.82, 0)\n"
            "                bt:GetFontString():SetTextColor(Unpack(def.on and C_GOLD or C_GREY))\n"
            "                if _MK then _MK(\"闸-文本\", _m0) end\n"
            "                _m0 = _T0 and _T0()\n"
            "                bt:Show()\n"
            "                if _MK then _MK(\"闸-显示\", _m0) end\n"
            "                if _MK then _MK(\"闸-合计\", _g0) end\n")

# D：探针声明
OLD_DECL = "local PF_SKIN0 = nil              -- ★ 第七刀：皮按钮「圆角边框帧重建」的入口快照\n"
NEW_DECL = (OLD_DECL +
            "local PF_TB0 = nil                -- ★ 第八刀：TryBuild 调用次数的入口快照\n")

# E：入场快照
OLD_BEGIN = "        PF_SKIN0 = (ns.hui and ns.hui.__skinBuilds) or 0\n"
NEW_BEGIN = (OLD_BEGIN +
             "        PF_TB0 = (ns.hui and ns.hui.__tryBuilds) or 0\n")

# F：记号器定义（挂在 pfOut 之后）
OLD_PFOUT = "local function pfOut(s) print(\"|cff46bf72[DF性能]|r \" .. s) end\n"
NEW_PFOUT = (OLD_PFOUT +
             "\n"
             "-- ★★ 第八刀（rev14）：工具行闸门内部切刀用的记号器。\n"
             "--   PD.PaintTool 在**热路径**上 ⇒ 探针关（不在入口里）时 __pfT0 返回 nil，\n"
             "--   闸门里一次 pfNow 都不调。起止都用 pfNow()（桩安全），不用 GetTime()。\n"
             "--   ★ 必须**运行期动态取**：第七刀把 DG.ItemName 在加载期抓成局部，探针\n"
             "--     运行期替换就再也不生效（审计全红），这里不能重犯。\n"
             "function PD.__pfT0()\n"
             "    if not PF_SUB then return nil end\n"
             "    return pfNow()\n"
             "end\n"
             "\n"
             "function PD.__pfMark(tag, t0)\n"
             "    if not PF_SUB or not t0 then return end\n"
             "    local dt = pfNow() - t0\n"
             "    local e = PF_SUB[tag]\n"
             "    if e then e[1] = e[1] + 1; e[2] = e[2] + dt\n"
             "    else PF_SUB[tag] = { 1, dt } end\n"
             "end\n")

# G：pfEnd 打印（无条件 + rev + 闸门分解）
OLD_END = ("    -- ★ 第七刀：这一段入口内「皮按钮圆角边框帧」被重建了几副（每次 8 个新纹理）。\n"
           "    --   改动前工具行每次换文案/宽度 = 每颗一次 SetSize = 每颗两副 ⇒ 20 颗 ≈ 20ms。\n"
           "    local sk = ((ns.hui and ns.hui.__skinBuilds) or 0) - (PF_SKIN0 or 0)\n"
           "    if sk > 0 then\n"
           "        pfOut(string.format(\"  └ 皮按钮边框帧重建：%d 次（SetSize 一次就是一次建帧）\", sk))\n"
           "    end\n")

NEW_END = ("    -- ★★ 第八刀（rev14）：**无条件**打印 + 版本号。\n"
           "    --   第七刀把这一行写成「sk>0 才打」⇒ 实机看不到它时**无法区分**\n"
           "    --   「这一版没加载」与「加载了但一副边框帧都没建」。现在恒打：\n"
           "    --   读到 N=0 就是「本版在跑，且这一入口没建帧」这个硬事实。\n"
           "    local sk = ((ns.hui and ns.hui.__skinBuilds) or 0) - (PF_SKIN0 or 0)\n"
           "    local tb = ((ns.hui and ns.hui.__tryBuilds) or 0) - (PF_TB0 or 0)\n"
           "    pfOut(string.format(\"  └ 皮按钮帧：建 %d 次 · TryBuild 调用 %d 次（rev14）\", sk, tb))\n"
           "    -- ★★ 第八刀（rev14）：工具行闸门内部拆解。这四项**已含在「工具P」里**，\n"
           "    --   只作分解展示，**不相加**。\n"
           "    local zg = PF_SUB and PF_SUB[\"闸-合计\"]\n"
           "    if zg then\n"
           "        local seg, hit = {}, 0\n"
           "        for _, kv in ipairs({ { \"闸-尺寸\", \"尺寸\" }, { \"闸-锚点\", \"锚点\" },\n"
           "                              { \"闸-文本\", \"文本\" }, { \"闸-显示\", \"显示\" } }) do\n"
           "            local e = PF_SUB[kv[1]]\n"
           "            if e then\n"
           "                seg[#seg + 1] = string.format(\"%s %.1f\", kv[2], e[2])\n"
           "                hit = e[1]\n"
           "            end\n"
           "        end\n"
           "        pfOut(string.format(\"  └ 工具闸门（已含在「工具P」里）：%d 开 / %.1fms = %s\",\n"
           "                            hit, zg[2], table.concat(seg, \" + \")))\n"
           "    end\n")

# ────────────────────────────── 双 harness 断言 ──────────────────────────────

ANCHOR_CK = "       and 'if r and i <= syncN then' in _paintlive)\n"

NEW_CK = (ANCHOR_CK +
          "    # ★★ 2026-10-09 第八刀（rev14）：第七刀把「皮按钮帧」那行写成「sk>0 才打」⇒\n"
          "    #   实机看不到它时无法区分「本版没加载」与「加载了但没建帧」。现在恒打 + rev。\n"
          "    #   并把工具行闸门内部切四刀（16 颗按钮切页时吃 21~26ms，闸门里每样都便宜 ⇒\n"
          "    #   必须实测拆开）。★ 计时器要**运行期动态取**（加载期抓局部会让替换失效）。\n"
          "    _pt = profui[profui.index('function PD.PaintTool'):\n"
          "                 profui.index('function PD.PaintLvTiles')]\n"
          "    _ptlive = '\\n'.join(l.split('--')[0] for l in _pt.split('\\n'))\n"
          "    ck('★★ 工具行闸门内部切四刀（尺寸/锚点/文本/显示），且「皮按钮帧」行恒打并带 rev',\n"
          "       'PD.__pfT0, PD.__pfMark' in _ptlive\n"
          "       and '_MK(\"闸-尺寸\", _m0)' in _ptlive\n"
          "       and '_MK(\"闸-锚点\", _m0)' in _ptlive\n"
          "       and '_MK(\"闸-文本\", _m0)' in _ptlive\n"
          "       and '_MK(\"闸-显示\", _m0)' in _ptlive\n"
          "       and 'function PD.__pfMark(' in profui\n"
          "       and 'if sk > 0 then' not in profui\n"
          "       and '（rev14' in profui)\n")

# ────────────────────── 探针离线冒烟断言 ──────────────────────

SMOKE = '_temp/_prof_perf_print_check.py'
OLD_SMOKE = ("    ck('★ setter 调用行确实打出来了（且不只 SetText/SetTextColor，还有 SetPoint/SetSize 等）',\n"
             "       any('setter 调用' in l for l in lines),\n"
             "       next((l for l in lines if 'setter 调用' in l), '(无)'))\n")

NEW_SMOKE = (OLD_SMOKE +
             "    # ★★ 第八刀（rev14）：①「皮按钮帧」那行必须**恒打**（第七刀写成「sk>0 才打」\n"
             "    #   ⇒ 实机看不到它时**无法区分**「本版没加载」与「加载了但一副都没建」）；\n"
             "    #   ② 工具行闸门内部必须能拆出四刀（16 颗按钮切页吃 21~26ms，而闸门里每样\n"
             "    #   按 bench 单价都是微秒级 ⇒ 不实测拆开就只能读代码猜）。\n"
             "    ck('★★ 「皮按钮帧」行恒打（带 rev14）且工具闸门能拆出四刀',\n"
             "       any('皮按钮帧：建' in l and 'rev14' in l for l in lines)\n"
             "       and any('工具闸门（已含在「工具P」里）' in l and '尺寸' in l\n"
             "               and '锚点' in l and '文本' in l and '显示' in l for l in lines),\n"
             "       next((l for l in lines if '工具闸门（已含在' in l), '(无)'))\n")

# ────────────────────────────── 变异 ──────────────────────────────

MUT_DEF_ANCHOR = ("MUT_PROF_ROW_SYNC_ALL = ('Core/ProfessionUI.lua', (\n"
                  "    b'            if r and i <= syncN then\\n',\n"
                  "    b'            if r then  -- MUT: rebind every pooled row inline\\n'))\n")

MUT_DEF = (
    "\n"
    "# ★★ 工具行闸门插桩（2026-10-09 第八刀 rev14）：把计时器来源摘掉（_T0/_MK 置 nil）\n"
    "#   ⇒ _MK 永远为 nil，闸-* 四项一条都记不上 ⇒ 工具行 21~26ms 又拆不开（回归到只能\n"
    "#   读代码猜）。★ 锚点必须**纯 ASCII**：Python 3 的 b'...' 不许含非 ASCII 字面量。\n"
    "MUT_PROF_TOOL_GATE_UNMARKED = ('Core/ProfessionUI.lua', (\n"
    "    b'    local _T0, _MK = PD.__pfT0, PD.__pfMark\\n',\n"
    "    b'    local _T0, _MK = nil, nil  -- MUT: tool gate left uninstrumented\\n'))\n")

MUT_REG_ANCHOR = ("    ('专业页：行帧已在池里也本帧全量重绑（切回配方页那一下又 100ms+）',"
                  " MUT_PROF_ROW_SYNC_ALL),\n")
MUT_REG_NEW = (MUT_REG_ANCHOR +
               "    ('专业页：工具行闸门插桩被摘（21ms 又拆不开，只能读代码猜）',"
               " MUT_PROF_TOOL_GATE_UNMARKED),\n")

WANT_ANCHOR = "    '专业页：行帧已在池里也本帧全量重绑（切回配方页那一下又 100ms+）',\n"
WANT_NEW = (WANT_ANCHOR +
            "    '专业页：工具行闸门插桩被摘（21ms 又拆不开，只能读代码猜）',\n")

# (文件, 名字, 旧, 新, 哨兵) —— 哨兵只在「已应用」后出现。
JOBS = [
    (HUI, 'A Hui TryBuild 计数', OLD_TB, NEW_TB, 'ns.hui.__tryBuilds = (ns.hui.__tryBuilds or 0) + 1'),
    (PROF, 'B PaintTool 取计时器', OLD_TOP, NEW_TOP, 'local _T0, _MK = PD.__pfT0, PD.__pfMark'),
    (PROF, 'C 闸门切四刀', OLD_GATE, NEW_GATE, '_MK("闸-尺寸", _m0)'),
    (PROF, 'D 探针 PF_TB0 声明', OLD_DECL, NEW_DECL, 'local PF_TB0 = nil'),
    (PROF, 'E pfBegin 快照', OLD_BEGIN, NEW_BEGIN, 'PF_TB0 = (ns.hui and ns.hui.__tryBuilds)'),
    (PROF, 'F 记号器定义', OLD_PFOUT, NEW_PFOUT, 'function PD.__pfMark(tag, t0)'),
    (PROF, 'G pfEnd 无条件 + rev', OLD_END, NEW_END, '皮按钮帧：建 %d 次 · TryBuild 调用 %d 次（rev14）'),
    (CHECK, 'H harness 加断言', ANCHOR_CK, NEW_CK, '工具行闸门内部切四刀'),
    (MK, 'I 生成器加断言', ANCHOR_CK, NEW_CK, '工具行闸门内部切四刀'),
    (MUT, 'J 变异定义', MUT_DEF_ANCHOR, MUT_DEF_ANCHOR + MUT_DEF, 'MUT_PROF_TOOL_GATE_UNMARKED = '),
    (MUT, 'K 变异登记', MUT_REG_ANCHOR, MUT_REG_NEW, 'MUT_PROF_TOOL_GATE_UNMARKED),'),
    (WANT, 'L DEFAULT_WANT', WANT_ANCHOR, WANT_NEW, '工具行闸门插桩被摘'),
    (SMOKE, 'M 冒烟断言', OLD_SMOKE, NEW_SMOKE, '「皮按钮帧」行恒打（带 rev14）'),
]


def main():
    check = '--check' in sys.argv
    bad, plans, raws = 0, {}, {}
    for path, name, old, new, key in JOBS:
        if path not in raws:
            raws[path] = open(path, 'rb').read()
        raw = raws[path]
        src = plans.get(path) or raw.decode('utf-8')
        nl = '\r\n' if b'\r\n' in raw else '\n'

        def fx(s):
            return s if nl == '\n' else s.replace('\n', nl)

        if key and fx(key) in src:
            print('  [SKIP] %-26s 已应用' % name)
            continue

        o, n = fx(old), fx(new)
        if src.count(o) != 1:
            print('  [BAD ] %-26s 锚点 %d 次' % (name, src.count(o)))
            bad += 1
            continue
        plans[path] = src.replace(o, n, 1)
        print('  [OK  ] %-26s 锚点 1 次' % name)

    if bad:
        print('  \u2717 %d 处未通过，未落盘' % bad)
        return 1
    if check:
        print('  [OK  ] 预检通过（未落盘）')
        return 0
    for path, src in plans.items():
        if src != raws[path].decode('utf-8'):
            with open(path, 'wb') as f:
                f.write(src.encode('utf-8'))
            print('  [OK  ] 已写入 %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
