# -*- coding: utf-8 -*-
"""数据四件套同步进 无限副本手册：逐字节同步 + 来源注释清洗。

上游 `Core/Data/Data_Dungeon*.lua` 是**由生成器产出、会被重跑**的文件
（`_temp/gen_dungeon_quests.py` 等）。当初手工拷贝 → 上游一重跑，本插件的数据就**静默变旧**
（实测：上游 q[7] 英文残留 0 处，而本插件还留着 102 处英文前置名 + 38 处英文 NPC 名）。

本脚本做两件事：
  ① **逐字节同步**上游内容（只改第 2 行项目名注释）；
  ② **来源注释清洗**（用户 2026-09-23 定：数据来源只保留 wowhead）——
     · 头部注释块整体换成本插件自己的版本，删掉数据来源声明；
     · 删除具名第三方来源（外部站点 / AtlasQuest / GPLv2 / nfuwow / mangoszero）；
     · 删除各副本行尾的「· 其中 N 条来自 AtlasQuest」与「-- [AQ]」标记。
     wowhead 相关的说明按口径保留。

用法：
    python _temp/sync_data.py            # 同步并打印差异统计
    python _temp/sync_data.py --dry-run  # 只看差异，不写盘
"""
import difflib
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                                    # .../AddOns/DungeonsForever
ADDONS = os.path.dirname(ROOT)                                  # .../Interface/AddOns
SRC_DIR = os.path.join(ADDONS, 'TalentsForever', 'Core', 'Data')
DST_DIR = os.path.join(ROOT, 'Core', 'Data')

FILES = ['Data_Dungeons.lua', 'Data_DungeonLoot.lua',
         'Data_DungeonQuests.lua', 'Data_NPCLoc.lua']

OLD_HDR = '-- TalentsForever ·'
NEW_HDR = '-- 无限副本手册 ·'

DRY = '--dry-run' in sys.argv
EN = re.compile(r'[A-Za-z]{2,}')

# ── 退役闸（2026-09-25）────────────────────────────────────────────────────
# 上游 TalentsForever 已移除副本页与副本数据文件，数据源唯一化为本插件 Core/Data。
_missing = [f for f in FILES if not os.path.exists(os.path.join(SRC_DIR, f))]
if _missing:
    sys.stderr.write(
        'sync_data: 上游已无 %s（2026-09-25 上游副本页拆除）：本同步链退役，'
        '本插件 Core/Data 为唯一数据源，请直接改这里。\n' % ', '.join(_missing))
    sys.exit(1)

# ── 头部注释块（替换文件开头连续的 `--` 行）──────────────────────────────────
HEAD_DUNGEONS = ''

HEAD_LOOT = ''

HEAD_QUESTS = ''

HEAD_NPCLOC = ''

HEAD_BLOCKS = {
    'Data_Dungeons.lua': HEAD_DUNGEONS,
    'Data_DungeonLoot.lua': HEAD_LOOT,
    'Data_DungeonQuests.lua': HEAD_QUESTS,
    'Data_NPCLoc.lua': HEAD_NPCLOC,
}

