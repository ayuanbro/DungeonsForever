import sys

DF = r"D:\workspace\DungeonsForever\Core\DungeonUI.lua"
CK = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"
MU = r"D:\workspace\DungeonsForever\_temp\df_mut_check.py"


def patch(path, pairs):
    d = open(path, "rb").read()
    for i, (old, new) in enumerate(pairs):
        n = d.count(old)
        print("  [%s] #%d 命中 %d" % (path.split("\\")[-1], i, n))
        if n != 1:
            sys.exit(1)
        d = d.replace(old, new)
    open(path, "wb").write(d)
    print("  -> 写回 OK")


# ---------- 1) 源码：删 selMark（创建块 + 使用行） ----------
print("== Core/DungeonUI.lua ==")
patch(DF, [
    (b'            r.selMark = r:CreateTexture(nil, "OVERLAY")\r\n'
     b'            r.selMark:SetColorTexture(1, 0.82, 0, 0.95)\r\n'
     b'            r.selMark:SetPoint("TOPRIGHT", r, "TOPRIGHT", 0, 0)\r\n'
     b'            r.selMark:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", 0, 0)\r\n'
     b'            r.selMark:SetWidth(3)\r\n'
     b'            r.selMark:Hide()\r\n', b''),
    (b'                r.selMark:SetShown(isSel)\r\n', b''),
])

# ---------- 2) harness：静态断言改口径 + 新增动态断言 ----------
print("== df_dungeon_check.py ==")
patch(CK, [
    ("    ck('★ 任务行选中态：右缘金标条 + OnLeave/paint 按选中态复位（悬停不冲掉选中）',\n"
     "       'r.selMark:SetShown(isSel)' in src\n"
     "       and 'HuiCardState(r, isSel and \"hover\" or \"norm\")' in src\n"
     "       and '(self.__q and self.__q[1] == U.dungeonQuestSel) and \"hover\" or \"norm\"' in src)\n"
     ).encode("utf-8"),
    ("    ck('★ 任务行选中态：无强调条（右缘金标条 selMark 已删）+ OnLeave/paint 按选中态复位（悬停不冲掉选中）',\n"
     "       'r.selMark' not in src\n"
     "       and 'HuiCardState(r, isSel and \"hover\" or \"norm\")' in src\n"
     "       and '(self.__q and self.__q[1] == U.dungeonQuestSel) and \"hover\" or \"norm\"' in src)\n"
     ).encode("utf-8"),
    ("    ck(\"★ 行不再有左状态色条（2026-10-13 强调条全删，行内改小卡片）\",\n"
     "       rawget(qpool0.row[1], \"bar\") == nil)\n"
     "    ck(\"★ 行不再有右缘金标条 selMark（2026-10-13 二次：选中强调条也删）\",\n"
     "       rawget(qpool0.row[1], \"selMark\") == nil)\n"
     ).encode("utf-8"),
])

# ---------- 3) 变异锚点：删掉已无对应代码的 selMark 变异 ----------
print("== df_mut_check.py ==")
patch(MU, [
    (("# 选中行没有右缘金标条。\n"
      "MUT_SELMARK_HIDE = (\n"
      "    b'                r.selMark:SetShown(isSel)\\r\\n',\n"
      "    b'                r.selMark:Hide() -- MUT: no selection mark\\r\\n')\n"
      "\n").encode("utf-8"), b""),
    (b"    ('\xe9\x80\x89\xe4\xb8\xad\xe8\xa1\x8c\xe6\xb2\xa1\xe6\x9c\x89\xe5\x8f\xb3\xe7\xbc\x98\xe9\x87\x91\xe6\xa0\x87\xe6\x9d\xa1', MUT_SELMARK_HIDE),\n", b""),
])
print("done")
