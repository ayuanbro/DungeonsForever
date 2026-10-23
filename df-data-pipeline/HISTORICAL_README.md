# 历史说明：以下命令不属于统一入口

本文保留最初交接时的结构、脚本数量和路径说明。2026-10-23已清理旧专业包、重复归档、部分已完成脚本、日志和48份工具运行样例，因此下文不代表当前文件清单或可直接执行的流程。当前入口见 [README.md](README.md)；工具数据工作副本由仓库根命令 `python -B df-data-pipeline/prepare_workspace.py` 按需创建，目标目录已存在则拒绝。旧工具中的固定 D 盘路径仍需逐项检查，准备工作副本不会修复这些路径。

# 无限副本手册 · 数据表获取全链路

`Core/Data/` 下 46 张数据表是怎么来的，这个包就装的是那套 Python。

包含：`_temp/` 全部 **1165 个脚本**（原样）+ 可复用的抓取缓存 + 46 张表的产物样例
+ `samples/ClassQuestsForever/`（职业任务生成器的输入样例）。
脚本一个字节没改，路径也没改——所以它不是「开箱即跑」，而是「原样交接」。
能不能跑取决于你本机的路径对不对，见下面「跑起来」。

---

## 先看这张图：数据从哪来

```
                      ┌─────────────────────────┐
   游戏客户端 ────────▶│  ClassQuestsForever     │  任务/链
   (CLIENT)           │  Questie / BGLite / 自带 │  NPC 坐标、法术、物品
                      └───────────┬─────────────┘
                                  │
                      ┌───────────▼─────────────┐
   foreverchanges.pro ▶│  _fc/cache  (RSC 载荷) │  专业 / BIS / 职业指南
   (专业与配装)        └───────────┬─────────────┘  套装 / PvP
                                  │
                      ┌───────────▼─────────────┐
   wowhead  ─────────▶│  nether tooltip (JSON)  │  中英文名
   (攻略与中文名)      │  CDP 真浏览器 (评论)     │  掉落 / 首领 / 评论
                      └───────────┬─────────────┘
                                  │
                      ┌───────────▼─────────────┐
   wuxianwow.com ────▶│  /data/page/quest/*.json│  中文名兜底
   wago.tools    ────▶│  AreaTable              │  区域表
                      └───────────┬─────────────┘
                                  │
                      ┌───────────▼─────────────┐
   手工（路线编辑器） ▶│   _temp/*.json 缓存     │
                      └───────────┬─────────────┘
                                  ▼
                        gen_*.py  /  fc_gen.py
                                  ▼
                        Core/Data/Data_*.lua   ← 禁止手改
```

| 源代号 | 具体是什么 | 用在哪些表 |
|---|---|---|
| **CLIENT** | 游戏客户端的插件数据：`ClassQuestsForever/Data/{Quests,Chains}.lua`、`Questie`、`BGLite`、`TalentsForever` 等 | 副本结构、首领坐标、NPC 位置、任务链、职业战斗、训练师 |
| **FOREVERCHANGES** | `foreverchanges.pro`，Next.js 站点，数据在 RSC 载荷里，curl 抓 14 页 | 专业 5 张表、BIS、职业指南、套装、PvP |
| **WOWHEAD** | `nether.wowhead.com/tooltip/*`（纯 JSON，要代理）+ 浏览器 CDP 抓评论 | 中文名、掉落、首领技能、攻略注释 |
| **WUXIANWOW** | `wuxianwow.com/data/page/quest/<id>.json` 与 `/quest/<id>` 页面 | 中文名兜底（窝窝头查不到时） |
| **WAGO** | `wago.tools` 的 AreaTable 中文 CSV | 区域 → uiMapID |
| **手工** | 路线编辑器 `_route_plan/tune.html`、坐标校准、稀有刷新点 | 路线、地图标记、部分坐标 |

每张表对应哪个脚本、哪个源：见 **`INDEX.md`**。

---

## 跑起来

### 1. 环境

```bash
pip install playwright lupa requests
```

只这三个。`playwright` 用来 `connect_over_cdp` 接管本机浏览器，**不需要** `playwright install`。

还需要：
- **代理** `127.0.0.1:7897`（抓 wowhead 用，脚本里写死；不用的源可直连）
- **Chromium 内核浏览器**（QQBrowser / Chrome / Edge 都行），用于抓评论
- **游戏客户端**（读 CLIENT 类数据时）
- **`wuxian.exe`**（可选，游戏内执行 + 截图的那套自动化）

### 2. 路径

