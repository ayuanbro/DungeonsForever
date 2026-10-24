# -*- coding: utf-8 -*-
"""把 _cg_parsed.json 各专精的 flow 预规范化成 _cg_norm.json，供 LLM 翻译管线对齐。

- 与 fc_guide.normalize_flow 完全同源（直接 import），保证译文 flow 与英文 flow 逐位对齐。
- druid_balance 已有手翻译文，跳过。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fc_guide import normalize_flow, KEYS, load_trans

SRC = os.path.join(HERE, '_cg_parsed.json')
DST = os.path.join(HERE, '_cg_norm.json')


def main():
    data = json.load(io.open(SRC, encoding='utf-8'))
    out = {}
    for key in KEYS:
        if load_trans(key):
            print('skip (has trans):', key)
            continue
        rec = data.get(key)
        if not rec:
            print('missing:', key)
            continue
        secs = []
        for sec in rec['sections']:
            flow = normalize_flow(sec['flow'], sec['key'])
            if flow:
                secs.append({'key': sec['key'], 'flow': flow})
        out[key] = {'updated': rec.get('updated') or '', 'sections': secs}
        n = sum(len(s['flow']) for s in secs)
        print('%-24s sections=%d flow=%d' % (key, len(secs), n))
    io.open(DST, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print('->', DST)


if __name__ == '__main__':
    main()
