# -*- coding: utf-8 -*-
"""军衔页两列卡片重构补丁（全锚点断言，任一失败即中止不写盘）
R1 双卡片容器插入 | R2 军衔行重构 | R3 wkRows/capHead/capNote 行池
R4a/R4b HideAll 补隐藏 | R5 RenderRanks 整体替换 | R6 三语 locale 补键
"""
import re, json, glob, os, shutil, sys

SRC = "Core/PvPUI.lua"
BAK = "_temp/_bak_PvPUI_2col.lua"
REPORT = "_temp/patch_ranks_2col_report.json"

src = open(SRC, encoding="utf-8", errors="strict").read()
orig_len = len(src)
rep = {"steps": [], "ok": False, "errors": []}

def count(s, sub):
    return s.count(sub)

def must(s, sub, step, n=1):
    c = count(s, sub)
    if c != n:
        rep["errors"].append(f"{step}: anchor count {c} != {n}: {sub[:70]!r}")
        return False
    return True

def replace_slice(s, start_anchor, end_anchor, new_text, step, sanity=None):
    """替换 [start_anchor 起点, end_anchor 起点) 区间（end_anchor 保留）"""
    i = s.find(start_anchor)
    j = s.find(end_anchor)
    if i < 0 or j < 0 or i >= j:
        rep["errors"].append(f"{step}: slice anchors bad (i={i}, j={j})")
        return None
    if sanity and sanity not in s[i:j]:
        rep["errors"].append(f"{step}: sanity missing in slice")
        return None
    return s[:i] + new_text + s[j:]

# ---------- R1: 双卡片容器（插在 scroll/child 建好之后、芯片池之前） ----------
A_R1 = '    PV.scroll, PV.child = scroll, child\n'
R1_NEW = A_R1 + '''    -- ★★ 军衔页双卡片容器（左「军衔」/ 右「每周上限」，2026-10-08 反馈：卡片倒圆角）：
    --   圆角底复用套装卡的 ns.hui.BuildRoundedBG（radius 4 / layer L3 / both），
    --   离线桩（ns.hui 不在）走平铺底+描边兜底。先建卡片再建行池/芯片/列头，
    --   同层后建者后画 → 行与芯片必然盖在卡片底之上（帧数纪律：全部 Build 期建）。
    local function NewRoundCard(w, h)
        local f = CreateFrame("Frame", nil, child)
        f:SetSize(w, h)
        local layer = ns.hui and ns.hui.layer
        if ns.hui and ns.hui.BuildRoundedBG and layer then
            ns.hui.BuildRoundedBG(f, 4, layer.L3, "both", true, 1)
        else
            f.edge = f:CreateTexture(nil, "BACKGROUND")
            f.edge:SetAllPoints(f)
            f.edge:SetColorTexture(1, 1, 1, 0.10)
            f.bg = f:CreateTexture(nil, "BACKGROUND", nil, 1)
            f.bg:SetPoint("TOPLEFT", f, "TOPLEFT", 1, -1)
            f.bg:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -1, 1)
            f.bg:SetColorTexture(0x36 / 255, 0x36 / 255, 0x36 / 255, 1)
        end
        return f
    end
    PV.rankCard = NewRoundCard(500, 536)
    PV.capCard = NewRoundCard(PV.W - 512, 536)
'''

# ---------- R2: 军衔行池重构（徽章 + 单军衔名 + 点数/累计 + more 记数） ----------
A_R2_START = '    for i = 1, 14 do\n        local r = CreateFrame("Button", nil, child)\n        r:SetSize(PV.W, PV.ROW_H)'
A_R2_END = '        PV.rankRows[i] = r\n    end'
R2_NEW = '''    -- ★★ 军衔行（两列布局左卡）：徽章贴图 + 按阵营单军衔名（去 nameA/slash/nameH
    --   三件套）+ 点数/累计 + 独立奖励列（芯片由 RenderRanks 锚到行右侧，行内只留
    --   +N 记数）。行宽 476 于 500 卡内 12px 内边距；行高 34 × 14 行 = 530 恰好一屏。
    for i = 1, 14 do
        local r = CreateFrame("Button", nil, child)
        r:SetSize(476, 34)
        r.badge = r:CreateTexture(nil, "ARTWORK")
        r.badge:SetSize(24, 24)
        r.badge:SetPoint("TOPLEFT", r, "TOPLEFT", 0, -5)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.badge) end
        r.name = MakeFS(r, 13, C_GOLD, "LEFT")
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 32, -9)
        r.name:SetWidth(152)
        r.name:SetWordWrap(false)
        r.pts = MakeFS(r, 12, C_TEXT, "RIGHT")
        r.pts:SetPoint("TOPRIGHT", r, "TOPLEFT", 288, -9)
        r.cum = MakeFS(r, 12, C_GREY, "RIGHT")
        r.cum:SetPoint("TOPRIGHT", r, "TOPLEFT", 360, -9)
        r.more = MakeFS(r, 11, C_GREY, "LEFT")
        r.more:SetPoint("TOPLEFT", r, "TOPLEFT", 458, -11)
        r.more:SetWordWrap(false)
        r.sep = r:CreateTexture(nil, "BACKGROUND")
        r.sep:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 0, 0)
        r.sep:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", 0, 0)
        r.sep:SetHeight(1)
        r.sep:SetColorTexture(1, 1, 1, 0.06)
        ForwardWheel(r)'''

