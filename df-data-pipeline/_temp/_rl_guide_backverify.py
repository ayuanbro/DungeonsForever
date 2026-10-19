# -*- coding: utf-8 -*-
"""攻略页断言的反向验证：逐条注入变异，确认冒烟脚本真的报 FAIL，再还原。

每条变异都走：注入源码 → sync_beta → 跑 _rl_guide_smoke.py → 记录 → 还原 → sync_beta。
"""
import io
import os
import subprocess
import sys

ROOT = r'D:\workspace\DungeonsForever'
PY = r'C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe'
UI = os.path.join(ROOT, 'Core', 'DungeonUI.lua')
SMOKE = os.path.join(ROOT, '_temp', '_rl_guide_smoke.py')
SYNC = os.path.join(ROOT, '_temp', 'sync_beta.py')
BAK = os.path.join(ROOT, '_temp', '_rl_bak2', 'DungeonUI.guide.lua.bak')

MUTS = [
    ('MUT_GUIDE_TAB_GONE',
     ', { key = "guide", text = L["攻略"] }', ''),
    ('MUT_GUIDE_DISPATCH_LOOT',
     'elseif isGuide then\n        U:RenderDungeonGuide()',
     'elseif isGuide then\n        U:RenderDungeonLoot()'),
    ('MUT_GUIDE_KEEP_SCROLL',
     'SetShown(not isQuest and not isGuide)', 'SetShown(not isQuest)'),
    ('MUT_GUIDE_BOSSNAME_LITERAL',
     'if loot[i][1] == en then return loot[i][2] or en end',
     'if loot[i][1] == en then return en end'),
]

raw0 = io.open(UI, 'rb').read()
io.open(BAK, 'wb').write(raw0)


def write(body):
    io.open(UI, 'wb').write(body)


def sync():
    subprocess.run([PY, SYNC, '--apply'], cwd=ROOT, capture_output=True)


def run_smoke():
    p = subprocess.run([PY, SMOKE], cwd=os.path.join(ROOT, '_temp'),
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    fails = [l.strip() for l in (p.stdout or '').split('\n') if '[FAIL]' in l]
    return p.returncode, fails


results = []
try:
    for name, old, new in MUTS:
        src = raw0.decode('utf-8').replace('\r\n', '\n')
        if src.count(old) != 1:
            print('!! [%s] 注入锚点命中 %d 次' % (name, src.count(old)))
            sys.exit(1)
        write(src.replace(old, new).replace('\n', '\r\n').encode('utf-8'))
        sync()
        rc, fails = run_smoke()
        caught = (rc != 0 and len(fails) > 0)
        results.append((name, caught, fails))
        print('[%s] %s' % ('抓住' if caught else '!! 漏抓 !!', name))
        for f in fails:
            print('        ' + f)
        # 还原
        write(raw0)
        sync()
finally:
    write(raw0)
    sync()

print('\n还原完成，复跑一次确认全绿：')
rc, fails = run_smoke()
print('  exit=%d  失败行=%d' % (rc, len(fails)))
bad = [r for r in results if not r[1]]
print('\n变异总数 %d，漏抓 %d' % (len(results), len(bad)))
sys.exit(1 if bad or rc != 0 else 0)
