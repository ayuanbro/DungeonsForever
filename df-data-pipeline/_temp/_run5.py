# -*- coding: utf-8 -*-
"""第五轮收尾编排（串行，缩短并发窗口）：
  1) 快照 Core → /tmp/Core_snap6
  2) BEFORE: strip_comments.py --dry-run Core Locales（记录哪些文件会被去注释）
  3) fc_guide.py（断言必须过；写 zhCN + enUS）
  4) 记录 enUS/头块/并行 WIP 文件哈希
  5) gen_zhtw_data.py 连跑两次 → 证明 enUS 幂等（两次后哈希不变）
  6) AFTER: strip_comments.py --dry-run Core（对比）
  7) sync_beta.py --apply
  8) harness 双端（串行 + mtime 夹逼证明无并发写入）
  9) luacheck
 10) scan_forever_v4 / 未翻译扫描 / Core 净变更
全部输出写 _temp/_run5_summary.txt。
"""
import hashlib
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMP = os.path.join(ROOT, '_temp')
PY = r'C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe'
SNAP = r'/tmp/Core_snap_r5_%d'   # 每次用新目录（避免 rmtree 触发安全删除守卫）
ENUS_REL = 'Data/enUS/Data_ClassGuide.lua'
WIP = ['LootFilterUI.lua', 'MainFrame.lua', 'Core.lua', 'LootFilter.lua',
       'Data/Data_LootFilter.lua', 'Data/zhTW/Data_LootFilter.lua']
CLASSGUIDE = {'Data/Data_ClassGuide.lua', ENUS_REL, 'Data/zhTW/Data_ClassGuide.lua'}

sys.path.insert(0, TEMP)

log = []


def run(cmd, env=None, tail=None):
    e = dict(os.environ)
    e.setdefault('PYTHONIOENCODING', 'utf-8')
    e.setdefault('PYTHONUTF8', '1')
    if env:
        e.update(env)
    p = subprocess.run(cmd, cwd=ROOT, env=e, capture_output=True)
    out = (p.stdout + p.stderr).decode('utf-8', 'replace')
    lines = out.rstrip().split('\n')
    if tail:
        lines = lines[-tail:]
    log.append('$ %s  (exit=%d)' % (' '.join(cmd), p.returncode))
    log.extend(lines)
    log.append('')
    return p.returncode, out


def md5(rel):
    p = os.path.join(ROOT, 'Core', rel)
    if not os.path.exists(p):
        return '<missing>'
    return hashlib.md5(open(p, 'rb').read()).hexdigest()[:12]


def head(rel, n=4):
    p = os.path.join(ROOT, 'Core', rel)
    return [l.rstrip() for l in open(p, encoding='utf-8').read().split('\n')[:n]]


