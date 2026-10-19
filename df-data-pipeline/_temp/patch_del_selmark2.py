import sys

CK = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"
MU = r"D:\workspace\DungeonsForever\_temp\df_mut_check.py"

OLD_STATIC = ("    ck('★ 任务行选中态：右缘金标条 + OnLeave/paint 按选中态复位（悬停不冲掉选中）',\n"
              "       'r.selMark:SetShown(isSel)' in src\n"
              "       and 'HuiCardState(r, isSel and \"hover\" or \"norm\")' in src\n"
              "       and '(self.__q and self.__q[1] == U.dungeonQuestSel) and \"hover\" or \"norm\"' in src)\n")
NEW_STATIC = ("    ck('★ 任务行选中态：无强调条（右缘金标条 selMark 已删）+ OnLeave/paint 按选中态复位（悬停不冲掉选中）',\n"
              "       'r.selMark' not in src\n"
              "       and 'HuiCardState(r, isSel and \"hover\" or \"norm\")' in src\n"
              "       and '(self.__q and self.__q[1] == U.dungeonQuestSel) and \"hover\" or \"norm\"' in src)\n")

OLD_DYN = ("    ck(\"★ 行不再有左状态色条（2026-10-13 强调条全删，行内改小卡片）\",\n"
           "       rawget(qpool0.row[1], \"bar\") == nil)\n")
NEW_DYN = (OLD_DYN +
           "    ck(\"★ 行不再有右缘金标条 selMark（2026-10-13 二次：选中强调条也删）\",\n"
           "       rawget(qpool0.row[1], \"selMark\") == nil)\n")

OLD_MUT_DEF = ("# 选中行没有右缘金标条。\n"
               "MUT_SELMARK_HIDE = (\n"
               "    b'                r.selMark:SetShown(isSel)\\r\\n',\n"
               "    b'                r.selMark:Hide() -- MUT: no selection mark\\r\\n')\n"
               "\n")
OLD_MUT_ITEM = "    ('选中行没有右缘金标条', MUT_SELMARK_HIDE),\n"


def patch(path, pairs):
    d = open(path, "rb").read()
    for i, (old, new) in enumerate(pairs):
        o = old.encode("utf-8") if isinstance(old, str) else old
        n = new.encode("utf-8") if isinstance(new, str) else new
        c = d.count(o)
        print("  [%s] #%d 命中 %d" % (path.split("\\")[-1], i, c))
        if c != 1:
            sys.exit(1)
        d = d.replace(o, n)
    open(path, "wb").write(d)
    print("  -> 写回 OK")


print("== df_dungeon_check.py ==")
patch(CK, [(OLD_STATIC, NEW_STATIC), (OLD_DYN, NEW_DYN)])
print("== df_mut_check.py ==")
patch(MU, [(OLD_MUT_DEF, ""), (OLD_MUT_ITEM, "")])
print("done")