脚本里写死的是作者本机的绝对路径，共 477 个脚本含绝对路径。两种做法：

**A. 把包放到作者的位置**（最省事，零改动）
```
D:\workspace\DungeonsForever\        ← 本包解压到这里
D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\
```

**B. 批量改路径**
```bash
cd _temp
python fix_paths.py            # 先看会改什么
python fix_paths.py --apply    # 写回
```

`fix_paths.py` 只做字符串替换（项目根 / 客户端根 / ClassQuestsForever / 浏览器 / wuxian），
不改逻辑。默认目标是 `D:\workspace\DungeonsForever`、包内 `samples/`、`_classic_beta_`：

```bash
python fix_paths.py --apply --root "D:/my/DF" --wow "D:/Games/WoW/World of Warcraft" \
                    --cqf "D:/Games/WoW/Interface/AddOns/ClassQuestsForever/Data"
```

> 备份脚本（`_bak_*`）里也有路径，替换后它们指向你自己的目录——但这些脚本本来就别跑。

### 3. 三条典型链路

**专业页（最快验证环境对不对）**
```bash
cd _temp
python fc_update.py --offline    # 用包内缓存重放，不联网
python fc_update.py --check      # 联网只检查
python fc_update.py --apply      # 联网落盘
```

**职业任务（有评论抓取，最慢）**
```bash
cd _temp
python gen_class_quest.py --stats   # 先确认能读客户端
python _cq_list_ids.py              # 刷新 id 列表
python _cq_comments_fetch.py        # 抓评论，628 个任务约 49 分钟
python _cq_forever_fetch.py         # 补 forever 分区
python _cq_comments_prep.py         # 清洗
# 人工提炼 → _cq_notes.json
python gen_class_quest.py --apply
```

**副本路线（纯本地，最快）**
```bash
cd _temp
python gen_route_lua.py            # _route_plan/data/*.json → Data_Route.lua
```

### 4. 收尾（每次改完数据都要过）

```bash
python _temp/lua51_check.py        # Lua 5.1 语法
python _temp/qa_lf_verify.py       # 行尾 LF
python _temp/check_zero_comments.py # 零注释门禁
python _temp/sync_beta.py --apply  # 同步到两个客户端
```

---

## 这个包不含什么

| 没带 | 为什么 | 需要时怎么办 |
|---|---|---|
| `_qqb_profile*`（3.2 GB） | 浏览器 profile，含登录态 | 脚本会自己新建 `_temp/_qqb_profile` |
| `_fc/cache_wh_vendors_waf`（156 MB） | 商家页 WAF 抓取缓存 | 重跑 `fc_vendor_resolve_waf.py` |
| `_gearvend` `_mapbake` `_mapcheck` `live` | 一次性中间产物 | 用不到 |
| 截图 / png | 调试产物 | 用不到 |
| `*.psd` / 字体 | 美术资源 | 不在数据处理链路里 |
| 大于 2 MB 的 json/csv | 体积 | 重抓或见 `INDEX.md` 对应脚本 |

包内保留的缓存：`_fc/{cache,cache_zh,data,i18n}`、`_route_plan/{data,tune.html}`、
`questie/questie_forever.json`、`_cq_*.json`、`_wago_AreaTable_zh.csv`，以及 600+ 个小 JSON。
`samples/ClassQuestsForever/{Quests,Chains}.lua` 是客户端那份数据的快照，
`fix_paths.py --apply` 会让 `gen_class_quest.py` 默认读它，不装游戏也能出表。

---

## 几条踩过的坑

1. **生成物禁手改**。改数据改脚本，再重跑；手改会在下次生成时被覆盖。
2. **`dataEnv=1` 只返回零售版**。经典/无限服任务要按 `[8, 11, 4, 5, 3, 1]` 依次回退。
3. **`cn.wowhead.com` 对 curl 返回 403**，评论只在页面 SSR 的 `window.lv_comments0` 里，
   必须真浏览器 CDP。每 10 条落盘一次，断了重跑会自动续。
4. **无限服专属任务在 `www.wowhead.com/forever/cn/quest=<id>`**，主站没有页面——
   抓不到不是没数据，是地址不对。
5. **`Data_ProfRecipes.lua` 是惰性建表**（`setmetatable` + `__index`），
   用 `pairs` 遍历拿到空表，审计脚本要先调 `ns.EnsureProfRecipes()`。
6. **路径已改的脚本别再 `fix_paths --apply`**：替换是幂等的，但会覆盖你手动调过的参数。

---

数据快照：2026-10-19，46 张表 / 1164 个脚本。
