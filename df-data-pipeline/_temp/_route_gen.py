# -*- coding: utf-8 -*-
import io
import json
import math
import re

W, H = 1002.0, 668.0
FR = 'D:/Game/World of Warcraft/_cn_beta_/Interface/AddOns/ForeverDungeonRoutes/Data/DefaultRoutes.lua'
BP = 'D:/workspace/DungeonsForever/Core/Data/Data_BossPos.lua'
OUT = 'D:/workspace/DungeonsForever/_temp/_route_plan/route.json'
OVR = 'D:/workspace/DungeonsForever/_temp/_route_override.json'

DUNGEON = 'blackfathom'
DUNGEON_ID = 'blackfathom_deeps'

FLOOR_KEY = {221: 1, 222: 2, 223: 3}
SNAP = 9.0
AMP = 4.2


def load_override(dkey=None):
    try:
        d = json.load(io.open(OVR, encoding='utf-8'))
    except Exception:
        return {}
    return d.get(dkey or DUNGEON) or {}


def parse_fdr(key):
    s = io.open(FR, encoding='utf-8').read()
    m = re.search(r'DR\.DefaultRoutes\["%s"\] = \{(.*?)\n\}\n' % key, s, re.S)
    body = m.group(1)
    paths = []
    for pm in re.finditer(r'\{kind="(main|side)", floor=(\d+),(.*?)pts=\{([^}]*)\}\}', body):
        nums = [float(x) for x in pm.group(4).split(',') if x.strip()]
        pts = [(nums[i] * 100, nums[i + 1] * 100) for i in range(0, len(nums) - 1, 2)]
        t0 = re.search(r't0=([\d.]+)', pm.group(3))
        t1 = re.search(r't1=([\d.]+)', pm.group(3))
        title = re.search(r'title="([^"]*)"', pm.group(3))
        paths.append({
            'kind': pm.group(1), 'floor': int(pm.group(2)), 'pts': pts,
            't0': float(t0.group(1)) if t0 else 0.0,
            't1': float(t1.group(1)) if t1 else 1.0,
            'title': title.group(1) if title else '',
        })
    stops = []
    for sm in re.finditer(r'\{kind="(\w+)", floor=(\d+), x=([\d.]+), y=([\d.]+), name="([^"]*)"(.*?)\}', body):
        tail = sm.group(6)
        cn = re.search(r'nameCN="([^"]*)"', tail)
        stops.append({'kind': sm.group(1), 'floor': int(sm.group(2)),
                      'x': float(sm.group(3)) * 100, 'y': float(sm.group(4)) * 100,
                      'en': sm.group(5), 'cn': cn.group(1) if cn else sm.group(5)})
    notes = []
    for nm in re.finditer(r'\{floor=(\d+), x=([\d.]+), y=([\d.]+), text="([^"]*)"', body):
        notes.append({'floor': int(nm.group(1)),
                      'x': float(nm.group(2)) * 100, 'y': float(nm.group(3)) * 100,
                      'text': nm.group(4)})
    return paths, stops, notes


def parse_boss_pos(dungeon):
    s = io.open(BP, encoding='utf-8').read()
    m = re.search(r'\["%s"\] = \{(.*?)\n    \},' % dungeon, s, re.S)
    body = m.group(1)
    out = {}
    for row in re.finditer(r'\["([^"]+)"\] = \{([^}]*\}[^}]*)?\}', body):
        name = row.group(1)
        pts = []
        for pm in re.finditer(r'\{\s*([\d.]+),\s*([\d.]+)(?:,\s*(\d+))?\s*\}', row.group(0)):
            pts.append({'x': float(pm.group(1)), 'y': float(pm.group(2)),
                        'f': int(pm.group(3)) if pm.group(3) else 1})
        out[name] = pts
    return out


def rdp(pts, eps):
    if len(pts) < 3:
        return pts[:]
    keep = {0, len(pts) - 1}

    def rec(i, j):
        if j <= i + 1:
            return
        ax, ay = pts[i]
        bx, by = pts[j]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy) or 1e-9
        best, bk = -1.0, -1
        for k in range(i + 1, j):
            px, py = pts[k]
            d = abs(dx * (py - ay) - dy * (px - ax)) / L
            if d > best:
                best, bk = d, k
        if best > eps:
            keep.add(bk)
            rec(i, bk)
            rec(bk, j)

    rec(0, len(pts) - 1)
    return [pts[k] for k in sorted(keep)]


def cumlen(pts):
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    return cum


