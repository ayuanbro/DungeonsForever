# -*- coding: utf-8 -*-
# 追加日志：手工入口钉（怒焰/哀嚎/死矿，用户截图标位）。
import io

p = '.workbuddy/memory/2026-10-04.md'
note = '''
## 手工入口钉三连（用户截图标 1 落位）
- **新入口**：怒焰裂谷 (59.1,16.9) / 哀嚎洞穴 (41.2,60.6) / 死亡矿井第 1 层 (31.3,22.8)——fc 站只给 halls/ruins 的 entrance，其余副本由用户在地图页标 1、截图红圈质心换算（PIL 找饱和红像素团）。口径用图上既有 boss 钉反验（Oggleflint/Rhahk\\'Zor 偏差 ~1%），截图全图 = 画布假设成立。
- **fc_pins.py**：新增 ENTR_MANUAL 表（slug → (x,y)），parse() 里并入 ent——与 fc RSC entrance 同一管线，exercises 缺省层号 = 第 1 层（死矿 floor1 生效、floor2 不出）。
- **断言 7 处换计数**：怒焰 4→5（4 boss+1 入口，第 6 颗起隐藏）、死矿 floor1 4→5、切层/开关缺省/恢复同步 4→5、ExtraPinsFor 抽查加死矿入口（怒焰从「恒 nil」改查 1 条 entrance）。
- 基线：**1487（16001）/ 1223（38002）双端 0**；锚点 **389/0**；run_all_checks 5/5；sync_beta 零漂移。未提交 git。
'''
s = io.open(p, encoding='utf-8', newline='').read()
io.open(p, 'a', encoding='utf-8', newline='').write(s + note)
print('log ok')
