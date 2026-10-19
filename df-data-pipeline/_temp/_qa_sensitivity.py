# -*- coding: utf-8 -*-
"""敏感性自证 + 最终回归（一次跑完，报告落盘 _qa_sensitivity_report.txt）。

- 变异只写 BETA（harness/probe 都读 beta），每个场景后从 SOURCE 还原。
- harness 与 df_mut_check 串行（subprocess 阻塞）。
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
SRC = os.path.join(os.path.dirname(HERE), 'Core', 'TierUI.lua')
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever\Core\TierUI.lua'
REPORT = os.path.join(HERE, '_qa_sensitivity_report.txt')

LOG = []


def log(s=''):
    LOG.append(s)


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def run(script, env_extra=None, args=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    cmd = [PY, os.path.join(HERE, script)] + (args or [])
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def probe_line(out, key):
    for ln in out.split('\n'):
        if key in ln:
            st = 'OK' if '[OK ]' in ln else ('FAIL' if '[FAIL]' in ln else '?')
            extra = ''
            if '[[' in ln and ']]' in ln:
                extra = ln.split('[[', 1)[1].rsplit(']]', 1)[0]
            return st, extra
    return 'MISSING', ''


def harness_tally(out):
    for ln in out.split('\n'):
        if '通过' in ln and '失败' in ln and '项' in ln:
            return ln.strip()
    return 'NO-SUMMARY'


def write_beta(text):
    with open(BETA, 'wb') as fh:
        fh.write(text.encode('utf-8'))


def restore():
    shutil.copyfile(SRC, BETA)


def main():
    pristine = open(SRC, 'rb').read().decode('utf-8')
    assert open(BETA, 'rb').read().decode('utf-8') == pristine, 'SRC/BETA 不一致，先同步'
    log('== 前置 ==')
    log('SRC md5 = %s' % md5(SRC))
    log('BETA md5 = %s' % md5(BETA))

    # ---------- 组 0：基线（当前正确代码） ----------
    rc, out = run('_qa_probe_spec.py')
    log('')
    log('== [基线] probe ==')
    log('  spec: %s  %s' % probe_line(out, '专精模式：TT.scroll 顶锚'))
    log('  rank: %s  %s' % probe_line(out, '排行模式：TT.scroll 顶锚'))
    log('  结构: %s  %s' % probe_line(out, 'SEC_TOP 结构'))
    for ln in out.split('\n'):
        if ln.startswith('通过'):
            log('  ' + ln.strip())

    # ---------- 组 1：SEC_DROP = 10 / 0（不钉数值，只证明探针读到真实常量） ----------
    for val in (10, 0):
        assert pristine.count('TT.SEC_DROP     = 5\n') == 1
        mutated = pristine.replace('TT.SEC_DROP     = 5\n', 'TT.SEC_DROP     = %d\n' % val)
        write_beta(mutated)
        try:
            rc, out = run('_qa_probe_spec.py')
            st, extra = probe_line(out, '专精模式：TT.scroll 顶锚')
            s2, e2 = probe_line(out, '排行模式：TT.scroll 顶锚')
            log('')
            log('== [变异] SEC_DROP=%d ==' % val)
            log('  probe spec: %s  %s' % (st, extra))
            log('  probe rank: %s  %s' % (s2, e2))
            for ln in out.split('\n'):
                if ln.startswith('通过'):
                    log('  ' + ln.strip())
        finally:
            restore()

    # ---------- 组 2：spec 分支误换成 BODY_TOP（探针必须抓住） ----------
    assert pristine.count('TT.PlaceScroll(TT.SEC_TOP)') == 1
    mutated = pristine.replace('TT.PlaceScroll(TT.SEC_TOP)', 'TT.PlaceScroll(TT.BODY_TOP)')
    write_beta(mutated)
    try:
        rc, out = run('_qa_probe_spec.py')
        st, extra = probe_line(out, '专精模式：TT.scroll 顶锚')
        log('')
        log('== [变异] spec 分支 TT.PlaceScroll(SEC_TOP) -> (BODY_TOP) ==')
        log('  probe spec: %s  %s' % (st, extra))
        fails = [l.strip() for l in out.split('\n') if '[FAIL]' in l]
        log('  probe FAIL 行数 = %d' % len(fails))
        for f in fails[:5]:
            log('    ' + f)
        for ln in out.split('\n'):
            if ln.startswith('通过'):
                log('  ' + ln.strip())
    finally:
        restore()

    # ---------- 组 3：插入注释 `-- stripe`（静态守卫必须抓住） ----------
    anchor = 'TT.SEC_TOP      = TT.SEC_TAB_Y + TT.SEC_TAB_H + TT.SEC_DROP\n'
    assert pristine.count(anchor) == 1
    mutated = pristine.replace(anchor, anchor + 'local x = 1 -- stripe\n')
    write_beta(mutated)
    try:
        rc, out = run('df_dungeon_check.py')
        st, extra = probe_line(out, '专精卡已无左侧竖条 stripe')
        # probe_line 用 [[ 取 extra，但 harness 的 extra 是 [hits: ...]，单独取
        gline = ''
        for ln in out.split('\n'):
            if '专精卡已无左侧竖条' in ln:
                gline = ln.strip()
        log('')
        log('== [变异] 插入 "local x = 1 -- stripe" ==')
        log('  守卫行: %s' % gline)
        log('  harness: %s' % harness_tally(out))
        log('  harness FAIL 行数 = %d' % out.count('[FAIL]'))
    finally:
        restore()

    # ---------- 最终回归（串行） ----------
    log('')
    log('== 最终回归（串行） ==')
    rc, out = run('df_dungeon_check.py')
    log('  harness 16001: %s   rc=%d' % (harness_tally(out), rc))
    rc, out = run('df_dungeon_check.py', env_extra={'TF_BUILD': '38002'})
    log('  harness 38002: %s   rc=%d' % (harness_tally(out), rc))
    rc, out = run('df_mut_check.py')
    mutline = [l.strip() for l in out.split('\n') if '变异后 FAIL 行数' in l or '变异被抓住' in l]
    log('  mut: rc=%d  %s' % (rc, ' | '.join(mutline)))

    # lua51 / luacheck（源码侧）
    lua51 = os.path.join(HERE, 'lua51_check.py')
    rc, out = run('lua51_check.py', args=[SRC])
    log('  lua51: %s' % [l.strip() for l in out.split('\n') if 'failed' in l.lower() or 'FAIL' in l])

    log('')
    log('== 后置 ==')
    log('SRC md5 = %s' % md5(SRC))
    log('BETA md5 = %s' % md5(BETA))
    log('一致 = %s' % (md5(SRC) == md5(BETA)))
    log('BETA stripe 残留 = %d' % open(BETA, 'rb').read().count(b'stripe'))

    with open(REPORT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(LOG) + '\n')
    print('report written: %s' % REPORT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
