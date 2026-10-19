#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""patch_prof_perf6.py
  配方页的物品请求改成「按需轻量」—— 不再调 DG.RequestItem。

  证据（实机 /dfprofperf，2026-10-09 第四轮）：
    点开「制皮·recipe」整次 363.3ms，其中
      请求段 288.2ms / 392 次 = 每次 0.72ms —— 占 79%
    而 DG.RequestItem 每次做四件事：
      ① C_Item.RequestLoadItemDataByID(id)          —— 请求载入（异步，便宜）
      ② GetItemInfo(id)                             —— 查一次（便宜）
      ③ DG.__warmTip:SetItemByID(id)                —— **构建整条 tooltip**（贵）
      ④ DG.ContinueOnItemLoad(id, cb)               —— **Item:CreateFromItemID + 回调**（贵）
    ③④ 是给**掉落页**（要品质/图标/随机属性等完整数据）准备的；配方页只要一个
    **物品名**。⇒ 只保留 ①②，且「名字已到货就不再请求」，天然去重。

  ★ 不碰 DungeonUI.lua：只改 ProfessionUI.lua 里 PD.RequestRows 自己的调用方式。
  ★ 名字到货后的重渲链路不变：PD.notReady + PD.ScheduleSweep(0.5/1.5/4/9s) → PD.SweepNames → PD.Render。
  ★ 幂等：哨兵命中即 SKIP。--check 只预检不落盘。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.normpath(os.path.join(HERE, '..', 'Core', 'ProfessionUI.lua'))

SENTINEL = '★★ 轻量请求（2026-10-09 第四轮'

E1_OLD = '    if not DG.RequestItem then return end\n'
E1_NEW = '    if not DG.ItemName then return end\n'

E2_OLD = ('        DG.RequestItem(id)\n'
          '        if not select(2, DG.ItemName(id)) then wait[#wait + 1] = id end\n')

E2_NEW = '''        local hasName = select(2, DG.ItemName(id))
        if hasName then return end
        -- ★★ 轻量请求（2026-10-09 第四轮；实机 /dfprofperf 实测）：
        --   原先这里调 DG.RequestItem(id) —— 那是为**掉落页**写的：每次都往一个
        --   隐藏 GameTooltip 上 SetItemByID 预热（构建整条 tooltip），再
        --   Item:CreateFromItemID + ContinueOnItemLoad 注册回调。
        --   实测点开配方页签 392 次 = 282.7ms，占整次 363.3ms 的 79%。
        --   配方页只需要**物品名** ⇒ 只请求载入 + 查一次，不建 tooltip、不建 Item 对象。
        --   名字到货后由 PD.SweepNames（0.5/1.5/4/9s 定时）触发重渲，链路不变。
        if C_Item and C_Item.RequestLoadItemDataByID then
            pcall(C_Item.RequestLoadItemDataByID, id)
        end
        local gi = GetItemInfo or (C_Item and C_Item.GetItemInfo)
        if type(gi) == "function" then pcall(gi, id) end
        -- 名字已到货的**不再请求** ⇒ 天然去重；客户端驱逐缓存后名字退回占位，
        -- 那时 hasName 又为假 ⇒ 自动重请一次（与 DG.RequestItem 的 force 语义一致）。
        wait[#wait + 1] = id
'''

EDITS = [
    ('1 前置判空换成 DG.ItemName', E1_OLD, E1_NEW),
    ('2 want() 改轻量请求', E2_OLD, E2_NEW),
]


def to_file_style(text, raw):
    if b'\r\n' in raw:
        return text.replace('\r\n', '\n').replace('\n', '\r\n')
    return text


def main():
    check = '--check' in sys.argv
    raw = open(TARGET, 'rb').read()
    src = raw.decode('utf-8')

    if SENTINEL in src:
        print('  [SKIP] 轻量请求已应用（哨兵命中）')
        return 0

    out = src
    bad = 0
    for name, old, new in EDITS:
        o, n = to_file_style(old, raw), to_file_style(new, raw)
        if out.count(n) == 1 and out.count(o) == 0:
            print('  [SKIP] %-28s 已应用' % name)
            continue
        if out.count(o) != 1:
            print('  [BAD ] %-28s 锚点 %d 次' % (name, out.count(o)))
            bad += 1
            continue
        if out.count(n) >= 1:
            print('  [BAD ] %-28s 替换串已存在（幂等冲突）' % name)
            bad += 1
            continue
        out = out.replace(o, n, 1)
        print('  [OK  ] %-28s 锚点 1 次' % name)

    if bad:
        return 1
    if check:
        print('  [OK  ] 预检通过（未落盘）')
        return 0

    with open(TARGET, 'wb') as f:
        f.write(out.encode('utf-8'))
    print('  [OK  ] 已写入 %s（%+d 字节）' % (TARGET, len(out.encode('utf-8')) - len(raw)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
