# -*- coding: utf-8 -*-
"""探索页 · 第 2 步：解析 Warcraft Tavern 指南 → 40 本书结构化 JSON。

输入：_fc/cache/tavern_arcane_barrage.html（explore_fetch.py 的产物）
输出：_fc/data/explore_books.json
    [{name, zone, x, y, note, side, alt:[{zone,x,y,note}]}]

口径：
- 同名书在多个区域出现（如 Rumi 在洛克莫丹/西部荒野二选一）→ 合并成一条，
  第二处落 alt 列表（界面同样可标记）。
- side：正文提示「Horde players ... skip」→ 联盟限定 A；「Alliance players」→ 部落限定 H。
  只是「难拿」不算限定，只写进 note。
- 坐标来自「Location of ... at a, b」行；解析不到的书名数不对/缺坐标直接退出。
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '_fc', 'cache')
DATA = os.path.join(HERE, '_fc', 'data')

SRC = os.path.join(CACHE, 'tavern_arcane_barrage.html')
DST = os.path.join(DATA, 'explore_books.json')

# 站点本身没给坐标的条目 → 人工从 Icy-Veins 同主题页补（2026-09-24 抓取）
OVERRIDE = {
    'Magma or Lava?': {'x': 48.0, 'y': 64.0, 'zone': 'Blackrock Mountain',
                       'note': 'Blackrock Depths 入口外侧（不要进副本）'},
    'Stonewrought Design': {'x': 48.3, 'y': 64.6, 'zone': 'Blackrock Mountain',
                            'note': '铁穹堡 Franclorn Forgewright 的祭坛（BRD 入口旁台地，无需进本）'},
}

# 坐标修正：站点给的是上山路径口 / 营地泛坐标，实际书落点按 wowhead 高赞评论校正
# （2026-09-24，与 MageBookTracker 交叉验证一致）
COORD_FIX = {
    'Geomancy: The Stone-Cold Truth': {'x': 34.4, 'y': 40.2},
    # ↑ 站点 31,37 是上山路径口；wowhead 评论「34.43, 40.15 inside the large hut」
    'Runes of the Sorcerer-Kings': {'x': 77.5, 'y': 14.2},
    # ↑ 站点 74.5,19.6 是蛮兵营地泛点；wowhead 评论「North eastern most cave... Coords: 77.45, 14.16」
}

# 阵营限定：仅保留「书落在敌营主城内部、对立阵营物理无法进入」的真·限定两本。
#   - 铁炉堡（探险者大厅，联盟主城）⇒ 部落进不去 ⇒ A
#   - 奥格瑞玛（灵魂谷，部落主城）⇒ 联盟进不去 ⇒ H
# 其余 4 本一律移除：阿祖拉之塔(艾尔文森林)、布瑞尔(提瑞斯法)、银松(争夺区)、
#   Rumi(洛克莫丹+西部荒野副本，部落可走西部荒野那本) —— 都是争夺/起始区或带副本，
#   对立阵营可潜入或走另一副本拿到，并非真阵营限定（2026-10-13 按 zockify 最新页
#   与游戏机制复核：拾取本身无阵营锁，仅主城内部两本为地理性真限定）。
SIDE = {
    'Archmage Antonidas: The Unabridged Autobiography': 'A',
    "The Lessons of Ta'zo": 'H',
}


def die(msg):
    sys.stderr.write('explore_parse: %s\n' % msg)
    sys.exit(1)


def norm_name(s):
    """站点排版引号 → 游戏内常用直引号，压缩空白。"""
    s = html.unescape(s)
    s = s.replace('\u2019', "'").replace('\u2018', "'")
    s = s.replace('\u201c', '"').replace('\u201d', '"')
    return re.sub(r'\s+', ' ', s).strip()


def strip_tags(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()


def main():
    h = open(SRC, encoding='utf-8').read()
    body = h[h.find('<h2 id="ftoc-book-locations"'):]
    if not body:
        die('找不到 Book Locations 正文起点')
    body = body[:body.find('<h2 id="ftoc-wrapping-up"')] if '<h2 id="ftoc-wrapping-up"' in body else body

    heads = list(re.finditer(
        r'<h([23])[^>]*id="ftoc-([^"]+)"[^>]*>(.*?)</h\1>', body, re.S))
    if len(heads) < 20:
        die('正文标题只解析出 %d 个，疑似页面改版' % len(heads))

    books, cur_zone, last = [], None, None
    for i, m in enumerate(heads):
        lvl, title = m.group(1), norm_name(re.sub('<[^>]+>', '', m.group(3)))
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        seg = body[m.end():end]
        if lvl == '2':
            cur_zone = title
            continue
        # h3 = 书条目
        txt = strip_tags(seg)
        cm = (re.search(r'Location of[^.]*?at \(?(\d{1,3}\.\d),\s*(\d{1,3}\.\d)\)?', txt)
              or re.search(r'/way \S+ (\d{1,3}\.?\d*) (\d{1,3}\.?\d*)', txt))
        if not cm:
            # 兜底：取全文最后一对坐标（书落点通常在描述句尾点出，前面的多是路径/洞穴口）
            pairs = re.findall(r'(?:at|in)\s*\(?\s*(\d{1,3}\.\d),\s*(\d{1,3}\.\d)\s*\)?', txt)
            if not pairs:
                ov = OVERRIDE.get(title)
                if not ov:
                    die('书「%s」解析不到坐标且无覆写：%s' % (title, txt[:120]))
                x, y, cur_zone, note = ov['x'], ov['y'], ov['zone'], ov['note']
                side = None
                books.append({'name': title, 'zone': cur_zone, 'x': x, 'y': y,
                              'note': note[:180], 'side': side, 'alt': []})
                print('  [覆写] %-40s %s (%s)' % (title, ov['zone'], ov['note']))
                continue
            if len(pairs) > 1:
                print('  [多坐标] %-40s %s → 取末位' % (title, pairs))
            cm = pairs[-1]
        a, b = (cm.group(1), cm.group(2)) if hasattr(cm, 'group') else (cm[0], cm[1])
        x, y = float(a), float(b)
        fix = COORD_FIX.get(title)
        if fix:
            print('  [坐标修正] %-40s (%s, %s) -> (%s, %s)' % (title, x, y, fix['x'], fix['y']))
            x, y = fix['x'], fix['y']
        # 位置细节 = 除「Location of ...」句外的描述句（截前两句）
        desc = re.split(r'Location of', txt)[0]
        desc = re.sub(r'^This book (can be found|is located)[^.]*\.\s*', '', desc).strip()
        side = None
        if re.search(r'Horde players', desc) and re.search(r'Alliance-only|only Alliance|Alliance players can', txt):
            side = 'A'
        if re.search(r'Alliance players', desc) and re.search(r'Horde-only|only Horde|Horde players can', txt):
            side = 'H'
        note = re.sub(r'\s+', ' ', desc).strip()
        # 清掉被「Location of」切断后残留的坐标碎片前缀（如 "4, 70.1). ..."）
        note = re.sub(r'^[0-9.]+, [0-9.]+\)\.?\s*', '', note)
        rec = {'name': title, 'zone': cur_zone, 'x': x, 'y': y,
               'note': note[:180], 'side': SIDE.get(title), 'alt': []}
        dup = next((b for b in books if b['name'].lower() == title.lower()), None)
        if dup:
            dup['alt'].append({'zone': cur_zone, 'x': x, 'y': y, 'note': note[:180]})
        else:
            books.append(rec)
        last = rec

    if not 35 <= len(books) <= 45:
        die('解析出 %d 本独立书籍，不在预期 35~45 区间' % len(books))
    miss_coord = [b['name'] for b in books if not (0 < b['x'] <= 100 and 0 < b['y'] <= 100)]
    if miss_coord:
        die('坐标越界：%s' % miss_coord)

    os.makedirs(DATA, exist_ok=True)
    with open(DST, 'w', encoding='utf-8') as f:
        json.dump(books, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('解析 %d 本独立书籍（含 %d 处多位置）→ %s'
          % (len(books), sum(len(b['alt']) for b in books), os.path.relpath(DST, os.path.dirname(HERE))))
    for b in books[:6]:
        print('  %-52s %-20s (%.1f, %.1f)%s' % (b['name'], b['zone'], b['x'], b['y'],
                                                ' [%s]' % b['side'] if b['side'] else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
