import ctypes, sys, time

u = ctypes.windll.user32
h = int(sys.argv[1]) if len(sys.argv) > 1 else 1381794

u.ShowWindow(h, 9)          # SW_RESTORE
u.SetForegroundWindow(h)
u.BringWindowToTop(h)

time.sleep(0.3)
buf = ctypes.create_unicode_buffer(512)
u.GetWindowTextW(h, buf, 512)
fg = u.GetForegroundWindow()
print(f"target={h} title={buf.value!r} foreground={fg} match={fg == h}")
