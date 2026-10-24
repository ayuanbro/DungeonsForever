# -*- coding: utf-8 -*-
"""专业页数据 · 第 3 步：归一化 JSON → Core/Data/Data_Prof*.lua。

六个产物（保留已维护数据，按变化来源拆开）：

    Data_Professions.lua   13 个专业的元信息 / 营地物件 / Legacy 特权 / 待核实文案
    Data_ProfRecipes.lua   配方行 + 附魔 + 附魔材料 + 商人兑换 + 分类
    Data_ProfLeveling.lua  1→300 升级路线 + 购物单 + 营地与商贩坐标
    Data_ProfGathering.lua 采集节点表（采矿 / 采药 / 剥皮 / 钓鱼）
    Data_ProfVendors.lua   商人定位表（NPCID → 坐标，配方来源点图用）
    Data_ProfTrainers.lua  版本化维护输入中的训练师基线

★ 物品名 / 图标 / 品质 / 区域名一律不落盘：只存 ID，显示时由客户端给中文（用户 2026-09-23 定，
  2026-09-24 起采集页的区域名与节点名也照此办理）。这条是本方案体积能从 2.5MB 压到 1MB 的关键，
  也是「客户端一升级就自动跟上」的原因。区域名 → AreaTable ID 的对照表由 fc_zones.py 维护。

★ 紧凑数组的字段序集中定义在本文件（ROW_FIELDS / ENCHANT_FIELDS / …），
  生成时会写进 Lua 头注释；两处永远一致，改序只改这里。

用法：
    python fc_gen.py            在工具包目录生成 6 个 Lua
    python fc_gen.py --dry-run  只统计体积，不写盘
"""
import argparse
import copy
from contextvars import ContextVar
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
DATA = os.path.join(HERE, '_fc', 'data')
OUT = os.path.join(DF, 'Core', 'Data')
ZH_PATH = os.path.join(HERE, '_fc', 'i18n', 'zh.json')
_RENDER = ContextVar('fc_generation_inputs', default=None)


def _data_path(name):
    context = _RENDER.get()
    return os.path.join(context['data_dir'] if context else DATA, name)


def _read_json(path):
    with open(path, encoding='utf-8') as stream:
        return json.load(stream)


def _support_path(name):
    context = _RENDER.get()
    if context:
        frozen = os.path.join(context['data_dir'], name)
        if os.path.isfile(frozen):
            return frozen
    return os.path.join(HERE, name)


def _camp_areas():
    context = _RENDER.get()
    return context['camp_area'] if context else CAMP_AREA

sys.path.insert(0, HERE)
from fc_i18n import kind_tokens  # noqa: E402  「部位, level N」的拆词实现与白名单同一份

# ── 紧凑数组的字段序（唯一源头，写进 Lua 头注释）────────────────────────────
# ★ 键名必须与 fc_parse.py 的 norm_* 产出**逐字一致** —— 写错一个名字就是静默丢字段。
#   改完务必跑 `python fc_fields.py --strict`（会对着实际 JSON 键集核一遍）。
ROW_FIELDS = ('spell', 'id', 'count', 'cat', 'kind', 'effect', 'learn', 'yellow', 'green',
              'grey', 'is_new', 'reagents', 'formula', 'source', 'was', 'set', 'armor')
ENCHANT_FIELDS = ('name', 'short', 'group', 'text', 'learn', 'yellow', 'green', 'grey',
                  'reagents', 'source', 'is_new', 'sod', 'bis', 'spell', 'created')
CRAFTED_FIELDS = ('spell', 'id', 'count', 'learn', 'yellow', 'green', 'grey',
                  'reagents', 'taught_by', 'is_new')
GROUP_FIELDS = ('key', 'label', 'icon', 'count')
FAVOR_FIELDS = ('id', 'skill', 'favor', 'recipe', 'makes')
CAMP_OBJ_FIELDS = ('id', 'name', 'icon', 'skill', 'effect', 'buff', 'role', 'replaces',
                   'exclusive', 'capacity', 'reagents', 'blueprint')
MILESTONE_FIELDS = ('name', 'skill', 'points')
# perks 不直接 tup()，而是在 build_professions 里手工拼成一条紧凑数组：
#   {名称, 图标, 树, 满级, 逐级文本, 正文, 状态, 未确认项}
# 'id' 当字典键用掉，'effect' 并进正文，故两者不在 PERK_FIELDS 里 —— 但它们是**被取用**的，
# 列进 PERK_CONSUMED 供 fc_fields.py 审计（防「文档说用到了、其实没取」）。
PERK_FIELDS = ('name', 'icon', 'tree', 'max_rank', 'rank_texts', 'text', 'status', 'uncertain')
PERK_CONSUMED = ('id', 'name', 'icon', 'tree', 'max_rank', 'rank_texts', 'text', 'effect',
                 'status', 'uncertain')
STEP_FIELDS = ('from', 'to', 'spell', 'crafts')
SHOP_FIELDS = ('id', 'count')
NODE_FIELDS = ('items', 'skill', 'zones')
SKIN_FIELDS = ('levels', 'items', 'zones')
FISH_ENTRY_FIELDS = ('id', 'name', 'icon', 'text', 'sub', 'skill', 'bonus', 'minutes',
                     'level', 'on_learn', 'is_new', 'hat', 'req')

LUA_KEYWORDS = {
    'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function', 'if',
    'in', 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then', 'true', 'until', 'while',
}
IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


# ── Lua 字面量序列化 ────────────────────────────────────────────────────────
def lit(v):
    if v is None:
        return 'nil'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return repr(v)
    if isinstance(v, str):
        out = []
        for ch in v:
            if ch == '\\':
                out.append('\\\\')
            elif ch == '"':
                out.append('\\"')
            elif ch == '\n':
                out.append('\\n')
            elif ch == '\r':
                pass
            elif ord(ch) < 32:
                out.append(' ')
            else:
                out.append(ch)
        return '"' + ''.join(out) + '"'
    if isinstance(v, list):
        if not v:
            return '{}'
        return '{ ' + ', '.join(lit(x) for x in v) + ' }'
    if isinstance(v, dict):
        if not v:
            return '{}'
        parts = []
        for k, val in v.items():
            kk = k if (IDENT.match(str(k)) and k not in LUA_KEYWORDS) else '["%s"]' % k
            parts.append('%s=%s' % (kk, lit(val)))
        return '{ ' + ', '.join(parts) + ' }'
    sys.exit('fc_gen: 无法序列化的类型 %r' % type(v))


def tup(d, fields):
    """按字段序把 dict 转成位置数组（缺键给 nil）。"""
    return [d.get(f) for f in fields]


