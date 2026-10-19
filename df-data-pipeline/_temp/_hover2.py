import ctypes, time, sys
from ctypes import wintypes

u = ctypes.windll.user32

# --- focus game window ---
hwnd = 112079692
u.ShowWindow(hwnd, 9)
time.sleep(0.3)
u.SetForegroundWindow(hwnd)
time.sleep(0.6)

# --- geometry ---
ox, oy = 509, 30
cw, ch = 2394, 1354
pw, ph = 2088.0437011719, 1181.5385742188
ux, uy = float(sys.argv[1]), float(sys.argv[2])
cx = ox + ux * cw / pw
cy = oy + uy * ch / ph

# --- absolute SendInput with virtual-desktop normalization ---
SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN = 76, 77
SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 78, 79
vx = u.GetSystemMetrics(SM_XVIRTUALSCREEN)
vy = u.GetSystemMetrics(SM_YVIRTUALSCREEN)
vw = u.GetSystemMetrics(SM_CXVIRTUALSCREEN)
vh = u.GetSystemMetrics(SM_CYVIRTUALSCREEN)
nx = int((cx - vx) * 65535 / (vw - 1))
ny = int((cy - vy) * 65535 / (vh - 1))

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]

class INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _anonymous_ = ("i",)
    _fields_ = [("type", wintypes.DWORD), ("i", _I)]

def move(dx, dy):
    inp = INPUT()
    inp.type = 0
    inp.mi.dx = dx
    inp.mi.dy = dy
    inp.mi.mouseData = 0
    inp.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
    inp.mi.time = 0
    inp.mi.dwExtraInfo = None
    u.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

# 先移到远处，再分步逼近目标（产生连续 move 事件）
move(int((100 - vx) * 65535 / (vw - 1)), int((100 - vy) * 65535 / (vh - 1)))
time.sleep(0.25)
for k in range(1, 9):
    px = int((100 + (cx - 100) * k / 8 - vx) * 65535 / (vw - 1))
    py = int((100 + (cy - 100) * k / 8 - vy) * 65535 / (vh - 1))
    move(px, py)
    time.sleep(0.06)

p = wintypes.POINT()
u.GetCursorPos(ctypes.byref(p))
print(f"target client=({cx:.0f},{cy:.0f}) cursor=({p.x},{p.y}) fg={u.GetForegroundWindow()==hwnd}")
