# -*- coding: utf-8 -*-
import io
import json
import os

from _route_paths import ROOT, TEMP, PLAN, checked
from _route_gen import replay_amplitudes

DATA = checked(PLAN + '/data')
DST = checked(ROOT + '/Core/Data/Data_Route.lua')
OVR = checked(TEMP + '/_route_override.json')

try:
    _ovr = json.load(io.open(OVR, encoding='utf-8'))
except Exception:
    _ovr = {}


def apply_ovr(fdr, ui, segs):
    """把 override 里的改段/加段/删段合并进基础数据。"""
    if not fdr:
        return segs
    fl = (_ovr.get(fdr) or {}).get(str(ui)) or {}
    ovsegs = fl.get('segs') or {}
    if not ovsegs:
        return segs
    out = []
    seen = set()
    for s in segs:
        n = str(s.get('n'))
        v = ovsegs.get(n)
        if isinstance(v, dict) and v.get('del'):
            continue
        pts = s.get('pts') or []
        if isinstance(v, dict) and len(v.get('pts') or []) >= 2:
            pts = v['pts']
        if len(pts) >= 2:
            out.append({'n': s.get('n'), 'from': s.get('from'), 'to': s.get('to'), 'pts': pts})
            seen.add(n)
    for n, v in ovsegs.items():
        if not isinstance(v, dict) or v.get('del'):
            continue
        pts = v.get('pts') or []
        if len(pts) < 2 or str(n) in seen:
            continue
        out.append({'n': int(n), 'from': v.get('from') or '自定义起点',
                    'to': v.get('to') or '自定义终点', 'pts': pts})
    out.sort(key=lambda s: int(s.get('n') or 0))
    return out


def num(v):
    s = '%.1f' % v
    if s.endswith('.0'):
        s = s[:-2]
    return s


def pts_block(pts, indent):
    out = []
    line = []
    for p in pts:
        line.append('{ %s, %s }' % (num(p[0]), num(p[1])))
        if len(line) == 4:
            out.append(indent + ', '.join(line) + ',')
            line = []
    if line:
        out.append(indent + ', '.join(line) + ',')
    return '\n'.join(out)


def main():
    idx = json.load(io.open(DATA + '/index.json', encoding='utf-8'))
    routes = {}
    notes = {}
    for d in idx['dungeons']:
        did = d['id']
        try:
            row = json.load(io.open(DATA + '/%s.json' % did, encoding='utf-8'))
        except Exception:
            row = {}
        for f in d['floors']:
            fl_key = str(f['ui']) if f.get('ui') else ('L%d' % f['n'])
            src = row.get(str(f['ui'])) or {}
            floor_override = (_ovr.get(d.get('fdr') or did) or {}).get(fl_key) or {}
            segs = [s for s in replay_amplitudes(src, floor_override) if len(s.get('pts') or []) >= 2]
            segs = apply_ovr(d.get('fdr') or did, fl_key, segs)
            if segs:
                routes.setdefault(did, {})[f['n']] = segs
            ns = src.get('notes') or []
            if ns:
                notes.setdefault(did, {})[f['n']] = ns

    L = ['local _, ns = ...', '']
    L.append('ns.DungeonRoute = {')
    for did in sorted(routes):
        L.append('    ["%s"] = {' % did)
        for fl in sorted(routes[did]):
            L.append('        [%d] = {' % fl)
            for s in routes[did][fl]:
                L.append('            {')
                L.append('                from = "%s",' % s['from'])
                L.append('                to = "%s",' % s['to'])
                L.append('                pts = {')
                L.append(pts_block(s['pts'], '                    '))
                L.append('                },')
                L.append('            },')
            L.append('        },')
        L.append('    },')
    L.append('}')
    L.append('')
    L.append('ns.DungeonRouteNote = {')
    for did in sorted(notes):
        L.append('    ["%s"] = {' % did)
        for fl in sorted(notes[did]):
            L.append('        [%d] = {' % fl)
            for n in notes[did][fl]:
                L.append('            { %s, %s, "%s" },' % (
                    num(n['x']), num(n['y']), n['text'].replace('"', "'")))
            L.append('        },')
        L.append('    },')
    L.append('}')
    L.append('')

    txt = '\n'.join(L)
    io.open(DST, 'w', encoding='utf-8', newline='\n').write(txt)
    nseg = sum(len(v) for r in routes.values() for v in r.values())
    npt = sum(len(s['pts']) for r in routes.values() for v in r.values() for s in v)
    print('written %s %d bytes; %d dungeons %d segs %d pts %d notes' % (
        os.path.basename(DST), len(txt), len(routes), nseg, npt,
        sum(len(v) for r in notes.values() for v in r.values())))


main()
