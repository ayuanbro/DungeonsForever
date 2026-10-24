# -*- coding: utf-8 -*-
"""专业页数据 · 中文对照表。

为什么不做「翻一遍写死在 Lua 里」：数据源改文案就白翻了。
这里把译文独立成一张表（`_fc/i18n/zh.json`），生成期按**英文原文**套用：

    命中 → 出中文；未命中 → 原样回落英文。

于是数据源新增文案**不阻塞**更新：插件照常能跑、只是那几句显示英文，
跑一次 `--todo` 就知道要补哪几条。

★ 物品名 / 法术名 / 图标 / 品质**不在本表范围内** —— 那些走客户端 ID 取中文。

用法：
    python fc_i18n.py --scan      统计待译量（按字段分组，看去重后到底要翻多少）
    python fc_i18n.py --todo      列出「还没译文」的条目（写进 _fc/i18n/todo.json）
"""
import argparse
import re
import glob
import json
import os
import sys
from collections import Counter, defaultdict
from fc_pipeline_common import configured_path

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = configured_path('DF_PIPELINE_DATA_DIR', os.path.join(HERE, '_fc', 'data'))
I18N = configured_path('DF_PIPELINE_I18N_DIR', os.path.join(HERE, '_fc', 'i18n'))
ZH = os.path.join(I18N, 'zh.json')


def load_data():
    index = json.load(open(os.path.join(DATA, 'index.json'), encoding='utf-8'))
    details = {}
    for f in glob.glob(os.path.join(DATA, 'prof_*.json')):
        details[os.path.basename(f)[len('prof_'):-len('.json')]] = \
            json.load(open(f, encoding='utf-8'))
    return index, details


def kind_tokens(s):
    """把产出物描述拆成「部位词 + 等级」，只翻部位词。

    实测该字段值高度模板化（"Cloth chest, level 12" / "8 Slot Bag" /
    "Attached to an item for good, level 30"），全量去重有 700+ 条，
    但拆掉 ", level N" 后缀后词表只有几十个 —— 翻词不翻句，一次到位且以后
    数据源加新等级也不会冒出未译文。返回 (词, 等级或 None)。
    """
    if not isinstance(s, str) or not s.strip():
        return None
    s = s.strip()
    m = re.match(r'^(.*), level (\d+)$', s)
    if m:
        return (m.group(1).strip(), int(m.group(2)))
    m = re.match(r'^level (\d+)$', s)
    if m:
        return ('', int(m.group(1)))
    return (s, None)


