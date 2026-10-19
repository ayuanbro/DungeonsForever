import ctypes, time, sys
u = ctypes.windll.user32
hwnd = 112079692
u.ShowWindow(hwnd, 9)          # SW_RESTORE
time.sleep(0.3)
u.SetForegroundWindow(hwnd)
time.sleep(0.5)
# 客户区 -> 屏幕
ox, oy = 509, 30
cw, ch = 2394, 1354
pw, ph = 2088.0437011719, 1181.5385742188
def to_screen(ux, uy):
    return int(ox + ux * cw / pw), int(oy + uy * ch / ph)
# 先移到窗口外再移入，确保产生移动事件序列
u.SetCursorPos(50, 50); time.sleep(0.2)
x, y = to_screen(504.0, 631.0)
u.SetCursorPos(x, y)
print("hover at", x, y, "fg=", u.GetForegroundWindow() == hwnd)
