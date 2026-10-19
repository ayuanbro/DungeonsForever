#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用真正的 Lua 5.1（lupa.lua51）做 WoW 插件语法校验。

为什么不用 luaparser：luaparser 走的是 5.3/5.4 文法，会放过
「嵌套闭包里用 ...」这种 5.1 才报错的写法（曾导致 ZZ_YYDiag 整文件编译失败）。

用法: python lua51_check.py <文件或目录> [...]
"""
import io
import os
import sys

from lupa import lua51


def make_loader():
    L = lua51.LuaRuntime(unpack_returned_tuples=True, encoding=None)
    # loadstring 产出的 chunk 一定是 vararg 函数，和 WoW 加载插件文件一致
    loader = L.eval(
        """
        function(src)
            local f, err = loadstring(src)
            if not f then return false, err end
            return true
        end
        """
    )
    return loader


def read_text(path):
    with io.open(path, "rb") as fh:
        raw = fh.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.decode("utf-8", "replace")


def collect(targets):
    out = []
    for t in targets:
        if os.path.isdir(t):
            for root, _dirs, files in os.walk(t):
                for name in sorted(files):
                    if name.lower().endswith(".lua"):
                        out.append(os.path.join(root, name))
        elif os.path.isfile(t):
            out.append(t)
    return out


def main(argv):
    files = collect(argv[1:])
    if not files:
        print("no .lua files")
        return 2
    loader = make_loader()
    bad = 0
    print("lua51 check: %d file(s)" % len(files))
    for path in files:
        src = read_text(path)
        # encoding=None 时 lupa 只把 bytes 当作 Lua string 传入
        res = loader(src.encode("utf-8"))
        if isinstance(res, tuple):
            ok, err = res
        else:
            ok, err = res, None
        if ok:
            print("  OK    %s" % path)
        else:
            bad += 1
            print("  FAIL  %s\n        %s" % (path, err))
    print("--- %d failed / %d total ---" % (bad, len(files)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
