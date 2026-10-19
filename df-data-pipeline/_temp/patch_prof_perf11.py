# -*- coding: utf-8 -*-
"""第七刀（探针）：把实机 77.6ms 里最后两个谜（工具行 28.3 / 冷热）问清楚。

实机 12:48 还有两处没落地：
  · **工具行 28.3ms** —— 合并了 PaintTool + RecipeTool + LevelTool，不知道是谁。
    而 bench 量出 setter 单价只有 0.18~0.62 µs/次 ⇒ 20 个按钮就算每个写 8 次
    setter 也才 0.04ms ⇒ **28.3ms 绝不是 setter**，必须先把三个函数拆开。
  · **冷 / 热** —— 这一版是「首次点该专业配方页」。到底是**一次性建帧**（第二次该骤降）
    还是**每帧都得做**？`/dfprofperf rep` 连渲 3 次一跑就知道。

另修一个探针自身的时机 bug：
  `pfWrapAll()`（给按钮/行装 setter 计数器）原本只在 `PF_DEPTH == 0` 的 Render 里跑，
  而**入口包装器（SetTab / Show）会先把 PF_DEPTH 置 1 再调 Render** ⇒
  **第一次点击永远装不上计数器**，实机第一版就是这样（setter 调用行一次都没出现过，
  看着像「根本没有 setter 调用」）。改成每层都补包（pfWrapSetter 自带幂等标记）。

只追加 / 只改探针自身，**不碰任何产品逻辑**。
"""

import sys

PROD = 'Core/ProfessionUI.lua'
SENTINEL = '"工具P", "工具R", "工具L"'


def heal(s, raw):
    nl = '\r\n' if b'\r\n' in raw else '\n'
    if nl == '\n':
        return s
    return s.replace('\r\n', '\n').replace('\n', nl)


# ── 1 工具行三拆：PF_ORDER ────────────────────────────────────────────
P1_OLD = 'local PF_ORDER = { "导航", "数据", "工具行", "信息卡", "布局", "铺行", "开关", "请求" }\n'
P1_NEW = ('local PF_ORDER = { "导航", "数据", "工具P", "工具R", "工具L", "信息卡",\n'
          '                   "布局", "铺行", "开关", "请求" }\n')

# ── 2 工具行三拆：pfTime 映射 ─────────────────────────────────────────
P2_OLD = ('pfTime(PD, "PaintTool",    "工具行")\n'
          'pfTime(PD, "RecipeTool",   "工具行")\n'
          'pfTime(PD, "LevelTool",    "工具行")\n')
P2_NEW = ('-- ★ 三拆（2026-10-09 第六轮）：实机「工具行 28.3ms」是三项之和，得先知道是谁。\n'
          'pfTime(PD, "PaintTool",    "工具P")\n'
          'pfTime(PD, "RecipeTool",   "工具R")\n'
          'pfTime(PD, "LevelTool",    "工具L")\n')

# ── 3 细分加「工具尺寸 / 搜索预留」（都在 工具P 里）───────────────────
P3_OLD = ('pfSub(PD, "RecipeSpec",    "单条spec")\n')
P3_NEW = ('pfSub(PD, "RecipeSpec",    "单条spec")\n'
          '-- 工具行内部（都在 工具P 那一段里）：量大头是不是 ToolSize 的字体测量。\n'
          'pfSub(PD, "ToolSize",      "工具尺寸")\n'
          'pfSub(PD, "SearchReserve", "搜索预留")\n')

# ── 4 细分打印列表 + 标签 ─────────────────────────────────────────────
P4_OLD = ('    for _, k in ipairs({ "扫描", "建spec", "列宽材料", "材料串", "单条spec" }) do\n')
P4_NEW = ('    for _, k in ipairs({ "扫描", "建spec", "列宽材料", "材料串", "单条spec",\n'
          '                        "工具尺寸", "搜索预留" }) do\n')
P5_OLD = '    if #sub > 0 then pfOut("  └ 细分（已含在数据里）：" .. table.concat(sub, " · ")) end\n'
P5_NEW = '    if #sub > 0 then pfOut("  └ 细分（已含在上面某一段里，不相加）：" .. table.concat(sub, " · ")) end\n'

# ── 6 setter 计数：补包更多引擎调用 ───────────────────────────────────
P6_OLD = ('local function pfWrapEl(f)\n'
          '    if type(f) ~= "table" then return end\n'
          '    pfWrapSetter(f, "SetText")\n')
P6_NEW = ('local function pfWrapEl(f)\n'
          '    if type(f) ~= "table" then return end\n'
          '    pfWrapSetter(f, "SetText")\n'
          '    -- ★ 2026-10-09 第六轮：bench 单价告诉我们 setter 便宜（0.2~0.6µs），\n'
          '    --   但「便宜 × 多少次」才是耗时 ⇒ 这些也得计数。都是没有\n'
          '    --   hooksecurefunc 挂在实例上的方法，覆盖实例字段不影响 HUI 的钩子。\n'
          '    pfWrapSetter(f, "SetPoint")\n'
          '    pfWrapSetter(f, "SetSize")\n'
          '    pfWrapSetter(f, "SetShown")\n'
          '    pfWrapSetter(f, "Show")\n'
          '    pfWrapSetter(f, "Hide")\n')

