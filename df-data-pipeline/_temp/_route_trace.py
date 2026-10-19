# -*- coding: utf-8 -*-
"""从参考截图自动描出哀嚎洞穴三条路线（青/黄/红）→ 显示空间百分比折线。

底图空间 = 用户自制图（1002x668，与钉点空间恒等）。参考截图 (980x653) 与
显示空间的仿射关系由 ORB 特征匹配解得：beta = M @ ref，M≈[[1.026,0],[-.43],[1.026,-1.44]]。
流程：HSV 邻域色掩膜（排除标注文字/横幅/说明框 bbox）→ 连通域去噪 →
Zhang-Suen 细化 → 端点链式走线 → RDP 简化 → 仿射变换 → 百分比。
"""
import numpy as np, cv2, json, io, sys
sys.setrecursionlimit(100000)

REF = r'C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-10-10T05-38-38-244Z-cf0e86f8.jpg'
R = cv2.cvtColor(cv2.imread(REF), cv2.COLOR_BGR2RGB).astype(int)
Hh, Ww = R.shape[:2]

def excl(mask, boxes):
    for x0, y0, x1, y1 in boxes:
        mask[y0:y1, x0:x1] = False
    return mask

EX_ALL = [
    (420, 5, 930, 80),     # 横幅（含底部描边）
    (60, 90, 180, 125),    # PIT OF FANCS
    (430, 175, 530, 215),  # SCREAMING GULLY
    (740, 110, 850, 145),  # WINDING CHASM
    (620, 458, 768, 505),  # CRAG OF THE EVERLIVING
    (0, 495, 520, 630),    # 底部说明框
    (195, 28, 320, 62),    # DREAMER'S ROCK
    (830, 12, 930, 52),    # 横幅右端
    (100, 285, 190, 315),  # Jump Down 文字
    (480, 228, 585, 272),  # Jump Down / Head back to Start 文字
    (565, 420, 660, 452),  # Jump Over 文字
    (380, 285, 445, 350),  # 入口绿色漩涡
    (448, 292, 522, 428),  # 瀑布高光
    (175, 3, 250, 45),     # NARALEX EVENT 指示束
    (190, 133, 288, 182),  # KRESH 指示束
    (790, 108, 920, 148),  # PYTHAS 指示束
    (528, 136, 695, 163),  # Faerie Dragon 文字
    (552, 236, 628, 263),  # VERDAN 文字
    (845, 483, 922, 522),  # SKUM 文字
    (188, 270, 277, 320),  # ANACONDRA 文字
    (148, 350, 272, 394),  # COBRAHN 文字
]

def mask_cyan():
    m = (R[:,:,2] - R[:,:,0] > 18) & (R[:,:,1] - R[:,:,0] > 8) & (R[:,:,1] > 80)
    return excl(m, EX_ALL)

def mask_yellow():
    r, g, b = R[:,:,0], R[:,:,1], R[:,:,2]
    s = (R.max(2) - R.min(2)) * 255 // np.maximum(R.max(2), 1)
    V = R.max(2)
    m = (r > 160) & (r - b > 55) & (g - b > 40) & (s > 118) & (V > 185)
    return excl(m, EX_ALL)

def mask_red():
    r, g, b = R[:,:,0], R[:,:,1], R[:,:,2]
    m = (r > 105) & (r - g > 45) & (r - b > 40) & (g < 115)
    return excl(m, EX_ALL)

def thinning(img):
    """Zhang-Suen 细化。"""
    img = (img > 0).astype(np.uint8)
    P = lambda a: a
    changed = True
    def nb(I):
        p = np.pad(I, 1)
        return [p[0:-2,0:-2], p[0:-2,1:-1], p[0:-2,2:], p[1:-1,2:],
                p[2:,2:], p[2:,1:-1], p[2:,0:-2], p[1:-1,0:-2]]
    while changed:
        changed = False
        for step in (0, 1):
            n = nb(img)
            B = sum(n)
            seq = [n[0], n[1], n[2], n[3], n[4], n[5], n[6], n[7], n[0]]
            A = sum(((seq[i] == 0) & (seq[i+1] == 1)).astype(np.uint8) for i in range(8))
            if step == 0:
                cond = (img == 1) & (B >= 2) & (B <= 6) & (A == 1) & \
                       ((n[0]*n[2]*n[4] == 0) & (n[2]*n[4]*n[6] == 0))
            else:
                cond = (img == 1) & (B >= 2) & (B <= 6) & (A == 1) & \
                       ((n[0]*n[2]*n[6] == 0) & (n[0]*n[4]*n[6] == 0))
            if cond.any():
                img[cond] = 0
                changed = True
    return img

