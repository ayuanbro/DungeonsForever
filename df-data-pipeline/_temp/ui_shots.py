import ctypes, os, sys, time
from ctypes import wintypes
from PIL import ImageGrab

u = ctypes.windll.user32
WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x100, 0x101, 0x102
VK_RETURN, VK_ESCAPE = 0x0D, 0x1B

def find_game():
    out = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        if u.IsWindowVisible(h):
            n = u.GetWindowTextLengthW(h)
            b = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, b, n + 1)
            if b.value == "魔兽世界":
                out.append(h)
        return True
    u.EnumWindows(cb, 0)
    return out

def press(hwnd, vk):
    scan = u.MapVirtualKeyW(vk, 0)
    lp = 1 | (scan << 16)
    u.PostMessageW(hwnd, WM_KEYDOWN, vk, lp)
    time.sleep(0.05)
    u.PostMessageW(hwnd, WM_KEYUP, vk, lp | 0xC0000000)
    time.sleep(0.05)

def type_text(hwnd, text):
    for ch in text:
        u.PostMessageW(hwnd, WM_CHAR, ord(ch), 1)
        time.sleep(0.03)

def send_command(hwnd, text):
    press(hwnd, VK_RETURN)
    time.sleep(0.25)
    type_text(hwnd, text)
    time.sleep(0.1)
    press(hwnd, VK_RETURN)
    time.sleep(0.3)

def focus(hwnd):
    u.ShowWindow(hwnd, 9)
    try:
        fg = u.GetForegroundWindow()
        tf = u.GetWindowThreadProcessId(fg, None)
        tm = ctypes.windll.kernel32.GetCurrentThreadId()
        u.AttachThreadInput(tm, tf, True)
        u.AttachThreadInput(tm, u.GetWindowThreadProcessId(hwnd, None), True)
        u.BringWindowToTop(hwnd)
        u.SetForegroundWindow(hwnd)
        u.AttachThreadInput(tm, tf, False)
        u.AttachThreadInput(tm, u.GetWindowThreadProcessId(hwnd, None), False)
    except Exception:
        pass
    time.sleep(0.6)
    return u.GetForegroundWindow() == hwnd

def ensure_focus(hwnd, tries=6):
    for i in range(tries):
        if u.GetForegroundWindow() == hwnd:
            return True
        focus(hwnd)
        time.sleep(1.0)
    return u.GetForegroundWindow() == hwnd

def shot(hwnd, path):
    r = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
    img.save(path)
    g = img.convert("L")
    extrema = g.getextrema()
    return img.size, extrema

OUT = r"C:\Users\Administrator\Desktop\无限副本手册\1.8.0"
os.makedirs(OUT, exist_ok=True)

wins = find_game()
if not wins:
    print("ERR no game window")
    sys.exit(1)
hwnd = wins[0]
print("hwnd", hwnd, "focused", focus(hwnd))

STEPS = [
    ("/df fb", 4.0, "01_副本"),
    ("/df tb", 3.0, "02_团本"),
    ("/df zy /run _G.DF_NS.ProfModule.Show(\"alchemy\")", 6.0, "03_专业_总览"),
    ("/df zy /run _G.DF_NS.ProfModule.Show(\"alchemy\") _G.DF_NS.ProfModule.SetTab(\"trainer\")", 3.0, "04_专业_训练师"),
    ("/df zy /run _G.DF_NS.ProfModule.Show(\"alchemy\") _G.DF_NS.ProfModule.SetTab(\"recipe\")", 3.0, "05_专业_配方"),
    ("/df zy /run _G.DF_NS.ProfModule.Show(\"herbalism\") _G.DF_NS.ProfModule.SetTab(\"gather\")", 3.0, "06_专业_采集"),
    ("/df zy /run _G.DF_NS.ProfModule.Show(\"alchemy\") _G.DF_NS.ProfModule.SetTab(\"leveling\")", 3.0, "07_专业_升级"),
    ("/df zy /run _G.DF_NS.ProfModule.Show(\"crates\")", 3.0, "08_专业_板条箱"),
    ("/df zy /run _G.DF_NS.ProfModule.Show(\"crates\") _G.DF_NS.ProfModule.SetTab(\"writ\")", 3.0, "09_专业_工匠文书"),
    ("/df ts", 3.0, "10_探索"),
    ("/df hp", 3.0, "11_收藏"),
    ("/df wm", 3.0, "12_声望"),
    ("/df bis", 3.0, "13_BIS"),
    ("/df zn", 3.0, "14_职业指南"),
    ("/run _G.DF_NS.OpenPage(\"PvP\")", 3.0, "15_PvP"),
    ("/run _G.DF_NS.OpenPage(\"Gear\")", 6.0, "16_装备库"),
]

results = []
only = set(sys.argv[1:])
for cmd, wait, name in STEPS:
    if only and name not in only:
        continue
    for part in cmd.split(" /"):
        part = part if part.startswith("/") else "/" + part
        send_command(hwnd, part)
        time.sleep(0.2)
    time.sleep(wait)
    if not ensure_focus(hwnd):
        print("SKIP", name, "game window not foreground")
        results.append((name, False, (0, 0)))
        continue
    p = os.path.join(OUT, name + ".png")
    size, ext = shot(hwnd, p)
    ok = ext[0] != ext[1]
    results.append((name, ok, ext))
    print("SHOT", name, "size", size, "range", ext, "OK" if ok else "SUSPECT-BLANK")
    time.sleep(0.5)

bad = [n for n, ok, e in results if not ok]
print("DONE total", len(results), "blank", len(bad), bad)
