# -*- coding: utf-8 -*-
# 验证：攻略段配方的断点数据覆盖率 + 升点概率模型抽查（ProfFollow craftsLeft）
import re

base = r"D:/workspace/DungeonsForever/Core/Data/enUS"
lv = open(base + r"/Data_ProfLeveling.lua", encoding="utf-8").read()
rc = open(base + r"/Data_ProfRecipes.lua", encoding="utf-8").read()

segs = re.findall(r"\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}", lv)
print("总段数:", len(segs))

# 配方行: { id, spell, 1, "grp", "tag", "desc", o, y, g, gr, ...
DESC = r'"(?:[^"\\]|\\.)*"'
row_pat = re.compile(
    r'^\s*\{\s*(\d+),\s*(\d+),\s*1,\s*"[^"]*",\s*"[^"]*",\s*' + DESC +
    r',\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),', re.M)
rowmap = {}
for m in row_pat.finditer(rc):
    rowmap[int(m.group(1))] = tuple(int(m.group(i)) for i in (3, 4, 5, 6))
print("带断点配方行:", len(rowmap))

missing = []
for a, b, rid, c in segs:
    if int(rid) not in rowmap:
        missing.append((int(a), int(b), int(rid)))
print("缺断点数据的段:", missing if missing else "无")


def exp_pp(sk, y, g, gr):
    if sk < y:
        return 1.0
    if sk < g:
        return 1.0 / (1 - 0.5 * (sk - y) / (g - y))
    if sk < gr:
        return 1.0 / (0.5 - 0.45 * (sk - g) / (gr - g))
    return None


rec = rowmap.get(2152)
print("2152 断点(橙黄绿灰):", rec)
for sk in (15, 30, 42, 45, 50, 57):
    e = exp_pp(sk, rec[1], rec[2], rec[3])
    print("  skill=%d: %s 次/点" % (sk, "灰" if e is None else round(e, 2)))

tot = sum(e for s in range(42, 58) for e in [exp_pp(s, *rec[1:])] if e is not None)
print("当前场景(制皮42, 段15-58) 还需制作 ≈", round(tot, 1), "→", -(-tot // 1))

print()
print("抽查对比（段 概率口径 vs 攻略口径）:")
for a, b, rid, c in segs[:6] + segs[-3:]:
    r = rowmap.get(int(rid))
    if not r or not (r[1] < r[2] < r[3]):
        print("  %s-%s rid=%s: 无断点数据(走线性回退) 攻略=%s" % (a, b, rid, c))
        continue
    t = sum(exp_pp(s, *r[1:]) or 20 for s in range(int(a), int(b)))
    print("  %s-%s rid=%s: 期望≈%d 攻略=%s" % (a, b, rid, round(t), c))
