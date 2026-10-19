# -*- coding: utf-8 -*-
"""重锚 df_mut_check.py 里 23 条「死锚」变异（22 条真坏 + MUT_PROF_DETAIL_BACK 拆冲突）。

背景：这些变异的锚点写的是旧代码（被后续重构改掉了字面），`check_mut_anchors.audit()`
报 22 条异常、`df_mut_check.main()` 又多跳 3 条（两条变异共用同一段锚点，先跑的吃掉后跑的）。

做法：锚点不用手抄——**按行号从当前源文件切片**，再做纯 ASCII 的字符串替换生成 new。
这样锚点永远与当前代码逐字一致，且不会再抄错中文/CRLF。

幂等：跑第二遍时模块里的 old 已等于目标 old ⇒ 直接跳过。
--check：只预检，不落盘。

用法：
    python patch_mut_reanchor.py --check
    python patch_mut_reanchor.py
"""
import ast
import os
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = r'D:\workspace\DungeonsForever'
MUTPY = os.path.join(HERE, 'df_mut_check.py')
BAK = os.path.join(HERE, '_bak18_df_mut_check.py')

# ---------------------------------------------------------------------------
# 每条 job：常量名 / 目标文件 / 行区间(1-based, 含) / 替换表 / 或 new 覆盖
#   替换表 = [(find, repl), ...] 对「按行切出来的那段」做 str.replace
#   new_override 给定时，直接用它当 new（不再做替换）
# ---------------------------------------------------------------------------
JOBS = [
    # ---- ProfessionUI.lua（纯 LF）----
    ('MUT_PROF_SHOP_RIGHT_GONE', 'Core/ProfessionUI.lua', (3882, 3882),
     [('#mats), 1)', '#mats), 2) -- MUT: mats list back to right column')]),
    ('MUT_PROF_LVMAT_NAMEGAP', 'Core/ProfessionUI.lua', (3724, 3724),
     [('PD.TBL_NAME_GAP', '20 -- MUT: name-to-mats gap fattened')]),
    ('MUT_PROF_LV_TBL_GROUP_LEFT', 'Core/ProfessionUI.lua', (2881, 2881),
     [('W - PD.TBL_MAT_RPAD', 'PD.TBL_MAT_RPAD -- MUT: material group not right-aligned')]),
    # 拆冲突：原来锚在 PD.BuildIndexGrid(child) 那行（与 MUT_IX_GRID_BUILT 同锚），
    # 改成锚在下一行的 PD.secCards = {} 上、把 detail 帧插在它前面（语义等价、锚点不重叠）
    ('MUT_PROF_DETAIL_BACK', 'Core/ProfessionUI.lua', (1788, 1788),
     [('    PD.secCards = {}\n',
       '    PD.detail = CreateFrame("Frame", nil, page) -- MUT: detail back\n    PD.secCards = {}\n')]),

    # ---- DungeonUI.lua（纯 CRLF）----
    ('MUT_GUIDE_TAB_GONE', 'Core/DungeonUI.lua', (1512, 1512),
     [(', { key = "guide", text = L["\u653b\u7565"] }', '')]),
    ('MUT_GUIDE_KEEP_SCROLL', 'Core/DungeonUI.lua', (4919, 4919),
     [('not isQuest and not isGuide and not isMap) end', 'not isQuest) end -- MUT: scroll no longer yields')]),
    ('MUT_EXPLORE_PAGE_GONE', 'Core/DungeonUI.lua', (5076, 5076),
     [('        ns.ExploreModule.Build(U.explorePage)',
       '        -- MUT: explore page build dropped')]),
    ('MUT_DETAIL_OLD', 'Core/DungeonUI.lua', (2761, 2761),
     [('local r = rows[idx]', 'local r = nil -- MUT: never reuse row')]),
    ('MUT_TIP_PREWARM', 'Core/DungeonUI.lua', (2175, 2179),
     [('    DG.EnsureItemListener()\r\n',
       '    DG.EnsureItemListener()\r\n    if true then return end -- MUT: prewarm does nothing\r\n')]),
    ('MUT_SWEEP_NO_SKIP', 'Core/DungeonUI.lua', (2238, 2240),
     [('if it and not c.__named then', 'if it then -- MUT: sweep rescans named cards')]),
    ('MUT_NO_NAMED_MARK', 'Core/DungeonUI.lua', (1957, 1965),
     [('                c.__named = hasName\r\n', '                -- MUT: no __named mark\r\n')]),
    ('MUT_NO_NAMED_BIND', 'Core/DungeonUI.lua', (2011, 2019),
     [('        c.__named = hasName\r\n', '        -- MUT: no __named mark on bind\r\n')]),
    ('MUT_WHEEL_CARD', 'Core/DungeonUI.lua', (2699, 2701),
     [('        r:EnableMouseWheel(true)\r\n', '        -- MUT: loot card eats the wheel\r\n')]),
    ('MUT_NO_LOGUPD', 'Core/DungeonUI.lua', (3473, 3474),
     [('    ev:RegisterEvent("QUEST_LOG_UPDATE")\r\n', '    -- MUT: no quest log update listener\r\n')]),
    # RenderQuestDetail() 在文件里有 3 处同缩进调用 ⇒ 必须带上一行做上下文唯一化
    ('MUT_NO_QDET', 'Core/DungeonUI.lua', (4001, 4002),
     [('    U:RenderQuestDetail()\r\n', '    -- MUT: no quest detail linkage\r\n')]),
    ('MUT_ROW_FRAME', 'Core/DungeonUI.lua', (3803, 3804),
     [('CreateFrame("Button", nil, child, "BackdropTemplate")\r\n            r:SetSize(DG.Q_LIST_W',
       'CreateFrame("Frame", nil, child, "BackdropTemplate") -- MUT: row is Frame\r\n            r:SetSize(DG.Q_LIST_W')]),
    ('MUT_GAINS_GONE', 'Core/DungeonUI.lua', (4678, 4678),
     [('if seg and #seg > 0 then', 'if false then -- MUT: gains section gone')]),
    ('MUT_NO_REQ_SECT', 'Core/DungeonUI.lua', (4652, 4652),
     [('if hasChips or objTxt then', 'if false then -- MUT: no required-items section')]),
    ('MUT_CARD_COLS', 'Core/DungeonUI.lua', (1793, 1793),
     [('DG.LOOT_COLS = 4', 'DG.LOOT_COLS = 2')]),
    ('MUT_CARD_BG_RESET', 'Core/DungeonUI.lua', (2851, 2853),
     [('                    r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)\r\n'
       '                    r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)\r\n',
       '                    -- MUT: backdrop reset skipped\r\n')]),
    ('MUT_LOAD_TIP', 'Core/DungeonUI.lua', (2145, 2151), None,
     '    -- MUT: hidden tooltip fallback removed\r\n'),
    ('MUT_LOAD_LISTENER', 'Core/DungeonUI.lua', (2132, 2133),
     [('    DG.EnsureItemListener()\r\n', '    -- MUT: ensure-listener call removed\r\n')]),
    ('MUT_CLICK_FRAME', 'Core/DungeonUI.lua', (2691, 2692),
     [('CreateFrame("Button", nil, child, "BackdropTemplate")\r\n        r:SetSize(cw',
       'CreateFrame("Frame", nil, child, "BackdropTemplate") -- MUT: frame cannot click\r\n        r:SetSize(cw')]),
]


