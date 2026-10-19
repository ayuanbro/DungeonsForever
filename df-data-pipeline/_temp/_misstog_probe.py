# -*- coding: utf-8 -*-
"""非恒真证明（2026-10-11 「仅显示缺失」开关左侧文字标签）：把改动前的两种形态注回去，
新断言必须变红。

两种注入：
  ① 标签根本没建（删掉 missLab 的四行）—— 用户要的「左边写上文字」没落实；
  ② 让位量写死常数（`labW + 48` → `96`）—— enUS 的宽标签会压表头。

★ 为什么跑 **harness（df_dungeon_check.py）** 而不是 `_hud_routemode_smoke.py`：
  注入①会让 `f.shop.missLab:SetWordWrap(...)` 索引 nil ⇒ **Build 当场抛异常**。
  冒烟是「先驱动 Build、再跑断言」，Build 一炸就一条 `[FAIL]` 都不输出 ⇒
  看起来「0 条新增失败」= 误判白测（PROF_PITFALLS 的「断言段自己不许炸」同族）。
  harness 把 Lua 块异常**记成一条 FAIL 后继续**跑静态断言 —— 静态断言正是本批
  的主守护，所以用它才测得准。

隔离副本树 + DF_ADDON_ROOT 重定向；只碰临时副本，产品文件零改动。

用法：python _temp/_misstog_probe.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
PY = sys.executable

#   锚点用 UTF-8 字节（b'…中文…' 是 Python 语法错，见 PROF_PITFALLS）
OLD_LABEL = ('    f.shop.missLab = MakeFS(f.shop, 14, C_TEXT, "RIGHT")\n'
             '    f.shop.missLab:SetWordWrap(false)\n'
             '    f.shop.missLab:SetPoint("RIGHT", f.shop.missTog, "LEFT", -4, 0)\n'
             '    f.shop.missLab:SetText(L["\u4ec5\u663e\u793a\u7f3a\u5931"])\n').encode('utf-8')
OLD_RESERVE = b'    local SHOP_TOG_W = labW + 48\n'

INJECTIONS = [
    ('标签没建（用户要的「仅显示缺失」文字缺失）', OLD_LABEL, b''),
    ('让位量写死 96（enUS 宽标签会压表头）', OLD_RESERVE, b'    local SHOP_TOG_W = 96\n'),
]


def run(addon):
    env = dict(os.environ, DF_ADDON_ROOT=addon)
    p = subprocess.run([PY, os.path.join(HERE, 'df_dungeon_check.py')],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', env=env)
    return p.stdout or ''


def fails(out):
    got = set()
    for line in out.splitlines():
        s = line.strip()
        if s.startswith('[FAIL]'):
            got.add(s[6:].strip().split('  [')[0])
    return got


def main():
    base = fails(run(SRC))
    print('基准（已改）失败 %d 条（并行会话既有项按差集排除）' % len(base))

    tmp = tempfile.mkdtemp(prefix='dfmisstog_')
    dst = os.path.join(tmp, 'DungeonsForever')
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns(
        '.git', '.workbuddy', '__pycache__', '_temp'))
    os.makedirs(os.path.join(tmp, '_temp'), exist_ok=True)
    for f in ('df_dungeon_check.py', 'tf_dryrun.py'):
        shutil.copy(os.path.join(HERE, f), os.path.join(tmp, '_temp', f))

    p = os.path.join(dst, 'Core', 'ProfFollow.lua')
    clean = open(p, 'rb').read()
    allgood = True
    for name, old, new in INJECTIONS:
        assert clean.count(old) == 1, \
            '注入锚点命中 %d 次（锚点变了？）：%s' % (clean.count(old), name)
        open(p, 'wb').write(clean.replace(old, new, 1))
        fresh = fails(run(dst)) - base
        hit = [n for n in fresh if '仅显示缺失' in n or '让位量' in n]
        print('─' * 62)
        print('注入「%s」→ 新增失败 %d 条，命中新断言 %d 条' % (name, len(fresh), len(hit)))
        for n in sorted(hit):
            print('  ✗ %s' % n)
        if not hit:
            allgood = False
    open(p, 'wb').write(clean)      # 探针自己收尾，别在临时树里留注入态
    shutil.rmtree(tmp, ignore_errors=True)

    print('=' * 62)
    print('非恒真：注入即变红（新断言单独抓住）' if allgood
          else '★ 白测！有注入没被新断言抓住')
    return 0 if allgood else 1


if __name__ == '__main__':
    sys.exit(main())
