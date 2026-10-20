# -*- coding: utf-8 -*-
"""专业页数据 · 字段覆盖审计（§5.1 白名单的兑现检查）。

为什么单列一个脚本：`fc_gen.py` 的字段序元组是**手写的**，而 `fc_parse.py` 产出的
键名也是**手写的** —— 两边谁改了名字，另一边 `tup()` 就静默取到 nil，Lua 里少一个字段
但脚本全绿（实测已发生：`count` 被写成 `makes` → 「一次做几个」整列丢失；
`kind` / `was` 干脆不在字段序里 → 部位与旧材料表丢失）。

本脚本按「实际 JSON 键集」逐一对照生成期字段序：
  ✗ 表里有、元组里没有  → 静默丢字段（必须处理）
  · 元组里有、表里没有  → 该列恒 nil（死列，应删）

用法：
    python fc_fields.py            # 审计并列出问题
    python fc_fields.py --strict   # 有「静默丢字段」时 exit 1（供前检串联）
"""
import argparse
import glob
import json
import os
import sys
from fc_pipeline_common import configured_path, lua_runtime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = configured_path('DF_PIPELINE_DATA_DIR', os.path.join(HERE, '_fc', 'data'))

sys.path.insert(0, HERE)
import fc_gen  # noqa: E402


def load():
    index = json.load(open(os.path.join(DATA, 'index.json'), encoding='utf-8'))
    details = {}
    for f in glob.glob(os.path.join(DATA, 'prof_*.json')):
        slug = os.path.basename(f)[len('prof_'):-len('.json')]
        details[slug] = json.load(open(f, encoding='utf-8'))
    return index, details


def keyset(items):
    ks = set()
    for it in items or []:
        if isinstance(it, dict):
            ks |= set(it.keys())
    return ks


# ═══════════════════════════════════════════════════════════════════════════
# 发射复检：声称「已取用」的键，必须真的出现在**生成的 Lua** 里
# ═══════════════════════════════════════════════════════════════════════════
# 为什么单补这一道：上面的「解析产出 vs 生成器取用」只比**声明**——它只看得见
#   「这一键在生成器的取用清单里」。实测踩到的坑是声明与实际不一致：
#   `ranks`（钓鱼技能等级表）在 fc_parse / fc_i18n.collect / localize 三处都在、
#   取用清单里也登记了，唯独 build_professions 忘了发射 →
#   数据文件里恒无此键，UI 那边是**静默读 nil**（不报错、整块不显示）。
#   两道「声明」之间互相对齐、却与**产物**不对齐 —— 只有对着产物核才能发现。
#
# 做法：用 Lua 把生成的 4 个 Data_Prof*.lua 真的跑一遍，取回每种结构实际落地的键集，
#   再与「解析侧有该键 + 生成器声明取用」的键做差。差的那些＝声称用了却没写出来。
# 三类**正当的不落盘**，显式登记（不进本复检）：
#   · 改名列盘（发射时换了名字，用 EMIT_RENAME 映射，不算漏）；
#   · 并进别的键 / 拆到别的文件（detail.leveling → Data_ProfLeveling 的 steps…）；
#   · 页面类型标记（kind / slug / build），本来就只是解析期的记号。
EMIT_RENAME = {'camp_objects': 'camp', 'recipe_sub': 'sub', 'recipe_count': 'recipes',
               'recipe_kinds': 'kinds', 'certification': 'cert', 'milestones': 'miles',
               'specific_perks': 'perks', 'shared_perks': 'perks', 'camp': 'camp'}
EMIT_SKIP = {'kind', 'slug', 'build', 'gathering', 'leveling', 'smelting', 'sod'}
# scope → 产物文件（4 个 Data_Prof*.lua 全跑一遍，键集按 scope 归拢）
EMIT_FILES = ('Data_Professions.lua', 'Data_ProfRecipes.lua',
              'Data_ProfLeveling.lua', 'Data_ProfGathering.lua')


def nonempty_keys(items):
    """哪些键在**至少一条**记录上有内容。

    ★ 复检的判据必须是「源数据有内容」而不是「生成器声明取用」：
      生成器有不少字段是**条件发射**（`if p['lede']:` / `if lv.get('note'):`），
      当前全部记录都空时就一条都不写 —— 这不是漏发，是本来就没东西可发。
      拿「声明」当判据会把 lede / word / note 这类记成假阳性，
      拿「源数据有内容」当判据才既放过真实的情有可原、又抓住真的漏发。
    """
    ks = set()
    for it in items or []:
        if not isinstance(it, dict):
            continue
        for k, v in it.items():
            if v not in (None, '', 0, False, [], {}):
                ks.add(k)
    return ks


