import sys, shutil

TOC = r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/DungeonsForever/DungeonsForever.toc"
BAK = r"D:/workspace/DungeonsForever/_temp/toc_client_opt.bak"

mode = sys.argv[1] if len(sys.argv) > 1 else ""

if mode == "backup":
    shutil.copy2(TOC, BAK)
    print("backup ->", BAK)

elif mode == "strip":
    data = open(TOC, "rb").read()
    out, n = [], 0
    for ln in data.split(b"\n"):
        i = ln.find(b" [AllowLoadTextLocale ")
        if i >= 0:
            ln = ln[:i]
            n += 1
        out.append(ln)
    open(TOC, "wb").write(b"\n".join(out))
    print("stripped directives:", n)

elif mode == "restore":
    shutil.copy2(BAK, TOC)
    print("restored ->", TOC)

elif mode == "count":
    data = open(TOC, "rb").read()
    print("directives now:", data.count(b"[AllowLoadTextLocale "))
    print("zhTW refs:", data.count(b"zhTW"))
    print("enUS refs:", data.count(b"enUS"))

else:
    print("usage: toc_ab.py backup|strip|restore|count")
