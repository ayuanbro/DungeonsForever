# -*- coding: utf-8 -*-
"""用真 Lua 5.1 (lupa) 量 DungeonsForever 的「登录期 Lua 解析/执行」成本。
- compile : 只 loadstring（模拟 TOC 列出的每个文件都要编译）
- run     : 编译 + 执行（模拟该文件真的跑起来建表）
"""
import os, time, sys, io
from lupa import lua51

ROOT = r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/DungeonsForever"

def collect():
    paths = []
    for sub in ("Locales", "Libs", "Core"):
        for dp, dn, fn in os.walk(os.path.join(ROOT, sub)):
            for f in fn:
                if f.endswith(".lua"):
                    paths.append(os.path.join(dp, f))
    return sorted(paths)

def load_src(p):
    with open(p, "rb") as fh:
        return fh.read()

def bench(files, do_run, locale):
    rt = lua51.LuaRuntime(encoding=None)
    g = rt.globals()
    # 最小 mock：TOC 里 ns 是第二返回值
    g[b"GetLocale"] = lambda: locale
    g[b"GetBuildInfo"] = lambda: (b"1", b"1", b"1", 120000)
    g[b"type"] = g[b"type"]
    g[b"LibStub"] = None
    total_c = 0.0
    total_r = 0.0
    n_c = 0
    for p in files:
        src = load_src(p)
        t0 = time.perf_counter()
        try:
            chunk = rt.eval(b"function(s) return loadstring(s) end")(src)
        except Exception as e:
            chunk = None
        t1 = time.perf_counter()
        total_c += (t1 - t0)
        n_c += 1
        if do_run and chunk:
            t2 = time.perf_counter()
            try:
                chunk(b"DF", g[b"ns"] if b"ns" in g else None)
            except Exception:
                pass
            t3 = time.perf_counter()
            total_r += (t3 - t2)
    return total_c, total_r, n_c

LOCALE = sys.argv[1] if len(sys.argv) > 1 else "zhCN"
all_files = collect()
size = sum(os.path.getsize(p) for p in all_files) / 1048576.0

# 只编译：全部 TOC 文件
tc, _, n = bench(all_files, False, LOCALE)
print("=== 仅编译（TOC 里全部 %d 个 lua，%.2f MB 源码）===" % (n, size))
print("    耗时 %.0f ms   (%.2f MB/s)" % (tc * 1000, size / tc if tc else 0))

# 编译 + 执行：只跑 zhCN 主数据（一定会跑的）
base = [p for p in all_files if os.sep + "Data" + os.sep in p and os.sep + "zhTW" + os.sep not in p and os.sep + "enUS" + os.sep not in p]
b2 = sum(os.path.getsize(p) for p in base) / 1048576.0
bc, br, bn = bench(base, True, LOCALE)
print("=== 编译+执行 zhCN 主数据（%d 个文件 %.2f MB）===" % (bn, b2))
print("    编译 %.0f ms + 执行 %.0f ms = %.0f ms" % (bc * 1000, br * 1000, (bc + br) * 1000))
