import sys

P = r"D:\workspace\DungeonsForever\.workbuddy\UI_RULES.md"
d = open(P, "rb").read()
print("CRLF", d.count(b"\r\n"), "bareLF", d.count(b"\n") - d.count(b"\r\n"))
assert d.count(b"\r\n") == 0

old1 = ("**iOS 开关（2026-10-13 五人本任务页实测口径）**：`ns.hui.ReskinToggle(tg[, w, h])`，默认 **36×20**（圆钮 14）。"
        "标签必须挂**父帧**（`PurgeNative` 会隐藏 tg 上一切非自建子件），锚 `LEFT tg RIGHT 6`、字号 14。")
new1 = ("**iOS 开关（2026-10-13 五人本任务页实测口径）**：`ns.hui.ReskinToggle(tg[, w, h])`，默认 **36×20**（圆钮 14）。"
        "标签必须挂**开关本体**（★ 挂父帧会被同级子帧——如左卡实底卡——永久盖住：父帧 FontString 永远排在子帧之下），"
        "且在 `ReskinToggle` **之后**创建（`PurgeNative` 会隐藏 tg 上一切非自建子件）；字号 14。"
        "**位置口径（2026-10-13 用户拍板：靠最右）**：开关贴所在卡**右内衬**（`TOPRIGHT 卡 TOPRIGHT −Q_PAD`），"
        "标签随之移到开关**左侧**（锚 `RIGHT tg LEFT −6`），热区随侧改 `SetHitRectInsets(−(labelW+6), 0, 0, 0)`。")

old2 = "`Q_X_PRE`/`Q_BAR_W` 退役）"
new2 = ("`Q_X_PRE`/`Q_BAR_W` 退役）⑤ 「显示已完成」开关改**靠左卡最右**（`TOPRIGHT` 右内衬 8，标签移到开关左侧）|")

for name, o, n in (("sw1", old1, new1), ("sw2", old2, new2)):
    c = d.count(o.encode("utf-8"))
    print(name, "命中", c)
    if c != 1:
        sys.exit(1)
    d = d.replace(o.encode("utf-8"), n.encode("utf-8"))

open(P, "wb").write(d)
print("UI_RULES 写回 OK")