# ── 暴风城（uiMapID 1453）坐标校正 ──────────────────────────────────────────
# 无限服客户端的暴风城地图按新生代边界重画过，而 g_mapperData 记的是经典边界口径 →
# 该图**全部**百分比坐标系统性偏移（不是个别 NPC 写错）。实测两点：5413 由 57.4,16.0
# 校正为 64.6,37.2；6579 由 55.4,12.4 校正为 62.6,34.1（与地图重画后的实机位置一致）。
# 校正值 = 巫妖王分支坐标库，且与 wowhead 同页 g_mapperData 的第二个 spawn 点集交叉吻合
# （18/19 双源确认，最大偏差 0.3）；233 组静止 NPC 拟合的边界变换独立复核，偏差 ≤ 0.8。
# 唯一无库值的 1748（伯瓦尔）取该变换的预测值 79.6,38.3，待实机复核。
NPCLOC_COORD_FIX = {
    332: (78.3, 70.7),     # 马迪亚斯·肖尔
    656: (70.3, 40.8),     # 维尔德·蓟草
    928: (48.4, 50.2),     # 格雷森·沙东布瑞克公爵
    1284: (50.3, 45.5),    # 大主教本尼迪塔斯
    1416: (59.7, 33.8),    # 格瑞曼德·艾尔默
    1646: (57.7, 47.9),    # 巴隆斯·阿历克斯顿
    1719: (51.5, 69.4),    # 典狱官塞尔沃特
    1721: (73.3, 55.5),    # 尼科瓦·拉斯克（巡逻，取出生点）
    1748: (79.6, 38.3),    # 伯瓦尔·弗塔根公爵（无库值 → 边界变换预测）
    2198: (56.4, 74.1),    # 公告员古德曼（巡逻，取出生点）
    2285: (76.9, 47.8),    # 雷明顿·瑞治维尔伯爵
    4984: (36.2, 67.6),    # 阿古斯·夜语
    5384: (69.5, 40.4),    # 布罗哈恩·铁桶
    5413: (64.6, 37.2),    # 弗伦·长须
    6171: (50.5, 47.5),    # 达索瑞恩·拉尔
    6579: (62.6, 34.1),    # 沉默的舒尼
    7917: (51.0, 48.4),    # 萨尔努修士
    12336: (52.6, 43.2),   # 克罗雷修士
    14450: (56.3, 54.0),   # 孤儿监护员奈丁加尔
    11026: (62.0, 30.4),   # 斯普莱特 <初级技师>（矮人区，wotlk 分支口径）
    1325: (78.2, 58.4),    # 贾斯伯·菲尔 <毒药商>（旧城区 SI:7，wotlk 分支口径）
}


def fix_npcloc(raw):
    """把 Data_NPCLoc.lua 里暴风城那张图的坐标换成新生代边界口径。

    锚点同时校验 uiMapID 与地图名，命中数不等于 1 立即中止 —— 上游若改了行格式，
    必须显式失败，绝不能静默改错行或静默不生效。
    """
    txt = raw.decode('utf-8')
    for nid in sorted(NPCLOC_COORD_FIX):
        x, y = NPCLOC_COORD_FIX[nid]
        rx = re.compile(r'(\[%d\] = \{ 1453, )[\d.]+(, )[\d.]+(, "暴风城" \})' % nid)
        txt, cnt = rx.subn(lambda m: '%s%s%s%s%s' % (m.group(1), x, m.group(2), y, m.group(3)), txt)
        if cnt != 1:
            raise SystemExit('Data_NPCLoc.lua 里 [%d] 的暴风城条目锚点命中 %d 次（期望 1），同步中止' % (nid, cnt))
    # 自检：该图条目集必须与修正表键集一一对应 —— 上游新增该图 NPC 时要显式补进来，
    # 否则新条目会带着旧边界口径静默混进产物（「改了一半」比不改正难查）。
    got = set(int(m) for m in re.findall(r'\[(\d+)\] = \{ 1453, ', txt))
    want = set(NPCLOC_COORD_FIX)
    if got != want:
        raise SystemExit('暴风城条目集与修正表不一致：多 %s / 缺 %s'
                         % (sorted(got - want) or '无', sorted(want - got) or '无'))
    return txt.encode('utf-8')


# ── 前导链备注（链上某些环其实非必需）────────────────────────────────────────
# 用户 2026-09-24 指名 2040：「给 2040 这个前导任务需要备注一下：不需要接 2041 就可以接」。
# 2040 的直连前置写的是 2041（诺恩给的引导任务），但那个环不做也能接 2040 —— 任务行
# 18 个位置上都放不下这类说明，故另开一张表，由界面渲染在「前导任务」区链节点**下方**。
# ⚠️ 上游没有这张表（是本插件特有的界面需求），必须由本脚本注入：数据文件是生成物，
#    手改会被下次同步覆盖；上游若哪天自己也加了同名表，下面的自检会显式中止。
# 键 = 本任务的 questID（**不是**前置环的 ID）；值 = 一句话说明。
QUEST_PRE_NOTE = {
    2040: '注：2041 不是必须，不接也能直接接这个任务。',
}


