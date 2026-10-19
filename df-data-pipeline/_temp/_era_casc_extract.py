# -*- coding: utf-8 -*-
"""本地 CASC 最小提取器（wow_classic_era 1.15.9）——提取 zhCN 哀嚎洞穴地图瓦片。

链路：idx → BLTE(encoding) → encoding 查 root CKey → BLTE(root) → FDID+locale → CKey
     → encoding 查 EKey → idx → archive → BLTE(BLP) → PNG。
格式规范对齐 wow.export（casc-source.js / casc-source-local.js / blte-reader.js）。
"""
import io, os, re, sys, struct, zlib

ROOT = r"D:/Game/World of Warcraft"
IDX_DIR = os.path.join(ROOT, "Data", "wow_classic_era")
DATA_DIR = os.path.join(ROOT, "Data", "data")
BUILD_KEY = "2417084b8b041ee120d02d4adf31b0bc"
ROOT_CKEY = "1a2996789c9154c28673b668381cb61f"
ENC_EKEYS = ["940628f67d84c761239ce75eb2814ab5", "ebd50ad019467814eb7b3ceb9c929656"]

FDIDS = {1: 448454, 2: 448458, 3: 448459, 4: 448460, 5: 448461, 6: 448462,
         7: 448463, 8: 448464, 9: 448465, 10: 448455, 11: 448456, 12: 448457}
LOCALE_ZHCN, LOCALE_ENUS = 0x40, 0x2
ROOT_MAGIC, ENC_MAGIC = 0x4D465354, 0x4E45
NO_NAME_HASH = 0x10000000


