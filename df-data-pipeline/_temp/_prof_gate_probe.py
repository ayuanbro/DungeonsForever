# -*- coding: utf-8 -*-
"""非恒真证明（2026-10-09）：专业页分帧 + 顶部进度条

两条线各证一遍（都在**隔离副本树**上做，产品文件零触碰）：
  A. 静态：把回潮注入副本 → 直接调 df_dungeon_check.static_guard() → 目标断言必须变红；
  B. 运行时段：把回潮注入副本 → 子进程跑 _prof_gate_smoke.py（DF_ADDON_ROOT 重定向）
     → 目标断言必须出现在 FAIL 行里。

任何一条「没变红」= 白测 → 整体非零退出。
用法：python _prof_gate_probe.py
"""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D      # noqa: E402

PROF = 'Core/ProfessionUI.lua'

# ── A. 静态断言 ───────────────────────────────────────────────────────────
# (目标断言名子串, 文件, old, new)
STATIC_MUTS = [
    ('★★ 渲染那一帧不再同步建行帧', PROF,
     '        local h = PD.RowHeight(spec)\n        local r = PD.rows[i]\n',
     '        local h = PD.RowHeight(spec)\n        local r = PD.Row(i)\n'),
    ('★★ 专业页大列表分帧', PROF,
     '    DG.Gate.Begin(n)\n',
     '    -- MUT: gate dropped\n'),
    ('★ 量小走快速通道', PROF,
     '    if n < PD.ROW_SYNC_MAX then\n',
     '    if false then\n'),
    ('★ 间距行（kind == "gap"）也进待建表', PROF,
     'PD.__pendRows[#PD.__pendRows + 1] = { idx = i, gap = true }\n',
     '-- MUT: gap not queued\n'),
    ('★ 每轮渲染开头丢掉上一轮排下', PROF,
     '    -- ★ 上一轮排下、还没建的行必须丢掉（玩家已经点到别的专业 / 别的子页签了），\n'
     '    --   否则它们会在新页面上冒出来。\n'
     '    PD.__pendRows = {}\n',
     '    -- MUT: queue not reset per render\n'),
    ('★ 设置页开关不对还没建出来的行取层级', PROF,
     '        if PD.setOpen and spec.togKey and rr then\n',
     '        if PD.setOpen and spec.togKey then\n'),
    ('★ 进度条自检入口', PROF,
     'SLASH_DUNGEONSFOREVERPROFGATE1 = "/dfprofgate"\n',
     'SLASH_DUNGEONSFOREVERPROFGATE1 = "/dfprofgateX"\n'),
]

# ── B. 运行时段（冒烟）────────────────────────────────────────────────────
# (目标断言名子串, 文件, old, new)
RUNTIME_MUTS = [
    ('① 大页强制分帧', PROF,
     '        local h = PD.RowHeight(spec)\n        local r = PD.rows[i]\n',
     '        local h = PD.RowHeight(spec)\n        local r = PD.Row(i)\n'),
    ('② 抽一批泵后', PROF,
     '        DG.Gate.Advance(1)\n',
     '        -- MUT: advance dropped\n'),
    # ③ 间距行不入队 → 配方页看不见（它的 gap 落在 ROW_CAP 之外），必须靠 ⑤ 那一段
    #    「可见范围里有 gap 的页签」才抓得住 ⇒ 目标断言名字串指 ⑤。
    ('⑤ 间距行同样入队', PROF,
     'PD.__pendRows[#PD.__pendRows + 1] = { idx = i, gap = true }\n',
     '-- MUT: gap not queued\n'),
    # ④ 快速通道阈值被摘 → 量小也走分帧：④ 当场建完 + 条不亮 这条必须变红。
    ('④ 阈值内', PROF,
     '    if n < PD.ROW_SYNC_MAX then\n',
     '    if false then\n'),
]


def _copy_tree(root):
    dst = tempfile.mkdtemp(prefix='_prof_gate_')
    shutil.copytree(root, os.path.join(dst, 'DungeonsForever'))
    return os.path.join(dst, 'DungeonsForever'), dst


def _apply(root, rel, old, new):
    p = os.path.join(root, *rel.split('/'))
    raw = open(p, 'rb').read()
    s = raw.decode('utf-8')
    # ★★ 行尾自愈（同 df_check_new_muts.py 234-244）：专业页/副本页是手写件、
    #    纯 CRLF。锚点串在源码里写成裸 \n，直接按原始字节比对永远 count==0 ——
    #    注入全失败、看着像「脚本 bug」而不是「断言没人守」。此处按目标文件实际
    #    行尾把 old/new 的裸 \n 补成 \r\n；LF / 混合行尾文件保持原样。
    if b'\r\n' in raw and raw.count(b'\n') == raw.count(b'\r\n'):
        old = old.replace('\r\n', '\n').replace('\n', '\r\n')
        new = new.replace('\r\n', '\n').replace('\n', '\r\n')
    if s.count(old) != 1:
        return '锚点 %d 次' % s.count(old)
    open(p, 'w', encoding='utf-8', newline='').write(s.replace(old, new))
    return None


