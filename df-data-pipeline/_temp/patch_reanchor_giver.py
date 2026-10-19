import sys

CK = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"
MU = r"D:\workspace\DungeonsForever\_temp\df_mut_check.py"

COORD_GSUB = '    s = s:gsub("%s*[%d%.]+%s*,%s*[%d%.]+%s*$", "")'
DASH_GSUB = '    s = s:gsub("%s*%-%s*[^%-]*$", "")'

# ---------- 1) harness：静态断言补 pin 剥皮体 ----------
c = open(CK, "rb").read()
old_ck = ("    ck('\u2605 \u7b2c\u4e8c\u5217\u53ea\u663e\u793a\u5927\u5730\u56fe\u540d\uff08\u53bb\u5750\u6807 + \u53bb\u5b50\u533a\u57df\uff09',\n"
          "       'function DG.QuestMapName(s)' in src\n"
          "       and 'r.sub:SetText(DG.QuestMapName(loc))' in src)\n").encode("utf-8")
new_ck = ("    ck('\u2605 \u7b2c\u4e8c\u5217\u53ea\u663e\u793a\u5927\u5730\u56fe\u540d\uff08\u53bb\u5750\u6807 + \u53bb\u5b50\u533a\u57df\uff09',\n"
          "       'function DG.QuestMapName(s)' in src\n"
          "       and 'r.sub:SetText(DG.QuestMapName(loc))' in src\n"
          "       and '" + COORD_GSUB + "' in src\n"
          "       and '" + DASH_GSUB + "' in src)\n").encode("utf-8")
n = c.count(old_ck)
print("CK 命中", n)
if n != 1:
    sys.exit(1)
open(CK, "wb").write(c.replace(old_ck, new_ck))
print("CK 写回 OK")

# ---------- 2) 变异：整块替换 MUT_ROW_GIVER 定义 ----------
d = open(MU, "rb").read()
head = "# 左列单行重新拼上起始 NPC。".encode("utf-8")
i = d.index(head)
j = d.index(b"\n\n", i) + 2
old_block = d[i:j]
print("--- 旧块 ---")
print(old_block.decode("utf-8"))
new_block = ("# \u7b2c\u4e8c\u5217\u53c8\u4e0d\u5265\u5750\u6807\uff08\u5730\u56fe\u540d\u5e26 63,37\uff09\u3002\u671f\u671b\uff1a\u9759\u6001\u300c\u53ea\u663e\u793a\u5927\u5730\u56fe\u540d\u300d\u5931\u8d25\u3002\n"
             "MUT_ROW_GIVER = (\n"
             "    b'" + COORD_GSUB + "\\r\\n',\n"
             "    b'    -- MUT: coords not stripped\\r\\n')\n"
             "\n").encode("utf-8")
d = d[:i] + new_block + d[j:]

item = "    ('\u5de6\u5217\u5355\u884c\u62fc\u56de\u8d77\u59cb NPC', MUT_ROW_GIVER),\n".encode("utf-8")
new_item = "    ('\u7b2c\u4e8c\u5217\u53c8\u4e0d\u5265\u5750\u6807\uff08\u5730\u56fe\u540d\u5e26\u5750\u6807\uff09', MUT_ROW_GIVER),\n".encode("utf-8")
n = d.count(item)
print("MU item 命中", n)
if n != 1:
    sys.exit(1)
d = d.replace(item, new_item)
open(MU, "wb").write(d)
print("MU 写回 OK")
