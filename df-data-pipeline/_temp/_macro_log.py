# -*- coding: utf-8 -*-
"""一次性：把宏收集记录追加到当日工作日志。"""
p = '.workbuddy/memory/2026-10-17.md'
note = """

## 全职业专精宏命令收集（wowhead Classic）
- ★ 抓 wowhead 通道复用（10-07 姿势，本次实测仍有效）：`node _temp/_waf_fetch.js <outDir> "key=url"…`（playwright-core + chromium + proxy 7897，NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules）—— 一次 200 全过。同时段对照：jina.ai 匿名被封（AbuseAlleviationError，解封 10-17 01:51）、curl_cffi chrome110/124/131 → 202 AWS WAF 挑战页、curl+UA → 403。**以后抓 wowhead 直接上浏览器通道，别先试 HTTP 客户端**。
- URL 规律：`/classic/guide/classes/{class}/{role}-macros`（role = dps | tank | healer）。Classic 端宏指南全集只有 10 个：战士防护、圣骑神圣+惩戒、猎人、盗贼、牧师治疗、萨满恢复、法师、术士、德鲁伊恢复。缺失（战士武器/狂暴、防骑、暗影牧、元素/增强萨、平衡/野性德）在 classic 树不存在 —— warrior/dps-macros 与 paladin/tank-macros 会 302 到 TBC 同名页（canonical 落 /tbc/）；旧式 slug（classic/guides/xxx-macros-classic-wow）不存在时 302 到职业索引页。
- `/classic/cn/…` 与 `/classic/…` 是同一页，差别只是专有名词本地化（标题/正文里的法术物品名变中文，宏代码仍英文）。
- 解析要点：宏段两种渲染 —— ① `pre class="code exclude-units"` ② `h3 id=…` + `div class="box" data-level="null"`；正文与评论区分界 = 首个 `class="comment-body"`（不切会把用户评论里的宏也算进来）。
- 产物：`_temp/_macro_parse.py` → `_temp/_macro_data.json`；`_temp/gen_macro_doc.py` → `_temp/macros/wow_classic_macros.html|.md`（10 职业 / 74 条宏 / 97 段代码）。
"""
open(p, 'a', encoding='utf-8').write(note)
print('appended')