def olist(items, indent='            '):
    """对象数组：每项一行，缩进对齐，便于 diff。"""
    if not items:
        return '{}'
    lines = ['{']
    for it in items:
        lines.append('%s%s,' % (indent, lit(it)))
    lines.append(indent[:-4] + '}')
    return '\n'.join(lines)


def tlist(items, fields, indent='            '):
    """紧凑元组数组：每项一行。"""
    return olist([tup(x, fields) for x in items], indent)


def field_doc(fields, note=''):
    return '--   %s%s' % (' / '.join('[%d]%s' % (i + 1, f) for i, f in enumerate(fields)),
                          ('   ' + note if note else ''))


HEAD_COMMON = '''-- =============================================================================
-- 无限副本手册 · %s
--
-- ★ 本文件由 _temp/fc_gen.py 生成，请勿手改 ★
--   数据更新：python _temp/fc_update.py --apply（抓取 → 解析 → 生成 → 审计）
--
-- ★ 物品名 / 图标 / 品质 / 区域名一律不落盘：本文件只存 ID，
--   显示时由客户端给中文（GetItemInfo / GetItemInfoInstant / C_Map.GetAreaInfo）。
--   客户端查不到就把 ID 原样显示，不回落外部资料。
--
-- ★ 人写的文案（简介 / 提示 / 营地物件 / Legacy 特权 / 分类名 / 部位词 / 套装名）
--   已按 _temp/_fc/i18n/zh.json 套成中文；新增文案未登记时回落英文原文，
--   跑 `python _temp/fc_i18n.py --audit` 看还差哪几条。
--
-- 数据版本 build %s（标注更新日 %s）
'''

HEAD_ROW = '''-- 配方行字段序（由 fc_gen.py 的 ROW_FIELDS 生成，勿手改）：
--   %s
--   · count   一次做几个
--   · cat     分类（对应 groups 的 key）
--   · kind    产出物的「部位 + 等级」描述，如 "Cloth chest, level 12"
--   · learn/yellow/green/grey  = 学 / 黄 / 绿 / 灰 技能阈值
--   · reagents 材料 {{物品ID, 数量}, ...}
--   · formula  图纸 {物品ID, 品质}（nil = 不需要图纸）
--   · source   来源 {skill, read, drops={{npc,zone,chance,{lv1,lv2}}}, vendors={{name,zone,cost,skill,id}}}
--              ⚠️ drops / vendors 里的人名与地名是**游戏内专名**，原表未给 ID
--                 故保留原文；物品本身的名称仍由客户端给中文。
--   · was      改版前的旧材料表（只有 Forever 改过材料的配方才有，用于「共同变化」对照）
--   · effect   产出物的效果原文（客户端有中文时优先用客户端的）
--   · set / armor  套装名 / 护甲类型（同样无 ID，保留原文）
'''


def build_professions(index, details):
    profs = index['professions']
    perks = {}
    for p in profs:
        for k in ('specific_perks', 'shared_perks'):
            for pk in p[k]:
                if pk['id'] and pk['id'] not in perks:
                    perks[pk['id']] = [pk['name'], pk['icon'], pk['tree'], pk['max_rank'],
                                       pk['rank_texts'], pk['text'] or pk['effect'],
                                       pk['status']] + [pk['uncertain']]

    lines = []
    lines.append('local _, ns = ...\n')
    lines.append('ns.ProfData = {')
    lines.append('    build = %s,' % lit(index['build']))
    lines.append('    updated = %s,' % lit(index['updated']))
    lines.append('')
    lines.append('    -- 左侧导航顺序（按原表展示次序）')
    lines.append('    order = %s,' % lit(index['nav'] and [p['slug'] for p in profs] or []))
    lines.append('')
    lines.append('    -- Legacy 特权公共池：13 个专业共用同一批特权，'
                 '去重只存一份，专业里用 id 引用。')
    lines.append('    -- 字段序：%s' % ' / '.join(PERK_FIELDS))
    lines.append('    perks = {')
    for pid in sorted(perks):
        lines.append('        [%s] = %s,' % (lit(pid), lit(perks[pid])))
    lines.append('    },')
    lines.append('')
    lines.append('    -- 13 个专业。')
    lines.append('    --   camp 字段序：%s' % ' / '.join(CAMP_OBJ_FIELDS))
    lines.append('    --   miles = 里程碑 {名称, 技能, Legacy 点数}')
    lines.append('    --   steps = 该专业的说明步骤 {{标题, 正文}, ...}')
    lines.append('    pro = {')
    for p in profs:
        s = p['slug']
        lines.append('        [%s] = {' % lit(s))
        for k, v in (('name', p['name']), ('icon', p['icon']), ('kind', p['kind']),
                     ('section', p['section']), ('guide', p['guide']), ('word', p['word']),
                     ('summary', p['summary']), ('lede', p['lede']), ('title', p['title']),
                     ('description', p['description']), ('status', p['status']),
                     ('recipes', p['recipe_count']), ('sub', p['recipe_sub'])):
            if v not in (None, '', 0):
                lines.append('            %s = %s,' % (k, lit(v)))
        if p['recipe_kinds']:
            lines.append('            kinds = %s,' % lit(p['recipe_kinds']))
        if p['certification']:
            c = p['certification']
            lines.append('            cert = { %s, %s, %s, %s, %s },'
                         % (lit(c['id']), lit(c['name']), lit(c['icon']), lit(c['skill']),
                            lit(c['title'])))
        if p['milestones']:
            lines.append('            miles = %s,'
                         % tlist(p['milestones'], MILESTONE_FIELDS, ' ' * 16))
        if p['camp_objects']:
            lines.append('            camp = %s,'
                         % tlist(p['camp_objects'], CAMP_OBJ_FIELDS, ' ' * 16))
        pids = [k['id'] for k in p['specific_perks']] + [k['id'] for k in p['shared_perks']]
        pids = [x for x in pids if x]
        if pids:
            lines.append('            perks = %s,' % lit(pids))
        if p['racials']:
            lines.append('            racials = %s,' % lit(
                [[r['id'], r['prof'], r['note']] for r in p['racials']]))
        if p['bonuses']:
            lines.append('            bonuses = %s,'
                         % lit([[b['name'], b['icon'], b['kind'], b['text']]
                                for b in p['bonuses']]))
        for k in ('tips', 'verify', 'unknowns'):
            if p[k]:
                lines.append('            %s = %s,' % (k, lit(p[k])))
        if p['steps']:
            lines.append('            steps_title = %s,' % lit(p['steps_title']))
            if p['steps_note']:
                lines.append('            steps_note = %s,' % lit(p['steps_note']))
            lines.append('            steps = %s,'
                         % tlist([{'a': a, 'b': b} for a, b in p['steps']],
                                 ('a', 'b'), ' ' * 16))
        # 钓鱼技能等级表。★ 曾经是「解析了、翻译了、但忘了往 Lua 写」：
        #   ranks 在 fc_parse / fc_i18n.collect / localize 三处都在，唯独 build_professions
        #   没发射 → 数据文件里恒无此键，UI 那边是**静默读 nil**（不报错、整块不显示）。
        #   字段序与 fc_parse.rank_row 的产出同形：[等级名, 所需技能, 获取说明, 书籍物品ID]。
        if p.get('ranks'):
            lines.append('            -- 钓鱼技能等级 {等级名, 所需技能, 获取说明, 书籍物品ID}')
            lines.append('            --   ⚠️ 说明文本里的 {book} 占位由 UI 用书籍的中文名替换')
            lines.append('            ranks = %s,'
                         % tlist([{'name': r[0] if len(r) > 0 else None,
                                   'skill': r[1] if len(r) > 1 else None,
                                   'note': r[2] if len(r) > 2 else None,
                                   'book': r[3] if len(r) > 3 else None}
                                  for r in p['ranks']],
                                 ('name', 'skill', 'note', 'book'), ' ' * 16))
        if p['fishing']:
            lines.append('            fishing = {')
            lines.append('                -- 条目字段序：%s' % ' / '.join(FISH_ENTRY_FIELDS))
            for gk in ('spells', 'lures', 'food', 'items', 'titles'):
                if p['fishing'].get(gk):
                    lines.append('                %s = %s,'
                                 % (gk, tlist(p['fishing'][gk], FISH_ENTRY_FIELDS, ' ' * 20)))
            lines.append('            },')
        lines.append('        },')
    lines.append('    },')
    lines.append('}')
    head = HEAD_COMMON % ('专业页 · 专业元信息', index['build'], index['updated'])
    return head, '\n'.join(lines) + '\n'