# ---------- R3: 右卡行池 + 列头 + 注释行（插在 capRows 池之后） ----------
A_R3 = '        PV.capRows[i] = r\n    end\n'
R3_NEW = A_R3 + '''    -- ★★ 军衔页右卡「每周上限」行池（独立于本周页 capRows 双列网格，RenderWeek
    --   零改动、两条闸互不干扰）：周标签 / 军衔名全部 SetWordWrap(false)，
    --   「第 10 周」「R14 高阶督军」保证单行不折行（用户点名）。增量为项目绿。
    PV.wkRows = {}
    for i = 1, 10 do
        local r = CreateFrame("Frame", nil, child)
        r:SetSize(400, 44)
        r.week = MakeFS(r, 12, C_GREY, "LEFT")
        r.week:SetPoint("TOPLEFT", r, "TOPLEFT", 0, -13)
        r.week:SetWordWrap(false)
        r.badge = r:CreateTexture(nil, "ARTWORK")
        r.badge:SetSize(20, 20)
        r.badge:SetPoint("TOPLEFT", r, "TOPLEFT", 62, -12)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.badge) end
        r.rank = MakeFS(r, 12, C_GOLD, "LEFT")
        r.rank:SetPoint("TOPLEFT", r, "TOPLEFT", 88, -13)
        r.rank:SetWordWrap(false)
        r.cum = MakeFS(r, 12, C_TEXT, "RIGHT")
        r.cum:SetPoint("TOPRIGHT", r, "TOPLEFT", 312, -13)
        r.inc = MakeFS(r, 12, C_GREY, "RIGHT")
        r.inc:SetPoint("TOPRIGHT", r, "TOPLEFT", 388, -13)
        r.inc:SetTextColor(0.27, 0.75, 0.45, 1)
        r.sep = r:CreateTexture(nil, "BACKGROUND")
        r.sep:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 0, 0)
        r.sep:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", 0, 0)
        r.sep:SetHeight(1)
        r.sep:SetColorTexture(1, 1, 1, 0.06)
        ForwardWheel(r)
        PV.wkRows[i] = r
    end

    -- 右卡列头四枚 + 注释行：不进 secSpecs（fs=11 分支会按整页宽 SetWidth），
    --   单独建并按卡内 400 定宽；挂进 PV.labels 让 HideAll 统一收。
    PV.capHead = {
        week = MakeFS(child, 11, C_GREY, "LEFT"),
        rank = MakeFS(child, 11, C_GREY, "LEFT"),
        cum = MakeFS(child, 11, C_GREY, "RIGHT"),
        inc = MakeFS(child, 11, C_GREY, "RIGHT"),
    }
    PV.capHead.week:SetText(L["周"])
    PV.capHead.rank:SetText(L["达到军衔"])
    PV.capHead.cum:SetText(L["累计上限"])
    PV.capHead.inc:SetText(L["本周增量"])
    PV.capNote = MakeFS(child, 11, C_GREY, "LEFT")
    PV.capNote:SetWidth(400)
    PV.capNote:SetWordWrap(false)
    PV.labels.capNote = PV.capNote
'''

# ---------- R4a/R4b: HideAll 补隐藏 ----------
A_R4A = '    for i = 1, 10 do PV.capRows[i]:Hide() end\n'
R4A_NEW = A_R4A + '''    for i = 1, 10 do PV.wkRows[i]:Hide() end
    PV.rankCard:Hide()
    PV.capCard:Hide()
'''
A_R4B = '    for _, fs in pairs(PV.rankHead or {}) do fs:Hide() end\n'
R4B_NEW = A_R4B + '    for _, fs in pairs(PV.capHead or {}) do fs:Hide() end\n'

