# -*- coding: utf-8 -*-
"""商人阵营回填 · wowhead NPC 页 Reaction 解析（方案 A 第 1 步）。

背景：配方来源 vendors[] 没有 side 字段 ⇒ 部落玩家能看到联盟商人。
本步给每个商人 NPC 抓 wowhead 页，解析「反应 Reaction」行 → side：
    'a' = 仅联盟可见 / 'h' = 仅部落可见 / 不写 = 中立或未知（双方可见，运行时兜底）

产物 `_fc/data/vendor_side.json`：{ "商人英文原名": "a"|"h" }
  · 键 = 英文原名（与 vendor_loc.json 同口径，fc_gen inject 在 localize 之前）；
  · 抓不到页 / 页里没有 Reaction 行的商人**不写入**（保持双方可见兜底）；
  · 可无限重跑：每个 NPC 的 HTML 落 `_fc/cache_wh_side/`，已成功的直接跳过。

★ 通道：wowhead 对本机/代理 IP 有时段性封锁（2026-10-10 21:15 实测 curl_cffi
  202 挑战 + jina 403）。curl_cffi（Chrome 指纹）优先、jina 兜底，整轮撞墙就
  sleep 后重试下一轮 —— 反正缓存落了就永久有效，磨到 WAF 放行为止。

用法：
    python fc_vendor_side.py            # 主流程（联网，可中断重跑）
    python fc_vendor_side.py --parse    # 只对缓存重新解析（不联网；调正则用）
    python fc_vendor_side.py --report   # 覆盖率对账
"""
import argparse
import glob
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DATA = os.path.join(HERE, '_fc', 'data')
VLOC = os.path.join(DATA, 'vendor_loc.json')
OUT = os.path.join(DATA, 'vendor_side.json')
CACHE = os.path.join(HERE, '_fc', 'cache_wh_side')
PROXY = 'http://127.0.0.1:7897'
SLEEP = 1.5          # 成功抓页后的节流
WAF_WAIT = 90        # 整轮被 WAF 拦后的等待（秒）


def load_json(path, default):
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    return default


def vendor_id_map():
    """配方来源里的全部商人英文名 → {id, zone}（id 可能缺，缺的跳过）。"""
    out = {}
    for f in glob.glob(os.path.join(DATA, 'prof_*.json')):
        d = json.load(open(f, encoding='utf-8'))
        for coll in ('rows', 'enchants', 'crafted'):
            for r in d.get(coll) or []:
                src = r.get('source')
                if not isinstance(src, dict):
                    continue
                for v in src.get('vendors') or []:
                    if isinstance(v, dict) and v.get('name'):
                        ent = out.setdefault(v['name'], {})
                        if v.get('id'):
                            ent['id'] = int(v['id'])
    vloc = load_json(VLOC, {})
    for name, ent in out.items():
        if not ent.get('id') and isinstance(vloc.get(name), dict) and vloc[name].get('id'):
            ent['id'] = int(vloc[name]['id'])
    return {k: v['id'] for k, v in out.items() if v.get('id')}


# ---------------------------------------------------------------- 抓取

def _cffi_get(url, dst):
    from curl_cffi import requests as cr
    try:
        r = cr.get(url, impersonate='chrome',
                   proxies={'http': PROXY, 'https': PROXY}, timeout=60)
    except Exception:
        return None
    if r.status_code == 200 and len(r.text) > 3000 and 'awsWafCookieDomainList' not in r.text:
        open(dst, 'w', encoding='utf-8').write(r.text)
        return True
    return False


def _jina_get(url, dst):
    full = 'https://r.jina.ai/' + url
    cmd = ['curl', '-s', '-m', '90', '-x', PROXY, '-H', 'x-return-format: html',
           '-o', dst, '-w', '%{http_code}', full]
    try:
        r = __import__('subprocess').run(cmd, capture_output=True, text=True)
    except Exception:
        return False
    if (r.stdout or '').strip() == '200':
        txt = open(dst, encoding='utf-8', errors='replace').read()
        if len(txt) > 3000 and 'awsWafCookieDomainList' not in txt:
            return True
    if os.path.exists(dst):
        os.remove(dst)
    return False


def fetch_npc(nid, branch='forever'):
    """抓 forever 分支 NPC 页（404 时退 wotlk/classic 试经典老 NPC）。返回 (ok, html)。"""
    dst = os.path.join(CACHE, '%d.html' % nid)
    if os.path.exists(dst) and os.path.getsize(dst) > 3000:
        return True, open(dst, encoding='utf-8', errors='replace').read()
    for br in (branch, 'wotlk', 'classic'):
        url = 'https://www.wowhead.com/%s/cn/npc=%d' % (br, nid)
        if _cffi_get(url, dst) or _jina_get(url, dst):
            return True, open(dst, encoding='utf-8', errors='replace').read()
        if br == branch and os.path.exists(dst):
            os.remove(dst)
    return False, None


# ---------------------------------------------------------------- 解析

RE_ROW = re.compile(
    r'(反应|Reaction)[^<]{0,40}</th>\s*<td[^>]*>(.{0,300}?)</td>', re.S)