def build_recipes(index, details):
    lines = []
    lines.append('local _, ns = ...\n')
    lines.append('local PARTS = {}')
    lines.append('local KEYS = {}')
    lines.append('local HAND = {')
    lines.append('}')
    lines.append('')
    for slug in [p['slug'] for p in index['professions']]:
        d = details.get(slug)
        if not d or not (d['rows'] or d['enchants'] or d['crafted'] or d['favor']):
            continue
        lines.append('KEYS[#KEYS + 1] = %s' % lit(slug))
        lines.append('PARTS[%s] = function() return {' % lit(slug))
        if d['word']:
            lines.append('        word = %s,' % lit(d['word']))
        if d['counts']:
            c = d['counts']
            lines.append('        counts = { total=%s, sourced=%s, unreadable=%s, items=%s },'
                         % (lit(c.get('total')), lit(c.get('sourced')),
                            lit(c.get('unreadable')), lit(c.get('recipeItems'))))
        if d['groups']:
            lines.append('        -- 分类 {key, 显示名, 图标, 条数}')
            lines.append('        groups = %s,' % tlist(d['groups'], GROUP_FIELDS))
        if d['rows']:
            src = next((r['source'] for r in d['rows'] if r['source']), {})
            if d['counts']:
                lines.append('')
                lines.append('        -- 原表自报：%s 条配方中 %s 条有来源、%s 条来源不可读'
                             % (c.get('total'), c.get('sourced'), c.get('unreadable')))
            lines.append('        rows = %s,' % tlist(d['rows'], ROW_FIELDS))
        if d['enchants']:
            lines.append('        enchants = %s,' % tlist(d['enchants'], ENCHANT_FIELDS))
        if d['crafted']:
            lines.append('        crafted = %s,' % tlist(d['crafted'], CRAFTED_FIELDS))
        if d['favor']:
            lines.append('        -- 商人兑换 {{兑换物ID, 所需技能, 所需青睐, 配方名, 产出ID}}')
            lines.append('        favor = %s,' % olist([
                [f['id'], f['skill'], f['favor'],
                 (f['recipe'] or {}).get('name'), (f['recipe'] or {}).get('makes')]
                for f in d['favor']], ' ' * 12))
        lines.append('} end')
        lines.append('')
    lines.append('for k, v in pairs(HAND) do')
    lines.append('    KEYS[#KEYS + 1] = k')
    lines.append('    PARTS[k] = function() return v end')
    lines.append('end')
    lines.append('')
    lines.append('ns.ProfRecipeKeys = KEYS')
    lines.append('ns.ProfRecipes = setmetatable({}, {')
    lines.append('    __index = function(t, k)')
    lines.append('        local f = PARTS[k]')
    lines.append('        if not f then return nil end')
    lines.append('        PARTS[k] = nil')
    lines.append('        local v = f()')
    lines.append('        rawset(t, k, v)')
    lines.append('        return v')
    lines.append('    end,')
    lines.append('})')
    lines.append('ns.EnsureProfRecipes = function(keys)')
    lines.append('    local t = ns.ProfRecipes')
    lines.append('    local list = keys or KEYS')
    lines.append('    for i = 1, #list do local _ = t[list[i]] end')
    lines.append('    return t')
    lines.append('end')
    head = HEAD_COMMON % ('专业页 · 配方与附魔', index['build'], index['updated'])
    head += HEAD_ROW % ' / '.join(ROW_FIELDS)
    head += '''-- 附魔行字段序：%s
-- 附魔材料字段序：%s
''' % (' / '.join(ENCHANT_FIELDS), ' / '.join(CRAFTED_FIELDS))
    return head, '\n'.join(lines) + '\n'


