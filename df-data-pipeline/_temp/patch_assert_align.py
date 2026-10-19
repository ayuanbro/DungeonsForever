# -*- coding: utf-8 -*-
"""2026-10-09 变异重锚收尾：对齐过时断言 + 补孤儿变异的配对静态断言。

背景：_mut_verify.py（基线差集）显示 25 条变异只有 8 条被守住，其余 17 条注入后
零新增红 = 没人守。分两类：
  (a) 配对断言随重构过时（基线就红 / 或改动不再触及断言文本）—— 修 5 条 + 3 条计数化：
      名字到货 __named（count 2→4）、重扫（RefreshItemCards→PaintItemRow + 计数化）、
      常驻池（takeCard/rows[nI]→takeRow/rows[idx]）、收获节（GainsSegs 现口径）、
      任务需求节（renderChips 三参现口径 + 锚点行钉死）、
      QUEST_LOG_UPDATE（计数化 ==2）、RenderQuestDetail 联动（计数化 ==4）、
      卡片列数（3→4）。
  (b) 孤儿变异没有配对断言 —— 补 8 条静态 tripwire：
      攻略页签 / 攻略滚动区让位 / 探索模块挂载 / 预热不短路 / 掉落卡滚轮 /
      专业页 ×3（右对齐 / TBL_NAME_GAP / PushHead 单倍行距）。

口径纪律（与前几轮一致）：
  - 幂等：--check 语义内建（new 已在 → 跳过；old 不在且 new 不在 → 报错退出）。
  - 每条 old 在目标文件中必须恰好命中 1 次（防误伤）。
  - df_dungeon_check.py（实际运行）+ mk_df_check.py（生成器插入块）双处同改；
    上游 tf 直通的断言（收获节/需求节/常驻池/重扫/列数/QDET）mk 里没有，
    只改 df —— mk 重新生成会丢这几条的对齐，见文件头注记。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- 孤儿变异配对断言块（df 与 mk 同文本插入） ----
ORPHANS = '''

    # ---- ★★ 2026-10-09 变异重锚收尾：孤儿变异的配对静态断言 ----
    # 这些变异此前没有配对断言（或配对断言随重构过时），注入后零新增红 = 没人守。
    # 口径：钉住变异锚点行的存在性/计数 —— 基线全绿、注入变异必红（非恒真）。
    ck('★ 攻略页签在二级页签表里（key = "guide" 入口不被摘除）',
       _dui.count('key = "guide"') == 1)
    ck('★ 攻略页签激活时掉落滚动区让位（not isGuide 参与显隐判断）',
       _dui.count('SetShown(not isQuest and not isGuide and not isMap)') == 1)
    ck('★ 探索模块挂载点：ns.ExploreModule.Build(U.explorePage) 调用在（行池有主人）',
       _dui.count('ns.ExploreModule.Build(U.explorePage)') == 1)
    ck('★ 提示框预热不得提前短路（PrewarmLoot 必须真的发请求）',
       'if true then return end' not in _dui)
    ck('★ 掉落卡/任务行等 r:EnableMouseWheel(true) 共 4 处（压在卡上滚轮收得到）',
       _dui.count('r:EnableMouseWheel(true)') == 4)
    ck('★ 专业页：材料组右对齐（right = W - TBL_MAT_RPAD，不从左起摆）',
       profui.count('local right = W - PD.TBL_MAT_RPAD') == 1)
    ck('★ 专业页：名称→材料间距走 TBL_NAME_GAP（白留给材料列）',
       profui.count('local avail = rowW - PD.TBL_MAT_RPAD - PD.LV_NAME_X - PD.TBL_NAME_GAP') == 1)
    ck('★ 专业页：备料清单标题行高走单倍行距（PushHead(..., 1)）',
       profui.count('PushHead(rows, format(L["材料（%d 种）"], #mats), 1)') == 1)
'''

# ---- job 定义：name -> {文件名: (old, new)}；文件不在表里 = 该文件不含此断言（上游直通） ----
JOBS = [
    ('J1 名字到货 __named 计数 2→4 + 孤儿断言块', {
        'df_dungeon_check.py': (
            "    ck('★ 名字到货打 __named 标记（重扫只扫没标记的卡，否则每轮白刷）',\n"
            "       _dui.count('c.__named = hasName') == 2)",
            "    ck('★ 名字到货打 __named 标记（重扫只扫没标记的卡，否则每轮白刷）',\n"
            "       _dui.count('c.__named = hasName') == 4)" + ORPHANS,
        ),
        'mk_df_check.py': (
            "    ck('★ 名字到货打 __named 标记（重扫只扫没标记的卡，否则每轮白刷）',\n"
            "       _dui.count('c.__named = hasName') == 2)",
            "    ck('★ 名字到货打 __named 标记（重扫只扫没标记的卡，否则每轮白刷）',\n"
            "       _dui.count('c.__named = hasName') == 4)" + ORPHANS,
        ),
    }),
    ('J2 QUEST_LOG_UPDATE 监听计数化（==2，变异摘 1 处剩 1 必红）', {
        'df_dungeon_check.py': (
            "    ck('★ 接任务 / 放弃任务也要当场刷（QUEST_LOG_UPDATE 监听 + 独立分支不动完成态快照）',\n"
            "       'RegisterEvent(\"QUEST_LOG_UPDATE\")' in qcode\n"
            "       and 'elseif event == \"QUEST_LOG_UPDATE\" then' in qcode)",
            "    ck('★ 接任务 / 放弃任务也要当场刷（QUEST_LOG_UPDATE 监听 + 独立分支不动完成态快照）',\n"
            "       qcode.count('RegisterEvent(\"QUEST_LOG_UPDATE\")') == 2\n"
            "       and 'elseif event == \"QUEST_LOG_UPDATE\" then' in qcode)",
        ),
    }),
    ('J3 重扫断言对齐 PaintItemRow + 计数化（==2）', {
        'df_dungeon_check.py': (
            "    ck('★ 重扫只碰「名字还没到货」的卡（带 __named 的跳过，别每轮白刷）',\n"
            "       'if it and not c.__named then' in tipcode\n"
            "       and 'DG.RefreshItemCards(it[1])' in tipcode)",
            "    ck('★ 重扫只碰「名字还没到货」的卡（带 __named 的跳过，别每轮白刷）',\n"
            "       tipcode.count('if it and not c.__named then') == 2\n"
            "       and 'DG.PaintItemRow(c, it[1])' in tipcode)",
        ),
    }),
    ('J4 常驻池断言对齐 takeRow/rows[idx]', {
        'df_dungeon_check.py': (
            "    ck('卡片仍走常驻池（建卡在 takeCard、位置在 rows[nI]）',\n"
            "       'local function takeCard()' in rcode and 'rows[nI] = r' in rcode)",
            "    ck('卡片仍走常驻池（takeRow 从 rows 池取行，不每轮新建）',\n"
            "       'takeRow' in rcode and 'local r = rows[idx]' in rcode)",
        ),
    }),
    ('J5 收获节断言对齐 DG.GainsSegs 现口径', {
        'df_dungeon_check.py': (
            "    ck('★ 详情页收获节：经验/金钱/声望（q[18]，wowhead 收获区，2026-09-22）',\n"
            "       'if g and (g.xp or g.money or (g.rep and #g.rep > 0)) then' in src\n"
            "       and 'math.floor(g.money / 10000)' in src\n"
            "       and 'rs[#rs + 1] = rr[3] .. \" +\" .. rr[2]' in src\n"
            "       and '{ xp = ' in qdat)",
            "    ck('★ 详情页收获节：经验/金钱/声望（DG.GainsSegs 统一拼装，2026-10-09 对齐现口径）',\n"
            "       'local seg = DG.GainsSegs(q)' in src\n"
            "       and 'if seg and #seg > 0 then' in src\n"
            "       and 'L[\"收获\"]' in src)",
        ),
    }),
    ('J6 任务需求节断言对齐 renderChips 三参 + 锚点行钉死', {
        'df_dungeon_check.py': (
            "    ck('★ 奖励/需求两列网格 + 「任务需求」单列（需要提供 ≠ 奖励，2026-09-22）',\n"
            "       'local function renderChips(items, ncol)' in src\n"
            "       and 'renderChips(q[14], 2)' in src and 'renderChips(rew, 2)' in src\n"
            "       and 'L[\"任务需求\"]' in src)",
            "    ck('★ 奖励/需求两列网格 + 「任务需求」单列（需要提供 ≠ 奖励，2026-09-22）',\n"
            "       'local function renderChips(items, ncol, questID)' in src\n"
            "       and 'renderChips(q[14], 2, q[1])' in src and 'renderChips(rew, 2)' in src\n"
            "       and 'if hasChips or objTxt then' in src\n"
            "       and 'L[\"任务需求\"]' in src)",
        ),
    }),
    ('J7 右列详情联动计数化（1 定义 + 3 调用 ==4）', {
        'df_dungeon_check.py': (
            "    ck('★ 点行选中 → 右列就地刷新（渲染尾部联动 RenderQuestDetail）',\n"
            "       'U.dungeonQuestSel = r.__q[1]' in src and 'U:RenderQuestDetail()' in src)",
            "    ck('★ 点行选中 → 右列就地刷新（渲染尾部联动 RenderQuestDetail，1 定义 + 3 调用）',\n"
            "       'U.dungeonQuestSel = r.__q[1]' in src and 'U:RenderQuestDetail()' in src\n"
            "       and src.count('U:RenderQuestDetail()') == 4)",
        ),
    }),
    ('J8 卡片列数断言 3→4（2026-10-01 用户定版）', {
        'df_dungeon_check.py': (
            '    ck("卡片列数 = 3", DGn.LOOT_COLS == 3, DGn.LOOT_COLS)',
            '    ck("卡片列数 = 4（2026-10-01 用户：一行 3 件 → 4 件）", DGn.LOOT_COLS == 4, DGn.LOOT_COLS)',
        ),
    }),
    ('J9 卡片列数静态 tripwire（动态断言在 Lua 265 行死区，静态兜底）', {
        'df_dungeon_check.py': (
            "    ck('★ 专业页：备料清单标题行高走单倍行距（PushHead(..., 1)）',\n"
            "       profui.count('PushHead(rows, format(L[\"材料（%d 种）\"], #mats), 1)') == 1)",
            "    ck('★ 专业页：备料清单标题行高走单倍行距（PushHead(..., 1)）',\n"
            "       profui.count('PushHead(rows, format(L[\"材料（%d 种）\"], #mats), 1)') == 1)\n"
            "    ck('★ 卡片墙列数定版 4（DG.LOOT_COLS = 4；动态断言在 Lua 死区，静态兜底）',\n"
            "       'DG.LOOT_COLS = 4' in _dui)",
        ),
        'mk_df_check.py': (
            "    ck('★ 专业页：备料清单标题行高走单倍行距（PushHead(..., 1)）',\n"
            "       profui.count('PushHead(rows, format(L[\"材料（%d 种）\"], #mats), 1)') == 1)",
            "    ck('★ 专业页：备料清单标题行高走单倍行距（PushHead(..., 1)）',\n"
            "       profui.count('PushHead(rows, format(L[\"材料（%d 种）\"], #mats), 1)') == 1)\n"
            "    ck('★ 卡片墙列数定版 4（DG.LOOT_COLS = 4；动态断言在 Lua 死区，静态兜底）',\n"
            "       'DG.LOOT_COLS = 4' in _dui)",
        ),
    }),
]


def apply(path, old, new):
    data = open(path, 'rb').read()
    text = data.decode('utf-8')
    if new in text:
        return '已是最新'
    n = text.count(old)
    if n != 1:
        # 兜底：文件若为 CRLF，把 old/new 的 \n 换成 \r\n 再试
        if b'\r\n' in data:
            o2, n2 = old.replace('\n', '\r\n'), new.replace('\n', '\r\n')
            c2 = text.count(o2)
            if c2 == 1:
                text = text.replace(o2, n2)
                open(path, 'wb').write(text.encode('utf-8'))
                return '已应用(CRLF)'
        return 'old 命中 %d 次（预期 1）' % n
    text = text.replace(old, new)
    open(path, 'wb').write(text.encode('utf-8'))
    return '已应用'


def main():
    bad = 0
    for name, targets in JOBS:
        print('== %s ==' % name)
        for fname, (old, new) in sorted(targets.items()):
            path = os.path.join(HERE, fname)
            try:
                status = apply(path, old, new)
            except Exception as exc:  # noqa: BLE001
                status = '异常: %r' % (exc,)
            if status.startswith(('已应用', '已是最新')):
                print('   [%s] %s' % (status, fname))
            else:
                bad += 1
                print('   [失败] %s -> %s' % (fname, status))
    if bad:
        print('共 %d 个失败' % bad)
        return 1
    print('全部 job 完成')
    return 0


if __name__ == '__main__':
    sys.exit(main())
