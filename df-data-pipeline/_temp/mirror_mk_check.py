# -*- coding: utf-8 -*-
# 把 df_dungeon_check.py 新增的「配方搜索 + 名称列现算」断言镜像进 mk_df_check.py（保生成器一致）
import io, sys

SRC = r'D:\workspace\DungeonsForever\_temp\df_dungeon_check.py'
DST = r'D:\workspace\DungeonsForever\_temp\mk_df_check.py'

s = io.open(SRC, 'r', encoding='utf-8', newline='').read()
d = io.open(DST, 'r', encoding='utf-8', newline='').read()
if '配方搜索 + 名称列现算' in d:
    print('SKIP: mk 已有'); sys.exit(0)

# 从 df_dungeon_check.py 截取刚插入的两段
i1 = s.index('    # ⑩ 配方搜索 + 名称列现算（2026-10-09：第一列名称太宽 / 材料列截断太多 + 工具行右端加搜索框）')
i2 = s.index("    ck('★ 材料列字体串吃 PD.MAT_FS（字号口径不许被旁路写死）',", i1)
static_block = s[i1:i2]

j1 = d.index(a1 := "       and 'PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * LV_SPLIT)' in profui)\n")
if d.count(a1) != 1:
    print('FATAL: mk 静态锚 %d 次' % d.count(a1)); sys.exit(1)
d2 = d[:j1 + len(a1)] + '\n' + static_block.rstrip('\n') + '\n' + d[j1 + len(a1):]

k1 = d2.index('            ck("★ 材料列预算不足时不劈字（截到放得下 + …）", type(_t0) == "string")\n          end\n')
k1c = d2.count('            ck("★ 材料列预算不足时不劈字（截到放得下 + …）", type(_t0) == "string")\n          end\n')
if k1c != 1:
    print('FATAL: mk 运行时锚 %d 次' % k1c); sys.exit(1)

# 运行时段取 df_dungeon_check 里的同一段
r1 = s.index('          -- ---------- 配方搜索 + 名称列现算（2026-10-09）----------')
r2 = s.index('          -- ---------- 专业页的行同样支持 Shift+点击发链接 ----------')
runtime_block = s[r1:r2]
k2 = d2.index('          -- ---------- 专业页的行同样支持 Shift+点击发链接 ----------')
if d2.count('          -- ---------- 专业页的行同样支持 Shift+点击发链接 ----------') != 1:
    print('FATAL: mk Shift 锚不唯一'); sys.exit(1)
d3 = d2[:k2] + runtime_block + d2[k2:]

io.open(DST, 'w', encoding='utf-8', newline='').write(d3)
print('OK mk_df_check.py 镜像完成')