def _emitted_keys():
    """用 Lua 跑一遍生成的 4 个数据文件，取回每种结构的实际键集。"""
    for TOOLS in (os.path.join(HERE, 'tools'),):
        if os.path.isdir(TOOLS) and TOOLS not in sys.path:
            sys.path.insert(0, TOOLS)
    import tf_dryrun as T

    lua = lua_runtime()
    lua.execute(T.STUB)
    lua.execute('TF_NS = {}')
    root = configured_path('DF_PIPELINE_OUTPUT_DIR', os.path.join(os.path.dirname(HERE), 'Core', 'Data')).replace('\\', '/')
    ev = lua.eval('function(rel) local c = loadfile("%s/" .. rel) '
                  'return c("DungeonsForever", TF_NS) end' % root)
    for f in EMIT_FILES:
        ev(f)
    # ★ Data_ProfRecipes 是惰性建表：pairs 走不到 __index，不显式物化的话
    #   kset(rc) 永远是空集，复检会把 detail 的 rows/groups/enchants 全报成漏发。
    lua.execute('if TF_NS.EnsureProfRecipes then TF_NS.EnsureProfRecipes() end')

    def kset(t):
        """容器 → 其「元素键集」并集（数组则取每项的键并集）。"""
        out = set()
        if t is None or not hasattr(t, 'items'):
            return out
        for _, v in t.items():
            if v is not None and hasattr(v, 'items'):
                for k in v.keys():
                    if isinstance(k, str):
                        out.add(k)
        return out

    ds, rc, lv, ga = (lua.eval('TF_NS.ProfData'), lua.eval('TF_NS.ProfRecipes'),
                      lua.eval('TF_NS.ProfLeveling'), lua.eval('TF_NS.ProfGathering'))
    return {
        'profession': kset(ds.pro),
        # detail 的键分落两个文件：配方/附魔/分类在 Recipes，升级路线与营地在 Leveling
        # （leveling / camps / vendor 三项就住在后者里，故并集才是它的完整落地键集）。
        'detail': kset(rc) | kset(lv),
        'leveling': kset(lv),
        'gathering': set() if ga is None else set(),
    }


def emit_audit(SPEC, pools):
    """把「源数据有内容 + 声明取用」与「产物实际落地」对一遍，返回缺失项列表。"""
    print()
    print('=== 发射复检（源数据有内容 且 声明取用 vs 产物实际落地）===')
    try:
        emitted = _emitted_keys()
    except Exception as e:
        raise ValueError('Lua emission validation failed: %s' % e) from e

    missing = []
    for scope in ('profession', 'detail', 'leveling'):
        declared, _ = SPEC[scope]
        got = emitted.get(scope, set())
        if not got:
            continue
        want = ((declared & nonempty_keys(pools[scope])) - EMIT_SKIP)
        want = {EMIT_RENAME.get(k, k) for k in want}
        lack = sorted(want - got)
        print('  %-11s 该发 %2d 键 · 产物 %2d 键 · %s'
              % (scope, len(want), len(got), '✗ 漏发 %s' % lack if lack else '✓'))
        for k in lack:
            missing.append('%s.%s' % (scope, k))
    return missing