def _run_static(root):
    prev = D.ADDON
    D.ADDON = root
    del D.FAILED[:]
    del D.PASSED[:]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            D.static_guard()
    except Exception as e:                      # 崩了也算没通过，但要报出来
        D.FAILED.append('__CRASH__: %s' % e)
    finally:
        D.ADDON = prev
    return list(D.FAILED)


def _run_smoke(root):
    env = dict(os.environ)
    env['DF_ADDON_ROOT'] = root
    r = subprocess.run([sys.executable, os.path.join(HERE, '_prof_gate_smoke.py')],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', env=env, cwd=HERE)
    return (r.stdout or '') + (r.stderr or '')


def _smoke_hit(out, name):
    """注入后到底红没红：① 有同名 FAIL 行；② 冒烟崩了 / 没跑到汇总行也算红。"""
    lines = [l.strip() for l in out.splitlines() if '[FAIL]' in l and name in l]
    if lines:
        return lines, ''
    crash = [l.strip() for l in out.splitlines()
             if 'LuaError' in l or 'Traceback' in l]
    if '冒烟完成' not in out:
        return [], (crash[-1][:90] if crash else '没有跑到汇总行')
    return [], ''


def main():
    base = D.ADDON
    print('隔离副本源：%s' % base)
    bad = []

    # 基线：静态守卫里那 7 条必须全在 PASSED（不红）
    root, tmp = _copy_tree(base)
    try:
        base_fails = _run_static(root)
        for name, _, _, _ in STATIC_MUTS:
            if any(name in f for f in base_fails):
                bad.append('基线就红着：%s' % name)
                print('  ✗ 基线已红：%s' % name)
        print('基线（未变异）：静态守卫 FAIL %d 条（我的 7 条都不在其中）'
              % len(base_fails))

        for name, rel, old, new in STATIC_MUTS:
            err = _apply(root, rel, old, new)
            if err:
                bad.append('%s → %s' % (name, err))
                print('  ✗✗ %-28s 注入失败：%s' % (name, err))
            else:
                fails = _run_static(root)
                hit = [f for f in fails if name in f]
                mark = 'YES' if hit else 'NO 白测!'
                print('  [%s] 静态 %s' % (mark, name))
                if not hit:
                    bad.append(name)
                # 还原该文件
                src = os.path.join(base, *rel.split('/'))
                shutil.copyfile(src, os.path.join(root, *rel.split('/')))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 基线冒烟：必须 0 失败
    root, tmp = _copy_tree(base)
    try:
        out = _run_smoke(root)
        if '冒烟完成：失败 0 条' not in out:
            bad.append('基线冒烟不为 0 失败')
            print('  ✗ 基线冒烟异常：')
            for l in out.splitlines():
                if '[FAIL]' in l or '冒烟完成' in l:
                    print('     ' + l.strip())
        else:
            print('基线（未变异）：冒烟失败 0 条')

        for name, rel, old, new in RUNTIME_MUTS:
            err = _apply(root, rel, old, new)
            if err:
                bad.append('%s → %s' % (name, err))
                print('  ✗✗ %-28s 注入失败：%s' % (name, err))
            else:
                out = _run_smoke(root)
                hit, why = _smoke_hit(out, name)
                mark = 'YES' if (hit or why) else 'NO 白测!'
                print('  [%s] 运行时 %s   新 FAIL 共 %d 条%s'
                      % (mark, name,
                         len([l for l in out.splitlines() if '[FAIL]' in l]),
                         ('（%s）' % why) if why else ''))
                for l in hit[:2]:
                    print('       ' + l[:130])
                if not hit and not why:
                    bad.append(name)
                src = os.path.join(base, *rel.split('/'))
                shutil.copyfile(src, os.path.join(root, *rel.split('/')))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('=' * 66)
    if bad:
        print('✗ %d 条没被证明非恒真：' % len(bad))
        for b in bad:
            print('   ' + b)
        return 1
    print('✓ 静态 %d 条 + 运行时 %d 条 全部被证明非恒真（注入即变红）'
          % (len(STATIC_MUTS), len(RUNTIME_MUTS)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
