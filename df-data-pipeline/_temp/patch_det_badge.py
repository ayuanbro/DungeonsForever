import sys

DF = r"D:\workspace\DungeonsForever\Core\DungeonUI.lua"
d = open(DF, "rb").read()
print("CRLF", d.count(b"\r\n"), "bareLF", d.count(b"\n") - d.count(b"\r\n"))

PAIRS = [
    # ---- A) 文案：前导任务 → 前置任务 ----
    (b'            f:SetText(L["\xe5\x89\x8d\xe5\xaf\xbc\xe4\xbb\xbb\xe5\x8a\xa1"])\r\n',
     b'            f:SetText(L["\xe5\x89\x8d\xe7\xbd\xae\xe4\xbb\xbb\xe5\x8a\xa1"])\r\n'),

    # ---- B) 徽章底色常量 ----
    (b'DG.Q_BADGE_FS = 14\r\n',
     b'DG.Q_BADGE_FS = 14\r\n'
     b'DG.Q_BADGE_PRE_BG = { 0.78, 0.60, 0.10, 1 }\r\n'
     b'DG.Q_BADGE_SHARE_BG = { 0.16, 0.52, 0.26, 1 }\r\n'),

    # ---- C) 可共享判定改走客户端共享数据 ----
    (b'function DG.QuestShare(id)\r\n'
     b'    return (ns.DungeonQuestShare and ns.DungeonQuestShare[id]) and true or false\r\n'
     b'end\r\n',
     b'function DG.QuestShare(id)\r\n'
     b'    if not id then return false end\r\n'
     b'    local v = DG.QLCall("IsPushableQuest", id)\r\n'
     b'    if v ~= nil then return v == true end\r\n'
     b'    return (ns.DungeonQuestShare and ns.DungeonQuestShare[id]) and true or false\r\n'
     b'end\r\n'),

    # ---- D) MakeBadge 支持底色 + 白字 ----
    (b'function DG.MakeBadge(parent)\r\n'
     b'    local b = CreateFrame("Frame", nil, parent, "BackdropTemplate")\r\n'
     b'    b:SetSize(10, DG.Q_BADGE_H)\r\n'
     b'    if not HuiCardFX(b, nil, 3) then\r\n'
     b'        b:SetBackdrop({\r\n'
     b'            bgFile = "Interface\\\\Buttons\\\\WHITE8x8",\r\n'
     b'            edgeFile = "Interface\\\\Buttons\\\\WHITE8x8",\r\n'
     b'            edgeSize = 1,\r\n'
     b'        })\r\n'
     b'        b:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)\r\n'
     b'        b:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)\r\n'
     b'    end\r\n'
     b'    b.lab = MakeFS(b, DG.Q_BADGE_FS, C_TEXT, "CENTER")\r\n',
     b'function DG.MakeBadge(parent, bg)\r\n'
     b'    local b = CreateFrame("Frame", nil, parent, "BackdropTemplate")\r\n'
     b'    b:SetSize(10, DG.Q_BADGE_H)\r\n'
     b'    local painted = false\r\n'
     b'    if IsHui() and ns.hui and ns.hui.BuildRoundedBG then\r\n'
     b'        local fill, border = ns.hui.BuildRoundedBG(b, 6, bg or ns.hui.layer.L3, "both", true, 1)\r\n'
     b'        b.__huiCard = { fill = fill, border = border }\r\n'
     b'        painted = true\r\n'
     b'    end\r\n'
     b'    if not painted then\r\n'
     b'        b:SetBackdrop({\r\n'
     b'            bgFile = "Interface\\\\Buttons\\\\WHITE8x8",\r\n'
     b'            edgeFile = "Interface\\\\Buttons\\\\WHITE8x8",\r\n'
     b'            edgeSize = 1,\r\n'
     b'        })\r\n'
     b'        b:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)\r\n'
     b'        b:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)\r\n'
     b'    end\r\n'
     b'    b.lab = MakeFS(b, DG.Q_BADGE_FS, C_WHITE, "CENTER")\r\n'),

    # ---- E) 两枚徽章带底色创建 ----
    (b'            r.preB = DG.MakeBadge(r)\r\n'
     b'            r.shareB = DG.MakeBadge(r)\r\n',
     b'            r.preB = DG.MakeBadge(r, DG.Q_BADGE_PRE_BG)\r\n'
     b'            r.shareB = DG.MakeBadge(r, DG.Q_BADGE_SHARE_BG)\r\n'),

    # ---- F) 详情节点行删左强调条 + 内衬 10→8 ----
    (b'            r.bar = r:CreateTexture(nil, "ARTWORK")\r\n'
     b'            r.bar:SetPoint("TOPLEFT", r, "TOPLEFT", 0, 0)\r\n'
     b'            r.bar:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 0, 0)\r\n'
     b'            r.bar:SetWidth(3)\r\n'
     b'            r.name = MakeFS(r, 14, C_TEXT, "LEFT")\r\n'
     b'            r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 10, -3)\r\n',
     b'            r.name = MakeFS(r, 14, C_TEXT, "LEFT")\r\n'
     b'            r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -3)\r\n'),

    (b'            r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 10, -21)\r\n',
     b'            r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -21)\r\n'),

    # ---- G) 删掉三处节点行条上色 ----
    (b'                    r.bar:SetColorTexture(pcol[1], pcol[2], pcol[3], 1)\r\n', b''),
    (b'                    r.bar:SetColorTexture(0.43, 0.4, 0.32, 1)\r\n', b''),
    (b'                r.bar:SetColorTexture(fcol[1], fcol[2], fcol[3], 1)\r\n', b''),
]

for i, (old, new) in enumerate(PAIRS):
    c = d.count(old)
    print("  #%d 命中 %d" % (i, c))
    if c != 1:
        print("     old=", old[:90])
        sys.exit(1)
    d = d.replace(old, new)

open(DF, "wb").write(d)
print("写回 OK；CRLF", d.count(b"\r\n"), "bareLF", d.count(b"\n") - d.count(b"\r\n"))
