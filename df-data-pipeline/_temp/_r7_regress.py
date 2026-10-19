# -*- coding: utf-8 -*-
"""第七轮 ④ 收尾回归：生成器链（安全顺序）+ 快照零漂移核验。

安全顺序（★ enUS/Data_ClassGuide 的权威作者是 fc_guide，gen_enus_data 会写同名
文件，故 gen_enus_data 必须排在 fc_guide 之前）：
    fc_gen.py → gen_enus_data.py → gen_locales.py → fc_guide.py → gen_zhtw_data.py

每步前后对 Core/**/*.lua + Locales/*.lua + DungeonsForever.toc 取 md5 快照，
跑完打印「变更集」，核对是否 == 预期集合（3 个 ClassGuide 产物）。
输出：_temp/_r7_regress.txt
"""
import hashlib
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
PY = sys.executable
LOG = os.path.join(HERE, '_r7_regress.txt')

EXCLUDE_DIRS = {'_temp', '.git'}


def snap():
    out = {}
    for base in ('Core', 'Locales'):
        root = os.path.join(DF, base)
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in EXCLUDE_DIRS]
            for fn in fns:
                if not fn.endswith('.lua'):
                    continue
                p = os.path.join(dp, fn)
                rel = os.path.relpath(p, DF).replace('\\', '/')
                out[rel] = hashlib.md5(open(p, 'rb').read()).hexdigest()
    toc = os.path.join(DF, 'DungeonsForever.toc')
    if os.path.exists(toc):
        out['DungeonsForever.toc'] = hashlib.md5(open(toc, 'rb').read()).hexdigest()
    return out


CHAIN = [
    'fc_gen.py',
    'gen_enus_data.py',
    'gen_locales.py',
    'fc_guide.py',
    'gen_zhtw_data.py',
]


def run(name):
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    r = subprocess.run([PY, os.path.join(HERE, name)], cwd=HERE, env=env,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r


def main():
    out = []
    w = out.append
    w('=' * 78)
    w('第七轮 ④ 收尾回归 · 生成器链（安全顺序）+ 零漂移快照核验')
    w('=' * 78)
    w('')
    before = snap()
    w('快照基准：%d 个文件（Core/** + Locales/*.lua + toc）' % len(before))
    w('')

    rc_all = 0
    for name in CHAIN:
        r = run(name)
        tail = (r.stdout or '').strip().splitlines()
        w('▶ %s   exit=%d' % (name, r.returncode))
        for t in tail[-8:]:
            w('    ' + t)
        if r.stderr and r.stderr.strip():
            w('    [stderr] ' + r.stderr.strip()[:400])
        if r.returncode != 0:
            rc_all = r.returncode
        w('')

    after = snap()
    changed = sorted(k for k in before if k in after and before[k] != after[k])
    added = sorted(k for k in after if k not in before)
    removed = sorted(k for k in before if k not in after)

    w('-' * 78)
    w('变更集（跑完全链后 vs 基准）：')
    w('  内容变化 %d 个：' % len(changed))
    for k in changed:
        w('    MOD  %s' % k)
    w('  新增 %d 个：' % len(added))
    for k in added:
        w('    ADD  %s' % k)
    w('  删除 %d 个：' % len(removed))
    for k in removed:
        w('    DEL  %s' % k)
    w('')

    expected = {
        'Core/Data/Data_ClassGuide.lua',
        'Core/Data/enUS/Data_ClassGuide.lua',
        'Core/Data/zhTW/Data_ClassGuide.lua',
    }
    got = set(changed) | set(added) | set(removed)
    w('预期变更集（本轮 Skyborne/中英夹杂 只应动这 3 个）：')
    for k in sorted(expected):
        w('    EXP  %s' % k)
    w('')
    if got == expected:
        w('★ 零漂移核验：PASS —— 实际变更集 == 预期集（其余全部字节不变）')
    elif got < expected:
        w('★ 零漂移核验：PASS（子集）—— 实际 %s ⊂ 预期' % sorted(got))
    else:
        w('★ 零漂移核验：需核对 —— 额外变更 %s' % sorted(got - expected))
    w('★ 生成器链耗时/退出码：exit=%d' % rc_all)

    text = '\n'.join(out) + '\n'
    io.open(LOG, 'w', encoding='utf-8', newline='\n').write(text)
    print(text)
    return rc_all


if __name__ == '__main__':
    sys.exit(main())
