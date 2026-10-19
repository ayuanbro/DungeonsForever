# -*- coding: utf-8 -*-
import io

p = '.workbuddy/memory/2026-10-04.md'
note = """
## 乌尔之书 / 乔丹铁锤 最终对调（用户实机查验第三次定案）
- **定案**：乔丹铁锤 6895 = 第 1 层 (37.3,53.8)（庭院铁匠铺）；乌尔之书 6283 = 第 6 层 (47.2,79.3)（阿鲁高档）。fc slug 与坐标交叉 + wowhead cn 域 404 三轮才掰正——教训：物品身份必须用 www.wowhead.com/classic 页标题核，位置以用户实机查验为最终真源。
- fc_pins.py OBJ_BY_COORD 对调 + 注释更新；Data_MapPins 三语变体再生。
- harness：动态抽查/影牙第1层/第6层/静态 Data_MapPins 四段断言同步对调。
- 基线：**1487（16001）/ 1223（38002）双端 0**；run_all_checks 5/5；锚点 390/0；sync_beta 零漂移。未提交 git。
"""
with io.open(p, 'a', encoding='utf-8', newline='') as f:
    f.write(note)
print('ok')
