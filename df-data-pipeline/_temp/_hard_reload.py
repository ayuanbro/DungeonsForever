import ctypes
import sys
import time
from ctypes import wintypes

u = ctypes.windll.user32
k = ctypes.windll.kernel32

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_MENU = 0x12


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _INPUTunion(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("pad", ctypes.c_byte * 32)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTunion)]


def send_key(vk, up=False):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki.wVk = vk
    inp.u.ki.wScan = 0
    inp.u.ki.dwFlags = KEYEVENTF_KEYUP if up else 0
    inp.u.ki.time = 0
    inp.u.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
    u.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def send_char(ch):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki.wVk = 0
    inp.u.ki.wScan = ord(ch)
    inp.u.ki.dwFlags = KEYEVENTF_UNICODE
    inp.u.ki.time = 0
    inp.u.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
    u.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    inp.u.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    u.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def find_game():
    out = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        if u.IsWindowVisible(h):
            n = u.GetWindowTextLengthW(h)
            b = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, b, n + 1)
            if "魔兽世界" in b.value:
                r = wintypes.RECT()
                u.GetClientRect(h, ctypes.byref(r))
                out.append((h, b.value, r.right, r.bottom))
        return True

    u.EnumWindows(cb, 0)
    return out


def main():
    text = sys.argv[1] if len(sys.argv) > 1 else "/reload"
    wins = find_game()
    if not wins:
        print("ERR no window")
        sys.exit(1)
    for w in wins:
        print("candidate", w[0], repr(w[1]), w[2], "x", w[3])
    hwnd = max(wins, key=lambda x: x[2] * x[3])[0]
    fg = u.GetForegroundWindow()
    print("before fg", fg, "target", hwnd)
    u.ShowWindow(hwnd, 9)
    send_key(VK_MENU)
    send_key(VK_MENU, True)
    u.SetForegroundWindow(hwnd)
    u.BringWindowToTop(hwnd)
    u.SetActiveWindow(hwnd)
    time.sleep(0.6)
    print("after fg", u.GetForegroundWindow())
    send_key(VK_ESCAPE)
    time.sleep(0.2)
    send_key(VK_RETURN)
    time.sleep(0.45)
    for ch in text:
        send_char(ch)
        time.sleep(0.03)
    time.sleep(0.2)
    send_key(VK_RETURN)
    time.sleep(0.2)
    send_key(VK_RETURN, True)
    print("sent", repr(text))


main()