# ---------- R5: RenderRanks 整体替换 ----------
A_R5_START = 'function PV.RenderRanks()'
A_R5_END = 'function PV.RenderSets()'
R5_NEW = '''function PV.RenderRanks()
    -- ★★ 两列卡片布局（2026-10-08 反馈三条全落地）：①两卡圆角（BuildRoundedBG）
    --   ②「第 N 周」单行不折行（SetWordWrap(false) + 列宽留足）③奖励独立成列
    --   （列头「奖励」与芯片列对齐 382，行内 ≤3 枚 + 「+N」记数）。
    --   左卡标题条收编阵营切换与当前军衔徽章（滚动区外不再占一行）。
    local LW, RH = 500, 28
    local function T(k) return L[k] or k end
    PV.rankCard:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 0, 0)
    PV.capCard:SetPoint("TOPLEFT", PV.child, "TOPLEFT", LW + 12, 0)
    PV.rankCard:Show()
    PV.capCard:Show()
    local head = PV.labels.ranksHead
    head:SetPoint("TOPLEFT", PV.rankCard, "TOPLEFT", 12, -8)
    head:SetText(T("军衔阶梯"))
    head:Show()
    if SetTip then
        SetTip(head, L["达到军衔后，在暴风城的勇士大厅 / 奥格瑞玛的传说大厅购买奖励；点数按赛季累计，升级不消耗"])
    end
    PV.facBtn1:ClearAllPoints()
    PV.facBtn1:SetPoint("TOPRIGHT", PV.rankCard, "TOPRIGHT", -8, -2)
    PV.facBtn2:ClearAllPoints()
    PV.facBtn2:SetPoint("TOPRIGHT", PV.facBtn1, "TOPLEFT", -4, 0)
    PV.facBtn1:Show()
    PV.facBtn2:Show()
    SetOutline(PV.facBtn1, PV.faction == "A", 1, 0.82, 0)
    SetOutline(PV.facBtn2, PV.faction == "H", 1, 0.82, 0)
    local lv, lp = LiveState()
    if lv and lv >= 1 then
        PV.rankBadge:SetTexture(format("Interface\\PvPRankBadges\\PvPRank%02d", lv))
        PV.rankBadge:SetPoint("TOPRIGHT", PV.facBtn2, "TOPLEFT", -6, -2)
        PV.rankBadge:Show()
        if SetTip then
            SetTip(PV.rankBadge, format(L["当前军衔：R%d · %.0f%%"], lv, (lp or 0) * 100))
        end
    end
    local rh = PV.rankHead
    rh.lvl:SetText(L["军衔"])
    rh.lvl:SetPoint("TOPLEFT", PV.rankCard, "TOPLEFT", 12, -(RH + 5))
    rh.pts:SetPoint("TOPRIGHT", PV.rankCard, "TOPLEFT", 300, -(RH + 5))
    rh.cum:SetPoint("TOPRIGHT", PV.rankCard, "TOPLEFT", 372, -(RH + 5))
    rh.rew:SetPoint("TOPLEFT", PV.rankCard, "TOPLEFT", 382, -(RH + 5))
    for _, fs in pairs(rh) do fs:Show() end
    rh.week:Hide()
    local y0 = RH + 26
    local cursor = 1
    for i = 1, 14 do
        local rec = RD.ranks[i]
        local row = PV.rankRows[i]
        local nm = RANK_NAMES[i]
        row.badge:SetTexture(format("Interface\\PvPRankBadges\\PvPRank%02d", i))
        row.name:SetText(PV.faction == "H" and nm.h or nm.a)
        if i == 14 then
            row.name:SetTextColor(1, 0.5, 0, 1)
        else
            row.name:SetTextColor(Unpack(C_GOLD))
        end
        row.pts:SetText(format("%d", rec.pts))
        row.cum:SetText(format("%d", rec.cum))
        row:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 12, -(y0 + (i - 1) * 34))
        row:Show()
        local all = {}
        local own = (PV.faction == "H") and rec.h or rec.a
        for _, id in ipairs(own) do all[#all + 1] = id end
        for _, id in ipairs(rec.s) do all[#all + 1] = id end
        local shown = math.min(#all, 3)
        for k = 1, shown do
            local chip = PV.chips[cursor]
            cursor = cursor + 1
            chip.iconTex:SetTexture(ItemIcon(id))
            chip.__id = all[k]
            chip:SetPoint("TOPLEFT", PV.child, "TOPLEFT",
                382 + (k - 1) * (PV.CHIP + 4), -(y0 + (i - 1) * 34 + 4))
            chip:Show()
        end
        if #all > 3 then
            row.more:SetText(format("+%d", #all - 3))
            row.more:Show()
        else
            row.more:Hide()
        end
    end
    local capHead = PV.labels.weekCaps
    capHead:SetPoint("TOPLEFT", PV.capCard, "TOPLEFT", 12, -8)
    capHead:SetText(T("每周上限"))
    capHead:Show()
    PV.capNote:SetPoint("TOPLEFT", PV.capCard, "TOPLEFT", 12, -(RH + 2))
    PV.capNote:SetText(T("荣誉逐周累计，第 10 周封顶大元帅；增量为本周需打满的荣誉"))
    PV.capNote:Show()
    local ch = PV.capHead
    ch.week:SetPoint("TOPLEFT", PV.capCard, "TOPLEFT", 12, -(RH + 24))
    ch.rank:SetPoint("TOPLEFT", PV.capCard, "TOPLEFT", 74, -(RH + 24))
    ch.cum:SetPoint("TOPRIGHT", PV.capCard, "TOPLEFT", 312, -(RH + 24))
    ch.inc:SetPoint("TOPRIGHT", PV.capCard, "TOPLEFT", 388, -(RH + 24))
    for _, fs in pairs(ch) do fs:Show() end
    for i = 1, 10 do
        local rec = RD.caps[i]
        local row = PV.wkRows[i]
        local nm = RANK_NAMES[rec.rank]
        row.week:SetText(format(L["第 %d 周"], i))
        row.badge:SetTexture(format("Interface\\PvPRankBadges\\PvPRank%02d", rec.rank))
        row.rank:SetText(format("R%d %s", rec.rank, PV.faction == "H" and nm.h or nm.a))
        row.cum:SetText(format("%d", rec.cum))
        row.inc:SetText(format("+%d", rec.inc))
        row:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 512 + 12, -(RH + 46 + (i - 1) * 44))
        row:Show()
    end
    PV.child:SetHeight(540)
end

'''