def build_leveling(index, details):
    lines = []
    lines.append('local _, ns = ...\n')
    lines.append('ns.ProfLeveling = {')
    for slug in [p['slug'] for p in index['professions']]:
        d = details.get(slug)
        if not d or not (d['leveling'] or d['camps'] or d['vendor']):
            continue
        lv = d['leveling'] or {}
        lines.append('    [%s] = {' % lit(slug))
        if lv.get('note'):
            lines.append('        note = %s,' % lit(lv['note']))
        if lv.get('steps'):
            lines.append('        -- 升级分段 {起始技能, 目标技能, 配方法术ID, 做几个}')
            lines.append('        steps = %s,' % tlist(lv['steps'], STEP_FIELDS))
        if lv.get('shopping'):
            lines.append('        -- 按这条路线练要备的料 {物品ID, 数量}')
            lines.append('        shopping = %s,' % tlist(lv['shopping'], SHOP_FIELDS))
        # rinfo（2026-10-08）：steps 引用但配方表（rows）里没有的法术 —— 典型是附魔
        # （路线配方游离在 enchants 之外）与附魔魔棒。按站点 leveling.recipes 的明细
        # 落成**纯数值**兜底表：界面/自动路线拿它当配方行（材料、颜色区间、产物图标、
        # 是否训练师直教）。名字不落盘 —— 显示一律走客户端 GetSpellInfo 出中文，
        # 落英文名只会污染三语副本（与 fc_parse.norm_route_recipes 的口径一致）。
        _rowsp = set()
        for _r in (d.get('rows') or []):
            if isinstance(_r.get('spell'), int):
                _rowsp.add(_r['spell'])
        _rinfo = {int(_s): _e for _s, _e in (lv.get('recipes') or {}).items()
                  if isinstance(_e, dict) and int(_s) not in _rowsp}
        if _rinfo:
            lines.append('        -- 步骤引用但配方表没有的法术 {spell={learn,yellow,green,grey,mats,makes,trainer}}')
            _parts = []
            for _sid in sorted(_rinfo):
                _e = _rinfo[_sid]
                _parts.append('[%d]={%s}' % (_sid, ', '.join([
                    'learn=%d' % (_e.get('learn') or 0),
                    'yellow=%d' % (_e.get('yellow') or 0),
                    'green=%d' % (_e.get('green') or 0),
                    'grey=%d' % (_e.get('grey') or 0),
                    'mats=%s' % (lit(_e.get('reagents') or [])),
                    'makes=%s' % (_e.get('makes') if _e.get('makes') else 'nil'),
                    'trainer=%s' % ('true' if _e.get('source') == 'trainer' else 'false'),
                ])))
            lines.append('        rinfo = { %s },' % ', '.join(_parts))
        for k, note in (('sold', '商人直接卖的（不用自己攒）'),
                        ('quest', '关联任务 ID'),
                        ('parts', '半成品配方产物 ID'),
                        ('learn', '这条路线要学的法术 ID')):
            if lv.get(k):
                lines.append('        -- %s' % note)
                lines.append('        %s = %s,' % (k, lit(lv[k])))
        if lv.get('rods'):
            # 原表给的是 {所需技能: 魔棒物品ID} 的字典；按技能排序成数组，
            # 免得 Lua 侧再 pairs() 排序（字典键会被序列化成字符串，反而更绕）。
            rods = sorted((int(k), v) for k, v in lv['rods'].items() if v)
            lines.append('        -- 附魔魔棒 {所需技能, 魔棒物品ID}')
            lines.append('        rods = %s,' % lit([[a, b] for a, b in rods]))
        if d['camps'] or d['vendor']:
            # 尾部追加 AreaTable ID（zone_ids.json，英文区域名 → AreaTable）：
            # 界面层用客户端 C_Map.GetMapInfoFromAreaID 现取中文区域名 + 解析 uiMapID 落航点。
            # ★ 查表必须用**汉化前**的区域名 —— main() 在 localize 之前已把本表算好存 CAMP_AREA。
            # 军需官 NPC 就站在本侧营地 → 沿用本侧营地的区域（数据源两处坐标互证一致）。
            area = {}
            for side in ('a', 'h'):
                area[side] = (_camp_areas().get(slug) or {}).get(side)
            if d['camps']:
                lines.append('        -- 营地：a=联盟 h=部落 {阵营, 区域, 地点, x, y, 区域AreaID}')
                lines.append('        camps = { a=%s, h=%s },'
                             % (lit(place_tup(d['camps'].get('a'), area['a'])),
                                lit(place_tup(d['camps'].get('h'), area['h']))))
            if d['vendor']:
                lines.append('        -- 军需官：a=联盟 h=部落 {NPC名, NPCID, 职责, 图标, x, y, 区域AreaID}')
                lines.append('        vendor = { a=%s, h=%s },'
                             % (lit(vendor_tup(d['vendor'].get('a'), area['a'])),
                                lit(vendor_tup(d['vendor'].get('h'), area['h']))))
        lines.append('    },')
    lines.append('}')
    head = HEAD_COMMON % ('专业页 · 升级路线与营地坐标', index['build'], index['updated'])
    head += '''-- 坐标 x / y 为 0..100 的地图百分比（原表原始精度，未换算成客户端像素）。
'''
    return head, '\n'.join(lines) + '\n'


def place_tup(p, area_id=None):
    if not p:
        return None
    t = [p['faction'], p['zone'], p['place'], p['x'], p['y']]
    if area_id:
        t.append(area_id)
    return t


def vendor_tup(v, area_id=None):
    if not v:
        return None
    t = [v['npc'], v['id'], v['role'], v['icon'], v['x'], v['y']]
    if area_id:
        t.append(area_id)
    return t


# 营地区域 → AreaTable ID（slug → {'a': id, 'h': id}）。必须在 **localize 之前**从原始
# （英文区域名）数据算好 —— localize 之后区域名已是中文，zone_ids.json 查不到。
CAMP_AREA = {}


def collect_camp_area(details_raw):
    zmap = zone_map()
    for slug, d in details_raw.items():
        if not d:
            continue
        ent = {}
        for side in ('a', 'h'):
            cp = (d.get('camps') or {}).get(side)
            if cp:
                if cp['zone'] not in zmap:
                    sys.exit('fc_gen: 营地区域名 %r 没有 AreaTable ID —— 补跑 fc_zones.py 再生成'
                             % (cp['zone'],))
                ent[side] = zmap[cp['zone']]
        _camp_areas()[slug] = ent


def zone_map():
    """英文区域名 → AreaTable ID（fc_zones.py 的产物）。"""
    p = _data_path('zone_ids.json')
    if not os.path.exists(p):
        sys.exit('fc_gen: 缺 %s —— 先跑 `python fc_zones.py`'
                 % os.path.relpath(p, os.path.dirname(HERE)))
    return _read_json(p)


def vendor_loc_map():
    """商人英文名 → {id, x, y, areaID, mapID}（fc_vendors.py 的产物）。缺文件视为空表。"""
    p = _data_path('vendor_loc.json')
    if not os.path.exists(p):
        return {}
    return _read_json(p)


def vendor_side_map():
    """商人英文名 → 'a'|'h'（fc_vendor_side.py 的产物；缺 = 中立/未知，双方可见）。"""
    p = _data_path('vendor_side.json')
    if not os.path.exists(p):
        return {}
    return _read_json(p)


def drop_loc_map():
    p = _data_path('drop_loc.json')
    if not os.path.exists(p):
        return {}
    return _read_json(p)


def area_map_ids():
    context = _RENDER.get()
    if context is not None:
        return dict(context['area_map'])
    p = os.path.join(OUT, 'Data_AreaMap.lua')
    if not os.path.exists(p):
        return {}
    m = {}
    for mm in re.finditer(r'\[(\d+)\] = (\d+)', open(p, encoding='utf-8', errors='replace').read()):
        m[int(mm.group(1))] = int(mm.group(2))
    return m


def zone_zh_map():
    """英文区域名 → 中文区域名（fc_zh_sync.py 对齐站点 zh-cn 页的产物）。缺文件视为空表。"""
    p = _data_path('zone_zh.json')
    if not os.path.exists(p):
        return {}
    return _read_json(p)


