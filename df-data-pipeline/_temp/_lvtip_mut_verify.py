# -*- coding: utf-8 -*-
"""升级行提示框改版（2026-10-09）—— 自建逐条隔离变异验证。

为什么不用 df_check_new_muts.py：那个脚本开头会跑全量锚点体检，只要 harness 里
还有**别的开发线**留下的烂锚就直接 exit(1)。并发会话此刻正压在
Core/DungeonUI.lua / RaidUI / ExploreUI 上，全量烂锚 22 条，探针根本进不到
「注入 → 跑」那一步。这里只取本批变异、只认「注入后**新出现**的 FAIL」。

用法：python _lvtip_mut_verify.py
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DEV = r'D:\workspace\DungeonsForever'
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
PY = r'C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe'

import df_mut_check as M       # noqa: E402

WANT = '升级行：'
specs = {}
for _n, _s in M.MUTATIONS:
    if _n.startswith(WANT):
        specs[_n] = M.split_spec(_s)

# 行尾自愈：CRLF 目标的锚点里裸 \n 要补成 \r\n（ProfessionUI.lua 是纯 CRLF）
for _n in list(specs):
    _f, _o, _w = specs[_n]
    _src = open(os.path.join(DEV, *_f.split('/')), 'rb').read()
    if _src.count(b'\r\n') and _src.count(b'\n') == _src.count(b'\r\n'):
        specs[_n] = (_f,
                     _o.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'),
                     _w.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))

print('待验证 %d 条：' % len(specs))
for _n in sorted(specs):
    print('   · ' + _n)


def run():
    env = dict(os.environ, TF_BUILD='16001')
    r = subprocess.run([PY, os.path.join(HERE, 'df_dungeon_check.py')],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', env=env)
    out = (r.stdout or '') + (r.stderr or '')
    fails = [l.strip() for l in out.splitlines() if '[FAIL]' in l]
    tail = [l.strip() for l in out.splitlines() if l.strip().startswith('通过')]
    return fails, (tail[0] if tail else None), (r.stdout or '') + (r.stderr or '')


def restore(fname):
    src = os.path.join(DEV, *fname.split('/'))
    dst = os.path.join(BETA, *fname.split('/'))
    shutil.copyfile(src, dst)
    a = open(src, 'rb').read()
    b = open(dst, 'rb').read()
    assert a == b, '还原后与开发仓不一致：%s' % fname


# ── 基线 ──────────────────────────────────────────────────────────────────
base_fails, base_tail, _ = run()
print('\n基线（未变异）：%s，既有 FAIL %d 条（与本批无关，按差集判定）'
      % (base_tail or '无汇总行', len(base_fails)))

ok = bad = 0
for name in sorted(specs):
    fname, old, new = specs[name]
    p = os.path.join(BETA, *fname.split('/'))
    data = open(p, 'rb').read()
    c = data.count(old)
    if c != 1:
        print('\n[锚点异常] %s：命中 %d 次' % (name, c))
        bad += 1
        continue
    open(p, 'wb').write(data.replace(old, new))
    try:
        fails, tail, out = run()
        newf = [l for l in fails if l not in base_fails]
        print('\n' + '=' * 74)
        print('变异：%s   [%s]' % (name, fname))
        print('  %s   新 FAIL %d 条' % (tail or '（没解析到汇总行）', len(newf)))
        for l in newf[:6]:
            print('    ✗ ' + l[:150])
        if newf:
            print('  ✓ 变异被抓住（断言非恒真）')
            ok += 1
        else:
            print('  ✗✗ 变异未被抓住 —— 这条断言是白测，必须改')
            bad += 1
    finally:
        restore(fname)

print('\n' + '=' * 74)
print('结果：被抓住 %d 条 / 未抓住（或锚点异常） %d 条 / 共 %d 条' % (ok, bad, len(specs)))
sys.exit(1 if bad else 0)