def project(pts, cum, x, y, min_s=0.0):
    best = (1e9, 0, 0.0)
    for i in range(1, len(pts)):
        ax, ay = pts[i - 1]
        bx, by = pts[i]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy or 1e-9
        u = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L2))
        px, py = ax + dx * u, ay + dy * u
        d = math.hypot(px - x, py - y)
        s = cum[i - 1] + (cum[i] - cum[i - 1]) * u
        if s < min_s - 1e-6:
            continue
        if d < best[0]:
            best = (d, i, u)
    d, i, u = best
    if d > 1e8:
        return 1e9, len(pts) - 1, 0.0, cum[-1]
    s = cum[i - 1] + (cum[i] - cum[i - 1]) * u
    return d, i, u, s


def jitter(vals, amp, freq, phase):
    return amp * (0.68 * math.sin(2 * math.pi * freq * vals + phase)
                  + 0.32 * math.sin(2 * math.pi * freq * 2.9 * vals + phase * 1.7))


def build_seg(pts, s0, s1, cum, start_pin, end_pin, amp, seed):
    total = cum[-1] or 1.0
    out = []
    for i in range(len(pts)):
        s = cum[i]
        if s < s0 - 1e-6 or s > s1 + 1e-6:
            continue
        out.append([pts[i][0], pts[i][1], (s - s0) / max(1e-6, s1 - s0)])
    if not out:
        out.append([pts[0][0], pts[0][1], 0.0])
    for i in range(1, len(pts)):
        if cum[i - 1] < s0 < cum[i]:
            u = (s0 - cum[i - 1]) / (cum[i] - cum[i - 1])
            out.insert(0, [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * u,
                           pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * u, 0.0])
            break
    for i in range(1, len(pts)):
        if cum[i - 1] < s1 < cum[i]:
            u = (s1 - cum[i - 1]) / (cum[i] - cum[i - 1])
            out.append([pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * u,
                        pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * u, 1.0])
            break
    res = []
    n = len(out)
    head, tail = out[0], out[-1]
    warpA = (start_pin[0] - head[0], start_pin[1] - head[1]) if start_pin else (0.0, 0.0)
    warpB = (end_pin[0] - tail[0], end_pin[1] - tail[1]) if end_pin else (0.0, 0.0)
    for k, (x, y, u) in enumerate(out):
        wx = warpA[0] * (1 - u) ** 1.4 + warpB[0] * u ** 1.4
        wy = warpA[1] * (1 - u) ** 1.4 + warpB[1] * u ** 1.4
        if 0 < k < n - 1:
            ax, ay = out[k - 1][0], out[k - 1][1]
            bx, by = out[k + 1][0], out[k + 1][1]
            dx, dy = bx - ax, by - ay
            L = math.hypot(dx, dy) or 1e-9
            nx, ny = -dy / L, dx / L
            w = min(1.0, min(k, n - 1 - k) / 2.0)
            d = jitter(u, amp, 1.25, seed) * w
            x += nx * d
            y += ny * d
        res.append([round(x + wx, 2), round(y + wy, 2)])
    return res


def bez(pts, step=8.0):
    n = len(pts)
    if n < 3:
        return pts
    cur = [[p[0], p[1]] for p in pts]
    for _ in range(1):
        nxt = [cur[0][:]]
        for i in range(len(cur) - 1):
            p, q = cur[i], cur[i + 1]
            nxt.append([0.72 * p[0] + 0.28 * q[0], 0.72 * p[1] + 0.28 * q[1]])
            nxt.append([0.28 * p[0] + 0.72 * q[0], 0.28 * p[1] + 0.72 * q[1]])
        nxt.append(cur[-1][:])
        cur = nxt
    return [[round(x, 2), round(y, 2)] for x, y in cur]


