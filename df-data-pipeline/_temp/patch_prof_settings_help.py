# -*- coding: utf-8 -*-
# 专业设置页：行下直铺的说明文字（desc/d1/d2）退役 → 设置名右侧「?」图标 + 悬停 tooltip。
P = r"D:\workspace\DungeonsForever\Core\ProfessionUI.lua"
d = open(P, "rb").read().decode("utf-8")
crlf = d.count("\r\n")
assert d.count("\n") - crlf == 0, "unexpected bare LF"

def rep1(old, new):
    global d
    assert d.count(old) == 1, "anchor (%d): %r" % (d.count(old), old[:80])
    d = d.replace(old, new)

# ── ① Build：「?」帮助图标池（与开关池同容量，显隐由 PlaceSettingsToggles 管）──
rep1(
    "        PD.setToggles[i] = tg\r\n"
    "    end\r\n",
    "        PD.setToggles[i] = tg\r\n"
    "    end\r\n"
    "\r\n"
    "    -- 设置行「?」帮助图标池：详细说明收到悬停提示框里，不再直铺在行下\r\n"
    "    PD.setHelps = {}\r\n"
    "    for i = 1, PD.SETTING_TOG_MAX do\r\n"
    "        local hp = CreateFrame(\"Button\", nil, child)\r\n"
    "        hp:SetSize(16, 16)\r\n"
    "        hp.text = MakeFS(hp, 12, C_GOLD, \"CENTER\")\r\n"
    "        hp.text:SetAllPoints()\r\n"
    "        hp.text:SetText(\"?\")\r\n"
    "        hp:SetScript(\"OnEnter\", function(self)\r\n"
    "            local ln = self.__tip\r\n"
    "            if not ln then return end\r\n"
    "            GameTooltip:SetOwner(self, \"ANCHOR_RIGHT\")\r\n"
    "            GameTooltip:ClearLines()\r\n"
    "            for _, t in ipairs(ln) do\r\n"
    "                if t[1] and t[1] ~= \"\" then\r\n"
    "                    GameTooltip:AddLine(t[1], t[2] or 1, t[3] or 1, t[4] or 1, true)\r\n"
    "                end\r\n"
    "            end\r\n"
    "            GameTooltip:Show()\r\n"
    "        end)\r\n"
    "        hp:SetScript(\"OnLeave\", function() GameTooltip:Hide() end)\r\n"
    "        hp:EnableMouseWheel(true)\r\n"
    "        hp:SetScript(\"OnMouseWheel\", function(_, delta)\r\n"
    "            DG.WheelScroll(PD.scroll, PD.child, delta)\r\n"
    "        end)\r\n"
    "        hp:Hide()\r\n"
    "        PD.setHelps[i] = hp\r\n"
    "    end\r\n"
)

# ── ② RowsSettings：行只留名字 + togKey；说明进 help（tooltip 用），sub/直铺 PushText 删 ──
rep1(
    "        rows[#rows + 1] = {\r\n"
    "            kind = \"row\", h = 40, col = 1,\r\n"
    "            text = d.name,\r\n"
    "            sub = d.desc,\r\n"
    "            togKey = d.k,\r\n"
    "            lines = { { d.name }, { d.desc, 0.7, 0.7, 0.7 }, { d.d1, 0.7, 0.7, 0.7 }, { d.d2, 0.7, 0.7, 0.7 } },\r\n"
    "        }\r\n"
    "        if d.d1 then PushText(rows, d.d1, 11, C_GREY) end\r\n"
    "        if d.d2 then PushText(rows, d.d2, 11, C_GREY) end\r\n"
    "        PushGap(rows, 6)\r\n",
    "        rows[#rows + 1] = {\r\n"
    "            kind = \"row\", h = 40, col = 1,\r\n"
    "            text = d.name,\r\n"
    "            togKey = d.k,\r\n"
    "            help = { { d.name }, { d.desc, 0.7, 0.7, 0.7 }, { d.d1, 0.7, 0.7, 0.7 }, { d.d2, 0.7, 0.7, 0.7 } },\r\n"
    "        }\r\n"
    "        PushGap(rows, 6)\r\n"
)

# ── ③ PlaceSettingsToggles：问号摆到名字右侧（锚行名字 FontString 右缘）并绑 tooltip ──
rep1(
    "            tg.__key = spec.togKey\r\n"
    "            tg:Show()\r\n"
    "        end\r\n"
    "    end\r\n"
    "    for j = ti + 1, #PD.setToggles do PD.setToggles[j]:Hide() end\r\n",
    "            tg.__key = spec.togKey\r\n"
    "            tg:Show()\r\n"
    "            local hp = PD.setHelps[ti]\r\n"
    "            if hp then\r\n"
    "                hp:ClearAllPoints()\r\n"
    "                hp:SetPoint(\"LEFT\", rr.a, \"RIGHT\", 6, -1)\r\n"
    "                hp:SetFrameLevel((rr:GetFrameLevel() or 0) + 10)\r\n"
    "                hp.__tip = spec.help\r\n"
    "                hp:SetShown(spec.help and true or false)\r\n"
    "            end\r\n"
    "        end\r\n"
    "    end\r\n"
    "    for j = ti + 1, #PD.setToggles do PD.setToggles[j]:Hide() end\r\n"
    "    for j = ti + 1, #PD.setHelps do PD.setHelps[j]:Hide() end\r\n"
)

# ── ④ 杂帧扫描的已知骨架帧集合补问号池 ──
rep1(
    "    if PD.setToggles then for _, c in ipairs(PD.setToggles) do known[c] = true end end\r\n",
    "    if PD.setToggles then for _, c in ipairs(PD.setToggles) do known[c] = true end end\r\n"
    "    if PD.setHelps then for _, c in ipairs(PD.setHelps) do known[c] = true end end\r\n"
)

open(P, "wb").write(d.encode("utf-8"))
print("ProfessionUI ok CRLF", d.count("\r\n"), "bare", d.count("\n") - d.count("\r\n"))
