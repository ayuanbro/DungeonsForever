# -*- coding: utf-8 -*-
# 追加日志：乌尔之书/乔丹铁锤最终对位（用户第二轮截图反馈）
import io

note = '''
## 乌尔之书/乔丹铁锤最终对位（接上，用户第二轮截图）
- **上轮我搞反了**：wowhead classic 页标题实锤 6895 = Jordan's Smithing Hammer、6283 = The Book of Ur（cn.wowhead item 页现全 404，当时据此的「核验」不可信）。DungeonLoot 两行的物品本来就是对的。
- **用户两轮标位合并 ground truth**：乌尔之书 6283 → 第 1 层 (37.3,53.8)（本轮标位，原被乔丹铁锤 boss 骷髅占着）；乔丹铁锤 6895 → 第 6 层 (47.2,79.3)（首轮标位，即 fc 原坐标）。**fc RSC 的 slug↔坐标在影牙页是交叉的**。
- **落地**：① fc_pins.py 改 OBJ_BY_COORD（按 x 坐标登记，绕开交叉 slug）→ Data_MapPins object = {{37.3,53.8,6283},{47.2,79.3,6895,6}}；② Data_BossPos 删 Jordan's Smithing Hammer 条目（非 boss；BossesFor 由 DungeonLoot+PosFor 驱动，删后右栏 boss 列表同步消失，DungeonLoot 行保留=掉落页仍列物件）；规模 63首领/75钉 → 62/74。
- 断言 5 处换口径（动态数据抽查 / 影牙 floor1=3boss+书钉=4 / floor6 文字 / 静态 ID 集 / 规模）。
- 基线：**1486（16001）/ 1222（38002）双端 0**；run_all_checks 5/5；锚点 387/0；sync_beta 零漂移。未提交 git。
- ★ 教训：cn.wowhead 的 item 页全 404 不可用作核验源，用 www.wowhead.com/classic/item=N 页标题；用户两次截图标位要合并成一张对照表再动手。
'''
p = r'D:/workspace/DungeonsForever/.workbuddy/memory/2026-10-04.md'
with io.open(p, 'a', encoding='utf-8', newline='') as f:
    f.write(note)
print('ok')
