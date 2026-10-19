# -*- coding: utf-8 -*-
"""输出「暴风城 NPC 坐标核对表」：Markdown + CSV。"""
import re, io, os, json, csv

TITAN = r"D:/workspace/DungeonsForever"
OUTDIR = os.path.join(TITAN, "_temp")
rd = lambda p: io.open(p, encoding='utf-8').read()

loc = rd(TITAN + "/Core/Data/Data_NPCLoc.lua")
qs  = rd(TITAN + "/Core/Data/Data_DungeonQuests.lua")

# ---- NPCLoc ----
nploc = {}
for m in re.finditer(r'\[\s*(\d+)\s*\]\s*=\s*\{\s*(\d+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*"([^"]*)"\s*\}', loc):
    nploc[int(m.group(1))] = (int(m.group(2)), float(m.group(3)), float(m.group(4)), m.group(5))
qpre = {}
mb = re.search(r'ns\.QuestPreNpcID\s*=\s*\{(.*?)\n\}', loc, re.S)
for m in re.finditer(r'\[\s*(\d+)\s*\]\s*=\s*(\d+)\s*,', mb.group(1)):
    qpre[int(m.group(1))] = int(m.group(2))

# ---- PreExtra: questID -> {pre=[...], npc=name} ----
pe = {}
pem = re.search(r'ns\.DungeonQuestPreExtra\s*=\s*\{(.*?)\n\}\n', qs, re.S)
for line in pem.group(1).split('\n'):
    m = re.match(r'\s*\[(\d+)\]\s*=\s*\{(.*)\},\s*$', line)
    if not m: continue
    qid = int(m.group(1)); body = m.group(2)
    nm = re.search(r'npc\s*=\s*"([^"]*)"', body)
    pre = re.match(r'\s*([\d,\s]*?)(?:,\s*npc|$)', body)
    preids = [int(x) for x in re.findall(r'\d+', pre.group(1))] if pre else []
    pe[qid] = dict(npc=(nm.group(1) if nm else None), pre=preids)

# ---- quest rows ----
def split_top(line):
    fields = []; depth = 0; cur = ''; instr = False; esc = False; started = False
    for ch in line:
        if not started:
            if ch == '{': started = True; depth = 1; cur = ''
            continue
        if instr:
            cur += ch
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == '"': instr = False
            continue
        if ch == '"': instr = True; cur += ch; continue
        if ch == '{': depth += 1; cur += ch; continue
        if ch == '}':
            depth -= 1
            if depth == 0:
                fields.append(cur.strip()); break
            cur += ch; continue
        if ch == ',' and depth == 1:
            fields.append(cur.strip()); cur = ''; continue
        cur += ch
    return fields

def unq(s):
    if not s or s == 'nil': return None
    return s[1:-1] if s.startswith('"') and s.endswith('"') else s

rows = []
cur = None
for line in qs.split('\n'):
    m = re.search(r'^\s*\["([^"]+)"\]\s*=\s*\{', line)
    if m: cur = m.group(1); continue
    m = re.match(r'\s*\{\s*(\d+)\s*,', line)
    if not m: continue
    f = split_top(line)
    if len(f) < 18: continue
    try:
        npcid = int(unq(f[15]))
    except (TypeError, ValueError):
        npcid = None
    rows.append(dict(dun=cur, qid=int(f[0]), site=unq(f[5]), npcid=npcid, npcname=unq(f[16])))

DUN_CN = {}
for m in re.finditer(r'\["([a-z_]+)"\]\s*=\s*\{[^\n]*?--\s*([^\n·]+)·', qs):
    DUN_CN[m.group(1)] = m.group(2).strip()

# ---- 暴风城 NPC 集合 ----
SW_MAP = 1453
sw_ids = sorted(k for k, v in nploc.items() if v[3] == '暴风城')

NAME = {332:'马迪亚斯·肖尔',656:'维尔德·蓟草',928:'格雷森·沙东布瑞克公爵',1284:'大主教本尼迪塔斯',
        1416:'格瑞曼德·艾尔默',1646:'巴隆斯·阿历克斯顿',1719:'典狱官塞尔沃特',1721:'尼科瓦·拉斯克',
        1748:'伯瓦尔·弗塔根公爵',2198:'公告员古德曼',2285:'雷明顿·瑞治维尔伯爵',4984:'阿古斯·夜语',
        5384:'布罗哈恩·铁桶',5413:'弗伦·长须',6171:'达索瑞恩·拉尔',6579:'沉默的舒尼',
        7917:'萨尔努修士',12336:'克罗雷修士',14450:'孤儿监护员奈丁加尔'}

# 全表按 NPC 名扫「暴风城 ... x,y」引用串
all_quest_lines = [l for l in qs.split('\n') if re.match(r'\s*\{\s*\d+\s*,', l)]
NAME_HINTS = {}
for nm in set(NAME.values()):
    hits = []
    for l in all_quest_lines:
        if nm in l:
            for m in re.finditer(r'暴风城[^\s，。、]{0,10}\d{1,3}\s*,\s*\d{1,3}）?', l):
                if m.group(0) not in hits:
                    hits.append(m.group(0))
    NAME_HINTS[nm] = hits

