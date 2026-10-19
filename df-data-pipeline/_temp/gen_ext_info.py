# -*- coding: utf-8 -*-
"""生成 ns.DungeonQuestExtInfo（副本外前置任务详情段，源 = 窝窝头 quests.json）。

- 输入：_temp/_ext_pre_ids.json（ext 前置任务清单）+ _temp/_ww_quests.json（全量）；
- 写入 Core/Data/Data_DungeonQuests.lua 顶层段（幂等替换）；
- 字段（键名式，与 DungeonQuestPreExtra 同风格）：
  [id] = { lv=可接, lvStd=标准, nm=兜底全名, npc=接取, npcid=接取NPCID, side="A"/"H", zone=区域,
           goals={ {"i",itemId,n} | {"c",npc名,n} | {"o",描述} }, text=攻略讲解 }
- text 取 _temp/_ext_notes.json 的中文讲解（缺失则整段不写，不回退剧情 lore）；
  npcid 取 _temp/questie/questie_forever.json 的 quest_npc 映射。
- 任务名优先运行时 GetTitleForQuestID，客户端缺名时用 nm 兜底（2026-10-17 用户拍板）。
用法：python gen_ext_info.py
"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
SRC = os.path.join(DF, 'Core', 'Data', 'Data_DungeonQuests.lua')
NL = chr(10)
BS = chr(92)
ids = json.load(io.open(os.path.join(HERE, '_ext_pre_ids.json'), encoding='utf-8'))['ids']
qs = {q['id']: q for q in json.load(io.open(os.path.join(HERE, '_ww_quests.json'), encoding='utf-8'))['quests']}
NOTES = json.load(io.open(os.path.join(HERE, '_ext_notes.json'), encoding='utf-8'))
QFOREVER = json.load(io.open(os.path.join(HERE, 'questie', 'questie_forever.json'), encoding='utf-8'))
QNPC = QFOREVER.get('quest_npc') or {}

SIDE = {'部落': 'H', '联盟': 'A'}
CLASS_CATS = {"战士", "圣骑士", "猎人", "潜行者", "盗贼", "牧师", "萨满祭司", "法师", "术士", "德鲁伊",
              "死亡骑士", "武僧", "恶魔猎手", "唤魔师"}
CLS_ALIAS = {"潜行者": "盗贼"}


def esc(s):
    s = s.replace(BS, BS * 2)
    s = s.replace('"', BS + '"')
    s = s.replace('$B$B', NL).replace('$B', NL)
    s = s.replace(NL, BS + 'n')
    return s


def goal_entry(g):
    t = g.get('type')
    if t == 'item' and g.get('id'):
        return '{ "i", %d, %d }' % (g['id'], g.get('n') or 1)
    if t == 'creature' and g.get('name') and '[DNT]' not in g['name']:
        return '{ "c", "%s", %d }' % (esc(g['name']), g.get('n') or 1)
    if t == 'object' and g.get('desc'):
        return '{ "o", "%s" }' % esc(g['desc'])
    return None


rows = []
src = io.open(SRC, encoding='utf-8').read()
PRE = {}
_a = src.find('ns.DungeonQuestPreExtra = {' + NL)
if _a >= 0:
    _b = src.find(NL + '}' + NL, _a)
    if _b > _a:
        for _m in re.finditer(r'^    \[(\d+)\] = \{(.*)\},?$', src[_a:_b], re.M):
            _nm = re.search(r'npc = "([^"]*)"', _m.group(2))
            _lv = re.search(r'lv = (\d+)', _m.group(2))
            PRE[int(_m.group(1))] = (_nm.group(1) if _nm else None,
                                     int(_lv.group(1)) if _lv else None)
for qid in ids:
    q = qs.get(qid)
    if not q:
        continue
    tmp = q.get('tmp') or {}
    pen, pelv = PRE.get(qid, (None, None))
    f = []
    lv = q.get('min_level') or tmp.get('min_level') or pelv
    if lv:
        f.append('lv = %d' % lv)
    lvs = q.get('level') or tmp.get('level')
    if lvs:
        f.append('lvStd = %d' % lvs)
    nm = q.get('title') or tmp.get('name')
    if nm:
        f.append('nm = "%s"' % esc(nm))
    giver = tmp.get('giver')
    si = q.get('start_items') or []
    if not giver and si and si[0].get('name'):
        giver = si[0]['name']
    if not giver and pen:
        giver = pen
    if giver:
        f.append('npc = "%s"' % esc(giver))
    nid = QNPC.get(str(qid))
    if nid:
        f.append('npcid = %d' % nid)
    if SIDE.get(tmp.get('side')):
        f.append('side = "%s"' % SIDE[tmp['side']])
    zn = (q.get('zone') or {}).get('name') or (tmp.get('zone') or {}).get('name')
    if zn:
        f.append('zone = "%s"' % esc(zn))
    cat = (q.get('category') or {}).get('name')
    if cat in CLASS_CATS:
        f.append('cls = "%s"' % esc(CLS_ALIAS.get(cat, cat)))
    prev = [p for p in (tmp.get('prev') or []) if isinstance(p, int)]
    if prev:
        f.append('pre = { %s }' % ', '.join(str(p) for p in prev))
    if si:
        f.append('si = true')
    goals = [goal_entry(g) for g in (q.get('goals') or [])]
    goals = [g for g in goals if g]
    if goals:
        f.append('goals = { %s }' % ', '.join(goals))
    rw = q.get('reward') or {}
    rews = []
    for key in ('choices', 'items'):
        for it in (rw.get(key) or []):
            iid = it[0] if isinstance(it, list) else it
            if iid and iid not in rews:
                rews.append(iid)
    if rews:
        f.append('rew = { %s }' % ', '.join(str(x) for x in rews))
    g = []
    if rw.get('xp'):
        g.append('xp = %d' % rw['xp'])
    if rw.get('money'):
        g.append('money = %d' % rw['money'])
    reps = rw.get('rep') or []
    if reps:
        g.append('rep = { %s }' % ', '.join(
            '{ %d, %d, "%s" }' % (r['id'], r['n'], esc(r['name'])) for r in reps if r.get('name')))
    if g:
        f.append('gains = { %s }' % ', '.join(g))
    texts = q.get('cache_texts') or []
    texts = [t.strip() for t in texts if t and t.strip()]
    if texts:
        f.append('obj = "%s"' % esc(texts[0]))
    note = NOTES.get(str(qid))
    if note:
        f.append('text = "%s"' % esc(note))
    rows.append('    [%d] = { %s },' % (qid, ', '.join(f)))

seg = 'ns.DungeonQuestExtInfo = {' + NL + (NL.join(rows) + NL if rows else '') + '}' + NL
pat = re.compile(r'ns\.DungeonQuestExtInfo = \{' + re.escape(NL) + r'.*?' + re.escape(NL) + r'\}' + re.escape(NL), re.S)
if pat.search(src):
    src = pat.sub(lambda m: seg, src, count=1)
    act = 'replaced'
else:
    if not src.endswith(NL):
        src += NL
    src += seg
    act = 'appended'
io.open(SRC, 'w', encoding='utf-8', newline='').write(src)
print(act, 'rows=%d' % len(rows))
