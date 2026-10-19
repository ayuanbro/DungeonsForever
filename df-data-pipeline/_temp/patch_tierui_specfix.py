# -*- coding: utf-8 -*-
"""A/B 两处改动施加到 Core/TierUI.lua（源码侧）。

A) 删除专精指南卡左侧竖向强调条（stripe）：常量 / 创建块 / 常量表字段 /
   BuildSpecCard 上色调用全部清干净，title 锚点偏移回 TT.CARD_PAD。
B) 专精模式内容区整体下移 5px：新增语义常量 TT.SEC_DROP 并并进 TT.SEC_TOP。

逐条 assert 恰中 1 次，纯 LF 写回。幂等：已打过则整体零命中并退出码 0。
"""
import io
import sys

PATH = r'D:\workspace\DungeonsForever\Core\TierUI.lua'

# (name, old, new)
EDITS = [
    (
        "A1 删常量 TT.STRIPE_W",
        "TT.HDR_H = 26\nTT.STRIPE_W = 3\nTT.SPEC_GAP = 8\n",
        "TT.HDR_H = 26\nTT.SPEC_GAP = 8\n",
    ),
    (
        "A2 删 stripe 创建块 + title 锚点回 CARD_PAD",
        '        Cardify(fr, 0.03)\n'
        '        local stripe = fr:CreateTexture(nil, "OVERLAY")\n'
        '        stripe:SetWidth(TT.STRIPE_W)\n'
        '        stripe:SetPoint("TOPLEFT", fr, "TOPLEFT", 1, -1)\n'
        '        stripe:SetPoint("BOTTOMLEFT", fr, "BOTTOMLEFT", 1, 1)\n'
        '        stripe:SetColorTexture(1, 1, 1, 1)\n'
        '        local title = MakeFS(fr, 14, C_WHITE, "LEFT")\n'
        '        title:SetPoint("TOPLEFT", fr, "TOPLEFT", TT.CARD_PAD + TT.STRIPE_W, -TT.CARD_PAD)\n',
        '        Cardify(fr, 0.03)\n'
        '        local title = MakeFS(fr, 14, C_WHITE, "LEFT")\n'
        '        title:SetPoint("TOPLEFT", fr, "TOPLEFT", TT.CARD_PAD, -TT.CARD_PAD)\n',
    ),
    (
        "A3 删常量表字段 stripe",
        "        TT.scCards[i] = { frame = fr, stripe = stripe, title = title, divider = divider, n = 0, H = 0 }\n",
        "        TT.scCards[i] = { frame = fr, title = title, divider = divider, n = 0, H = 0 }\n",
    ),
    (
        "A4 删 BuildSpecCard 的 acc + stripe 上色",
        '    card.pairBot = nil\n'
        '    local acc = TT.ACCENT[sec.key] or TT.ACCENT_FALLBACK\n'
        '    card.stripe:SetColorTexture(acc[1], acc[2], acc[3], 1)\n'
        '\n'
        '    TT.__cur = card\n',
        '    card.pairBot = nil\n'
        '\n'
        '    TT.__cur = card\n',
    ),
    (
        "B1 新增 TT.SEC_DROP 并并进 TT.SEC_TOP",
        "TT.SEC_TAB_Y    = TT.SPEC_TOP + TT.SEC_TAB_GAP\n"
        "TT.SEC_TOP      = TT.SEC_TAB_Y + TT.SEC_TAB_H\n",
        "TT.SEC_TAB_Y    = TT.SPEC_TOP + TT.SEC_TAB_GAP\n"
        "TT.SEC_DROP     = 5\n"
        "TT.SEC_TOP      = TT.SEC_TAB_Y + TT.SEC_TAB_H + TT.SEC_DROP\n",
    ),
]


def main():
    with io.open(PATH, "rb") as fh:
        raw = fh.read()
    assert raw.count(b"\r\n") == 0, "expected pure LF"
    s = raw.decode("utf-8")
    if all(old not in s for _, old, _ in EDITS):
        print("[SKIP] already applied (0 hits)")
        return 0
    for name, old, new in EDITS:
        n = s.count(old)
        if n == 0:
            print("[ALREADY] %s" % name)
            continue
        assert n == 1, "%s: anchor hit %d times (want 1)" % (name, n)
        s = s.replace(old, new)
        print("[OK] %s" % name)
    # 残留自检：源码里不得再有任何 stripe / STRIPE_W 引用
    assert "STRIPE_W" not in s, "STRIPE_W still present"
    assert "stripe" not in s, "stripe still present"
    out = s.encode("utf-8")
    assert out.count(b"\r\n") == 0, "would introduce CRLF"
    with io.open(PATH, "wb") as fh:
        fh.write(out)
    print("[WRITE] %s  (%d -> %d bytes)" % (PATH, len(raw), len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
