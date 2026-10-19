# -*- coding: utf-8 -*-
# 2026-10-10：check/mut 脚本补丁（自适应行尾：目标文件 LF）
import io

def load(p):
    return open(p, "rb").read()

def save(p, b):
    open(p, "wb").write(b)

def rep1(data, old, new):
    for o in (old.encode("utf-8"), old.encode("utf-8").replace(b"\n", b"\r\n")):
        n = new.encode("utf-8").replace(b"\n", o[: len(o) - len(old.encode("utf-8").replace(b"\n", b"\r\n"))]) if False else new.encode("utf-8")
        if o != old.encode("utf-8"):
            n = new.encode("utf-8").replace(b"\n", b"\r\n")
        c = data.count(o)
        if c == 1:
            return data.replace(o, n)
    raise AssertionError("anchor not unique: %r" % old[:60])


# ---- df_dungeon_check.py：两条静态断言（挂在 NAME_FIT 双口径块后） ----
p1 = r"D:/workspace/DungeonsForever/_temp/df_dungeon_check.py"
d = load(p1)
d = rep1(
    d,
    """       and 'nameW - (s.is_new and PD.RECIPE_BADGE_W or 0)' not in profui)
""",
    """       and 'nameW - (s.is_new and PD.RECIPE_BADGE_W or 0)' not in profui)
    ck('★★ 配方/可制造名称按产物物品品质着色（qItem + 会话缓存 QualCached；无品质退默认色）',
       'function PD.QualCached' in profui
       and 'qItem = r[2],' in profui and 'qItem = c[2],' in profui
       and 'if not ncol and spec.qItem then' in profui
       and 'if q then ncol = { DG.QColor(q) } end' in profui)
    ck('★★ 材料段名按材料品质着色（附魔/可制造也挂 matSegs；…纯段无 id 保持默认）',
       'if q then scol = { DG.QColor(q) } end' in profui
       and 'fs:SetTextColor(Unpack(scol))' in profui
       and profui.count('matSegs = matSg,') == 2)
""",
)
save(p1, d)

# ---- df_mut_check.py：两条变异 + 注册 ----
p2 = r"D:/workspace/DungeonsForever/_temp/df_mut_check.py"
d = load(p2)
d = rep1(
    d,
    """MUT_PROF_MATTAIL_GONE = ('Core/ProfessionUI.lua', (
    '                local piece2 = PD.MatIconTex(m[1], px) .. PD.Fit(name, fs, avail)\\n'.encode('utf-8'),
    '                local piece2 = PD.MatIconTex(m[1], px) .. name -- MUT: tail refit gone\\n'.encode('utf-8')))
""",
    """MUT_PROF_MATTAIL_GONE = ('Core/ProfessionUI.lua', (
    '                local piece2 = PD.MatIconTex(m[1], px) .. PD.Fit(name, fs, avail)\\n'.encode('utf-8'),
    '                local piece2 = PD.MatIconTex(m[1], px) .. name -- MUT: tail refit gone\\n'.encode('utf-8')))

# 2026-10-10 用户：配方名/材料名按物品品质着色
MUT_PROF_QNAME_GONE = ('Core/ProfessionUI.lua', (
    '    if not ncol and spec.qItem then'.encode('utf-8'),
    '    if false then -- MUT: name quality color gone'.encode('utf-8')))
MUT_PROF_QSEG_GONE = ('Core/ProfessionUI.lua', (
    '            if q then scol = { DG.QColor(q) } end'.encode('utf-8'),
    '            scol = col -- MUT: material quality color gone'.encode('utf-8')))
""",
)
d = rep1(
    d,
    "    ('专业页：材料末段整段丢弃回潮（右缘留白）', MUT_PROF_MATTAIL_GONE),\n",
    """    ('专业页：材料末段整段丢弃回潮（右缘留白）', MUT_PROF_MATTAIL_GONE),
    ('专业页：配方名品质色断开', MUT_PROF_QNAME_GONE),
    ('专业页：材料段品质色断开', MUT_PROF_QSEG_GONE),
""",
)
save(p2, d)
print("check/mut patch OK")
