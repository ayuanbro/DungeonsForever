# -*- coding: utf-8 -*-
import numpy as np

pairs = [
    ('Ghamoo', (32.9, 60.2), (33.01, 60.68)),
    ('Sarevess', (10.1, 36.0), (11.19, 39.42)),
    ('Gelihast', (52.3, 55.1), (54.50, 56.92)),
    ('Aquanis', (41.5, 75.4), (39.91, 75.07)),
    ('Kelris', (51.9, 81.6), (52.45, 78.01)),
    ('Akumai', (85.6, 86.6), (85.93, 86.50)),
    ('Serrakis', (60.6, 31.2), (58.81, 30.77)),
]

A = []
bx = []
by = []
for _, ours, theirs in pairs:
    A.append([theirs[0], theirs[1], 1.0])
    bx.append(ours[0])
    by.append(ours[1])
A = np.array(A)
cx, rx, _, _ = np.linalg.lstsq(A, np.array(bx), rcond=None)
cy, ry, _, _ = np.linalg.lstsq(A, np.array(by), rcond=None)
print('x: %.4f*X + %.4f*Y + %.3f' % tuple(cx))
print('y: %.4f*X + %.4f*Y + %.3f' % tuple(cy))
for name, ours, theirs in pairs:
    px = cx[0] * theirs[0] + cx[1] * theirs[1] + cx[2]
    py = cy[0] * theirs[0] + cy[1] * theirs[1] + cy[2]
    print('%-9s ours(%.1f,%.1f) pred(%.1f,%.1f) err(%.2f,%.2f)' % (
        name, ours[0], ours[1], px, py, px - ours[0], py - ours[1]))
