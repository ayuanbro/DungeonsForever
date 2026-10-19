# -*- coding: utf-8 -*-
"""QA 临时探针：核对 zhTW 覆盖层一致性 / 词频 / WeaponName 段（只读，不写盘）。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_zhtw_data as G  # noqa: E402
from strip_comments import strip_text  # noqa: E402

DF = os.path.dirname(HERE)
src = open(os.path.join(DF, 'Core', 'Data', 'Data_LootFilter.lua'),
           encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
ztw = open(os.path.join(DF, 'Core', 'Data', 'zhTW', 'Data_LootFilter.lua'),
           encoding='utf-8', errors='replace').read().replace('\r\n', '\n')


def split_cc(line):
    code, in_str, i = line, False, 0
    while i < len(line):
        c = line[i]
        if c == '\\' and in_str:
            i += 2
            continue
        if c in ('"', "'"):
            in_str = not in_str
        elif not in_str and line[i:i + 2] == '--':
            return line[:i], line[i:]
        i += 1
    return line, ''


def norm(lines):
    out = []
    for ln in lines:
        code, _ = split_cc(ln)
        code = code.rstrip()
        if code.strip():
            out.append(code)
    return out


# 源：逐行剥注释 → 转繁 → 归一
conv_norm = norm([G.convert_line(split_cc(l)[0])[0] for l in src.split('\n')])
# zhTW：守卫之后的正文
gi = max(i for i, l in enumerate(ztw.split('\n')) if "if gl ~= 'zhTW' then return end" in l)
zbody = norm(ztw.split('\n')[gi + 1:])
zfull = norm(ztw.split('\n'))
print('conv_norm 行数 =', len(conv_norm))
print('zbody     行数 =', len(zbody))
print('zfull     行数 =', len(zfull))
eq = conv_norm == zbody
print('逐行相等 =', eq)
if not eq:
    for i in range(max(len(conv_norm), len(zbody))):
        a = conv_norm[i] if i < len(conv_norm) else '<缺行>'
        b = zbody[i] if i < len(zbody) else '<缺行>'
        if a != b:
            print('首个差异@%d\n  源繁化=%r\n  zhTW  =%r' % (i, a[:120], b[:120]))
            break

print('\n-- 词频（原始整文件，含注释）--')
for zh, cn in [('戰刃', '战刃'), ('長矛', '长矛'), ('釣魚竿', '钓鱼竿'),
               ('小盾', '小盾'), ('主屬性', '主属性'), ('MainAttribute', 'MainAttribute')]:
    print('  %-14s zhTW=%d  src(简)=%d' % (zh, ztw.count(zh), src.count(cn)))

print('\n-- 词频（剥注释后的正文）--')
src_code = '\n'.join(split_cc(l)[0] for l in src.split('\n'))
ztw_code = '\n'.join(split_cc(l)[0] for l in ztw.split('\n'))
for zh, cn in [('戰刃', '战刃'), ('長矛', '长矛'), ('釣魚竿', '钓鱼竿'),
               ('小盾', '小盾'), ('主屬性', '主属性')]:
    print('  %-14s zhTW=%d  src(简)=%d' % (zh, ztw_code.count(zh), src_code.count(cn)))

# 定位「长矛」在源里的所有出现
print('\n-- 源里「长矛」出现位置 --')
for i, l in enumerate(src.split('\n'), 1):
    if '长矛' in l:
        print('  L%d: %s' % (i, l.strip()[:100]))
print('\n-- zhTW 里「長矛」出现位置 --')
for i, l in enumerate(ztw.split('\n'), 1):
    if '長矛' in l:
        print('  L%d: %s' % (i, l.strip()[:100]))

# WeaponName 段（zhTW 剥注释后）
print('\n-- zhTW WeaponName 段 --')
lines = ztw.split('\n')
a = next(i for i, l in enumerate(lines) if l.strip().startswith('D.WeaponName'))
b = next(i for i in range(a, len(lines)) if lines[i].strip() == '}')
seg = '\n'.join(lines[a:b + 1])
for w in ('戰刃', '長矛', '釣魚竿'):
    print('  %s: 段内=%d 全文件=%d' % (w, seg.count(w), ztw_code.count(w)))
print('  --- 段原文 ---')
print(seg)

# 检查 gen main 会写 zhTW 与当前一致？
print('\n-- D.FlagLabel / D.ShuXingLabel 段（zhTW）--')
for key in ('D.FlagLabel', 'D.ShuXingLabel', 'D.ShuXing ['):
    idx = ztw.find(key)
    print('  %s @%d' % (key, idx))
