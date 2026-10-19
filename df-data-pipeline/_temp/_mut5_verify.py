# -*- coding: utf-8 -*-
"""五稿新增变异的逐条注入体检（TITAN 缺失时的等价跑法）。

背景：_mut_isolate.py 注入 BETA 后从 TITAN 还原，但 _classic_titan_ 端当前没有
本插件 ⇒ 该跑法不可用。本脚本改从 **dev 仓**还原（先校验 dev 与 BETA 逐字节一致，
不一致直接拒绝跑），效果等价且兜底更近。

流程：备份 → 逐条注入 BETA / 跑 df_dungeon_check / 还原 → 末尾哈希复核。
判读：rc!=0 且 FAIL>0 且未崩 = 该变异被守住。

用法：python _mut5_verify.py 五稿
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_mut_check as M   # noqa: E402

DEV = M.DF
BETA = M.BETA
PY = sys.executable
HARNESS = os.path.join(HERE, 'df_dungeon_check.py')


def sha(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def main():
    keys = [a for a in sys.argv[1:] if not a.startswith('--')] or ['五稿']
    muts = [(n, s) for n, s in M.MUTATIONS if any(k in n for k in keys)]
    if not muts:
        print('没有命中关键字的变异'); return 1

    # ── 前置校验：涉及的文件 dev 与 BETA 必须逐字节一致，否则拒绝跑 ──
    files = sorted({M.split_spec(s)[0] for _, s in muts})
    backup = {}
    for f in files:
        pd, pb = os.path.join(DEV, *f.split('/')), os.path.join(BETA, *f.split('/'))
        if not os.path.isfile(pd):
            print('!! dev 缺文件：%s' % f); return 1
        if sha(pd) != sha(pb):
            print('!! dev 与 BETA 不一致，先 deploy 再跑：%s' % f); return 1
        backup[f] = open(pb, 'rb').read()
    print('备份 %d 个文件（dev == BETA 校验通过）' % len(backup))

    ok = fail = 0
    try:
        for name, spec in muts:
            fname, old, new = M.split_spec(spec)
            p = os.path.join(BETA, *fname.split('/'))
            raw = open(p, 'rb').read()
            o, nw = M.to_file_style(old, raw), M.to_file_style(new, raw)
            if raw.count(o) != 1:
                print('[SKIP] %-55s 锚点命中 %d 次' % (name[:55], raw.count(o)))
                fail += 1
                continue
            open(p, 'wb').write(raw.replace(o, nw))
            try:
                r = subprocess.run([PY, HARNESS], capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', cwd=HERE)
                out = (r.stdout or '') + (r.stderr or '')
            finally:
                open(p, 'wb').write(backup[fname])   # 立即还原
            crash = 'loadfile 返回 nil' in out or 'Traceback' in out
            fails = [ln.strip() for ln in out.split('\n') if '[FAIL]' in ln]
            held = (r.returncode != 0) and bool(fails) and not crash
            print('[%s] %s  rc=%d FAIL=%d 崩=%s' %
                  ('OK ' if held else 'BAD', name[:55], r.returncode, len(fails), crash))
            for ln in fails[:3]:
                print('        ' + ln[:110])
            ok, fail = ok + (1 if held else 0), fail + (0 if held else 1)
    finally:
        for f, data in backup.items():
            open(os.path.join(BETA, *f.split('/')), 'wb').write(data)
        # 末尾复核：必须与备份逐字节一致
        for f in backup:
            p = os.path.join(BETA, *f.split('/'))
            if open(p, 'rb').read() != backup[f]:
                print('!! 还原失败：%s' % f); return 1
        print('还原复核通过（BETA == 备份）')

    print('结论：%d 守住 / %d 失守' % (ok, fail))
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
