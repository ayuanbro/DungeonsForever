import math
from PIL import Image, ImageDraw, ImageFont

S = 8
CANVAS = 128 * S
cx = cy = CANVAS / 2

GOLD = (212, 172, 96, 255)
GOLD_HI = (240, 208, 138, 255)
BRONZE = (78, 52, 26, 255)
DARK = (46, 30, 14, 255)

im = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
d = ImageDraw.Draw(im)

R_OUT = 58 * S

def ring(r_out, width, color):
    d.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out],
              outline=color, width=width)

ring(R_OUT, 4 * S, DARK)
ring(R_OUT - 5 * S, 9 * S, BRONZE)
ring(R_OUT - 15 * S, 3 * S, GOLD)
ring(R_OUT - 19 * S, 2 * S, DARK)
inner = R_OUT - 24 * S
d.ellipse([cx - inner, cy - inner, cx + inner, cy + inner], fill=(36, 24, 12, 255))
d.ellipse([cx - inner + 3 * S, cy - inner + 3 * S,
           cx + inner - 3 * S, cy + inner - 3 * S], outline=BRONZE, width=2 * S)

for ang in (0, 90, 180, 270):
    a = math.radians(ang)
    kx = cx + math.cos(a) * (R_OUT - 9.5 * S)
    ky = cy + math.sin(a) * (R_OUT - 9.5 * S)
    kr = 6.5 * S
    d.ellipse([kx - kr, ky - kr, kx + kr, ky + kr], fill=BRONZE, outline=DARK, width=S)
    d.ellipse([kx - kr + 2.5 * S, ky - kr + 2.5 * S,
               kx + kr - 2.5 * S, ky + kr - 2.5 * S], fill=GOLD)

wing_r = 15 * S
wing_w = 6 * S
for side in (-1, 1):
    wx = cx + side * (R_OUT + 1 * S)
    bbox = [wx - wing_r, cy - wing_r, wx + wing_r, cy + wing_r]
    if side == -1:
        bbox = [wx - wing_r, cy - wing_r, wx + wing_r, cy + wing_r]
        d.arc([wx - wing_r, cy - wing_r, wx + wing_r, cy + wing_r],
              start=40, end=320, fill=BRONZE, width=wing_w)
    else:
        d.arc([wx - wing_r, cy - wing_r, wx + wing_r, cy + wing_r],
              start=220, end=500, fill=BRONZE, width=wing_w)

font = None
for name in ("CINZELB.TTF", "Cinzel-Bold.ttf", "GEORGIA.TTF", "TIMES.TTF", "times.ttf"):
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/" + name, 44 * S)
        break
    except OSError:
        continue
if font is None:
    font = ImageFont.load_default()

wbox = d.textbbox((0, 0), "W", font=font)
tw, th = wbox[2] - wbox[0], wbox[3] - wbox[1]
tx, ty = cx - tw / 2 - wbox[0], cy - th / 2 - wbox[1]

for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2), (2, 2), (-2, -2), (2, -2), (-2, 2)):
    d.text((tx + dx * S, ty + dy * S), "W", font=font, fill=DARK)
d.text((tx, ty - S), "W", font=font, fill=GOLD_HI)
d.text((tx, ty), "W", font=font, fill=GOLD)

final = im.resize((128, 128), Image.LANCZOS)
final.save(r"D:/workspace/DungeonsForever/_temp/MyForeverMark_preview.png")
final.save(r"D:/workspace/DungeonsForever/_temp/MyForeverMark.tga",
           format="TGA", rle=True)

chk = Image.open(r"D:/workspace/DungeonsForever/_temp/MyForeverMark.tga")
print("tga:", chk.size, chk.mode)
