# -*- coding: utf-8 -*-
# 落地日志：图钉图层第三轮（SetFrameLevel 显式钉层级）
import io

p = '.workbuddy/memory/2026-10-04.md'
note = """
## 钉点图层第三轮：SetFrameLevel 显式钉层级（用户实机三反馈：任务钉仍被「副本入口」文字盖）
- **实锤引擎坑**：pinText 与按钮同为 pins 子级时，同层级下 FontString 渲染在兄弟 Frame **之后**（引擎文字后画）——「先建低层容器」压不住，必须显式 `pinText:SetFrameLevel(math.max(pins:GetFrameLevel(), 0))`，按钮保持默认 = 父层+1 ⇒ 图标严格高于全部文字。
- **断言/变异**：㊲b 图钉图层断言升第三轮口径（+SetFrameLevel 行）；变异 +1「层级没钉住」（隔离有效 1/1）；锚点 **390/0**。
- 基线：**1487（16001）/ 1223（38002）双端 0**；run_all_checks 5/5；sync_beta 零漂移。未提交 git。
"""
with io.open(p, 'a', encoding='utf-8', newline='') as f:
    f.write(note)
print('日志已追加')
