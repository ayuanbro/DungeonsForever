# -*- coding: utf-8 -*-
"""从副本任务数据推断「阵营」：任务（qid）直接取数据里的 A/H；注释点按名字（NPC / 任务名）反查。

- 中文名 → Core/Data/Data_DungeonQuests.lua
- 英文名 → Core/Data/enUS/Data_DungeonQuests.lua
- 只在同一副本的任务行里找，避免跨副本误配。
"""
import io
import re

from _route_paths import ROOT
ZH = ROOT + '/Core/Data/Data_DungeonQuests.lua'
EN = ROOT + '/Core/Data/enUS/Data_DungeonQuests.lua'

_did_cache = {}


def _split_cols(line):
    line = line.strip()
    if not re.match(r'\{\s*\d+\s*,', line):
        return None
    cols = []
    depth = 0
    cur = ''
    in_str = False
    esc = False
    for ch in line[1:]:
        if esc:
            cur += ch
            esc = False
            continue
        if ch == '\\':
            cur += ch
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            cur += ch
            continue
        if not in_str:
            if ch == '{':
                depth += 1
            elif ch == '}':
                if depth == 0:
                    cols.append(cur)
                    break
                depth -= 1
            elif ch == ',' and depth == 0:
                cols.append(cur)
                cur = ''
                continue
        cur += ch
    return cols


def _unq(s):
    s = (s or '').strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def _is_name(v):
    return bool(v) and v not in ('nil', 'false', 'true') and not re.match(r'^[\d\s,.{}-]+$', v)


def _block(path, did):
    try:
        s = io.open(path, encoding='utf-8').read()
    except Exception:
        return ''
    m = re.search(r'\["%s"\]\s*=\s*\{(.*?)\n\s*\},' % re.escape(did), s, re.S)
    return m.group(1) if m else ''


def _rows(path, did):
    out = []
    for line in _block(path, did).split('\n'):
        cols = _split_cols(line)
        if not cols or len(cols) < 17:
            continue
        qid = _unq(cols[0])
        try:
            qid = int(qid)
        except Exception:
            continue
        side = _unq(cols[1]).upper()
        if side not in ('A', 'H'):
            side = None
        out.append({'qid': qid, 'side': side, 'cols': cols})
    return out


def _names(cols, zh):
    """一行里能当「可匹配名字」的串：起始/结束 NPC + 引号里的任务名。"""
    out = []
    for idx in (4, 16):
        if idx < len(cols):
            v = _unq(cols[idx])
            if _is_name(v):
                out.append(v)
    for idx in (10, 11):
        if idx >= len(cols):
            continue
        body = _unq(cols[idx])
        if not body:
            continue
        if zh:
            out.extend(re.findall(r'《([^》]{2,30})》', body))
        out.extend(re.findall(r'"([^"]{2,40})"', body))
    return out


def index(did):
    """did -> {'qid': {qid: side}, 'zh': [(name, side)], 'en': [(name, side)]}"""
    if did in _did_cache:
        return _did_cache[did]
    qmap = {}
    zh_names = []
    en_names = []
    for row in _rows(ZH, did):
        qmap[row['qid']] = row['side']
        for nm in _names(row['cols'], True):
            zh_names.append((nm, row['side']))
    for row in _rows(EN, did):
        for nm in _names(row['cols'], False):
            en_names.append((nm, row['side']))
    idx = {'qid': qmap, 'zh': zh_names, 'en': en_names}
    _did_cache[did] = idx
    return idx


def quest_side(did, qid):
    return index(did)['qid'].get(int(qid)) if qid else None


def _lcs_len(a, b):
    if not a or not b:
        return 0
    best = 0
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0] * (len(b) + 1)
        for j, cb in enumerate(b, 1):
            if ca == cb:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def _match(text, pairs, fuzzy):
    if not text:
        return None
    low = text.lower()
    hits = {}
    for nm, side in pairs:
        if not side or len(nm) < 3:
            continue
        ln = nm.lower()
        if ln in low:
            hits[side] = max(hits.get(side, 0), len(nm))
            continue
        if fuzzy:
            r = _lcs_len(ln, low) / float(len(ln))
            if r >= 0.72 and _lcs_len(ln, low) >= 3:
                hits[side] = max(hits.get(side, 0), int(len(nm) * r))
    if not hits:
        return None
    best = max(hits.values())
    tops = [k for k, v in hits.items() if v == best]
    return tops[0] if len(tops) == 1 else None


def note_side(did, text, raw=''):
    """注释点阵营推断：先按英文原名（更准），再按中文名。冲突或找不到 -> None（通用）。"""
    idx = index(did)
    s = _match(raw or '', idx['en'], False)
    if s:
        return s
    return _match(text or '', idx['zh'], True)


if __name__ == '__main__':
    import json
    import glob
    import os
    data = json.load(io.open(ROOT + '/_temp/_route_plan/data/index.json', encoding='utf-8'))
    tot = ha = hh = hn = 0
    for d in data['dungeons']:
        did = d['id']
        c = {'A': 0, 'H': 0, None: 0}
        for fl in d.get('floors') or []:
            for n in fl.get('notes') or []:
                s = note_side(did, n.get('text'), n.get('raw'))
                c[s] = c.get(s, 0) + 1
        if sum(c.values()):
            print('%-26s A=%2d H=%2d 通用=%2d' % (did, c['A'], c['H'], c[None]))
        tot += sum(c.values())
        ha += c['A']
        hh += c['H']
        hn += c[None]
    print('total notes %d  A=%d H=%d 通用=%d (%.0f%% 已判定)' % (tot, ha, hh, hn, (ha + hh) * 100.0 / max(1, tot)))
