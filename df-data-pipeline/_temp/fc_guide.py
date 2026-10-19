# -*- coding: utf-8 -*-
"""专精指南数据管线：_cg_parsed.json + _cg_trans/*.json → Core/Data/Data_ClassGuide.lua。

- _cg_parse_guide.py 先把 27 页 markup 解析成英文结构 JSON（flow 保序）。
- _cg_trans/<cls>_<spec>.json 存在则按 key/t 逐元素覆盖为中文；缺译文回落英文。
- 文本占位约定（生成层统一清洗）：
    |sID|   法术引用，运行期客户端取名 + 悬停
    换行    条目分隔（原 \x05 → Lua "\n"，一个 FontString 内多行）
    \x03/\x04 加粗占位、\x06/\x07 阵营、\x08/\x09 勾选 → 剥除
- 界面署名只写「数据来源：wowhead」。

用法：python _temp/fc_guide.py
"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '_cg_parsed.json')
TRANS = os.path.join(HERE, '_cg_trans')
DST = os.path.join(os.path.dirname(HERE), 'Core', 'Data', 'Data_ClassGuide.lua')

LEAK = ['站点', '出处', '上游', '参考', '照抄', '抄它', '剥离', '抽取段',
        'foreverchanges', 'ForeverChanges', 'AtlasQuest']

KEYS = ['warrior_arms', 'warrior_fury', 'warrior_protection',
        'paladin_holy', 'paladin_protection', 'paladin_retribution',
        'hunter_beast-mastery', 'hunter_marksmanship', 'hunter_survival',
        'rogue_assassination', 'rogue_combat', 'rogue_subtlety',
        'priest_discipline', 'priest_holy', 'priest_shadow',
        'shaman_elemental', 'shaman_enhancement', 'shaman_restoration',
        'mage_arcane', 'mage_fire', 'mage_frost',
        'warlock_affliction', 'warlock_demonology', 'warlock_destruction',
        'druid_balance', 'druid_feral', 'druid_restoration']

CLASS_OF = {'warrior': 'WARRIOR', 'paladin': 'PALADIN', 'hunter': 'HUNTER',
            'rogue': 'ROGUE', 'priest': 'PRIEST', 'shaman': 'SHAMAN',
            'mage': 'MAGE', 'warlock': 'WARLOCK', 'druid': 'DRUID'}

SPEC_OF = {'arms': 'arms', 'fury': 'fury', 'protection': 'prot',
           'holy': 'holy', 'retribution': 'ret',
           'beast-mastery': 'bm', 'marksmanship': 'mm', 'survival': 'surv',
           'assassination': 'assa', 'combat': 'combat', 'subtlety': 'sub',
           'discipline': 'disc', 'shadow': 'shadow',
           'elemental': 'ele', 'enhancement': 'enh', 'restoration': 'resto',
           'arcane': 'arcane', 'fire': 'fire', 'frost': 'frost',
           'affliction': 'affli', 'demonology': 'demo', 'destruction': 'destro',
           'balance': 'balance', 'feral': 'feral'}

STRIP = ['\x03', '\x04', '\x06', '\x07', '\x08', '\x09']

# sw 表头按列判定 good/bad：词边界收紧，杜绝 'con' 误命中 Control/Concentrated 之类。
WEAK_RE = re.compile(r'weakness|disadvantage|\bcons\b|劣势|缺點|缺点')
GOOD_RE = re.compile(r'strength|advantage|\bpros\b|优势|優點|优点')

# races 板块的阵营分组标题（含解析器把相邻段落粘一起的融合形态）。
FACTION_EXACT = {'alliance', 'horde', 'both', 'all', '联盟', '部落', '双方', '全部'}
FACTION_PREFIX = ['alliance/horde', 'alliance / horde', '联盟/部落', '联盟 / 部落',
                  'alliance', 'horde', '联盟', '部落']
SENT_PUNCT = set('。.！!？?,，;；:：、…—')

# 解析器偶尔把标题位置解析成 JS 字面量（如 priest_disc prof 出现过 h4="false"）。
# 这类元素会在界面上渲染成字面小标题，按严格等值在最终 flow 上丢弃。
JUNK_VALS = {'false', 'true', 'nil', 'null', 'none', 'undefined'}

# ---------------------------------------------------------------------------
# 版本名术语兜底归一（merge 之后、写盘之前对中文文本做规则处理）
#   wowhead 英文原文的版本名 Forever / WoW Forever 在中文译文里被译成「永恒·永恆」「永久」，
#   或干脆留下 latin「Forever」/「《Forever》」——统一纠正为「无限」。
#   规范（Spec）：
#     · 全称        《魔兽世界：无限》—— 每篇 flow 内**首次**出现的版本名升级为全称
#     · 版本简称    《无限》          —— 该 flow 内其余版本名
#     · 服务器指代  无限服            —— in Forever / 永久服 / 永恒服 …
#     · 版本后缀    无限版本 / 无限版
#     · 测试服      无限测试服
#     · 任何情况不得产出 `魔兽世界：《无限》`、`《无限》服` 这类怪搭配；版本名前后不留空格。
#   ★ 只命中「版本指代」语境；放过副词性「永久」（永久提高 / 永久提升 / 永久（性地）
#     重做·重新设计 —— 表 permanently 义）。裸「永恒/永恆」按版本指代处理，带 (?!之)
#     负向保护（「永恒之井」等专名不受影响）。
#   ★ 该层保证重跑幂等：将来新译文再犯同样的误译会被自动纠正。
# ---------------------------------------------------------------------------
CANON_TITLE = '无限服新增的职业-种族组合'
FULL_NAME = '《魔兽世界：无限》'

# 固定标题短语（wowhead races 板块标题 “New Class-Race Combinations Available for
# Forever” 的各种误译/半译形态）——字面整段/前缀归一到规范译名，必须最先执行。
TERM_TITLE_LITERALS = [
    '永久》可用的全新职业—种族组合',
    '《永久》新增可用的职业—种族组合',
    '经典永恒版本新增的种族与职业组合',
    '《永恒》版本可用的全新种族职业组合',
    '《永恒》新增的职业-种族组合',
    '《永恒》新增的职业与种族组合',
    '《永久》新增的职业-种族组合',
    '永久新增的种族-职业组合',
    '永久开放的新职业种族组合',
    '永久开放全新职业-种族组合',
    '永久开放全新的种族-职业组合',
    '永久可用的全新种族-职业组合',
    '永久开放的全新种族-职业组合',
    '全新职业-种族组合永久开放',
    '全新职业种族组合永久开放',
    '永恒服新增可用的职业-种族组合',
    '《永久经典》中开放的新职业-种族组合',
    '新增的种族与职业组合(适用于《永恒》)',
    'Forever 中新增的职业-种族组合',
    'Forever中可用的新职业-种族组合',
    '《Forever》新增的职业与种族组合',
]

# 经英文核对确认属「版本指代」（wowhead 原句 “…changed for Forever”）的整句纠正。
TERM_PHRASE_LITERALS = [
    ('所有专业都已被永久重做', '所有专业都已随《无限》重做'),
    ('所有专业都被永久性地重新设计了', '所有专业都已随《无限》重做'),
]

_TERM_REGEX = [
    # 全称（含书名号）
    (r'《WoW\s*[Ff]orever》', '《魔兽世界：无限》'),
    (r'《魔兽世界[：:·]\s*(?:[Ff]orever|永恒|永恆|永久)》', '《魔兽世界：无限》'),
    # 简称（书名号，先长后短）
    (r'《[Ff]orever》', '《无限》'),
    (r'《永久经典》', '《无限》'),
    (r'《永久[ _]?[bB]eta》', '无限测试服'),
    (r'《永恒》', '《无限》'),
    (r'《永恆》', '《无限》'),
    (r'《永久》', '《无限》'),
    # 全称（无书名号）
    (r'魔兽世界[：:·]经典永恒版本', '《魔兽世界：无限》'),
    (r'WoW[：:]?\s*[Ff]orever', '《魔兽世界：无限》'),
    (r'魔兽世界[：:·]?\s*[Ff]orever', '魔兽世界：无限'),
    (r'魔兽世界[：:·]?\s*(?:永恒|永恆)', '魔兽世界：无限'),
    (r'魔兽世界[：:·]?\s*永久', '魔兽世界：无限'),
    # 残缺书名号（译文丢了左书名号）
    (r'(?:永恒|永恆|永久)》', '《无限》'),
    # 引号式简称
    (r'“(?:永恒|永恆)”版本', '《无限》版本'),
    (r'“永久”版本', '《无限》版本'),
    # beta
    (r'[Ff]orever\s*[Bb]eta', '无限测试服'),
    (r'《无限》测试服', '无限测试服'),
    # in Forever（含 latin）
    (r'在\s*[Ff]orever\s*中', '在无限服中'),
    (r'于\s*[Ff]orever\s*中', '于无限服中'),
    # 服务器指代
    (r'《永久》怀旧服', '无限服'),
    (r'永久经典怀旧服', '无限服'),
    (r'永久怀旧服', '无限服'),
    (r'(?:永恒|永恆)服', '无限服'),
    (r'永久服', '无限服'),
    (r'永久魔兽', '无限服'),
    (r'[Ff]orever\s*服', '无限服'),
    # 版 / 版本
    (r'经典永恒版本', '无限版本'),
    (r'(?:永恒|永恆)版本', '无限版本'),
    (r'永久版本', '无限版本'),
    (r'[Ff]orever\s*版本', '无限版本'),
    (r'(?:永恒|永恆)版', '无限版'),
    (r'永久版', '无限版'),
    # 裸 in 短语（限定「中/里」）
    (r'(?:永恒|永恆)里', '无限服里'),
    (r'(?:永恒|永恆)中', '无限服中'),
    (r'永久中', '无限服中'),
    (r'永久里', '无限服里'),
    # 裸「永恒/永恆」（负向保护「…之…」专名）
    (r'(?:永恒|永恆)(?!之)', '《无限》'),
    # 兜底：未翻译的 latin Forever
    (r'[Ff]orever', '《无限》'),
    # ★ 版本性杂词清理（放最后）：版本 token **相邻**的杂词一并归一，杜绝
    #   「《无限》怀旧服」「《魔兽世界：无限》资料片」这类「无限 + 杂词」怪搭配。
    #   与 assert_forever_alignment 的「相邻判据」互补：此层清输出，那层拦源头。
    (r'(《[^》]*无限》|无限测试服|无限版本|无限服|无限版)\s*(?:怀旧服|懷舊服|怀旧|懷舊)', '无限服'),
    (r'(《[^》]*无限》|无限测试服|无限版本|无限服|无限版)\s*(?:资料片|資料片|经典赛季|經典賽季|永驻|永駐|永燃|永夜|永昼)', r'\1'),
]
_TERM_REGEX = [(re.compile(rx), rep) for rx, rep in _TERM_REGEX]

# 空白规整：版本名前后不留半角空格（相邻非空格为 CJK 或 CJK 标点时）。
_TERM_TOKENS = r'(?:《魔兽世界：无限》|无限测试服|无限版本|无限服|无限版|《无限》)'
_CJK_L = r'[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]'
_WS_LEFT = re.compile(r'(?<=' + _CJK_L + r')[ \t]+(?=' + _TERM_TOKENS + r')')
_WS_RIGHT = re.compile(r'(' + _TERM_TOKENS + r')[ \t]+(?=' + _CJK_L + r')')

# 首个版本名 token（供「每篇 flow 首次出现 → 全称」升级用，长形在前）。
_PROMO_TOKEN = re.compile(r'(?:《魔兽世界：无限》|无限测试服|无限版本|无限服|无限版|《无限》)')


def normalize_terms(text):
    """对单条中文文本做版本名归一（含空白规整；幂等）。"""
    if not isinstance(text, str) or not text:
        return text
    for lit in TERM_TITLE_LITERALS:
        if lit in text:
            text = text.replace(lit, CANON_TITLE)
    for old, new in TERM_PHRASE_LITERALS:
        if old in text:
            text = text.replace(old, new)
    for rx, rep in _TERM_REGEX:
        text = rx.sub(rep, text)
    text = _WS_LEFT.sub('', text)
    text = _WS_RIGHT.sub(r'\1', text)
    return text


def _promote_first(text, state):
    """把 flow 内**首次**出现的版本名升级为全称《魔兽世界：无限》（幂等；跳过规范标题短语）。"""
    if state['done'] or not isinstance(text, str) or not text:
        return text
    masked = text.replace(CANON_TITLE, '\x00' * len(CANON_TITLE))  # 保护标题里的「无限服」
    m = _PROMO_TOKEN.search(masked)
    if not m:
        return text
    if m.group(0) == FULL_NAME:
        state['done'] = True
        return text
    state['done'] = True
    return text[:m.start()] + FULL_NAME + text[m.end():]


def _promote_element(f, state):
    """按元素类型顺序访问其文本串，做首次版本名升级（races 结构化字段无版本名，跳过）。"""
    t, v = f['t'], f['v']
    if t in ('p', 'h4'):
        f['v'] = _promote_first(v, state)
    elif t == 'tb':
        for row in v:
            cells = row['cells'] if isinstance(row, dict) else row
            for i in range(len(cells)):
                cells[i] = _promote_first(cells[i], state)
                if state['done']:
                    return
    elif t == 'ul':
        for it in v:
            it['text'] = _promote_first(it['text'], state)
            if state['done']:
                return
    elif t in ('good', 'bad'):
        for i in range(len(v)):
            v[i] = _promote_first(v[i], state)
            if state['done']:
                return


def normalize_flow_terms(flow):
    """对最终 flow 做版本名归一：① 逐串形态归一 + 空白规整；② flow 首次出现升级为全称。"""
    out = []
    for f in flow:
        t, v = f['t'], f['v']
        if t in ('p', 'h4'):
            nv = normalize_terms(v)
        elif t == 'tb':
            nv = [[normalize_terms(c) for c in
                   (row['cells'] if isinstance(row, dict) else row)] for row in v]
        elif t == 'ul':
            nv = []
            for it in v:
                rec = {'text': normalize_terms(it['text'])}
                if it.get('term'):
                    rec['term'] = it['term']
                nv.append(rec)
        elif t in ('good', 'bad'):
            nv = [normalize_terms(x) for x in v]
        else:
            nv = v
        out.append({'t': t, 'v': nv})
    state = {'done': False}
    for f in out:
        _promote_element(f, state)
        if state['done']:
            break
    return out


def is_junk_element(f):
    """p/h4 的值归一化后为空串或属解析垃圾字面量 → 丢弃（严格等值，避免误伤正文）。"""
    if f.get('t') not in ('p', 'h4'):
        return False
    v = f.get('v')
    if not isinstance(v, str):
        return False
    nv = v.strip().lower()
    return nv == '' or nv in JUNK_VALS


def drop_junk(flow):
    """在最终 flow（merge 之后）上剔除解析垃圾元素与空标题/空段落。

    ★ 必须在 merge_flow 之后做：en/cn 两侧都带同位的垃圾元素，若在 merge 前删会打乱
    merge_flow 的按序对齐（索引位移）。放在最终 flow 上则 zhCN/enUS 一次覆盖。
    """
    return [f for f in flow if not is_junk_element(f)]


def clean_text(s):
    for ch in STRIP:
        s = s.replace(ch, '')
    return s


def luatext(s):
    for ch in STRIP:
        s = s.replace(ch, '')
    s = s.replace('\\', '\\\\').replace('"', '\\"')   # 先转义原始反斜杠
    s = s.replace('\x05', '\\n')                       # 再插入换行转义（避免被二次转义）
    return s


def classify_col(hdr):
    """按 sw 表「列头」判定 good/bad；无法识别（含空列头）返回 None，该列跳过。"""
    if not hdr:
        return None
    hl = str(hdr).strip().lower()
    if not hl:
        return None
    if WEAK_RE.search(hl):
        return 'bad'
    if GOOD_RE.search(hl):
        return 'good'
    return None


def is_group_header(text):
    """races 板块里「恰为/以阵营词开头」的短段落 = 分组标题（严格匹配，避免误伤长句）。"""
    norm = ' '.join(clean_text(text).split())
    if not norm:
        return False
    low = norm.lower()
    if low in FACTION_EXACT:
        return True
    for lab in FACTION_PREFIX:
        if low.startswith(lab):
            if len(norm) > 30:
                return False
            rest = norm[len(lab):]
            if rest and not any(ch in SENT_PUNCT for ch in rest):
                return True
    return False


def postprocess_headers(flow, sec_key):
    """races 板块里的阵营分组标题：p → h4。★ 必须在 merge_flow 之后调用（对齐按 t）。"""
    if sec_key != 'races':
        return flow
    out = []
    for f in flow:
        if f['t'] == 'p' and is_group_header(f['v']):
            out.append({'t': 'h4', 'v': f['v']})
        else:
            out.append(f)
    return out


def normalize_flow(flow, sec_key):
    """tb: dict→cells；多行表丢表头首行（单行表无表头，整行即内容，保留）。
    sw: 表/列表 → good/bad 条目组。"""
    out = []
    good, bad = [], []
    for f in flow:
        if f['t'] == 'tb':
            all_rows = [row['cells'] if isinstance(row, dict) else row for row in f['v']]
            # ★ 多行表：首行 = 表头 → 丢弃；单行表：无表头 → 保留整行（否则整段内容被吞）。
            #   2026-09-29 修：曾一律丢首行，导致 4 个单行表被静默吞掉
            #   （paladin_protection/systems 的 Pro/Con、warrior_protection/changes 的 3 条要点）。
            rows = all_rows[1:] if len(all_rows) > 1 else all_rows
            if not rows:
                continue
            if sec_key == 'sw':
                # sw 表多为「优势 | 空 | 缺点」三列：必须逐列读各自表头决定归属，
                # 否则缺点列会被误并进 good（全体渲染成绿色加号）。
                header = all_rows[0] if all_rows else []
                for cells in rows:
                    for ci in range(min(len(header), len(cells))):
                        cls = classify_col(header[ci])
                        if cls is None:
                            continue
                        dst = good if cls == 'good' else bad
                        for part in str(cells[ci]).split('\x05'):
                            part = part.strip()
                            if part:
                                dst.append(part)
            else:
                out.append({'t': 'tb', 'v': rows})
        elif f['t'] == 'ul' and sec_key == 'sw':
            for item in f['v']:
                if item.get('icon') == 'plus':
                    good.append(item['text'])
                elif item.get('icon') == 'minus':
                    bad.append(item['text'])
                else:
                    out.append({'t': 'ul', 'v': [item]})
        else:
            out.append(dict(f))
    if sec_key == 'sw':
        if good:
            out.append({'t': 'good', 'v': good})
        if bad:
            out.append({'t': 'bad', 'v': bad})
    return out


def resync_sw_cn(en_flow, cn_flow, key):
    """sw 板块译文常把 good+bad 混装进单个 good 元素；按 en 条数还原为分列结构。

    译文条目与英文一一对应且顺序一致（前 n_good 条 = 优势，后 n_bad 条 = 缺点）。
    若条数不符（漏译/增译），回落英文并打印警告——错位比不修更糟。
    """
    n_good = sum(len(f['v']) for f in en_flow if f['t'] == 'good')
    n_bad = sum(len(f['v']) for f in en_flow if f['t'] == 'bad')
    cn_goods = [f for f in cn_flow if f.get('t') == 'good']
    cn_bads = [f for f in cn_flow if f.get('t') == 'bad']
    # 译文侧已正确分列：原样使用。
    if cn_bads and sum(len(f['v']) for f in cn_goods) == n_good \
            and sum(len(f['v']) for f in cn_bads) == n_bad:
        return cn_flow
    # 单个 good 元素混装：按 en 条数切分为 good/bad。
    if len(cn_goods) == 1 and not cn_bads:
        arr = list(cn_goods[0].get('v', []))
        if len(arr) == n_good + n_bad:
            out = []
            for f in cn_flow:
                if f.get('t') == 'good':
                    out.append({'t': 'good', 'v': arr[:n_good]})
                    if n_bad:
                        out.append({'t': 'bad', 'v': arr[n_good:]})
                else:
                    out.append(dict(f))
            return out
        print('WARN sw 译文条数不匹配 %s: cn=%d en_good=%d en_bad=%d → 回落英文'
              % (key, len(arr), n_good, n_bad))
        return [dict(f) for f in cn_flow if f.get('t') not in ('good', 'bad')]
    return cn_flow


def merge_flow(en_flow, cn_flow):
    """按序对齐覆盖：t 必须一致（en 已 normalize，tb 无表头）。"""
    out = []
    for i, en in enumerate(en_flow):
        cn = cn_flow[i] if i < len(cn_flow) else None
        t = en['t']
        if cn is None or cn.get('t') != t:
            v = en.get('v')
        elif t in ('good', 'bad', 'races'):
            v = cn['v']
        elif t == 'tb':
            v = [[luatext(c) for c in row] for row in cn['v']]
        elif t == 'ul':
            v = []
            for j, item in enumerate(en['v']):
                ci = cn['v'][j] if j < len(cn['v']) else None
                rec = {'text': ci['text'] if ci else item['text']}
                term = (ci or item).get('term') or item.get('term')
                if term:
                    rec['term'] = term
                v.append(rec)
        else:
            v = cn.get('v')
        out.append({'t': t, 'v': v})
    return out


def lua_str(s):
    return '"%s"' % s


ENUS_GUARD_LINES = [
    '-- DungeonsForever · English (enUS) data overlay — Data_ClassGuide',
    '-- Loads on the enUS client only; other locales exit immediately.',
    '',
    "if (type(GetLocale) ~= \"function\") or GetLocale() ~= \"enUS\" then return end",
]


def build_lines(data, use_trans, enus_guard=False):
    lines = []
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    # ★ enUS 守卫放在**头部注释块之内**（而非文件最前），使整个头部成为「文件头注释块」——
    #   对任何去注释（strip_comments）都幂等；否则守卫代码会把头块截断，导致下半头块被剥。
    if enus_guard:
        lines.append('')
        lines.extend(ENUS_GUARD_LINES)
    lines.append('')
    lines.append('local _, ns = ...')
    lines.append('')
    lines.append('ns.EnsureClassGuide = function()')
    lines.append('if ns.ClassGuide then return ns.ClassGuide end')
    lines.append('ns.ClassGuide = {')
    lines.append('    meta = {')
    lines.append('        patch = "1.60.1",')
    lines.append('        level = 30,')
    lines.append('        updated = "%s",' % max_updated(data))
    lines.append('    },')
    lines.append('')
    lines.append('    specs = {')
    cur_cls = None
    for key in KEYS:
        rec = data.get(key)
        if not rec:
            continue
        cls, _, slug = key.partition('_')
        spec = SPEC_OF[slug]
        cn = load_trans(key) if use_trans else None
        if cls != cur_cls:
            if cur_cls is not None:
                lines.append('        },')
            lines.append('        %s = {' % CLASS_OF[cls])
            cur_cls = cls
        lines.append('            %s = {' % spec)
        lines.append('                updated = "%s",' % ((cn or {}).get('updated') or rec['updated']))
        lines.append('                sections = {')
        for sec in rec['sections']:
            flow = normalize_flow(sec['flow'], sec['key'])
            if cn:
                cn_sec = find_cn_sec(cn, sec['key'])
                if cn_sec:
                    cn_flow = cn_sec.get('flow', [])
                    if sec['key'] == 'sw':
                        cn_flow = resync_sw_cn(flow, cn_flow, key)
                    flow = merge_flow(flow, cn_flow)
            # ★ races 分组标题必须在 merge 之后改 t（merge 按 t 对齐，改早了会回落英文）
            flow = postprocess_headers(flow, sec['key'])
            # ★ 解析垃圾（h4="false" 等）/空标题空段落，在 merge 之后的最终 flow 上剔除
            flow = drop_junk(flow)
            # ★ 版本名术语兜底归一（仅中文侧）：重跑幂等，未来新译文再犯自动纠正
            if use_trans:
                flow = normalize_flow_terms(flow)
            lines.append('                    { key = "%s", flow = {' % sec['key'])
            for f in flow:
                lines.append('                        %s' % flow_lua(f))
            lines.append('                    } },')
        lines.append('                },')
        lines.append('            },')
    if cur_cls is not None:
        lines.append('        },')
    lines.append('    },')
    lines.append('}')
    lines.append('return ns.ClassGuide')
    lines.append('end')
    lines.append('')
    return '\n'.join(lines)


def gen():
    data = json.load(io.open(SRC, encoding='utf-8'))
    zh = build_lines(data, True)
    en = build_lines(data, False, True)
    # ★ 英文锚强校验：merge 之后、写盘之前。失败非零退出（绝不静默 pass）。
    assert_forever_alignment(data)
    outs = [(DST, zh), (os.path.join(os.path.dirname(HERE), 'Core', 'Data', 'enUS', 'Data_ClassGuide.lua'), en)]
    for path, body in outs:
        for w in LEAK:
            if w in body:
                raise SystemExit('LEAK word in output: %s' % w)
        if '\x03' in body or '\x05' in body or '|l|' in body:
            raise SystemExit('control char leaked in output')
        io.open(path, 'w', encoding='utf-8', newline='\n').write(body)
        print('->', path, len(body), 'bytes')


def max_updated(data):
    best = ''
    for _, rec in data.items():
        u = rec.get('updated') or ''
        if u > best:
            best = u
    return best


def load_trans(key):
    p = os.path.join(TRANS, key + '.json')
    if os.path.exists(p):
        return json.load(io.open(p, encoding='utf-8'))
    return None


# ---------------------------------------------------------------------------
# 英文锚强校验（根治「以中文变体为锚必然漏网」）
#   判据：英文 flow 元素全文含**大写 `Forever`** 者，中文对应元素（section 按 key 配对，
#        与 find_cn_sec 同口径；flow 元素按索引配对）必须含「无限」。
#   ★ 大小写判据（2026-09-29 全 27 页统计核实，无反例）：
#       版本名一律大写 `Forever`（152 处，如 In Forever / WoW Forever /
#       World of Warcraft: Forever / ...Available for Forever）；
#       副词一律小写 `forever`（3 处，全部是 warlock_*/races 的
#       "you'll be looking at it forever"）。
#     故只认大写，避免把副词误当版本名（曾因此逼出 3 处不忠实增译）。
#   ★ 配对 MUST 按 section key（绝不能按索引——如 mage_fire 中英 section 顺序不同）；
#     flow 元素按索引配对（merge_flow 亦按索引，二者一致）。
#   ★ 元素全文覆盖 p/h4 的 v、tb 的 cells（en 是 {cells:[...]}、cn 是 [[...]]，两形态都吃）、
#     ul 的 term/text、good/bad 的数组。
#   白名单：sections[].title（界面板块名走 TT.SEC_TITLE 硬编码，不进界面）。
#   只在中文侧跑（enUS 是英文原文，不参与）；失败 → 收集全部违规、打印完整清单、非零退出。
#   放在 merge 之后、写盘之前（见 gen）。
# ---------------------------------------------------------------------------
_FOREVER_RE = re.compile(r'Forever')

# ★ 收紧后的第二判据（版本 token + 版本性杂词「相邻」= 违规）：
#   英文含 Forever 的条目，其中文对应元素除须含「无限」外，**还不得出现
#   「版本 token 紧邻版本性杂词」的怪搭配** —— 如「《无限》怀旧服」
#   「《魔兽世界：无限》资料片」。旧锚只看「含不含无限」，对「无限 + 杂词」
#   并存直接放行（QA 抓到 3 处盲区），此判据补上该盲区。
#   ★ 只在**相邻**（中间仅允许空白）时判违规，放过合法语境：如
#     priest_discipline 的「后续资料片」——那是真在讲后续资料片，未与版本 token 相邻。
#   ★ 「永恒/永恆」加 (?!之) 负向保护（永恒之井等专名）。
_VER_TOK = r'(?:《魔兽世界：无限》|《无限》|无限测试服|无限版本|无限服|无限版)'
_WORDY = (r'(?:怀旧服|懷舊服|怀旧|懷舊|资料片|資料片|永驻|永駐|永燃|永夜|永昼'
          r'|永[恒恆](?!之)|永久|经典赛季|經典賽季|永远的魔兽世界|[Ff]orefore)')
_VER_WORDY_RE = re.compile(
    r'(?:' + _VER_TOK + r'\s*' + _WORDY + r'|' + _WORDY + r'\s*' + _VER_TOK + r')')


def _flat_texts(o, acc):
    """递归收集元素内所有可上屏文本；跳过结构键 title/t/key。"""
    if isinstance(o, str):
        acc.append(o)
    elif isinstance(o, list):
        for x in o:
            _flat_texts(x, acc)
    elif isinstance(o, dict):
        for k, v in o.items():
            if k in ('title', 't', 'key'):
                continue
            _flat_texts(v, acc)
    return acc


def _element_text(el):
    """把单个 flow 元素（en/cn 两形态）摊平成全文串（不含结构键）。"""
    if not isinstance(el, dict):
        return ''
    return ''.join(_flat_texts({k: v for k, v in el.items() if k != 't'}, []))


def assert_forever_alignment(data):
    """英文锚强校验（双判据）：凡英文含 Forever 的条目，中文必须含「无限」，
    且**不得**出现「版本 token 相邻版本性杂词」的怪搭配（如「《无限》怀旧服」）。

    违规（中文缺「无限」/ 译文整段缺失 / 对应 section 整段缺失 / 无限+杂词）→
    打印完整清单并非零退出。绝不允许静默 pass。
    """
    violations = []   # (spec, key, idx, t, en_text, cn_text_or_None, matched_wordy_or_None)
    for spec in sorted(data):
        tr = load_trans(spec)
        tmap = {s.get('key'): s for s in ((tr or {}).get('sections') or [])}
        for sec in data[spec].get('sections', []):
            key = sec.get('key')
            tsec = tmap.get(key)
            ef = sec.get('flow', []) or []
            cf = (tsec or {}).get('flow', []) or []
            for i, e in enumerate(ef):
                en_text = _element_text(e)
                if not _FOREVER_RE.search(en_text):
                    continue
                cn_text = _element_text(cf[i]) if i < len(cf) else None
                if cn_text is None or '无限' not in cn_text:
                    violations.append((spec, key, i, e.get('t'), en_text, cn_text, None))
                    continue
                m = _VER_WORDY_RE.search(cn_text)
                if m:
                    violations.append((spec, key, i, e.get('t'), en_text, cn_text,
                                       m.group(0)))
    if violations:
        print('')
        print('=' * 78)
        print('★ FOREVER 英文锚校验失败：英文含 Forever 的条目，中文不合规（%d 处）'
              % len(violations))
        print('  规则：en 元素含大写 Forever ⇒ 对应 cn 元素（section 按 key、flow 按索引配对）'
              '必须含「无限」，且不得出现「版本 token 相邻版本性杂词」的怪搭配。')
        print('=' * 78)
        for n, (spec, key, i, t, en_text, cn_text, wordy) in enumerate(violations, 1):
            kind = ('缺「无限」' if wordy is None else '无限+杂词「%s」' % wordy)
            print('%2d. [%s / %s #%d t=%s]  %s' % (n, spec, key, i, t, kind))
            print('    EN: %s' % en_text[:180].replace('\n', '\\n'))
            print('    CN: %s' % (cn_text[:180].replace('\n', '\\n')
                                  if cn_text is not None else '<缺失>'))
            print('    >>> 修正：改 _temp/_cg_trans/%s.json 的 section[%s].flow[%d]'
                  % (spec, key, i))
        raise SystemExit('FOREVER 英文锚校验失败：%d 处不合规' % len(violations))
    print('★ FOREVER 英文锚校验通过：英文含 Forever 的条目，中文均含「无限」且无「无限+杂词」。')


def find_cn_sec(cn, key):
    for s in cn.get('sections', []):
        if s.get('key') == key:
            return s
    return None


def flow_lua(f):
    t = f['t']
    if t == 'p' or t == 'h4':
        return '{ t = "p", v = %s },' % lua_str(luatext(f['v'])) if t == 'p' \
            else '{ t = "h4", v = %s },' % lua_str(luatext(f['v']))
    if t == 'tb':
        rows = []
        for row in f['v']:
            cells = row['cells'] if isinstance(row, dict) else row
            rows.append('{ %s }' % ', '.join('"%s"' % luatext(c) for c in cells))
        return '{ t = "tb", v = { %s } },' % ', '.join(rows)
    if t == 'ul':
        items = []
        for it in f['v']:
            term = it.get('term')
            if term:
                items.append('{ term = "%s", text = "%s" }' % (luatext(term), luatext(it['text'])))
            else:
                items.append('{ text = "%s" }' % luatext(it['text']))
        return '{ t = "ul", v = { %s } },' % ', '.join(items)
    if t in ('good', 'bad'):
        items = ', '.join('"%s"' % luatext(x) for x in f['v'])
        return '{ t = "%s", v = { %s } },' % (t, items)
    if t == 'races':
        items = ['{ race = "%s", side = "%s", mark = "%s" }' % (r['race'], r['side'], r['mark'])
                 for r in f['v']]
        return '{ t = "races", v = { %s } },' % ', '.join(items)
    raise SystemExit('unknown flow type: %r' % t)


if __name__ == '__main__':
    gen()
