# -*- coding: utf-8 -*-
"""第七轮 ②：对**产出的 Lua 文件**（非 JSON）再扫一遍「夹生拉丁词」。

覆盖：Core/Data/Data_ClassGuide.lua（zhCN）、Core/Data/zhTW/Data_ClassGuide.lua（zhTW）。
（enUS 产物本就是英文正文，不参与本扫描。）
规则与 _r7_mixed.py 一致：只报「中文相邻（前后 4 字内含 CJK）的英文实词」，
排除 |sID| 占位、游戏缩写/专名白名单。输出：_temp/_r7_lua_scan.txt
"""
import io
import os
import re

DF = r'D:\workspace\DungeonsForever'
OUT = os.path.join(DF, '_temp', '_r7_lua_scan.txt')

SID = re.compile(r'\|s\d+\|')
CJK = re.compile(r'[\u4e00-\u9fff]')
ALLOW = re.compile(
    r'(?<![A-Za-z])(?:PVP|PVE|AOE|DPS|HPS|DOT|HOT|BOSS|BETA|TBC|WOTLK|WOD|RAIDBOTS|DISCORD|WCL'
    r'|GCD|CD|AP|SP|HP|MP|XP|NPC|OMEN|RDF|AH|TANK|HEALER)(?![A-Za-z])', re.I)

TARGETS = [
    'Core/Data/Data_ClassGuide.lua',
    'Core/Data/zhTW/Data_ClassGuide.lua',
]


def extract_strings(text):
    """抽取双引号字符串字面量（处理 \\" 转义与 \\\\）。"""
    out = []
    i, n = 0, len(text)
    while i < n:
        if text[i] == '"':
            j = i + 1
            buf = []
            while j < n:
                c = text[j]
                if c == '\\' and j + 1 < n:
                    buf.append(text[j:j + 2])
                    j += 2
                    continue
                if c == '"':
                    break
                buf.append(c)
                j += 1
            out.append(''.join(buf))
            i = j + 1
        else:
            i += 1
    return out


def clean(s):
    return re.sub(r'\s+', ' ', SID.sub('', s or '')).strip()


lines = []
w = lines.append
total = 0
for rel in TARGETS:
    p = os.path.join(DF, rel)
    text = io.open(p, encoding='utf-8').read()
    hits = []
    for raw in extract_strings(text):
        cc = clean(raw)
        if not cc:
            continue
        stripped = ALLOW.sub(' ', cc)
        runs = []
        for m in re.finditer(r'[A-Za-z][A-Za-z\-\'\. ]*[A-Za-z]', stripped):
            seg = re.sub(r'[\.\-\' ]+$', '', m.group(0).strip()).strip()
            if len(seg) < 2:
                continue
            a = max(0, m.start() - 4)
            b = min(len(stripped), m.end() + 4)
            near = stripped[a:m.start()] + stripped[m.end():b]
            if CJK.search(near):
                runs.append(seg)
        if runs:
            hits.append((runs, cc))
    total += len(hits)
    w('===== %s 命中 %d 段 =====' % (rel, len(hits)))
    for runs, cc in hits:
        w('  latin=%s' % runs)
        for r in runs:
            k = cc.find(r)
            if k >= 0:
                w('    …%s…' % cc[max(0, k - 24):k + len(r) + 24])
    w('')

w('★ 两产物合计「中英夹杂」段数 = %d' % total)
w('★ 判定：%s' % ('PASS（中英夹杂=0）' if total == 0 else 'FAIL'))

text = '\n'.join(lines) + '\n'
io.open(OUT, 'w', encoding='utf-8', newline='\n').write(text)
print(text)
