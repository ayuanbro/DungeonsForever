import sys

CK = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"
d = open(CK, "rb").read()

OLD1 = (
    "    ck('\u2605\u2605 \u4efb\u52a1\u884c\u5c0f\u5361\u7247\uff082026-10-13 \u7528\u6237\u5b9a\uff1a\u524d\u7f6e\u6539\u5c0f\u5361\u7247 + \u65b0\u589e\u53ef\u5171\u4eab\uff0c\u7d27\u8d34\u4efb\u52a1\u540d\u53f3\u4fa7\uff09',\n"
    "       'function DG.MakeBadge(parent)' in src and 'function DG.PlaceBadge(b, x, text)' in src\n"
    "       and 'r.preB = DG.MakeBadge(r)' in src and 'r.shareB = DG.MakeBadge(r)' in src\n"
    "       and 'DG.PlaceBadge(r.preB, bx, L[\"\u524d\u7f6e\"])' in src\n"
    "       and 'DG.PlaceBadge(r.shareB, bx, L[\"\u53ef\u5171\u4eab\"])' in src)\n")
NEW1 = (
    "    ck('\u2605\u2605 \u4efb\u52a1\u884c\u5c0f\u5361\u7247\uff082026-10-13 \u7528\u6237\u5b9a\uff1a\u524d\u7f6e\u6539\u5c0f\u5361\u7247 + \u65b0\u589e\u53ef\u5171\u4eab\uff0c\u7d27\u8d34\u4efb\u52a1\u540d\u53f3\u4fa7\uff09',\n"
    "       'function DG.MakeBadge(parent, bg)' in src and 'function DG.PlaceBadge(b, x, text)' in src\n"
    "       and 'r.preB = DG.MakeBadge(r, DG.Q_BADGE_PRE_BG)' in src\n"
    "       and 'r.shareB = DG.MakeBadge(r, DG.Q_BADGE_SHARE_BG)' in src\n"
    "       and 'DG.Q_BADGE_PRE_BG = { 0.78, 0.60, 0.10, 1 }' in src\n"
    "       and 'DG.Q_BADGE_SHARE_BG = { 0.16, 0.52, 0.26, 1 }' in src\n"
    "       and 'MakeFS(b, DG.Q_BADGE_FS, C_WHITE, \"CENTER\")' in src\n"
    "       and 'DG.PlaceBadge(r.preB, bx, L[\"\u524d\u7f6e\"])' in src\n"
    "       and 'DG.PlaceBadge(r.shareB, bx, L[\"\u53ef\u5171\u4eab\"])' in src)\n")

OLD2 = (
    "    ck('\u2605\u2605 \u53ef\u5171\u4eab\u5224\u5b9a\u8d70\u6570\u636e\u8868\uff08ns.DungeonQuestShare = QuestieDB questFlags & 0x08\uff09',\n"
    "       'function DG.QuestShare(id)' in src\n"
    "       and 'ns.DungeonQuestShare and ns.DungeonQuestShare[id]' in src\n"
    "       and 'ns.DungeonQuestShare = {' in qdat)\n")
NEW2 = (
    "    ck('\u2605\u2605 \u53ef\u5171\u4eab\u5224\u5b9a\u8d70\u5ba2\u6237\u7aef\u300c\u5171\u4eab\u300d\u6570\u636e\uff08C_QuestLog.IsPushableQuest\uff0c\u4e0e\u8be6\u60c5\u5361\u540c\u4e00\u53e3\u5f84\uff1b\u6570\u636e\u8868\u4e3a\u79bb\u7ebf\u56de\u9000\uff09',\n"
    "       'function DG.QuestShare(id)' in src\n"
    "       and 'DG.QLCall(\"IsPushableQuest\", id)' in src\n"
    "       and 'ns.DungeonQuestShare and ns.DungeonQuestShare[id]' in src\n"
    "       and 'ns.DungeonQuestShare = {' in qdat)\n"
    "    ck('\u2605 \u8be6\u60c5\u5361\u300c\u524d\u7f6e\u4efb\u52a1\u300d\u6807\u9898\uff082026-10-13 \u7531\u300c\u524d\u5bfc\u4efb\u52a1\u300d\u6539\u540d\uff09',\n"
    "       'f:SetText(L[\"\u524d\u7f6e\u4efb\u52a1\"])' in src and 'L[\"\u524d\u5bfc\u4efb\u52a1\"]' not in src)\n"
    "    ck('\u2605 \u8be6\u60c5\u8282\u70b9\u884c\u4e0d\u518d\u6709\u5de6\u5f3a\u8c03\u6761\uff08r.bar \u5220\u51c0\uff0c\u5185\u886c 10\u21928\uff09',\n"
    "       'r.bar' not in src\n"
    "       and 'r.name:SetPoint(\"TOPLEFT\", r, \"TOPLEFT\", 8, -3)' in src\n"
    "       and 'r.sub:SetPoint(\"TOPLEFT\", r, \"TOPLEFT\", 8, -21)' in src)\n")

for i, (old, new) in enumerate(((OLD1, NEW1), (OLD2, NEW2))):
    o, n = old.encode("utf-8"), new.encode("utf-8")
    c = d.count(o)
    print("  #%d 命中 %d" % (i, c))
    if c != 1:
        sys.exit(1)
    d = d.replace(o, n)

open(CK, "wb").write(d)
print("写回 OK")
