# -*- coding: utf-8 -*-
"""第八刀（验证）：给第六刀的两处改动配「断言 + 变异 + 登记」。

第六刀改了两处产品逻辑：
  ① PD.ItemIcon —— 材料图标查询记忆化（原来 PD.MatIconTex 每行每材料都直调
     DG.ItemIcon → DG.ItemInfo = GetItemInfo 零缓存引擎调用，一页 ≈ 900 次）
  ② PD.ScanRecipe —— 只给画得出来的行量宽（计数 n 仍精确）

本补丁：
  · df_dungeon_check.py 与 mk_df_check.py（双份）各加 2 条断言；
  · df_mut_check.py 加 2 条变异定义 + MUTATIONS 登记；
  · df_check_new_muts.py 的 DEFAULT_WANT 里登记名字（回归用）。

★ 两条断言都必须**非恒真**：变异一注入就得变红（随后逐条隔离证明）。
"""

import sys

CHECK = '_temp/df_dungeon_check.py'
MK = '_temp/mk_df_check.py'
MUT = '_temp/df_mut_check.py'
WANT = '_temp/df_check_new_muts.py'

ANCHOR = "    ck('★★ 物品名记忆表每次渲染清空（不清就会把「名字还没到货」的占位钉死一整局）',\n"
ANCHOR_TAIL = ("       'local _nmMemo, _nmN = {}, 0' in profui\n"
               "       and 'function PD.ResetItemNameMemo()' in profui\n"
               "       and 'function PD.ItemName(id)' in profui\n"
               "       and 'PD.ResetItemNameMemo()' in _prender)\n")

NEW_CKS = (
    "    # ★★ 2026-10-09 第六轮：实机「列宽材料 17.9ms（其中 材料串 17.2）」那一笔 ——\n"
    "    #   材料图标查询原来**没记忆化**：PD.MatCol 每行每个材料都走\n"
    "    #   PD.MatIconTex → DG.ItemIcon → DG.ItemInfo(id)（= GetItemInfo，零缓存引擎调用），\n"
    "    #   一页 300 行 × 平均 3 材料 ≈ 900 次，且与物品名**同源**。离线实测\n"
    "    #   取名(引擎) 1198 → 467（−61%）、真量宽 288 → 186。\n"
    "    #   ★ 守护点：MatIconTex **不许**再直调 DG.ItemIcon（绕过记忆表 = 白做）；\n"
    "    #     记忆表还必须**跟着 PD.ResetItemNameMemo 一起清**（否则「图标未到货」的\n"
    "    #     占位会钉死一整局）。\n"
    "    ck('★★ 材料图标查询走记忆化（一页上千次同源引擎调用；MatIconTex 不许绕过记忆表）',\n"
    "       'function PD.ItemIcon(id)' in profui\n"
    "       and 'local _icMemo, _icN = {}, 0' in profui\n"
    "       and '    _icMemo, _icN = {}, 0' in profui\n"
    "       and 'local ic = PD.ItemIcon(id)' in profui\n"
    "       and 'local ic = DG.ItemIcon(id)' not in profui)\n"
    "    # ★★ 2026-10-09 第六轮：轻量扫描**只给画得出来的行量宽**。\n"
    "    #   列宽 maxW → PD.RECIPE_NAME_W 只要放得下**真正画出来的**那些行；第\n"
    "    #   ROW_CAP+1 条往后根本不进列表 ⇒ 给它们量宽是纯白做（每次点开白量\n"
    "    #   211 次取名 + 422 次量宽）。\n"
    "    #   ★ 判据是「量宽被 n <= ROW_CAP 圈住」，**不是**「少扫了行」—— 计数 n 必须\n"
    "    #     仍然精确（抬头要显示真实总数）。\n"
    "    ck('★★ 配方页只给画得出来的行量宽（计数 n 仍精确；不许给 ROW_CAP 之后的行白量宽度）',\n"
    "       'if n <= PD.ROW_CAP then' in profui\n"
    "       and 'if w > maxW then maxW = w end' in profui)\n"
)

MUT_KEY = ("MUT_PROF_NO_NM_RESET = ('Core/ProfessionUI.lua', (\n"
           "    b'    PD.ResetItemNameMemo()\\n',\n"
           "    b'    -- MUT: item-name memo never reset\\n'))\n")

