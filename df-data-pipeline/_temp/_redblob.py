import sys
from PIL import Image

src = sys.argv[1]
im = Image.open(src).convert("RGB")
px = im.load()
W, H = im.size
seen = set()
blobs = []
for y in range(H):
    for x in range(W):
        if (x, y) in seen:
            continue
        r, g, b = px[x, y]
        if not (r > 150 and g < 90 and b < 90):
            continue
        stack = [(x, y)]
        seen.add((x, y))
        pts = []
        while stack:
            cx, cy = stack.pop()
            pts.append((cx, cy))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if nx < 0 or ny < 0 or nx >= W or ny >= H or (nx, ny) in seen:
                    continue
                rr, gg, bb = px[nx, ny]
                if rr > 150 and gg < 90 and bb < 90:
                    seen.add((nx, ny))
                    stack.append((nx, ny))
        if len(pts) > 80:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            blobs.append((min(xs), min(ys), max(xs), max(ys), len(pts)))
blobs.sort(key=lambda t: (t[1], t[0]))
for bb in blobs:
    print("cx=%d cy=%d w=%d h=%d n=%d" % ((bb[0] + bb[2]) // 2, (bb[1] + bb[3]) // 2, bb[2] - bb[0] + 1, bb[3] - bb[1] + 1, bb[4]))
