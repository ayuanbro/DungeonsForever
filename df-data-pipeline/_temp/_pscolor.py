from PIL import Image

p = r"C:\Users\Administrator\.workbuddy\clipboard-images\clipboard-2026-10-18T07-09-22-434Z-691a85bb.png"
im = Image.open(p).convert("RGB")
w, h = im.size
print("size", w, h)

pts = [
    ("corr_top_L_col1", 150, 97),
    ("corr_top_col2L", 250, 97),
    ("corr_top_col2R", 340, 97),
    ("corr_top_col4L", 620, 97),
    ("corr_top_col4R", 700, 97),
    ("corr_top_col5R", 880, 97),
    ("v_col2_top", 297, 112),
    ("v_col2_top2", 297, 118),
    ("v_col4_top", 657, 112),
    ("v_col5_top", 845, 112),
    ("card_col2_border", 215, 160),
    ("corr_bot_col2L", 250, 400),
    ("corr_bot_col4R", 700, 400),
    ("v_col2_bot", 297, 320),
    ("v_col4_bot", 657, 320),
    ("v_col5_bot", 845, 320),
    ("v_col1_top", 120, 112),
    ("v_col1_bot", 120, 320),
]

for name, x, y in pts:
    best = None
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            xx, yy = x + dx, y + dy
            if 0 <= xx < w and 0 <= yy < h:
                c = im.getpixel((xx, yy))
                s = c[0] + c[1] + c[2]
                if best is None or s > best[0]:
                    best = (s, c, xx, yy)
    print("%-18s %s at (%d,%d)" % (name, best[1], best[2], best[3]))
