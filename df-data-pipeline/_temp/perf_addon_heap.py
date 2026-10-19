# -*- coding: utf-8 -*-
"""在真 Lua 5.1 里按 TOC 顺序加载 DungeonsForever 的全部文件，测其 Lua 堆占用。

背景：游戏内 GetAddOnMemoryUsage 的口径是「该插件代码执行期间分配、归属于它的
Lua 字节数」。本脚本用同一口径在离线复现，用于在无法连接游戏（如客户端以管理员
运行、UIPI 拦截输入）时给出内存占用的实测近似值。

用法：python perf_addon_heap.py [zhCN|zhTW|enUS]
"""
import os
import re
import sys
import time
from lupa import lua51

ROOT = r"D:/workspace/DungeonsForever"
TOC = os.path.join(ROOT, "DungeonsForever.toc")
COND_RE = re.compile(r"\s*[\[(].*$")
SCRIPT_RE = re.compile(r'<Script\s+[^>]*file\s*=\s*"([^"]+)"', re.I)
INCLUDE_RE = re.compile(r'<Include\s+[^>]*file\s*=\s*"([^"]+)"', re.I)

LUA_DRIVER = r"""
local fileList, root = ...
local files = {}
for line in string.gmatch(fileList, "[^\n]+") do files[#files + 1] = line end

local function makeProxy()
  local p
  p = setmetatable({}, {
    __index = function(t, k) local v = makeProxy(); rawset(t, k, v); return v end,
    __call = function() return makeProxy() end,
    __concat = function() return "" end, __tostring = function() return "" end,
    __add = function() return 0 end, __sub = function() return 0 end,
    __mul = function() return 0 end, __div = function() return 0 end,
    __mod = function() return 0 end, __pow = function() return 0 end,
    __unm = function() return 0 end, __eq = function() return false end,
    __lt = function() return false end, __le = function() return false end,
  })
  return p
end

local env = setmetatable({}, {})
env._G = env
env.type=type env.pairs=pairs env.ipairs=ipairs env.next=next env.tostring=tostring
env.tonumber=tonumber env.rawget=rawget env.rawset=rawset env.setmetatable=setmetatable
env.getmetatable=getmetatable env.rawequal=rawequal env.error=error env.assert=assert
env.pcall=pcall env.xpcall=xpcall env.unpack=unpack env.select=select
env.collectgarbage=collectgarbage env.string=string env.table=table env.math=math
env.os=os env.coroutine=coroutine env.print=function() end
env.GetLocale = function() return "zhCN" end
env.GetBuildInfo = function() return "1.60.1", "70245", "2026", 16001 end
env.strsplit = function(sep, s) local o = {}; for x in string.gmatch(s, "([^" .. sep .. "]+)") do o[#o+1] = x end; return unpack(o) end
env.strtrim = function(s) return (string.gsub(s, "^%s*(.-)%s*$", "%1")) end
env.wipe = function(t) if type(t) == "table" then for k in pairs(t) do t[k] = nil end end; return t end
env.tContains = function() return false end
env.IsInRaid = function() return false end
env.IsAddOnLoaded = function() return false, false end
env.C_Timer = { After = function() end, NewTimer = function() return {} end, NewTicker = function() return {} end }
env.CreateFrame = function()
  local f = makeProxy()
  f.SetScript = function() end f.HookScript = function() end
  f.RegisterEvent = function() end f.RegisterUnitEvent = function() end
  f.Show = function() end f.Hide = function() end f.SetPoint = function() end
  f.SetSize = function() end f.CreateTexture = function() return makeProxy() end
  f.CreateFontString = function() return makeProxy() end
  return f
end
env.hooksecurefunc = function() end
env.SlashCmdList = {}
env.SLASH = setmetatable({}, { __index = function() return "" end })
env.GetAddOnInfo = function() return "DungeonsForever", 1, "", true, "", "", false, false, "", "", "", "" end
env.C_AddOns = { GetAddOnInfo = env.GetAddOnInfo, GetNumAddOns = function() return 0 end,
                 IsAddOnLoaded = function() return false, false end, LoadAddOn = function() end }
-- 未知全局：返回代理（近似真实客户端里「有这个东西」），并缓存以免重复分配
local proxyCache = {}
setmetatable(env, { __index = function(t, k)
  local v = proxyCache[k]; if v == nil then v = makeProxy(); proxyCache[k] = v end
  rawset(t, k, v); return v
end })

local ns = {}                       -- 与游戏一致：跨文件共享的 addon 私有表
local ADDON = "DungeonsForever"

collectgarbage("collect"); collectgarbage("collect")
local base = collectgarbage("count")
local rows, failed = {}, {}
for i = 1, #files do
  local rel = files[i]
  local fh = io.open(root .. "/" .. rel, "rb")
  if not fh then
    failed[#failed + 1] = { rel, "MISSING" }
  else
    local data = fh:read("*a"); fh:close()
    collectgarbage("collect"); collectgarbage("collect")
    local before = collectgarbage("count")
    local chunk, err = loadstring(data, "@" .. rel)
    if not chunk then
      failed[#failed + 1] = { rel, tostring(err) }
    else
      setfenv(chunk, env)
      io.stderr:write(".") io.stderr:flush()
      debug.sethook(function() error("__STEP_LIMIT__") end, "", 4000000)
      local ok, e = pcall(chunk, ADDON, ns)
      debug.sethook()
      if not ok then failed[#failed + 1] = { rel, tostring(e) } end
    end
    collectgarbage("collect"); collectgarbage("collect")
    local after = collectgarbage("count")
    rows[#rows + 1] = { rel, before, after, after - before }
  end
end
collectgarbage("collect"); collectgarbage("collect")
local proxyCount = 0
for _ in pairs(proxyCache) do proxyCount = proxyCount + 1 end
return { base = base, final = collectgarbage("count"), rows = rows, failed = failed,
         proxies = proxyCount }
"""


