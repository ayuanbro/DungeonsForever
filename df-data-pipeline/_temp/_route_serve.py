# -*- coding: utf-8 -*-
import io
import json
import os
import re
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from _route_paths import ROOT, TEMP, PLAN, checked, require_workspace
from _route_gen import replay_amplitudes

OVR = TEMP + '/_route_override.json'
PORT = 8766

PY = sys.executable

SHIPPED = 'blackfathom_deeps'


def run(args, timeout=240):
    try:
        p = subprocess.run([PY, '-B'] + args, cwd=TEMP, capture_output=True, timeout=timeout,
                           env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        out = (p.stdout or b'').decode('utf-8', 'replace')
        err = (p.stderr or b'').decode('utf-8', 'replace')
        return p.returncode == 0, out, err
    except subprocess.TimeoutExpired:
        return False, '', 'timeout: ' + ' '.join(args)
    except Exception as e:
        return False, '', '%s: %s' % (type(e).__name__, e)


def g(v):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, float):
        s = ('%.2f' % v).rstrip('0').rstrip('.')
        return s or '0'
    return str(v)


def fmt_pts(pts):
    return '[' + ', '.join('[%s, %s]' % (g(p[0]), g(p[1])) for p in (pts or [])) + ']'


def dump_override(d):
    L = ['{']
    keys = list(d.keys())
    for di, dk in enumerate(keys):
        L.append(' "%s": {' % dk)
        floors = list((d[dk] or {}).items())
        for fi, (f, fl) in enumerate(floors):
            L.append('  "%s": {' % f)
            blocks = []
            segs = (fl or {}).get('segs') or {}
            if segs:
                s = ['   "segs": {']
                items = list(segs.items())
                for j, (n, sv) in enumerate(items):
                    tail = ',' if j < len(items) - 1 else ''
                    if (sv or {}).get('del'):
                        s.append('    "%s": { "del": 1 }%s' % (n, tail))
                        continue
                    body = ' "pts": %s' % fmt_pts((sv or {}).get('pts'))
                    if (sv or {}).get('from'):
                        body += ', "from": "%s"' % str(sv['from']).replace('"', '')
                    if (sv or {}).get('to'):
                        body += ', "to": "%s"' % str(sv['to']).replace('"', '')
                    s.append('    "%s": {%s }%s' % (n, body, tail))
                s.append('   }')
                blocks.append('\n'.join(s))
            amp = (fl or {}).get('amp') or {}
            if amp:
                s = ['   "amp": {']
                items = list(amp.items())
                for j, (n, av) in enumerate(items):
                    s.append('    "%s": %s%s' % (n, g(av), ',' if j < len(items) - 1 else ''))
                s.append('   }')
                blocks.append('\n'.join(s))
            marks = (fl or {}).get('marks')
            if marks:
                s = ['   "marks": [']
                for j, m in enumerate(marks):
                    extra = ''
                    if m.get('hide'):
                        extra += ', "hide": 1'
                    if m.get('tip'):
                        extra += ', "tip": "%s"' % str(m.get('tip')).replace('\\', '\\\\').replace('"', '\\"')
                    s.append('    { "k": "%s", "x": %s, "y": %s%s }%s' % (
                        m.get('k'), g(m.get('x')), g(m.get('y')), extra,
                        ',' if j < len(marks) - 1 else ''))
                s.append('   ]')
                blocks.append('\n'.join(s))
            pins = (fl or {}).get('pins')
            if pins:
                s = ['   "pins": [']
                for j, p in enumerate(pins):
                    s.append('    { "en": "%s", "x": %s, "y": %s%s }%s' % (
                        str(p.get('en') or '').replace('"', ''), g(p.get('x')), g(p.get('y')),
                        ', "hide": 1' if p.get('hide') else '',
                        ',' if j < len(pins) - 1 else ''))
                s.append('   ]')
                blocks.append('\n'.join(s))
            notes = (fl or {}).get('notes')
            if notes:
                s = ['   "notes": [']
                for j, n in enumerate(notes):
                    sd = n.get('side')
                    s.append('    { "x": %s, "y": %s, "text": "%s"%s%s }%s' % (
                        g(n.get('x')), g(n.get('y')),
                        str(n.get('text') or '').replace('\\', '\\\\').replace('"', '\\"'),
                        ', "side": "%s"' % sd if sd in ('A', 'H') else '',
                        ', "hide": 1' if n.get('hide') else '',
                        ',' if j < len(notes) - 1 else ''))
                s.append('   ]')
                blocks.append('\n'.join(s))
            L.append(',\n'.join(blocks))
            L.append('  }' + (',' if fi < len(floors) - 1 else ''))
        L.append(' }' + (',' if di < len(keys) - 1 else ''))
    L.append('}')
    return '\n'.join(L) + '\n'


