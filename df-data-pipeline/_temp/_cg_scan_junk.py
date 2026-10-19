# -*- coding: utf-8 -*-
"""扫描 _cg_parsed.json 全部 27 页 flow 元素里的解析垃圾（一次性诊断，可复用）。

用法：python _temp/_cg_scan_junk.py
"""
import io
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '_cg_parsed.json')

# 归一化后严格等值判定为「解析垃圾字面量」的词
JUNK = {'false', 'true', 'nil', 'null', 'none', 'undefined', 'nan',
        'inf', '-inf', '[object object]'}


def norm(v):
    return str(v).strip().lower()


def main():
    data = json.load(io.open(SRC, encoding='utf-8'))
    hits = []          # (cls_spec, section_key, idx, t, value)
    empties = []       # 空串值的元素
    tb_junk = []       # tb 单元格里的垃圾
    tcount = Counter()

    for key in data:
        rec = data[key]
        for sec in rec.get('sections', []):
            for i, f in enumerate(sec.get('flow', [])):
                t = f.get('t')
                tcount[t] += 1
                v = f.get('v')
                if isinstance(v, str):
                    if norm(v) in JUNK:
                        hits.append((key, sec['key'], i, t, v))
                    elif v.strip() == '':
                        empties.append((key, sec['key'], i, t, repr(v)))
                if t == 'tb':
                    for row in f.get('v', []):
                        cells = row['cells'] if isinstance(row, dict) else row
                        for c in cells:
                            if isinstance(c, str) and norm(c) in JUNK:
                                tb_junk.append((key, sec['key'], repr(c)))
                if t in ('good', 'bad') and isinstance(v, list):
                    for it in v:
                        if isinstance(it, str) and norm(it) in JUNK:
                            tb_junk.append((key, sec['key'], 'good/bad ' + repr(it)))
                if t == 'ul' and isinstance(v, list):
                    for it in v:
                        txt = (it or {}).get('text') if isinstance(it, dict) else None
                        if isinstance(txt, str) and norm(txt) in JUNK:
                            tb_junk.append((key, sec['key'], 'ul ' + repr(txt)))

    print('=== JUNK 值（t 为标量字符串的 p/h4 等）命中 %d 处 ===' % len(hits))
    for h in hits:
        print('  %-26s [%s] idx=%-2d t=%-4s v=%r' % h)
    print()
    print('=== 空串值元素 命中 %d 处 ===' % len(empties))
    for e in empties:
        print('  %-26s [%s] idx=%-2d t=%-4s v=%s' % e)
    print()
    print('=== tb/ul/good/bad 内嵌垃圾 命中 %d 处 ===' % len(tb_junk))
    for x in tb_junk:
        print('  %-26s [%s] %s' % x)
    print()
    print('=== 全量 t 类型分布 ===')
    print(dict(tcount))
    print()
    print('汇总: JUNK=%d  EMPTY=%d  NESTED=%d' % (len(hits), len(empties), len(tb_junk)))


if __name__ == '__main__':
    main()