def chains_from_skel(skel):
    """骨架 → 折线链列表（像素坐标 (x,y)）。"""
    ys, xs = np.nonzero(skel)
    pts = set(zip(xs.tolist(), ys.tolist()))
    def nbrs(p):
        x, y = p
        return [q for q in ((x+1,y),(x-1,y),(x,y+1),(x,y-1),(x+1,y+1),(x-1,y-1),(x+1,y-1),(x-1,y+1)) if q in pts]
    deg = {p: len(nbrs(p)) for p in pts}
    used = set()
    chains = []
    def walk(start, first):
        chain = [start, first]
        used.add(start); used.add(first)
        cur = first
        while True:
            nxt = [q for q in nbrs(cur) if q not in used]
            if not nxt:
                break
            # 优先延续直线方向
            if len(chain) >= 2:
                dx, dy = chain[-1][0]-chain[-2][0], chain[-1][1]-chain[-2][1]
                nxt.sort(key=lambda q: -((q[0]-cur[0])*dx + (q[1]-cur[1])*dy))
            cur = nxt[0]
            used.add(cur)
            chain.append(cur)
        return chain
    # 先从端点（度=1）出发
    ends = sorted([p for p in pts if deg[p] == 1])
    for e in ends:
        if e in used: continue
        for q in nbrs(e):
            if q not in used:
                chains.append(walk(e, q))
                break
    # 剩余（纯环）随便选起点
    for p in sorted(pts):
        if p not in used:
            q2 = nbrs(p)
            if q2:
                chains.append(walk(p, q2[0]))
    # 端点距离 <=6px 的链拼接
    def ep(c): return (c[0], c[-1])
    merged = True
    while merged:
        merged = False
        for i in range(len(chains)):
            for j in range(i+1, len(chains)):
                for a in ep(chains[i]):
                    for b in ep(chains[j]):
                        if (a[0]-b[0])**2 + (a[1]-b[1])**2 <= 196:
                            ca, cb = chains[i], chains[j]
                            if a == ca[-1]: ca = ca[::-1]
                            if b == cb[0]: cb = cb[::-1]
                            chains[i] = ca + cb
                            chains.pop(j)
                            merged = True
                            break
                    if merged: break
                if merged: break
            if merged: break
    return chains

def rdp(pts, eps):
    if len(pts) < 3: return pts
    pts = np.array(pts, float)
    def _r(i, j, keep):
        if j <= i + 1: return
        a, b = pts[i], pts[j]
        ab = b - a
        L = np.hypot(*ab) or 1e-9
        d = np.abs(ab[0]*(pts[i+1:j, 1] - a[1]) - ab[1]*(pts[i+1:j, 0] - a[0])) / L
        k = int(np.argmax(d))
        if d[k] > eps:
            keep.add(i+1+k)
            _r(i, i+1+k, keep); _r(i+1+k, j, keep)
    keep = {0, len(pts)-1}
    _r(0, len(pts)-1, keep)
    return [pts[k] for k in sorted(keep)]

def minmax_area(chains, min_len=40):
    return [c for c in chains if sum(np.hypot(c[i+1][0]-c[i][0], c[i+1][1]-c[i][1]) for i in range(len(c)-1)) >= min_len]

# 参考图 → 显示空间
SC, TX, TY = 1.026, -0.4275, -1.4376
def to_disp(px, py):
    return (SC*px + TX, SC*py + TY)

out = {}
for name, fn in (('cyan', mask_cyan), ('yellow', mask_yellow), ('red', mask_red)):
    m = fn()
    n0 = int(m.sum())
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE,
                         np.ones((3, 3), np.uint8), iterations=2)
    nlab, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    for i in range(1, nlab):
        if stats[i, cv2.CC_STAT_AREA] < 90:
            m[lab == i] = False
    skel = thinning(m > 0)
    chs = chains_from_skel(skel)
    chs = minmax_area(chs)
    polys = []
    for c in chs:
        simp = rdp([(float(x), float(y)) for x, y in c], 2.0)
        pts = []
        for x, y in simp:
            X, Y = to_disp(x + 0.5, y + 0.5)
            pts.append([round(X / 1002 * 100, 2), round(Y / 668 * 100, 2)])
        polys.append(pts)
    out[name] = polys
    print('%s: mask %d → 链 %d 条，点数 %s' % (name, n0, len(polys), [len(p) for p in polys]))

with io.open('_temp/_wc_routes_raw.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('saved _temp/_wc_routes_raw.json')