def add_quest_pre_notes(raw):
    """在 ns.DungeonQuestPreExtra 表之后追加 ns.DungeonQuestPreNote 表。

    锚点 = 表头行 + 该表自己的收尾 `}`（扫到列 0 的 `}` 为止），不依赖表内容，
    上游增删条目不会失效；找不到表头 / 收尾立即中止，绝不静默产出一份没有备注的数据
    （界面上表现为「那一行凭空消失」，离线断言拿表比自己比永远相等 → 只有实机看得出来）。
    """
    txt = raw.decode('utf-8')
    # ⚠️ 判据必须是**表定义**而不是名字：头部注释里本来就写着这张表的名字（HEAD_QUESTS）。
    if 'ns.DungeonQuestPreNote = {' in txt:
        raise SystemExit('数据里已存在 ns.DungeonQuestPreNote 表（上游已加同名表？），'
                         '请人工核对后再同步')
    nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl)
    try:
        i = lines.index('ns.DungeonQuestPreExtra = {')
    except ValueError:
        raise SystemExit('Data_DungeonQuests.lua 里找不到 ns.DungeonQuestPreExtra 表头，同步中止')
    j = None
    for k in range(i + 1, len(lines)):
        if lines[k] == '}':
            j = k
            break
    if j is None:
        raise SystemExit('ns.DungeonQuestPreExtra 表找不到收尾 `}`，同步中止')
    for qid, v in QUEST_PRE_NOTE.items():
        if '"' in v or '\\' in v or not v:
            raise SystemExit('前导链备注 [%d] 不能含引号 / 反斜杠，也不能为空：%r' % (qid, v))
    block = ['',
             '-- 前导链备注：链上某些环其实**非必需** —— 不做那个环也能接本任务。',
             '-- 值 = 一句话说明，界面渲染在「前导任务」区链节点下方；',
             '-- 键 = 本任务的 questID（**不是**前置环的 ID）。写了才渲染。',
             'ns.DungeonQuestPreNote = {']
    for qid in sorted(QUEST_PRE_NOTE):
        block.append('    [%d] = "%s",' % (qid, QUEST_PRE_NOTE[qid]))
    block.append('}')
    lines[j + 1:j + 1] = block
    return nl.join(lines).encode('utf-8')


# ── 死亡矿井「爆破」任务链（用户反馈补录）────────────────────────────────────
# 玩家反馈死亡矿井任务页缺任务：wowhead forever 的西部荒野 zone 页已收录 1.60.1 新增的
# 毒素调查链（测井 → 鱼人鳃 → 矿井状况 → 月溪镇谍报 → 爆炸物筹备 ×4 → 爆破死亡矿井 →
# 引爆收尾），但站点快照与上游生成器都还没收录 —— 手改数据文件会被下次同步冲掉，
# 故在同步时按行注入；上游哪天自己也收录了，下面的防重复守卫会显式中止提醒人工迁移。
# 口径：wowhead forever 任务页 infobox（Start/End/Difficulty，q10 = 可接等级、
# r1..r4 = 档 2..5，已与 166 / 5722 交叉校准）+ zone 列表 JSON（任务等级 / money）；
# 92747 / 92753 的 xp 取玩家实机截图（575 / 4050，站点旧值 580 / 1350 不采用）；
# 92819 站点只有旧值（680 / 500）而实机口径未知 → 只落声望，不落 xp / money。
DM_CHAIN_QUESTS = [
    '        { 92747, "A", 9, 16, "阿尔巴·晴月", "西部荒野 52.4,53", nil, false, {92745}, nil, "从月溪镇收集 8 份可疑的工业补给品。补给品箱不在镇上街头，在通往死亡矿井入口的建筑内，沿路下到洞穴中即可找到。", "毒素调查链的一环：几处矿井的样本都查过了，线索都指向月溪镇下方的死亡矿井。到月溪镇收集补给品，回阿尔巴·晴月处交任务后开启爆炸物筹备段。前导环「测井」的两个采样点：莫尔森农场 46.2,38.3、詹森农庄 56.7,18.7。", {{9,1}, {12,2}, {14,3}, {19,4}, {23,5}}, nil, nil, 253092, "阿尔巴·晴月", { xp = 575, money = 400, rep = { {72, 50, "暴风城"} } } },',
    '        { 92753, "A", 9, 18, "阿尔巴·晴月", "西部荒野 52.4,53", nil, false, {92752}, nil, "找到深藏于死亡矿井中的熔炉，在旁安放强效炸药；随后在死亡矿井出口与阿尔巴·晴月会合。", "本链的副本段：进本前炸药已由爆炸物筹备段（斯普莱特 → 贾斯伯·菲尔）备齐。安放炸药后从副本出口出来，到月溪镇后方的山丘与阿尔巴·晴月会合。", {{9,1}, {14,2}, {16,3}, {21,4}, {25,5}}, nil, nil, 253092, "阿尔巴·晴月", { xp = 4050, rep = { {72, 50, "暴风城"} } } },',
    '        { 92819, "A", 9, 18, "阿尔巴·晴月", "西部荒野 - 月溪镇后方山丘 38.6,83.2", "爆破死亡矿井", false, {92753}, nil, "使用遥控起爆器，引爆安放在熔炉旁的炸药。", "「爆破死亡矿井」的收尾环：与月溪镇后方山丘的阿尔巴·晴月会合后，使用起爆器收尾。", {{9,1}, {14,2}, {16,3}, {21,4}, {25,5}}, nil, nil, 253279, "阿尔巴·晴月", { rep = { {72, 50, "暴风城"} } } },',
]

