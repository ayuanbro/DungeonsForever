# -*- coding: utf-8 -*-
"""把详情页的「物品数据催到货」与「名字收割」从「一帧几百次」改成分帧。

2026-10-03「点副本就卡死」第三刀。
"""
import hashlib
import os
import shutil

SRC = r'Core/DungeonUI.lua'
BAK = r'_temp/_bak_DungeonUI_warmsplit.lua.bak'

b = open(SRC, 'rb').read()
assert b.count(b'\n') == b.count(b'\r\n'), '期望全 CRLF'
before_crlf = b.count(b'\r\n')


def j(*lines):
    return ('\r\n'.join(lines) + '\r\n').encode('utf-8')


def rep(data, old, new, tag):
    c = data.count(old)
    assert c == 1, '%s: count=%d' % (tag, c)
    return data.replace(old, new)


if not os.path.exists(BAK):
    shutil.copyfile(SRC, BAK)
    print('备份 ->', BAK)

# ── ① 新常量 ────────────────────────────────────────────────────────────────
b = rep(
    b,
    b'DG.SWEEP_AT = { 0.5, 1.5, 4, 9 }\r\n',
    j('-- ★★★ 物品数据「催到货」的分帧片大小（2026-10-03「点副本就卡死」第三刀）——',
      '--   一本副本的掉落一次最多催这么多件，剩下的由分帧器摊到随后的空闲帧里。',
      '--   实机根因：通灵学院一本 292 件、黑石深渊 180 件，原来在「打开详情」的那一帧里',
      '--   **一口气**全催一遍；每一件都走 DG.RequestItem 的隐藏 tooltip（真机上 tooltip',
      '--   渲染物品必须先有数据 ⇒ 同步装载），几百次堆在同一帧 = 主线程卡死数秒 ⇒ Windows',
      '--   判定无响应、整窗涂灰。分片之后每帧只付一小撮的成本，界面全程可交互。',
      'DG.ITEM_WARM_CHUNK = 6',
      '',
      'DG.SWEEP_AT = { 0.5, 1.5, 4, 9 }'),
    'ITEM_WARM_CHUNK')

# ── ② PrewarmLoot 改分帧 ────────────────────────────────────────────────────
b = rep(
    b,
    j('    DG.EnsureItemListener()',
      '    for _, s in ipairs(loot) do',
      '        for _, it in ipairs(s[5]) do',
      '            local _, hasName = DG.ItemName(it[1])',
      '            DG.RequestItem(it[1], not hasName)',
      '        end',
      '    end'),
    j('    DG.EnsureItemListener()',
      '    -- ★★★ 分帧（2026-10-03「点副本就卡死」第三刀）：整本的物品不再在「打开详情」这一帧',
      '    --   里一口气催完（见 DG.ITEM_WARM_CHUNK）。现在每帧只催一小撮，催完自己在队尾续',
      '    --   一段；C_Timer 不可用（离线 harness / 极端环境）时 DG.RunSteps 递归同步跑完 ——',
      '    --   调用方返回时整本已经催过，断言因此看到的仍是「全都做了」，无需感知分帧。',
      '    local list, n = {}, 0',
      '    for _, s in ipairs(loot) do',
      '        local its = s[5]',
      '        for k = 1, #(its or {}) do',
      '            n = n + 1',
      '            list[n] = its[k]',
      '        end',
      '    end',
      '    local i = 1',
      '    local function warmChunk()',
      '        local stop = i + DG.ITEM_WARM_CHUNK - 1',
      '        if stop > n then stop = n end',
      '        for k = i, stop do',
      '            local it = list[k]',
      '            -- 名字还拿不到就**强制**重请一次：客户端物品缓存会被驱逐',
      '            -- （ItemMixin:IsDataEvictable 恒 true），去过重的话驱逐之后再进这个副本',
      '            -- 就永远停在占位文案上了。',
      '            local _, hasName = DG.ItemName(it[1])',
      '            DG.RequestItem(it[1], not hasName)',
      '        end',
      '        i = stop + 1',
      '        if i <= n then DG.PushStep(warmChunk) end   -- 本帧催完这一撮，下一帧接着来',
      '    end',
      '    if n > 0 then',
      '        DG.PushStep(warmChunk)',
      '        DG.RunSteps()',
      '    end'),
    'PrewarmLoot')

# ── ③ SweepMissingNames 改分帧 ──────────────────────────────────────────────
POOL_HEAD = ['    if %s then',
             '        for i = 1, #%s do',
             '            local c = %s[i]',
             '            local it = c and c.__it',
             '            if it and not c.__named then',
             '                DG.RefreshItemCards(it[1])',
             '                if not c.__named and DG.HarvestTipName then',
             '                    if left <= 0 then',
             '                        more = true',
             '                    else',
             '                        left = left - 1',
             '                        local nm = DG.HarvestTipName(it[1])',
             '                        if nm and c.name then',
             '                            c.name:SetText(nm)',
             '                            local col = DG.__tipColor',
             '                            if col then',
             '                                c.name:SetTextColor(col[1] or 1, col[2] or 1, col[3] or 1)',
             '                                DG.__tipColor = nil',
             '                            else',
             '                                c.name:SetTextColor(Unpack(C_GREY))',
             '                            end',
             '                            c.__named = true']


