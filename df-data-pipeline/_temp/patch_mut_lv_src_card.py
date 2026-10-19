# -*- coding: utf-8 -*-
"""重锚两条 ProfessionUI 变异（来源行 → 色阶条 + 来源卡片），三份文件同步。

  MUT_PROF_LV_TBL_SRC_GONE  : 原来钉 `r.b:SetText(spec.src or "")`（来源写进来源行）
                              → 改钉 `PD.PaintCard(r, spec.card)`（来源卡片）
  MUT_PROF_LV_TBL_SRC_SAMEY : 原来钉 `r.b:SetPoint(..., PD.TBL_SRC_DY)`（两行不共 y）
                              → 改钉色阶条的 y（`bg:SetPoint(..., PD.SB_DY)`）

同步：df_mut_check.py（定义 + 名字列表）、mk_df_mut.py（生成器，多一层转义）、
      df_check_new_muts.py（新增变异清单里的名字）。

★ 所有锚点都落在**单行内、且不含 \\n / \\\\n** —— mk 生成器里 Lua 的 `\\n` 存成双反斜杠，
  手工拼转义层极易错，索性整段绕开。
"""
import sys

ROOT = r'D:\workspace\DungeonsForever'


def patch(name, pairs):
    p = ROOT + '\\_temp\\' + name
    t = open(p, 'rb').read().decode('utf-8')
    for old, new in pairs:
        n = t.count(old)
        if n != 1:
            print('!! [%s] 锚点命中 %d 次：%r' % (name, n, old[:90]))
            sys.exit(1)
        t = t.replace(old, new)
        print('OK [%s] %s' % (name, old[:60]))
    open(p, 'wb').write(t.encode('utf-8'))
    print('== %s 写入 OK' % name)


# ── df_mut_check.py（成品：真实 Lua 源码，无额外转义层）──────────────────
patch('df_mut_check.py', [
    (r"""b'        r.b:SetText(spec.src or "")\n',""",
     r"""b'        PD.PaintCard(r, spec.card)\n',"""),
    (r"""b'        r.b:SetText("") -- MUT: source line dropped""",
     r"""b'        PD.PaintCard(r, nil) -- MUT: source card dropped"""),
    (r"""b'        r.b:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X, PD.TBL_SRC_DY)""",
     r"""b'        bg:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X + (k - 1) * seg, PD.SB_DY)"""),
    (r"""b'        r.b:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X, PD.TBL_NAME_DY)""",
     r"""b'        bg:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X + (k - 1) * seg, PD.TBL_NAME_DY)"""),
    ("-- MUT: two lines collapsed", "-- MUT: bar onto name line"),
    ("('专业页：来源那一行不写了', MUT_PROF_LV_TBL_SRC_GONE)",
     "('专业页：来源卡片不显示了（来源信息又消失）', MUT_PROF_LV_TBL_SRC_GONE)"),
    ("('专业页：两行塌回一行（来源与配方名同一 y）', MUT_PROF_LV_TBL_SRC_SAMEY)",
     "('专业页：色阶条塌到配方名那一行（两行叠一起）', MUT_PROF_LV_TBL_SRC_SAMEY)"),
])

# ── mk_df_mut.py（生成器：`r.b` 前面多一层 `\"` 转义；锚点避开 \n）──────
patch('mk_df_mut.py', [
    (r"""r.b:SetText(spec.src or \"\")""",
     "PD.PaintCard(r, spec.card)"),
    (r"""r.b:SetText(\"\") -- MUT: source line dropped""",
     "PD.PaintCard(r, nil) -- MUT: source card dropped"),
    (r"""r.b:SetPoint(\"LEFT\", r, \"LEFT\", PD.LV_NAME_X, PD.TBL_SRC_DY)""",
     r"""bg:SetPoint(\"LEFT\", r, \"LEFT\", PD.LV_NAME_X + (k - 1) * seg, PD.SB_DY)"""),
    (r"""r.b:SetPoint(\"LEFT\", r, \"LEFT\", PD.LV_NAME_X, PD.TBL_NAME_DY)""",
     r"""bg:SetPoint(\"LEFT\", r, \"LEFT\", PD.LV_NAME_X + (k - 1) * seg, PD.TBL_NAME_DY)"""),
    ("-- MUT: two lines collapsed", "-- MUT: bar onto name line"),
    ("('专业页：来源那一行不写了', MUT_PROF_LV_TBL_SRC_GONE)",
     "('专业页：来源卡片不显示了（来源信息又消失）', MUT_PROF_LV_TBL_SRC_GONE)"),
    ("('专业页：两行塌回一行（来源与配方名同一 y）', MUT_PROF_LV_TBL_SRC_SAMEY)",
     "('专业页：色阶条塌到配方名那一行（两行叠一起）', MUT_PROF_LV_TBL_SRC_SAMEY)"),
])

# ── df_check_new_muts.py（清单里的名字）────────────────────────────────
patch('df_check_new_muts.py', [
    ("'专业页：来源那一行不写了'", "'专业页：来源卡片不显示了（来源信息又消失）'"),
    ("'专业页：两行塌回一行（来源与配方名同一 y）'", "'专业页：色阶条塌到配方名那一行（两行叠一起）'"),
])

print('\ndone')
