# -*- coding: utf-8 -*-
"""团本页 · 修 2026-09-29 实机事故：os.time() 在客户端根本不存在（幂等补丁）

事故：实机开团本页 → 界面构建出错：RaidUI.lua:126: attempt to index a nil value
  CountdownText(126) ← UpdateCD(136) ← Render(331) ← Build(442)
根因：WoW 的 Lua **没有 os 库**（暴雪用全局 time() / date() / difftime() 替代）。
  离线 harness 跑的是 lupa 真 Lua —— 标准库齐全（有 os.time）、反而没有全局 time，
  所以「用 os.* 的代码」在 harness 恒绿、实机必崩。这是 harness 的盲区，不是代码的偶然。

改三件事（锚点命中数 != 1 就中止；已打过就 SKIP）：
  1) Core/RaidUI.lua —— 时钟走纯函数 RU.PickClock(env) / RU.NowSec()：
     time() → GetServerTime() → env.os.time()（离线桩，type 守卫）；拿不到就该条不显示。
  2) _temp/df_dungeon_check.py + _temp/mk_df_check.py —— 静态断言改成「时钟链 + 全仓禁 os.*」；
  3) 两份 harness 的 Lua 环境与客户端同形：抹掉 os、补上全局 time()。

用法：python _temp/_patch_raid_clock.py     （幂等，可重复跑）
"""
import io
import os
import py_compile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

RAID = os.path.join(ROOT, 'Core', 'RaidUI.lua')
CHECKS = [os.path.join(HERE, 'df_dungeon_check.py'),
          os.path.join(HERE, 'mk_df_check.py')]


def read(path):
    with io.open(path, 'rb') as f:
        raw = f.read()
    return raw.decode('utf-8').replace('\r\n', '\n'), (b'\r\n' in raw)


def write(path, txt, crlf):
    if crlf:
        txt = txt.replace('\n', '\r\n')
    with io.open(path, 'wb') as f:
        f.write(txt.encode('utf-8'))


def sub1(path, txt, old, new, marker):
    """整段替换：old 必须恰好命中 1 次；marker 已在文件里则视为已打过。"""
    if marker in txt:
        print('  SKIP %s' % marker)
        return txt, False
    n = txt.count(old)
    if n != 1:
        raise SystemExit('!! 锚点命中 %d 次（应为 1）：%s\n   %r' % (n, path, old[:90]))
    print('  OK   %s' % marker)
    return txt.replace(old, new), True


# ─────────────────────────────────────────────────────────────────────────────
# 1) Core/RaidUI.lua
# ─────────────────────────────────────────────────────────────────────────────
RAID_EDITS = [
    # ① 文件头：把「默认取 os.time()」这条错误口径换成时钟链，并写明事故
    (
        '--   给到秒是假精度；RU.CountdownText(nowSec, shift) 是纯函数（默认取 os.time()），\n'
        '--   Build 里挂 1 秒 OnUpdate 重算，只在文本变化时才 SetText。\n',

        '--   给到秒是假精度；RU.CountdownText(nowSec, shift) 是纯函数（默认取 RU.NowSec()），\n'
        '--   Build 里挂 1 秒 OnUpdate 重算，只在文本变化时才 SetText。\n'
        '--\n'
        '-- ★★ 时钟一律走 RU.NowSec()，**不许直接写 os 的 time**（2026-09-29 实机事故）：\n'
        '--   WoW 的 Lua **没有 os 库**（暴雪用全局 time() / date() / difftime() 顶替），\n'
        '--   所以 `os.time()` 在客户端会抛 `attempt to index a nil value`，\n'
        '--   把整页 Build 打断（实测：团本页直接开不出来）。\n'
        '--   ★ 离线 harness 跑的是 lupa 真 Lua：标准库齐全（有 os.time）、反而没有全局 time\n'
        '--   → 「写了 os.* 的代码」在离线恒绿、实机必崩（harness 盲区，非偶然）。\n'
        '--   故 harness 现已抹掉 os、补上全局 time()，与客户端同形。\n'
        '--   RU.PickClock(env) 是纯函数（环境可注入，便于离线断言），解析顺序：\n'
        '--   time() → GetServerTime() → env.os.time()（仅离线桩用，且 type() 守卫）。\n'
        '--   一个时钟都拿不到时倒计时返回空串（不显示、也不报错），绝不阻断 Build。\n',

        '不许直接写 os 的 time',
    ),
    # ② 时钟解析：纯函数 + 载入期解析（都放在 CountdownText 之前）
    (
        'function RU.CountdownText(nowSec, shift)\n'
        '    local remain = RU.UnlockAt(shift) - (nowSec or os.time())\n',

        'function RU.PickClock(env)\n'
        '    if type(env) ~= "table" then return nil end\n'
        '    if type(env.time) == "function" then return env.time end\n'
        '    if type(env.serverTime) == "function" then return env.serverTime end\n'
        '    if type(env.os) == "table" and type(env.os.time) == "function" then\n'
        '        return env.os.time\n'
        '    end\n'
        '    return nil\n'
        'end\n'
        '\n'
        'local Clock = RU.PickClock({ time = _G.time,\n'
        '                             serverTime = _G.GetServerTime,\n'
        '                             os = _G.os })\n'
        '\n'
        'function RU.NowSec()\n'
        '    if Clock then return Clock() end\n'
        '    return nil\n'
        'end\n'
        '\n'
        'function RU.CountdownText(nowSec, shift)\n'
        '    local now = nowSec or RU.NowSec()\n'
        '    local target = RU.UnlockAt(shift)\n'
        '    if type(now) ~= "number" or type(target) ~= "number" then return "" end\n'
        '    local remain = target - now\n',

        'function RU.PickClock(env)',
    ),
]

