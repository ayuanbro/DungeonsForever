# -*- coding: utf-8 -*-
"""向游戏窗口投递鼠标消息（PostMessageW，不改前台、不动物理光标）。
用法：
    python _temp/_mouse_probe.py info
    python _temp/_mouse_probe.py move  X Y      # 客户端像素坐标
    python _temp/_mouse_probe.py click X Y      # 先 move 再 down/up
"""
import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import time

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_MOUSEWHEEL = 0x020A
MK_LBUTTON = 0x0001


def game_hwnd():
    out = subprocess.check_output(
        ['D:/workspace/project-024-wuxian-workshop/.venv/Scripts/wuxian.exe', 'status'],
        text=True)
    pid = None
    for line in out.splitlines():
        if line.startswith('game'):
            for tok in line.replace(':', ' ').split():
                if tok.isdigit() and len(tok) > 2 and 'pid' not in tok:
                    pid = int(tok)
                    break
            # "game    pid 6540  build ..." → pid 后的第一个数字
            parts = line.split()
            if 'pid' in parts:
                pid = int(parts[parts.index('pid') + 1])
            break
    if not pid:
        raise SystemExit('no game pid in wuxian status')
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, lp):
        wpid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid and user32.IsWindowVisible(hwnd):
            r = wt.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(r))
            found.append((hwnd, r.right, r.bottom))
        return True

    user32.EnumWindows(cb, 0)
    if not found:
        raise SystemExit('no visible window for pid %d' % pid)
    found.sort(key=lambda t: -(t[1] * t[2]))
    return found[0]


def lparam(x, y):
    return (y << 16) | (x & 0xFFFF)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'info'
    hwnd, cw, ch = game_hwnd()
    if cmd == 'info':
        fg = user32.GetForegroundWindow()
        print('hwnd=%s client=%dx%d foreground=%s' % (hwnd, cw, ch, fg == hwnd))
        return
    x, y = int(sys.argv[2]), int(sys.argv[3])
    ok1 = user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam(x, y))
    time.sleep(0.05)
    if cmd == 'move':
        print('move %d,%d -> %s' % (x, y, ok1))
        return
    if cmd == 'wheel':
        delta = int(sys.argv[4]) if len(sys.argv) > 4 else 120
        wp = (delta & 0xFFFF) << 16
        ok2 = user32.PostMessageW(hwnd, WM_MOUSEWHEEL, wp, lparam(x, y))
        print('wheel %d,%d delta=%d -> %s' % (x, y, delta, ok2))
        return
    ok2 = user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam(x, y))
    time.sleep(0.08)
    if cmd == 'drag':
        dx, dy = int(sys.argv[4]), int(sys.argv[5])
        steps = 8
        for i in range(1, steps + 1):
            mx, my = x + dx * i // steps, y + dy * i // steps
            user32.PostMessageW(hwnd, WM_MOUSEMOVE, MK_LBUTTON, lparam(mx, my))
            time.sleep(0.03)
        ok3 = user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam(x + dx, y + dy))
        print('drag %d,%d -> %+d,%+d -> %s' % (x, y, dx, dy, ok3))
        return
    ok3 = user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam(x, y))
    print('click %d,%d -> move=%s down=%s up=%s' % (x, y, ok1, ok2, ok3))


main()
