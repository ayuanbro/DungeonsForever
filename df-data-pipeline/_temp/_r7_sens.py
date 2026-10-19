# -*- coding: utf-8 -*-
"""R7 敏感性自证：证明新增的 SEC_DROP==5 pin 能抓住 beta 侧变异。

前置：SRC/BETA 的 Core/TierUI.lua 必须一致（否则先 sync）。
流程：基线 probe → 变异 beta SEC_DROP 5->10 → 再跑 probe（应 FAIL 1 条）→ finally 从 SRC 还原。
探针 _qa_probe_spec.py 的 ADDON 指向 beta，故变异 beta 会被读到。
"""
import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
SRC = os.path.join(os.path.dirname(HERE), 'Core', 'TierUI.lua')
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever\Core\TierUI.lua'
REPORT = os.path.join(HERE, '_r7_sens_report.txt')

LOG = []


def log(s=''):
    LOG.append(s)


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def run(script):
    r = subprocess.run([PY, os.path.join(HERE, script)], cwd=HERE,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def pick(out):
    for ln in out.split('\n'):
        s = ln.strip()
        if 'SEC_DROP' in s or s.startswith('通过'):
            log('  ' + s)


def main():
    pristine = open(SRC, 'rb').read()
    log('== 前置 ==')
    log('  SRC  md5=%s' % md5(SRC))
    log('  BETA md5=%s' % md5(BETA))
    assert open(BETA, 'rb').read() == pristine, 'SRC/BETA 不一致，先 sync_beta'

    log('')
    log('== [基线] probe（SEC_DROP=5，应全过）==')
    rc, out = run('_qa_probe_spec.py')
    pick(out)

    try:
        txt = pristine.decode('utf-8')
        assert txt.count('TT.SEC_DROP     = 5\n') == 1, '未找到唯一的 SEC_DROP=5 赋值行'
        open(BETA, 'wb').write(
            txt.replace('TT.SEC_DROP     = 5\n', 'TT.SEC_DROP     = 10\n').encode('utf-8'))
        log('')
        log('== [变异] beta SEC_DROP 5 -> 10（新增 pin 应 FAIL）==')
        rc, out = run('_qa_probe_spec.py')
        pick(out)
        fails = [l.strip() for l in out.split('\n') if '[FAIL]' in l]
        log('  FAIL 行数 = %d' % len(fails))
        for f in fails[:5]:
            log('    ' + f)
    finally:
        open(BETA, 'wb').write(pristine)

    log('')
    log('== 后置（还原校验）==')
    log('  BETA 还原 == SRC: %s' % (open(BETA, 'rb').read() == pristine))
    log('  BETA md5=%s' % md5(BETA))

    with open(REPORT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(LOG) + '\n')
    print('report written: %s' % REPORT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
