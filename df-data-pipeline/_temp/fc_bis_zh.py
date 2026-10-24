# -*- coding: utf-8 -*-
"""BIS 来源英文残留汉化管线（2026-10-07）
1. 任务名：缓存 HTML 的 /zh-cn/quest/<id> 链接 → nether.wowhead classic/cn tooltip 取官方中文名
2. 区域名：内置静态官方译名表
3. NPC/杂项：人工/搜索补充表
结果全部落到 _fc_bis/name_zh.json，fc_bis.py 生成时用 zh_note() 替换 note 里的英文。
"""
import io, re, json, time, html as htmllib, os, sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
MAP_PATH = os.path.join(HERE, '_fc_bis', 'name_zh.json')

# ── 区域名：官方经典旧世中文译名（稳定，无需联网） ──────────────────────────
ZONES = {
    'Redridge Mountains': '赤脊山',
    'The Barrens': '贫瘠之地',
    'Ashenvale': '灰谷',
    'Stonetalon Mountains': '石爪山脉',
    'Dun Morogh': '丹莫罗',
    'Orgrimmar': '奥格瑞玛',
    'Silverpine Forest': '银松森林',
    'Darnassus': '达纳苏斯',
    'Thunder Bluff': '雷霆崖',
    'Stranglethorn Vale': '荆棘谷',
    'Burning Steppes': '燃烧平原',
    'Wetlands': '湿地',
    'Alterac Mountains': '奥特兰克山脉',
    'Mulgore': '莫高雷',
    'Loch Modan': '洛克莫丹',
    'Arathi Highlands': '阿拉希高地',
    'Duskwood': '暮色森林',
    'Stormwind City': '暴风城',
    'Ironforge': '铁炉堡',
    'Undercity': '幽暗城',
}

# ── NPC/杂项英文名：wowhead 能查到的查，查不到的在这里人工补 ─────────────────
NPC_EXTRA = {
    # 例：'Prospector Ironband': '勘探员铁带',
}


def load_map():
    if os.path.exists(MAP_PATH):
        return json.load(io.open(MAP_PATH, encoding='utf-8'))
    return {'quests': {}, 'names': {}}


def save_map(mp):
    io.open(MAP_PATH, 'w', encoding='utf-8').write(
        json.dumps(mp, ensure_ascii=False, indent=1, sort_keys=True))


def fetch_quest_names(ids):
    """{en: [ids]} → 逐个 nether classic/cn tooltip 取中文名，返回 {en: zh}"""
    from curl_cffi import requests as cr
    proxies = {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}
    out = {}
    total = len(ids)
    for i, (en, qids) in enumerate(sorted(ids.items()), 1):
        for qid in qids:
            url = 'https://nether.wowhead.com/classic/cn/tooltip/quest/%d' % qid
            zh = None
            for attempt in range(3):
                try:
                    r = cr.get(url, impersonate='firefox133', timeout=20, proxies=proxies)
                    if r.status_code == 200:
                        j = r.json()
                        n = (j.get('name') or '').strip()
                        # 排除明显无效
                        if n and not n.lower().startswith('unknown'):
                            zh = n
                    break
                except Exception:
                    time.sleep(3 + 3 * attempt)
            if zh:
                out[en] = zh
                break
        if i % 10 == 0 or i == total:
            print('  quest %d/%d, 命中 %d' % (i, total, len(out)), flush=True)
        time.sleep(0.6)
    return out


def main():
    mp = load_map()
    raw_path = os.path.join(HERE, '_fc_bis', 'quest_map_raw.json')
    if not os.path.exists(raw_path):
        print('缺 quest_map_raw.json，先跑提取'); return
    ids = json.load(io.open(raw_path, encoding='utf-8'))
    todo = {en: q for en, q in ids.items() if en not in mp['quests']}
    print('任务名待查:', len(todo), '/', len(ids))
    if todo:
        got = fetch_quest_names(todo)
        mp['quests'].update(got)
        save_map(mp)
    print('任务名命中:', len(mp['quests']), '/', len(ids))
    miss = [en for en in ids if en not in mp['quests']]
    print('未命中(自定义任务, 留待客户端DB):', len(miss))
    for m in miss:
        print('  -', m)


if __name__ == '__main__':
    main()