def localize_source_geo(details):
    """配方来源的地域信息落地（在 localize() 之后跑）：

    · vendors[].zone / drops[].zone：英文区域名 → 中文（zone_zh.json；未命中留原文，
      与 i18n 的回落口径一致 —— 4 个无限服自定义区域里 3 个站点已翻，缺的宁可不猜）。

    注意：商人 NPCID 的注入在 localize() **之前**（inject_vendor_ids，键是英文原名）；
    这里跑在 localize 之后，名字已汉化，按名查表会 miss。
    """
    zzh = zone_zh_map()
    for d in details.values():
        if not d:
            continue
        for coll in ('rows', 'enchants', 'crafted'):
            for r in d.get(coll) or []:
                src = r.get('source')
                if not isinstance(src, dict):
                    continue
                for dd in src.get('drops') or []:
                    if isinstance(dd, dict) and dd.get('zone') in zzh:
                        dd['zone'] = zzh[dd['zone']]
                for v in src.get('vendors') or []:
                    if isinstance(v, dict) and v.get('zone') in zzh:
                        v['zone'] = zzh[v['zone']]
    return details


def inject_enchant_ids(details):
    """给 enchants 回填 spell（法术ID）/ created（产物物品ID，纯附魔=None）。
    键 = 英文名（enchant_ids.json = fc_enchant_ids.py 对 Skillwright Recipes.lua
    [333] 段的行尾英文名注释 join 产物）。必须在 localize 之前跑 —— localize 会把
    name 套成中文，之后就没键可查了。"""
    p = _data_path('enchant_ids.json')
    if not os.path.exists(p):
        sys.exit('fc_gen: 缺 %s —— 先跑 `python fc_enchant_ids.py`' % p)
    jmap = _read_json(p)
    for d in details.values():
        if not d:
            continue
        for e in d.get('enchants') or []:
            j = jmap.get(e.get('name'))
            if j:
                e['spell'] = j.get('spell')
                e['created'] = j.get('created')
    return details


def inject_vendor_ids(details):
    """给配方来源的商人填 NPCID（vendor_loc.json；必须在 localize 之前跑 ——
    localize 会把名字套成中文，之后就没键可查了）。"""
    vloc = vendor_loc_map()
    for d in details.values():
        if not d:
            continue
        for coll in ('rows', 'enchants', 'crafted'):
            for r in d.get(coll) or []:
                src = r.get('source')
                if not isinstance(src, dict):
                    continue
                for v in src.get('vendors') or []:
                    if isinstance(v, dict):
                        ent = vloc.get(v.get('name')) or {}
                        if ent.get('id'):
                            v['id'] = int(ent['id'])
    return details


def inject_drop_ids(details):
    dloc = drop_loc_map()
    for d in details.values():
        if not d:
            continue
        for coll in ('rows', 'enchants', 'crafted'):
            for r in d.get(coll) or []:
                src = r.get('source')
                if not isinstance(src, dict):
                    continue
                for dd in src.get('drops') or []:
                    if isinstance(dd, dict) and not dd.get('id'):
                        ent = dloc.get(dd.get('npc')) or {}
                        if ent.get('id'):
                            dd['id'] = int(ent['id'])
    return details


def questie_json():
    """QuestieDB-Forever 提取产物（questie_extract.py 产物）。缺文件视为空表。"""
    p = _support_path('questie/questie_forever.json')
    if not os.path.exists(p):
        return {}
    return _read_json(p)


def area_zh_by_id():
    """areaID → 中文区名（_temp/_wago_AreaTable_zh.csv 的 ID/AreaName_lang 列）。"""
    out = {}
    p = _support_path('_wago_AreaTable_zh.csv')
    if not os.path.exists(p):
        return out
    with open(p, encoding='utf-8') as f:
        for ln in f:
            parts = ln.split(',')
            if len(parts) > 2 and parts[0].isdigit():
                out[int(parts[0])] = parts[2].strip()
    return out


def inject_questie_sources(details):
    """配方图纸来源补全（QuestieDB-Forever 第 4 源，localize 之前跑）：

    formula 图纸物品的 npcDrops（item 字段 2）/ vendors（字段 14）→ source.drops /
    source.vendors。fc 站点数据已有的条目**不覆盖**（setdefault 语义）——
    站点带中文 NPC 名与掉率，Questie 只补缺口。

    drops 条目形态与既有 drops 一致：{npc(英文名), zone(中文区名), chance(nil), lv{min,max}, id}。
    vendors 条目：{name(英文名), zone, cost(""), skill(nil), id}。
    NPC 名走英文原文（localize 不翻 NPC 名，与既有回落口径一致）。
    """
    qj = questie_json()
    if not qj:
        if _RENDER.get() is None:
            print('  QuestieDB 来源补全：缺 questie_forever.json，跳过')
        return details
    ndrops = qj.get('item_npcDrops') or {}
    nvend = qj.get('item_vendors') or {}
    ninfo = qj.get('npc_info') or {}
    azz = area_zh_by_id()
    added_d = added_v = 0
    for d in details.values():
        if not d:
            continue
        for coll in ('rows', 'enchants', 'crafted'):
            for r in d.get(coll) or []:
                f = r.get('formula')
                fid = f[0] if isinstance(f, (list, tuple)) and f else None
                if not fid:
                    continue
                src = r.get('source')
                if not isinstance(src, dict):
                    src = r['source'] = {}
                if not src.get('drops'):
                    ids = ndrops.get(str(fid)) or []
                    if ids:
                        arr = []
                        for i in ids:
                            inf = ninfo.get(str(i)) or []
                            arr.append({
                                'npc': inf[0] if inf else ('#' + str(i)),
                                'zone': azz.get(inf[3], '') if len(inf) > 3 else '',
                                'chance': None,
                                'lv': [x for x in (inf[1], inf[2]) if x is not None] if inf else [],
                                'id': int(i),
                            })
                        src['drops'] = arr
                        added_d += 1
                if not src.get('vendors'):
                    ids = nvend.get(str(fid)) or []
                    if ids:
                        arr = []
                        for i in ids:
                            inf = ninfo.get(str(i)) or []
                            arr.append({
                                'name': inf[0] if inf else ('#' + str(i)),
                                'zone': azz.get(inf[3], '') if len(inf) > 3 else '',
                                'cost': '',
                                'skill': None,
                                'id': int(i),
                            })
                        src['vendors'] = arr
                        added_v += 1
    if _RENDER.get() is None:
        print('  QuestieDB 来源补全：掉落 +%d 配方、商人 +%d 配方' % (added_d, added_v))
    return details


