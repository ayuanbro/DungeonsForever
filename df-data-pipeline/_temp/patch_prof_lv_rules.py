# -*- coding: utf-8 -*-
# 专业页：① 总览删「数字速览」段 ② 齿轮右缘对齐内容右缘（UI_RULES §3 三点一线）
#         ③ 升级页四张信息卡补悬停胶囊 L4（UI_RULES §2/§4 标准件）。全程 CRLF。
P = r"D:\workspace\DungeonsForever\Core\ProfessionUI.lua"
d = open(P, "rb").read().decode("utf-8")
crlf = d.count("\r\n")
assert d.count("\n") - crlf == 0, "unexpected bare LF"

def rep1(old, new):
    global d
    assert d.count(old) == 1, "anchor (%d): %r" % (d.count(old), old[:80])
    d = d.replace(old, new)

# ── ① 删数字速览段（stat 助手 + 4 行统计 + 段尾空档；hasPerks 保留给传承段）──
old_block = (
    "    local function stat(label, value)\r\n"
    "        rows[#rows + 1] = {\r\n"
    "            kind = \"row\", h = PD.ROW_H1, col = 1,\r\n"
    "            nameColor = C_GREY, text = label, right = value,\r\n"
    "        }\r\n"
    "    end\r\n"
    "    PushHead(rows, L[\"数字速览\"], 1)\r\n"
    "    if p.cert then stat(L[\"认证技能\"], format(L[\"技能 %d\"], p.cert[4] or 0)) end\r\n"
    "    if p.recipes or p.sub then\r\n"
    "        stat(L[\"配方规模\"], format(L[\"%d 条 · %d 个分类\"], p.recipes or 0, p.sub or 0))\r\n"
    "    end\r\n"
    "    if p.camp and #p.camp > 0 then stat(L[\"营地\"], format(L[\"%d 档\"], #p.camp)) end\r\n"
    "    if hasPerks then stat(L[\"传承特权\"], format(L[\"%d 个\"], #p.perks)) end\r\n"
    "    PushGap(rows, PD.OV_GUT, 1)\r\n"
)
rep1(old_block, "")

# ── ② 齿轮右缘对齐（原 -8 突进，违反 §3 右缘三点一线）──
rep1('gear:SetPoint("TOPRIGHT", page, "TOPLEFT", PD.RIGHT_X + PD.RIGHT_W - 8, -PD.SUB_Y)',
     'gear:SetPoint("TOPRIGHT", page, "TOPLEFT", PD.RIGHT_X + PD.RIGHT_W, -PD.SUB_Y)')

# ── ③ 信息卡悬停胶囊（Build 期建好，PaintLvTiles 的 TipOn 切显隐）──
rep1("        tf.__border = bord or {}\r\n",
     "        tf.__border = bord or {}\r\n"
     "        if ns.hui and ns.hui.BuildCapsule then\r\n"
     "            -- 悬停胶囊 L4 = L2 内卡 +2 档（UI_RULES 卡中卡阶梯）；进出由 TipOn 切显隐\r\n"
     "            tf.__hov = ns.hui.BuildCapsule(tf, 8, ns.hui.layer.L4, 1, 2) or {}\r\n"
     "            for _, t in ipairs(tf.__hov) do t:Hide() end\r\n"
     "        end\r\n")

old_tip = (
    "    local function TipOn(tf, lines)\r\n"
    "        tf:SetScript(\"OnEnter\", function(self)\r\n"
    "            GameTooltip:SetOwner(self, \"ANCHOR_RIGHT\")\r\n"
)
new_tip = (
    "    local function TipOn(tf, lines)\r\n"
    "        tf:SetScript(\"OnEnter\", function(self)\r\n"
    "            if tf.__hov then for _, t in ipairs(tf.__hov) do t:Show() end end\r\n"
    "            GameTooltip:SetOwner(self, \"ANCHOR_RIGHT\")\r\n"
)
rep1(old_tip, new_tip)

rep1('        tf:SetScript("OnLeave", function() GameTooltip:Hide() end)\r\n'
     "    end\r\n",
     '        tf:SetScript("OnLeave", function()\r\n'
     "            if tf.__hov then for _, t in ipairs(tf.__hov) do t:Hide() end end\r\n"
     "            GameTooltip:Hide()\r\n"
     "        end)\r\n"
     "    end\r\n")

open(P, "wb").write(d.encode("utf-8"))
print("ProfessionUI ok CRLF", d.count("\r\n"), "bare", d.count("\n") - d.count("\r\n"))
