# -*- coding: utf-8 -*-
# 2026-10-09 v3：升级页底部「关联任务」区块退役（用户拍板 A 方案：纯展示零交互）
#  - ProfessionUI.lua：删渲染块 + 删 PD.QuestName/qname 死代码
#  - df_dungeon_check.py / mk_df_check.py：2 条断言改写（魔棒行保留、关联任务断言退役）
#  - df_mut_check.py：MUT_PROF_QUEST_BAREID 定义 + 注册行删除
import sys, py_compile

def rd(p):
    return open(p, 'rb').read().decode('utf-8')
def wr(p, s):
    open(p, 'wb').write(s.encode('utf-8'))

def sub1(s, old, new, tag):
    n = s.count(old)
    assert n == 1, '%s: anchor x%d' % (tag, n)
    return s.replace(old, new, 1)

BASE = r'D:\workspace\DungeonsForever'
changed = []

# ── 1) ProfessionUI.lua（CRLF）────────────────────────────────────────────
P = BASE + r'\Core\ProfessionUI.lua'
s = rd(P)
assert '关联任务' not in s and 'QuestName' not in s, 'ProfessionUI 状态异常'
wr(P, s); changed.append('ProfessionUI.lua')

# ── 2) 两条静态断言镜像（df_dungeon_check.py / mk_df_check.py）────────────
for name in ('df_dungeon_check.py', 'mk_df_check.py'):
    P = BASE + r'\_temp' + '\\' + name
    s = rd(P)
    if '关联任务一行一个' not in s:
        print('SKIP(已处理) ' + name); continue
    eol = '\r\n' if s.count('\r\n') > s.count('\n') - s.count('\r\n') else '\n'
    assert eol == '\n', name + ' 应为 LF'
    # ① 魔棒/关联任务解耦断言 → 只留魔棒（ rods 行还在用 FitL ）
    s = sub1(s, '#   ③单行行（魔棒 / 关联任务）不再拿「名称列宽」去截',
                '#   ③单行行（魔棒）不再拿「名称列宽」去截（关联任务区块已退役）', name + '#c')
    s = sub1(s, "ck('★★ 单行行（魔棒 / 关联任务）的截断宽与名称列解耦（名称列变窄不许跟着切任务名）',",
                "ck('★★ 单行行（魔棒）的截断宽与名称列解耦（名称列变窄不许跟着切任务名）',", name + '#l')
    s = sub1(s, "       and 'text = FitL(PD.QuestName(id))' in profui)",
                "       and 'text = FitL(DG.ItemName(rd[2]))' in profui)", name + '#c1')
    # ② 关联任务整行断言退役
    old = eol.join([
        "    ck('★★ 关联任务一行一个：任务名（客户端优先）在左、ID 在右',",
        "       'function PD.QuestName' in profui and 'text = FitL(PD.QuestName(id))' in profui",
        "       and 'right = format(\"#%d\", id)' in profui)",
    ])
    new = "    #   （2026-10-09 v3：升级页底部「关联任务」区块已退役，断言随块删除）"
    s = sub1(s, old, new, name + '#ck')
    assert 'PD.QuestName' not in s and '关联任务一行一个' not in s
    wr(P, s); changed.append(name)

# ── 3) 变异退役（df_mut_check.py）────────────────────────────────────────
P = BASE + r'\df_mut_check.py'
P = BASE + r'\_temp\df_mut_check.py'
s = rd(P)
if 'MUT_PROF_QUEST_BAREID' in s:
    start = s.index('MUT_PROF_QUEST_BAREID = (')
    end = s.index('MUT_PROF_LEARN_BACK', start)
    s = s[:start] + s[end:]
    s = sub1(s, "    ('专业页：关联任务退回裸 ID（任务名被摘）', MUT_PROF_QUEST_BAREID),\n", '', '注册行')
    assert 'MUT_PROF_QUEST_BAREID' not in s
    wr(P, s); changed.append('df_mut_check.py')
else:
    print('SKIP(已处理) df_mut_check.py')

py_compile.compile(BASE + r'\_temp\df_dungeon_check.py', doraise=True)
py_compile.compile(BASE + r'\_temp\mk_df_check.py', doraise=True)
py_compile.compile(BASE + r'\_temp\df_mut_check.py', doraise=True)
print('OK 修改:', ', '.join(changed))