def main():
    import time
    snap = SNAP % int(time.time())
    shutil.copytree(os.path.join(ROOT, 'Core'), snap)
    log.append('== 快照 %s 完成 ==\n' % snap)

    # 2) BEFORE dry-run
    log.append('===== [C] BEFORE: strip_comments.py --dry-run Core Locales =====')
    run([PY, os.path.join(TEMP, 'strip_comments.py'), '--dry-run', 'Core', 'Locales'])
    log.append('')

    # 3) fc_guide
    rc, _ = run([PY, os.path.join(TEMP, 'fc_guide.py')])
    if rc != 0:
        raise SystemExit('fc_guide 失败 rc=%d' % rc)
    enus_after_fc = md5(ENUS_REL)

    # 4) hashes after fc_guide
    log.append('===== [C] fc_guide 后 关键文件哈希 =====')
    log.append('enUS/Data_ClassGuide.lua = %s' % enus_after_fc)
    log.append('enUS 头部前 4 行:')
    for l in head(ENUS_REL, 4):
        log.append('   | %s' % l)
    for r in WIP:
        log.append('WIP %-32s = %s' % (r, md5(r)))
    log.append('')

    # 5) gen_zhtw_data 两次
    wip_h1 = {r: md5(r) for r in WIP}
    rc, _ = run([PY, os.path.join(TEMP, 'gen_zhtw_data.py')], tail=6)
    if rc != 0:
        raise SystemExit('gen_zhtw_data #1 失败 rc=%d' % rc)
    enus_run1 = md5(ENUS_REL)
    wip_h2 = {r: md5(r) for r in WIP}

    rc, _ = run([PY, os.path.join(TEMP, 'gen_zhtw_data.py')], tail=6)
    if rc != 0:
        raise SystemExit('gen_zhtw_data #2 失败 rc=%d' % rc)
    enus_run2 = md5(ENUS_REL)

    log.append('===== [C] gen_zhtw_data 幂等 / 不外溢 证明 =====')
    log.append('enUS 哈希: fc_guide 后=%s  gen#1 后=%s  gen#2 后=%s' %
               (enus_after_fc, enus_run1, enus_run2))
    log.append('→ enUS 三次一致: %s' % (enus_after_fc == enus_run1 == enus_run2))
    wip_ok = all(wip_h1[r] == wip_h2[r] for r in WIP)
    log.append('→ 并行 WIP 文件 gen 前后哈希一致: %s' % wip_ok)
    for r in WIP:
        log.append('   %-32s %s -> %s %s' % (r, wip_h1[r], wip_h2[r],
                                             'OK' if wip_h1[r] == wip_h2[r] else '**CHANGED**'))
    log.append('')

    # 6) AFTER dry-run
    log.append('===== [C] AFTER: strip_comments.py --dry-run Core Locales =====')
    run([PY, os.path.join(TEMP, 'strip_comments.py'), '--dry-run', 'Core', 'Locales'])
    log.append('')

    # 7) sync_beta
    run([PY, os.path.join(TEMP, 'sync_beta.py'), '--apply'], tail=8)

    # 8) harness 双端（mtime 夹逼）
    snap_before = subprocess.run(['bash', '-lc',
                                  'stat -c "%Y %n" Core/LootFilterUI.lua Core/MainFrame.lua '
                                  'Core/Data/Data_LootFilter.lua Core/Core.lua Core/LootFilter.lua'],
                                 cwd=ROOT, capture_output=True)
    for label, env in [('16001', {}), ('38002', {'TF_BUILD': '38002'})]:
        rc, out = run([PY, os.path.join(TEMP, 'df_dungeon_check.py')], env=env, tail=6)
        for ln in out.split('\n'):
            if '通过' in ln and '失败' in ln:
                log.append('[harness %s] %s' % (label, ln.strip()))
        log.append('[harness %s] exit=%d\n' % (label, rc))
    snap_after = subprocess.run(['bash', '-lc',
                                 'stat -c "%Y %n" Core/LootFilterUI.lua Core/MainFrame.lua '
                                 'Core/Data/Data_LootFilter.lua Core/Core.lua Core/LootFilter.lua'],
                                cwd=ROOT, capture_output=True)
    log.append('[harness] mtime before==after: %s'
               % (snap_before.stdout == snap_after.stdout))

    # 9) luacheck：① 项目基线口径（非递归，30 文件）② 递归口径（含 enUS/zhTW，60 文件）
    #    经 bash 执行，保证 glob 由 shell 展开（与项目基线命令一致）。
    log.append('===== [D] luacheck 基线口径 Core/*.lua Core/Data/*.lua Locales/*.lua =====')
    rc, out = run(['bash', '-lc',
                   'D:/workspace/tool/luacheck.exe --no-max-string-line-length '
                   'Core/*.lua Core/Data/*.lua Locales/*.lua 2>&1'], tail=4)
    for ln in out.split('\n'):
        if 'Total:' in ln:
            log.append('[luacheck 基线] %s' % ln.strip())
    log.append('')
    log.append('===== [D] luacheck 递归口径（含 Data/enUS, Data/zhTW）=====')
    rc, out = run(['bash', '-lc',
                   'D:/workspace/tool/luacheck.exe --no-max-string-line-length '
                   'Core/*.lua Core/Data/*.lua Core/Data/enUS/*.lua '
                   'Core/Data/zhTW/*.lua Locales/*.lua 2>&1'], tail=4)
    for ln in out.split('\n'):
        if 'Total:' in ln:
            log.append('[luacheck 递归] %s' % ln.strip())
    log.append('')

    # 10) scans
    log.append('===== [D] scan_forever_v4 =====')
    run([PY, os.path.join(TEMP, '_scan_forever_v4.py')], tail=12)
    log.append('===== [D] 未翻译扫描 (probe1/probe3) =====')
    run([PY, os.path.join(TEMP, '_r5_probe.py')], tail=10)
    run([PY, os.path.join(TEMP, '_r5_probe3.py')], tail=6)
    log.append('===== [D] 「无限+杂词」产线扫描 =====')
    run([PY, os.path.join(TEMP, '_scan_wordy.py')], tail=6)

    # 11) net change
    diffs = []
    for base, _dirs, files in os.walk(snap):
        for fn in files:
            sp = os.path.join(base, fn)
            rel = os.path.relpath(sp, snap).replace('\\', '/')
            cp = os.path.join(ROOT, 'Core', rel)
            if not os.path.exists(cp) or open(sp, 'rb').read() != open(cp, 'rb').read():
                diffs.append(rel)
    log.append('\n== 最终 Core 净变更（vs 快照）:')
    for d in sorted(diffs):
        tag = ' [本轮目标]' if d in CLASSGUIDE else (' [外部并发]' if d in WIP else '')
        log.append('   %s%s' % (d, tag))

    with open(os.path.join(TEMP, '_run6_summary.txt'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(log))
    print('done')


if __name__ == '__main__':
    main()
