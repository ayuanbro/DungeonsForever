# -*- coding: utf-8 -*-
"""第四刀：名字收割别再逐卡走「全池扫 + Invalidate + ApplyAll」那条重链。

背景（2026-10-03「点副本就卡死」）：
  分片之后每帧只收割 12 张，但**每张**都调一次 DG.RefreshItemCards(itemID) ——
  那个函数是「按 itemID 全池扫」的入口，末尾还要 LF.Invalidate + LF.ApplyAll。
  于是单帧成本 = 292 张卡 × (292 次全池扫 + 292 次整池 ApplyAll) ≈ 常数万次内层循环，
  而且分片把它切成十几次调用后，**总工作量比原来单帧一次涨了十几倍**。
  收割时卡片本来就是手里这张 ⇒ 直接 O(1) 画它自己即可。
  LF.Invalidate(it[1]) 保留（O(1)，语义 = 「这件物品的过滤缓存作废」），
  末尾那一次 LF.ApplyAll() 照旧（原来每张卡都 ApplyAll，现在整轮只做一次，只快不慢）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r'D:\workspace\DungeonsForever\Core\DungeonUI.lua'
BAK = os.path.join(HERE, '_bak_DungeonUI_sweeppaint.lua.bak')

data = open(SRC, 'rb').read()
open(BAK, 'wb').write(data)


def j(*lines):
    return ('\r\n'.join(lines) + '\r\n').encode('utf-8')


def rep(old, new, tag, cnt=1):
    global data
    got = data.count(old)
    assert got == cnt, '%s：锚点命中 %d 次（期望 %d）' % (tag, got, cnt)
    data = data.replace(old, new, cnt)
    print('  ok %s' % tag)


# ① 新增两个 O(1) 单卡绘制口（插在 DG.ItemName 之前）
NEW_FUNCS = j(
    '-- ★★ 单卡刷新（2026-10-03「点副本就卡死」第四刀）：DG.RefreshItemCards 是「按 itemID',
    '--   **全池扫**」的入口（事件 / 官方异步回调只拿得到 itemID），而且每次调用末尾还要',
    '--   LF.Invalidate + LF.ApplyAll 走一遍掉落过滤。名字收割里卡片本来就是手里这张，',
    '--   逐卡走那条链 = 每题 292 次全池扫 + 292 次整池 ApplyAll（实测是分片之后剩下最大的一坨）。',
    '--   这里给「已知是哪张卡」的场景一个 O(1) 的纯绘制口。',
    '--   ⚠️ 绘制口径必须与 DG.RefreshItemCards 里那两段保持一致（那边留给「只有 itemID」的入口）。',
    'function DG.PaintItemRow(c, itemID)',
    '    if not (c and itemID) then return end',
    '    if c.name then',
    '        local nm, hasName = DG.ItemName(itemID)',
    '        c.name:SetText(nm)',
    '        if hasName then',
    '            c.name:SetTextColor(DG.QColor(DG.QualOf(itemID)))',
    '        else',
    '            c.name:SetTextColor(Unpack(C_GREY))',
    '        end',
    '        c.__named = hasName',
    '    end',
    '    if c.icon and c.icon.SetTexture then c.icon:SetTexture(DG.ItemIcon(itemID)) end',
    '    if c.tp then c.tp:SetText(DG.ItemMeta(itemID)) end',
    'end',
    '',
    'function DG.PaintItemChip(c, itemID)',
    '    if not (c and c.name and itemID) then return end',
    '    local nm, hasName = DG.ItemName(itemID)',
    '    c.name:SetText(nm)',
    '    if hasName then',
    '        local qr, qg, qb = DG.QColor(DG.QualOf(itemID))',
    '        if qr then',
    '            c.name:SetTextColor(qr, qg, qb)',
    '        else',
    '            c.name:SetTextColor(Unpack(C_TEXT))',
    '        end',
    '    else',
    '        c.name:SetTextColor(Unpack(C_GREY))',
    '    end',
    '    c.__named = hasName',
    'end',
    '',
    'function DG.ItemName(id)')
rep(j('function DG.ItemName(id)'), NEW_FUNCS, '① 新增 PaintItemRow / PaintItemChip')

# ② 收割里 LF 提到函数头（后面两处单卡刷新都要用）
rep(j('    local left = DG.ITEM_WARM_CHUNK * 2',
      '    local more = false'),
    j('    local LF = ns.LootFilter',
      '    local left = DG.ITEM_WARM_CHUNK * 2',
      '    local more = false'),
    '② 收割函数头 hoist LF')
rep(j('    local LF = ns.LootFilter',
      '    if LF then LF.ApplyAll() end',
      'end'),
    j('    if LF then LF.ApplyAll() end',
      'end'),
    '② 删掉函数尾重复的 local LF')

# ③ 物品池：逐卡全池扫 → O(1) 画自己 + 单件失效
rep(j('        for i = 1, #pool do',
      '            local c = pool[i]',
      '            local it = c and c.__it',
      '            if it and not c.__named then',
      '                DG.RefreshItemCards(it[1])'),
    j('        for i = 1, #pool do',
      '            local c = pool[i]',
      '            local it = c and c.__it',
      '            if it and not c.__named then',
      '                -- ★ O(1) 画这张卡；失效只针对这一件（末尾统一 ApplyAll 一次）',
      '                DG.PaintItemRow(c, it[1])',
      '                if LF then LF.Invalidate(it[1]) end'),
    '③ 物品池改为单卡刷新')

# ④ 任务奖励芯片池：同上
rep(j('        for i = 1, #qpool do',
      '            local c = qpool[i]',
      '            local it = c and c.__it',
      '            if it and not c.__named then',
      '                DG.RefreshItemCards(it[1])'),
    j('        for i = 1, #qpool do',
      '            local c = qpool[i]',
      '            local it = c and c.__it',
      '            if it and not c.__named then',
      '                DG.PaintItemChip(c, it[1])',
      '                if LF then LF.Invalidate(it[1]) end'),
    '④ 芯片池改为单卡刷新')

open(SRC, 'wb').write(data)
crlf = data.count(b'\r\n')
bare = data.count(b'\n') - crlf
print('写入 %s：%d 字节，CRLF = %d，裸 LF = %d' % (SRC, len(data), crlf, bare))
