# -*- coding: utf-8 -*-
"""升级路线「四档色阶条 + 名字右侧来源卡片」（2026-10-09 需求三）—— 自建逐条隔离变异验证。

为什么不用 df_check_new_muts.py：那个脚本开头会跑全量锚点体检，只要 harness 里
还有**别的开发线**留下的烂锚就直接 exit(1)（此刻并发会话压在 Core/DungeonUI.lua /
RaidUI / ExploreUI 上，未修完的烂锚仍在）。这里只取本批变异、只认「注入后**新出现**的 FAIL」。

本批两条（都是本轮改动把注入点搬走而重锚的）：
  · 专业页：来源卡片不显示了（来源信息又消失）  → PD.PaintCard(r, spec.card) 改成 r, nil
  · 专业页：色阶条塌到配方名那一行（两行叠一起）→ 色阶条 y 从 PD.SB_DY 搬到 PD.TBL_NAME_DY

用法：python _skillbar_mut_verify.py
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

WANT = (
    '专业页：来源卡片不显示了（来源信息又消失）',
    '专业页：色阶条塌到配方名那一行（两行叠一起）',
    '专业页：等级竖线只剩一根（第二根丢了）',
    '专业页：终点竖线退回「向下吸」（106 又落回 100 那道交界）',
)
specs = {}
for _n, _s in M.MUTATIONS:
    if _n in WANT:
        specs[_n] = M.split_spec(_s)

missing = [w for w in WANT if w not in specs]
if missing:
    sys.exit('MUTATIONS 里找不到：%s' % missing)

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
    return fails, (tail[0] if tail else None), out


def restore(fname):
    src = os.path.join(DEV, *fname.split('/'))
    dst = os.path.join(BETA, *fname.split('/'))
    shutil.copyfile(src, dst)
    a = open(src, 'rb').read()
    b = open(dst, 'rb').read()
    assert a == b, '还原后与开发仓不一致：%s' % fname


# ── 前置：确保副本 == 开发仓（变异在副本上做，基线也在副本上跑）────────────────
for fname in sorted({s[0] for s in specs.values()}):
    src = os.path.join(DEV, *fname.split('/'))
    dst = os.path.join(BETA, *fname.split('/'))
    if open(src, 'rb').read() != open(dst, 'rb').read():
        shutil.copyfile(src, dst)
        print('[pre] 已把开发仓 %s 拷到副本（副本此前是旧的）' % fname)

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
