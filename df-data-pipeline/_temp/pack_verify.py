# -*- coding: utf-8 -*-
"""无限副本手册 · 打包前检 + 打包一键入口（结构参照 TalentsForever/_temp/pack_verify.py）。

依次执行，全部输出同时落 _temp/pack_cmd_out.txt：
  1) luacheck 全量               要求 0 errors（warning 允许：WoW 全局未声明的固有噪声）
  2) 残留身份扫描                 功能性旧身份串（注释里的溯源说明放行）
  2b) 注释红线扫描                 只扫注释：其他插件名 / 站点措辞（check_comment_redline.py）
  2c) 注释零容忍                   打包集出现任何一行注释即失败（check_zero_comments.py）
  3) 变异锚点体检                 98 条变异锚点各自恰好命中 1 次（秒级；锚点烂掉是静默的）
  4) 同步 beta                    harness 断的是 beta 副本，漏同步 = 全绿但跑的是旧代码
  5) 行为 harness                 df_dungeon_check.py（TF_BUILD=16001 无限服；本插件只工作于无限服）
  6) 打包                        package_zip.py（含引用反向扫描 + 孤儿扫描）

用法：
  python pack_verify.py            # 前检 + 正式打包
  python pack_verify.py --dry-run  # 前检 + 只列打包清单，不落盘
"""
import glob
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "pack_cmd_out.txt")

LUACHECK = r"D:\workspace\tool\luacheck.exe"
PY_VENV = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

LUA_TARGETS = ("Core", "Locales")
TOC_NAME = "DungeonsForever.toc"

# 功能性旧身份串（旧插件身份必须彻底消失）。2026-09-23 起注释里也不再有溯源说明，
# 故这里**不再放行任何串**；ns.TalentSimFrame 是有意保留的宿主字段名，不列入本表。
# 2026-09-26 增补第三方站名/「站点」措辞（数据来源口径 = 只保留 wowhead）。
RESIDUAL_RE = re.compile(
    r"TalentsForeverDB|TalentsForever_MainFrame|TalentsForever_SourceURL"
    r"|Interface[/\\]AddOns[/\\]TalentsForever|ns\.TalentSimUI|ns\.OpenTalentSim"
    r"|TALENTSFOREVER|无限天赋模拟器"
    r"|foreverchanges|Icy-Veins|icy-veins|warcrafttavern|indiekings|MageBookTracker"
    r"|站点")
RESIDUAL_ALLOW = (
    # 「零站点回退」是否定句（说明运行期不从数据站取、从客户端取），非残留身份串——放行。
    # 2026-10-08 PvP 三件套（PvPUI / Data_PvPRanks / Data_PvPSets）的文件头注释命中「站点」二字。
    "零站点回退",
)

FAILED = []
lines = []


def emit(msg=""):
    print(msg)
    lines.append(msg)


def run(cmd, label, cwd=None, env=None):
    r = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    tail = (r.stdout or "").strip().splitlines()
    emit("-- %s  exit=%d" % (label, r.returncode))
    for t in tail[-14:]:
        emit("   " + t)
    if r.stderr and r.stderr.strip():
        emit("   [stderr] " + r.stderr.strip()[:600])
    return r


def lua_files():
    out = []
    for sub in LUA_TARGETS:
        out += glob.glob(os.path.join(ROOT, sub, "**", "*.lua"), recursive=True)
    return sorted(out)


def step_luacheck():
    files = lua_files()
    r = run([LUACHECK, "--no-max-string-line-length"] + files, "luacheck")
    text = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"Total:\s*\d+\s+warnings\s*/\s*(\d+)\s+errors", text)
    errors = int(m.group(1)) if m else (0 if r.returncode == 0 else -1)
    if errors != 0:
        FAILED.append("luacheck: %s error（%d 文件）" % (errors if errors >= 0 else "?", len(files)))
    else:
        emit("[OK] luacheck %d 文件 0 errors" % len(files))


def step_residual():
    hits = []
    targets = [os.path.join(ROOT, TOC_NAME)] + lua_files()
    for p in targets:
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                for i, ln in enumerate(f, 1):
                    if RESIDUAL_RE.search(ln) and not any(a in ln for a in RESIDUAL_ALLOW):
                        hits.append("%s:%d  %s" % (os.path.relpath(p, ROOT), i, ln.strip()[:110]))
        except OSError:
            pass
    emit("-- 残留身份扫描")
    for h in hits:
        emit("   " + h)
    if hits:
        FAILED.append("残留扫描命中 %d 处" % len(hits))
    else:
        emit("[OK] 残留扫描 0 命中")


def step_comment_redline():
    """注释红线（AGENTS.md 注释纪律）：注释里出现其他插件名 / 站点即打包失败。"""
    r = run([PY_VENV, os.path.join(HERE, "check_comment_redline.py")], "comment_redline")
    if r.returncode != 0:
        FAILED.append("注释红线命中 exit=%d" % r.returncode)


def step_zero_comments():
    """注释零容忍（2026-10-17 用户定：插件不带任何注释）。
    生成器重跑会把文件头 banner 带回来 —— 这道门就是拦它的。Libs/ 第三方豁免。"""
    r = run([PY_VENV, os.path.join(HERE, "check_zero_comments.py")], "check_zero_comments")
    if r.returncode != 0:
        FAILED.append("注释零容忍命中 exit=%d" % r.returncode)


def step_mut_anchors():
    """变异锚点体检（秒级）：锚点变成 0 命中时那条变异就**再注入不进去**，
    `df_check_new_muts.py` 只会在跑到它时才 assert 失败 —— 不跑 --all 就是静默的。
    打包前必须确认「所有断言都还有人守」，故放在这里。"""
    r = run([PY_VENV, os.path.join(HERE, "check_mut_anchors.py")], "check_mut_anchors")
    if r.returncode != 0:
        FAILED.append("变异锚点体检不通过 exit=%d" % r.returncode)


def step_sync_beta():
    r = run([PY_VENV, os.path.join(HERE, "sync_beta.py"), "--apply"], "sync_beta")
    if r.returncode != 0:
        FAILED.append("sync_beta 失败 exit=%d" % r.returncode)


def step_harness():
    """只跑 16001 无限服（2026-10-10 用户定案：本插件只工作于无限服，不再双端跑）。"""
    env = dict(os.environ, TF_BUILD="16001")
    r = run([PY_VENV, os.path.join(HERE, "df_dungeon_check.py")],
            "harness TF_BUILD=16001", env=env)
    if r.returncode != 0:
        FAILED.append("harness(16001) 失败 exit=%d" % r.returncode)


def step_pack(dry):
    cmd = [PY_VENV, os.path.join(HERE, "package_zip.py")]
    if dry:
        cmd.append("--dry-run")
    r = run(cmd, "package_zip")
    if r.returncode != 0:
        FAILED.append("package_zip 失败 exit=%d" % r.returncode)


def main():
    dry = "--dry-run" in sys.argv[1:]
    emit("=== 无限副本手册 打包前检 %s ===" % ("(DRY-RUN)" if dry else ""))
    step_luacheck()
    step_residual()
    step_comment_redline()
    step_zero_comments()
    step_mut_anchors()
    step_sync_beta()
    step_harness()
    step_pack(dry)

    emit()
    if FAILED:
        emit("[FAIL] " + "；".join(FAILED))
    else:
        emit("[PASS] 前检全部通过" if dry else "[PASS] 前检通过并已打包")

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("日志 -> " + OUT)
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
