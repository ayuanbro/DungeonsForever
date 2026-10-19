# -*- coding: utf-8 -*-
BS = chr(92)
p = r"D:\workspace\DungeonsForever\.workbuddy\memory\2026-10-10.md"
note = (
    "\n## 专业设置页说明改「?」悬停提示（17:59-18:05，本会话）\n"
    "- 用户：设置行下直铺的说明文字（desc/d1/d2 两行灰字 + 行内副行）改为 设置名右侧「?」图标，"
    "悬停出 tooltip 显示这些注释。\n"
    "- 实现（patch_prof_settings_help.py）：① Build 期新增 `PD.setHelps` 池（容量 = SETTING_TOG_MAX，"
    "Button 16x16 + 金色「?」FontString，OnEnter 出 GameTooltip ANCHOR_RIGHT、OnLeave 收，"
    "滚轮转发 DG.WheelScroll）；② RowsSettings 行 spec 删 `sub`/`lines`/两条直铺 PushText，"
    "改挂 `help = {名字, desc, d1, d2}`（行悬停提示同步退役，信息只在 ? 上）；"
    "③ PlaceSettingsToggles 里问号锚 `LEFT, rr.a(名字 FS), RIGHT, 6, -1`、帧层 rr+10、"
    "`hp.__tip = spec.help`，尾部隐藏循环与开关池同款；④ 杂帧扫描 known 集合补 setHelps。\n"
    "- harness：㉒ 静态断言补 setHelps/锚点/__tip + 负向（sub=d.desc、d1 直铺 PushText 判缺席）；"
    "新增 MUT_PROF_HELP_GONE（hp.__tip 断开）。★ 又踩：注册行锚点别带字面 NL（那是 b'' 内部用的），"
    "源码行尾用真换行。\n"
    "- 验证：lua51 0 错；CRLF 5650/0；锚点 246/0；主 harness 920/1（os.* 存量）；"
    "新变异隔离 1/1；部署 md5 全等。未提交、未打包。\n"
)
open(p, "a", encoding="utf-8").write(note)
print("log appended")