# ---------------------------------------------------------------------------
def slice_lines(path, a, b):
    raw = open(path, 'rb').read()
    return b''.join(raw.splitlines(keepends=True)[a - 1:b]).decode('utf-8')


def build_pair(job):
    """返回 (const, prefix_or_None, old_bytes, new_bytes)"""
    if len(job) == 5:
        const, rel, (a, b), repls, new_override = job
    else:
        const, rel, (a, b), repls = job
        new_override = None
    seg = slice_lines(os.path.join(DEV, *rel.split('/')), a, b)
    if new_override is not None:
        new = new_override
    else:
        new = seg
        for find, repl in repls:
            if seg.count(find) != 1:
                raise AssertionError('%s: 切片里 %r 出现 %d 次（应为 1）' % (const, find, seg.count(find)))
            new = new.replace(find, repl)
    if new == seg:
        raise AssertionError('%s: 替换没改变内容' % const)
    prefix = None if rel == 'Core/DungeonUI.lua' else rel
    return const, prefix, seg.encode('utf-8'), new.encode('utf-8')


def _esc(seg):
    out = []
    for by in seg:
        if by == 0x0a:
            out.append('\\n')
        elif by == 0x0d:
            out.append('\\r')
        elif by == 0x09:
            out.append('\\t')
        elif by == 0x5c:
            out.append('\\\\')
        elif by == 0x27:
            out.append("\\'")
        elif 0x20 <= by <= 0x7e:
            out.append(chr(by))
        else:
            out.append('\\x%02x' % by)
    return ''.join(out)


