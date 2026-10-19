import ctypes, sys, time
from ctypes import wintypes

u = ctypes.windll.user32
k = ctypes.windll.kernel32

target_pid = int(sys.argv[1]) if len(sys.argv) > 1 else 0

found = []

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

def cb(hwnd, lparam):
    pid = wintypes.DWORD()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value != target_pid:
        return True
    if not u.IsWindowVisible(hwnd):
        return True
    n = u.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return True
    buf = ctypes.create_unicode_buffer(n + 1)
    u.GetWindowTextW(hwnd, buf, n + 1)
    r = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    found.append((hwnd, buf.value, r.right - r.left, r.bottom - r.top))
    return True

u.EnumWindows(EnumWindowsProc(cb), 0)

for hwnd, title, w, h in found:
    print(f"hwnd={hwnd} size={w}x{h} title={title!r}")

big = [f for f in found if f[2] > 1000]
if not big:
    print("NO BIG WINDOW")
    sys.exit(1)

hwnd = big[0][0]
u.ShowWindow(hwnd, 9)   # SW_RESTORE
time.sleep(0.4)
u.SetForegroundWindow(hwnd)
time.sleep(0.8)
print(f"activated hwnd={hwnd} fg={u.GetForegroundWindow() == hwnd}")
