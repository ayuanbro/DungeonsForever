# -*- coding: utf-8 -*-
"""生成「还原两处空洞安全补丁」的变异副本 _temp/_addonH（只碰副本）。"""
import hashlib
import os
import shutil

SRC = r'D:\workspace\DungeonsForever'
DST = os.path.join(SRC, '_temp', '_addonH')

shutil.rmtree(DST, ignore_errors=True)
os.makedirs(DST, exist_ok=True)
for name in os.listdir(SRC):
    if name in ('.git', '.workbuddy', '_temp'):
        continue
    s = os.path.join(SRC, name)
    d = os.path.join(DST, name)
    (shutil.copytree if os.path.isdir(s) else shutil.copy2)(s, d)

p = os.path.join(DST, 'Core', 'ProfessionUI.lua')
raw = open(p, 'rb').read()
before = hashlib.md5(raw).hexdigest()

# ── 还原补丁 1：整块删掉页面身份闸（从注释头到 `    end\r\n` 后接空行与 if PD.setOpen）──
head = ('    -- ★★ 第二道闸（2026-10-09）：').encode('utf-8')
tail = ('    end\r\n\r\n    if PD.setOpen then\r\n').encode('utf-8')
i0 = raw.index(head)
i1 = raw.index(tail, i0) + len(tail)
raw = raw[:i0] + '    if PD.setOpen then\r\n'.encode('utf-8') + raw[i1:]

# ── 还原补丁 2：两条注释 + pairs 行 → 旧 `#PD.rows` 行 ──
blk = ('    -- ★ 空洞安全（2026-10-09）：`#PD.rows` 遇空洞会提前截断 ⇒ 上一页尾部还在\r\n'
       '    --   显示中的行藏不掉。改用 pairs 扫（集合与原来逐字相同，只是不再依赖 `#`）。\r\n'
       '    for i, rr in pairs(PD.rows) do if i > n then rr:Hide() end end\r\n').encode('utf-8')
assert raw.count(blk) == 1, ('补丁2 区块命中', raw.count(blk))
raw = raw.replace(blk, '    for i = n + 1, #PD.rows do PD.rows[i]:Hide() end\r\n'.encode('utf-8'))

open(p, 'wb').write(raw)
print('变异副本:%s' % p)
print('md5 %s -> %s ; bytes -> %d' % (before, hashlib.md5(raw).hexdigest(), len(raw)))
print('残留 PD.__pageKey =', raw.count(b'PD.__pageKey'))
print('残留 pairs(PD.rows) =', raw.count(b'pairs(PD.rows)'))
