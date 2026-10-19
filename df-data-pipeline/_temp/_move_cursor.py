import ctypes, sys, time
u = ctypes.windll.user32
# 游戏窗口客户区原点 (509,30)，客户区物理尺寸 2394x1354
# 行目标：UI px (327.6, 357.9)，effscale 0.65 => 客户区物理 = UI * 1.0? 
# 客户区物理宽 2394 与 UI 2088.04 之比 = 1.1463 => 物理 = UI/0.65/... 直接反算：
# UI 坐标体系宽 2088.04 映射到客户区 2394 物理像素 => 比例 2394/2088.04 = 1.1465
ux, uy = float(sys.argv[1]), float(sys.argv[2])
ox, oy = 509, 30
cw, ch = 2394, 1354
pw, ph = 2088.0437011719, 1181.5385742188
px = int(ox + ux * cw / pw)
py = int(oy + uy * ch / ph)
print(f"move to client phys ({px},{py}) from ui ({ux},{uy})")
u.SetCursorPos(px, py)