def collect(index, details):
    """收集「需要人翻」的文案。返回 {英文原文: [出处标签, ...]}。

    ★ 白名单制：只有列在这里的字段才进对照表。
      不进表的三类：
        · 有客户端 ID 的（物品名 / 法术名 / 图标 / 品质）；
        · 游戏内专名且数据源未给 ID 的（配方来源里的 NPC 名 / 区域名 / 节点名 / 套装名）——
          这些保留原文，翻错反而对不上游戏；营地 / 军需官段**例外**：vendor 行带 NPCID、
          营地带 AreaTable ID，且用户 2026-09-24 点名要汉化（NPC 中文名人工翻进 zh.json）；
        · 纯 ID 字符串（如附魔材料的 taught_by = NPC ID）。
      另：配方分类 rows.cat 与 groups.key 实测 1:1，故只翻 groups.label，
      rows.cat 保持英文键供查表。
    """
    out = defaultdict(list)

    def add(path, v):
        if isinstance(v, str) and v.strip():
            out[v.strip()].append(path)

    def addlist(path, vs):
        for v in vs or []:
            add(path, v)

    for p in index['professions']:
        s = p['slug']
        add(s + '.name', p['name'])
        for k in ('summary', 'lede', 'title', 'description', 'status', 'word',
                  'steps_title', 'steps_note'):
            add('%s.%s' % (s, k), p[k])
        for k in ('tips', 'verify', 'unknowns'):
            addlist('%s.%s' % (s, k), p[k])
        for i, st in enumerate(p['steps'] or []):
            add('%s.steps[%d].title' % (s, i), st[0])
            add('%s.steps[%d].text' % (s, i), st[1])
        for b in p['bonuses'] or []:
            add(s + '.bonus.name', b['name'])
            add(s + '.bonus.text', b['text'])
        for c in p['camp_objects'] or []:
            for k in ('name', 'effect', 'buff', 'role', 'replaces', 'exclusive'):
                add('%s.camp[%d].%s' % (s, c['id'], k), c[k])
        for k in ('specific_perks', 'shared_perks'):
            for pk in p[k] or []:
                add(s + '.perk.name', pk['name'])
                add(s + '.perk.text', pk['text'])
                add(s + '.perk.effect', pk['effect'])
                addlist(s + '.perk.rank', pk['rank_texts'])
                addlist(s + '.perk.uncertain', pk['uncertain'])
        for m in p['milestones'] or []:
            add(s + '.milestone.name', m['name'])
        if p['certification']:
            add(s + '.cert.name', p['certification']['name'])
            add(s + '.cert.title', p['certification']['title'])
        for r in p['racials'] or []:
            add(s + '.racial.note', r['note'])
        for rk in p.get('ranks') or []:          # 钓鱼技能等级表
            add(s + '.rank.name', rk[0])
            add(s + '.rank.note', rk[2] if len(rk) > 2 else '')
        for grp, entries in (p['fishing'] or {}).items():
            for e in entries:
                add('%s.fishing.%s.text' % (s, grp), e['text'])
                add('%s.fishing.%s.sub' % (s, grp), e['sub'])

    for s, d in details.items():
        if not d:
            continue
        for g in d['groups'] or []:
            add(s + '.group.label', g['label'])
        for r in d['rows'] or []:
            tk = kind_tokens(r['kind'])
            if tk and tk[0]:
                add(s + '.rows.kind', tk[0])
            add(s + '.rows.armor', r['armor'])
            add(s + '.rows.set', r['set'])
        for e in d['enchants'] or []:
            for b in e['bis'] or []:              # 适用职业专精的显示名
                add(s + '.ench.bis', b[2] if len(b) > 2 else '')
            add(s + '.ench.group', e['group'])
            add(s + '.ench.short', e['short'])
            add(s + '.ench.text', e['text'])
        # 营地 / 军需官（用户 2026-09-24：营地与军需官那一段要汉化）——
        # 军需官行有 NPCID、营地有 AreaTable ID，都不再是「没 ID 的游戏内专名」，
        # 从白名单豁免里拿出来照常收录；NPC 中文名数据源没有，人工翻（zh.json）。
        c2 = d.get('camps') or {}
        for side in ('a', 'h'):
            cp = c2.get(side)
            if cp:
                for k in ('faction', 'zone', 'place'):
                    add('%s.camps.%s.%s' % (s, side, k), cp.get(k))
        v2 = d.get('vendor') or {}
        for side in ('a', 'h'):
            vd = v2.get(side)
            if vd:
                add('%s.vendor.%s.npc' % (s, side), vd.get('npc'))
                add('%s.vendor.%s.role' % (s, side), vd.get('role'))
        # 配方来源里的商人（2026-10-08）：**已定位**的进白名单 —— 定位表
        # （_fc/data/vendor_loc.json，fc_vendors.py 产物）里有条目 = 拿到了 NPCID，
        # 就不再是「没 ID 的游戏内专名」，与营地 / 军需官段的豁免口径一致。
        # 名字汉化数据源没有，人工 / wowhead zh 页翻（zh.json）。
        vl_path = os.path.join(DATA, 'vendor_loc.json')
        vloc = json.load(open(vl_path, encoding='utf-8')) if os.path.exists(vl_path) else {}
        for coll in ('rows', 'enchants', 'crafted'):
            for r in d.get(coll) or []:
                src = r.get('source')
                if not isinstance(src, dict):
                    continue
                for v in src.get('vendors') or []:
                    if isinstance(v, dict) and v.get('name') in vloc:
                        add(s + '.src.vendor.npc', v['name'])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--todo', action='store_true')
    ap.add_argument('--export', metavar='GROUP', nargs='?', const='',
                    help='导出待译条目为「原文|||」行（可按字段组过滤）')
    ap.add_argument('--add', action='store_true',
                    help='从 stdin 读「原文|||译文」行合并进 zh.json')
    ap.add_argument('--batch', metavar='TAG',
                    help='配合 --add：按 batch 文件行号提交，stdin 格式为「行号|||译文」')
    ap.add_argument('--split', action='store_true',
                    help='把待译条目按字段组分批导出到 _fc/i18n/batch_*.txt（带行号）')
    ap.add_argument('--audit', action='store_true',
                    help='对账：白名单里没译文的 / 对照表里已失效（僵尸）的')
    args = ap.parse_args()

    index, details = load_data()
    strings = collect(index, details)
    os.makedirs(I18N, exist_ok=True)
    zh = json.load(open(ZH, encoding='utf-8')) if os.path.exists(ZH) else {}
    missing = {k: v for k, v in strings.items() if k not in zh}
    done = len(strings) - len(missing)

    def group_of(paths):
        g = paths[0].split('.', 1)[1]
        return g.split('[')[0].split('.')[0]

    if args.audit:
        zombie = sorted(k for k in zh if k not in strings)
        print('=== 对照表对账 ===')
        print('  白名单应译 %d 条 · 对照表 %d 条 · 未译 %d 条 · 僵尸 %d 条'
              % (len(strings), len(zh), len(missing), len(zombie)))
        if missing:
            print()
            print('  ✗ 未译（生成期会回落英文）：')
            for k in sorted(missing):
                print('      %s' % k[:110])
        if zombie:
            print()
            print('  · 僵尸（白名单已不再取用，删掉可保持表干净）：')
            for k in zombie:
                print('      %s' % k[:110])
        return 0

    if args.split:
        BATCH = {
            'A': {'name', 'summary', 'title', 'description', 'status', 'steps_title',
                  'steps_note', 'tips', 'verify', 'unknowns', 'racial', 'milestone',
                  'cert', 'bonus', 'fishing', 'word', 'rank'},
            'B': {'camp', 'perk', 'steps'},
            'C': {'ench', 'rows', 'group', 'bis'},
        }
        for tag, gs in BATCH.items():
            rows = [k for k, p in missing.items() if group_of(p) in gs]
            rows.sort()
            path = os.path.join(I18N, 'batch_%s.txt' % tag)
            with open(path, 'w', encoding='utf-8') as f:
                for i, r in enumerate(rows, 1):
                    f.write('%3d  %s\n' % (i, r))
            print('%s: %d 条 → %s' % (tag, len(rows), path))
        return 0

    if args.add:
        added = 0
        bad = 0
        if args.batch:
            path = os.path.join(I18N, 'batch_%s.txt' % args.batch)
            src = [l.rstrip('\n') for l in open(path, encoding='utf-8')]
            # 行号 → 原文（按导出的 %3d 前缀解析）
            keyed = {}
            for l in src:
                m = re.match(r'^\s*(\d+)\s+(.*)$', l)
                if m:
                    keyed[int(m.group(1))] = m.group(2).strip()
            pairs = []
            for line in sys.stdin:
                line = line.rstrip('\n').rstrip('\r')
                if not line.strip() or '|||' not in line:
                    continue
                n, zhv = line.split('|||', 1)
                n = n.strip().split()[-1] if n.strip() else ''
                if not n.isdigit() or zhv.strip() == '':
                    bad += 1
                    print('  ⚠️ 行号无法解析：%r' % line[:60])
                    continue
                if int(n) not in keyed:
                    bad += 1
                    print('  ⚠️ 行号越界：%s' % n)
                    continue
                pairs.append((keyed[int(n)], zhv.strip()))
        else:
            pairs = []
            for line in sys.stdin:
                line = line.rstrip('\n').rstrip('\r')
                if not line.strip() or '|||' not in line:
                    bad += 1
                    continue
                en, zhv = line.split('|||', 1)
                pairs.append((en.strip(), zhv.strip()))
        for en, zhv in pairs:
            if not zhv:
                bad += 1
                continue
            zh[en] = zhv
            added += 1
        json.dump(zh, open(ZH, 'w', encoding='utf-8'), ensure_ascii=False,
                  indent=1, sort_keys=True)
        print('已写入 %d 条（对照表合计 %d 条；忽略 %d 行）' % (added, len(zh), bad))
        return 0

    if args.export is not None:
        for k, paths in sorted(missing.items(), key=lambda kv: kv[1][0]):
            if args.export and group_of(paths) != args.export:
                continue
            print('%s|||' % k)
        return 0

    if args.scan:
        groups = Counter()
        gwords = Counter()
        for k, paths in strings.items():
            g = group_of(paths)
            groups[g] += 1
            gwords[g] += len(k.split())
        print('=== 待译文案（去重后）===')
        print('  %-14s %6s %8s %8s' % ('字段组', '条数', '词数', '已译'))
        for g, _ in gwords.most_common():
            print('  %-14s %6d %8d %8d' % (
                g, groups[g], gwords[g],
                groups[g] - sum(1 for k, p in missing.items() if group_of(p) == g)))
        print('  %-14s %6d %8d %8d' % ('合计', len(strings), sum(gwords.values()), done))
        print()

    if args.todo:
        out = os.path.join(I18N, 'todo.json')
        json.dump({k: sorted(set(v))[:3] for k, v in sorted(missing.items())},
                  open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('待译 %d 条 → %s' % (len(missing), out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