# 表外环（wowhead 线性系列：92742 → 92744 → 92745 → 92747 → 92748 → 92749 → 92750
# → 92751 → 92752 → 92753）。npc = 任务页 Start 字段（接任务的人，非交任务的人）；
# lv = infobox q10。92752 的 Start 是斯普莱特（交回阿尔巴·晴月），别按直觉写成晴月。
DM_CHAIN_PRE_EXTRA = [
    '    [92742] = { npc = "阿尔巴·晴月", lv = 9 },',
    '    [92744] = { 92742, npc = "阿尔巴·晴月", lv = 9 },',
    '    [92745] = { 92744, npc = "阿尔巴·晴月", lv = 9 },',
    '    [92748] = { 92747, npc = "阿尔巴·晴月", lv = 9 },',
    '    [92749] = { 92748, npc = "斯普莱特", lv = 9 },',
    '    [92750] = { 92749, npc = "斯普莱特", lv = 9 },',
    '    [92751] = { 92750, npc = "贾斯伯·菲尔", lv = 9 },',
    '    [92752] = { 92751, npc = "斯普莱特", lv = 9 },',
]

# 前导链节点反查起始 NPCID（点击开图用）。92742/92744/92745/92748 = 阿尔巴·晴月(253092)；
# 92749/92750 = 斯普莱特(11026)；92751 = 贾斯伯·菲尔(1325)；92752 = 斯普莱特(11026)。
DM_CHAIN_PRE_NPCID = [
    (92742, 253092), (92744, 253092), (92745, 253092), (92748, 253092),
    (92749, 11026), (92750, 11026), (92751, 1325), (92752, 11026),
]

# NPC 坐标（wowhead forever/cn NPC 页 g_mapperData 第一条；暴风城两键已是新生代边界
# 口径 —— wotlk 分支取数，与 NPCLOC_COORD_FIX 同一套校正，fix_npcloc 会再核一遍）。
DM_CHAIN_NPLOC = [
    '    [253092] = { 1436, 52.4, 53.0, "西部荒野" },   -- 阿尔巴·晴月',
    '    [253279] = { 1436, 38.6, 83.2, "西部荒野" },   -- 阿尔巴·晴月（月溪镇后方山丘）',
    '    [11026] = { 1453, 62.0, 30.4, "暴风城" },   -- 斯普莱特 <初级技师>',
    '    [1325] = { 1453, 78.2, 58.4, "暴风城" },   -- 贾斯伯·菲尔 <毒药商>',
]

DM_KEYS = {92742, 92744, 92745, 92747, 92748, 92749, 92750, 92751, 92752, 92753, 92819}


def _inject_before_block_end(lines, anchor, err_what):
    """在 anchor 行（必须唯一）所在块内、缩进收尾行之前插入。返回插入下标。

    块收尾 = anchor 之后第一条列 0 的 `}`（ns.NPCLoc / PreExtra / QuestPreNpcID 同构）。
    """
    hits = [k for k, ln in enumerate(lines) if ln.startswith(anchor)]
    if len(hits) != 1:
        raise SystemExit('%s锚点命中 %d 次（期望 1），同步中止' % (err_what, len(hits)))
    i = hits[0]
    for k in range(i + 1, len(lines)):
        if lines[k] == '}':
            return k
    raise SystemExit('%s找不到收尾 `}`，同步中止' % err_what)


