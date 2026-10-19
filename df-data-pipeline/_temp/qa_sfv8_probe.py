# -*- coding: utf-8 -*-
"""QA v8 非恒真探针（Edward）。

目的：独立证明 df_dungeon_check.py 里那条 v8 新增断言

    ★★ SFv8 设置弹窗不抢鼠标：无覆盖主窗的遮罩（主窗内容可悬停可点击 / 不再点外收起）

**真的能抓住「把覆盖主窗的遮罩塞回设置弹窗」这个变异**，而不是恒真。

为什么必须单独做（预存缺陷，本项目已知）：
  df_mut_check.py 把 214 条变异**一次性**注入同一份文件，只要求 nfail>0；而它的变异批次里
  只要有一条变异（例如删掉 DungeonUI.lua 里的 `function DG.QualOf(id)`）就会让
  df_dungeon_check.py 的 static_guard() 在 src.index(...) 处抛 ValueError → main() 早退，
  且 df_mut_check 只打印 harness 输出的**最后 2600 字符**。
  于是「mut 全绿/变红」既无法定位、也无法证明 SFv8 这一条本身有效。
  （本探针实测：未注入时 SFv8 [OK]；单独注入遮罩变异后 static_guard 不再崩、SFv8 [FAIL]。）

做法（与 _temp/qa_lf7_probe.py 同思路，仅针对 SFv8）：
  1. 把**交付树（源码侧）**复制到 _temp/_qa_sfv8_tree（副本树，产品文件零触碰）；
  2. 把 df_dungeon_check.py 的 ADDON 常量重定向到副本树；
  3. 未注入 → 跑一遍，SFv8 必须 OK（绿）；
  4. 注入「塞回全窗遮罩」变异（old/new 逐字取自 df_mut_check.py 第 ㉟ 条）→ 再跑，SFv8 必须 FAIL（红）；
  5. 还原副本、删除副本树与临时检查器。

只读产品文件；只写 _temp/ 下的副本与临时文件。
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# 交付树（源码侧）。MainFrame.lua 两侧 md5 一致，用源码侧（=交付物）即可，不碰实机 beta。
SRC = r'D:\workspace\DungeonsForever'
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
WORK = os.path.join(HERE, '_qa_sfv8_tree')

REL = os.path.join('Core', 'MainFrame.lua')
# ↓ 逐字取自 df_mut_check.py 的『设置弹窗：重新塞回覆盖主窗的遮罩』条目（第 ㉟ 条）
OLD = (b'ns.CloseSettings = function()\n'
       b'    if settingsPop then settingsPop:Hide() end\n')
NEW = (OLD +
       b'    local sh = CreateFrame("Frame", nil, f)\n'
       b'    sh:SetAllPoints(f)\n'
       b'    sh:SetFrameLevel(509)\n'
       b'    sh:EnableMouse(true)\n')

SFV8 = '★★ SFv8 设置弹窗不抢鼠标'


def build_tree():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    shutil.copytree(SRC, WORK,
                    ignore=shutil.ignore_patterns('_temp', '__pycache__', '.git', '.svn'))
    src = open(os.path.join(HERE, 'df_dungeon_check.py'), encoding='utf-8').read()
    assert BETA in src, 'df_dungeon_check.py 的 ADDON 常量没找到（结构变了吗）'
    out = os.path.join(HERE, '_qa_sfv8_dcheck.py')
    open(out, 'w', encoding='utf-8').write(src.replace(BETA, WORK))
    return out


def run(checker):
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    p = subprocess.run([sys.executable, checker], cwd=HERE, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode('utf-8', 'replace')


def sfv8_line(out):
    for l in out.split('\n'):
        if SFV8 in l:
            return l.strip()
    return None


def main():
    checker = build_tree()
    rel_path = os.path.join(WORK, REL)
    raw = open(rel_path, 'rb').read()

    print('=' * 72)
    print('SFv8 非恒真隔离探针  ·  副本树 = %s' % WORK)
    print('=' * 72)
    print('[锚点] df_mut_check 的第 ㉟ 条 old 片段在 %s 命中 %d 次（要求 == 1）'
          % (REL, raw.count(OLD)))
    if raw.count(OLD) != 1:
        print('!! 锚点不是唯一命中 —— 探针前提不成立')
        return 1
    print('[锚点] new != old ? %s' % (NEW != OLD))
    print('[锚点] new 里重新塞回: SetAllPoints(f)=%s  SetFrameLevel(509)=%s  EnableMouse(true)=%s'
          % (b'SetAllPoints(f)' in NEW, b'SetFrameLevel(509)' in NEW, b'EnableMouse(true)' in NEW))

    rc0, out0 = run(checker)
    line0 = sfv8_line(out0)
    ok0 = (line0 is not None and line0.startswith('[OK'))
    crash0 = ('ValueError' in out0) or ('Traceback' in out0)
    print()
    print('-' * 72)
    print('① 未注入（基线）  退出码=%d  static_guard 崩溃=%s' % (rc0, crash0))
    print('   SFv8 行：%s' % line0)
    print('   判定：%s' % ('绿（OK）—— 符合预期' if ok0 else '非绿！探针前提不成立'))
    print('-' * 72)

    open(rel_path, 'wb').write(raw.replace(OLD, NEW))
    rc1, out1 = run(checker)
    line1 = sfv8_line(out1)
    ok1 = (line1 is not None and line1.startswith('[FAIL'))
    crash1 = ('ValueError' in out1) or ('Traceback' in out1)
    print('② 注入变异后（塞回全窗遮罩）  退出码=%d  static_guard 崩溃=%s' % (rc1, crash1))
    print('   SFv8 行：%s' % line1)
    print('   判定：%s' % ('红（FAIL）—— 断言抓住了变异' if ok1 else '未变红！断言恒真/失效'))
    print('-' * 72)
    # 仅报告：注入后还有哪些断言变红（确认不是脏抓：不是语法错导致的整片红）
    fails = [l.strip() for l in out1.split('\n') if l.strip().startswith('[FAIL')]
    print('   注入后 harness 内 FAIL 总数 = %d' % len(fails))
    for l in fails[:12]:
        print('     ' + l)
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