def expand(path, depth=0, seen=None):
    """把 TOC 条目展开成真正的 .lua 序列（递归展开 XML 的 Script/Include）。"""
    if seen is None:
        seen = set()
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        return []
    if path.lower().endswith(".lua"):
        return [path]
    if not path.lower().endswith(".xml") or depth > 6:
        return []
    text = open(p, encoding="utf-8", errors="replace").read()
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    base_dir = os.path.dirname(path)
    out = []
    for m in re.finditer(r"<(Script|Include)\s+[^>]*file\s*=\s*\"([^\"]+)\"", text, re.I):
        kind, rel = m.group(1).lower(), m.group(2).replace("\\", "/")
        # XML 里的路径相对插件根写（如 "Libs\LibHUI\..."），也有相对当前 XML 的
        cand = os.path.normpath(rel.replace("/", os.sep))
        full = os.path.join(ROOT, cand)
        if not os.path.exists(full):
            cand2 = os.path.normpath(os.path.join(base_dir, rel.replace("/", os.sep)))
            if os.path.exists(os.path.join(ROOT, cand2)):
                cand = cand2
            else:
                continue
        key = cand.lower()
        if key in seen:
            continue
        seen.add(key)
        if kind == "script":
            out.append(cand)
        else:
            out.extend(expand(cand, depth + 1, seen))
    return out


def toc_files(locale):
    out, seen = [], set()
    with open(TOC, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            s = raw.rstrip("\r\n").strip()
            if not s or s.startswith("#"):
                continue
            cond = None
            m = re.search(r"\[AllowLoadTextLocale\s+([A-Za-z0-9_,\s]+)\]", s)
            if m:
                cond = [c.strip() for c in m.group(1).split(",") if c.strip()]
            path = COND_RE.sub("", s).strip()
            if cond and locale not in cond:
                continue
            for f in expand(path):
                k = f.lower()
                if k not in seen:
                    seen.add(k)
                    out.append(f)
    return out


def main():
    locale = next((a for a in sys.argv[1:] if not a.startswith("--")), "zhCN")
    files = toc_files(locale)
    total = sum(os.path.getsize(os.path.join(ROOT, f)) for f in files
                if os.path.exists(os.path.join(ROOT, f)))
    rt = lua51.LuaRuntime(encoding=None, unpack_returned_tuples=True)
    t0 = time.perf_counter()
    res = rt.execute(LUA_DRIVER,
                     "\n".join(files).encode("utf-8"),
                     ROOT.replace("\\", "/").encode("utf-8"))
    elapsed = (time.perf_counter() - t0) * 1000

    base = float(res[b"base"]); final = float(res[b"final"])

    def tx(x):
        return x.decode("utf-8", "replace") if isinstance(x, (bytes, bytearray)) else str(x)

    rows = [(tx(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in res[b"rows"].values()]
    failed = [(tx(f[1]), tx(f[2])) for f in res[b"failed"].values()]

    def norm(s):
        s = s.replace("\\", "/")
        return s if s.startswith("/") else "/" + s

    data_kb = sum(d for rel, b, a, d in rows if "/Core/Data/" in norm(rel))
    libs_kb = sum(d for rel, b, a, d in rows if norm(rel).startswith("/Libs/"))
    core_kb = sum(d for rel, b, a, d in rows
                  if norm(rel).startswith("/Core/") and "/Core/Data/" not in norm(rel))
    loc_kb = sum(d for rel, b, a, d in rows if norm(rel).startswith("/Locales/"))
    proxies = float(res[b"proxies"])

    print("=" * 82)
    print("DungeonsForever  Lua 堆占用实测（真 Lua 5.1 / lupa）   locale = %s" % locale)
    print("=" * 82)
    print("TOC 实际加载文件  : %d 个 / %.2f MB 源码" % (len(files), total / 1048576.0))
    print("环境基线堆        : %8.1f KB" % base)
    print("加载后总堆        : %8.1f KB" % final)
    print(">> 插件净贡献     : %8.1f KB  =  %.2f MB" % (final - base, (final - base) / 1024.0))
    print("   其中 数据层    : %8.1f KB  =  %.2f MB" % (data_kb, data_kb / 1024.0))
    print("        代码层    : %8.1f KB  =  %.2f MB" % (core_kb, core_kb / 1024.0))
    print("        嵌入库    : %8.1f KB  =  %.2f MB" % (libs_kb, libs_kb / 1024.0))
    print("        本地化    : %8.1f KB  =  %.2f MB" % (loc_kb, loc_kb / 1024.0))
    print("加载耗时          : %.0f ms" % elapsed)
    print("存根膨胀上界      : %d 个代理对象 ≈ %.0f KB（<%.1f%%，已计入总量）"
          % (proxies, proxies * 0.10, 100.0 * proxies * 0.10 / max(final - base, 1)))
    print("-" * 82)
    print("%-50s %9s %11s" % ("单文件堆增量 Top 20", "源码KB", "堆增量KB"))
    for rel, b, a, d in sorted(rows, key=lambda r: -r[3])[:20]:
        print("%-50s %9.0f %11.0f"
              % (norm(rel)[-50:], os.path.getsize(os.path.join(ROOT, rel)) / 1024.0, d))
    if failed:
        print("-" * 82)
        print("未完整执行 %d 个文件（已分配部分仍计入）：" % len(failed))
        for rel, why in failed[:14]:
            print("   %-48s %s" % (norm(rel)[-48:], why[:56]))
    print("=" * 82)


if __name__ == "__main__":
    main()
