# -*- coding: utf-8 -*-
"""QA(严过关) 定向复核 A：strip_comments.py CLI 守卫。输出写文件。"""
import io, os, sys, subprocess, hashlib
DF = r'D:\workspace\DungeonsForever'
HERE = os.path.join(DF, '_temp')
PY = r'C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe'
sys.path.insert(0, HERE)
import strip_comments as S

L = []
def w(x=''): L.append(str(x))

# ============================ A1: strip_text 行为 ============================
w('#' * 78)
w('# A1 · strip_text() 行为（属性断言）')
w('#' * 78)

def prop(name, cond, detail=''):
    w('  [%s] %s  %s' % ('OK ' if cond else 'FAIL', name, detail))

# P1 头部块保留 + body 注释删
inp = '-- H1\n-- H2\nlocal a = 1\n-- mid\nlocal b = 2\n'
out, cmt, tail = S.strip_text(inp)
prop('P1 头部块保留', out.startswith('-- H1\n-- H2') and 'local a = 1' in out and 'local b = 2' in out)
prop('P1b 中部整行注释被删', '-- mid' not in out, '(cmt=%d tail=%d)' % (cmt, tail))

# P2 字符串里的 -- 不被误判
inp2 = '-- H\nlocal s = "a--b" -- tail\n'
out2, c2, t2 = S.strip_text(inp2)
prop('P2 字符串里 "--" 保留', '"a--b"' in out2 and 'tail' not in out2, repr(out2))

# P3 幂等
inp3 = '-- H\n-- x\nlocal a=1 -- t\nlocal b=2\n'
o3a, _, _ = S.strip_text(inp3)
o3b, _, _ = S.strip_text(o3a)
prop('P3 幂等', o3a == o3b)

# P4 CRLF 保留
inp4 = '-- H\r\nlocal a=1 -- t\r\nlocal b=2\r\n'
out4, _, _ = S.strip_text(inp4)
prop('P4 CRLF 保留', '\r\n' in out4 and '\n' not in out4.replace('\r\n', ''), repr(out4))

# P5 长注释 [[ ]]
inp5 = '-- H\n--[[ long\ncomment ]]\nlocal a=1\n'
out5, _, _ = S.strip_text(inp5)
prop('P5 长注释被删/头块保留', 'long' not in out5 and out5.startswith('-- H'), repr(out5))

# 记录 strip_text / comment_spans 源码哈希（供与改动前比对）
import inspect
h_strip = hashlib.md5(inspect.getsource(S.strip_text).encode()).hexdigest()[:12]
h_span = hashlib.md5(inspect.getsource(S.comment_spans).encode()).hexdigest()[:12]
h_walk = hashlib.md5(inspect.getsource(S.walk).encode()).hexdigest()[:12]
w('  strip_text  源码 md5=%s' % h_strip)
w('  comment_spans 源码 md5=%s' % h_span)
w('  walk        源码 md5=%s' % h_walk)

# ============================ A2: is_generated 分类 ============================
w()
w('#' * 78)
w('# A2 · is_generated() 全量分类（Core + Locales）')
w('#' * 78)

def all_lua(rootdir):
    out = []
    for dp, _, fn in os.walk(rootdir):
        for f in sorted(fn):
            if f.endswith('.lua'):
                out.append(os.path.join(dp, f))
    return out

files = all_lua(os.path.join(DF, 'Core')) + all_lua(os.path.join(DF, 'Locales'))

def owner(rel):
    r = rel.replace('\\', '/')
    if r in ('Core/Data/Data_Professions.lua', 'Core/Data/Data_ProfRecipes.lua',
             'Core/Data/Data_ProfLeveling.lua', 'Core/Data/Data_ProfGathering.lua'):
        return 'fc_gen'
    if r in ('Core/Data/Data_ClassGuide.lua', 'Core/Data/enUS/Data_ClassGuide.lua'):
        return 'fc_guide'
    if r == 'Locales/zhCN.lua':
        return 'gen_locales'
    if r == 'Locales/zhTW.lua':
        return 'gen_zhtw'
    if r == 'Locales/enUS.lua':
        return 'HAND?'
    if r.startswith('Core/Data/enUS/Data_'):
        return 'gen_enus_data'
    if r.startswith('Core/Data/zhTW/Data_'):
        return 'gen_zhtw_data'
    return 'HAND'

gen_like = ('fc_gen', 'fc_guide', 'gen_locales', 'gen_zhtw', 'gen_enus_data', 'gen_zhtw_data')

false_neg = []   # 生成物但判为手写（漏）
false_pos = []   # 手写但判为生成物（外溢）
rows = []
for p in sorted(files):
    rel = os.path.relpath(p, DF).replace('\\', '/')
    gen = S.is_generated(p)
    head = S.head_comment_block(p)
    mark = [m for m in S.GEN_MARKERS if m in head]
    ow = owner(rel)
    rows.append((rel, gen, ow, mark, head.splitlines()[:1]))
    if ow in gen_like and not gen:
        false_neg.append((rel, ow, mark))
    if ow == 'HAND' and gen:
        false_pos.append((rel, mark))

w('共 %d 个 .lua' % len(rows))
w()
w('--- 逐文件（rel | is_generated | 归属 | 命中标记 | 首行）---')
for rel, gen, ow, mark, h1 in rows:
    w('  %-42s gen=%-5s %-14s %-30s %s'
      % (rel, gen, ow, ','.join(mark) if mark else '-', (h1[0][:40] if h1 else '')))

w()
w('★ 漏判（生成物被判为手写 → 注释会残留）: %d' % len(false_neg))
for rel, ow, mark in false_neg:
    w('    !! %s  (归属 %s, 标记 %s)' % (rel, ow, mark))
w('★ 误判（手写件被判为生成物 → 有外溢风险）: %d' % len(false_pos))
for rel, mark in false_pos:
    w('    ?? %s  (标记 %s)' % (rel, mark))

# ============================ A3: 显式点名生成物 ============================
w()
w('#' * 78)
w('# A3 · 显式点名生成物 / 默认范围 的 CLI 实测')
w('#' * 78)

def run_cli(args):
    r = subprocess.run([PY, os.path.join(HERE, 'strip_comments.py'), '--dry-run'] + args,
                       cwd=DF, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout + r.stderr

w('--- (a) 显式点名 Core/Data/Data_Professions.lua ---')
w(run_cli(['Core/Data/Data_Professions.lua']))
w('--- (b) 显式点名 Locales/zhCN.lua ---')
w(run_cli(['Locales/zhCN.lua']))
w('--- (c) 默认（无参数）---')
w(run_cli([]))
w('--- (d) 显式目录 Core Locales ---')
w(run_cli(['Core', 'Locales']))

text = '\n'.join(L) + '\n'
io.open(os.path.join(HERE, '_qa2_cli_report.txt'), 'w', encoding='utf-8', newline='\n').write(text)
print('written')