def replay_amplitudes(floor, override):
    """Replay saved raw paths without reading external FDR or boss-position files.

    Keep the raw-path order and repeated segment numbers: the original generator
    restarts numbering for every main path and applies the same amp to each one.
    Verify the reconstructed baseline before using it instead of guessing when
    a manually maintained floor no longer matches its saved source geometry.
    """
    segments = floor.get('segs') or []
    manual = override.get('segs') or {}
    amplitudes = {}
    for number, value in (override.get('amp') or {}).items():
        edit = manual.get(str(number)) or {}
        if edit.get('del') or len(edit.get('pts') or []) >= 2:
            continue
        amplitude = float(value)
        if not math.isfinite(amplitude):
            raise ValueError('路线 amp 必须是有限数值')
        amplitudes[str(number)] = amplitude
    if not amplitudes:
        return segments
    if not set(amplitudes).issubset({str(s.get('n')) for s in segments}):
        raise ValueError('路线 amp 引用了不存在的路段')

    side_paths = [side['pts'] for side in floor.get('sides') or []]
    rebuilt = []
    for raw in floor.get('raw') or []:
        if len(raw) < 2 or any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in raw):
            raise ValueError('路线 amp 缺少有效原始坐标')
        points = rdp(raw, 1.0)
        # Consume side paths one at a time, preserving duplicate raw paths.
        if points in side_paths:
            side_paths.remove(points)
            continue
        cumulative = cumlen(points)
        total = cumulative[-1]
        if total <= 0:
            raise ValueError('路线 amp 原始路径长度为零')
        anchors = []
        for stop in floor.get('stops') or []:
            best = None
            for pin in stop.get('pins') or []:
                distance, _, _, position = project(points, cumulative, pin[0], pin[1])
                if best is None or distance < best[0]:
                    best = (distance, position, pin)
            if best is not None and best[0] <= SNAP:
                anchors.append((best[1], best[2], stop['cn']))
        anchors.sort(key=lambda value: value[0])
        previous_position, previous_pin = 0.0, None
        for index, anchor in enumerate(anchors + [None]):
            position = anchor[0] if anchor else total
            end_pin = anchor[1] if anchor else points[-1]
            number = str(index + 1)
            baseline = build_seg(points, previous_position, position, cumulative,
                                 previous_pin, end_pin, AMP, index * 1.11)
            if len(baseline) >= 2 and (position - previous_position) > total * 0.012:
                def finish(control):
                    if previous_pin:
                        control[0] = [round(v, 2) for v in previous_pin]
                    control[-1] = [round(v, 2) for v in end_pin]
                    return bez(control, 7.0)

                baseline_points = finish(baseline)
                output_points = baseline_points
                if number in amplitudes:
                    output_points = finish(build_seg(
                        points, previous_position, position, cumulative,
                        previous_pin, end_pin, amplitudes[number], index * 1.11))
                rebuilt.append((index + 1, '入口' if index == 0 else anchors[index - 1][2],
                                anchor[2] if anchor else '出口', baseline_points, output_points))
            if anchor:
                previous_position, previous_pin = position, end_pin
    if side_paths or len(rebuilt) != len(segments):
        raise ValueError('路线 amp 原始路径与现有路段不一致，请先核对路线基线')
    result = []
    for segment, generated in zip(segments, rebuilt):
        if (segment.get('n'), segment.get('from'), segment.get('to')) != generated[:3]:
            raise ValueError('路线 amp 路段顺序与原始路径不一致')
        if not segment.get('ovr') and segment.get('pts') != generated[3]:
            raise ValueError('路线 amp 基线几何与原始路径不一致')
        row = dict(segment)
        if str(segment['n']) in amplitudes:
            row.update(pts=generated[4], ovr=False)
        result.append(row)
    return result