def audit(label, items, fields):
    got = keyset(items)
    want = set(fields)
    dropped = sorted(got - want)
    dead = sorted(want - got)
    n = len(items or [])
    flag = '✗' if dropped else ('·' if dead else '✓')
    print('%-46s %4d 项  %s' % (label, n, flag))
    if dropped:
        print('        ✗ 静默丢字段：%s' % ', '.join(dropped))
    if dead:
        print('        · 恒 nil 死列：%s' % ', '.join(dead))
    return dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--strict', action='store_true')
    ap.add_argument('--source-only', action='store_true',
                    help='只审计源字段；统一入口随后校验维护修订后的完整 Lua 逻辑')
    args = ap.parse_args()

    index, details = load()
    bad = []

    print('=== 专业页字段覆盖审计 ===')
    print()

    # ── 配方 / 附魔 ────────────────────────────────────────────────────────
    rows, enchs, crf, grps = [], [], [], []
    for d in details.values():
        if not d:
            continue
        rows += d['rows'] or []
        enchs += d['enchants'] or []
        crf += d['crafted'] or []
        grps += d['groups'] or []
    bad += audit('ns.ProfRecipes[*].rows → ROW_FIELDS', rows, fc_gen.ROW_FIELDS)
    bad += audit('ns.ProfRecipes[*].enchants → ENCHANT_FIELDS', enchs, fc_gen.ENCHANT_FIELDS)
    bad += audit('ns.ProfRecipes[*].crafted → CRAFTED_FIELDS', crf, fc_gen.CRAFTED_FIELDS)
    bad += audit('ns.ProfRecipes[*].groups → GROUP_FIELDS', grps, fc_gen.GROUP_FIELDS)

    # ── 专业元信息 ─────────────────────────────────────────────────────────
    profs = index['professions']
    bad += audit('ns.ProfData.pro[*].camp → CAMP_OBJ_FIELDS',
                 [c for p in profs for c in (p['camp_objects'] or [])],
                 fc_gen.CAMP_OBJ_FIELDS)
    bad += audit('ns.ProfData.pro[*].miles → MILESTONE_FIELDS',
                 [m for p in profs for m in (p['milestones'] or [])],
                 fc_gen.MILESTONE_FIELDS)
    bad += audit('ns.ProfData.perks[id] → PERK_CONSUMED',
                 [k for p in profs for key in ('specific_perks', 'shared_perks')
                  for k in (p[key] or [])],
                 list(fc_gen.PERK_CONSUMED))
    bad += audit('ns.ProfData.pro[*].fishing[*] → FISH_ENTRY_FIELDS',
                 [e for p in profs for g in (p['fishing'] or {}).values() for e in g],
                 fc_gen.FISH_ENTRY_FIELDS)

    # ── 升级路线 ───────────────────────────────────────────────────────────
    st = []
    for d in details.values():
        if d and d['leveling']:
            st += d['leveling'].get('steps') or []
    bad += audit('ns.ProfLeveling[*].steps → STEP_FIELDS', st, fc_gen.STEP_FIELDS)

    # ── 采集 ───────────────────────────────────────────────────────────────
    g = index.get('gathering') or {}
    bad += audit('ns.ProfGathering.mining → NODE_FIELDS',
                 g.get('mining'), fc_gen.NODE_FIELDS)
    bad += audit('ns.ProfGathering.herbalism → NODE_FIELDS',
                 g.get('herbalism'), fc_gen.NODE_FIELDS)
    bad += audit('ns.ProfGathering.skinning → SKIN_FIELDS',
                 g.get('skinning'), fc_gen.SKIN_FIELDS)
    bad += audit('ns.ProfGathering.fishing → (zone,skill,raw) 手写',
                 g.get('fishing'), ('zone', 'skill', 'raw'))

    # ── 顶层键：解析产出 vs 生成器取用 ──────────────────────────────────────
    # 分类而不是「一票否决」：有些键是**故意不取**的（冗余/重复/恒空），
    # 把它们和「该取却没取」混在一起报，久了就没人看了。故拆成三档 + 理由。
    print()
    print('=== 顶层键覆盖（解析产出 vs 生成器取用）===')
    SPEC = {
        'profession': (
            {'slug', 'name', 'icon', 'kind', 'section', 'guide', 'word', 'summary', 'lede',
             'title', 'description', 'status', 'recipe_count', 'recipe_sub', 'recipe_kinds',
             'certification', 'milestones', 'camp_objects', 'specific_perks', 'shared_perks',
             'racials', 'bonuses', 'tips', 'verify', 'unknowns', 'steps', 'steps_title',
             'steps_note', 'fishing', 'ranks'},
            {'camp': '＝ camp_objects[0] 的摘要，三档详情已全在 camp_objects 里'},
        ),
        'detail': (
            {'rows', 'enchants', 'crafted', 'favor', 'groups', 'word', 'counts', 'leveling',
             'camps', 'vendor', 'build'},
            {'gathering': '已合并进 index.gathering（跨页取最长的那份）',
             'kind': '恒为 "detail"，是数据源的页面类型标记',
             'lede': '与 index.professions[].lede 逐字相同，取 index 那份',
             'slug': '就是文件名 prof_<slug>.json 的后半段',
             'sod': '已按条目并进 enchants[].sod 布尔位',
             'smelting': '站点该块当前恒空；一旦填充会在下面单独告警'},
        ),
        'index': (
            {'professions', 'gathering', 'build', 'updated', 'nav'},
            {'kind': '恒为 "index"，同上'},
        ),
        'leveling': (
            {'note', 'steps', 'shopping', 'sold', 'quest', 'parts', 'learn', 'rods'},
            {'build': '与 detail.build 同值',
             'recipes': '⊆ steps[].spell 的并集（只用于站点自己排序）'},
        ),
    }
    pools = {
        'profession': profs,
        'detail': [d for d in details.values() if d],
        'index': [index],
        'leveling': [d['leveling'] for d in details.values() if d and d['leveling']],
    }
    for scope, (used, redundant) in SPEC.items():
        ks = keyset(pools[scope])
        unknown = sorted(ks - used - set(redundant))
        if unknown:
            bad.append('%s: %d 个键既没取用也没登记' % (scope, len(unknown)))
            print('  %-11s ✗ 未登记：%s' % (scope, ', '.join(unknown)))
        else:
            print('  %-11s ✓ 已用 %d 键 · 故意不取 %d 键' % (scope, len(ks & used), len(ks & set(redundant))))
        for k in sorted(ks & set(redundant)):
            print('        · %-11s %s' % (k, redundant[k]))
        # 恒空的「待接入」块一旦有内容就得有人管
        for k in ('smelting',):
            nonempty = [x for x in pools[scope] if x.get(k) not in (None, {}, [], '')]
            if nonempty:
                print('        ⚠️ %s 有内容了（%d 份），生成器尚未接入' % (k, len(nonempty)))

    print()
    missing = [] if args.source_only else emit_audit(SPEC, pools)
    if missing:
        bad.append('发射复检：%d 个键声明取用但产物里没有' % len(missing))
        for m in missing:
            print('        ✗ %s 声明取用，但产物 Lua 里没有' % m)

    print()
    if bad:
        print('✗ 有 %d 处静默丢字段，必须修（改 fc_gen.py 的字段序或 fc_parse.py 的键名）'
              % len(bad))
        if args.strict:
            return 1
    else:
        print('✓ 字段序与解析产出完全对齐（含产物发射复检）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