# ── 7 setter 打印列表 ─────────────────────────────────────────────────
P7_OLD = '    for _, k in ipairs({ "SetText", "SetTextColor" }) do\n'
P7_NEW = ('    for _, k in ipairs({ "SetText", "SetTextColor", "SetPoint", "SetSize",\n'
          '                        "SetShown", "Show", "Hide" }) do\n')

# ── 8 pfWrapAll 时机修正 ──────────────────────────────────────────────
P8_OLD = ('        -- 入口层先补包 setter（新池化出来的行、其 fontstring 下一帧才包得上）\n'
          '        if PF_DEPTH == 0 then pfWrapAll() end\n')
P8_NEW = ('        -- ★ 每一层都补包（2026-10-09 第六轮修）：入口层（SetTab / Show）会**先**把\n'
          '        --   PF_DEPTH 置 1 再调 Render ⇒ 只看 PF_DEPTH == 0 的话第一次点击永远\n'
          '        --   装不上计数器（实机第一版 setter 行一次都没出现过）。\n'
          '        --   pfWrapSetter 自带 __dfw<meth> 幂等标记，重复包无害。\n'
          '        pfWrapAll()\n')

# ── 9 /dfprofperf rep：连渲 3 次分辨冷热 ──────────────────────────────
P9_OLD = ('        if msg == "off" then\n'
          '            PD.PERF = false\n'
          '            pfOut("已关闭。")\n'
          '            return\n'
          '        end\n')
P9_NEW = ('        if msg == "off" then\n'
          '            PD.PERF = false\n'
          '            pfOut("已关闭。")\n'
          '            return\n'
          '        end\n'
          '        if msg == "rep" then\n'
          '            -- ★★ 冷 / 热自测（2026-10-09 第六轮）：连渲同一页 3 次。\n'
          '            --   第 1 次含「一次性建帧」，第 2/3 次是热路径。两者差多大，\n'
          '            --   就知道某一段值不值得挪进分帧段 / 做预建。\n'
          '            if not (PD.built and PD.page) then\n'
          '                pfOut("先打开专业页（/df zy）再 rep。")\n'
          '                return\n'
          '            end\n'
          '            local save, saveMin = PD.PERF, PD.PERF_MIN\n'
          '            PD.PERF, PD.PERF_MIN = "all", 0\n'
          '            for i = 1, 3 do\n'
          '                pfOut("  ---- 第 " .. i .. " 次 ----")\n'
          '                PD.Render()\n'
          '            end\n'
          '            PD.PERF, PD.PERF_MIN = save, saveMin\n'
          '            pfOut("rep 完成（第 1 次含建帧，后两次是热路径）。")\n'
          '            return\n'
          '        end\n')

EDITS = [
    ('1 PF_ORDER 三拆', P1_OLD, P1_NEW, None),
    ('2 pfTime 三拆', P2_OLD, P2_NEW, None),
    # 3 / 6 / 9 的「旧串」是「新串」的一部分（插入型），count(old) 判不出「已应用」
    #   ⇒ 各给一个只在应用后出现的哨兵。
    ('3 细分加工具尺寸', P3_OLD, P3_NEW, 'pfSub(PD, "SearchReserve", "搜索预留")'),
    ('4 细分打印列表', P4_OLD, P4_NEW, None),
    ('5 细分标签', P5_OLD, P5_NEW, None),
    ('6 pfWrapEl 扩 setter', P6_OLD, P6_NEW, 'pfWrapSetter(f, "SetPoint")'),
    ('7 setter 打印列表', P7_OLD, P7_NEW, None),
    ('8 pfWrapAll 时机', P8_OLD, P8_NEW, None),
    ('9 rep 命令', P9_OLD, P9_NEW, 'if msg == "rep" then'),
]


def main():
    check = '--check' in sys.argv
    raw = open(PROD, 'rb').read()
    src = raw.decode('utf-8')
    bad, out = 0, src
    for name, old, new, key in EDITS:
        o, n = heal(old, raw), heal(new, raw)
        if key and out.count(heal(key, raw)) >= 1:
            print('  [SKIP] %-24s 已应用' % name)
            continue
        c_o, c_n = out.count(o), out.count(n)
        if c_n == 1 and c_o == 0:
            print('  [SKIP] %-24s 已应用' % name)
            continue
        if c_o != 1:
            print('  [BAD ] %-24s 锚点 %d 次' % (name, c_o))
            bad += 1
            continue
        if c_n >= 1:
            print('  [BAD ] %-24s 替换串已存在 %d 次' % (name, c_n))
            bad += 1
            continue
        out = out.replace(o, n, 1)
        print('  [OK  ] %-24s 锚点 1 次' % name)
    if bad:
        print('  ✗ %d 处未通过，未落盘' % bad)
        return 1
    if SENTINEL not in out:
        print('  [BAD ] 哨兵缺失：三拆没落上')
        return 1
    if check:
        print('  [OK  ] 预检通过（未落盘）')
        return 0
    if out != src:
        with open(PROD, 'wb') as f:
            f.write(out.encode('utf-8'))
        print('  [OK  ] 已写入 %s' % PROD)
    return 0


if __name__ == '__main__':
    sys.exit(main())
