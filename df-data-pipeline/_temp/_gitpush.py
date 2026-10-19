# -*- coding: utf-8 -*-
"""临时推送助手：用凭据管理器取 GitCode 凭据 → 带凭据 URL 推送（清空 credential.helper）。

用法： python _temp/_gitpush.py <远程路径> [本地refspec]
默认： YY_Addons/DungeonsForever.git  refs/heads/master:refs/heads/master
凭据只在本进程内存中，不落盘；输出里对 userinfo 打码。
"""
import glob
import os
import re
import subprocess
import sys
import urllib.parse

ROOT = r"D:\workspace\DungeonsForever"
HOST = "gitcode.com"


def _gcm():
    """UGit 会随升级换版本目录（旧目录被清），自动挑最新的那份 GCM。"""
    cands = sorted(glob.glob(r"C:\Users\Administrator\AppData\Local\UGit\app-*"), reverse=True)
    for d in cands:
        p = os.path.join(d, "resources", "app", "git", "mingw64", "bin", "git-credential-manager.exe")
        if os.path.isfile(p):
            return p
    raise SystemExit("[FAIL] 找不到 git-credential-manager.exe（检查 UGit 安装）")


GCM = _gcm()


def creds(host):
    r = subprocess.run([GCM, "get"], input="protocol=https\nhost=%s\n\n" % host,
                       capture_output=True, text=True)
    d = {}
    for line in r.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d.get("username"), d.get("password")


def mask(s):
    return re.sub(r"//[^/@]+@", "//***@", s or "")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "YY_Addons/DungeonsForever.git"
    refspec = sys.argv[2] if len(sys.argv) > 2 else "refs/heads/master:refs/heads/master"
    u, p = creds(HOST)
    if not u or not p:
        print("[FAIL] 取不到凭据")
        sys.exit(2)
    url = "https://%s:%s@%s/%s" % (urllib.parse.quote(u, safe=""),
                                   urllib.parse.quote(p, safe=""), HOST, path)
    try:
        r = subprocess.run(["git", "-c", "credential.helper=", "-C", ROOT, "push", url, refspec],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=180)
    except subprocess.TimeoutExpired:
        print("[FAIL] push 超时（>180s）")
        sys.exit(3)
    print("rc =", r.returncode)
    print(mask(r.stdout).strip())
    print(mask(r.stderr).strip())
    sys.exit(r.returncode)
