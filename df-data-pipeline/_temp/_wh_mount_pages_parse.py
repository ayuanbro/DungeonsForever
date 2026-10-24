# -*- coding: utf-8 -*-
"""从 _temp/whb_item/*.html（已落盘的物品页）重新提取 sold-by/dropped-by/quest 来源。
修正 batch 脚本 extractDataArray 的括号回退 bug（i 被循环消耗 → slice 错位 → JSON.parse 失败）。"""
import os, re, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

RAW = '_temp/whb_item'


def extract_data_array(html, anchor):
    """从 anchor 起找 data: [ ... ] 平衡数组（字符串感知）"""
    m = re.compile(r'data:\s*\[').search(html, anchor, anchor + 4000)
    if not m:
        return None
    start = m.end() - 1  # 指向 '['
    depth = 0
    instr = False
    esc = False
    end = -1
    for i in range(start, len(html)):
        c = html[i]
        if instr:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                instr = False
        else:
            if c == '"':
                instr = True
            elif c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
    if end < 0:
        return None
    try:
        return json.loads(html[start:end])
    except Exception:
        return None


def extract(html):
    out = {}
    m = re.search(r'og:image[^>]*content="([^"]+)"', html)
    if m:
        mm = re.search(r'icons/(?:large|medium)/([a-z0-9_\-]+)\.(?:jpg|png)', m.group(1))
        if mm:
            out['icon'] = mm.group(1)
    if 'icon' not in out:
        m = re.search(r'icons/(?:large|medium)/([a-z0-9_\-]+)\.jpg', html)
        if m:
            out['icon'] = m.group(1)
    m = re.search(r'<title>([^<]+)</title>', html)
    if m:
        out['title'] = m.group(1).strip()
    for lid in ('sold-by', 'dropped-by', 'quest-reward', 'reward-from'):
        idx = html.find("id: '%s'" % lid)
        if idx < 0:
            continue
        data = extract_data_array(html, idx)
        if data:
            out[lid] = [{
                'id': r.get('id'),
                'name': r.get('name') or r.get('displayName'),
                'location': r.get('location'),
                'cost': r.get('cost'),
            } for r in data]
    return out


def main():
    result = {}
    n_sold = n_drop = n_quest = 0
    for f in sorted(os.listdir(RAW)):
        if not f.endswith('.html'):
            continue
        iid = f[:-5]
        html = open(os.path.join(RAW, f), encoding='utf-8').read()
        ex = extract(html)
        result[iid] = ex
        if ex.get('sold-by'):
            n_sold += 1
        if ex.get('dropped-by'):
            n_drop += 1
        if ex.get('quest-reward') or ex.get('reward-from'):
            n_quest += 1
    json.dump(result, open('_temp/_wh_mount_item_pages.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'parsed {len(result)} pages: sold={n_sold} drop={n_drop} quest={n_quest}')
    # 样例
    shown = 0
    for iid, ex in result.items():
        if ex.get('sold-by') and shown < 8:
            s = ex['sold-by'][0]
            print('SOLD', iid, ex.get('title', '')[:16], '->', s['name'], json.dumps(s['cost'], ensure_ascii=False))
            shown += 1
    shown = 0
    for iid, ex in result.items():
        if ex.get('dropped-by') and shown < 8:
            d = ex['dropped-by'][0]
            print('DROP', iid, ex.get('title', '')[:16], '->', d['name'], 'loc', d.get('location'))
            shown += 1
    shown = 0
    for iid, ex in result.items():
        q = ex.get('quest-reward') or ex.get('reward-from')
        if q and shown < 8:
            print('QUEST', iid, ex.get('title', '')[:16], '->', q[0]['name'])
            shown += 1


if __name__ == '__main__':
    main()
