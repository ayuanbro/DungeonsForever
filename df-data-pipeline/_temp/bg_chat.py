import ctypes
import sys
import time
from ctypes import wintypes

u = ctypes.windll.user32
WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x100, 0x101, 0x102
VK_RETURN, VK_ESCAPE = 0x0D, 0x1B

def find_game(title):
    out = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
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


def press_fg(vk, ext=0):
    u.keybd_event(vk, u.MapVirtualKeyW(vk, 0), 0, 0)
    time.sleep(0.03)
    u.keybd_event(vk, u.MapVirtualKeyW(vk, 0), 2, 0)
    time.sleep(0.05)

def type_text_fg(text):
    for ch in text:
        vk = u.VkKeyScanW(ch)
        if vk == -1:
            continue
        vk = vk & 0xFF
        shift = (vk >> 8) & 1
        if shift:
            u.keybd_event(0x10, 0, 0, 0)
        press_fg(vk)
        if shift:
            u.keybd_event(0x10, 0, 2, 0)

def run_fg(hwnd, text):
    u.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    press_fg(VK_ESCAPE)
    time.sleep(0.15)
    press_fg(VK_RETURN)
    time.sleep(0.3)
    type_text_fg(text)
    time.sleep(0.15)
    press_fg(VK_RETURN)

def main():
    args = sys.argv[1:]
    open_chat = "--open" in args
    text = "".join(a for a in args if not a.startswith("--")) or "/reload"
    wins = find_game("魔兽世界")
    if not wins:
        print("ERR no game window")
        sys.exit(1)
    hwnd = wins[0]
    if "--fg" in args:
        run_fg(hwnd, text)
        print("OK fg-sent", repr(text), "hwnd", hwnd)
        return
    if open_chat:
        press(hwnd, VK_ESCAPE)
        time.sleep(0.1)
        press(hwnd, VK_RETURN)
        time.sleep(0.2)
    type_text(hwnd, text)
    time.sleep(0.1)
    press(hwnd, VK_RETURN)
    print("OK sent", repr(text), "hwnd", hwnd)

if __name__ == "__main__":
    main()
