import io, os, datetime

D = r"D:\workspace\DungeonsForever\.workbuddy\memory\2026-10-13.md"
line = ("- 任务页四次（用户：显示已完成靠最右边）：iOS 开关锚点 `TOPLEFT plateL +308` → `TOPRIGHT plateL -Q_PAD(8)`，"
        "标签从开关右侧（`LEFT tg RIGHT 6` + justify LEFT）移到**左侧**（`RIGHT tg LEFT -6` + justify RIGHT），"
        "热区随之改 `SetHitRectInsets(-(labelW+6), 0, 0, 0)`；探针实测 tg={TOPRIGHT,TOPRIGHT,-8,-10}。"
        "harness 断言补两 pin（TOPRIGHT 锚 + label RIGHT 锚）。UI_RULES §7 iOS 开关口径纠正：标签挂**开关本体**"
        "（旧文档写「父帧」是错的——父帧 FontString 永被同级子卡盖住）+ 位置口径「靠最右、标签在开关左」。\n")
os.makedirs(os.path.dirname(D), exist_ok=True)
if not os.path.exists(D):
    io.open(D, "w", encoding="utf-8", newline="\n").write("# 2026-10-13 工作日志\n\n")
with io.open(D, "ab") as f:
    f.write(line.encode("utf-8"))
print("appended")