def summarize(dungeon):
    try:
        d = json.load(io.open(checked(PLAN + '/data/%s.json' % dungeon), encoding='utf-8'))
    except Exception:
        return '?'
    segs = sum(len(v.get('segs') or []) for v in d.values())
    pts = sum(len(s.get('pts') or []) for v in d.values() for s in (v.get('segs') or []))
    ovr = sum(1 for v in d.values() for s in (v.get('segs') or []) if s.get('ovr'))
    return '%d 层 · %d 段 · %d 点 · %d 段手改' % (len(d), segs, pts, ovr)


QOVR = TEMP + '/_route_qicon_override.json'
QTIPOVR = TEMP + '/_route_qtip_override.json'
QHIDEOVR = TEMP + '/_route_qi_hide.json'


def do_save(body):
    try:
        j = json.loads(body.decode('utf-8'))
    except Exception as e:
        return {'ok': False, 'err': 'JSON 解析失败: %s' % e}

    dungeon = j.get('dungeon') or ''
    fdr = j.get('fdr') or dungeon
    data = j.get('data')
    if not dungeon or not isinstance(data, dict) or not data:
        return {'ok': False, 'err': '缺少副本或段数据'}
    if not re.fullmatch(r'[a-z0-9_-]+', dungeon) or not re.fullmatch(r'[a-z0-9_-]+', fdr):
        return {'ok': False, 'err': '副本标识格式错误'}
    try:
        require_workspace()
        checked(OVR + '.bak')
    except (OSError, ValueError) as error:
        return {'ok': False, 'err': str(error)}

    floors = data.get('floors')
    if not isinstance(floors, dict):
        floors = data if any(isinstance(v, dict) and 'segs' in v for v in data.values()) else {}
    qicons = data.get('qicons') if isinstance(data.get('qicons'), dict) else {}
    qtips = data.get('qtips') if isinstance(data.get('qtips'), dict) else {}
    qhide = data.get('qhide') if isinstance(data.get('qhide'), dict) else {}

    if any((floor or {}).get('amp') for floor in floors.values()):
        try:
            with io.open(checked(PLAN + '/data/%s.json' % dungeon), encoding='utf-8') as source:
                baseline = json.load(source)
            with io.open(checked(PLAN + '/data/index.json'), encoding='utf-8') as source:
                index = json.load(source)
            page = next((row for row in index['dungeons'] if row['id'] == dungeon), {})
            page_floors = {str(row['ui']) if row.get('ui') else 'L%d' % row['n']: row
                           for row in page.get('floors') or []}
            for key, floor in floors.items():
                replay_amplitudes(baseline.get(str(key)) or {}, floor or {})
                replay_amplitudes(page_floors.get(str(key)) or {}, floor or {})
        except (OSError, TypeError, ValueError) as error:
            return {'ok': False, 'err': str(error)}

    try:
        cur = json.load(io.open(OVR, encoding='utf-8'))
        if not isinstance(cur, dict):
            cur = {}
    except Exception:
        cur = {}

    if os.path.exists(OVR):
        try:
            with io.open(OVR, 'r', encoding='utf-8') as f:
                old = f.read()
            with io.open(OVR + '.bak', 'w', encoding='utf-8', newline='\n') as f:
                f.write(old)
        except Exception:
            pass

    if floors:
        cur[fdr] = floors
        txt = dump_override(cur)
        with io.open(OVR, 'w', encoding='utf-8', newline='\n') as f:
            f.write(txt)
    elif not qicons and not qtips and not qhide:
        return {'ok': False, 'err': '没有可保存的改动（路段、标记与图标都为空）'}

    log = []
    if floors:
        log.append('写入 _route_override.json（%s，%d 字节）' % (fdr, len(txt)))

    if qicons:
        try:
            qcur = json.load(io.open(QOVR, encoding='utf-8'))
            if not isinstance(qcur, dict):
                qcur = {}
        except Exception:
            qcur = {}
        qcur[dungeon] = qicons
        qtxt = json.dumps(qcur, ensure_ascii=False, indent=1) + '\n'
        with io.open(QOVR, 'w', encoding='utf-8', newline='\n') as f:
            f.write(qtxt)
        log.append('写入 _route_qicon_override.json（%d 个图标）' % len(qicons))

    if qtips:
        try:
            tcur = json.load(io.open(QTIPOVR, encoding='utf-8'))
            if not isinstance(tcur, dict):
                tcur = {}
        except Exception:
            tcur = {}
        keep = {}
        old = tcur.get(dungeon)
        if isinstance(old, dict):
            for k, v in old.items():
                keep[k] = v
        for k, v in qtips.items():
            txtv = str(v).strip()
            if txtv:
                keep[k] = txtv
        tcur[dungeon] = keep
        ttxt = json.dumps(tcur, ensure_ascii=False, indent=1) + '\n'
        with io.open(QTIPOVR, 'w', encoding='utf-8', newline='\n') as f:
            f.write(ttxt)
        log.append('写入 _route_qtip_override.json（%d 条提示文字）' % len(keep))

    try:
        hcur = json.load(io.open(QHIDEOVR, encoding='utf-8'))
        if not isinstance(hcur, dict):
            hcur = {}
    except Exception:
        hcur = {}
    if qhide:
        hcur[dungeon] = {str(k): 1 for k in qhide}
    else:
        hcur.pop(dungeon, None)
    htxt = json.dumps(hcur, ensure_ascii=False, indent=1) + '\n'
    with io.open(QHIDEOVR, 'w', encoding='utf-8', newline='\n') as f:
        f.write(htxt)
    log.append('写入 _route_qi_hide.json（%d 个隐藏图标）' % len(qhide))

    steps = []
    if qicons:
        steps.append(('写回图钉数据', ['_route_write_pins.py']))
        steps.append(('重算图标清单', ['_route_qicons.py']))
    # Existing route JSON is the maintained baseline. Raw external route import
    # remains an explicit operation, separate from saving editor overrides.
    steps.append(('刷新微调页', ['_route_make_tune.py']))
    if dungeon == SHIPPED:
        steps.append(('生成 Lua', ['gen_route_lua.py']))
    for name, args in steps:
        ok, out, err = run(args)
        head = [x for x in (out or '').splitlines() if x.strip()]
        h = (head[-1] if head else '')[:120]
        log.append(('[ok] ' if ok else '[FAIL] ') + name + '  ' + h)
        if not ok:
            log.append((out + err)[-800:])
            return {'ok': False, 'err': '\n'.join(log),
                    'where': '_temp/_route_override.json'}

    log.append('[ok] 已保存到当前仓库；生成数据位于 df-data-pipeline/Core/Data')

    return {'ok': True, 'log': '\n'.join(log), 'brief': summarize(dungeon),
            'where': '_temp/_route_override.json'}


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=PLAN, **kw)

    def log_message(self, fmt, *args):
        sys.stdout.write('%s  %s\n' % (self.log_date_time_string(), fmt % args))
        sys.stdout.flush()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def do_GET(self):
        if self.path.startswith('/__save__'):
            self.js({'serve': 1})
            return
        if self.path in ('/', ''):
            self.send_response(302)
            self.send_header('Location', '/tune.html')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            return
        super().do_GET()

    def do_POST(self):
        if not self.path.startswith('/__save__'):
            self.send_error(404)
            return
        try:
            n = int(self.headers.get('Content-Length') or 0)
            body = self.rfile.read(n) if n else b''
        except Exception as e:
            self.js({'ok': False, 'err': 'read: %s' % e})
            return
        try:
            res = do_save(body)
        except Exception as e:
            res = {'ok': False, 'err': '%s: %s' % (type(e).__name__, e)}
        print('  save ->', 'ok' if res.get('ok') else 'FAIL',
              res.get('brief') or (res.get('err') or '')[:120])
        sys.stdout.flush()
        self.js(res)

    def js(self, obj):
        b = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(b)


if __name__ == '__main__':
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), H)
    print('route tune server  http://127.0.0.1:%d/tune.html' % PORT)
    print('root:', PLAN)
    srv.serve_forever()
