# -*- coding: utf-8 -*-
"""GitHub 用户版镜像同步：把打包集（= ZIP 内容口径）镜像到独立仓并推送 GitHub。

- 镜像仓 = D:/workspace/DungeonsForeverGitHub（独立 .git，不属于开发仓）。
- 文件清单 = .workbuddy/tools/pkgfiles.py::walk_files（与 package_zip.py 完全同口径）。
- 变更才有 commit；commit 后 push origin master。
- 用法：python _temp/_github_sync.py [--no-push]
"""
import os
import shutil
import subprocess
import sys

ROOT = r"D:\workspace\DungeonsForever"
MIRROR = r"D:\workspace\DungeonsForeverGitHub"
REMOTE_URL = "https://github.com/ayuanbro/DungeonsForever.git"
TOOLS = os.path.join(ROOT, ".workbuddy", "tools")

sys.path.insert(0, TOOLS)
import pkgfiles  # noqa: E402


def run(args, cwd=None, check=True):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        raise SystemExit("[FAIL] %s" % " ".join(args))
    return r


def git(args, cwd=MIRROR, check=True):
    return run(["git", "-c", "core.autocrlf=false"] + args, cwd=cwd, check=check)


def main():
    push = "--no-push" not in sys.argv
    files = pkgfiles.walk_files(ROOT)
    rels = set()
    for src in files:
        rel = os.path.relpath(src, ROOT).replace(os.sep, "/")
        rels.add(rel)
        dst = os.path.join(MIRROR, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.isfile(dst) or os.path.getsize(src) != os.path.getsize(dst) \
                or open(src, "rb").read() != open(dst, "rb").read():
            shutil.copy2(src, dst)
    removed = 0
    for r, dirs, names in os.walk(MIRROR):
        if ".git" in dirs:
            dirs.remove(".git")
        for n in names:
            p = os.path.join(r, n)
            rel = os.path.relpath(p, MIRROR).replace(os.sep, "/")
            if rel not in rels:
                os.remove(p)
                removed += 1
    for r, dirs, names in os.walk(MIRROR, topdown=False):
        if ".git" in dirs:
            dirs.remove(".git")
            continue
        if not dirs and not names and r != MIRROR:
            os.rmdir(r)

    if not os.path.isdir(os.path.join(MIRROR, ".git")):
        run(["git", "init", "-b", "master"], cwd=MIRROR)
        git(["remote", "add", "origin", REMOTE_URL])
    git(["add", "-A"])
    has_head = git(["rev-parse", "--verify", "--quiet", "HEAD"], check=False).returncode == 0
    staged = has_head and git(["diff", "--cached", "--name-only"], check=False).stdout.strip()
    if not staged and has_head:
        print("[SAME] 打包集无变化，镜像已是最新（%d 文件）" % len(rels))
        return
    ver = pkgfiles.read_version(ROOT)
    git(["commit", "-m", "release: %s" % ver])
    print("[COMMIT] %s（%d 文件，删除 %d）" % (ver, len(rels), removed))
    if push:
        for attempt in range(3):
            r = git(["-c", "http.proxy=http://127.0.0.1:7897", "push", "-u", "origin", "master"],
                    check=False)
            if r.returncode == 0:
                print("[PUSH] GitHub OK（%s）" % ver)
                return
            print("[RETRY %d] push rc=%d %s" % (attempt + 1, r.returncode,
                                                (r.stderr or "").strip().splitlines()[-1:]))
        print(r.stdout.strip())
        print(r.stderr.strip())
        sys.exit(r.returncode)


if __name__ == "__main__":
    main()
