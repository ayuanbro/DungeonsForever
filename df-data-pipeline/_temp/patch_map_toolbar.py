import sys, os

ROOT = 'D:/workspace/DungeonsForever/'
MAP = ROOT + 'Core/MapUI.lua'
CHK = ROOT + '_temp/df_dungeon_check.py'

CHECK_ONLY = '--check' in sys.argv

MAP_SUBS = [
    # M1: FRAME_H 真值口径
    (
        "M.FRAME_H = Host.CONTENT_H - (Host.ROW_CLASS + 36) - Host.PAGE_INSET - DG.GUIDE_TOP_Y",
        "M.FRAME_H = Host.CONTENT_H - DG.GUTTER - Host.PAGE_INSET - DG.GUIDE_TOP_Y",
        1,
    ),
    # M2: 新增工具栏卡常量 + MAP_W 改由 MAP_H 反算
    (
        "M.SIDE_GAP = 10\nM.MAP_W = math.floor(M.FRAME_H * M.ART_W / M.ART_H)",
        "M.HDR_CARD_H = 50\nM.HDR_GAP = 8\nM.SIDE_GAP = 10\nM.MAP_H = M.FRAME_H - M.HDR_CARD_H - M.HDR_GAP\nM.MAP_W = math.floor(M.MAP_H * M.ART_W / M.ART_H)",
        1,
    ),
    # M3: Box 图上偏移 = 卡高 + 间距
    (
        "    return M.MAP_W, M.MAP_W, M.FRAME_H, 0, 0",
        "    return M.MAP_W, M.MAP_W, M.MAP_H, 0, M.HDR_CARD_H + M.HDR_GAP",
        1,
    ),
    # M4: 空态文字居中于地图区（含下移）
    (
        '    empty:SetPoint("CENTER", frame, "TOPLEFT", (M.FRAME_W - M.SIDE_W - M.SIDE_GAP) / 2, -M.FRAME_H / 2)',
        '    empty:SetPoint("CENTER", frame, "TOPLEFT", (M.FRAME_W - M.SIDE_W - M.SIDE_GAP) / 2, -(M.HDR_CARD_H + M.HDR_GAP + M.MAP_H / 2))',
        1,
    ),
    # M5: 新建顶部工具栏卡
    (
        "    if hero then frame:SetFrameLevel(hero:GetFrameLevel() + 1) end\n    frame:Hide()\n\n    -- 地图画布（12 块瓦片）",
        "    if hero then frame:SetFrameLevel(hero:GetFrameLevel() + 1) end\n    frame:Hide()\n\n    local hdrCard = CreateFrame(\"Frame\", nil, frame, \"BackdropTemplate\")\n    hdrCard:SetPoint(\"TOPLEFT\", frame, \"TOPLEFT\", 0, 0)\n    hdrCard:SetSize(M.MAP_W, M.HDR_CARD_H)\n    hdrCard:SetFrameLevel(frame:GetFrameLevel() + 1)\n    if ns.hui and ns.hui.BuildRoundedBG then\n        ns.hui.BuildRoundedBG(hdrCard, M.BLK_RADIUS, { 1, 1, 1, 0.03 }, \"both\", true, 1)\n    else\n        hdrCard:SetBackdrop({\n            bgFile = \"Interface\\\\Buttons\\\\WHITE8x8\",\n            edgeFile = \"Interface\\\\Buttons\\\\WHITE8x8\",\n            edgeSize = 1,\n        })\n        hdrCard:SetBackdropColor(1, 1, 1, 0.03)\n        hdrCard:SetBackdropBorderColor(1, 1, 1, 0.10)\n    end\n\n    -- 地图画布（12 块瓦片）",
        1,
    ),
    # M6: 池化字段登记
    (
        "    frame.canvas = canvas\n    frame.tiles = tiles",
        "    frame.canvas = canvas\n    frame.hdrCard = hdrCard\n    frame.tiles = tiles",
        1,
    ),
    # M7: 楼层条 / 隐藏图钉 移入工具栏卡
    (
        '    frame.bar:SetPoint("TOPRIGHT", frame, "TOPLEFT",\n                       cx + cw - M.FLOOR_INSET, -(cy + M.FLOOR_INSET))',
        '    frame.bar:SetPoint("RIGHT", frame.hdrCard, "RIGHT", -M.SIDE_PAD, 0)',
        1,
    ),
    (
        '    frame.bossBtn:SetPoint("TOPLEFT", frame, "TOPLEFT",\n                           cx + M.FLOOR_INSET, -(cy + M.FLOOR_INSET))',
        '    frame.bossBtn:SetPoint("LEFT", frame.hdrCard, "LEFT", M.SIDE_PAD, 0)',
        1,
    ),
]

CHK_SUBS = [
    (
        "    ck('★★ 奥巢 hero/卡面美术 = 插件自带 TGA（ArtOf 先查 MEDIA 表再走客户端 FDID）',",
        "    ck('★★ 地图页顶部工具栏卡：卡高 + 间距 + 地图高 == 可用高（尺寸解耦）',\n"
        "       'M.MAP_H = M.FRAME_H - M.HDR_CARD_H - M.HDR_GAP' in _mu\n"
        "       and 'M.MAP_W = math.floor(M.MAP_H * M.ART_W / M.ART_H)' in _mu)\n"
        "    ck('★★ 奥巢 hero/卡面美术 = 插件自带 TGA（ArtOf 先查 MEDIA 表再走客户端 FDID）',",
        1,
    ),
]


def run(path, subs, label):
    raw = open(path, 'rb').read()
    text = raw
    fails = 0
    for old, new, want in subs:
        ob = old.encode('utf-8')
        nb = new.encode('utf-8')
        n = text.count(ob)
        if n != want:
            print('  FAIL hits=%d expect=%d : %s' % (n, want, old[:60].replace('\n', '\\n')))
            fails += 1
            continue
        if CHECK_ONLY:
            print('  ok   hits=%d : %s' % (n, old[:60].replace('\n', '\\n')))
            continue
        text = text.replace(ob, nb, 1)
        print('  OK   %s' % old[:60].replace('\n', '\\n'))
    if fails:
        print('[%s] %d anchor(s) FAILED' % (label, fails))
        return fails
    if CHECK_ONLY:
        print('[%s] all anchors ok (dry-run)' % label)
        return 0
    if text == raw:
        print('[%s] nothing changed' % label)
        return 0
    open(path, 'wb').write(text)
    print('[%s] written %d bytes' % (label, len(text)))
    return 0


fails = 0
fails += run(MAP, MAP_SUBS, 'MapUI')
fails += run(CHK, CHK_SUBS, 'df_dungeon_check')
sys.exit(1 if fails else 0)