# ---------- 预断言 ----------
steps = [
    ("R1", count(src, A_R1), 1),
    ("R2a", count(src, A_R2_START), 1),
    ("R2b", count(src, A_R2_END), 1),
    ("R3", count(src, A_R3), 1),
    ("R4a", count(src, A_R4A), 1),
    ("R4b", count(src, A_R4B), 1),
    ("R5a", count(src, A_R5_START), 1),
    ("R5b", count(src, A_R5_END), 1),
]
for name, c, want in steps:
    rep["steps"].append({"step": name, "count": c})
    if c != want:
        rep["errors"].append(f"pre {name}: count {c} != {want}")
if rep["errors"]:
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("PATCH ABORT pre-assert")
    sys.exit(2)

# ---------- 执行 ----------
new = src
seg = replace_slice(new, A_R2_START, A_R2_END, R2_NEW, "R2", sanity="r.nameA")
if seg is None:
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("PATCH ABORT R2")
    sys.exit(2)
new = seg
seg = replace_slice(new, A_R5_START, A_R5_END, R5_NEW, "R5", sanity="rh.rew:SetPoint")
if seg is None:
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("PATCH ABORT R5")
    sys.exit(2)
new = seg
new = new.replace(A_R1, R1_NEW, 1)
new = new.replace(A_R3, R3_NEW, 1)
new = new.replace(A_R4A, R4A_NEW, 1)
new = new.replace(A_R4B, R4B_NEW, 1)

# ---------- 后断言 ----------
post = [
    ("rankCard", count(new, "PV.rankCard") >= 3),
    ("capCard", count(new, "PV.capCard") >= 3),
    ("wkrows_build", count(new, "PV.wkRows[i] = r"), 1),
    ("rankrows_assign_one", count(new, "        PV.rankRows[i] = r\n    end"), 1),
    ("wkrows_hide", count(new, "PV.wkRows[i]:Hide()"), 1),
    ("rankrows_old_build_gone", count(new, 'r.nameA = MakeFS(r, 14, C_TEXT, "LEFT")'), 0),
    ("rankrows_old_render_gone", count(new, 'row.nameA:SetText(nm.a)'), 0),
    ("slash_old_gone", count(new, 'r.slash = MakeFS(r, 14, C_DIM, "LEFT")'), 0),
    ("rounded2", count(new, "BuildRoundedBG") >= 2),
    ("caphead", count(new, "PV.capHead.week:SetText"), 1),
    ("render_new", count(new, "row.more:SetText") >= 1),
    ("setscrollchild", count(new, "SetScrollChild(child)"), 1),
    ("one_renderanks", count(new, "function PV.RenderRanks()"), 1),
]
post_ok = True
for item in post:
    if len(item) == 2:
        name, ok = item
        c, want = (1 if ok else 0), 1
        if not ok:
            post_ok = False
            rep["errors"].append(f"post {name}: FAIL")
        rep["steps"].append({"step": "post_" + name, "ok": bool(ok)})
    else:
        name, c, want = item
        rep["steps"].append({"step": "post_" + name, "count": c})
        if c != want:
            post_ok = False
            rep["errors"].append(f"post {name}: count {c} != {want}")
