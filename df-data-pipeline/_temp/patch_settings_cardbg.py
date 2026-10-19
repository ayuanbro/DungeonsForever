# -*- coding: utf-8 -*-
# 2026-10-08 用户：设置弹窗加「卡片背景」——内容区垫一张 L2 圆角大卡片（与页面大卡同皮）。
# 改 Core/QuickBar.lua（LF）：EnsureSettings 里 ①建卡（先于各行 ⇒ 恒垫底）②排完回填高度。
# 幂等：已含标记则 SKIP。锚点各须命中 1 次，否则中止。
import sys, io

P = r"D:/workspace/DungeonsForever/Core/QuickBar.lua"
MARK = "QB_SET_CARD_BG"

with io.open(P, "r", encoding="utf-8", newline="") as f:
    src = f.read()

if MARK in src:
    print("SKIP: already patched")
    sys.exit(0)

A_OLD = (
    "    local set = { group = {}, expl = {} }\n"
    "    local y = -44\n"
)
A_NEW = (
    "    local set = { group = {}, expl = {} }\n"
    "    local y = -44\n"
    "\n"
    "    -- ★ 设置弹窗「卡片背景」（" + MARK + "，2026-10-08 用户）：内容区垫一张 L2 圆角大卡片\n"
    "    --   （与各页「页底大卡」同皮：弧盘 + 1px 描边）。先于各行创建 ⇒ 恒垫底；\n"
    "    --   普通 Frame 不收鼠标；高度在内容排完后回填（底边超出末行 12px）。\n"
    "    if not self.cardBg then\n"
    "        local card = CreateFrame(\"Frame\", nil, pop)\n"
    "        if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then\n"
    "            ns.hui.BuildRoundedBG(card, 8, ns.hui.layer.L2, \"both\", true, 1)\n"
    "        else\n"
    "            local bg = card:CreateTexture(nil, \"BACKGROUND\")\n"
    "            bg:SetColorTexture(0.21, 0.22, 0.25, 1)\n"
    "            bg:SetAllPoints()\n"
    "        end\n"
    "        self.cardBg = card\n"
    "    end\n"
    "    self.cardBg:ClearAllPoints()\n"
    "    self.cardBg:SetPoint(\"TOPLEFT\", pop, \"TOPLEFT\", 6, -6)\n"
    "    self.cardBg:SetPoint(\"TOPRIGHT\", pop, \"TOPRIGHT\", -6, -6)\n"
)

B_OLD = "    self.set, self.setBuilt = set, true\n"
B_NEW = (
    "    if self.cardBg then self.cardBg:SetHeight(6 - y) end\n"
    "    self.set, self.setBuilt = set, true\n"
)

ca, cb = src.count(A_OLD), src.count(B_OLD)
if ca != 1 or cb != 1:
    print("ABORT: anchor hits A=%d B=%d (expect 1/1)" % (ca, cb))
    sys.exit(1)

out = src.replace(A_OLD, A_NEW, 1).replace(B_OLD, B_NEW, 1)
assert "\r" not in out, "QuickBar.lua must stay LF"
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write(out)
print("OK: patched, +%d lines" % (out.count("\n") - src.count("\n")))
