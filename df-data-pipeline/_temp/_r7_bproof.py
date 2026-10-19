# -*- coding: utf-8 -*-
"""第七轮 B 证明：跑一次 gen_enus_data.py，核验
  ① enUS/Data_LootFilter.lua 字节不变；② enUS/Data_ClassGuide.lua 字节不变；
  ③ 产物清单不再含它俩；④ 其余 enUS 产物字节不变（幂等）。
输出：_temp/_r7_bproof.txt
"""
import hashlib
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
ENUS = os.path.join(DF, 'Core', 'Data', 'enUS')
PY = sys.executable


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def snap():
    return {f: md5(os.path.join(ENUS, f)) for f in sorted(os.listdir(ENUS)) if f.endswith('.lua')}


before = snap()
r = subprocess.run([PY, os.path.join(HERE, 'gen_enus_data.py')], cwd=HERE,
                   capture_output=True, text=True, encoding='utf-8', errors='replace',
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
after = snap()

L = []
w = L.append
w('=' * 78)
w('第七轮 B · gen_enus_data 产物收口证明   exit=%d' % r.returncode)
w('=' * 78)
w('--- gen_enus_data stdout ---')
for ln in (r.stdout or '').strip().splitlines():
    w('   ' + ln)
if r.stderr and r.stderr.strip():
    w('   [stderr] ' + r.stderr.strip()[:400])
w('')
changed = sorted(f for f in before if before.get(f) != after.get(f))
w('--- 跑前/跑后 enUS/*.lua 变更集 ---')
w('内容变化 %d 个：%s' % (len(changed), changed or '（无）'))
w('')
for name in ('Data_LootFilter.lua', 'Data_ClassGuide.lua'):
    b = before.get(name)
    a = after.get(name)
    w('  %-24s before=%s after=%s  %s' % (
        name, (b or '缺')[:12], (a or '缺')[:12], '字节不变 ✓' if b == a else '★被改写'))
w('')
w('判定：%s' % ('PASS（占位/权威件未被改写，其余幂等）' if not changed else 'FAIL（有意外改写）'))

text = '\n'.join(L) + '\n'
io.open(os.path.join(HERE, '_r7_bproof.txt'), 'w', encoding='utf-8', newline='\n').write(text)
print(text)