MUT_DEF = (
    "\n"
    "# ★★ 材料图标记忆化（2026-10-09 第六轮）：摘掉 = 每行每材料又直查一次\n"
    "#   DG.ItemInfo（GetItemInfo，零缓存引擎调用），一页白烧 ≈ 900 次。\n"
    "MUT_PROF_NO_ICON_MEMO = ('Core/ProfessionUI.lua', (\n"
    "    b'    local ic = PD.ItemIcon(id)',\n"
    "    b'    local ic = DG.ItemIcon(id)  -- MUT: icon memo gone'))\n"
    "\n"
    "# ★★ 扫描只给可见行量宽（2026-10-09 第六轮）：把闸拿掉 = 又给全量 511 行量宽。\n"
    "MUT_PROF_SCAN_ALL_ROWS = ('Core/ProfessionUI.lua', (\n"
    "    b'                if n <= PD.ROW_CAP then\\n',\n"
    "    b'                if true then  -- MUT: scan measures every row\\n'))\n"
)

MUT_REG_ANCHOR = ("    ('专业页：物品名记忆表不清（「名字未到货」的占位被钉死一整局）',"
                  " MUT_PROF_NO_NM_RESET),\n")
MUT_REG_NEW = (MUT_REG_ANCHOR +
               "    ('专业页：材料图标查询又直调 DG.ItemIcon（一页上千次同源引擎调用）',"
               " MUT_PROF_NO_ICON_MEMO),\n"
               "    ('专业页：扫描又给全量行量宽（只画 300 行却量 511 行）',"
               " MUT_PROF_SCAN_ALL_ROWS),\n")

WANT_ANCHOR = "    '专业页：物品名记忆表不清（「名字未到货」的占位被钉死一整局）',\n"
WANT_NEW = (WANT_ANCHOR +
            "    '专业页：材料图标查询又直调 DG.ItemIcon（一页上千次同源引擎调用）',\n"
            "    '专业页：扫描又给全量行量宽（只画 300 行却量 511 行）',\n")

# (文件, 名字, 旧, 新, 哨兵) —— 哨兵是「只在应用后出现」的片段。
#   ★ 本补丁 5 处全是**插入型**（新串包含旧串）⇒ 光靠 count(old) 判不出「已应用」，
#     第二次非 --check 跑就会**再插一遍**。必须靠哨兵。
JOBS = [
    (CHECK, 'A harness 加 2 条断言', ANCHOR + ANCHOR_TAIL, ANCHOR + ANCHOR_TAIL + NEW_CKS,
     '材料图标查询走记忆化'),
    (MK, 'B 生成器加 2 条断言', ANCHOR + ANCHOR_TAIL, ANCHOR + ANCHOR_TAIL + NEW_CKS,
     '材料图标查询走记忆化'),
    (MUT, 'C 变异定义', '', '', 'MUT_PROF_NO_ICON_MEMO = '),
    (MUT, 'D 变异登记', MUT_REG_ANCHOR, MUT_REG_NEW, 'MUT_PROF_NO_ICON_MEMO),'),
    (WANT, 'E DEFAULT_WANT 登记', WANT_ANCHOR, WANT_NEW, '专业页：材料图标查询又直调'),
]


def main():
    check = '--check' in sys.argv
    bad, plans, raws = 0, {}, {}
    for path, name, old, new, key in JOBS:
        if path not in raws:
            raws[path] = open(path, 'rb').read()
        raw = raws[path]
        src = plans.get(path) or raw.decode('utf-8')
        nl = '\r\n' if b'\r\n' in raw else '\n'

        def fx(s):
            return s if nl == '\n' else s.replace('\n', nl)

        if key and fx(key) in src:
            print('  [SKIP] %-22s 已应用' % name)
            continue

        if name.startswith('C'):
            k = fx(MUT_KEY)
            if src.count(k) != 1:
                print('  [BAD ] %-22s 变异定义插入锚点 %d 次' % (name, src.count(k)))
                bad += 1
                continue
            plans[path] = src.replace(k, k + fx(MUT_DEF), 1)
            print('  [OK  ] %-22s 锚点 1 次' % name)
            continue

        o, n = fx(old), fx(new)
        if src.count(o) != 1:
            print('  [BAD ] %-22s 锚点 %d 次' % (name, src.count(o)))
            bad += 1
            continue
        plans[path] = src.replace(o, n, 1)
        print('  [OK  ] %-22s 锚点 1 次' % name)

    if bad:
        print('  \u2717 %d 处未通过，未落盘' % bad)
        return 1
    if check:
        print('  [OK  ] 预检通过（未落盘）')
        return 0
    for path, src in plans.items():
        if src != raws[path].decode('utf-8'):
            with open(path, 'wb') as f:
                f.write(src.encode('utf-8'))
            print('  [OK  ] 已写入 %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
