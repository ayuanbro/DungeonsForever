import sys
files = ["Bridge","GearUI","Hui","ExploreMap","ExploreUI","Core","ProfFollow","VendorPriceDB","ProfRouteAuto","QuickBar","DungeonUI","MainFrame"]
for f in files:
    p = "Core/" + f + ".lua"
    d = open(p, "rb").read()
    crlf = d.count(b"\r\n")
    lf_only = d.count(b"\n") - crlf
    tag = "CRLF" if crlf > 0 and lf_only == 0 else ("LF" if crlf == 0 else "MIXED!")
    print("%-18s crlf=%-6d lf=%-6d %s" % (f, crlf, lf_only, tag))
