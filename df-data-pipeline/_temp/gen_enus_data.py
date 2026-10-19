# -*- coding: utf-8 -*-
"""生成 Core/Data/enUS/Data_*.lua（数据层英文覆盖副本，2026-09-25）。

与 gen_zhtw_data.py 同机制：
- 11 个 Data_*.lua 原文件零改动（上游生成器重跑不受影响）；
- 产出 Core/Data/enUS/ 副本，头部 enUS 语言守卫（其他客户端秒退），
  toc 排在原数据之后覆盖加载；
- 翻译管线：EXACT 精确表 → RULES 正则规则 → ZONES/DUNGEONS/BOSSES/TOKENS 共用表
  → GLOSS 段级替换。四表同源（enus_data.py），跨文件对查键自动一致。
- 未命中的字符串保留简体原文（设计如此：物品/任务/NPC 兜底名会被客户端
  英文真名替换，enUS 客户端基本看不到；真露面的纯文案已尽数收录）。
- 幂等：重跑只产出同一份内容。

用法：python gen_enus_data.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import enus_data as D1
import enus_data_prof
import enus_data_quests as DQ1
import enus_data_quests2 as DQ2
import enus_data_names as DN
import enus_data_names2 as DN2
import enus_data_names3 as DN3
import enus_data_names_hand as DH
import enus_data_prose as DP
import enus_data_resid as DR
import enus_data_whguide as DW
import enus_data_onyxia as DOX
import enus_data_guide19 as DG19
import enus_data_tier as DT
import enus_data_toys as DTY
import enus_data_banner as DBAN
import enus_data_raidsets as DRS

EXACT = dict(D1.EXACT)
EXACT.update(enus_data_prof.PROF)
EXACT.update(D1.ZONES)
EXACT.update(D1.DUNGEONS)
EXACT.update(D1.BOSSES)
EXACT.update(D1.TOKENS)
# wowhead 官方名（任务名 + NPC 名）。同一中文名既是任务标题又是 NPC 名时，
# NPC 名优先：任务标题运行时走客户端 GetTitleForQuestID（数据标题只是兜底），
# 起始 NPC 名 q[17] 是直接上屏的，映射错会整列显示成任务名。
EXACT.update(DN.Q)
EXACT.update(DN.N)
# 补抓批次（fetch2/3/4/5/6）：classic-cn/NFU 对齐的官方名
EXACT.update(DN2.Q)
EXACT.update(DN2.N)
EXACT.update(DN3.H)
# 手翻自由文本（整句/整段）
EXACT.update(DQ1.QUESTS)
EXACT.update(DQ2.QUESTS2)
# 人工拍板层，最高优先
EXACT.update(DH.HAND)
# 纯文本备注散文层（人工翻译整句，键=数据原文，最高优先）
EXACT.update(DP.FREE)
# 残余收口层（附魔/类目/专精等，先于手翻层并入）
EXACT.update(DR.RESID)
# wowhead 首领攻略全文（zhCN → 英文原文，最高优先整段替换）
EXACT.update(DW.FREE)
EXACT.update(DOX.FREE)
EXACT.update(DG19.FREE)
EXACT.update(DTY.TOYS)
EXACT.update(DBAN.BANNER)
# ★ EXTRA_RULES 必须排在 D1.RULES 之前：D1 有一条宽字符类规则会截胡
#   「火焰伤害 +20」这类串并原样返回，导致精确规则永远轮不到
RULES = DR.EXTRA_RULES + D1.RULES
GLOSS = D1.GLOSS

# 按文件覆盖的精确表（同一中文名在不同数据文件里语义不同才需要；全局歧义禁入）。
# 「东部王国」：NPCLoc 里是区域名（Eastern Kingdoms，走全局 ZONES），
# DungeonQuests 里是任务 4003 的标题兜底（wowhead 官方 The Royal Rescue）。
FILE_SPECIFIC = {
    'Data_DungeonQuests.lua': dict(DQ1.FILE_EXACT),
    'Data_ClassTier.lua': dict(DT.TIER),
    # Data_BIS 方案页专精标签（preset 行「天赋」段）。★ 必须走文件级表：「武器」「元素」
    # 「神圣」等键在全局层另有语义（配方类别 Weapon / 附魔法术学派），全局覆盖会污染
    # 那些数据；复盘见 2026-10-16 日志。
    'Data_BIS.lua': {
        '武器': 'Arms', '狂暴': 'Fury', '防战': 'Protection', '防护': 'Protection',
        '神圣': 'Holy', '神圣震击': 'Shockadin', '惩戒': 'Retribution',
        '射击': 'Marksmanship', '生存': 'Survival',
        '奇袭': 'Assassination', '战斗': 'Combat', '敏锐': 'Subtlety',
        '戒律': 'Discipline', '神牧': 'Holy', '暗牧': 'Shadow',
        '奥法': 'Arcane', '火法': 'Fire', '冰法': 'Frost', '痛苦': 'Affliction',
        '鸟德': 'Balance', '猫德': 'Feral', '熊德': 'Feral', '奶德': 'Restoration',
        '元素': 'Elemental', '增强': 'Enhancement', '奶萨': 'Restoration',
    },
    # Data_MapPins 稀有怪名（wowhead 官方英文名；Bruegal Ironknuckle 本就是 ASCII 直过）
    'Data_MapPins.lua': {
        '黑铁大使': 'Dark Iron Ambassador',
        '死亡之誓': 'Deathsworn Captain',
        '矿工约翰森': 'Miner Johnson',
    },
    # Data_RaidSets 团本套装名 + 批次标签（2026-10-07 加；只补 9 套专属批的英文名）
    'Data_RaidSets.lua': dict(DRS.RS),
}
CUR_FILE = None

# ★ 不由本生成器产出的基数据文件（enUS 侧另有权威来源 / 手写占位）——第七轮收口：
#   · Data_ClassGuide.lua：权威作者 = _temp/fc_guide.py（英文正文由解析层直出，非本生成器机翻）；
#   · Data_LootFilter.lua：归 LootFilter 流程 / 手写占位，不由本生成器产出。
#   两者既不写盘、也不参与收尾注释精简，避免用「半机翻覆盖层」冲掉它们的权威内容 / 手写占位。
ENUS_EXCLUDE = {'Data_ClassGuide.lua', 'Data_LootFilter.lua', 'Data_Gear.lua', 'Data_ClassCombat.lua'}

SRC_DIR = os.path.join(os.path.dirname(HERE), 'Core', 'Data')
DST_DIR = os.path.join(SRC_DIR, 'enUS')

HEAD = '''local _, ns = ...

if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end
'''


def translate(s):
    fx = FILE_SPECIFIC.get(CUR_FILE)
    if fx and s in fx:
        return fx[s]
    if s in EXACT:
        return EXACT[s]
    # 斜杠分隔 NPC 名单（QuestPreNpcID 节点）：逐段查表，全中才翻（避免半翻）
    if ' / ' in s:
        parts = s.split(' / ')
        if all(p in EXACT for p in parts):
            return ' / '.join(EXACT[p] for p in parts)
    for pat, fn in RULES:
        m = pat.match(s)
        if m:
            return fn(m)
    # GLOSS 段级替换（合成标签；全部命中才算转成功，避免半翻）
    parts = []
    rest = s
    while rest:
        for g in sorted(GLOSS, key=len, reverse=True):
            if rest.startswith(g):
                parts.append(GLOSS[g])
                rest = rest[len(g):]
                break
        else:
            return s          # 有未收录片段 → 保持原文
    out = ''.join(parts)
    # 空格清理（中文接段无空格，英文段间要一个空格）
    out = re.sub(r'(?<=\S) (?=\S)', ' ', out)
    return out


def transform(src):
    """字符级扫描：只改字符串字面量内部，注释与代码零接触（处理转义引号）。"""
    out = []
    i, n = 0, len(src)
    in_str = False
    changed = 0
    while i < n:
        c = src[i]
        if not in_str:
            if c == '"':
                in_str = True
                out.append(c)
            elif c == '-' and src[i:i + 2] == '--':   # 注释整段原样搬
                j = src.find('\n', i)
                j = n if j < 0 else j
                out.append(src[i:j])
                i = j
                continue
            else:
                out.append(c)
            i += 1
            continue
        # 字符串内部
        if c == '\\' and i + 1 < n:
            out.append(src[i:i + 2])
            i += 2
            continue
        if c == '"':
            in_str = False
            out.append(c)
            i += 1
            continue
        # 收集到串尾再整体翻译（保证精确表长键优先）
        j = i
        while j < n:
            if src[j] == '\\':
                j += 2
                continue
            if src[j] == '"':
                break
            j += 1
        seg = src[i:j]
        t = translate(seg)
        if t != seg:
            changed += 1
            # 翻译值里的裸双引号必须转义（表里允许直接写 "Lures"，落盘变 \"Lures\"）；
            # 源串自带的 \" 转义（如 \"Secre）不会被 translate 命中，原样保留。
            t = re.sub(r'(?<!\\)"', r'\\"', t)
        out.append(t)
        i = j
    return ''.join(out), changed


def main():
    os.makedirs(DST_DIR, exist_ok=True)
    total = 0
    written = 0
    for fn in sorted(os.listdir(SRC_DIR)):
        if not fn.endswith('.lua') or fn in ENUS_EXCLUDE:   # ★ 不由本生成器产出的，跳过
            continue
        src = io.open(os.path.join(SRC_DIR, fn), encoding='utf-8').read()
        global CUR_FILE
        CUR_FILE = fn
        body, changed = transform(src)
        head = HEAD.format(name=fn)
        dst = os.path.join(DST_DIR, fn)
        io.open(dst, 'w', encoding='utf-8', newline='\n').write(head + body)
        total += changed
        written += 1
        print('%-28s 转换 %4d 处' % (fn, changed))
    skip = sorted(f for f in os.listdir(SRC_DIR) if f in ENUS_EXCLUDE)
    if skip:
        print('跳过（不由本生成器产出）：%s' % '、'.join(skip))
    print('共 %d 个文件、%d 条字符串转为英文 → Core/Data/enUS/' % (written, total))




def _strip_comments_after_gen():
    """注释精简：**只清理本生成器写出的文件**（Core/Data/enUS/Data_*.lua）。

    ★ 2026-09-29 收口（第七轮）：旧实现无条件重扫整个 Core/，副作用有二：
      (1) 剥掉 Core/Data/enUS/Data_ClassGuide.lua 的头部表结构注释块 —— 该文件
          是 _temp/fc_guide.py 的产物（非本生成器所写），被外溢剥注释后会使
          「还原 enUS 头块」不幂等（再跑一次 gen 又被剥）；
      (2) 剥掉并行会话手改文件（LootFilterUI / MainFrame / Core / LootFilter 等）的注释。
      现限定为「本次实际生成的 enUS 数据副本」白名单：Core/Data/enUS/Data_*.lua，
      并显式排除 enUS/Data_ClassGuide.lua（归属 fc_guide.py），杜绝上述外溢。
      注释口径本身不变：每个 Lua 只留文件头注释块（逻辑仍在 _temp/strip_comments.py）。
    """
    import os as _os
    import sys as _sys
    _here = _os.path.dirname(_os.path.abspath(__file__))
    if _here not in _sys.path:
        _sys.path.insert(0, _here)
    import strip_comments as _S
    names = sorted(f for f in _os.listdir(DST_DIR)
                   if f.startswith('Data_') and f.endswith('.lua')
                   and f not in ENUS_EXCLUDE)   # ★ 排除非本生成器产物（ClassGuide / LootFilter）
    n = 0
    for _p in _S.walk([_os.path.join(DST_DIR, name) for name in names]):
        _raw = open(_p, 'rb').read()
        _txt = _raw.decode('utf-8')
        _new, _c, _t = _S.strip_all_text(_txt)
        if _new != _txt:
            open(_p, 'wb').write(_new.encode('utf-8'))
            n += 1
    if n:
        print('注释精简：收尾清理 %d 个文件（仅 enUS 数据副本）' % n)


if __name__ == '__main__':
    main()
    _strip_comments_after_gen()