out = []
for nid in sw_ids:
    mp, x, y, zone = nploc[nid]
    name = NAME.get(nid) or '(未定名)'
    # 起始任务（quest 表里 field16 == nid）
    starts = [r for r in rows if r['npcid'] == nid]
    preq   = sorted(q for q, n in qpre.items() if n == nid)
    # 区域串：起始任务里的 起始地点
    sitestrs = []
    for r in starts:
        if r['site'] and r['site'] not in sitestrs:
            sitestrs.append(r['site'])
    sub = ''
    for s in sitestrs:
        if s.startswith('暴风城'):
            p = s.split(' ', 1)
            if len(p) > 1:
                sub = re.sub(r'^-\s*', '', p[1].rsplit(' ', 1)[0])
    out.append(dict(id=nid, name=name, x=x, y=y, map=mp, zone=zone,
                    sub=sub, sites=' / '.join(sitestrs) or '',
                    hints=NAME_HINTS.get(name, []),
                    starts=starts, preq=[(q, pe.get(q, {}).get('npc')) for q in preq]))

lines = []
lines.append("# 暴风城 NPC 坐标核对表")
lines.append("")
lines.append("> 来源：`Core/Data/Data_NPCLoc.lua` 里 `地图 = 暴风城 (uiMapID 1453)` 的全部条目，共 **%d** 个。" % len(out))
lines.append("> 名称取自 wowhead forever/cn NPC 页（本地缓存 `TalentsForever/_temp/_wh_npccache/`）逐页核对。")
lines.append("> 坐标口径：`x% = 西→东`，`y% = 北→南`（addon 直接 /100 交给 C_Map 用户航点）。")
lines.append("> 「区域」列来自任务表里的「起始地点」文字（`暴风城 - 矮人区 70,41` 这类），括号里的数字是**站点口径的老坐标**，可与 NPCLoc 值对照。")
lines.append("")
lines.append("| # | NPC ID | 名称 | 当前坐标 (x, y) | 区域 | 站点口径引用（老坐标） | 关联任务 |")
lines.append("|---|---|---|---|---|---|---|")
for i, o in enumerate(out, 1):
    ref = []
    if o['sites']: ref.append('起始地点：' + o['sites'])
    for h in o['hints']:
        ref.append(h)
    ref = ' / '.join(dict.fromkeys(ref)) or '—'
    qs_ = []
    for r in o['starts']:
        qs_.append("%d(起始·%s)" % (r['qid'], DUN_CN.get(r['dun'], r['dun'])))
    for q, nm in o['preq']:
        qs_.append("%d(前置链)" % q)
    lines.append("| %d | %d | %s | %.1f, %.1f | %s | %s | %s |"
                 % (i, o['id'], o['name'], o['x'], o['y'], o['sub'] or '—', ref, '、'.join(qs_) or '—'))
lines.append("")
lines.append("## 核对誊写用（把游戏内实测的 x, y 填在后面）")
lines.append("")
lines.append("```")
for i, o in enumerate(out, 1):
    lines.append("%-2d  %-7d  %-12s  旧: %5.1f, %5.1f   →  新: ___, ___   %s"
                 % (i, o['id'], o['name'], o['x'], o['y'], o['sub']))
lines.append("```")
lines.append("")
lines.append("## 明细（逐条）")
lines.append("")
for i, o in enumerate(out, 1):
    lines.append("### %d. %s （NPC %d）" % (i, o['name'], o['id']))
    lines.append("- 当前坐标：**%s, %s**（地图 %d = %s）" % (o['x'], o['y'], o['map'], o['zone']))
    lines.append("- 区域：%s" % (o['sub'] or '—'))
    if o['sites']:
        lines.append("- 任务表站点口径：%s" % o['sites'])
    if o['hints']:
        lines.append("- 任务文本里出现的老坐标：%s" % '；'.join(dict.fromkeys(o['hints'])))
    for r in o['starts']:
        lines.append("  - 起始 NPC：任务 %d（%s）" % (r['qid'], DUN_CN.get(r['dun'], r['dun'])))
    for q, nm in o['preq']:
        lines.append("  - 前置链节点：任务 %d（该任务起始 NPC 记作「%s」）" % (q, nm or '?'))
    lines.append("- 链接：https://www.wowhead.com/forever/cn/npc=%d" % o['id'])
    lines.append("")

md = os.path.join(OUTDIR, "_stormwind_npc_coords.md")
io.open(md, 'w', encoding='utf-8').write('\n'.join(lines))
print("wrote", md, len(out), "npcs")

csvp = os.path.join(OUTDIR, "_stormwind_npc_coords.csv")
with io.open(csvp, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['npcID', '名称', '旧x', '旧y', '新x', '新y', 'uiMapID', '地图', '区域', '站点口径老坐标', '关联任务'])
    for o in out:
        w.writerow([o['id'], o['name'], o['x'], o['y'], '', '', o['map'], o['zone'], o['sub'],
                    o['sites'], ' | '.join(['%d起始' % r['qid'] for r in o['starts']] + ['%d前置' % q for q, _ in o['preq']])])
print("wrote", csvp)
for o in out:
    print("%-7d %-12s %5.1f,%5.1f  %s  sites=%s" % (o['id'], o['name'], o['x'], o['y'], o['sub'], o['sites']))
