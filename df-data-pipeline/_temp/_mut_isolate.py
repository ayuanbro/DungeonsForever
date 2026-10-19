# -*- coding: utf-8 -*-
"""变异「逐条隔离」体检 —— 按关键字挑一批变异，一条一条单独注入跑 harness。

为什么需要：「全量一次性注入」时断言之间会互相掩盖（同批别的变异先打红，某条自己
根本没被守到也看不出来）。改动一个功能后要确认「我为它新加的断言真的非恒真」，就得
一条一条来：单独注入 → 跑 df_dungeon_check.py → 看它变红没有、是真红还是崩出来的假红。

用法：
    python _mut_isolate.py 小动物          # 跑名字里含「小动物」的全部变异
    python _mut_isolate.py 掉落 图标       # 多个关键字（任一命中即跑）
    python _mut_isolate.py --list 小动物   # 只看命中哪些，不注入

判读：rc=1（harness 退出码非 0）+ FAIL>0 + 崩=False = 这条变异被保住。
      FAIL 行会逐条打出来，方便核对「红的是不是该红的那句」。
      崩=True（loadfile 返回 nil / Traceback）= 脏抓，锚点打成了 Lua 语法错，必须修。

跑完自动从 titan 端（干净）还原 beta；跑之前建议先 sync_beta.py --apply。
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import df_mut_check as M   # noqa: E402   （有 __main__ 守卫，导入安全）

HERE = M.HERE
BETA = M.BETA
TITAN = M.TITAN
PY = sys.executable


def run_one(name, spec):
    fname, old, new = M.split_spec(spec)
    p = os.path.join(BETA, *fname.split('/'))
    orig = open(p, 'rb').read()
    o, nw = M.to_file_style(old, orig), M.to_file_style(new, orig)
    if orig.count(o) != 1:
        print('  !! 锚点命中 %d 次 —— 锚点烂了（变异被静默跳过）' % orig.count(o))
        return False
    open(p, 'wb').write(orig.replace(o, nw))
    try:
        r = subprocess.run([PY, os.path.join(HERE, 'df_dungeon_check.py')],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace')
        out = (r.stdout or '') + (r.stderr or '')
    finally:
        shutil.copyfile(os.path.join(TITAN, *fname.split('/')), p)
    crash = 'loadfile 返回 nil' in out or 'Traceback' in out
    fails = [ln.strip() for ln in out.split('\n') if '[FAIL]' in ln]
    print('  [%s] rc=%s FAIL=%d 崩=%s' % (fname, r.returncode, len(fails), crash))
    for ln in fails[:12]:
        print('      ' + ln)
    if len(fails) > 12:
        print('      … 另 %d 条' % (len(fails) - 12))
    return (r.returncode != 0) and bool(fails) and not crash


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    listing = '--list' in sys.argv[1:]
    if not args:
        print('用法：python _mut_isolate.py <关键字> [关键字…]   （--list 只看不跑）')
        return 2
    picked = [(nm, sp) for nm, sp in M.MUTATIONS
              if any(k in nm for k in args)]
    if not picked:
        print('没有名字命中 %s 的变异' % args)
        return 2
    print('命中 %d 条：' % len(picked))
    for nm, _ in picked:
        print('  · ' + nm)
    if listing:
        return 0
    print('=' * 66)
    ok = 0
    for nm, sp in picked:
        print('— ' + nm)
        if run_one(nm, sp):
            ok += 1
    print('=' * 66)
    print('逐条有效 = %d / %d' % (ok, len(picked)))
    return 0 if ok == len(picked) else 1


if __name__ == '__main__':
    sys.exit(main())