print('== 1) Core/RaidUI.lua ==')
txt, crlf = read(RAID)
changed = 0
for old, new, marker in RAID_EDITS:
    txt, hit = sub1(RAID, txt, old, new, marker)
    changed += 1 if hit else 0
if changed:
    write(RAID, txt, crlf)
print('   RaidUI 落盘 = %s（行尾 %s，共 %d 处）'
      % (bool(changed), 'CRLF' if crlf else 'LF', changed))


# ─────────────────────────────────────────────────────────────────────────────
# 2) 两份 harness：静态断言
# ─────────────────────────────────────────────────────────────────────────────
STATIC_OLD = (
    "    ck('★★ RaidUI 倒计时到「分」（纯函数 RU.CountdownText，默认 os.time()）',\n"
    "       'function RU.CountdownText(nowSec, shift)' in _ra\n"
    "       and 'RU.UnlockAt(shift) - (nowSec or os.time())' in _ra)\n"
)
STATIC_NEW = (
    "    ck('★★ RaidUI 倒计时到「分」（纯函数 RU.CountdownText，默认 RU.NowSec()）',\n"
    "       'function RU.CountdownText(nowSec, shift)' in _ra\n"
    "       and 'local now = nowSec or RU.NowSec()' in _ra\n"
    "       and '距首批开放还有 %d 天 %d 小时 %d 分' in _ra)\n"
    "\n"
    "    # ★★ 时钟不许直用 os.*（2026-09-29 实机事故）：WoW 的 Lua 没有 os 库（只有全局\n"
    "    #    time() / date() / difftime()），而 lupa 的离线 harness 标准库齐全 ——\n"
    "    #    「写了 os.* 的代码」离线恒绿、实机必崩。故这里正面钉住时钟链 + 反向全仓扫。\n"
    "    def _os_direct_hits(src_text):\n"
    "        hits = []\n"
    "        for i, line in enumerate(src_text.replace('\\r\\n', '\\n').split('\\n'), 1):\n"
    "            if line.lstrip().startswith('--'):          # 注释里提 os.time 不算违规\n"
    "                continue\n"
    "            if re.search(r'(?<![\\w.])os\\.(time|date|clock|difftime|getenv)\\s*\\(', line):\n"
    "                hits.append(i)\n"
    "        return hits\n"
    "\n"
    "    ck('★★ RaidUI 时钟链：time() → GetServerTime() → 离线桩 os.time（os 必须 type 守卫）',\n"
    "       'function RU.PickClock(env)' in _ra\n"
    "       and 'function RU.NowSec()' in _ra\n"
    "       and 'time = _G.time' in _ra\n"
    "       and 'if type(env.time) == \"function\" then return env.time end' in _ra\n"
    "       and 'type(env.os) == \"table\" and type(env.os.time) == \"function\"' in _ra)\n"
    "    _os_hit = []\n"
    "    for _base, _dirs, _fs in os.walk(os.path.join(ADDON, 'Core')):\n"
    "        for _f in sorted(_fs):\n"
    "            if not _f.endswith('.lua'):\n"
    "                continue\n"
    "            _p = os.path.join(_base, _f)\n"
    "            with open(_p, encoding='utf-8', errors='replace') as _fh:\n"
    "                for _ln in _os_direct_hits(_fh.read()):\n"
    "                    _os_hit.append('%s:%d' % (os.path.relpath(_p, ADDON).replace(os.sep, '/'), _ln))\n"
    "    ck('★★ 全仓 Core/**/*.lua 不许直用 os.*（WoW 无 os 库，用全局 time()/date()）',\n"
    "       not _os_hit, ', '.join(_os_hit))\n"
)
STATIC_MARKER = "RaidUI 时钟链：time() → GetServerTime()"

