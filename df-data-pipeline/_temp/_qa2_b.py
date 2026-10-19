# -*- coding: utf-8 -*-
"""QA(严过关) 定向复核 B：gen_enus_data ENUS_EXCLUDE + 残余注释/归属交叉核对。写文件。"""
import io, os, sys, shutil, hashlib, subprocess
DF = r'D:\workspace\DungeonsForever'
HERE = os.path.join(DF, '_temp')
PY = r'C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe'
BAK = os.path.join(HERE, '_qa2_corebak')
L = []
def w(x=''): L.append(str(x))

def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()

def snap(root):
    d = {}
    for dp, _, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            d[os.path.relpath(p, DF).replace('\\', '/')] = md5(p)
    return d

CORE = os.path.join(DF, 'Core')

# ---------- 备份 Core ----------
if os.path.exists(BAK):
    shutil.rmtree(BAK)
shutil.copytree(CORE, BAK)
before = snap(CORE)
w('=== B · gen_enus_data.py ENUS_EXCLUDE 复核 ===')
w('备份 Core → %s（%d 文件）' % (BAK, len(before)))
w('跑前 enUS/Data_LootFilter.lua md5 = %s' % before.get('Core/Data/enUS/Data_LootFilter.lua', 'NONE'))
w('跑前 enUS/Data_ClassGuide.lua  md5 = %s' % before.get('Core/Data/enUS/Data_ClassGuide.lua', 'NONE'))
w()

r = subprocess.run([PY, os.path.join(HERE, 'gen_enus_data.py')],
                   cwd=HERE, capture_output=True, text=True, encoding='utf-8', errors='replace')
w('--- gen_enus_data.py stdout ---')
w(r.stdout.strip())
w('--- stderr ---'); w(r.stderr.strip())
w('exit=%d' % r.returncode)
w()

after = snap(CORE)
changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
only_after = sorted(k for k in after if k not in before)
only_before = sorted(k for k in before if k not in after)

w('--- 跑后 vs 跑前：变更文件 ---')
w('变更 %d 个：' % len(changed))
for k in changed:
    w('   MOD %s  (bef=%s -> aft=%s)' % (k, (before.get(k) or '')[:12], (after.get(k) or '')[:12]))
w('新增 %d：%s' % (len(only_after), only_after))
w('删除 %d：%s' % (len(only_before), only_before))
w()
tgt = 'Core/Data/enUS/Data_LootFilter.lua'
tgt2 = 'Core/Data/enUS/Data_ClassGuide.lua'
w('★ 目标文件字节不变？')
w('   %s : %s' % (tgt, 'YES(未被动)' if before.get(tgt) == after.get(tgt) and tgt in after else 'NO'))
w('   %s : %s' % (tgt2, 'YES(未被动)' if before.get(tgt2) == after.get(tgt2) and tgt2 in after else 'NO'))
w()
w('★ 其余 enUS 产物是否仍被正常生成（应有非空且与跑前一致/幂等）:')
enus = sorted(k for k in after if k.startswith('Core/Data/enUS/') and k.endswith('.lua'))
for k in enus:
    w('   %-42s %s' % (k, 'same' if before.get(k) == after.get(k) else 'CHANGED'))

# ---------- 还原 ----------
# 删除新增、还原变更/删除
for k in only_after:
    os.remove(os.path.join(DF, k))
for k in set(changed) | set(only_before):
    src = os.path.join(BAK, k[len('Core/'):])
    if os.path.exists(src):
        dst = os.path.join(DF, k)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
after2 = snap(CORE)
w()
w('=== 还原后校验: 与跑前一致? %s ===' % ('YES' if after2 == before else 'NO(MISMATCH)'))
if after2 != before:
    for k in sorted(set(after2) | set(before)):
        if after2.get(k) != before.get(k):
            w('   !! %s bef=%s aft=%s' % (k, (before.get(k) or '')[:12], (after2.get(k) or '')[:12]))

# ---------- 残余注释扫描 ----------
w()
w('=== 残余“正文注释”扫描（body comments beyond header）===')
sys.path.insert(0, HERE)
import strip_comments as S
def body_comment_lines(p):
    t = io.open(p, encoding='utf-8', errors='replace').read()
    new, cmt, tail = S.strip_text(t)
    return cmt, tail, (new != t)
need = []
for dp, _, fn in os.walk(CORE):
    for f in sorted(fn):
        if f.endswith('.lua'):
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, DF).replace('\\', '/')
            cmt, tail, diff = body_comment_lines(p)
            if diff:
                need.append((rel, cmt, tail, S.is_generated(p)))
w('需清理（strip 会改动）的 .lua = %d' % len(need))
for rel, cmt, tail, gen in need:
    w('   %-42s 整行注释 %d / 行尾 %d  is_generated=%s' % (rel, cmt, tail, gen))

# ---------- 归属：Data_DungeonEntry/Guide/Dungeons 是否生成物 ----------
w()
w('=== 归属交叉核对：谁生成 Data_DungeonEntry/Guide/Dungeons ===')
import glob, re
for name in ['Data_DungeonEntry.lua', 'Data_DungeonGuide.lua', 'Data_Dungeons.lua']:
    hits = []
    for pyf in glob.glob(os.path.join(HERE, '**', '*.py'), recursive=True):
        try:
            t = io.open(pyf, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        if name in t and ('open(' in t or '.lua' in t):
            hits.append(os.path.basename(pyf))
    w('   %-24s 引用它的 _temp 脚本: %s' % (name, hits[:8] if hits else '(无)'))

io.open(os.path.join(HERE, '_qa2_b_report.txt'), 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
print('done')
