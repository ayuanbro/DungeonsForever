# -*- coding: utf-8 -*-
"""任务行：左侧阵营标识改自制品图标 + 职业改行内职业色小卡片（白字，排在任务名右侧）。

用法：python patch_quest_cls_badge.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
SRC = os.path.join(DF, 'Core', 'DungeonUI.lua')

d = open(SRC, 'rb').read()
assert d.count(b'\r\n') > 1000 and d.count(b'\n') == d.count(b'\r\n'), 'CRLF 基准异常'
n0 = len(d)


def sub(old, new, tag):
    global d
    ob = old.replace('\n', '\r\n').encode('utf-8')
    nb = new.replace('\n', '\r\n').encode('utf-8')
    c = d.count(ob)
    if c != 1:
        sys.exit('HIT-MISS[%s]: count=%d' % (tag, c))
    d = d.replace(ob, nb, 1)
    print('  [ok] %s' % tag)


# ------------------------------------------------------------------ B1 常量
sub('''DG.QCLASS_TOKEN = {''',
    '''DG.QCLASS_DIM = 0.78
DG.QCLASS_TOKEN = {''', 'B1a QCLASS_DIM')

# ------------------------------------------------------------------ B1 助手
sub('''DG.QCLASS_CHAR = {
    [ns.DL("战士")] = L["战"], [ns.DL("圣骑士")] = L["骑"], [ns.DL("猎人")] = L["猎"], [ns.DL("盗贼")] = L["盗"], [ns.DL("牧师")] = L["牧"],
    [ns.DL("萨满")] = L["萨"], [ns.DL("法师")] = L["法"], [ns.DL("术士")] = L["术"], [ns.DL("德鲁伊")] = L["德"],
}
function DG.QClassColor(cls)
    local t = RAID_CLASS_COLORS and RAID_CLASS_COLORS[DG.QCLASS_TOKEN[cls] or ""]
    if t and t.r then return { t.r, t.g, t.b } end
    return C_GOLD
end
function DG.QClassChar(cls)
    local first = string.match(cls or "", "^([^/]+)")
    return DG.QCLASS_CHAR[first]
end''',
    '''function DG.QClassColor(cls)
    local t = RAID_CLASS_COLORS and RAID_CLASS_COLORS[DG.QCLASS_TOKEN[cls] or ""]
    if t and t.r then return { t.r, t.g, t.b } end
    return C_GOLD
end
function DG.QClassFill(cls)
    local c = DG.QClassColor(cls)
    return { c[1] * DG.QCLASS_DIM, c[2] * DG.QCLASS_DIM, c[3] * DG.QCLASS_DIM, 1 }
end
function DG.QClassList(cls)
    if not cls or cls == "" then return nil end
    local s = string.gsub(string.gsub(cls, "\u3001", "/"), ",", "/")
    local out = {}
    for seg in string.gmatch(s, "[^/]+") do
        seg = string.gsub(seg, "^%s*(.-)%s*$", "%1")
        if seg ~= "" then out[#out + 1] = seg end
    end
    if #out == 0 then return nil end
    return out
end
function DG.QClassLabel(cls)
    if not cls or cls == "" then return nil end
    local nm = L[cls] or cls
    if DG.QCLASS_TOKEN[cls] == "PALADIN" then
        nm = string.gsub(nm, "^\u5723", "")
        nm = string.gsub(nm, "^\u8056", "")
    end
    return nm
end''', 'B1b QClassLabel/Fill/List')

# ------------------------------------------------------------------ B2 徽章常量
sub('''DG.Q_BADGE_DY = 2
DG.Q_BADGE_FS = 12''',
    '''DG.Q_BADGE_DY = 2
DG.Q_BADGE_FS = 12
DG.Q_BADGE_CLS_BG = { 0.30, 0.30, 0.34, 1 }''', 'B2 Q_BADGE_CLS_BG')

# ------------------------------------------------------------------ B3 徽章助手
sub('''function DG.QuestState(id)''',
    '''function DG.BadgeTint(b, col)
    if not (b and col) then return end
    local fill = b.__huiCard and b.__huiCard.fill
    if fill then
        for i = 1, #fill do
            local t = fill[i]
            if t and t.__huiGlass and ns.hui and ns.hui.GlassPaint then
                t.__huiGlass.c = col
                ns.hui.GlassPaint(t)
            end
        end
    elseif b.SetBackdropColor then
        b:SetBackdropColor(col[1], col[2], col[3], 1)
    end
end

function DG.ClsBadgeAt(r, i)
    r.clsB = r.clsB or {}
    local b = r.clsB[i]
    if not b then
        b = DG.MakeBadge(r, DG.Q_BADGE_CLS_BG)
        r.clsB[i] = b
    end
    return b
end

function DG.QuestState(id)''', 'B3 BadgeTint/ClsBadgeAt')

# ------------------------------------------------------------------ B4 落点守卫
sub('''function DG.PlaceBadge(b, x, text)
    b.lab:SetText(text)
    local w = (b.lab:GetStringWidth() or 20) + DG.Q_BADGE_PAD * 2
    b:SetWidth(w)''',
    '''function DG.PlaceBadge(b, x, text, maxX)
    b.lab:SetText(text)
    local w = (b.lab:GetStringWidth() or 20) + DG.Q_BADGE_PAD * 2
    if maxX and x + w > maxX then
        b:Hide()
        return x
    end
    b:SetWidth(w)''', 'B4 PlaceBadge maxX')

# ------------------------------------------------------------------ B5 阵营贴图探测退役
sub('''DG.__facTex = {}
function DG.FactionTex(side)
    if side ~= "A" and side ~= "H" then return nil end
    if DG.__facTex[side] == nil then
        local p = "Interface\\\\PVPFrame\\\\PVP-Capture" .. (side == "A" and "Alliance" or "Horde")
        local ok = false
        if type(GetFileIDFromPath) == "function" then
            local ok2, fid = pcall(GetFileIDFromPath, p)
            ok = (ok2 and type(fid) == "number" and fid > 0) or false
        end
        DG.__facTex[side] = ok and p or false
    end
    return DG.__facTex[side] or nil
end
function DG.FactionLetter(side)
    if side == "A" then return L["盟"] end
    if side == "H" then return L["部"] end
    return nil
end

''', '', 'B5 退役 FactionTex/FactionLetter')

# ------------------------------------------------------------------ B6 行创建
sub('''            r.emL = MakeFS(r, 14, C_GREY, "LEFT")
            r.emL:SetPoint("TOPLEFT", r, "TOPLEFT", 13, -(DG.Q_ROW_H - 14) / 2 - 1)
            r.cls = MakeFS(r, 14, C_GREY, "LEFT")
            r.cls:SetPoint("TOPLEFT", r, "TOPLEFT", 30, -(DG.Q_ROW_H - 14) / 2 - 1)
''', '', 'B6 删 r.emL / r.cls')

# ------------------------------------------------------------------ B7 行填充
sub('''                local ftex = q[2] and DG.FactionTex(q[2]) or nil
                if ftex then
                    r.em:SetTexture(ftex)
                    r.em:Show()
                    r.emL:Hide()
                else
                    r.em:Hide()
                    local lt = q[2] and DG.FactionLetter(q[2]) or nil
                    if lt then
                        r.emL:SetText(lt)
                        r.emL:SetTextColor(Unpack(q[2] == "A" and DG.C_FAC_A or DG.C_FAC_H))
                        r.emL:Show()
                    else
                        r.emL:Hide()
                    end
                end
                local clsChar = q[15] and DG.QClassChar(q[15]) or nil
                if clsChar then
                    r.cls:SetText(clsChar)
                    r.cls:SetTextColor(Unpack(DG.QClassColor(q[15])))
                    r.cls:Show()
                    r.name:ClearAllPoints()
                    r.name:SetPoint("TOPLEFT", r, "TOPLEFT", DG.Q_X_NAME + 14, -(DG.Q_ROW_H - DG.Q_FS_NAME) / 2 - 1)
                    r.name:SetWidth(DG.Q_W_NAME - 14)
                else
                    r.cls:Hide()
                    r.name:ClearAllPoints()
                    r.name:SetPoint("TOPLEFT", r, "TOPLEFT", DG.Q_X_NAME, -(DG.Q_ROW_H - DG.Q_FS_NAME) / 2 - 1)
                    r.name:SetWidth(DG.Q_W_NAME)
                end''',
    '''                local ftex = q[2] and DG.Q_FAC_ICON[q[2]] or nil
                if ftex then
                    r.em:SetTexture(ftex)
                    r.em:Show()
                else
                    r.em:Hide()
                end
                local clsList = DG.QClassList(q[15])''', 'B7 阵营图标 + 职业清单')

# ------------------------------------------------------------------ B8 徽章链
sub('''                local bx = DG.Q_X_NAME + (clsChar and 14 or 0)
                       + math.min(r.name:GetStringWidth() or 0, DG.Q_W_NAME - (clsChar and 14 or 0)) + DG.Q_BADGE_GAP
                if hasName and (q[7] or q[9]) then
                    bx = DG.PlaceBadge(r.preB, bx, L["前置"])
                else
                    r.preB:Hide()
                end
                if hasName and DG.QuestShare(q[1]) then
                    DG.PlaceBadge(r.shareB, bx, L["可共享"])
                else
                    r.shareB:Hide()
                end''',
    '''                local bmax = DG.Q_X_LOC - 4
                local bx = DG.Q_X_NAME + math.min(r.name:GetStringWidth() or 0, DG.Q_W_NAME) + DG.Q_BADGE_GAP
                local ci = 0
                if hasName and clsList then
                    for k = 1, #clsList do
                        local cnm = DG.QClassLabel(clsList[k])
                        if cnm then
                            ci = ci + 1
                            local cb = DG.ClsBadgeAt(r, ci)
                            DG.BadgeTint(cb, DG.QClassFill(clsList[k]))
                            bx = DG.PlaceBadge(cb, bx, cnm, bmax)
                        end
                    end
                end
                local cbs = r.clsB
                if cbs then for k = ci + 1, #cbs do cbs[k]:Hide() end end
                if hasName and (q[7] or q[9]) then
                    bx = DG.PlaceBadge(r.preB, bx, L["前置"], bmax)
                else
                    r.preB:Hide()
                end
                if hasName and DG.QuestShare(q[1]) then
                    DG.PlaceBadge(r.shareB, bx, L["可共享"], bmax)
                else
                    r.shareB:Hide()
                end''', 'B8 徽章链（职业→前置→可共享）')

open(SRC, 'wb').write(d)
print('写入 %s：%d → %d 字节（%+d）' % (SRC, n0, len(d), len(d) - n0))
assert d.count(b'\n') == d.count(b'\r\n'), '行尾被破坏'
print('行尾复核：CRLF 全部一致')
