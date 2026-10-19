import sys

P = r"D:\workspace\DungeonsForever\_temp\gen_enus.py"
d = open(P, "rb").read()
print("CRLF", d.count(b"\r\n"), "bareLF", d.count(b"\n") - d.count(b"\r\n"))

old = "'\u524d\u5bfc\u4efb\u52a1': 'Intro quest', '\u540e\u7eed\u4efb\u52a1': 'Follow-up quests',".encode("utf-8")
new = "'\u524d\u7f6e\u4efb\u52a1': 'Pre-quests', '\u540e\u7eed\u4efb\u52a1': 'Follow-up quests',".encode("utf-8")
c = d.count(old)
print("命中", c)
if c != 1:
    sys.exit(1)
open(P, "wb").write(d.replace(old, new))
print("OK")