def inject_dm_chain(raw):
    """把死亡矿井「爆破」链写进 Data_DungeonQuests.lua（任务行 + 表外环 + NPCID 反查）。"""
    txt = raw.decode('utf-8')
    found = sorted(DM_KEYS & set(int(m) for m in re.findall(r'\{ (\d{5}), "', txt)))
    if found:
        raise SystemExit('数据里已收录本链任务 %s（生成器口径已更新？），'
                         '请把 DM_CHAIN_* 迁去生成器后移除本注入步' % found)
    nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl)

    # ① 任务行：插进死亡矿井块顶部（可接等级 9，排在现有 14 级行之前）。
    hits = [k for k, ln in enumerate(lines) if ln.startswith('    ["the_deadmines"] = {')]
    if len(hits) != 1:
        raise SystemExit('死亡矿井块头锚点命中 %d 次（期望 1），同步中止' % len(hits))
    lines[hits[0] + 1:hits[0] + 1] = \
        ['        -- 死亡矿井「爆破」任务链（数据来源：wowhead）'] + DM_CHAIN_QUESTS

    # ② 表外环：PreExtra 收尾前插入。
    j = _inject_before_block_end(lines, 'ns.DungeonQuestPreExtra = {', 'PreExtra 表')
    lines[j:j] = ['    -- 死亡矿井「爆破」链的表外环（数据来源：wowhead）'] + DM_CHAIN_PRE_EXTRA

    return nl.join(lines).encode('utf-8')


def inject_dm_nploc(raw):
    """Data_NPCLoc.lua 侧注入：链上 4 个 NPC 的坐标 + 表外链起始 NPCID 反查表。"""
    txt = raw.decode('utf-8')
    found = sorted(int(m) for m in re.findall(r'\[(253092|253279|11026|1325)\] = \{', txt))
    if found:
        raise SystemExit('Data_NPCLoc.lua 里已有本链 NPC %s（生成器口径已更新？），'
                         '请人工核对后把 DM_CHAIN_NPLOC 迁去生成器' % found)
    nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl)

    # ① NPCLoc 坐标。
    j = _inject_before_block_end(lines, 'ns.NPCLoc = {', 'NPCLoc 表')
    lines[j:j] = ['    -- 死亡矿井「爆破」任务链 NPC（数据来源：wowhead）'] + DM_CHAIN_NPLOC

    # ② 表外链起始 NPCID 反查（QuestPreNpcID 与 NPCLoc 同在本文件）。
    j = _inject_before_block_end(lines, 'ns.QuestPreNpcID = {', 'QuestPreNpcID 表')
    lines[j:j] = ['    -- 死亡矿井「爆破」链（数据来源：wowhead）'] + \
                 ['    [%d] = %d,' % kv for kv in DM_CHAIN_PRE_NPCID]

    return nl.join(lines).encode('utf-8')


# ── 行尾来源标记（逐行删除）──────────────────────────────────────────────────
TAIL_RULES = [
    (re.compile(r'\s*--\s*\[AQ\]\s*$'), ''),                          # `,  -- [AQ]`
    (re.compile(r'\s*·\s*其中\s*\d+\s*条来自\s*AtlasQuest\s*$'), ''),  # 副本行尾
]

# ── 文本片段清洗（头部之外的零散具名来源）────────────────────────────────────
FRAG_RULES = [
    ('（nfuwow 任务前提/系列核对）', ''),
    ('（nfu 页「开始」字段，可能 A/H 两条用 / 连接）', '（可能 A/H 两条用 / 连接）'),
    ('（nfu 页口径）', ''),
    ('-- 站点尚未公布 boss 名单', '-- 尚未公布 boss 名单'),
]

# 清洗后必须归零的具名来源（自检用）。注意 `来源：` 只查注释形态——
# 任务正文里有「宝石来源：…」这类游戏内文本，绝不能误伤。
BANNED = ('TalentsForever', 'AtlasQuest', 'nfuwow', 'nfu 页', 'mangoszero',
          '[AQ]', '站点', '-- 来源：', '剥离', '上游', '参考键')