# 运行时断言：接在「倒计时跨过开放时刻」之后
RT_OLD = (
    "        ck(\"★★ 倒计时跨过开放时刻即显示「已开启」（两档各自跨点）\",\n"
    "           RM.CountdownText(_tgt + 10, false) == \"已开启\",\n"
    "           RM.CountdownText(_tgt + 10, false))\n"
)
RT_NEW = (
    "        ck(\"★★ 倒计时跨过开放时刻即显示「已开启」（两档各自跨点）\",\n"
    "           RM.CountdownText(_tgt + 10, false) == \"已开启\",\n"
    "           RM.CountdownText(_tgt + 10, false))\n"
    "        -- ★★ 时钟解析链（2026-09-29 实机事故：os.time() 在客户端不存在）\n"
    "        local _cT = RM.PickClock({ time = function() return 11 end })\n"
    "        local _cS = RM.PickClock({ serverTime = function() return 22 end })\n"
    "        ck(\"★★ 时钟解析链：优先全局 time()，次 GetServerTime()，最后离线桩 os.time\",\n"
    "           _cT ~= nil and _cT() == 11\n"
    "           and _cS ~= nil and _cS() == 22\n"
    "           and RM.PickClock({ os = { time = function() return 33 end } })() == 33\n"
    "           and RM.PickClock({}) == nil and RM.PickClock(nil) == nil)\n"
    "        ck(\"★★ 拿不到时钟时倒计时返回空串（不报错、不阻断 Build）\",\n"
    "           RM.CountdownText(\"no-clock\") == \"\", tostring(RM.CountdownText(\"no-clock\")))\n"
    "        ck(\"★★ 无参调用走与游戏同款全局 time()（桩 time 固定 -> 现算得出文案）\",\n"
    "           RM.NowSec() == 1796850000 - 3660\n"
    "           and RM.CountdownText() == \"距首批开放还有 1 天 1 小时 1 分\",\n"
    "           tostring(RM.NowSec()) .. \" / \" .. tostring(RM.CountdownText()))\n"
)
RT_MARKER = "无参调用走与游戏同款全局 time()"

# 运行环境对齐：抹掉 os、补上全局 time()
ENV_OLD = (
    "    lua = lua51.LuaRuntime(unpack_returned_tuples=True)\n"
    "    lua.execute(T.STUB)\n"
)
ENV_NEW = (
    "    lua = lua51.LuaRuntime(unpack_returned_tuples=True)\n"
    "    lua.execute(T.STUB)\n"
    "    # ★★ 环境与客户端同形（2026-09-29 实机事故）：WoW 的 Lua **没有 os 库**\n"
    "    #    （暴雪用全局 time() / date() / difftime() 顶替），而 lupa 自带完整标准库\n"
    "    #    → 「写了 os.* 的代码」在离线 harness 恒绿、实机必崩（团本页倒计时就栽在这）。\n"
    "    #    这里把 os 抹掉、补上全局 time()（固定时刻，便于断言「无参调用」那条路径）。\n"
    "    #    注意：桩自身不用 os，所以抹掉是安全的；哪天桩要用，得先在这里补等价实现。\n"
    "    lua.execute('os = nil')\n"
    "    lua.execute('time = function() return 1796850000 - 3660 end')\n"
)
ENV_MARKER = "环境与客户端同形（2026-09-29 实机事故）"

print('== 2) harness 两份 ==')
for path in CHECKS:
    print(' %s' % os.path.basename(path))
    txt, crlf = read(path)
    changed = 0
    for old, new, marker in ((STATIC_OLD, STATIC_NEW, STATIC_MARKER),
                             (RT_OLD, RT_NEW, RT_MARKER),
                             (ENV_OLD, ENV_NEW, ENV_MARKER)):
        txt, hit = sub1(path, txt, old, new, marker)
        changed += 1 if hit else 0
    if changed:
        compile(txt, path, 'exec')   # 落盘前语法自检（Lua 语法混进 Python 段会在这里炸）
        write(path, txt, crlf)
        py_compile.compile(path, doraise=True)
    print('   落盘 = %s（行尾 %s，共 %d 处）'
          % (bool(changed), 'CRLF' if crlf else 'LF', changed))

print('\npy_compile OK；全部补丁幂等完成。')
