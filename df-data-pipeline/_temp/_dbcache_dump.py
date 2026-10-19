# -*- coding: utf-8 -*-
"""全量解析 zhCN DBCache.bin hotfix 记录，提取含中文文本的表/ID/文本。
结构（经 lycheedev CLI 第一页交叉验证）：
  文件头 44B：magic XFTH(4) + version(4) + build(4) + sha256(32)
  记录 32B 头：magic(4) region(4) push(4) uniqueId(4) tableHash(4)
               recordId(4) payloadSize(4) status(4) pad(8) + payload
产物：_temp/_dbcache_names.json {tableHash: {recordId: [texts]}}
"""
import json
import struct
import sys

P = r'D:/Game/World of Warcraft/_classic_beta_/Cache/ADB/zhCN/DBCache.bin'
OUT = r'D:/workspace/DungeonsForever/_temp/_dbcache_names.json'


def is_zh(s):
    return any('\u4e00' <= c <= '\u9fff' for c in s)


def strings_of(blob):
    out = []
    start = None
    for i, b in enumerate(blob + b'\x00'):
        if b == 0:
            if start is not None and i - start >= 2:
                try:
                    s = blob[start:i].decode('utf-8')
                    if all(ord(c) >= 0x20 for c in s):
                        out.append(s)
                except Exception:
                    pass
            start = None
        else:
            if start is None:
                start = i
    return out


def main():
    raw = open(P, 'rb').read()
    magic, ver, build = struct.unpack_from('<4sII', raw, 0)
    assert magic == b'XFTH', magic
    n = 0
    pos = 44
    tables = {}
    while pos + 32 <= len(raw):
        m, region, push, uid, th, rid, size, status = struct.unpack_from(
            '<4sIIIIIII', raw, pos)
        if m != b'XFTH':
            print('bad magic @%d' % pos, file=sys.stderr)
            break
        payload = raw[pos + 32: pos + 32 + size]
        if len(payload) != size:
            break
        n += 1
        if size and status == 1:
            for s in strings_of(payload):
                if is_zh(s):
                    tables.setdefault(th, {}).setdefault(
                        rid, []).append(s[:120])
        pos += 32 + size
    print('records %d, zh tables %d' % (n, len(tables)))
    for th, rows in sorted(tables.items(), key=lambda kv: -len(kv[1])):
        print('  hash %-12d zh-records %5d  sample: %s'
              % (th, len(rows), json.dumps(
                  list(rows.items())[:2], ensure_ascii=False)[:150]))
    json.dump({str(k): {str(r): v for r, v in t.items()}
               for k, t in tables.items()},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('-> %s' % OUT)


if __name__ == '__main__':
    main()