def transform(raw):
    """把上游字节流里的项目名注释换成本插件的（只动第 2 行那一处，不做全文替换）。"""
    old_b = OLD_HDR.encode('utf-8')
    new_b = NEW_HDR.encode('utf-8')
    n = raw.count(old_b)
    if n != 1:
        raise SystemExit('上游数据文件里项目名注释出现 %d 次（期望 1 次），同步中止' % n)
    return raw.replace(old_b, new_b)


def clean(raw, name):
    """来源注释清洗：换掉头部注释块 + 删行尾来源标记。保留原换行风格。"""
    txt = raw.decode('utf-8')
    nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl)

    # ① 头部：文件开头连续的 `--` 行整块换成自己的版本
    head = HEAD_BLOCKS.get(name)
    if head:
        i = 0
        while i < len(lines) and lines[i].startswith('--'):
            i += 1
        if i == 0:
            raise SystemExit('%s 首行不是注释，头部清洗中止（上游格式可能已变）' % name)
        lines = head.split('\n') + lines[i:]

    # ② 行尾来源标记 + 零散具名来源片段
    for j, ln in enumerate(lines):
        for rx, rep in TAIL_RULES:
            ln = rx.sub(rep, ln)
        for old, new in FRAG_RULES:
            ln = ln.replace(old, new)
        lines[j] = ln

    return nl.join(lines).encode('utf-8')


def en_count(raw):
    """粗略统计英文残留（仅用于报告，不参与判定）。跳过头部——头部是本插件自己的文案。"""
    lines = raw.decode('utf-8').split('\n')
    i = 0
    while i < len(lines) and lines[i].startswith('--'):
        i += 1
    return len(EN.findall('\n'.join(lines[i:])))


fail = 0
for name in FILES:
    sp = os.path.join(SRC_DIR, name)
    dp = os.path.join(DST_DIR, name)
    if not os.path.exists(sp):
        print('  [SKIP] 上游缺文件 %s' % name)
        fail += 1
        continue

    src_raw = io.open(sp, 'rb').read()
    new_raw = clean(transform(src_raw), name)
    if name == 'Data_NPCLoc.lua':
        # 先注入再校正：fix_npcloc 的「暴风城条目集 == 修正表」自检会把注入键一并验掉。
        new_raw = inject_dm_nploc(new_raw)
        new_raw = fix_npcloc(new_raw)
    if name == 'Data_DungeonQuests.lua':
        new_raw = add_quest_pre_notes(new_raw)
        new_raw = inject_dm_chain(new_raw)
    old_raw = io.open(dp, 'rb').read() if os.path.exists(dp) else b''

    if old_raw == new_raw:
        print('  [SAME] %-24s %6d 字节（已是最新）' % (name, len(new_raw)))
        continue

    # 差异行统计（按行对齐比对，报「本次变了多少行」）
    ol = old_raw.decode('utf-8').split('\n')
    nl_ = new_raw.decode('utf-8').split('\n')
    changed = sum(i2 - i1 for tag, i1, i2, _, _ in
                  difflib.SequenceMatcher(None, ol, nl_).get_opcodes() if tag != 'equal')
    print('  [SYNC] %-24s %6d → %6d 字节，%d 行不同' % (name, len(old_raw), len(new_raw), changed))
    if not DRY:
        io.open(dp, 'wb').write(new_raw)

    # 自检：同步后不得再有具名来源残留（数据来源只保留 wowhead）
    residue = []
    for i, ln in enumerate(nl_):
        for kw in BANNED:
            if kw in ln:
                residue.append('行%d 残留 %s' % (i + 1, kw))
                break
    if residue:
        print('         !! ' + '；'.join(residue[:6]))
        fail += 1
    if changed and old_raw and en_count(new_raw) > en_count(old_raw):
        print('         !! 英文残留数反而上升，请人工确认')

print()
if DRY:
    print('[DRY-RUN] 未写盘')
elif fail:
    print('[FAIL] 有 %d 项异常' % fail)
else:
    print('[OK] 数据四件套已同步（含来源注释清洗）')
sys.exit(1 if fail else 0)
