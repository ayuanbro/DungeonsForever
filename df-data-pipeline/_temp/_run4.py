# -*- coding: utf-8 -*-
"""第四轮收尾编排（一次跑完，缩短并发窗口）：
  1) 快照 Core → /tmp/Core_snap5（最新并发状态）
  2) fc_guide.py（写 zhCN + enUS，含头部；断言通过）
  3) 存 enUS（fc_guide 原样输出，含头部）
  4) gen_zhtw_data.py（zhTW + 注释精简副作用）
  5) 只还原「注释-only 的连带变更」文件（保留外部并发改动）+ enUS 头部还原
  6) sync_beta.py --apply
  7) harness 双端（串行）
  8) luacheck
  9) 记录最终 Core 净变更
全部输出写 _temp/_run4_summary.txt。
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMP = os.path.join(ROOT, '_temp')
PY = r'C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe'
SNAP = r'/tmp/Core_snap5'
ENUS = r'/tmp/enUS5.lua'
CLASSGUIDE = {'Data/Data_ClassGuide.lua', 'Data/enUS/Data_ClassGuide.lua',
              'Data/zhTW/Data_ClassGuide.lua'}

sys.path.insert(0, TEMP)
import strip_comments as S  # noqa: E402

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


def norm(t):
    return S.strip_text(t)[0]


def main():
    # 1) 快照
    if os.path.isdir(SNAP):
        shutil.rmtree(SNAP)
    shutil.copytree(os.path.join(ROOT, 'Core'), SNAP)
    log.append('== 快照 /tmp/Core_snap5 完成 ==\n')

    # 2/3) fc_guide + 存 enUS
    rc, _ = run([PY, os.path.join(TEMP, 'fc_guide.py')])
    if rc != 0:
        raise SystemExit('fc_guide 失败 rc=%d' % rc)
    shutil.copy2(os.path.join(ROOT, 'Core/Data/enUS/Data_ClassGuide.lua'), ENUS)

    # 4) gen_zhtw_data
    rc, _ = run([PY, os.path.join(TEMP, 'gen_zhtw_data.py')], tail=3)
    if rc != 0:
        raise SystemExit('gen_zhtw_data 失败 rc=%d' % rc)

    # 5) 只还原注释-only 连带变更（保留外部并发改动）+ enUS 头部
    restored, external = [], []
    for base, _dirs, files in os.walk(SNAP):
        for fn in files:
            sp = os.path.join(base, fn)
            rel = os.path.relpath(sp, SNAP).replace('\\', '/')
            cp = os.path.join(ROOT, 'Core', rel)
            if not os.path.exists(cp):
                continue
            a = open(sp, 'rb').read()
            b = open(cp, 'rb').read()
            if a == b or rel in CLASSGUIDE:
                continue
            if norm(a.decode('utf-8')) == norm(b.decode('utf-8')):
                shutil.copy2(sp, cp)
                restored.append(rel)
            else:
                external.append(rel)
    shutil.copy2(ENUS, os.path.join(ROOT, 'Core/Data/enUS/Data_ClassGuide.lua'))
    log.append('== 注释-only 连带变更（已还原）：%s' % (restored or '无'))
    log.append('== 非注释差异（视为外部并发改动，保留不动）：%s' % (external or '无'))
    log.append('== enUS 头部已还原为 fc_guide 输出 ==\n')

    # 6) sync_beta
    rc, sout = run([PY, os.path.join(TEMP, 'sync_beta.py'), '--apply'], tail=8)
    if rc != 0:
        log.append('!! sync_beta rc=%d' % rc)

    # 7) harness 双端
    for label, env in [('16001', {}), ('38002', {'TF_BUILD': '38002'})]:
        rc, out = run([PY, os.path.join(TEMP, 'df_dungeon_check.py')], env=env,
                      tail=6)
        # 摘出「通过 X 项 / 失败 Y 项」
        for ln in out.split('\n'):
            if '通过' in ln and '失败' in ln:
                log.append('[harness %s] %s' % (label, ln.strip()))
        log.append('[harness %s] exit=%d\n' % (label, rc))

    # 8) luacheck
    rc, out = run([r'D:/workspace/tool/luacheck.exe', '--no-max-string-line-length',
                   'Core/Core.lua', 'Core/Data/Data_ClassGuide.lua',
                   'Core/Data/enUS/Data_ClassGuide.lua',
                   'Core/Data/zhTW/Data_ClassGuide.lua',
                   'Core/Data/Data_LootFilter.lua', 'Core/LootFilter.lua',
                   'Core/LootFilterUI.lua'], tail=3)
    for ln in out.split('\n'):
        if 'Total:' in ln:
            log.append('[luacheck] %s' % ln.strip())

    # 9) 最终 Core 净变更
    diffs = []
    for base, _dirs, files in os.walk(SNAP):
        for fn in files:
            sp = os.path.join(base, fn)
            rel = os.path.relpath(sp, SNAP).replace('\\', '/')
            cp = os.path.join(ROOT, 'Core', rel)
            if not os.path.exists(cp) or open(sp, 'rb').read() != open(cp, 'rb').read():
                diffs.append(rel)
    log.append('\n== 最终 Core 净变更（vs 快照）：')
    for d in sorted(diffs):
        log.append('   %s' % d)

    with open(os.path.join(TEMP, '_run4_summary.txt'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(log))


if __name__ == '__main__':
    main()
