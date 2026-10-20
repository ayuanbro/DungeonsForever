# -*- coding: utf-8 -*-
"""专业页数据 · 第 2 步：RSC 载荷 → 归一化 JSON。

为什么是「归一化」而不是原样存：
  · 站点字段名是给 React 组件用的，带大量渲染细节（isNew / was / wasCount / bis 空数组…）；
    原样存进 Lua 会让数据文件一半是空值。
  · 归一化只取「插件会显示的东西」，并统一成稳定的数组/字段形态 ——
    站点加新字段时插件不受影响（白名单），站点改字段名时只改本文件一处。
  · ★ 物品名一律不落盘：只保留 ID，中文名运行时由客户端给（用户 2026-09-23 定）。

产出的 JSON 是 fc_gen.py 的唯一输入；中间产物不参与打包。

用法：
    python fc_parse.py             # 生成 _fc/data/*.json
    python fc_parse.py --report    # 只打字段覆盖报告，不落盘
    python fc_parse.py --diff      # 与上次 data/ 比对，出变更报告
"""
import argparse
import glob
import json
import os
import re
import sys
from fc_pipeline_common import configured_path

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = configured_path('DF_PIPELINE_CACHE_DIR', os.path.join(HERE, '_fc', 'cache'))
DATA = configured_path('DF_PIPELINE_DATA_DIR', os.path.join(HERE, '_fc', 'data'))
REPORTS = configured_path('DF_PIPELINE_REPORT_DIR', os.path.join(HERE, '_fc', 'reports'))

# 站点页面 → 数据键。采集类没有配方表，附魔走 enchants/crafted。
DROP = object()          # 白名单哨兵：显式声明「这个源字段有意丢弃」

# 钓鱼区域技能门槛的站点编码偏移。站点存的是「门槛 − 70」（实测六档：
# −70 / −20 / 55 / 130 / 205 / 330，等差还原后 = 0 / 50 / 125 / 200 / 275 / 400，
# 正是经典旧世的六个钓鱼区域档位）→ 生成期 +70 还原成玩家看得懂的数值。
# 原始编码一并存进 `raw`，将来站点换算法时好回溯。
FISH_SKILL_OFFSET = 70


# ── RSC 解码 ────────────────────────────────────────────────────────────────
def rsc_payload(html_path):
    h = open(html_path, encoding='utf-8', errors='replace').read()
    parts = []
    for c in re.findall(r'self\.__next_f\.push\(\[1,(".*?")\]\)', h, flags=re.S):
        try:
            parts.append(json.loads(c))
        except Exception:
            parts.append(c)
    return ''.join(parts)


_RSC_MEMO = {}


def rsc_rows(html_path):
    # 进程内记忆化：parse_index 与 parse_detail 会各解析同一页一次，
    # RSC 解析是全流程最慢的一环，缓存住让每页只算一遍。
    hit = _RSC_MEMO.get(html_path)
    if hit is not None:
        return hit
    rows = {}
    for m in re.finditer(r'(?m)^([0-9a-f]{1,3}):(.*)$', rsc_payload(html_path)):
        try:
            rows[m.group(1)] = json.loads(m.group(2))
        except Exception:
            pass
    _RSC_MEMO[html_path] = rows
    return rows


def deep_find_all(node, pred, acc=None):
    """收集**所有**满足 pred 的节点（含路径与自身大小）。"""
    if acc is None:
        acc = []
    if isinstance(node, dict):
        if pred(node):
            acc.append(node)
        for v in node.values():
            deep_find_all(v, pred, acc)
    elif isinstance(node, list):
        for v in node:
            deep_find_all(v, pred, acc)
    return acc


def deep_find(node, pred):
    """找**最大**的匹配节点。

    ★ 必须取最大：同一页会有多个候选（导航用的专业摘要、内嵌的预取数据都带
      profession 字段），取第一个会拿到裁剪版 —— 实测 v1 取到的是「不含
      herbalism 采集表」的那一份，采药整块数据静默丢失。取最大者即主数据对象。
    """
    hits = deep_find_all(node, pred)
    if not hits:
        return None
    return max(hits, key=lambda o: len(json.dumps(o, ensure_ascii=False)))


def site_updated(html_path):
    """页面上的 'Updated YYYY-MM-DD' —— 变更报告里要能看到站点自己标的日期。"""
    h = open(html_path, encoding='utf-8', errors='replace').read()
    m = re.search(r'Updated\s*\\?u?(\d{4}-\d{2}-\d{2})', h)
    if m:
        return m.group(1)
    m = re.search(r'"updated\\?":\\?"(\d{4}-\d{2}-\d{2})', h)
    return m.group(1) if m else None


