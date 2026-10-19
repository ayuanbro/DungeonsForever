# -*- coding: utf-8 -*-
"""无限副本手册 发布打包脚本（从 TalentsForever/_temp/package_zip.py 派生）。

流程（对应 AGENTS.md「打包规则」「验证要求」）：
  1. 版本号从 DungeonsForever.toc 的 ## Version 读取
  2. 引用反向扫描：TOC 与 XML 清单里引用的每个文件都必须存在
  3. 孤儿扫描：磁盘上存在但未被任何清单加载的 .lua 不允许进包
  4. 生成 ZIP（内层顶层目录固定 DungeonsForever/）+ SHA-256
  5. 复制到 forever 客户端实机 AddOns 根目录，并核对两份哈希一致
  6. 结构校验：顶层目录、排除项零泄漏

打包集规则唯一出处 = .workbuddy/tools/pkgfiles.py（2026-10-06 收拢，
本文件只保留 ZIP 流程；排除清单/清单列表/引用扫描/孤儿扫描全部从 pkgfiles 取）。

用法：
  python package_zip.py            # 正式打包
  python package_zip.py --dry-run  # 只做校验并列出清单，不落盘
"""
import hashlib
import os
import shutil
import sys
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), ".workbuddy", "tools"))
import pkgfiles  # noqa: E402

ADDON_NAME = pkgfiles.ADDON_NAME
# 源码根 = 仓根（pkgfiles 由 .workbuddy/tools 上溯三级得出，与本脚本上一级一致）
ADDON_DIR = pkgfiles.ROOT
# 产物副本目标 = forever 客户端实机 AddOns 根（原泰坦 AddOns 根随客户端移除而退役）
ADDONS_ROOT = r"D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns"
# 产物目录（2026-10-05 加 DF_PACK_OUT 环境变量口）：同名版本重打包时若旧 ZIP 被
# WorkBuddy 预览锁住（os.remove 被 shim 强转 trash 又 fail-closed），用
# DF_PACK_OUT=<临时目录> 绕开，产物落临时目录、实机侧复制不受影响。
OUT_DIR = os.environ.get("DF_PACK_OUT") or r"D:\UGit\打包后\无限副本手册"

# 兼容旧引用：结构校验里仍用这两个名字
EXCLUDE_DIRS = pkgfiles.EXCLUDE_DIRS
EXCLUDE_FILES = pkgfiles.EXCLUDE_FILES

read_version = pkgfiles.read_version
walk_files = pkgfiles.walk_files
excluded_name = pkgfiles.excluded_name
check_references = pkgfiles.check_references
find_orphans = pkgfiles.find_orphans


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def preflight():
    missing, loaded = check_references()
    if missing:
        print("[FAIL] 引用缺失（清单里写了但磁盘上没有）:")
        for m in missing:
            print("   - " + m)
        sys.exit(1)
    print("[OK] 引用反向扫描通过（%d 个清单）" % len(pkgfiles.MANIFESTS))

    orphans = find_orphans(loaded)
    if orphans:
        print("[FAIL] 孤儿模块（存在但未被任何清单加载，不得进包）:")
        for o in orphans:
            print("   - " + o)
        sys.exit(1)
    print("[OK] 孤儿扫描通过（无未加载 .lua）")
    return loaded


def main():
    dry_run = "--dry-run" in sys.argv[1:]

    version = read_version()
    zip_name = "%s%s.zip" % (ADDON_NAME, version)
    zip_path = os.path.join(OUT_DIR, zip_name)
    print("[INFO] 版本 %s -> %s" % (version, zip_name))

    preflight()

    files = walk_files()
    print("[INFO] 待打包文件 %d 个（已排除 %s / %s / 前缀 %s）"
          % (len(files), sorted(EXCLUDE_DIRS), sorted(EXCLUDE_FILES),
             pkgfiles.EXCLUDE_PREFIXES))
    for p in files:
        print("   + " + os.path.relpath(p, ADDON_DIR).replace(os.sep, "/"))

    if dry_run:
        print("[DRY-RUN] 未落盘。")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(zip_path):
        os.remove(zip_path)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            rel = os.path.relpath(p, ADDON_DIR)
            z.write(p, os.path.join(ADDON_NAME, rel))
    print("[OK] ZIP: %s (%d files)" % (zip_path, len(files)))

    digest = sha256_of(zip_path)
    sha_path = zip_path + ".sha256"
    with open(sha_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("%s  %s\n" % (digest, zip_name))
    print("[OK] SHA-256: %s" % digest)

    dst_zip = os.path.join(ADDONS_ROOT, zip_name)
    dst_sha = dst_zip + ".sha256"
    shutil.copy2(zip_path, dst_zip)
    shutil.copy2(sha_path, dst_sha)
    print("[OK] Copied: %s" % dst_zip)

    if sha256_of(dst_zip) != digest:
        print("[FAIL] AddOns 根目录副本哈希不一致！")
        sys.exit(1)
    print("[OK] 两份 ZIP 哈希一致")

    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
    bad = [n for n in names if n.replace("\\", "/").split("/")[0] != ADDON_NAME]
    leaked = [n for n in names
              if any(seg in EXCLUDE_DIRS for seg in n.replace("\\", "/").split("/")[:-1])
              or excluded_name(os.path.basename(n))]
    if bad:
        print("[FAIL] 顶层目录异常: %s" % bad[:5])
        sys.exit(1)
    if leaked:
        print("[FAIL] 排除项泄漏: %s" % leaked[:10])
        sys.exit(1)
    if len(names) != len(files):
        print("[FAIL] 条目数 %d != 磁盘文件数 %d" % (len(names), len(files)))
        sys.exit(1)
    if os.path.getsize(zip_path) == 0:
        print("[FAIL] ZIP 体积为 0")
        sys.exit(1)
    print("[OK] 结构校验通过：%d 个条目，顶层为 %s/" % (len(names), ADDON_NAME))


if __name__ == "__main__":
    main()