def _emit_lines(b, indent='    '):
    parts, buf = [], b''
    for by in b:
        buf += bytes([by])
        if by == 0x0a:
            parts.append(buf)
            buf = b''
    if buf:
        parts.append(buf)
    if not parts:
        parts = [b'']
    return [indent + "b'" + _esc(p) + "'" for p in parts]


def def_src(const, prefix, old, new, comments=()):
    """生成常量定义源码。block 自身已经收尾（`)` 或 `))`），外面不再补括号。"""
    ol = _emit_lines(old)
    nl = _emit_lines(new)
    closer = '))' if prefix else ')'
    head = list(comments)
    block = '\n'.join(head + ol[:-1] + [ol[-1] + ',']) + '\n' + \
            '\n'.join(nl[:-1] + [nl[-1] + closer])
    if prefix:
        return "%s = ('%s', (\n%s" % (const, prefix, block)
    return "%s = (\n%s" % (const, block)


def node_comments(lines, a, b):
    """取原始定义节点里的注释行（保留它们，别被重锚顺手删掉）。"""
    out = []
    for ln in lines[a - 1:b]:
        s = ln.strip()
        if s.startswith('#'):
            out.append(ln)
    return out


def load_mut_module():
    spec = importlib.util.spec_from_file_location('dmut_reanch', MUTPY)
    m = importlib.util.module_from_spec(spec)
    sys.modules['dmut_reanch'] = m
    spec.loader.exec_module(m)
    return m


def node_ranges(src):
    tree = ast.parse(src)
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id.startswith('MUT_'):
            out[node.targets[0].id] = (node.lineno, node.end_lineno)
    return out


def main():
    check = '--check' in sys.argv
    src = open(MUTPY, encoding='utf-8').read()
    lines = src.split('\n')
    ranges = node_ranges(src)
    mod = load_mut_module()
    cur = dict(mod.MUTATIONS)  # name -> spec

    # 反查常量 -> 当前 (old,new)
    def cur_pair(const):
        for name, s in mod.MUTATIONS:
            f, o, n = mod.split_spec(s)
            # 用名字找常量：MUTATIONS 里名字与常量一一对应，这里按模块属性比对
            v = getattr(mod, const, None)
            if v is None:
                return None
            return v
        return None

    jobs = []
    problems = []
    already = 0
    for job in JOBS:
        const = job[0]
        try:
            c, prefix, old, new = build_pair(job)
        except AssertionError as e:
            problems.append(str(e))
            continue
        val = getattr(mod, const, None)
        if val is None:
            problems.append('%s: 模块里没有这个常量' % const)
            continue
        # 取模块里该常量的 (old,new)
        if isinstance(val, tuple) and len(val) == 2 and isinstance(val[0], str):
            m_old, m_new = val[1]
        else:
            m_old, m_new = val
        if m_old == old and m_new == new:
            already += 1
            print('  [已是最新] %s' % const)
            continue
        if const not in ranges:
            problems.append('%s: AST 里找不到赋值节点' % const)
            continue
        jobs.append((const, prefix, old, new, ranges[const]))

    print('待更新 %d 条 / 已是最新 %d 条 / 问题 %d 条' % (len(jobs), already, len(problems)))
    for p in problems:
        print('  ✗ %s' % p)
    if problems:
        return 2
    if check:
        print('--check 通过（未落盘）')
        return 0

    if not os.path.exists(BAK):
        open(BAK, 'wb').write(open(MUTPY, 'rb').read())
        print('已备份 → %s' % os.path.basename(BAK))

    # 从后往前替换，避免行号漂移
    jobs.sort(key=lambda j: -j[4][0])
    for const, prefix, old, new, (a, b) in jobs:
        body = def_src(const, prefix, old, new, node_comments(lines, a, b)).split('\n')
        lines[a - 1:b] = body
        print('  [OK  ] %s  行 %d-%d' % (const, a, b))
    open(MUTPY, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('已写回 %s' % os.path.basename(MUTPY))
    return 0


if __name__ == '__main__':
    sys.exit(main())
