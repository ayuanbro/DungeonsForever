# -*- coding: utf-8 -*-
"""掉落过滤面板 v4 · 临时自检（zhTW 覆盖层一致性 + 隔离变异非恒真）。

非正式回归件（qa_lf_verify / df_dungeon_check 是正式件）。仅本会话临时用。
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_zhtw_data as G  # noqa: E402

DF = os.path.dirname(HERE)
SRC = os.path.join(DF, 'Core', 'Data', 'Data_LootFilter.lua')
DST = os.path.join(DF, 'Core', 'Data', 'zhTW', 'Data_LootFilter.lua')
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
PY = sys.executable


def split_code_comment(line):
    code, comment = line, ''
    in_str = False
    i = 0
    while i < len(line):
        c = line[i]
        if c == chr(92) and in_str:
            i += 2
            continue
        if c in ('"', "'"):
            in_str = not in_str
        elif not in_str and line[i:i + 2] == '--':
            code, comment = line[:i], line[i:]
            break
        i += 1
    return code, comment


def norm(lines):
    out = []
    for ln in lines:
        code, _ = split_code_comment(ln)
        code = code.rstrip()
        if code.strip():
            out.append(code)
    return out


def overlay_consistency():
    src_lf = open(SRC, encoding='utf-8').read().replace('\r\n', '\n')
    zhtw_lf = open(DST, encoding='utf-8').read().replace('\r\n', '\n')
    conv = norm([G.convert_line(split_code_comment(l)[0])[0] for l in src_lf.split('\n')])
    zl = zhtw_lf.split('\n')
    gi = max(i for i, l in enumerate(zl) if "if gl ~= 'zhTW' then return end" in l)
    body = norm(zl[gi + 1:])
    full = norm(zl)
    print('== zhTW 覆盖层一致性 ==')
    print('  源繁化行数 = %d  zhTW 正文行数 = %d  逐行相等 = %s'
          % (len(conv), len(body), conv == body))
    if conv != body:
        for i in range(max(len(conv), len(body))):
            a = conv[i] if i < len(conv) else '<缺行>'
            b = body[i] if i < len(body) else '<缺行>'
            if a != b:
                print('  首个差异@%d\n    源繁化=%r\n    zhTW  =%r' % (i, a[:100], b[:100]))
                break
    print('  zhTW 归一化行数（含守卫）= %d' % len(full))
    gone = ['小盾', 'MainAttribute', '主屬性', '主属性']
    print('  禁词命中 = %s' % ([w for w in gone if w in zhtw_lf] or 'clean'))
    for k, v in (('戰刃', '战刃'), ('長矛', '长矛'), ('釣魚竿', '钓鱼竿')):
        print('  保留词 %s: zhTW=%d src=%d（差值=%d，注释里的同名会致差）'
              % (k, zhtw_lf.count(k), src_lf.count(v),
                 zhtw_lf.count(k) - src_lf.count(v)))
    for probe in ('法術傷害', '職業限定', '保留戰網', '坦克裝備', '特定法術強度'):
        print('  overlay 含 %-6s = %s' % (probe, probe in zhtw_lf))


# (标签, 文件相对路径, old 子串, new 子串, 期望变红的断言名片段)
ISOLATED = [
    ('MUT_CLOSE_SETTINGS_GONE', 'Core/LootFilterUI.lua',
     'if ns.CloseSettings then ns.CloseSettings() end',
     '-- MUT: gone', 'LFv4 面板与「设置」弹窗互斥'),
    ('MUT_WIDTH_560', 'Core/LootFilterUI.lua',
     '    popup:SetWidth(220)\n',
     '    popup:SetWidth(560) -- MUT\n', 'LFv4 面板落位'),
    ('MUT_NO_RESKIN', 'Core/LootFilterUI.lua',
     '    if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(tg) end\n',
     '    -- MUT\n', 'LFv4 选项控件换成 iOS 开关'),
    ('MUT_NO_COLLAPSE_ROT', 'Core/LootFilterUI.lua',
     'hdr.arrD:SetRotation(math.pi)',
     'hdr.arrD:SetRotation(0) -- MUT', 'LFv4 四组可折叠'),
    ('MUT_NO_SHUXING_LABEL', 'Core/Data/Data_LootFilter.lua',
     '    ["特定法术强度"] = "法术伤害",\n',
     '    -- MUT\n', 'LFv4 数据层：词缀显示名'),
    ('MUT_NO_MUTEX_MF', 'Core/MainFrame.lua',
     'if ns.LootFilterUI and ns.LootFilterUI.CloseConfig then ns.LootFilterUI:CloseConfig() end\n',
     '-- MUT\n', 'LFv4 面板与「设置」弹窗互斥'),
    ('MUT_NO_PAGE_CLAMP', 'Core/LootFilterUI.lua',
     '    if (cfg.page or 0) > maxPage then cfg.page = maxPage end\n',
     '    -- MUT: stale page keeps end-page icons hidden\n',
     'LFv4 方案条翻页页码回夹'),
]


def isolated_mutations():
    print('\n== 隔离变异（逐条：注入 → df_dungeon_check 该断言变红 → 还原） ==')
    okall = True
    for label, rel, old, new, expect in ISOLATED:
        p = os.path.join(BETA, *rel.split('/'))
        orig = open(p, 'rb').read()
        ob = old.encode('utf-8')
        nb = new.encode('utf-8')
        if orig.count(ob) != 1:
            print('  [SKIP] %s 锚点命中 %d 次' % (label, orig.count(ob)))
            okall = False
            continue
        open(p, 'wb').write(orig.replace(ob, nb))
        try:
            r = subprocess.run([PY, os.path.join(HERE, 'df_dungeon_check.py')],
                               capture_output=True, text=True, encoding='utf-8',
                               errors='replace', cwd=HERE)
            out = (r.stdout or '') + (r.stderr or '')
            red = any(('[FAIL]' in ln and expect in ln) for ln in out.split('\n'))
            print('  [%s] %s → 目标断言变红=%s  (returncode=%d)'
                  % ('OK' if red else 'MISS', label, red, r.returncode))
            if not red:
                okall = False
        finally:
            open(p, 'wb').write(orig)
            assert open(p, 'rb').read() == orig, '还原失败 ' + rel
    print('  隔离变异全部命中 = %s' % okall)


if __name__ == '__main__':
    overlay_consistency()
    isolated_mutations()
