# -*- coding: utf-8 -*-
"""WDB 记录结构对齐试探"""
import struct, sys

p = (r"D:/Game/World of Warcraft/_classic_beta_/Cache/WDB/zhCN"
     r"/creaturecache.wdb")
raw = open(p, 'rb').read()
print("file %d bytes, header: magic %s build %d rec_size %d ver %d cv %d"
      % (len(raw), raw[:4], struct.unpack_from("<I", raw, 4)[0],
         struct.unpack_from("<I", raw, 12)[0],
         struct.unpack_from("<I", raw, 16)[0],
         struct.unpack_from("<I", raw, 20)[0]))

# 假设 A：从 off 起 [id u32][size u32][data size bytes] 内联
def try_inline(off):
    pos = off
    ids = []
    while pos + 8 <= len(raw):
        rid, rsize = struct.unpack_from("<II", raw, pos)
        if rsize > 4096 or pos + 8 + rsize > len(raw):
            return pos, ids, "size overflow at rec %d" % len(ids)
        ids.append((rid, rsize))
        pos += 8 + rsize
        if len(ids) > 20000:
            break
    return pos, ids, "eof %d left=%d" % (pos, len(raw) - pos)

for off in (0x14, 0x18, 0x1C, 0x20):
    end, ids, msg = try_inline(off)
    print("inline@0x%x: %d records, end=%s (%s), first5=%s"
          % (off, len(ids), hex(end), msg, ids[:5]))
