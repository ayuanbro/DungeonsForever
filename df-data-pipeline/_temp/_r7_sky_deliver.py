# -*- coding: utf-8 -*-
"""第七轮 ① 交付物：Skyborne 统一对照表 + 旧写法残留计数 + 误译订正（核英文原文）。
输出：_temp/_r7_sky_deliver.txt
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
import _r7_fix as F  # 复用 PH / WORD / TARGETED 单一真源（import 无副作用）

EN = json.load(io.open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')


def en_el(spec, key, idx):
    e = EN.get(spec, {})
    for sec in e.get('sections', []):
        if sec.get('key') == key:
            fl = sec.get('flow', [])
            if idx < len(fl):
                return fl[idx]
    return None


def el_text(el):
    if not isinstance(el, dict):
        return ''
    v = el.get('v')
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


def has_ascii(s):
    return any(('a' <= c.lower() <= 'z') for c in s)


L = []
w = L.append
w('=' * 78)
w('第七轮 ① Skyborne 统一 · 交付对照表')
w('=' * 78)
w('')
w('【A】英文原名 → 规范中文名（用户拍板 5 条）')
latin = [(a, b) for a, b in F.PH if has_ascii(a)]
for a, b in latin:
    w('    %-24s → %s' % (a, b))
w('')
w('【B】既有旧写法 → 规范名（同义归一，%d 条）' % (len([1 for a, b in F.PH if not has_ascii(a)])))
for a, b in F.PH:
    if not has_ascii(a):
        w('    %-12s → %s' % (a, b))
w('')
w('【C】误译订正 + 拉丁残留补译（★ 逐条核英文原文，勿误伤真 Void Elf / Phoenix）')
w('    关键词：英文字典/包名里 Void Elf≠Skyborne、Phoenix≠Skyborne；须按具体 spec 的 EN 原文判')
for (spec, key, idx), rules in sorted(F.TARGETED.items()):
    e = en_el(spec, key, idx)
    w('    ── %s / %s #%d' % (spec, key, idx))
    w('       EN 原文: %s' % (el_text(e)[:200] or '（无）'))
    for a, b in rules:
        w('       %r  →  %r' % (a, b))
w('')
w('【D】修复后残留计数（应全 0）与规范名分布')
for ln in io.open(os.path.join(HERE, '_r7_sky_final.txt'), encoding='utf-8').read().rstrip('\n').splitlines():
    w('    ' + ln)

text = '\n'.join(L) + '\n'
io.open(os.path.join(HERE, '_r7_sky_deliver.txt'), 'w', encoding='utf-8', newline='\n').write(text)
print(text)
