# -*- coding: utf-8 -*-
"""修正任务页开关：标签改挂 tg（挂 detail 会被 plateL 实底卡盖住，§5.2）+ 显隐归 ApplyDetailChrome。"""
import io
import sys

PATH = r"D:\workspace\DungeonsForever\Core\DungeonUI.lua"
CRLF = "\r\n"


def main():
    raw = io.open(PATH, "rb").read()
    txt = raw.decode("utf-8")

    edits = []

    # 1) 标签挂 tg + hit 区 + 初始隐藏
    edits.append((
        [
            "        tg.label = MakeFS(detail, 14, C_TEXT, \"LEFT\")",
            "        tg.label:SetPoint(\"LEFT\", tg, \"RIGHT\", 6, 0)",
            "        tg.label:SetText(L[\"显示已完成\"])",
            "        tg:SetScript(\"OnClick\", function(self)",
        ],
        [
            "        tg.label = MakeFS(tg, 14, C_TEXT, \"LEFT\")",
            "        tg.label:SetPoint(\"LEFT\", tg, \"RIGHT\", 6, 0)",
            "        tg.label:SetText(L[\"显示已完成\"])",
            "        tg:SetHitRectInsets(0, -((tg.label:GetStringWidth() or 60) + 6), 0, 0)",
            "        tg:Hide()",
            "        tg:SetScript(\"OnClick\", function(self)",
        ],
    ))

    # 2) ApplyDetailChrome：开关位置块移出 isQuest 块 → 独立块（含 Show/Hide）
    edits.append((
        [
            "        if U.dungeonQDoneTg then",
            "            U.dungeonQDoneTg:ClearAllPoints()",
            "            U.dungeonQDoneTg:SetPoint(\"TOPLEFT\", plateL, \"TOPLEFT\", DG.Q_PAD + 3 * 100, -DG.Q_PAD - 2)",
            "            U.dungeonQDoneTg:SetFrameLevel(plateL:GetFrameLevel() + 5)",
            "        end",
            "    elseif U.dungeonDetail then",
        ],
        [
            "    elseif U.dungeonDetail then",
        ],
    ))
    edits.append((
        [
            "    for key, bt in pairs(U.dungeonTabBtns or {}) do",
        ],
        [
            "    if U.dungeonQDoneTg then",
            "        local tg = U.dungeonQDoneTg",
            "        if isQuest and U.dungeonQPlateL then",
            "            local plateL = U.dungeonQPlateL",
            "            tg:ClearAllPoints()",
            "            tg:SetPoint(\"TOPLEFT\", plateL, \"TOPLEFT\", DG.Q_PAD + 3 * 100, -DG.Q_PAD - 2)",
            "            tg:SetFrameLevel(plateL:GetFrameLevel() + 5)",
            "            tg:Show()",
            "        else",
            "            tg:Hide()",
            "        end",
            "    end",
            "    for key, bt in pairs(U.dungeonTabBtns or {}) do",
        ],
    ))

    for i, (old_lines, new_lines) in enumerate(edits):
        old = CRLF.join(old_lines)
        new = CRLF.join(new_lines)
        n = txt.count(old)
        if n != 1:
            print("EDIT %d 命中 %d 次" % (i, n))
            sys.exit(1)
        txt = txt.replace(old, new)

    out = txt.encode("utf-8")
    io.open(PATH, "wb").write(out)
    print("OK CRLF=%d bareLF=%d" % (out.count(b"\r\n"), out.count(b"\n") - out.count(b"\r\n")))


if __name__ == "__main__":
    main()
