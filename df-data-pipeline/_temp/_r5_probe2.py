# -*- coding: utf-8 -*-
"""第五轮探针 v2：全库「未翻译散文」（含 tb 行/单元格级别）。
判据：字符串含 >=1 个 ASCII 字母 run 且**不含任何 CJK**，且不是纯 |sID|/标点/空白。
"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EN = json.load(io.open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')

CJK = re.compile(r'[\u4e00-\u9fff]')
LETTER = re.compile(r'[A-Za-z]{2,}')
SID = re.compile(r'\|s\d+\|')
PUNCT_ONLY = re.compile(r'^[\s\-—–:：、，,。.；;|s0-9]+$')


def is_prose_untranslated(s):
    if not isinstance(s, str):
        return False
    if not s.strip():
        return False
    if CJK.search(s):
        return False
    if not LETTER.search(s):
        return False
    # 纯法术引用/标点（如 "|s1259817|:"）不算
    if PUNCT_ONLY.match(s):
        return False
    stripped = SID.sub('', s)
    stripped = re.sub(r'[\s\-—–:：、，,。.；;0-9]', '', stripped)
    if not LETTER.search(stripped):
        return False
    return True


def walk_strings(o, path, out):
    if isinstance(o, str):
        if is_prose_untranslated(o):
            out.append(('>'.join(str(p) for p in path), o))
    elif isinstance(o, list):
        for i, x in enumerate(o):
            walk_strings(x, path + [i], out)
    elif isinstance(o, dict):
        for k, v in o.items():
            if k in ('title', 't', 'key'):
                continue
            walk_strings(v, path + [k], out)


def load_trans(spec):
    p = os.path.join(TD, spec + '.json')
    return json.load(io.open(p, encoding='utf-8')) if os.path.exists(p) else {}


def plan_norm(el):
    """归一后（tb 丢表头行）的元素，用于与 CN 对齐。"""
    t = el.get('t')
    v = el.get('v')
    if t == 'tb':
        rows = [r['cells'] if isinstance(r, dict) else r for r in v]
        rows = rows[1:] if len(rows) > 1 else rows
        return {'t': 'tb', 'v': rows}
    return el


def main():
    print('########## 全库「未翻译散文」单元格扫描 ##########')
    hits = []
    for spec in sorted(EN):
        tr = load_trans(spec)
        tmap = {s.get('key'): s for s in (tr.get('sections') or [])}
        for sec in EN[spec].get('sections', []):
            key = sec.get('key')
            tsec = tmap.get(key)
            if tsec is None:
                continue
            for i, e in enumerate(sec.get('flow', [])):
                c = (tsec.get('flow') or [])[i] if i < len((tsec.get('flow') or [])) else None
                if c is None:
                    continue
                # 用 EN 归一后的元素结构遍历 CN（tb 丢表头后与 CN 行对齐）
                out = []
                walk_strings(c, [spec, key, i, c.get('t')], out)
                for loc, s in out:
                    hits.append((loc, s))
    print('未翻译散文单元格总数 =', len(hits))
    for n, (loc, s) in enumerate(hits, 1):
        print('%3d. [%s] %s' % (n, loc, re.sub(r'\s+', ' ', s)[:160]))
    return hits


if __name__ == '__main__':
    main()
