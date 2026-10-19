# -*- coding: utf-8 -*-
"""第五轮探针：① dump druid_restoration/changes 的 EN/CN 逐元素对齐；
② 全库扫「CN 文本与 EN 完全相同（未翻译）」的元素。"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EN = json.load(io.open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')


def flat(o, acc):
    if isinstance(o, str):
        acc.append(o)
    elif isinstance(o, list):
        for x in o:
            flat(x, acc)
    elif isinstance(o, dict):
        for k, v in o.items():
            if k in ('title', 't', 'key'):
                continue
            flat(v, acc)
    return acc


def text_of(el):
    if not isinstance(el, dict):
        return ''
    return ''.join(flat({k: v for k, v in el.items() if k != 't'}, []))


def load_trans(spec):
    p = os.path.join(TD, spec + '.json')
    return json.load(io.open(p, encoding='utf-8')) if os.path.exists(p) else {}


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def dump_section(spec, key):
    tr = load_trans(spec)
    tmap = {s.get('key'): s for s in (tr.get('sections') or [])}
    sec = next((s for s in EN[spec]['sections'] if s.get('key') == key), None)
    tsec = tmap.get(key)
    ef = sec.get('flow', [])
    cf = (tsec or {}).get('flow', [])
    print('===== %s / %s  EN=%d  CN=%d =====' % (spec, key, len(ef), len(cf)))
    for i in range(max(len(ef), len(cf))):
        e = ef[i] if i < len(ef) else None
        c = cf[i] if i < len(cf) else None
        et = text_of(e) if e else ''
        ct = text_of(c) if c else ''
        same = (norm(et) == norm(ct)) if (e and c) else None
        has_cjk = bool(re.search(r'[\u4e00-\u9fff]', ct))
        flag = ''
        if same:
            flag = '  <<< CN==EN (未翻译)'
        elif not has_cjk and ct:
            flag = '  <<< CN 无中文 (疑未翻译)'
        print('[%02d] en.t=%s cn.t=%s same=%s cjk=%s%s'
              % (i, (e or {}).get('t'), (c or {}).get('t'), same, has_cjk, flag))
        print('   EN: %s' % norm(et)[:200])
        print('   CN: %s' % norm(ct)[:200])


def scan_untranslated():
    print('\n########## 全库「CN==EN 未翻译」元素 ##########')
    hits = []
    for spec in sorted(EN):
        tr = load_trans(spec)
        tmap = {s.get('key'): s for s in (tr.get('sections') or [])}
        for sec in EN[spec].get('sections', []):
            key = sec.get('key')
            tsec = tmap.get(key)
            if tsec is None:
                continue
            ef = sec.get('flow', [])
            cf = tsec.get('flow', []) or []
            for i, e in enumerate(ef):
                if i >= len(cf):
                    continue
                et = text_of(e)
                ct = text_of(cf[i])
                if not et or not ct:
                    continue
                if norm(et) == norm(ct):
                    # 纯 |sID| / 标点也算未翻译
                    hits.append((spec, key, i, e.get('t'), et))
    print('未翻译元素总数 =', len(hits))
    for n, (spec, key, i, t, et) in enumerate(hits, 1):
        print('%2d. [%s / %s #%d t=%s] %s' % (n, spec, key, i, t, norm(et)[:150]))
    return hits


if __name__ == '__main__':
    dump_section('druid_restoration', 'changes')
    scan_untranslated()
