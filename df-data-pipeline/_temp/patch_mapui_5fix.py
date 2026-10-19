# -*- coding: utf-8 -*-
"""地图页五项修改：①底色L2×2 ②字号14×4 ③返回钮96×24/14 ④SIDE_GAP 8 ⑨删死常量。MapUI.lua = LF。"""
import sys

P = 'Core/MapUI.lua'
d = open(P, 'rb').read()

def rep(old, new, tag):
    global d
    o, n = old.encode('utf-8'), new.encode('utf-8')
    if d.count(o) != 1:
        print('[MISS] %s (count=%d)' % (tag, d.count(o)))
        sys.exit(1)
    d = d.replace(o, n)
    print('[OK] %s' % tag)

rep('        ns.hui.BuildRoundedBG(hdrCard, M.BLK_RADIUS, { 1, 1, 1, 0.03 }, "both", true, 1)',
    '        ns.hui.BuildRoundedBG(hdrCard, M.BLK_RADIUS, ns.hui.layer.L2, "both", true, 1)',
    '1a hdrCard 底色 -> L2')
rep('        ns.hui.BuildRoundedBG(side, M.BLK_RADIUS, { 1, 1, 1, 0.03 }, "both", true, 1)',
    '        ns.hui.BuildRoundedBG(side, M.BLK_RADIUS, ns.hui.layer.L2, "both", true, 1)',
    '1b side 底色 -> L2')

rep('    local detLtCnt = MakeFS(blkLoot, 12, C_GREY, "RIGHT")',
    '    local detLtCnt = MakeFS(blkLoot, 14, C_GREY, "RIGHT")',
    '2a 件数注 12 -> 14')
rep('    local detLtNote = MakeFS(blkLoot, 13, C_GREY, "LEFT")',
    '    local detLtNote = MakeFS(blkLoot, 14, C_GREY, "LEFT")',
    '2b 空态注 13 -> 14')
rep('        r.ds = MakeFS(r, 12, C_TEXT, "LEFT")',
    '        r.ds = MakeFS(r, 14, C_TEXT, "LEFT")',
    '2c 技能描述 12 -> 14')
rep('    local listNote = MakeFS(listChild, 13, C_GREY, "LEFT")',
    '    local listNote = MakeFS(listChild, 14, C_GREY, "LEFT")',
    '2d 列表空态 13 -> 14')

rep('    local detBack = Host.NewButton(detChild, L["‹ 全部首领"], 84, 20, 12)',
    '    local detBack = Host.NewButton(detChild, L["‹ 全部首领"], 96, 24, 14)',
    '3 返回钮 84x20/12 -> 96x24/14')

rep('M.SIDE_GAP = 10', 'M.SIDE_GAP = 8', '4 SIDE_GAP 10 -> 8')
rep('（936 − 663 − 10 = 263）。这三者是一组**联动值**',
    '（936 − 663 − 8 = 265）。这三者是一组**联动值**',
    '4b 注释 263 -> 265')

rep('M.CUSTOM_W = 663                        -- 贴图宽 = M.MAP_W（画布实际像素）\nM.CUSTOM_H = 442                        -- 贴图高 = M.FRAME_H\n', '',
    '9 删死常量 CUSTOM_W/CUSTOM_H')

open(P, 'wb').write(d)
c = d.count(b'\r\n')
print('saved CRLF=%d LF-only=%d' % (c, d.count(b'\n') - c))
