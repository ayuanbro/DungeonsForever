# -*- coding: utf-8 -*-
"""五人本任务页二次改造（2026-10-13）：
  1) 删「未完成/已完成」筛选按钮 → 改 iOS 开关「显示已完成」（默认开）
  2) 删左列行强调条 r.bar（§6 强调条全删）
  3) 「前置」改行内小卡片 + 新增「可共享」小卡片（紧贴任务名右侧）
  4) 第二列只显示大地图名（去坐标 + 去子区域）
字节级替换，保持 CRLF。
"""
import io
import sys

PATH = r"D:\workspace\DungeonsForever\Core\DungeonUI.lua"
CRLF = "\r\n"


def main():
    raw = io.open(PATH, "rb").read()
    txt = raw.decode("utf-8")
    assert "\r\n" in txt, "文件应为 CRLF"

    edits = []

    # ── A. 常量区：列位重排 + badge 常量 ───────────────────────────────
    edits.append((
        [
            "DG.Q_X_LOC = 200",
            "DG.Q_X_LV = 348",
            "DG.Q_X_PRE = 416",
            "DG.Q_W_NAME = 164",
            "DG.Q_W_LOC = 144",
        ],
        [
            "DG.Q_X_LOC = 288",
            "DG.Q_X_LV = 386",
            "DG.Q_W_NAME = 150",
            "DG.Q_W_LOC = 90",
            "DG.Q_BADGE_H = 20",
            "DG.Q_BADGE_GAP = 4",
            "DG.Q_BADGE_PAD = 5",
            "DG.Q_BADGE_FS = 14",
        ],
    ))

    # ── B. 删 Q_BAR_W 常量 ────────────────────────────────────────────
    edits.append((
        [
            "DG.C_FAC_H = { 1, 0.40, 0.40 }",
            "DG.Q_BAR_W = 3",
        ],
        [
            "DG.C_FAC_H = { 1, 0.40, 0.40 }",
        ],
    ))

    # ── G. 新增助手（插在 DG.QClassChar 之后）─────────────────────────
    edits.append((
        [
            "function DG.QClassChar(cls)",
            "    local first = string.match(cls or \"\", \"^([^/]+)\")",
            "    return DG.QCLASS_CHAR[first]",
            "end",
        ],
        [
            "function DG.QClassChar(cls)",
            "    local first = string.match(cls or \"\", \"^([^/]+)\")",
            "    return DG.QCLASS_CHAR[first]",
            "end",
            "",
            "function DG.QuestShare(id)",
            "    return (ns.DungeonQuestShare and ns.DungeonQuestShare[id]) and true or false",
            "end",
            "",
            "function DG.QuestMapName(s)",
            "    if not s or s == \"\" then return s end",
            "    s = s:gsub(\"%s*[%d%.]+%s*,%s*[%d%.]+%s*$\", \"\")",
            "    s = s:gsub(\"%s*%-%s*[^%-]*$\", \"\")",
            "    return s",
            "end",
            "",
            "function DG.MakeBadge(parent)",
            "    local b = CreateFrame(\"Frame\", nil, parent, \"BackdropTemplate\")",
            "    b:SetSize(10, DG.Q_BADGE_H)",
            "    if not HuiCardFX(b, nil, 3) then",
            "        b:SetBackdrop({",
            "            bgFile = \"Interface\\\\Buttons\\\\WHITE8x8\",",
            "            edgeFile = \"Interface\\\\Buttons\\\\WHITE8x8\",",
            "            edgeSize = 1,",
            "        })",
            "        b:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)",
            "        b:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)",
            "    end",
            "    b.lab = MakeFS(b, DG.Q_BADGE_FS, C_TEXT, \"CENTER\")",
            "    b.lab:SetPoint(\"CENTER\", b, \"CENTER\", 0, 0)",
            "    b:Hide()",
            "    return b",
            "end",
            "",
            "function DG.PlaceBadge(b, x, text)",
            "    b.lab:SetText(text)",
            "    local w = (b.lab:GetStringWidth() or 20) + DG.Q_BADGE_PAD * 2",
            "    b:SetWidth(w)",
            "    b:ClearAllPoints()",
            "    b:SetPoint(\"TOPLEFT\", b:GetParent(), \"TOPLEFT\", x, -(DG.Q_ROW_H - DG.Q_BADGE_H) / 2)",
            "    b:Show()",
            "    return x + w + DG.Q_BADGE_GAP",
            "end",
        ],
    ))

    # ── D. 任务行创建：删 r.bar；r.pre → 两个 badge ───────────────────
    edits.append((
        [
            "            r.bar = r:CreateTexture(nil, \"ARTWORK\")",
            "            r.bar:SetPoint(\"TOPLEFT\", r, \"TOPLEFT\", 0, 0)",
            "            r.bar:SetPoint(\"BOTTOMLEFT\", r, \"BOTTOMLEFT\", 0, 0)",
            "            r.bar:SetWidth(DG.Q_BAR_W)",
            "            r.em = r:CreateTexture(nil, \"ARTWORK\")",
        ],
        [
            "            r.em = r:CreateTexture(nil, \"ARTWORK\")",
        ],
    ))
    edits.append((
        [
            "            r.pre = MakeFS(r, 14, C_GREY, \"LEFT\")",
            "            r.pre:SetPoint(\"TOPLEFT\", r, \"TOPLEFT\", DG.Q_X_PRE, -(DG.Q_ROW_H - 14) / 2 - 1)",
            "            r.pre:SetText(L[\"前置\"])",
        ],
        [
            "            r.preB = DG.MakeBadge(r)",
            "            r.shareB = DG.MakeBadge(r)",
        ],
    ))

    # ── E. 行填充：删 bar 上色 ────────────────────────────────────────
    edits.append((
        [
            "                local nm, hasName = DG.QuestName(q[1])",
            "                r.bar:SetColorTexture(col[1], col[2], col[3], 1)",
            "                r.bar:Show()",
        ],
        [
            "                local nm, hasName = DG.QuestName(q[1])",
        ],
    ))

    # ── F. 第二列只显示大地图名 ───────────────────────────────────────
    edits.append((
        [
            "                if loc == \"\" and q[8] then loc = L[\"副本内\"] end",
            "                r.sub:SetText(loc)",
        ],
        [
            "                if loc == \"\" and q[8] then loc = L[\"副本内\"] end",
            "                r.sub:SetText(DG.QuestMapName(loc))",
        ],
    ))

    # ── H. 前置/可共享小卡片上字 ─────────────────────────────────────
    edits.append((
        [
            "                if (q[7] or q[9]) and hasName then",
            "                    r.pre:Show()",
            "                else",
            "                    r.pre:Hide()",
            "                end",
        ],
        [
            "                local bx = DG.Q_X_NAME + (clsChar and 14 or 0)",
            "                       + math.min(r.name:GetStringWidth() or 0, DG.Q_W_NAME - (clsChar and 14 or 0)) + DG.Q_BADGE_GAP",
            "                if hasName and (q[7] or q[9]) then",
            "                    bx = DG.PlaceBadge(r.preB, bx, L[\"前置\"])",
            "                else",
            "                    r.preB:Hide()",
            "                end",
            "                if hasName and DG.QuestShare(q[1]) then",
            "                    DG.PlaceBadge(r.shareB, bx, L[\"可共享\"])",
            "                else",
            "                    r.shareB:Hide()",
            "                end",
        ],
    ))

    # ── I. 建开关（BuildDetailFilterRow 尾部）────────────────────────
    edits.append((
        [
            "        U.dungeonFilterBtns[i] = bt",
            "    end",
            "    DG.RefreshFilterRow()",
        ],
        [
            "        U.dungeonFilterBtns[i] = bt",
            "    end",
            "    if not U.dungeonQDoneTg then",
            "        local tg = CreateFrame(\"CheckButton\", nil, detail)",
            "        tg:SetSize(36, 20)",
            "        tg:EnableMouse(true)",
            "        if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(tg) end",
            "        tg.label = MakeFS(detail, 14, C_TEXT, \"LEFT\")",
            "        tg.label:SetPoint(\"LEFT\", tg, \"RIGHT\", 6, 0)",
            "        tg.label:SetText(L[\"显示已完成\"])",
            "        tg:SetScript(\"OnClick\", function(self)",
            "            U:SetQuestShowDone(self:GetChecked() and true or false)",
            "        end)",
            "        U.dungeonQDoneTg = tg",
            "    end",
            "    DG.RefreshFilterRow()",
        ],
    ))

    # ── J. ApplyDetailChrome：开关显隐 + 位置 ────────────────────────
    edits.append((
        [
            "    if isQuest and U.dungeonQPlateL then",
            "        local plateL = U.dungeonQPlateL",
            "        for i = 1, #(U.dungeonFilterBtns or {}) do",
            "            local bt = U.dungeonFilterBtns[i]",
            "            if bt then",
            "                bt:ClearAllPoints()",
            "                bt:SetPoint(\"TOPLEFT\", plateL, \"TOPLEFT\", DG.Q_PAD + (i - 1) * 100, -DG.Q_PAD)",
            "                bt:SetFrameLevel(plateL:GetFrameLevel() + 5)",
            "            end",
            "        end",
        ],
        [
            "    if isQuest and U.dungeonQPlateL then",
            "        local plateL = U.dungeonQPlateL",
            "        for i = 1, #(U.dungeonFilterBtns or {}) do",
            "            local bt = U.dungeonFilterBtns[i]",
            "            if bt then",
            "                bt:ClearAllPoints()",
            "                bt:SetPoint(\"TOPLEFT\", plateL, \"TOPLEFT\", DG.Q_PAD + (i - 1) * 100, -DG.Q_PAD)",
            "                bt:SetFrameLevel(plateL:GetFrameLevel() + 5)",
            "            end",
            "        end",
            "        if U.dungeonQDoneTg then",
            "            U.dungeonQDoneTg:ClearAllPoints()",
            "            U.dungeonQDoneTg:SetPoint(\"TOPLEFT\", plateL, \"TOPLEFT\", DG.Q_PAD + 3 * 100, -DG.Q_PAD - 2)",
            "            U.dungeonQDoneTg:SetFrameLevel(plateL:GetFrameLevel() + 5)",
            "        end",
        ],
    ))

    # ── K. RenderDungeonQuests：4/5 号按钮隐藏 ───────────────────────
    edits.append((
        [
            "    for i = 1, #(U.dungeonFilterBtns or {}) do",
            "        local bt = U.dungeonFilterBtns[i]",
            "        if bt then",
            "            local key, label, n",
            "            if i == 1 then key, label, n = \"qall\", DG.QSIDE_LABEL.all, cnt.all",
            "            elseif i == 2 then key, label, n = \"A\", DG.QSIDE_LABEL.A, cnt.A",
            "            elseif i == 3 then key, label, n = \"H\", DG.QSIDE_LABEL.H, cnt.H",
            "            elseif i == 4 then key, label, n = \"todo\", DG.QFILTER_LABEL.todo, cnt.todo",
            "            else key, label, n = \"done\", DG.QFILTER_LABEL.done, cnt.done end",
            "            bt.__mode, bt.__key = \"quest\", key",
        ],
        [
            "    for i = 1, #(U.dungeonFilterBtns or {}) do",
            "        local bt = U.dungeonFilterBtns[i]",
            "        if bt and i > 3 then",
            "            bt.__mode, bt.__key = \"quest\", nil",
            "            bt:Hide()",
            "            if bt.__em then bt.__em:Hide() end",
            "        elseif bt then",
            "            local key, label, n",
            "            if i == 1 then key, label, n = \"qall\", DG.QSIDE_LABEL.all, cnt.all",
            "            elseif i == 2 then key, label, n = \"A\", DG.QSIDE_LABEL.A, cnt.A",
            "            else key, label, n = \"H\", DG.QSIDE_LABEL.H, cnt.H end",
            "            bt.__mode, bt.__key = \"quest\", key",
        ],
    ))

    # ── L. 开关状态同步（渲染尾部）──────────────────────────────────
    edits.append((
        [
            "    U.dungeonQuestSum:SetText(format(L[\"已完成 %d / %d\"], doneVis, nVis) .. seg)",
            "    U.dungeonQuestSum:Hide()",
        ],
        [
            "    U.dungeonQuestSum:SetText(format(L[\"已完成 %d / %d\"], doneVis, nVis) .. seg)",
            "    U.dungeonQuestSum:Hide()",
            "    if U.dungeonQDoneTg then U.dungeonQDoneTg:SetChecked(status ~= \"todo\") end",
        ],
    ))

    # ── M. SetQuestShowDone ──────────────────────────────────────────
    edits.append((
        [
            "function U:SetQuestSide(key)",
        ],
        [
            "function U:SetQuestShowDone(on)",
            "    U.dungeonQFilter = on and \"all\" or \"todo\"",
            "    DB().dungeonQuestFilter = (U.dungeonQFilter ~= \"all\") and U.dungeonQFilter or nil",
            "    U:RenderDungeonQuests()",
            "end",
            "",
            "function U:SetQuestSide(key)",
        ],
    ))

    # ── N. 存档初始化归一化 ──────────────────────────────────────────
    edits.append((
        [
            "    U.dungeonQFilter = DB().dungeonQuestFilter or \"all\"",
        ],
        [
            "    U.dungeonQFilter = DB().dungeonQuestFilter or \"all\"",
            "    if U.dungeonQFilter == \"done\" then U.dungeonQFilter = \"all\" end",
        ],
    ))

    for i, (old_lines, new_lines) in enumerate(edits):
        old = CRLF.join(old_lines)
        new = CRLF.join(new_lines)
        n = txt.count(old)
        if n != 1:
            print("EDIT %d: 命中 %d 次（应为 1）" % (i, n))
            for l in old_lines:
                print("   |", l)
            sys.exit(1)
        txt = txt.replace(old, new)

    out = txt.encode("utf-8")
    io.open(PATH, "wb").write(out)
    crlf = out.count(b"\r\n")
    lone = out.count(b"\n") - crlf
    print("OK 写入 %d 字节，CRLF=%d, 裸LF=%d" % (len(out), crlf, lone))


if __name__ == "__main__":
    main()
