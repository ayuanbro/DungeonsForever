"""生成「设置」自绘图标 (方案 A 六边形圆环) -> Media/textures/DF_Settings.tga

口径：透明底 + 纯白形状，运行期靠 SetVertexColor 染色。
用法： python _temp/_gen_settings_icon.py
"""
import math
import os
from PIL import Image, ImageDraw, ImageFont

# ---- 形状参数（改这里即可调形，改完重跑本脚本） ---------------------------
R_OUT = 9.0      # 外六边形外接圆半径（viewBox 24 坐标系，中心 12,12）
R_IN = 3.15      # 内圆环半径
W_OUT = 2.25     # 外六边形描边宽
W_IN = 2.15      # 内圆环描边宽
SS = 8           # 超采样倍率
SIZE = 64        # 输出边长
# ------------------------------------------------------------------------

VB = 24.0
K = (SIZE * SS) / VB
CX = CY = VB / 2.0


def hex_points(r):
    """尖朝左右、上下为平边的正六边形（与参考图一致）。"""
    return [(CX + r * math.cos(math.radians(a)), CY + r * math.sin(math.radians(a)))
            for a in range(0, 360, 60)]


def build():
    big = SIZE * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)

    outer = [(x * K, y * K) for x, y in hex_points(R_OUT)]
    ow = W_OUT * K
    d.line(outer + [outer[0]], fill=white, width=int(round(ow)), joint="curve")
    for x, y in outer:                       # 顶点补圆，保证圆角接头干净
        rr = ow / 2.0
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=white)

    ri = R_IN * K
    iw = W_IN * K
    d.ellipse([CX * K - ri, CY * K - ri, CX * K + ri, CY * K + ri],
              outline=white, width=int(round(iw)))

    return img.resize((SIZE, SIZE), Image.LANCZOS)


def tint(img, rgb):
    out = img.copy()
    px = out.load()
    r, g, b = rgb
    for y in range(out.height):
        for x in range(out.width):
            _, _, _, a = px[x, y]
            px[x, y] = (int(r * 255), int(g * 255), int(b * 255), a)
    return out


def _font(size):
    for name in ("segoeui.ttf", "arial.ttf", "tahoma.ttf"):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def preview(icon, path):
    """四段对照：真机 1:1 / 14px 放大 / 24px 放大 / 64px 原图染色。"""
    GRAY = (0.55, 0.62, 0.70)
    WHITE = (1.0, 1.0, 1.0)
    GOLD = (1.0, 0.82, 0.0)
    BG = (0x1F, 0x1F, 0x23)
    W, H = 760, 230
    sheet = Image.new("RGB", (W, H), BG)
    sd = ImageDraw.Draw(sheet)
    label = (0x8C, 0x9E, 0xB3)
    f = _font(15)

    sd.text((20, 12), "A  actual size: 14 / 16 / 18 / 24 px", fill=label, font=f)
    x = 20
    for size, col in ((14, GRAY), (16, GRAY), (18, WHITE), (24, WHITE)):
        im = tint(icon.resize((size, size), Image.LANCZOS), col)
        sheet.paste(im, (x, 40), im)
        x += size + 16

    sd.text((20, 100), "B  14px x8", fill=label, font=f)
    im = tint(icon.resize((14, 14), Image.LANCZOS), GRAY).resize((112, 112), Image.NEAREST)
    sheet.paste(im, (20, 126), im)

    sd.text((170, 100), "C  24px x5", fill=label, font=f)
    im = tint(icon.resize((24, 24), Image.LANCZOS), WHITE).resize((120, 120), Image.NEAREST)
    sheet.paste(im, (170, 126), im)

    sd.text((330, 100), "D  64px source x2  (idle / hover / active)", fill=label, font=f)
    x = 330
    for col in (GRAY, WHITE, GOLD):
        im = tint(icon, col).resize((128, 128), Image.LANCZOS)
        sheet.paste(im, (x, 126), im)
        x += 138

    sheet.save(path)


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icon = build()
    tga = os.path.join(root, "Media", "textures", "DF_Settings.tga")
    icon.save(tga, format="TGA")
    png = os.path.join(root, "_temp", "_settings_icon_preview.png")
    preview(icon, png)
    print("TGA :", tga, os.path.getsize(tga), "bytes")
    print("PREV:", png)
