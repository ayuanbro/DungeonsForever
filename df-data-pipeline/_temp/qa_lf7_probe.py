# -*- coding: utf-8 -*-
"""QA v7 非恒真探针（Edward）。

目的：独立证明 df_dungeon_check.py 里那条新断言

    ★★ LFv7 面板不抢鼠标：无覆盖主窗的遮罩（主窗内容可悬停可点击 / 不再点外收起）

**真的能抓住「把覆盖主窗的遮罩塞回去」这个变异**，而不是恒真。

为什么必须单独做：
  df_mut_check.py 把 203 条变异**一次性**注入同一份文件，只要求 nfail>0；且它的变异批次里
  一旦某条较早的变异让 df_dungeon_check 早退（例如静态段 .index() 抛错、或某 Lua 文件
  loadfile 失败 → main() 提前 return），后面那批静态断言（含 LFv7）就**根本没被执行**。
  于是「mut 全绿/变红」并不能证明 LFv7 本身有效。

做法（与 _temp/_mf_iso_probe.py 同思路，但只针对 LFv7）：
  1. 把交付树复制到 _temp/_qa_lf7_tree（副本树，产品文件零触碰）；
  2. 把 df_dungeon_check.py 的 ADDON 常量重定向到副本树；
  3. 未注入 → 跑一遍，LFv7 必须 OK（绿）；
  4. 注入「塞回全窗遮罩」变异（old/new 逐字取自 df_mut_check.py）→ 再跑，LFv7 必须 FAIL（红）；
  5. 还原副本、删除副本树与临时检查器。

只读产品文件；只写 _temp/ 下的副本与临时文件。
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# 交付树（源码侧）。LootFilterUI.lua 两侧 md5 一致，用哪侧都行；这里用源码侧（=交付物）。
SRC = r'D:\workspace\DungeonsForever'
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
WORK = os.path.join(HERE, '_qa_lf7_tree')

REL = os.path.join('Core', 'LootFilterUI.lua')
# ↓ 逐字取自 df_mut_check.py 的『装备过滤面板：重新塞回覆盖主窗的遮罩』条目
OLD = (b'    local cfg = {\n'
       b'        popup = popup,\n'
       b'        page = 0,\n'
       b'        collapsed = {},\n')
NEW = (b'    local cfg = { popup = popup, page = 0, collapsed = {},\n'
       b'    cfg.shield = CreateFrame("Frame", nil, host)\n'
       b'    cfg.shield:SetAllPoints(host)\n'
       b'    cfg.shield:EnableMouse(true)\n')

LFV7 = 'LFv7 面板不抢鼠标'


def build_tree():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    shutil.copytree(SRC, WORK,
                    ignore=shutil.ignore_patterns('_temp', '__pycache__', '.git', '.svn'))
    src = open(os.path.join(HERE, 'df_dungeon_check.py'), encoding='utf-8').read()
    assert BETA in src, 'df_dungeon_check.py 的 ADDON 常量没找到（结构变了吗）'
    out = os.path.join(HERE, '_qa_lf7_dcheck.py')
    open(out, 'w', encoding='utf-8').write(src.replace(BETA, WORK))
    return out


def run(checker):
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    p = subprocess.run([sys.executable, checker], cwd=HERE, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode('utf-8', 'replace')


def lfv7_line(out):
    for l in out.split('\n'):
        if LFV7 in l:
            return l.strip()
    return None


def main():
    checker = build_tree()
    rel_path = os.path.join(WORK, REL)
    raw = open(rel_path, 'rb').read()

    print('=' * 72)
    print('LFv7 非恒真隔离探针  ·  副本树 = %s' % WORK)
    print('=' * 72)
    print('[锚点] df_mut_check 的 LFv7 变异 old 片段在 %s 命中 %d 次（要求 == 1）'
          % (REL, raw.count(OLD)))
    if raw.count(OLD) != 1:
        print('!! 锚点不是唯一命中 —— 探针前提不成立')
        return 1
    print('[锚点] new != old ? %s' % (NEW != OLD))
    print('[锚点] new 里重新塞回: SetAllPoints(host)=%s  cfg.shield=%s'
          % (b'SetAllPoints(host)' in NEW, b'cfg.shield' in NEW))

    rc0, out0 = run(checker)
    line0 = lfv7_line(out0)
    ok0 = (line0 is not None and line0.startswith('[OK'))
    print()
    print('-' * 72)
    print('① 未注入（基线）  退出码=%d' % rc0)
    print('   LFv7 行：%s' % line0)
    print('   判定：%s' % ('绿（OK）—— 符合预期' if ok0 else '非绿！探针前提不成立'))
    print('-' * 72)

    open(rel_path, 'wb').write(raw.replace(OLD, NEW))
    rc1, out1 = run(checker)
    line1 = lfv7_line(out1)
    ok1 = (line1 is not None and line1.startswith('[FAIL'))
    print('② 注入变异后（塞回全窗遮罩）  退出码=%d' % rc1)
    print('   LFv7 行：%s' % line1)
    print('   判定：%s' % ('红（FAIL）—— 断言抓住了变异' if ok1 else '未变红！断言恒真/失效'))
    print('-' * 72)

    open(rel_path, 'wb').write(raw)  # 还原副本
    shutil.rmtree(WORK, ignore_errors=True)
    try:
        os.remove(checker)
    except OSError:
        pass
    print('副本树 + 临时检查器已删除；产品文件未触碰。')

    verdict = ok0 and ok1
    print('RESULT = %s  （基线绿=%s / 注入后红=%s）'
          % ('PASS（非恒真已证）' if verdict else 'FAIL', ok0, ok1))
    return 0 if verdict else 1


if __name__ == '__main__':
    sys.exit(main())
