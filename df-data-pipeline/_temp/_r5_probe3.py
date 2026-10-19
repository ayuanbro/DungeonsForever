# -*- coding: utf-8 -*-
"""第五轮探针 v3：全库「用户可见未翻译」扫描。
- 排除结构性枚举键：side / mark / icon / race。
- 判为未翻译：
  (a) 无 CJK 且有 >=1 个 ASCII 词（散文），且非纯 |sID|/标点；
  (b) 有 CJK 但含长英文词串（>=8 连续 ASCII 词）= 半翻译残留。
"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EN = json.load(io.open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')

CJK = re.compile(r'[\u4e00-\u9fff]')
WORD = re.compile(r'[A-Za-z][A-Za-z\'\-]*')
SID = re.compile(r'\|s\d+\|')
SKIP_KEYS = ('title', 't', 'key', 'side', 'mark', 'icon', 'race')


def clean_probe(s):
    return SID.sub(' ', s)


def is_untranslated(s):
    if not isinstance(s, str) or not s.strip():
        return None
    has_cjk = bool(CJK.search(s))
    words = WORD.findall(clean_probe(s))
    if not has_cjk:
        if len(words) == 0:
            return None
        # 纯标记（如 ":" "/"）已由 word 计数排除
        return 'pure-EN'
    # 有 CJK：按 CJK 切段，段内连续英文词 >= 6 视为半翻译残留
    segs = re.split(r'[\u4e00-\u9fff]', clean_probe(s))
    mx = 0
    for seg in segs:
        mx = max(mx, len(WORD.findall(seg)))
    if mx >= 6:
        return 'mixed(%d)' % mx
    return None


def walk(o, path, out):
    if isinstance(o, str):
        r = is_untranslated(o)
        if r:
            out.append(('>'.join(str(p) for p in path), r, o))
    elif isinstance(o, list):
        for i, x in enumerate(o):
            walk(x, path + [i], out)
    elif isinstance(o, dict):
        for k, v in o.items():
            if k in SKIP_KEYS:
                continue
            walk(v, path + [k], out)


def load_trans(spec):
    p = os.path.join(TD, spec + '.json')
    return json.load(io.open(p, encoding='utf-8')) if os.path.exists(p) else {}


def main():
    hits = []
    for spec in sorted(EN):
        tr = load_trans(spec)
        tmap = {s.get('key'): s for s in (tr.get('sections') or [])}
        for sec in EN[spec].get('sections', []):
            key = sec.get('key')
            tsec = tmap.get(key)
            if tsec is None:
                continue
            cf = tsec.get('flow') or []
            for i, c in enumerate(cf):
                out = []
                walk(c, [spec, key, i, c.get('t')], out)
                hits.extend(out)
    print('全库用户可见未翻译单元格 =', len(hits))
    for n, (loc, kind, s) in enumerate(hits, 1):
        print('%3d. [%s] %-11s %s' % (n, loc, kind, re.sub(r'\s+', ' ', s)[:150]))
    return hits


if __name__ == '__main__':
    main()
