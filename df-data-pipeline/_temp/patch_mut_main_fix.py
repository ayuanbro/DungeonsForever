# -*- coding: utf-8 -*-
"""修 `_temp/df_mut_check.py` 的 `main()`：让它**真的**能跑起来，并且判据诚实。

三处病灶（2026-10-09 rev18 定位）：
  ① 【真 bug】锚点命中数用 `data.count(old)`，不做 `to_file_style`。变异锚点一律按 LF 书写，
     而 `Core/ProfessionUI.lua` / `Core/DungeonUI.lua` 是 CRLF 产物 ⇒ 这些锚点恒 0 次，
     合法锚点被当成「不存在」。
  ② 【死路径】撞上任何非 1 次锚点就 `return 2` 整批中止 ⇒ 「全量一次性注入」这条路径
     永远跑不完。改成：死锚只跳过该条并大声列出；**合法但被同文件更早的变异吃掉**的
     单列为「冲突」（锚点本身健康，守卫交给 `_mut_isolate.py` 单条隔离）。
  ③ 【静默失效】判据是 `nfail > 0`，可 baseline 本来就常年挂着别的工作线的失败断言
     ⇒ 恒为真，整批变异都被当成「被抓住」。改成跑一遍**未变异基线**取差集，
     并补「脏抓」判据（loadfile 返回 nil / Traceback）。

做法：单趟渐进替换（J1 插辅助函数 → J2 换注入/判据整段），幂等。
用法：
    python _temp/patch_mut_main_fix.py            # 落盘
    python _temp/patch_mut_main_fix.py --check    # 只预检，不落盘
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, 'df_mut_check.py')
BACKUP = os.path.join(HERE, '_bak18_df_mut_check.py')

# ------------------------------------------------------------ J1：插两个辅助函数
OLD_B = r'''def main():
    # 变异可跨文件（本插件的副本页代码全部落在 Core/DungeonUI.lua）
'''

NEW_B = r'''def _harness_once():
    """跑一遍 harness，返回 (returncode, stdout+stderr)。"""
    r = subprocess.run([PY, os.path.join(HERE, 'df_dungeon_check.py')],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def _fail_lines(out):
    """harness 输出里的失败行**去重集合**，用于取差集（基线 vs 注入后）。

    ★ 同一条失败会打两遍：详情 `  [FAIL] 名字  [附注]` 与汇总 `  ✗ 名字` —— 两者文本不等
      （详情带附注）⇒ 两个都收会把基线 22 条数成 44。**只认 `[FAIL]` 那一份**；
      万一一条 `[FAIL]` 都没有（整体崩了），退回 `✗` 行，别把「崩」当成「无失败」。
    """
    lines = [ln.strip() for ln in out.split('\n')]
    det = sorted({s[len('[FAIL]'):].strip() for s in lines if s.startswith('[FAIL]')})
    if det:
        return det
    return sorted({s[1:].strip() for s in lines if s.startswith('✗')})


def main():
    # 变异可跨文件（本插件的副本页代码全部落在 Core/DungeonUI.lua）
'''

# ------------------------------------------------- J2：换「注入 + 判据」整段
OLD_A = r'''    # 先在内存里把所有锚点校验/替换完，再统一落盘 ——
    # 中途报错不会留下「半边带变异」的 beta（踩过一次）
    payloads = {}
    for fname, items in files.items():
        p = os.path.join(BETA, *fname.split('/'))
        data = open(p, 'rb').read()
        for name, old, new in items:
            if data.count(old) != 1:
                print('!! 锚点不唯一/不存在（%d 次）: %s' % (data.count(old), name))
                return 2
            data = data.replace(old, new)
            print('已注入变异：%s  [%s]' % (name, fname))
        payloads[fname] = data
    for fname, data in payloads.items():
        p = os.path.join(BETA, *fname.split('/'))
        open(p, 'wb').write(data)
        bare = data.count(b'\n') - data.count(b'\r\n')
        print('  %s 注入后 CRLF = %d / 裸 LF = %d' % (fname, data.count(b'\r\n'), bare))
    try:
        r = subprocess.run([PY, os.path.join(HERE, 'df_dungeon_check.py')],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        out = (r.stdout or '') + (r.stderr or '')
        print(out[-2600:])
        nfail = out.count('[FAIL]') + out.count('✗')
        print('=' * 60)
        print('变异后 FAIL 行数 = %d' % nfail)
        if r.returncode != 0 and nfail > 0:
            print('✓ 变异被抓住（harness 非恒真）')
            return 0
        print('✗ 变异未被抓住 —— 断言是白测，必须修 harness')
        return 1
'''

NEW_A = r'''    # ★ 基线：先跑一遍**未变异**的 BETA。harness 里常年挂着别的工作线留下的失败断言
    #   （并发开发时尤甚）；不取差集的话「FAIL 数 > 0」恒为真 ⇒ 整批变异都会被当成
    #   「被抓住」，这条检查静默失效（同 df_check_new_muts.py 的教训）。
    _rc0, base_out = _harness_once()
    base_fails = set(_fail_lines(base_out))
    if base_fails:
        print('基线（未变异）：%d 条既有 FAIL（与本批无关，按差集判定）' % len(base_fails))
    else:
        print('基线（未变异）：无既有 FAIL')
    # ★ 2026-10-09（rev18）：① 锚点命中数**必须**按 `to_file_style` 后的形态数（变异锚点一律
    #   按 LF 书写，对 CRLF 产物直接 count(old) 恒 0 ⇒ 合法锚点被误判「不存在」）；
    #   ② 死锚只跳过该条、不再整批中止；③ 合法锚点被同文件更早的变异吃掉 ⇒ 只算「冲突」，
    #   不算死锚（那种变异单条隔离时照样能把断言打红，守卫是好的）。
    payloads, dead, conflict, injected = {}, [], [], 0
    for fname, items in files.items():
        p = os.path.join(BETA, *fname.split('/'))
        data = open(p, 'rb').read()
        pristine = data
        for name, old, new in items:
            c0 = pristine.count(to_file_style(old, pristine))
            if c0 != 1:
                dead.append((name, fname, c0))
                continue
            o, nw = to_file_style(old, data), to_file_style(new, data)
            c1 = data.count(o)
            if c1 != 1:
                conflict.append((name, fname, c1))
                continue
            data = data.replace(o, nw)
            injected += 1
            print('已注入变异：%s  [%s]' % (name, fname))
        payloads[fname] = data
    if dead:
        print('=' * 60)
        print('★ %d 条变异**死锚**（原始文件上就非 1 次）—— 锚点过期，等于没人守：' % len(dead))
        for name, fname, c in dead:
            print('    %2d 次  %-24s %s' % (c, fname, name))
        print('  → 重锚后跑 `python _temp/check_mut_anchors.py` 复检；'
              '单条守卫用 `python _temp/_mut_isolate.py <关键字>`。')
        print('=' * 60)
    if conflict:
        print('★ %d 条变异与同文件里更早的变异**改同一段**（锚点本身健康，批量注入时被吃掉）：'
              % len(conflict))
        for name, fname, c in conflict:
            print('        %-24s %s' % (fname, name))
        print('  → 守卫由 `_mut_isolate.py`（单条隔离）负责；批量注入本就不该同时生效。')
    print('本批：注入 %d 条 / 死锚 %d 条 / 冲突 %d 条（共 %d）'
          % (injected, len(dead), len(conflict), injected + len(dead) + len(conflict)))
    try:
        for fname, data in payloads.items():
            p = os.path.join(BETA, *fname.split('/'))
            open(p, 'wb').write(data)
            bare = data.count(b'\n') - data.count(b'\r\n')
            print('  %s 注入后 CRLF = %d / 裸 LF = %d' % (fname, data.count(b'\r\n'), bare))
        _rc, out = _harness_once()
        print(out[-2600:])
        crash = ('loadfile 返回 nil' in out) or ('Traceback' in out)
        newf = [l for l in _fail_lines(out) if l not in base_fails]
        print('=' * 60)
        print('变异后：新 FAIL %d 条（总 %d / 基线 %d）· 脏抓=%s'
              % (len(newf), len(_fail_lines(out)), len(base_fails), crash))
        if crash:
            print('✗ 注入后整体崩了（loadfile 返回 nil / Traceback）—— 这次注入无效，别当成功')
            return 1
        if newf:
            print('✓ 变异被抓住（harness 非恒真）')
            return 0
        print('✗ 变异未被抓住 —— 断言是白测，必须修 harness')
        return 1
'''


def main():
    do_check = '--check' in sys.argv[1:]
    src = open(TARGET, encoding='utf-8', newline='').read()
    out = src
    changed = False

    if 'def _harness_once():' in out:
        print('  [SKIP] J1 插入 _harness_once/_fail_lines      已应用')
    else:
        assert out.count(OLD_B) == 1, 'J1 锚点 %d 次' % out.count(OLD_B)
        out = out.replace(OLD_B, NEW_B, 1)
        changed = True
        print('  [OK  ] J1 插入 _harness_once/_fail_lines      锚点 1 次')

    if '**死锚**（原始文件上就非 1 次）' in out:
        print('  [SKIP] J2 注入/判据整段重写（含冲突分类）   已应用')
    else:
        assert out.count(OLD_A) == 1, 'J2 锚点 %d 次' % out.count(OLD_A)
        out = out.replace(OLD_A, NEW_A, 1)
        changed = True
        print('  [OK  ] J2 注入/判据整段重写（含冲突分类）   锚点 1 次')

    if do_check:
        print('  [OK  ] 预检通过（未落盘）')
        return 0
    if not changed:
        print('  [OK  ] 无需改动')
        return 0

    if not os.path.exists(BACKUP):
        shutil.copyfile(TARGET, BACKUP)
        print('  [BAK ] %s' % os.path.basename(BACKUP))

    assert '\r\n' not in out, '本文件必须保持纯 LF'
    assert 'def _harness_once():' in out and 'to_file_style(old, pristine)' in out
    open(TARGET, 'w', encoding='utf-8', newline='\n').write(out)
    print('  [DONE] %s：%d → %d 字节（纯 LF 保持）' % (
        os.path.basename(TARGET), len(src.encode('utf-8')), len(out.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
