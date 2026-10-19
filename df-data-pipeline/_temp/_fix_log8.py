# -*- coding: utf-8 -*-
import io

p = '.workbuddy/memory/2026-10-04.md'
note = """
## boss 钉图标恢复身份色（用户问「怎么全是黄色」——此前 R5 重写时我改成了钉体恒定金、身份色只在文字）
- **定案（用户口径）**：boss 图标与文字同色（都走 M.BossColor 身份色）；稀有仍银染 (0.72,0.76,0.85)；任务「!」/入口门/物品图标仍白染。
- **实现**：渲染块重排——名字/颜色块先算（local nm,cr,cg,cb 声明提前，避免 boss 色赋值落到全局），贴图分派后置；boss 分支 dot:SetVertexColor(cr,cg,cb)（原来恒定 (1,0.82,0)）。
- **收口**：静态断言 +1（BossColor 先算 + dot 同色 + 声明在分派前）；变异 +1「图标回退恒定金」（隔离有效，连带挂两条）；锚点 **391/0**。
- 基线：**1488（16001）/ 1224（38002）双端 0**；run_all_checks 5/5；sync_beta 零漂移。未提交 git。
"""
with io.open(p, 'a', encoding='utf-8', newline='') as f:
    f.write(note)
print('ok')