RE_EV = re.compile(
    r'(alliance|horde)[-_\w]{0,30}(reaction)?', re.I)
RE_AH = re.compile(r'["\s>]A["\s<].{0,120}?["\s>]H["\s<]', re.S)


def parse_side(html, nid, evidence):
    """从 NPC 页 HTML 推 side。返回 'a' / 'h' / None。

    思路：找「反应/Reaction」表行 → 在该行 300 字符里数联盟/部落标记；
    标记 = class/id 里含 alliance|horde 的元素（wowhead 的 A/H 徽记）。
    只有 A → 'a'；只有 H → 'h'；两个都有（或一个都没有）→ None（中立/未知）。
    首次命中把证据片段存进 evidence dict，便于人工核对正则。
    """
    if not html:
        return None
    m = RE_ROW.search(html)
    seg = m.group(2) if m else None
    if seg is None:
        # 兜底：全文找 alliance-reaction / horde-reaction 这类专用 class
        seg = html
    a = len(re.findall(r'alliance[-_]reaction|icon-alliance|"alliance"', seg, re.I))
    h = len(re.findall(r'horde[-_]reaction|icon-horde|"horde"', seg, re.I))
    if seg is html or (a == 0 and h == 0):
        # 行没抓到标记时做一次证据采样（每 NPC 只记一次，控制日志体积）
        if nid not in evidence:
            ev = RE_EV.findall(seg[:200000])
            if ev:
                evidence[nid] = sorted(set(e[0].lower() for e in ev))[:6]
        if a == 0 and h == 0:
            return None
    if a > 0 and h == 0:
        return 'a'
    if h > 0 and a == 0:
        return 'h'
    return None


def collect():
    os.makedirs(CACHE, exist_ok=True)
    ids = vendor_id_map()
    sides = load_json(OUT, {})
    todo = {n: i for n, i in ids.items() if n not in sides}
    print('商人 %d 个 · 已回填 %d · 待抓 %d' % (len(ids), len(sides) - 0, len(todo)))
    evidence = {}
    names = sorted(todo, key=lambda n: todo[n])
    while names:
        blocked = 0
        for name in list(names):
            nid = todo[name]
            ok, html = fetch_npc(nid)
            if not ok:
                blocked += 1
                print('  WAF/403 %s (npc=%d) 本轮拦 %d' % (name, nid, blocked), flush=True)
                if blocked >= 8:
                    break
                continue
            side = parse_side(html, nid, evidence)
            if side:
                sides[name] = side
            # side=None：中立或页面无 Reaction → 不写（双方可见兜底），但也要移出队列
            names.remove(name)
            if evidence.get(nid) and len(evidence) < 6:
                print('  证据 npc=%d: %s' % (nid, evidence[nid]), flush=True)
            print('  npc=%d %s -> %s（剩 %d）' % (nid, name, side or '中立/未知', len(names)), flush=True)
            time.sleep(SLEEP)
        if names and blocked >= 8:
            print('整轮被拦，睡 %ds 再来…' % WAF_WAIT, flush=True)
            time.sleep(WAF_WAIT)
        elif not names:
            break
        else:
            time.sleep(10)
    json.dump(sides, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('vendor_side.json：共 %d 条（联盟 %d / 部落 %d）'
          % (len(sides), sum(1 for v in sides.values() if v == 'a'),
             sum(1 for v in sides.values() if v == 'h')))


def parse_only():
    """对缓存里的 HTML 重新解析（调正则时用，不联网）。"""
    ids = vendor_id_map()
    sides = load_json(OUT, {})
    evidence = {}
    name_by_id = {}
    for n, i in ids.items():
        name_by_id.setdefault(i, n)
    for f in glob.glob(os.path.join(CACHE, '*.html')):
        nid = int(os.path.basename(f)[:-5])
        name = name_by_id.get(nid)
        if not name:
            continue
        side = parse_side(open(f, encoding='utf-8', errors='replace').read(), nid, evidence)
        if side:
            sides[name] = side
        else:
            sides.pop(name, None)
    json.dump(sides, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('重解析完成：%d 条（联盟 %d / 部落 %d）· 有证据样本 %d'
          % (len(sides), sum(1 for v in sides.values() if v == 'a'),
             sum(1 for v in sides.values() if v == 'h'), len(evidence)))
    for nid, ev in list(evidence.items())[:6]:
        print('  证据 npc=%d: %s' % (nid, ev))


def report():
    ids = vendor_id_map()
    sides = load_json(OUT, {})
    a = sum(1 for v in sides.values() if v == 'a')
    h = sum(1 for v in sides.values() if v == 'h')
    print('商人总数 %d · 已判 side %d（a=%d / h=%d）· 中立或未抓 %d'
          % (len(ids), len(sides), a, h, len(ids) - len(sides)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--parse', action='store_true')
    ap.add_argument('--report', action='store_true')
    args = ap.parse_args()
    if args.report:
        report()
    elif args.parse:
        parse_only()
    else:
        collect()
