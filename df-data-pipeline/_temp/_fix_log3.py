# -*- coding: utf-8 -*-
# 追加日志（2026-10-04 钉点图层第二轮）。bash 反引号会吃 note，改走脚本文件。
import io

p = '.workbuddy/memory/2026-10-04.md'
# 先删掉可能的残尾（上一条 bash 版写坏的段）
s = io.open(p, encoding='utf-8', newline='').read()
bad_head = '\n## 钉点图层第二轮'
i = s.find(bad_head)
if i >= 0:
    s = s[:i]
note = '\n## 钉点图层第二轮：文字层容器 pinText（跨钉遮挡实锤）\n'
note += '- **实锤**：同按钮内图层修完后，跨钉仍被盖——入口钉「副本入口」四字向下溢出按钮边界，压住旁边任务钉的黄「!」（两颗钉是独立 Button，fontstring 挂各自按钮上层级追不过去）。\n'
note += '- **修复（MapUI.lua BuildPins/SyncPins）**：池循环前先建 frame.pinText = CreateFrame("Frame", nil, pins) + SetAllPoints（先建 = frame level 低于全部钉按钮），bt.nm 改挂 pinText——图标（按钮本体 + dot OVERLAY）整体压过全部文字，跨钉成立。池按钮单独 Hide 的两处循环补 nm:SetText("")（文字层不随按钮收）；整体收走 frame.pins:SetShown 不变（pinText 挂其下）。\n'
note += '- **断言/变异**：旧「图钉图层」断言换新口径（pinText 先建 + nm 挂 pinText + 清文字）——旧断言因 MakeFS(bt 串消失 find=-1 **假绿**，顺带排雷；变异 +1「名字挂回按钮本体」；「钉点同步里又新建帧」重锚（单行循环改多行后锚点行没了）。★ 变异锚点必须纯代码行：行尾注释会让锚点结尾的换行符对不上 → 0 次。\n'
note += '- 基线：**1487（16001）/ 1223（38002）双端 0**；锚点 **389/0**；run_all_checks 5/5；sync_beta 零漂移。未提交 git。\n'
io.open(p, 'a', encoding='utf-8', newline='').write(s + note)
print('log ok')