def gen(fdr_key=None, dungeon_id=None, floor_uids=None, floor_key=None, out_path=None):
    fdr_key = fdr_key or DUNGEON
    dungeon_id = dungeon_id or DUNGEON_ID
    floor_key = floor_key or FLOOR_KEY
    out_path = out_path or OUT
    paths, stops, notes = parse_fdr(fdr_key)
    bp = parse_boss_pos(dungeon_id)
    ovr_all = load_override(fdr_key)
    floors = {}
    for f in (floor_uids or (221, 222, 223)):
        floors[str(f)] = {'segs': [], 'sides': [], 'stops': [], 'notes': [],
                          'loose': [], 'raw': [], 'entrance': None}

    for p in paths:
        fl = str(p['floor'])
        sp = rdp(p['pts'], 1.0)
        cum = cumlen(sp)
        group = floors[fl]
        group['raw'].append([[round(x, 2), round(y, 2)] for x, y in p['pts']])
        if p['kind'] == 'side':
            group['sides'].append({'title': p['title'], 'pts': [[round(x, 2), round(y, 2)] for x, y in sp]})
            continue
        on = []
        for st in stops:
            if st['floor'] != p['floor']:
                continue
            cands = [q for q in bp.get(st['en'], []) if q['f'] == floor_key[p['floor']]]
            if not cands:
                cands = [q for q in bp.get(st['en'], [])]
            if not cands:
                continue
            best = None
            for c in cands:
                d, i, u, s = project(sp, cum, c['x'], c['y'], 0.0)
                if best is None or d < best[0]:
                    best = (d, i, u, s, c)
            if best[0] <= SNAP:
                on.append({'st': st, 's': best[3], 'pin': [best[4]['x'], best[4]['y']], 'd': best[0]})
            else:
                group['loose'].append({'st': st, 'pin': [best[4]['x'], best[4]['y']], 'd': round(best[0], 2)})
        on.sort(key=lambda z: z['s'])
        for o in on:
            print('    anchor %-16s s=%.3f d=%.2f pin=(%.1f,%.1f)' % (
                o['st']['cn'], o['s'], o['d'], o['pin'][0], o['pin'][1]))
        prev_s = 0.0
        prev_pin = None
        idx = 0
        total = cum[-1] or 1.0
        ov_here = ovr_all.get(fl) or {}
        ov_segs = ov_here.get('segs') or {}
        ov_amp = ov_here.get('amp') or {}
        for o in on + [None]:
            seg_s = o['s'] if o else total
            end_pin = o['pin'] if o else [sp[-1][0], sp[-1][1]]
            start_pin = prev_pin
            seg_no = str(idx + 1)
            amp_here = float(ov_amp.get(seg_no, AMP))
            seg = build_seg(sp, prev_s, seg_s, cum, start_pin, end_pin, amp_here, idx * 1.11)
            manual = ov_segs.get(seg_no) or {}
            ctrl = manual.get('pts') or []
            is_ovr = len(ctrl) >= 2
            if len(seg) >= 2 and ((seg_s - prev_s) > total * 0.012 or is_ovr):
                seg[0] = [round(prev_pin[0], 2), round(prev_pin[1], 2)] if prev_pin else seg[0]
                seg[-1] = [round(end_pin[0], 2), round(end_pin[1], 2)]
                t0 = p['t0'] + (p['t1'] - p['t0']) * (prev_s / total)
                t1 = p['t0'] + (p['t1'] - p['t0']) * (seg_s / total)
                if is_ovr:
                    ctrl = [[round(float(q[0]), 2), round(float(q[1]), 2)] for q in ctrl]
                    if prev_pin:
                        ctrl[0] = [round(prev_pin[0], 2), round(prev_pin[1], 2)]
                    ctrl[-1] = [round(end_pin[0], 2), round(end_pin[1], 2)]
                    pts_out = bez(ctrl, 7.0)
                else:
                    pts_out = bez(seg, 7.0)
                group['segs'].append({
                    'n': idx + 1,
                    'from': '入口' if idx == 0 else on[idx - 1]['st']['cn'],
                    'to': o['st']['cn'] if o else '出口',
                    't0': round(t0, 4), 't1': round(t1, 4),
                    'pts': pts_out,
                    'ovr': is_ovr,
                })
            if o:
                prev_s = seg_s
                prev_pin = end_pin
                idx += 1
        if group['segs'] and not group['entrance']:
            group['entrance'] = group['segs'][0]['pts'][0]

    for st in stops:
        fl = str(st['floor'])
        q = [x for x in bp.get(st['en'], []) if x['f'] == floor_key[st['floor']]]
        if not q:
            q = bp.get(st['en'], [])
        if not q:
            continue
        floors[fl]['stops'].append({
            'en': st['en'], 'cn': st['cn'], 'kind': st['kind'],
            'pins': [[x['x'], x['y']] for x in q],
        })

    text_map = {
        'Lorgalis Manuscript (quest)': '洛迦利斯手稿（任务道具）',
        'Click the shrine for a buff': '摸一下神龛，拿增益',
        'Argent Guard Thaelrid (quest)': '银色守卫塞尔瑞德（交任务）',
        'Lorgus Jett can also be here': '洛古斯·杰特也可能刷在这里',
        'Fathom Stone: summons Baron Aquanis': '深渊之石：召唤阿奎尼斯男爵',
        'Jump into the water and swim under the shrine to reach the Forgotten Pool': '跳进水里，从神龛底下游到遗忘之池',
        'Light the braziers and defeat the waves to open the door': '点亮火盆，清完几波怪开门',
    }
    for nt in notes:
        floors[str(nt['floor'])]['notes'].append({
            'x': nt['x'], 'y': nt['y'],
            'text': text_map.get(nt['text'], nt['text']),
            'raw': nt['text'],
        })

    with io.open(out_path, 'w', encoding='utf-8') as f:
        json.dump(floors, f, ensure_ascii=False, indent=1)
    for k, v in floors.items():
        print(k, 'segs', len(v['segs']), 'sides', len(v['sides']),
              'stops', len(v['stops']), 'notes', len(v['notes']), 'loose', len(v['loose']))
        for s in v['segs']:
            print('   seg', s['n'], s['from'], '->', s['to'], 'pts', len(s['pts']),
                  't %.3f-%.3f' % (s['t0'], s['t1']), '[override]' if s.get('ovr') else '')
        for l in v['loose']:
            print('   loose', l['st']['cn'], l['d'])


def main():
    gen()


if __name__ == '__main__':
    main()