def load_indexes():
    """EKey 前 9 字节 hex → {index, offset, size}"""
    entries = {}
    for fn in os.listdir(IDX_DIR):
        if not fn.endswith(".idx"):
            continue
        b = open(os.path.join(IDX_DIR, fn), "rb").read()
        hhs = struct.unpack_from("<i", b, 0)[0]
        pos = (8 + hhs + 0x0F) & ~0x0F
        data_len = struct.unpack_from("<i", b, pos)[0]
        pos += 8
        for _ in range(data_len // 18):
            key = b[pos:pos + 9].hex()
            idx_high = b[pos + 9]
            idx_low = struct.unpack_from(">I", b, pos + 10)[0]
            size = struct.unpack_from("<i", b, pos + 14)[0]
            pos += 18
            if key not in entries:
                entries[key] = {"index": (idx_high << 2) | (idx_low >> 30),
                                "offset": idx_low & 0x3FFFFFFF, "size": size}
    return entries


IDX = load_indexes()
print("idx 条目:", len(IDX))


def read_blte(ekey):
    e = IDX.get(ekey[:18])
    if e is None:
        raise KeyError("EKey 不在本地 idx: " + ekey)
    arc = os.path.join(DATA_DIR, "%08x.archive" % e["index"])
    with open(arc, "rb") as f:
        f.seek(e["offset"])
        raw = f.read(e["size"])
    return blte_decode(raw)


def blte_decode(raw):
    assert raw[:4] == b"BLTE", "非 BLTE: " + raw[:4].hex()
    header_size = struct.unpack_from(">i", raw, 4)[0]
    frames = []
    if header_size == 0:
        frames.append((raw[8], raw[9:]))
    else:
        fc = raw[4:8]
        assert fc[0] == 0x0F, "帧表格式异常"
        n = fc[1] << 16 | fc[2] << 8 | fc[3]
        assert header_size == 24 * n + 12, "帧表大小不自洽"
        data_start = header_size
        for i in range(n):
            base = 8 + 24 * i
            comp = struct.unpack_from(">i", raw, base)[0]
            dec = struct.unpack_from(">i", raw, base + 4)[0]
            chunk = raw[data_start:data_start + comp]
            data_start += comp
            frames.append((chunk[0], chunk[1:]))
    out = b""
    for typ, payload in frames:
        if typ == 0x4E:      # N
            out += payload
        elif typ == 0x5A:    # Z
            out += zlib.decompress(payload)
        elif typ == 0x45:    # E 加密
            raise RuntimeError("BLTE E 帧（需要 tact key）")
        elif typ == 0x46:    # F 递归帧
            raise RuntimeError("BLTE F 帧（未实现）")
        else:
            raise RuntimeError("未知帧类型 0x%02x" % typ)
    return out


def parse_encoding(buf):
    """CKey hex → EKey hex（含长度）"""
    magic, = struct.unpack_from("<H", buf, 0)
    assert magic == ENC_MAGIC, "encoding magic 异常"
    hsz_c, hsz_e = buf[5], buf[6]
    cpage_kb, = struct.unpack_from(">h", buf, 7)
    cpage = cpage_kb * 1024
    cpage_count, = struct.unpack_from(">i", buf, 11)
    spec_size, = struct.unpack_from(">i", buf, 19)
    pos = 23 + spec_size + cpage_count * (hsz_c + 16)
    out = {}
    for i in range(cpage_count):
        page = pos + cpage * i
        end = page + cpage
        p = page
        while p < end:
            n = buf[p]
            if n == 0:
                break
            ck = buf[p + 6:p + 6 + hsz_c].hex()
            ek = buf[p + 6 + hsz_c:p + 6 + hsz_c + hsz_e].hex()
            out[ck] = ek
            p += 6 + hsz_c + hsz_e * n
    return out


print("读取 encoding …")
ENC = parse_encoding(read_blte(ENC_EKEYS[1]))
print("encoding 条目:", len(ENC))

root_ekey = ENC[ROOT_CKEY]
print("root EKey:", root_ekey)
root = read_blte(root_ekey)
magic, = struct.unpack_from("<I", root, 0)
assert magic == ROOT_MAGIC, "root magic 异常: %08x" % magic
header_size, version, total, named = struct.unpack_from("<4I", root, 4)
print("root version", version, "total", total, "named", named)

# ── 解析 root：FDID → [(localeFlags, contentFlags, CKey)] ──────────────────
entries = {}
pos = header_size
while pos < len(root):
    n, = struct.unpack_from("<I", root, pos); pos += 4
    if version == 2:
        locale, c1, c2 = struct.unpack_from("<3I", root, pos)
        cflag3 = root[pos + 12]
        content = c1 | c2 | (cflag3 << 17)
        pos += 13
    else:
        content, locale = struct.unpack_from("<2I", root, pos); pos += 8
    ids = []
    fid = 0
    for _ in range(n):
        d, = struct.unpack_from("<i", root, pos); pos += 4
        fid = fid + d
        ids.append(fid)
        fid += 1
    for fid in ids:
        ck = root[pos:pos + 16].hex(); pos += 16
        entries.setdefault(fid, []).append((locale, content, ck))
    if not (total != named and content & NO_NAME_HASH):
        pos += 8 * n

print("root FDID 数:", len(entries))

# ── 取目标瓦片：优先 zhCN，否则报告全部变体 ────────────────────────────────
os.makedirs("_temp/_wc_tiles/era_zhcn", exist_ok=True)
sys.path.insert(0, "_temp")
from _wc_dxt import lootified_blp
from PIL import Image
import numpy as np

for n in sorted(FDIDS):
    fid = FDIDS[n]
    variants = entries.get(fid)
    if not variants:
        print("tile %02d FDID %d: root 中不存在" % (n, fid))
        continue
    zh = [v for v in variants if v[0] & LOCALE_ZHCN]
    pick = zh[0] if zh else None
    tag = "zhCN" if zh else "无 zhCN"
    print("tile %02d FDID %d: %d 个变体，%s" % (n, fid, len(variants), tag))
    if not pick:
        continue
    locale, content, ck = pick
    ek = ENC[ck]
    blp = read_blte(ek)
    out = "_temp/_wc_tiles/era_zhcn/zhcn_%02d.blp" % n
    open(out, "wb").write(blp)
    img = lootified_blp(out).convert("RGB")
    img.save("_temp/_wc_tiles/era_zhcn/zhcn_%02d.png" % n)
    # 与 wago enUS 对比
    en = Image.open("_temp/_wc_tiles/era/era_%02d.blp" % n) if os.path.exists(
        "_temp/_wc_tiles/era/era_%02d.blp" % n) else None
    if en is not None:
        en = lootified_blp("_temp/_wc_tiles/era/era_%02d.blp" % n).convert("RGB")
        d = np.abs(np.asarray(img, np.int16) - np.asarray(en, np.int16))
        print("   zhCN vs enUS: mean=%.2f max=%d" % (d.mean(), d.max()))