def inject_vendor_side(details):
    """给配方来源的商人填 side（'a'|'h'；vendor_side.json；键是英文原名，必须在
    localize 之前跑 —— 2026-10-10 用户：联盟商人不得出现在部落的视野里）。"""
    vside = vendor_side_map()
    n = 0
    for d in details.values():
        if not d:
            continue
        for coll in ('rows', 'enchants', 'crafted'):
            for r in d.get(coll) or []:
                src = r.get('source')
                if not isinstance(src, dict):
                    continue
                for v in src.get('vendors') or []:
                    if isinstance(v, dict) and v.get('name') in vside:
                        v['side'] = vside[v['name']]
                        n += 1
    if _RENDER.get() is None:
        print('  商人 side 注入：%d 处' % n)
    return details


def build_gathering(index, details):
    g = index.get('gathering') or {}
    zmap = zone_map()

    def zid(name):
        try:
            return zmap[name]
        except KeyError:
            sys.exit('fc_gen: 区域名 %r 没有 ID —— 补跑 fc_zones.py 再生成' % (name,))

    def zlist(v):
        return [[zid(z[0]), int(z[1])] for z in (v or [])]

    lines = []
    lines.append('local _, ns = ...\n')
    lines.append('ns.ProfGathering = {')
    lines.append('    -- 采矿 / 采药节点：{{产出物品ID}, 所需技能, {{区域ID, 节点数}, ...}}')
    lines.append('    --   ★ 行标题 = **首个产出物**的客户端中文名（草药本来就与节点同名，')
    lines.append('    --     采矿显示成产物名）：原始数据的节点名是 GameObject 名，客户端没有查询口，')
    lines.append('    --     所以本表不落节点名 —— 与「只存 ID、名字问客户端」同一条口径。')
    for key in ('mining', 'herbalism'):
        if g.get(key):
            rows = [{'items': x['items'], 'skill': x['skill'], 'zones': zlist(x['zones'])}
                    for x in g[key]]
            lines.append('    [%s] = %s,' % (lit(key), tlist(rows, NODE_FIELDS, ' ' * 8)))
    if g.get('skinning'):
        lines.append('    -- 剥皮档次：{{起始等级, 结束等级}, {产出物品ID}, {{区域ID, 计数}, ...}}')
        rows = [{'levels': x['levels'], 'items': x['items'], 'zones': zlist(x['zones'])}
                for x in g['skinning']]
        lines.append('    skinning = %s,' % tlist(rows, SKIN_FIELDS, ' ' * 8))
    if g.get('fishing'):
        lines.append('    -- 钓鱼区域：{区域ID, 所需钓鱼技能, 原始值}')
        lines.append('    --   ★ 区域名不落盘：客户端 C_Map.GetAreaInfo(区域ID) 给中文名。')
        lines.append('    --   ⚠️ skill 已按原表的编码偏移还原（原始值 -70..330 → 真实门槛 0..400），')
        lines.append('    --      原始值存在 raw 里备查。')
        lines.append('    fishing = %s,' % olist(
            [[zid(x['zone']), x['skill'], x['raw']] for x in g['fishing']], ' ' * 8))
    lines.append('}')
    head = HEAD_COMMON % ('专业页 · 采集节点表', index['build'], index['updated'])
    return head, '\n'.join(lines) + '\n'


def build_vendors(index, details):
    """商人定位表：ns.ProfVendors = { [NPCID] = {区域AreaID, 图uiMapID, x, y} }。

    为什么按 NPCID 键而不是名字：Data_ProfRecipes 里来源商人的名字会被 localize
    套成中文（zhTW/enUS 副本又各有一套），名字当键在三语副本下对不上；ID 恒定。
    配方行的 vendors[].id（localize_source_geo 填的）就是查这张表的钥匙。

    只落**可定位**的商人（有坐标且有 areaID 或 mapID）；没定位的商人本来也不该
    出现在这张表里 —— 界面对缺失键显示「未收录」，等 fc_vendors.py --resolve 补。
    """
    vloc = vendor_loc_map()
    rows = [(k, v) for k, v in sorted(vloc.items())
            if v.get('id') and v.get('x') is not None and (v.get('areaID') or v.get('mapID'))]
    lines = []
    lines.append('local _, ns = ...\n')
    lines.append('ns.ProfVendors = {')
    for name, v in rows:
        lines.append('    [%d] = { %s, %s, %s, %s }, -- %s'
                     % (int(v['id']),
                        lit(v.get('areaID')), lit(v.get('mapID')),
                        lit(v.get('x')), lit(v.get('y')),
                        name))
    lines.append('}')
    dloc = drop_loc_map()
    amap = area_map_ids()
    npc_rows = {}
    for name, ent in dloc.items():
        nid = ent.get('id')
        if not nid:
            continue
        rows2 = []
        for sp in ent.get('spawns') or []:
            if not (isinstance(sp, (list, tuple)) and len(sp) >= 3):
                continue
            aid, x, y = int(sp[0]), sp[1], sp[2]
            mid = amap.get(aid)
            if mid:
                rows2.append((aid, mid, x, y))
        if rows2:
            npc_rows[int(nid)] = (name, rows2)
    lines.append('')
    lines.append('ns.ProfNPCLocs = {')
    for nid in sorted(npc_rows):
        name, rows2 = npc_rows[nid]
        inner = ', '.join('{ %d, %d, %s, %s }' % (aid, mid, lit(x), lit(y))
                          for (aid, mid, x, y) in rows2)
        lines.append('    [%d] = { %s }, -- %s' % (nid, inner, name))
    lines.append('}')
    head = HEAD_COMMON % ('专业页 · 商人定位表（配方来源点图用）', index['build'], index['updated'])
    head += '''-- 行字段：{ 区域AreaID, 图uiMapID, x, y } —— x/y 为 0..100 地图百分比。
--   areaID 优先经 Data_AreaMap 转 uiMapID（暴风城等新生代边界图沿用既有校正口径）；
--   mapID 直接来自定位源（wowhead mapperData），两者取先可用者。
--   名字键故意不用：Data_ProfRecipes 的商人名会随语言本地化，ID 恒定。
--   ProfNPCLocs：掉落 NPC（QuestieDB 刷点，同 NPC 多区域 = 多行），键 = NPCID。
'''
    return head, '\n'.join(lines) + '\n'


class Loc(object):
    """生成期中文套用器：命中出中文，未命中回落英文原文。

    ★ 为什么不在 Lua 里做映射：站点改文案时对照表按**英文原键**失配 —— 插件照跑
      （那几句回落英文），跑一次 `fc_i18n.py --audit` 就知道要补哪几条，不阻塞更新。
      若把映射塞进 Lua，数据源一改文案就只能改代码。

    ★ 只覆盖人写的文案（简介 / 提示 / 营地物件 / 特权 / 分类名 / 部位词 / 套装名）。
      带客户端 ID 的（物品名 / 法术名 / 图标 / 品质）与游戏内专名（NPC / 区域 / 节点）
      不进来 —— 前者由客户端给中文，后者翻了反而对不上游戏。
    """

    def __init__(self, zh):
        self.zh = zh
        self.used = set()
        self.missed = set()

    def __call__(self, v):
        if not isinstance(v, str) or not v.strip():
            return v
        s = v.strip()
        if s in self.zh:
            self.used.add(s)
            return self.zh[s]
        self.missed.add(s)
        return v

    def lst(self, vs):
        return [self(x) for x in vs] if vs else vs


