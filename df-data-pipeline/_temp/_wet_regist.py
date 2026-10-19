# -*- coding: utf-8 -*-
"""把「挖掘场湿地」游戏内截图与自制 TGA 素材做配准，解出画布在截图中的矩形。

做法：把素材当模板，在截图上做归一化互相关（FFT 实现），返回
(left, top, width, height) —— 即游戏里那块 663×442 画布在截图里的位置。
先用合成数据自检（把模板贴进随机画布，看能否找回偏移），再跑真图。
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SHOT = r'C:\Users\Administrator\.workbuddy\clipboard-images\clipboard-2026-10-02T21-53-47-280Z-91743acf.jpg'
TGA = os.path.join(HERE, '..', 'Media', 'Maps', 'ExcavationSite.tga')


def load(ds=4):
    shot = np.asarray(Image.open(SHOT).convert('L')).astype(np.float64)
    ref = np.asarray(Image.open(TGA).convert('L')).astype(np.float64)[:341, :]
    # 分块均值降采样（比直接切片抗噪）
    def block(a, k):
        h, w = a.shape
        h2, w2 = h // k * k, w // k * k
        return a[:h2, :w2].reshape(h2 // k, k, w2 // k, k).mean(axis=(1, 3))
    return block(shot, ds), ref


def zncc(s, t):
    """t 在 s 上滑动，返回 (最好 ZNCC, top-left x, top-left y)；t 会被零均值单位化。"""
    Hs, Ws = s.shape
    mh, mw = t.shape
    if mh > Hs or mw > Ws:
        return None
    t = t - t.mean()
    nrm = np.sqrt((t * t).sum())
    if nrm < 1e-9:
        return None
    t = t / nrm
    fh, fw = Hs + mh - 1, Ws + mw - 1
    F = np.fft.rfft2(s, s=(fh, fw))
    G = np.fft.rfft2(t[::-1, ::-1], s=(fh, fw))
    cc = np.fft.irfft2(F * G, s=(fh, fw))
    # 卷积后 [mh-1, mw-1] 起才是有效相关（lag 0..）
    valid = cc[mh - 1:Hs, mw - 1:Ws]
    hh, ww = valid.shape
    i = np.arange(hh)[:, None]
    j = np.arange(ww)[None, :]
    p1 = np.pad(s, ((1, 0), (1, 0)))
    p2 = np.pad(s * s, ((1, 0), (1, 0)))
    S1 = p1.cumsum(0).cumsum(1)
    S2 = p2.cumsum(0).cumsum(1)
    wsum = S1[i + mh, j + mw] - S1[i, j + mw] - S1[i + mh, j] + S1[i, j]
    wsq = S2[i + mh, j + mw] - S2[i, j + mw] - S2[i + mh, j] + S2[i, j]
    N = float(mh * mw)
    var = np.maximum(wsq / N - (wsum / N) ** 2, 1e-6)
    # t 已是零均值单位范数 ⇒ Σt·s = N·cov/σ_s，完美匹配时 z → 1
    z = valid / (np.sqrt(N) * np.sqrt(var))
    k = np.unravel_index(int(np.argmax(z)), z.shape)
    return float(z[k]), int(k[1]), int(k[0])


def selftest(ds):
    """合成自检：模板贴到已知位置，验证能否找回。"""
    rng = np.random.default_rng(7)
    shot_s, ref = load(ds)
    mw, mh = 120, 80
    t = np.asarray(Image.fromarray(ref.astype(np.uint8)).resize((mw * ds, mh * ds), Image.LANCZOS)
                   .resize((mw, mh), Image.LANCZOS)).astype(np.float64)
    canvas = rng.normal(90, 25, (260, 340))
    ox, oy = 137, 61
    canvas[oy:oy + mh, ox:ox + mw] = t * 0.9 + 12
    sc, x, y = zncc(canvas, t)
    print('  自检: 期望 (%d,%d) 实测 (%d,%d) score=%.3f -> %s' %
          (ox, oy, x, y, sc, 'OK' if (x, y) == (ox, oy) else 'FAIL'))
    return (x, y) == (ox, oy)


def main():
    ds = 4
    shot, ref = load(ds)
    print('降采样后 shot=%s ref=%s' % (shot.shape[::-1], ref.shape[::-1]))
    if not selftest(ds):
        print('自检未通过，终止'); return
    refimg = Image.fromarray(ref.astype(np.uint8))
    best = None
    for Wc in range(1090, 1290, 8):
        for Hc in range(700, 890, 8):
            mw, mh = int(round(Wc / ds)), int(round(Hc / ds))
            t = np.asarray(refimg.resize((mw, mh), Image.LANCZOS)).astype(np.float64)
            r = zncc(shot, t)
            if r and (best is None or r[0] > best[0]):
                best = (r[0], Wc, Hc, r[1], r[2])
    print('粗：score=%.4f W=%d H=%d left=%d top=%d' % (
        best[0], best[1], best[2], best[3] * ds, best[4] * ds))
    s0, W0, H0, x0, y0 = best
    # 二级：在粗解附近逐像素扫（ds=4 下 1 格 = 4px）
    for Wc in range(W0 - 8, W0 + 9):
        for Hc in range(H0 - 8, H0 + 9):
            mw, mh = int(round(Wc / ds)), int(round(Hc / ds))
            t = np.asarray(refimg.resize((mw, mh), Image.LANCZOS)).astype(np.float64)
            r = zncc(shot, t)
            if r and r[0] > s0:
                s0, W0, H0, x0, y0 = r[0], Wc, Hc, r[1], r[2]
    print('二级：score=%.4f W=%d H=%d left=%d top=%d' % (s0, W0, H0, x0 * ds, y0 * ds))
    # 三级：原分辨率，窄窗精修（±10px），模板按原图大小重采样
    shot1 = np.asarray(Image.open(SHOT).convert('L')).astype(np.float64)
    ref1 = np.asarray(Image.open(TGA).convert('L')).astype(np.float64)[:341, :]
    refimg1 = Image.fromarray(ref1.astype(np.uint8))
    best3 = (s0, W0, H0, x0 * ds, y0 * ds)
    for Wc in range(W0 - 10, W0 + 11, 2):
        for Hc in range(H0 - 10, H0 + 11, 2):
            t = np.asarray(refimg1.resize((Wc, Hc), Image.LANCZOS)).astype(np.float64)
            # 只在粗解邻域里找：把大图裁一块再相关
            y1, x1 = best3[4], best3[3]
            pad = 24
            y0c = max(0, y1 - pad); x0c = max(0, x1 - pad)
            sub = shot1[y0c:y1 + Hc + pad, x0c:x1 + Wc + pad]
            r = zncc(sub, t)
            if r and r[0] > best3[0]:
                best3 = (r[0], Wc, Hc, x0c + r[1], y0c + r[2])
    s3, W3, H3, L3, T3 = best3
    print('精：score=%.4f  left=%d top=%d w=%d h=%d  W/H=%.4f (素材 512/341=%.4f)'
          % (s3, L3, T3, W3, H3, W3 / H3, 512 / 341))
    np.save(os.path.join(HERE, '_regist.npy'), np.array([L3, T3, W3, H3], dtype=float))
    print('saved _regist.npy', [L3, T3, W3, H3])


if __name__ == '__main__':
    main()