# ── 归一化：小工具 ──────────────────────────────────────────────────────────
def s(v, default=''):
    """字符串归一：站点用 null 表示「没有」，统一成空串（Lua 侧少一类分支）。"""
    return v if isinstance(v, str) else (default if v is None else str(v))


def slist(v):
    return [s(x) for x in v] if isinstance(v, list) else []


def flat(v):
    """把「分段文本」拼成一句。

    ★ 站点的部分文本字段是**分段数组**，用于按档位插值显示，例如
        ['Increases ... by ', '33 / 67 / 100', '%.']
      早先直接 str() 过一遍，导致产物里出现 Python 的 list 字面量（带方括号与引号）——
      既不是给人看的文本，也不可能翻译。这里按段拼接还原成一句。
    """
    if isinstance(v, list):
        return ''.join(flat(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, str):
        return v
    return '' if v is None else str(v)


def num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def ints(v):
    return [x for x in v if isinstance(x, int) and not isinstance(x, bool)] if isinstance(v, list) else []


def rank_texts(p):
    """perk 的逐级文本：站点给的是 {"1":"...","2":"..."}，转成按 rank 顺序的数组。"""
    rt = p.get('rank_texts')
    if not isinstance(rt, dict) or not rt:
        return []
    out = []
    for k in sorted(rt, key=lambda x: int(x) if str(x).isdigit() else 0):
        out.append(flat(rt[k]))
    return out


def norm_perk(p):
    """Legacy 特权。站点字段极多（calculator_eligible / comparison_status …），
    插件只用得上这几项：id / 名 / 图标 / 上限 / 逐级文本 / 无级文本 / 证据强度。"""
    if not isinstance(p, dict):
        return None
    return {
        'id': s(p.get('id')),
        'name': s(p.get('name')),
        'icon': s(p.get('icon')),
        'tree': s(p.get('tree_name')),
        'max_rank': num(p.get('max_rank')) or 0,
        'rank_texts': rank_texts(p),
        'text': flat(p.get('unranked_effect')),
        'effect': flat(p.get('effect')),
        'status': s(p.get('evidence_status')),
        'uncertain': slist(p.get('uncertainties')),
    }


def norm_reagents(v):
    """材料表：{id, count} 或 {id, name, count} → 统一 [id, count]（名字走客户端）。"""
    out = []
    for r in v or []:
        if not isinstance(r, dict):
            continue
        i = num(r.get('id'))
        if i is None:
            continue
        out.append([int(i), num(r.get('count')) or 1])
    return out


def norm_camp_object(o):
    if not isinstance(o, dict):
        return None
    return {
        'id': num(o.get('id')),
        'name': s(o.get('name')),
        'icon': s(o.get('icon')),
        'skill': num(o.get('skill')) or 0,
        'effect': s(o.get('effect')),
        'buff': s(o.get('buff')),
        'role': s(o.get('role')),
        'replaces': s(o.get('replaces')),
        'exclusive': s(o.get('exclusive')),
        'capacity': s(o.get('capacity')),
        'reagents': norm_reagents(o.get('reagents')),
        'blueprint': norm_formula(o.get('blueprint')),
    }


def norm_formula(f):
    """图纸/配方物品：源字段 {id, q, name} 或 {id, name}。名字丢弃（走客户端）。"""
    if not isinstance(f, dict):
        return None
    i = num(f.get('id'))
    if i is None:
        return None
    return [int(i), num(f.get('q')) or 0]


def norm_source(src):
    """配方来源。站点给了 n(名字) / q(品质) / skill / drops[] / vendors[] / cost / read。
    `n` 是「图纸名」——名字走客户端；`drops` 的 npc 名保留（NPC 名客户端查不到时兜底）。"""
    if not isinstance(src, dict):
        return None
    drops = []
    for d in src.get('drops') or []:
        if not isinstance(d, dict):
            continue
        lv = d.get('level')
        drops.append({
            'npc': s(d.get('npc')),
            'zone': s(d.get('zone')),
            'chance': num(d.get('chance')),
            'lv': [int(x) for x in lv if isinstance(x, int)] if isinstance(lv, list) else [],
        })
    vendors = []
    for v in src.get('vendors') or []:
        if not isinstance(v, dict):
            vendors.append({'name': s(v), 'cost': None}) if isinstance(v, str) else None
            continue
        vendors.append({
            'name': s(v.get('npc') or v.get('name')),
            'zone': s(v.get('zone')),
            'cost': s(v.get('cost')),
            'skill': num(v.get('skill')),
        })
    out = {
        'skill': num(src.get('skill')),
        'read': s(src.get('read')),
        'drops': drops,
        'vendors': vendors,
    }
    if not any((out['skill'], out['drops'], out['vendors'], out['read'])):
        return None
    return out


def norm_row(r, spell_fix=None):
    """配方行。站点字段：spell/id/count/cat/kind/effect/learn/yellow/green/grey/
    reagents/formula/source/isNew/was/wasCount/set/armorType/bis。"""
    if not isinstance(r, dict):
        return None
    spell = num(r.get('spell')) or (spell_fix if spell_fix else None)
    rid = num(r.get('id'))
    if spell is None and rid is None:
        return None
    return {
        'spell': int(spell) if spell is not None else None,
        'id': int(rid) if rid is not None else None,
        'count': num(r.get('count')) or 1,
        'cat': s(r.get('cat')),
        'kind': s(r.get('kind')),
        'effect': s(r.get('effect')),
        'learn': num(r.get('learn')),
        'yellow': num(r.get('yellow')),
        'green': num(r.get('green')),
        'grey': num(r.get('grey')),
        'reagents': norm_reagents(r.get('reagents')),
        'formula': norm_formula(r.get('formula')),
        'source': norm_source(r.get('source')),
        'is_new': bool(r.get('isNew')),
        'was': norm_reagents(r.get('was')),   # 调整前的旧材料表（有改动的配方才有）
        'set': s(r.get('set')),          # 套装名（制皮/裁缝的套装件）
        'armor': s(r.get('armorType')),
    }


def norm_enchant(e):
    if not isinstance(e, dict):
        return None
    return {
        'name': s(e.get('name')),
        'short': s(e.get('short')),
        'group': s(e.get('group')),
        'text': s(e.get('text')),
        'learn': num(e.get('learn')),
        'yellow': num(e.get('yellow')),
        'green': num(e.get('green')),
        'grey': num(e.get('grey')),
        'reagents': norm_reagents(e.get('reagents')),
        'source': norm_source(e.get('source')) or norm_source(e.get('formula')),
        'is_new': bool(e.get('isNew')),
        'sod': bool(e.get('fromSod')),
        # 适用职业/专精：{cls, spec, 显示名}。href 是数据源自身站内链接，丢弃。
        'bis': [[s(b.get('cls')), s(b.get('spec')), s(b.get('name'))]
                for b in (e.get('bis') or []) if isinstance(b, dict)],
    }


def norm_crafted(e):
    """附魔的「可制造」条目（把材料做成附魔卷轴那一类）。"""
    if not isinstance(e, dict):
        return None
    return {
        'spell': num(e.get('spell')),
        'id': num(e.get('id')),
        'count': num(e.get('count')) or 1,
        'learn': num(e.get('learn')),
        'yellow': num(e.get('yellow')),
        'green': num(e.get('green')),
        'grey': num(e.get('grey')),
        'reagents': norm_reagents(e.get('reagents')),
        'taught_by': s(e.get('taught_by')),
        'is_new': bool(e.get('isNew')),
    }


# ── 归一化：专业元信息 ──────────────────────────────────────────────────────
def norm_profession(p):
    if not isinstance(p, dict):
        return None
    return {
        'slug': s(p.get('slug')),
        'name': s(p.get('name')),
        'icon': s(p.get('icon')),
        'kind': s(p.get('kind')),          # primary / secondary / system
        'section': s(p.get('section')),
        'guide': s(p.get('guide')),
        'summary': s(p.get('summary')),
        'title': s(p.get('title')),
        'description': s(p.get('description')),
        'lede': s(p.get('lede')),
        'tips': slist(p.get('tips')),
        'verify': slist(p.get('verify')),
        'unknowns': slist(p.get('unknowns')),
        'status': s(p.get('status')),
        'steps_title': s(p.get('steps_title')),
        'steps_note': s(p.get('steps_note')),
        'steps': [[s(a), s(b)] for a, b in (p.get('steps') or []) if isinstance(a, str)],
        'word': s(p.get('word')),
        'recipe_count': num(p.get('recipe_count')) or 0,
        'recipe_sub': num(p.get('recipe_sub')),
        'recipe_kinds': {s(k): num(v) or 0 for k, v in (p.get('recipe_kinds') or {}).items()},
        'milestones': [
            {'name': s(m.get('name')), 'skill': num(m.get('skill')) or 0,
             'points': num(m.get('legacy_points')) or 1}
            for m in (p.get('milestones') or []) if isinstance(m, dict)
        ],
        'certification': norm_cert(p.get('certification')),
        'camp_objects': [x for x in (norm_camp_object(o) for o in (p.get('camp_objects') or [])) if x],
        'camp': norm_camp(p.get('camp')),
        'specific_perks': [x for x in (norm_perk(o) for o in (p.get('specific_perks') or [])) if x],
        'shared_perks': [x for x in (norm_perk(o) for o in (p.get('shared_perks') or [])) if x],
        # 技能等级表（仅钓鱼专业有）：[等级名, 所需技能, 获取说明, 书籍物品ID]
        # ⚠️ 说明文本里的 {book} 是书籍名的占位，UI 用第 4 项的物品 ID 去客户端取名替换。
        'ranks': [rank_row(r) for r in (p.get('ranks') or []) if isinstance(r, list)],
        'racials': [
            {'id': s(r.get('racial_id')), 'prof': s(r.get('profession')), 'note': s(r.get('note'))}
            for r in (p.get('racials') or []) if isinstance(r, dict)
        ],
        'bonuses': [
            {'name': s(b.get('name')), 'icon': s(b.get('icon')),
             'kind': s(b.get('kind')), 'text': s(b.get('text'))}
            for b in (p.get('bonuses') or []) if isinstance(b, dict)
        ],
        'fishing': norm_fishing(p.get('fishing')),
    }


def rank_row(r):
    """钓鱼技能等级行：[等级名, 所需技能, 获取说明, 书籍物品ID]。
    第 4 项在源数据里是 RSC 引用对象，只取其 id（书籍名走客户端）。"""
    name = s(r[0]) if len(r) > 0 else ''
    skill = s(r[1]) if len(r) > 1 else ''
    note = s(r[2]) if len(r) > 2 else ''
    book = None
    if len(r) > 3 and isinstance(r[3], dict):
        book = num(r[3].get('id'))
    return [name, skill, note, book]


def norm_cert(c):
    if not isinstance(c, dict):
        return None
    return {'id': num(c.get('id')), 'name': s(c.get('name')), 'icon': s(c.get('icon')),
            'skill': num(c.get('skill')) or 0, 'title': s(c.get('title'))}


def norm_camp(c):
    if not isinstance(c, dict):
        return None
    return {'name': s(c.get('name')), 'skill': num(c.get('skill')) or 0,
            'effect': s(c.get('effect'))}


def norm_fishing(f):
    """钓鱼专业独有：法术 / 鱼饵 / 食物 / 物品 / 称号 五组。

    五组源字段各不相同（spells 有 on_learn；lures 有 skill/bonus/minutes/new/hat；
    food 有 level/bonus/minutes；items 有 text/sub/req；titles 只有 id+name）——
    归一成统一条目结构，缺的字段留 null，Lua 侧一套渲染走完五组。
    """
    if not isinstance(f, dict):
        return None

    def entry(e):
        if not isinstance(e, dict):
            return None
        return {
            'id': num(e.get('id')),
            'name': s(e.get('name')),
            'icon': s(e.get('icon')),
            'text': s(e.get('text')),
            'sub': s(e.get('sub')),
            'skill': num(e.get('skill')),
            'bonus': num(e.get('bonus')),
            'minutes': num(e.get('minutes')),
            'level': num(e.get('level')),
            'on_learn': bool(e.get('on_learn')),
            'is_new': bool(e.get('new')),
            'hat': bool(e.get('hat')),
            'req': slist(e.get('req')),
        }

    out = {}
    for k in ('spells', 'lures', 'food', 'items', 'titles'):
        v = f.get(k)
        if isinstance(v, list):
            out[k] = [x for x in (entry(e) for e in v) if x]
    return out or None


# ── 逐页解析 ────────────────────────────────────────────────────────────────
def parse_index():
    """专业清单 + 各专业元数据。

    ★ 2026-10-09 站点改版：首页（/professions）的 RSC 载荷只剩布局
      （children/className…），不再带 professions 数据块。改为：
      ① 清单从首页导航 tile 的 href 抠（顺序即页面渲染顺序）；
      ② 每个专业的元数据（name/kind/lede/tips/camp_objects…）改从**各自子页**
        的 RSC 里抠 —— 明细页仍然完整携带 profession 字典（camping 也在）。
    """
    path = os.path.join(CACHE, 'professions.html')
    h = open(path, encoding='utf-8', errors='replace').read()
    slugs = []
    for s2 in re.findall(r'href="/professions/([a-z0-9\-]+)"', h):
        if s2 not in slugs:
            slugs.append(s2)
    if len(slugs) < 10:
        sys.exit('fc_parse: 主页只解析出 %d 个专业链接（站点可能改版）' % len(slugs))
    profs = []
    for slug in slugs:
        ppath = os.path.join(CACHE, 'professions_%s.html' % slug)
        prows = rsc_rows(ppath)
        pobj = deep_find(prows, lambda n, _s=slug: n.get('slug') == _s
                         and 'camp_objects' in n)
        if pobj is None:
            sys.exit('fc_parse: %s 页找不到专业元数据（站点可能改版）' % slug)
        prof = norm_profession(pobj)
        if prof is None:
            sys.exit('fc_parse: %s 专业元数据归一化失败' % slug)
        profs.append(prof)
    return {
        'kind': 'index',
        'updated': site_updated(path),
        'professions': profs,
        'nav': [{'slug': p['slug'], 'name': p['name'], 'icon': p['icon'], 'kind': p['kind']}
                for p in profs],
    }


def parse_detail(slug):
    path = os.path.join(CACHE, 'professions_%s.html' % slug)
    rows = rsc_rows(path)
    obj = deep_find(rows, lambda n: isinstance(n.get('profession'), dict)
                    and any(k in n for k in ('rows', 'enchants', 'gathering', 'lede', 'counts')))
    if obj is None:
        # camping 页结构与主页同构（没有明细），返回空明细即可
        return None
    prof = norm_profession(obj['profession']) or {}
    out = {
        'kind': 'detail',
        'slug': slug,
        'build': s(obj.get('build')),
        'lede': s(obj.get('lede') or prof.get('lede')),
        'word': s(obj.get('word') or prof.get('word')),
        'counts': norm_counts(obj.get('counts')),
        'rows': [x for x in (norm_row(r) for r in (obj.get('rows') or [])) if x],
        'groups': [
            {'key': s(g.get('key')), 'label': s(g.get('label')),
             'icon': s(g.get('icon')), 'count': num(g.get('count')) or 0}
            for g in (obj.get('groups') or []) if isinstance(g, dict)
        ],
        'favor': [
            {'id': num(f.get('id')), 'skill': num(f.get('skill')) or 0,
             'favor': num(f.get('favor')) or 0,
             'recipe': norm_favor_recipe(f.get('recipe'))}
            for f in (obj.get('favor') or []) if isinstance(f, dict)
        ],
        'camps': norm_place(obj.get('camps')),
        'vendor': norm_vendor(obj.get('vendor')),
        'leveling': norm_leveling(obj.get('leveling')),
        'enchants': [x for x in (norm_enchant(e) for e in (obj.get('enchants') or [])) if x],
        'crafted': [x for x in (norm_crafted(e) for e in (obj.get('crafted') or [])) if x],
        'gathering': norm_gathering(obj.get('gathering')),
        'smelting': norm_smelting(obj.get('smelting')),
        'sod': slist(obj.get('sod')),
    }
    return out


def norm_counts(c):
    if not isinstance(c, dict):
        return None
    return {k: num(v) for k, v in c.items()}


def norm_favor_recipe(r):
    if not isinstance(r, dict):
        return None
    return {'name': s(r.get('name')), 'makes': num(r.get('makes'))}


def norm_place(p):
    """营地坐标（联盟 a / 部落 h）。"""
    if not isinstance(p, dict):
        return None
    out = {}
    for side in ('a', 'h'):
        v = p.get(side)
        if not isinstance(v, dict):
            continue
        out[side] = {'faction': s(v.get('faction')), 'zone': s(v.get('zone')),
                     'place': s(v.get('place')), 'x': num(v.get('x')), 'y': num(v.get('y'))}
    return out or None


def norm_vendor(p):
    if not isinstance(p, dict):
        return None
    out = {}
    for side in ('a', 'h'):
        v = p.get(side)
        if not isinstance(v, dict):
            continue
        out[side] = {'npc': s(v.get('npc')), 'id': num(v.get('id')), 'role': s(v.get('role')),
                     'icon': s(v.get('icon')), 'x': num(v.get('x')), 'y': num(v.get('y'))}
    return out or None


def norm_route_recipes(rec):
    """升级路线引用的配方明细（站点 leveling.recipes：spellID → dict）。

    ★ 2026-10-08 前只留了键（[int(k) for k in ...]），值全丢 —— 附魔页的
      16 个路线法术因此接不上任何配方行（附魔配方在 enchants、魔棒两头都不在），
      1→300 固定路线的材料/来源全空。现在保留数值明细：
      name / taught_by 等字符串**有意不落**（显示名一律走客户端 GetSpellInfo，
      落英文名只会污染三语副本）。reagents 归一成 [[id, count], …]。
    """
    if not isinstance(rec, dict):
        return None
    out = {}
    for k, v in rec.items():
        if not isinstance(v, dict):
            continue
        try:
            sid = int(k)
        except (TypeError, ValueError):
            continue
        out[sid] = {
            'learn': num(v.get('learn')), 'yellow': num(v.get('yellow')),
            'green': num(v.get('green')), 'grey': num(v.get('grey')),
            'source': s(v.get('source')),
            'makes': num(v['makes'].get('id')) if isinstance(v.get('makes'), dict) else None,
            'reagents': [[num(m.get('id')), num(m.get('count')) or 1]
                         for m in (v.get('reagents') or [])
                         if isinstance(m, dict) and m.get('id')],
        }
    return out or None


def norm_leveling(lv):
    """升级路线。steps=分段步骤，shopping=按此路线要备的料，sold=商人卖的，
    quest=关联任务 id，parts=半成品配方，recipes=路线配方明细，learn=要学的法术。"""
    if not isinstance(lv, dict):
        return None
    return {
        'build': s(lv.get('build')),
        # ⚠️ 有意丢弃 lv['note']：那是数据源写给自己编辑看的构建说明
        #    （形如「Built by scripts/xxx.mjs; do not edit.」），
        #    对玩家零信息量，留在产物里只是噪声。
        'steps': [
            {'from': num(x.get('from')) or 0, 'to': num(x.get('to')) or 0,
             'spell': num(x.get('spell')), 'crafts': num(x.get('crafts')) or 0}
            for x in (lv.get('steps') or []) if isinstance(x, dict)
        ],
        'shopping': [
            {'id': num(x.get('id')), 'count': num(x.get('count')) or 0}
            for x in (lv.get('shopping') or []) if isinstance(x, dict)
        ],
        'sold': ints(lv.get('sold')),
        'quest': ints(lv.get('quest')),
        'parts': [int(k) for k in (lv.get('parts') or {})],
        'recipes': norm_route_recipes(lv.get('recipes')),
        'learn': [int(k) for k in (lv.get('learn') or {})],
        'rods': lv.get('rods') if isinstance(lv.get('rods'), (list, dict)) else None,
    }


def norm_gathering(g):
    """采集类专业的节点表。三种形态各自不同（站点如此），归一化为统一外观：

    · mining   [{ skill, items[itemID], zones[[区域名, 节点数]] }]
    · skinning [{ levels[起, 止], items[itemID], zones[[区域名, 数量]] }]
    · fishing  [{ zone, skill }]  ← ⚠️ 见 FISH_SKILL_OFFSET；zone 在此仍是**区域名**，
                生成期由 fc_zones.py 的对照表换成 AreaTable ID（产物里不落名字）

    ★ 站点的 `node`（Copper Vein / Peacebloom…）**故意丢弃**：那是 GameObject 名，
      客户端没有任何查询口，界面上改用「首个产出物的客户端中文名」当行标题
      （草药本来与节点同名，采矿则显示成产物名）。留着它只会变成产物里的一串英文。
    """
    if not isinstance(g, dict):
        return None
    out = {}

    def zones(v):
        return [[s(z[0]), int(z[1])] for z in (v or [])
                if isinstance(z, list) and len(z) >= 2 and isinstance(z[1], (int, float))]

    if isinstance(g.get('skinning'), list):
        out['skinning'] = [{
            'levels': ints(x.get('levels')),
            'items': ints(x.get('items')),
            'zones': zones(x.get('zones')),
        } for x in g['skinning'] if isinstance(x, dict)]
    for key in ('mining', 'herbalism'):
        if isinstance(g.get(key), list):
            out[key] = [{
                'skill': num(x.get('skill')),
                'items': ints(x.get('items')),
                'zones': zones(x.get('zones')),
            } for x in g[key] if isinstance(x, dict)]
    if isinstance(g.get('fishing'), list):
        out['fishing'] = [{
            'zone': s(x.get('zone')),
            'skill': (num(x.get('skill')) or 0) + FISH_SKILL_OFFSET,
            'raw': num(x.get('skill')),
        } for x in g['fishing'] if isinstance(x, dict)]
    return out or None


def norm_smelting(sm):
    if isinstance(sm, list):
        return [x for x in (norm_row(r) for r in sm) if x]
    return None


# ── 物品 ID 汇总（不落名称，只落「插件会碰到的 ID」）────────────────────────
def collect_item_ids(index, details):
    ids = set()

    def add(v):
        if isinstance(v, int) and not isinstance(v, bool) and v > 0:
            ids.add(v)

    for p in index['professions']:
        for o in p['camp_objects']:
            add(o['id'])
            for r in o['reagents']:
                add(r[0])
            if o['blueprint']:
                add(o['blueprint'][0])
        if p['certification']:
            add(p['certification']['id'])
        for grp in (p['fishing'] or {}).values():      # 钓鱼专业的鱼饵 / 食物 / 物品
            for e in grp:
                add(e['id'])
    for d in details.values():
        if d is None:
            continue
        for r in d['rows']:
            add(r['id'])
            for x in r['reagents']:
                add(x[0])
            if r['formula']:
                add(r['formula'][0])
        for e in d['enchants']:
            for x in e['reagents']:
                add(x[0])
        for e in d['crafted']:
            add(e['id'])
            for x in e['reagents']:
                add(x[0])
        for f in d['favor']:
            add(f['id'])
            if f['recipe']:
                add(f['recipe']['makes'])
        lv = d['leveling'] or {}
        for x in lv.get('shopping', []):
            add(x['id'])
        for x in lv.get('sold', []):
            add(x)
        for g in (d['gathering'] or {}).values():      # 采矿 / 剥皮：节点产物
            if isinstance(g, list):
                for x in g:
                    for i in x.get('items') or []:
                        add(i)
    return sorted(ids)


# ── 主流程 ──────────────────────────────────────────────────────────────────
def build():
    index = parse_index()
    slugs = [p['slug'] for p in index['professions']]
    details = {}
    for slug in slugs:
        d = parse_detail(slug)
        # camping（system 类）没有明细页，站点上它就是一份说明
        if d is None and slug != 'camping':
            sys.exit('fc_parse: %s 子页定位失败（站点可能改版）' % slug)
        details[slug] = d
    # build 号：从任一有明细的子页取（主页没有该字段）
    builds = {d['build'] for d in details.values() if d and d['build']}
    if len(builds) > 1:
        sys.exit('fc_parse: 各页 build 号不一致 %s' % sorted(builds))
    index['build'] = builds.pop() if builds else ''
    # ★ 采集表跨页共享但按页裁剪：采药页只带 herbalism，采矿页只带 mining，
    #   钓鱼/剥皮在所有采集页都带（裁剪版）。取各 key 最长的一份合并成全局表。
    gathering = {}
    for d in details.values():
        for k, v in (((d or {}).get('gathering')) or {}).items():
            if k not in gathering or len(v) > len(gathering[k]):
                gathering[k] = v
    if 'herbalism' not in gathering:
        sys.exit('fc_parse: 采药采集表缺失（定位策略或站点结构变了）')
    index['gathering'] = gathering
    return index, details


def dump(index, details, ids):
    os.makedirs(DATA, exist_ok=True)
    j = lambda p, o: json.dump(o, open(p, 'w', encoding='utf-8'), ensure_ascii=False,
                               sort_keys=False, separators=(',', ':'))
    j(os.path.join(DATA, 'index.json'), index)
    for slug, d in details.items():
        if d is None:
            continue
        j(os.path.join(DATA, 'prof_%s.json' % slug), d)
    json.dump(ids, open(os.path.join(DATA, 'item_ids.json'), 'w', encoding='utf-8'))
    return sum(1 for d in details.values() if d)


def report(index, details):
    print('=== 归一化结果 ===')
    print('  build %s · 站点标注 Updated %s' % (index['build'], index['updated']))
    print('  %-16s %-4s %-6s %-6s %-6s %-5s %-5s %-5s' %
          ('slug', 'kind', 'rows', 'ench', 'favor', 'steps', 'shop', 'camps'))
    T = [0] * 4
    for p in index['professions']:
        d = details.get(p['slug']) or {}
        lv = d.get('leveling') or {}
        n_rows = len(d.get('rows') or [])
        n_en = len(d.get('enchants') or []) + len(d.get('crafted') or [])
        n_fa = len(d.get('favor') or [])
        n_st = len(lv.get('steps') or [])
        n_sh = len(lv.get('shopping') or [])
        n_cp = len(p['camp_objects'])
        print('  %-16s %-4s %-6d %-6d %-6d %-5d %-5d %-5d' %
              (p['slug'], p['kind'][:4], n_rows, n_en, n_fa, n_st, n_sh, n_cp))
        T[0] += n_rows
        T[1] += n_en
        T[2] += n_fa
        T[3] += n_cp
    print('  %-16s %-4s %-6d %-6d %-6d' % ('合计', '', T[0], T[1], T[2]))
    json_kb = 0
    for f in glob.glob(os.path.join(DATA, '*.json')):
        json_kb += os.path.getsize(f)
    print('  data/ 落盘 %.0f KB' % (json_kb / 1024))


def diff_report(index, details, ids):
    """与上次 data/ 比对出变更报告 —— 用户「网站更新后快速跟进」的落点。"""
    old_dir = DATA
    if not os.path.isdir(old_dir):
        print('  （首次运行，无基线可比）')
        return
    def load(name):
        p = os.path.join(old_dir, name)
        if not os.path.exists(p):
            return None
        return json.load(open(p, encoding='utf-8'))

    old_idx = load('index.json')
    if old_idx is None:
        print('  （无旧基线）')
        return
    lines = []
    if old_idx.get('build') != index.get('build'):
        lines.append('构建号：%s → %s' % (old_idx.get('build'), index.get('build')))
    if old_idx.get('updated') != index.get('updated'):
        lines.append('站点日期：%s → %s' % (old_idx.get('updated'), index.get('updated')))

    old = {p['slug']: p for p in old_idx.get('professions', [])}
    new = {p['slug']: p for p in index.get('professions', [])}
    for slug in sorted(set(new) - set(old)):
        lines.append('新增专业：%s' % slug)
    for slug in sorted(set(old) - set(new)):
        lines.append('移除专业：%s' % slug)
    for slug in sorted(set(old) & set(new)):
        a, b = old[slug], new[slug]
        for k in ('summary', 'tips', 'verify', 'unknowns', 'status', 'steps'):
            if a.get(k) != b.get(k):
                lines.append('%s.%s 有改动' % (slug, k))
        if len(a.get('camp_objects') or []) != len(b.get('camp_objects') or []):
            lines.append('%s 营地道具：%d → %d' % (slug, len(a.get('camp_objects') or []),
                                                len(b.get('camp_objects') or [])))
    for slug, d in sorted(details.items()):
        if d is None:
            continue
        od = load('prof_%s.json' % slug)
        if od is None:
            lines.append('%s：初次收录' % slug)
            continue
        for key, label in (('rows', '配方'), ('enchants', '附魔'), ('crafted', '附魔材料'),
                           ('favor', '商人兑换'), ('groups', '分类')):
            if len(od.get(key) or []) != len(d.get(key) or []):
                lines.append('%s %s：%d → %d' % (slug, label, len(od.get(key) or []),
                                               len(d.get(key) or [])))
        ol = (od.get('leveling') or {})
        nl = (d.get('leveling') or {})
        if len(ol.get('steps') or []) != len(nl.get('steps') or []):
            lines.append('%s 升级分段：%d → %d' % (slug, len(ol.get('steps') or []),
                                                len(nl.get('steps') or [])))
        if len(ol.get('shopping') or []) != len(nl.get('shopping') or []):
            lines.append('%s 购物单：%d → %d' % (slug, len(ol.get('shopping') or []),
                                              len(nl.get('shopping') or [])))
    oi = set(load('item_ids.json') or [])
    ni = set(ids)
    if oi != ni:
        lines.append('物品 ID：%d → %d（新增 %d / 移除 %d）' %
                     (len(oi), len(ni), len(ni - oi), len(oi - ni)))
    os.makedirs(REPORTS, exist_ok=True)
    out = os.path.join(REPORTS, 'diff-%s.md' % (index.get('updated') or 'latest').replace('-', ''))
    with open(out, 'w', encoding='utf-8') as f:
        f.write('# 专业页数据变更报告\n\n')
        f.write('- 站点标注 Updated：%s\n- 构建号：%s\n- 物品 ID 总数：%d\n\n' %
                (index.get('updated'), index.get('build'), len(ids)))
        if lines:
            f.write('## 变更 %d 处\n\n' % len(lines))
            for l in lines:
                f.write('- %s\n' % l)
        else:
            f.write('## 无变更\n')
    print('  变更报告 → %s' % out)
    for l in lines[:30]:
        print('    - %s' % l)
    if len(lines) > 30:
        print('    ... 另有 %d 条，见报告文件' % (len(lines) - 30))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--diff', action='store_true')
    args = ap.parse_args()

    index, details = build()
    ids = collect_item_ids(index, details)
    if args.diff:
        diff_report(index, details, ids)
        return 0
    if args.report:
        report(index, details)
        return 0
    n = dump(index, details, ids)
    print('已生成 index.json + %d 个明细 + item_ids.json（%d 个物品 ID）' % (n, len(ids)))
    report(index, details)
    return 0


if __name__ == '__main__':
    sys.exit(main())
