import ctypes
import sys
import time

u = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def find_game(title):
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, l):
        if u.IsWindowVisible(h):
            n = u.GetWindowTextLengthW(h)
            b = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, b, n + 1)
            if b.value == title:
                out.append(h)
        return True

    u.EnumWindows(cb, 0)
    return out

hwnd = find_game("魔兽世界")
if not hwnd:
    print("ERR no window")
    sys.exit(1)
hwnd = hwnd[0]
fg = u.GetForegroundWindow()
tid_fg = u.GetWindowThreadProcessId(fg, None)
tid_me = kernel32.GetCurrentThreadId()
u.AttachThreadInput(tid_me, tid_fg, True)
u.AttachThreadInput(tid_me, u.GetWindowThreadProcessId(hwnd, None), True)
u.BringWindowToTop(hwnd)
u.SetForegroundWindow(hwnd)
u.AttachThreadInput(tid_me, tid_fg, False)
u.AttachThreadInput(tid_me, u.GetWindowThreadProcessId(hwnd, None), False)
time.sleep(0.4)
print("fg=", u.GetForegroundWindow() == hwnd)
