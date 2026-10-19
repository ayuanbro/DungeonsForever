# -*- coding: utf-8 -*-
import os, time, sys
from lupa import lua51
ROOT = r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/DungeonsForever"
def collect(sub):
    out=[]
    for dp,dn,fn in os.walk(os.path.join(ROOT,sub)):
        for f in fn:
            if f.endswith(".lua"): out.append(os.path.join(dp,f))
    return sorted(out)
allf = collect("Locales")+collect("Libs")+collect("Core")
def size(ps): return sum(os.path.getsize(p) for p in ps)/1048576.0
def compile_ms(ps, rt):
    t0=time.perf_counter(); ok=0
    for p in ps:
        try:
            rt.eval(b"function(s) return loadstring(s) end")(open(p,'rb').read()); ok+=1
        except Exception: pass
    return (time.perf_counter()-t0)*1000, ok
rt = lua51.LuaRuntime(encoding=None)
active_locale = sys.argv[1] if len(sys.argv)>1 else "zhCN"
dead = [p for p in allf if os.sep+("enUS" if active_locale!="enUS" else "zhTW")+os.sep in p]
dead += [p for p in allf if os.sep+("zhTW" if active_locale!="zhTW" else "enUS")+os.sep in p]
dead = sorted(set(dead))
keep = [p for p in allf if p not in set(dead)]
w,_ = compile_ms(dead, rt)
k,_ = compile_ms(keep, rt)
print("客户端语言 = %s" % active_locale)
print("  非本语言覆盖层(编译完即 return，纯浪费)：%d 个文件 %.2f MB -> %.0f ms" % (len(dead), size(dead), w))
print("  其余（真正有用的）：%d 个文件 %.2f MB -> %.0f ms" % (len(keep), size(keep), k))
print("  合计 %.0f ms  (可省掉约 %.0f%%)" % (w+k, 100.0*w/(w+k)))
