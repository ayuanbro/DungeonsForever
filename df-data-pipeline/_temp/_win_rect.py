import ctypes
from ctypes import wintypes

u = ctypes.windll.user32

EnumWindows = u.EnumWindows
EnumWindows.restype = wintypes.BOOL
CB = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

found = []
def cb(h, l):
    if u.IsWindowVisible(h):
        n = u.GetWindowTextLengthW(h)
        b = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(h, b, n + 1)
        if b.value == "魔兽世界":
            found.append(h)
    return True
EnumWindows(CB(cb), 0)
print("hwnds", found)
for h in found:
    r = wintypes.RECT()
    u.GetClientRect(h, ctypes.byref(r))
    pt = wintypes.POINT(0, 0)
    u.ClientToScreen(h, ctypes.byref(pt))
    print("hwnd", h, "client", r.left, r.top, r.right, r.bottom,
          "w", r.right - r.left, "h", r.bottom - r.top,
          "origin", pt.x, pt.y)