def pool_block(pool_var, extra):
    lines = [x % pool_var if '%s' in x else x for x in POOL_HEAD]
    lines += extra
    lines += ['                        end',
              '                    end',
              '                end',
              '            end',
              '        end',
              '    end']
    return lines


NEW_SWEEP = [
    '    -- ★★★ 分帧（2026-10-03「点副本就卡死」第三刀）：重扫原来是**一次 for 扫完整池** ——',
    '    --   通灵学院一本 292 张卡，每张都走 DG.HarvestTipName，而那是「把隐藏 tooltip 渲染',
    '    --   一遍物品」的重活（真机上 tooltip 渲染物品必须先有数据 ⇒ 同步装载），几百次堆在',
    '    --   同一帧 = 主线程卡死数秒 ⇒ Windows 判定无响应、整窗涂灰。',
    '    --   现在一次最多收割 DG.ITEM_WARM_CHUNK × 2 张，没割完的排到后续空闲帧继续（more）。',
    '    local left = DG.ITEM_WARM_CHUNK * 2',
    '    local more = false',
    '    local pool = U.dungeonDetailPool and U.dungeonDetailPool.item',
] + pool_block('pool', []) + [
    '    local qpool = U.dungeonQDetPool and U.dungeonQDetPool.chip',
    '    local needQRender = false',
] + pool_block('qpool', [
    '                            DG.ApplyChipBadge(c)',
    '                            if c.__q then needQRender = true end',
]) + [
    '    -- ★ 分帧：这一帧没割完就排到下一帧（别把剩下的几百张也啃在这一帧里）。',
    '    if more then',
    '        DG.PushStep(DG.SweepMissingNames)',
    '        DG.RunSteps()',
    '        return',
    '    end',
    '    if needQRender and U.RenderQuestDetail and U.dungeonQDet',
    '       and U.dungeonQDet.IsShown and U.dungeonQDet:IsShown() then',
    '        U:RenderQuestDetail()',
    '    end',
    '    local LF = ns.LootFilter',
    '    if LF then LF.ApplyAll() end',
]

OLD_SWEEP = j(
    '    local pool = U.dungeonDetailPool and U.dungeonDetailPool.item',
    '    if pool then',
    '        for i = 1, #pool do',
    '            local c = pool[i]',
    '            local it = c and c.__it',
    '            if it and not c.__named then',
    '                DG.RefreshItemCards(it[1])',
    '                if not c.__named and DG.HarvestTipName then',
    '                    local nm = DG.HarvestTipName(it[1])',
    '                    if nm and c.name then',
    '                        c.name:SetText(nm)',
    '                        local col = DG.__tipColor',
    '                        if col then',
    '                            c.name:SetTextColor(col[1] or 1, col[2] or 1, col[3] or 1)',
    '                            DG.__tipColor = nil',
    '                        else',
    '                            c.name:SetTextColor(Unpack(C_GREY))',
    '                        end',
    '                        c.__named = true',
    '                    end',
    '                end',
    '            end',
    '        end',
    '    end',
    '    local qpool = U.dungeonQDetPool and U.dungeonQDetPool.chip',
    '    local needQRender = false',
    '    if qpool then',
    '        for i = 1, #qpool do',
    '            local c = qpool[i]',
    '            local it = c and c.__it',
    '            if it and not c.__named then',
    '                DG.RefreshItemCards(it[1])',
    '                if not c.__named and DG.HarvestTipName then',
    '                    local nm = DG.HarvestTipName(it[1])',
    '                    if nm and c.name then',
    '                        c.name:SetText(nm)',
    '                        local col = DG.__tipColor',
    '                        if col then',
    '                            c.name:SetTextColor(col[1] or 1, col[2] or 1, col[3] or 1)',
    '                            DG.__tipColor = nil',
    '                        else',
    '                            c.name:SetTextColor(Unpack(C_GREY))',
    '                        end',
    '                        c.__named = true',
    '                        DG.ApplyChipBadge(c)',
    '                        if c.__q then needQRender = true end',
    '                    end',
    '                end',
    '            end',
    '        end',
    '    end',
    '    if needQRender and U.RenderQuestDetail and U.dungeonQDet',
    '       and U.dungeonQDet.IsShown and U.dungeonQDet:IsShown() then',
    '        U:RenderQuestDetail()',
    '    end',
    '    local LF = ns.LootFilter',
    '    if LF then LF.ApplyAll() end')

b = rep(b, OLD_SWEEP, j(*NEW_SWEEP), 'SweepMissingNames')

assert b.count(b'\n') == b.count(b'\r\n'), '改造后出现裸 LF'
open(SRC, 'wb').write(b)
print('CRLF %d -> %d，字节 %d' % (before_crlf, b.count(b'\r\n'), len(b)))
print('md5 =', hashlib.md5(b).hexdigest()[:12])