def localize(index, details, loc):
    """把 zh.json 套到 index / details 上（原地改深拷贝后返回）。

    ⚠️ 本函数的**取用点必须与 fc_i18n.py 的 collect() 一一对应**：
       collect() 收了哪些字段，这里就得套哪些字段；否则那条译文永远不会被用到。
       fc_i18n.py --audit 的「僵尸 0 条」就是这句话的可执行版本。
    """
    index = copy.deepcopy(index)
    details = copy.deepcopy(details)

    for p in index['professions']:
        for k in ('name', 'summary', 'lede', 'title', 'description', 'status', 'word',
                  'steps_title', 'steps_note'):
            p[k] = loc(p[k])
        for k in ('tips', 'verify', 'unknowns'):
            p[k] = loc.lst(p[k])
        if p['steps']:
            p['steps'] = [[loc(a), loc(b)] for a, b in p['steps']]
        for b in p['bonuses'] or []:
            b['name'] = loc(b['name'])
            b['text'] = loc(b['text'])
        for c in p['camp_objects'] or []:
            for k in ('name', 'effect', 'buff', 'role', 'replaces', 'exclusive'):
                c[k] = loc(c[k])
        for key in ('specific_perks', 'shared_perks'):
            for pk in p[key] or []:
                pk['name'] = loc(pk['name'])
                pk['text'] = loc(pk['text'])
                pk['effect'] = loc(pk['effect'])
                pk['rank_texts'] = loc.lst(pk['rank_texts'])
                pk['uncertain'] = loc.lst(pk['uncertain'])
        for m in p['milestones'] or []:
            m['name'] = loc(m['name'])
        if p['certification']:
            p['certification']['name'] = loc(p['certification']['name'])
            p['certification']['title'] = loc(p['certification']['title'])
        for r in p['racials'] or []:
            r['note'] = loc(r['note'])
        for rk in p.get('ranks') or []:                 # 钓鱼技能等级表 [名, 技能, 说明, 书]
            if len(rk) > 0:
                rk[0] = loc(rk[0])
            if len(rk) > 2:
                rk[2] = loc(rk[2])
        for entries in (p['fishing'] or {}).values():
            for e in entries:
                e['text'] = loc(e['text'])
                e['sub'] = loc(e['sub'])

    for d in details.values():
        if not d:
            continue
        for g in d['groups'] or []:
            g['label'] = loc(g['label'])
        for r in d['rows'] or []:
            # kind 是「部位, level N」的模板串：只翻部位词，等级另拼中文后缀。
            tk = kind_tokens(r['kind'])
            if tk is not None:
                tok, lv = tk
                if lv is None:
                    r['kind'] = loc(tok)
                elif not tok:
                    r['kind'] = '%d 级' % lv           # 原文只有 "level 30" 的情形
                else:
                    r['kind'] = '%s，%d 级' % (loc(tok), lv)
            r['armor'] = loc(r['armor'])
            r['set'] = loc(r['set'])
        for e in d['enchants'] or []:
            e['group'] = loc(e['group'])
            e['short'] = loc(e['short'])
            e['text'] = loc(e['text'])
            for b in e['bis'] or []:
                if len(b) > 2:
                    b[2] = loc(b[2])
        # 营地 / 军需官（取用点与 fc_i18n.collect 的收录一一对应，见那边注释）
        for side in ('a', 'h'):
            cp = (d.get('camps') or {}).get(side)
            if cp:
                for k in ('faction', 'zone', 'place'):
                    cp[k] = loc(cp[k])
            vd = (d.get('vendor') or {}).get(side)
            if vd:
                vd['npc'] = loc(vd['npc'])
                vd['role'] = loc(vd['role'])
        # rows.effect 有意不翻：方案 §3.2 的配方表只有「配方·产物 / 学·黄绿灰 / 材料 / 来源」
        # 四列，效果文本只在客户端 tooltip 里出现（那是官方中文）。留英文当兜底。
        # 配方来源里的商人：**已定位**（vendor_loc.json 里有条目，即拿到了 NPCID）的
        # 才进白名单汉化 —— 与 fc_i18n.collect 的收录条件一一对应；没定位的保留英文原文，
        # 等定位补上后自动进入下一轮对账。
        vloc = vendor_loc_map()
        for coll in ('rows', 'enchants', 'crafted'):
            for r in d.get(coll) or []:
                src = r.get('source')
                if not isinstance(src, dict):
                    continue
                for v in src.get('vendors') or []:
                    if isinstance(v, dict) and v.get('name') in vloc:
                        v['name'] = loc(v['name'])
    return index, details


def render_unmaintained(data_dir, area_map=None, no_i18n=False, i18n_seed=None):
    """Pure legacy builders over an explicit JSON snapshot, before maintenance."""
    from pathlib import Path
    context = {'data_dir': str(Path(data_dir).resolve()), 'area_map': area_map or {},
               'camp_area': {}}
    token = _RENDER.set(context)
    try:
        index = _read_json(_data_path('index.json'))
        details = {path.stem[len('prof_'):]: json.loads(path.read_text(encoding='utf-8'))
                   for path in sorted(Path(context['data_dir']).glob('prof_*.json'))}
        inject_enchant_ids(details)
        inject_vendor_ids(details)
        inject_drop_ids(details)
        inject_questie_sources(details)
        inject_vendor_side(details)
        collect_camp_area(details)
        if not no_i18n:
            if i18n_seed is None:
                zh_path = Path(context['data_dir']) / 'zh.json'
                if not zh_path.exists():
                    zh_path = Path(ZH_PATH)
                zh = json.loads(zh_path.read_text(encoding='utf-8'))
            else:
                zh = i18n_seed
            index, details = localize(index, details, Loc(zh))
        localize_source_geo(details)
        outputs = {}
        for name, builder in (
                ('Data_Professions.lua', build_professions),
                ('Data_ProfRecipes.lua', build_recipes),
                ('Data_ProfLeveling.lua', build_leveling),
                ('Data_ProfGathering.lua', build_gathering),
                ('Data_ProfVendors.lua', build_vendors)):
            head, body = builder(index, details)
            outputs[name] = (head + '\n' + body).encode('utf-8')
        return outputs
    except SystemExit as error:
        from fc_maintenance import MaintenanceError
        raise MaintenanceError(str(error)) from error
    finally:
        _RENDER.reset(token)