if not post_ok:
    rep["nameA_remaining_lines"] = [i for i, l in enumerate(new.split("\n"), 1) if "nameA" in l]
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("PATCH ABORT post-assert")
    sys.exit(2)

# ---------- R6: locale 补键 ----------
NEW_KEYS = {
    "zhTW": [
        ('L["军衔阶梯"]', "軍銜階梯"),
        ('L["每周上限"]', "每週上限"),
        ('L["周"]', "週"),
        ('L["达到军衔"]', "達到軍銜"),
        ('L["累计上限"]', "累計上限"),
        ('L["本周增量"]', "本週增量"),
        ('L["荣誉逐周累计，第 10 周封顶大元帅；增量为本周需打满的荣誉"]',
         "榮譽逐週累計，第 10 週封頂大元帥；增量為本週需打滿的榮譽"),
    ],
    "enUS": [
        ('L["军衔阶梯"]', "Rank Ladder"),
        ('L["每周上限"]', "Weekly Cap"),
        ('L["周"]', "Week"),
        ('L["达到军衔"]', "Rank Reached"),
        ('L["累计上限"]', "Total Cap"),
        ('L["本周增量"]', "This Week"),
        ('L["荣誉逐周累计，第 10 周封顶大元帅；增量为本周需打满的荣誉"]',
         "Honor builds weekly, capping at Grand Marshal by week 10; the gain is this week's honor"),
    ],
    "zhCN": [
        ('L["军衔阶梯"]', "军衔阶梯"),
        ('L["每周上限"]', "每周上限"),
        ('L["周"]', "周"),
        ('L["达到军衔"]', "达到军衔"),
        ('L["累计上限"]', "累计上限"),
        ('L["本周增量"]', "本周增量"),
        ('L["荣誉逐周累计，第 10 周封顶大元帅；增量为本周需打满的荣誉"]',
         "荣誉逐周累计，第 10 周封顶大元帅；增量为本周需打满的荣誉"),
    ],
}
A_LOC = 'L["第 %d 周"]'
loc_done = []
for path in sorted(glob.glob("Locales/*.lua")):
    base = os.path.basename(path)
    variant = None
    for key in NEW_KEYS:
        if key.lower() in base.lower():
            variant = key
    if variant is None:
        loc_done.append({"file": base, "skipped": "no variant"})
        continue
    lsrc = open(path, encoding="utf-8", errors="strict").read()
    if 'L["军衔阶梯"]' in lsrc:
        loc_done.append({"file": base, "skipped": "already patched"})
        continue
    ai = lsrc.find(A_LOC)
    if ai < 0:
        loc_done.append({"file": base, "skipped": "anchor missing"})
        continue
    line_start = lsrc.rfind("\n", 0, ai) + 1
    line_end = lsrc.find("\n", ai)
    indent = ""
    while line_start + len(indent) < len(lsrc) and lsrc[line_start + len(indent)] == " ":
        indent += " "
    ins = "\n".join(indent + k + " = " + json.dumps(v, ensure_ascii=False) for k, v in NEW_KEYS[variant])
    lnew = lsrc[:line_end] + "\n" + ins + lsrc[line_end:]
    for k, _ in NEW_KEYS[variant]:
        if count(lnew, k) != 1:
            rep["errors"].append(f"locale {base}: key not unique after insert: {k[:40]}")
            post_ok = False
    open(path, "w", encoding="utf-8", newline="").write(lnew)
    loc_done.append({"file": base, "inserted": len(NEW_KEYS[variant])})
rep["locale"] = loc_done

# ---------- 备份 + 写盘 ----------
shutil.copyfile(SRC, BAK)
open(SRC, "w", encoding="utf-8", newline="").write(new)
rep["ok"] = True
rep["orig_len"] = orig_len
rep["new_len"] = len(new)
rep["backup"] = BAK
rep["nameA_remaining_lines"] = [i for i, l in enumerate(new.split("\n"), 1) if "nameA" in l]
json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"PATCH OK steps={len(rep['steps'])} len {orig_len}->{len(new)}")
