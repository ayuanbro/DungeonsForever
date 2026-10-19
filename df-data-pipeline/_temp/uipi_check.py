"""UIPI / 完整性级别诊断：判断窗口消息注入是否会被内核拦截。
用法：python _temp/uipi_check.py
"""
import ctypes
import ctypes.wintypes as w
import os

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
adv = ctypes.WinDLL('advapi32', use_last_error=True)
u32 = ctypes.WinDLL('user32', use_last_error=True)

LV = {0x0000: "Untrusted", 0x1000: "Low", 0x2000: "Medium",
      0x2100: "Medium+", 0x3000: "High", 0x4000: "System"}


def find_windows(sub):
    out = []

    @ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    def cb(h, l):
        n = u32.GetWindowTextLengthW(h)
        if n:
            b = ctypes.create_unicode_buffer(n + 1)
            u32.GetWindowTextW(h, b, n + 1)
            if sub in b.value:
                pid = w.DWORD()
                u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
                out.append((h, b.value, pid.value))
        return True

    u32.EnumWindows(cb, 0)
    return out


def integrity(pid):
    h = k32.OpenProcess(0x1000, False, pid)
    if not h:
        return "OpenProcess DENIED err=%d" % ctypes.get_last_error()
    tok = w.HANDLE()
    if not adv.OpenProcessToken(h, 0x0008, ctypes.byref(tok)):
        e = ctypes.get_last_error()
        k32.CloseHandle(h)
        return "OpenProcessToken DENIED err=%d" % e
    need = w.DWORD(0)
    adv.GetTokenInformation(tok, 25, None, 0, ctypes.byref(need))
    buf = ctypes.create_string_buffer(need.value)
    ok = adv.GetTokenInformation(tok, 25, buf, need.value, ctypes.byref(need))
    rid = None
    if ok:
        sid = ctypes.cast(buf, ctypes.POINTER(ctypes.c_void_p))[0]
        cnt = ctypes.cast(sid, ctypes.POINTER(ctypes.c_ubyte))[1]
        rid = [ctypes.cast(sid + 8 + 4 * i,
                           ctypes.POINTER(ctypes.c_uint32))[0] for i in range(cnt)][-1]
    k32.CloseHandle(tok)
    k32.CloseHandle(h)
    return "0x%04X %s" % (rid, LV.get(rid, "?")) if rid is not None else "parse-fail"


def main():
    me = os.getpid()
    print("== 完整性级别 ==")
    print("  本进程(注入探针所在) pid=%-7d %s" % (me, integrity(me)))

    games = [x for x in find_windows("魔兽世界") if x[2] != me]
    target_pid = None
    for h, t, pid in games:
        if "资源管理器" in t:
            continue
        target_pid = pid
        print("  游戏窗口 hwnd=0x%X pid=%-7d %s" % (h, pid, integrity(pid)))
        break

    if target_pid is None:
        print("  [warn] 未找到游戏窗口")
        return

    lv_me = integrity(me)
    lv_game = integrity(target_pid)
    print()
    if "High" in lv_game and "Medium" in lv_me:
        print("[结论] 注入进程 Medium < 游戏 High => UIPI 会拦截所有键盘/焦点消息")
    elif lv_game.split()[1] == lv_me.split()[1]:
        print("[结论] 进程同级 => UIPI 不拦截，PostMessage 注入可用")
    else:
        print("[结论] 见上表自行判断")

    print()
    print("== PostMessage 探针（err=5 = 被 UIPI 拦截）==")
    for h, t, pid in games:
        if pid == target_pid:
            print("  窗口 0x%X" % h)
            for msg, nm in ((0x0000, "WM_NULL"), (0x0100, "WM_KEYDOWN"),
                            (0x0101, "WM_KEYUP"), (0x0102, "WM_CHAR"),
                            (0x0007, "WM_SETFOCUS")):
                ctypes.set_last_error(0)
                r = u32.PostMessageW(h, msg, 0x0D if msg in (0x100, 0x101, 0x102) else 0, 0)
                e = ctypes.get_last_error()
                tag = "  << UIPI BLOCKED" if e == 5 else ("  (UIPI 白名单)" if e == 0 and msg == 0 else "")
                print("     %-14s ret=%d err=%-2d%s" % (nm, r, e, tag))
            break


if __name__ == "__main__":
    main()