def revision_inputs(data_dir, maintenance_path=None):
    """Select exact historical inputs before localization, otherwise use current rules."""
    from fc_maintenance import read_manifest, unpack, prepared_input_sha, select_revision
    manifest = read_manifest(maintenance_path)
    if manifest.get('accepted_revisions'):
        prepared = render_unmaintained(data_dir, area_map=unpack(manifest['area_map']), no_i18n=True)
        active = select_revision(manifest, prepared_input_sha(prepared))
    else:
        active = manifest
    sources = render_unmaintained(data_dir, area_map=unpack(active['area_map']),
                                  i18n_seed=active.get('historical_i18n_seed'))
    return sources, active


def render_data(data_dir, reference_dir=None, maintenance_path=None):
    """Return six maintained Lua files as bytes without reading previous outputs.

    reference_dir is accepted for migration compatibility; normal generation
    deliberately uses the versioned area map and trainer seed in maintenance.
    """
    from fc_maintenance import maintained_model, render_model
    raw, active = revision_inputs(data_dir, maintenance_path)
    return render_model(maintained_model(raw, active))


def render_catalog(data_dir, maintenance_path=None):
    """Return an additive evidence catalogue, independently of UI suppressions.

    Original profession JSON is never filtered or rewritten on disk. This view
    retains all original evidence and adds the maintained recipe partitions and
    explicit identity evidence required by the specialization audit.
    """
    from pathlib import Path
    from fc_maintenance import maintained_model, normalize, stable_key
    directory = Path(data_dir)
    raw, manifest = revision_inputs(directory, maintenance_path)
    model = normalize(maintained_model(raw, manifest))
    recipes = model['Data_ProfRecipes.lua']['ProfRecipes']
    catalog = {path.stem[len('prof_'):]: json.loads(path.read_text(encoding='utf-8'))
               for path in sorted(directory.glob('prof_*.json'))}
    enchant_path = directory / 'enchant_ids.json'
    enchants = json.loads(enchant_path.read_text(encoding='utf-8')) if enchant_path.exists() else {}
    maintained_ids = {(entry['collection'], entry['name']): entry
                      for entry in manifest.get('catalog_id_evidence', [])}

    def positive(value):
        return isinstance(value, int) and not isinstance(value, bool) and value > 0

    def json_value(value):
        if isinstance(value, dict):
            if value and set(value) == set(range(1, len(value) + 1)):
                return [json_value(value[i]) for i in range(1, len(value) + 1)]
            return {str(key): json_value(item) for key, item in value.items()}
        return value

    def source_row(row):
        result = {key: json_value(value) for key, value in row.items() if key != '$extra'}
        for key in ('reagents', 'formula', 'was', 'bis'):
            if result.get(key) == {}:
                result[key] = []
        for key in ('drops', 'vendors'):
            if isinstance(result.get('source'), dict) and result['source'].get(key) == {}:
                result['source'][key] = []
        return result

    for slug, data in recipes.items():
        if slug not in catalog:
            # A maintained partition is not evidence from the latest webpage.
            # Its captured source version remains independent of the target
            # addon build; unknown sources must stay unknown.
            provenance = copy.deepcopy(manifest.get('supplemental_catalog_sources', {}).get(slug, {}))
            catalog[slug] = {'kind': 'detail', 'slug': slug,
                             'build': provenance.get('source_build', ''),
                             'source_provenance': provenance}
        target = catalog[slug]
        for collection in ('rows', 'enchants', 'crafted'):
            existing = target.setdefault(collection, [])
            identities = {stable_key(collection, row): row for row in existing}
            grouped = data.get(collection, {'$rows': {}, '$order': {}})
            for position in sorted(grouped['$order']):
                key = grouped['$order'][position]
                row = grouped['$rows'][key]
                if key not in identities:
                    existing.append(source_row(row))
                    identities[key] = existing[-1]
                current = identities[key]
                # Evidence input wins whenever it already has a valid identity.
                for field in ('spell', 'id', 'created'):
                    if not positive(current.get(field)) and positive(row.get(field)):
                        current[field] = row[field]
            if collection == 'enchants':
                for current in existing:
                    evidence = enchants.get(current.get('name')) or maintained_ids.get(
                        (collection, current.get('name'))) or {}
                    for field in ('spell', 'created'):
                        if not positive(current.get(field)) and positive(evidence.get(field)):
                            current[field] = evidence[field]
    outputs = {'prof_%s.json' % slug: (json.dumps(value, ensure_ascii=False, separators=(',', ':'))
                                      + '\n').encode('utf-8') for slug, value in sorted(catalog.items())}
    if enchant_path.exists():
        outputs['enchant_ids.json'] = enchant_path.read_bytes()
    return outputs


def generation_input_paths(data_dir=None, maintenance_path=None):
    """Files consumed by render_data, keyed by their frozen snapshot locations."""
    from pathlib import Path
    from fc_maintenance import DEFAULT_PATH
    directory = Path(data_dir or DATA)
    inputs = {path.name: path for path in sorted(directory.glob('prof_*.json'))}
    for name in ('index.json', 'enchant_ids.json', 'vendor_loc.json', 'vendor_side.json',
                 'drop_loc.json', 'zone_ids.json', 'zone_zh.json'):
        path = directory / name
        if path.exists():
            inputs[name] = path
    for name, fallback in (
            ('zh.json', Path(ZH_PATH)),
            ('questie/questie_forever.json', Path(HERE) / 'questie/questie_forever.json'),
            ('_wago_AreaTable_zh.csv', Path(HERE) / '_wago_AreaTable_zh.csv')):
        path = directory / name
        if not path.is_file():
            path = fallback
        if path.is_file():
            inputs[name] = path
    inputs['maintenance/professions.json'] = Path(maintenance_path or DEFAULT_PATH)
    return inputs


def main(argv=None):
    from pathlib import Path
    from fc_pipeline_common import publish_batch, require_repo_path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--no-i18n', action='store_true', help='legacy English diagnostic output')
    parser.add_argument('--data-dir', type=Path, default=Path(DATA))
    parser.add_argument('--maintenance', type=Path)
    options = parser.parse_args(argv)
    if options.no_i18n:
        outputs = render_unmaintained(options.data_dir, no_i18n=True)
    else:
        outputs = render_data(options.data_dir, maintenance_path=options.maintenance)
    destinations = {require_repo_path(Path(OUT) / name): content for name, content in outputs.items()}
    for path, content in destinations.items():
        print('%s: %d bytes sha256=%s' % (path.name, len(content), hashlib.sha256(content).hexdigest()))
    if not options.dry_run:
        publish_batch(destinations)
    return 0


if __name__ == '__main__':
    sys.exit(main())
