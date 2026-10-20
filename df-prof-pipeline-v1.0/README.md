# 无限副本手册 · 专业页数据流水线

把 **foreverchanges.pro** 的专业页抓下来，归一化成 JSON，再生成插件用的 `Data_Prof*.lua`。
一条命令串完「抓取 → 解析 → 字段审计 → 文案对账 → 生成」，也可以分步跑。
另外合并本地客户端价格、商人和 NPC 三份 CSV，生成物品购买资料。
配方学习专精另由 WoW Tools 图纸数据和 Wowhead Forever 训练师数据合并生成，保留学习途径与来源。

> 网页专业数据来自 foreverchanges.pro（Next.js App Router，业务数据内嵌在 RSC 载荷里）。
> 本地 CSV 另包含上游采集的 Wowhead 商人资料和客户端物品资料；CSV 合并脚本不联网抓取。
> 专精步骤会低频请求 Wowhead Forever，默认优先使用七天内的有效缓存；`--offline` 完全不联网。

## 目录

```
_temp/
  fc_update.py          一键流水线（推荐入口）
  fc_fetch.py           1 抓 14 个页面到 _fc/cache（curl）
  fc_parse.py           2 RSC 载荷 → 归一化 JSON
  fc_zones.py           3 区域名 → AreaTable ID
  fc_fields.py          4 字段覆盖审计 + 产物发射复检（需要 lupa）
  fc_i18n.py            5 中文文案对照表对账
  fc_gen.py             6 归一化 JSON → Core/Data/Data_Prof*.lua
  fc_prof_items.py      7 三份本地 CSV → DataProfItems.csv / Data_ProfItems.lua，并更新商人定位
  fc_prof_specializations.py  8 图纸与训练师学习条件 → 训练师 CSV / Data_ProfSpecializations.lua
  strip_comments.py / strip_lua_comments.py   生成物去注释（--apply 后自动跑）
  _fc/cache/            原始页面缓存（--offline 重放用，约 39MB）
  _fc/data/             归一化后的 JSON、DataProfItems.csv、trainer-recipe-specializations.csv
  _fc/i18n/zh.json      中文文案表
  questie/              区域数据（fc_gen 取区域用）
  tools/                最小化 Lua 干跑桩（复检时用，不用装游戏）
Core/Data/              产物样例（随包缓存离线重放生成）
```

脚本全部用 `HERE = 本文件所在目录`、`ROOT = 上一级` 定位，**只要保持 `_temp/` 与 `Core/Data/` 同级就能直接跑**，不用改任何路径。

## 跑起来

```bash
python _temp/fc_update.py --check             # 联网抓取 + 解析 + 审计，不发布 Lua / 合并 CSV
python _temp/fc_update.py --apply             # 联网抓取 + 落盘生成
python _temp/fc_update.py --offline           # 不联网，用 _fc/cache 重放
python _temp/fc_update.py --apply --offline   # 离线落盘（回归 / 无网环境）
```

Windows 上也可以直接双击 `run.bat --check`。

## 流水线各步干什么

| 步骤 | 做什么 | 关键点 |
|---|---|---|
| fc_fetch | 抓首页 → 拿到 13 个专业清单 → 抓各子页 | 顺序请求，单页间隔 0.8s；已缓存且 >20KB 默认跳过，联网模式自动加 `--force` |
| fc_parse | 从 RSC 载荷切出业务数据 | **只取会显示的字段**（白名单）；物品只存 ID 不存名字 |
| fc_zones | 区域名 → AreaTable ID | 离线时用缓存对照表，否则会因没网拿不到 |
| fc_fields | 静态审计 + 把生成的 Lua 真跑一遍核对落地键 | 抓「声明用了但没发射」的静默丢字段 |
| fc_i18n | 文案对照表对账 | 新增英文文案没登记会在这里提示 |
| fc_gen | 生成 5 个 Lua | 紧凑数组的字段序集中在文件顶部的 `ROW_FIELDS` 等常量 |
| fc_prof_items | 合并本地三份 CSV，生成物品表并更新商人定位 | 接在 fc_gen 后，区分 Wowhead 与客户端资料、金币与兑换成本 |
| fc_prof_specializations | 图纸与训练师学习专精合并，生成独立 CSV / Lua | 接在 fc_prof_items 后；缺少证据保留待确认，Wowhead 请求有缓存与冷却限制 |
| strip_lua_comments | 生成物清零注释 | 只在 `--apply` 后跑 |

顺序是硬依赖：解析改键名 → 生成器字段序要跟着改 → 审计能抓到；少跑一步就是「全绿但数据静默变旧」。

## 依赖

- Python 3.8+
- `curl`（fc_fetch 直接调用；Windows 10+ 自带）
- `lupa`（**只有** fc_fields 的发射复检需要；没装会自动跳过那一段，其余照跑）

```bash
pip install lupa
```

## 产物

| 文件 | 内容 |
|---|---|
| `Data_Professions.lua` | 13 个专业的元信息 / 营地物件 / 特权 / 待核实文案 |
| `Data_ProfRecipes.lua` | 配方行 + 附魔 + 附魔材料 + 商人兑换 + 分类 |
| `Data_ProfLeveling.lua` | 1→300 升级路线 + 购物单 + 营地与商贩坐标 |
| `Data_ProfGathering.lua` | 采矿 / 采药 / 剥皮 / 钓鱼节点表 |
| `Data_ProfVendors.lua` | 商人定位（NPCID → 坐标） |
| `Data_ProfItems.lua` | 客户端物品资料及按物品 ID、NPC ID 分开的商人报价，由 fc_prof_items.py 生成 |
| `Data_ProfSpecializations.lua` | 配方 SpellID 对应的学习专精要求、学习途径、构建版本与来源证据 |

原五份网页数据产物约 1MB，只存物品 ID，由客户端提供物品显示资料。
新增的 `Data_ProfItems.lua` 另保留客户端三语物品名称和价格，供购买资料核对。

`Core/Data/` 里放的是**随包缓存离线重放**（`--apply --offline`）的产物，可直接对照格式；它与作者仓库当下的线上版会有差异（缓存停在一个较早的时间点），真数据请自己联网跑一遍。

## 本地 CSV 合并与商人物品表

`_temp/fc_prof_items.py` 只使用 Python 标准库，不联网；支持独立运行，也已接入
`fc_update.py`，排在 `fc_gen.py` 后面，以免新定位被旧生成器覆盖。

默认输入位置按脚本所在目录定位，不受启动目录影响：

- 仓库的 `scripts/out/vendors.csv`：Wowhead 供货关系、原成本、库存、阵营和 NPC 名称。
- 仓库的 `scripts/out/npcs.csv`：Wowhead NPC 名称与定位。
- 仓库的 `scripts/export_buyprice/output/item-buy-prices.csv`：客户端三语物品名、整组基础购买价、组数和构建版本。

从仓库根目录执行：

```powershell
# 独立生成：只处理本地三表，默认写入三个产物
python df-prof-pipeline-v1.0/_temp/fc_prof_items.py

# 独立检查：所有结果只在内存构建，三个产物均不写入
python df-prof-pipeline-v1.0/_temp/fc_prof_items.py --dry-run

# 只用已有 19 列 CSV 重建 Data_ProfItems.lua，不需要原三表，不更新 CSV 或 NPC Lua
python df-prof-pipeline-v1.0/_temp/fc_prof_items.py --from-csv df-prof-pipeline-v1.0/_temp/_fc/data/DataProfItems.csv

# 检查已有 CSV 的 Lua 生成结果，不写文件
python df-prof-pipeline-v1.0/_temp/fc_prof_items.py --from-csv df-prof-pipeline-v1.0/_temp/_fc/data/DataProfItems.csv --dry-run

# 整条流水线：仍先更新/重放网页数据，再合并本地三表
python df-prof-pipeline-v1.0/_temp/fc_update.py --check --offline
python df-prof-pipeline-v1.0/_temp/fc_update.py --apply --offline
```

检查模式仍沿用原流水线对页面缓存、归一化 JSON 和区域对照表的处理；
`--check` 不写生成 Lua 和新合并 CSV。单独运行 `fc_prof_items.py --dry-run` 完全不写文件。
三份输入 CSV 始终保持原样。默认三表模式下，任一输入缺失、结构错误或连接键冲突时停止，保留旧产物。
`--from-csv PATH` 只读取指定的合并 CSV 并重建物品 Lua，不依赖三份原始输入，也不修改商人定位。

可用 `--vendors-csv`、`--npcs-csv`、`--prices-csv` 指定输入，路径相对于调用时的目录。
独立脚本另有 `--output-csv`、`--items-lua`、`--vendors-lua` 输出路径选项。
`--verified-at YYYY-MM-DD` 仅为兼容旧调用保留，并校验日期格式；核验日期不输出到新 CSV 或 Lua。
三个原始输入路径和此兼容日期选项也可直接传给 `fc_update.py`。
`--from-csv` 是独立脚本选项，可配合 `--items-lua` 指定唯一输出路径，以及 `--dry-run` 只检查。

默认输出：

- `_temp/_fc/data/DataProfItems.csv`：以商人表为基础的合并表，UTF-8 BOM。
- `Core/Data/Data_ProfItems.lua`：严格由合并 CSV 的 19 列内容生成 `ns.ProfItems`，另有全局来源审计信息。
- `Core/Data/Data_ProfVendors.lua`：合并更新 `ns.ProfVendors`，保留原 `ns.ProfNPCLocs`。

### CSV 规则

连接键为 `vendors.item_id = prices.ItemID`。CSV 只输出以下 19 列，顺序固定：

```text
item_id,npc_id,name_en,zone_id,side,cost_copper,cost_text,currency_kind,currency_id,currency_amount,stock,Name_enUS,Name_zhTW,Name_zhCN,VendorStackCount,PriceStatus,Build,HotfixBuild,price_source
```

`name_en` 是 **NPC 英文名称**；三语物品名称使用 `Name_enUS/Name_zhTW/Name_zhCN`。
原输入扩展列不增加到 CSV，也不进入每个物品或 NPC 的 Lua 属性。

只有 `cost_copper`、`cost_text`、`currency_kind`、`currency_id`、`currency_amount`
五列去掉首尾空白后全部为空，且客户端基础价为正、状态为 `priced` 或未指定时，
才填写 `cost_copper/cost_text`。已有任何值（包括字符串 `0`）均阻止补价。
输入的 `BuyPriceCopper` 是整组价，补价时直接写入成本，不乘除 `VendorStackCount`。
零基础价或缺失资料不补为免费商品。原特殊货币、物品兑换、金币加兑换物的混合成本原样保留。

价格表中完全没有商人记录的每个物品也追加一行，`item_id` 使用它的 `ItemID`，
NPC、定位、库存、阵营均留空。此范围是价格表的全部物品，并非仅图纸。

`price_source`：已有成本为 `wowhead`，客户端补价为 `client`，未确定成本为空。
`VendorStackCount` 保留客户端的整组购买数量。

每次运行还检查混合成本：`cost_copper/cost_text` 任一有值，同时
`currency_kind/currency_id/currency_amount` 任一有值，即计入 `mixedCostRows`；
按物品 ID 去重计入 `mixedCostItems`。判断忽略首尾空白，`0` 算有值，记录不自动删除或改价。

`stock=-1` 表示不限量，非负库存数字表示补货上限，不能视为角色当前可买数量；
空库存保持未知，空阵营也不会被自动认定为中立。

### Lua 数据结构与定位更新

```lua
ns.ProfItems[item_id] = {
    item_id = item_id,
    Name_enUS = "...", Name_zhTW = "...", Name_zhCN = "...",
    VendorStackCount = 5, PriceStatus = "priced",
    Build = "...", HotfixBuild = "...",
    offers = {
        [npc_id] = {
            npc_id = npc_id, name_en = "NPC English",
            zone_id = 12, side = "a", stock = -1,
            cost_copper = 12345, cost_text = "1g23s45c",
            price_source = "client",
        },
    },
}
```

Lua 属性直接使用 CSV 原列名，区分大小写。物品根保存 `item_id`、三语名称、
`VendorStackCount`、`PriceStatus`、`Build`、`HotfixBuild`；`offers[npc_id]` 保存其余 11 列。
有兑换成本时，报价再保存 `currency_kind`（`currency` 为特殊货币、`item` 为物品兑换）、
`currency_id`、`currency_amount`。混合成本同时保留金币和兑换字段，页面文本不会被当作铜币解析。
未知字段省略，不用零或默认值伪装成已知。

无 `npc_id` 的行把成本等非空 CSV 字段直接保存在物品根，并使用 `offers = {}`，不会虚构 NPC 0。
每条物品或报价不再生成 `basePriceCopper`、`costKind`、`source`、`conditions`、`verifiedAt`
等 CSV 中不存在的属性。默认三表模式先序列化为 19 列 CSV，再用同一份序列化内容生成 Lua；
`--from-csv` 使用同一转换逻辑，适合调整 CSV 后单独重建物品表。

全局 `ns.ProfItemsMeta` 的 `schemaVersion` 为 `2`，仍记录生成时间（UTC）、
输入文件名、SHA-256、来源和行数统计；这些审计信息不增加每个物品或 NPC 的属性。

定位表继续使用 `{areaID, uiMapID, x, y}`，坐标范围 `0..100`（包括 0）。
NPC CSV 的非空字段覆盖已有值，同地图的空字段保留旧值；没有对应 CSV 行的旧 NPC 保留。
如果区域或地图改变，坐标必须完整才更新，不把旧坐标拼到新地图，也不借用旧地图 ID。
同 NPC 多地点全部收录到 `ns.ProfVendorDetails[npcID].locations`，
兼容表 `ns.ProfVendors` 取 CSV 中第一个可定位点；名称也保存在 `ProfVendorDetails`。
原掉落 NPC 表 `ProfNPCLocs` 保留。

脚本先在内存中构建并校验全部输出，再暂存并替换；发布失败时回滚已替换文件。
这些产物只在工具包内生成，尚未加入正式插件 TOC 或消费接口。

回归测试：

```powershell
python -B -m unittest discover -s tests -p 'test_prof_items*.py' -v
```

## 配方学习专精

本步骤覆盖专业配方目录与图纸映射，包括附魔。`ns.ProfSpecializations[spellID]`
保存各学习途径的专精要求，`ns.ProfSpecializationsMeta` 保存来源审计信息。
图纸的学习限制与训练师的学习限制分别保留；成品的使用专精不能替代配方的学习条件。
工程学 `SkillLine=202`、普通分类、配方或 NPC 名称都不能作为地精／侏儒专精证据。

以后重复更新使用统一入口。它先从本机 wow.tools.local 取得当前 DB2／Hotfix，
更新到期的网页缓存，再生成、审计并发布这一批产物。无需手动保存 DB2 表或修改 Build：

```powershell
# 从仓库根目录检查；允许更新缓存，不发布正式 CSV / Lua / 审计文件
python df-prof-pipeline-v1.0/_temp/fc_update.py --specializations-only --check

# 正式更新；同样适合以后由外部定时任务重复调用
python df-prof-pipeline-v1.0/_temp/fc_update.py --specializations-only --apply

# 已成功发布过的本地快照与网页证据可离线重放
python df-prof-pipeline-v1.0/_temp/fc_update.py --specializations-only --apply --offline
```

正式插件 TOC 现在加载仓库根目录的 `Core/Data/Data_ProfSpecializations.lua`。
更新运行数据时，从仓库根目录显式指定该输出；生成器仍保留证据、校验和同批发布流程：

```powershell
python df-prof-pipeline-v1.0/_temp/fc_update.py --specializations-only --apply `
  --specialization-output-lua Core/Data/Data_ProfSpecializations.lua

# 有已发布快照时离线重放到同一正式路径
python df-prof-pipeline-v1.0/_temp/fc_update.py --specializations-only --apply --offline `
  --specialization-output-lua Core/Data/Data_ProfSpecializations.lua
```

不指定覆盖路径时仍输出工具包内的数据样例。不要手工修改生成 Lua。
工程入门任务的任务、NPC、阵营和交付物配置独立保存在
`Core/Data/Data_ProfSpecializationQuests.lua`，由固定版本 Questie Forever 数据核对。
未知学习条件继续保存为 `pending`；运行时允许这类普通配方参与规划，不将其改成已确认通用。

`--specializations-only` 只运行这条更新流程；未指定时，`fc_update.py` 仍执行原有
专业管线。统一入口默认检查模式，只有 `--apply` 发布。在线模式需要可用的
wow.tools.local 和现有 `prof_*.json` 专业目录；它不会刷新其他专业管线的数据源。
从定时任务调用时，建议使用 Python 和脚本的绝对路径；默认输入输出按脚本位置定位，
不依赖任务的工作目录。退出码 `0` 表示成功（含无变化和检查通过），非零表示失败或已有更新进程运行。

统一入口也可直接运行，并覆盖所有输出路径：

```powershell
python df-prof-pipeline-v1.0/_temp/fc_refresh_specializations.py --help
python df-prof-pipeline-v1.0/_temp/fc_refresh_specializations.py --apply `
  --tool-directory 'C:\Users\yewei\Downloads\Release-win-x64' `
  --base-url 'http://127.0.0.1:5000'
```

底层生成器仍可单独重建训练师 CSV／Lua，但不会执行 DB2 导出及两类图纸审计：

```powershell
python df-prof-pipeline-v1.0/_temp/fc_prof_specializations.py --dry-run
python df-prof-pipeline-v1.0/_temp/fc_prof_specializations.py
python df-prof-pipeline-v1.0/_temp/fc_prof_specializations.py --offline
python df-prof-pipeline-v1.0/_temp/fc_prof_specializations.py --refresh-trainers --dry-run
```

默认位置按脚本所在目录定位：

| 类型 | 路径（相对仓库） |
|---|---|
| 图纸 CSV 输出／离线输入 | `scripts/export_buyprice/output/recipe-item-specializations.csv` |
| 训练师 CSV 输入／输出 | `df-prof-pipeline-v1.0/_temp/_fc/data/trainer-recipe-specializations.csv` |
| 配方目录输入 | `df-prof-pipeline-v1.0/_temp/_fc/data/` |
| Wowhead 缓存 | `df-prof-pipeline-v1.0/_temp/_fc/cache/specializations/wowhead-forever/` |
| wuxianwow 目录缓存 | `df-prof-pipeline-v1.0/_temp/_fc/cache/specializations/wuxianwow/` |
| DB2 快照 | `df-prof-pipeline-v1.0/_temp/_fc/cache/specializations/db2/<build>/<内容哈希>/` |
| DB2 图纸审计 | `df-prof-pipeline-v1.0/_temp/_fc/data/recipe-item-link-audit.csv`、`recipe-item-link-audit-summary.json` |
| 网页图纸审计 | `df-prof-pipeline-v1.0/_temp/_fc/data/recipe-item-web-link-audit.json` |
| 独立 Lua 输出 | `df-prof-pipeline-v1.0/Core/Data/Data_ProfSpecializations.lua` |

统一入口还会更新原有 `output/item-buy-prices.csv` 和 `output/item.csv`，字段保持兼容。
`fc_refresh_specializations.py` 支持 `--prices-csv`、`--item-csv`、
`--recipe-items-csv`、`--trainer-csv`、`--output-lua`、`--audit-csv`、
`--audit-json`、`--web-audit-json`、`--data-dir`、`--cache-root`、
`--wowhead-cache-dir`。显式路径相对于调用目录；输出不得覆盖输入目录或缓存。
`--build` 只校验实际目标版本，不把其他版本改标签。
底层 `fc_prof_specializations.py` 使用 `--cache-dir` 指定网页缓存，
网页未提供完整版本时，来源 Build 始终留空，不复制目标 Build。

`fc_update.py --specializations-only` 转发 `--prices-csv`、`--item-csv`、
`--recipe-items-csv`、`--trainer-csv`、`--tool-directory`、`--base-url`、
`--db2-dir`、`--refresh-trainers`、`--refresh-catalog`；
另以 `--specialization-cache-dir`、`--specialization-cache-root`、
`--specialization-data-dir`、`--specialization-output-lua`、`--specialization-build`
分别转发 `--wowhead-cache-dir`、`--cache-root`、`--data-dir`、`--output-lua`、`--build`。
`--skip-recipe-catalog` 对应统一入口的 `--skip-catalog`，显式跳过可选的 wuxianwow 核对。
原 `fc_fetch.py` 的联网强制刷新不会传给 Wowhead 抓取器。

### 重复运行与快照

导出器通过可选 `-LearningSnapshotPath` 保存同轮读取的九张原始表和 manifest；
其中包含完整 Build、Hotfix 哈希、表哈希、行数、来源与时间。
统一入口按内容哈希归档，同一 Build 下不同 Hotfix／表内容分别保留，
相同内容复用已有快照。它同时冻结本轮专业目录、外部目录和网页缓存，
让生成器与审计读取相同输入。

上一轮图纸 CSV 自动按哈希保存到 `cache/specializations/baselines/`。
审计以旧未关联集合与当前未关联集合的并集为范围，区分新增、补齐、仍未知、
以及从当前 Item 表消失或不再属于 ClassID=9 的记录。最后一种情况不算补齐。
没有硬编码 931 个物品或固定 Build；数据相同时保留上次比较基线，
不因重复运行而改写审计结果。八个正式产物只有内容改变时才替换，内容相同则保留修改时间。

`cache/specializations/current.json` 保存最近成功发布的产物哈希、DB2 快照和比较基线；
`runs/last-run.json` 保存本轮状态、变化文件和错误，`runs/update-*.log` 保存子步骤输出。
`--check` 不更新 `current.json` 或正式产物，但可以积累缓存、快照和运行日志。
更新入口使用整个仓库共用的进程锁，并在发布前复核源文件和旧输出未被其他进程改动。

离线默认校验 `current.json`，复用其中指定的 DB2 快照和已有三个导出 CSV；
缺失或哈希不符时停止。首次离线导入可用 `--db2-dir <完整快照目录>`，
但仍需已有、版本一致的价格、Item 和图纸 CSV。旧格式快照明确标为
`legacy_hotfix_unverified`，不会冒充带 Hotfix 哈希的新快照。
没有 wuxianwow 缓存时，可明确跳过这一可选核对；缺少网页证据的配方保持待确认。

### 证据和未知状态

图纸数据来自 `ItemXItemEffect → ItemEffect`，必要时追踪明确的 `SpellEffect`
教学效果与 `SpellLearnSpell`，将原始 `RequiredAbility` 关联至所教配方 SpellID。
通用教学法术本身不能当作制作配方。Wowhead 优先读取专业页的 `recipes` 列表与
`specialization`，依据训练师来源标记或配方页 `taught-by-npc` 确认学习途径；
仅对来源不明确的专精候选补查配方页。

`confirmed` 表示存在明确字段证据；`pending` 表示待确认；
`conflict` 表示同一学习途径的证据有矛盾。字段缺失或 `RequiredAbility=0`
均不能证明通用。不同学习途径不相互覆盖，也不依据名称猜测。
每条证据保存来源、版本及审计信息；网页记录还保留 URL、抓取时间和内容哈希。
本地目标 Build 与网页来源版本分别记录，避免把网页资料当成本地完整版本的核验结果。
训练师 CSV 的 `TargetBuild` 表示这次合并的客户端目标，离线重放允许将合法的旧目标版本
更新为新目标；`SourcePatch`、`SourceBuild`、来源时间与哈希始终保留原值。
网页来源补丁与目标补丁不同，或网页明确提供的完整 Build 与目标不同，证据仍保存，
状态降为待确认。再次重放到匹配版本时，这类版本原因的待确认可恢复为已确认，
其他缺少证据的待确认不会因此升级。补充训练师页面与主专业页面的版本不一致时，也保留待确认。

### 请求保护与失败处理

Wowhead 请求使用固定抓取器身份，先检查适用的 `robots.txt` 规则。
默认复用七天内验证通过的缓存，过期才请求；有服务器验证头时使用条件请求。
串行请求的间隔为三秒加零至两秒随机延迟，并使用跨进程互斥与持久化请求状态，
防止重复启动叠加请求。`--refresh-trainers` 仍遵守 robots、间隔与域名冷却。

遇到 `403`、`429`、验证码、验证页面或 `202` 空响应，立即停止本轮请求；
遵守 `Retry-After`，未提供时默认冷却 24 小时。超时和 `5xx` 最多退避重试两次。
抓取器不切换代理、轮换身份或反复请求验证页面。这些措施降低触发保护的风险，
不能保证站点一定允许抓取；冷却期间可用 `--offline` 重放已有证据。

只有成功解析的页面可以替换有效缓存，已完成的页面可供下次正常运行复用。
wuxianwow 目录下载也使用固定身份、robots 校验、七天有效缓存、条件请求、
跨进程限流和持久冷却；`--refresh-catalog` 强制刷新仍受这些保护约束。
无需每次更新都加刷新参数；正常运行会刷新过期缓存。

统一入口只有在全部校验通过后，才把三个客户端 CSV、训练师 CSV、专精 Lua
和三个审计文件同批暂存发布，并更新成功状态；替换失败使用补偿回滚。
在线抓取或审计失败返回非零，保留旧正式产物，首次失败不发布不完整快照。
缓存与已归档 DB2 快照可留待下次使用。
`--offline` 使用已有 CSV／缓存，缺失证据保留待确认，并报告确认、待确认及冲突数量。
`--check`／`--dry-run` 不发布 CSV、Lua 或审计结果，但允许更新抓取缓存及请求冷却状态。

默认产物写入管线包的 `Core/Data/`；正式插件已接入专精数据、UI 与求解器，
运行数据通过前述 `--specialization-output-lua` 明确更新到仓库根目录。
此流程不复制或部署到游戏安装目录。

### 未关联图纸审计

`_temp/fc_recipe_item_audit.py` 对已有 DB2 快照做离线审计，校验表的 SHA-256
与目标 Build，分别记录明确所教法术、专业等级学习、其他技能系、缺失法术记录、
缺失技能关联以及没有明确教学关系的物品。`SubclassID=0` 只表示书籍；
它不能作为排除专业配方的条件，审计分类也不表示物品当前可获得。

```powershell
python df-prof-pipeline-v1.0/_temp/fc_recipe_item_audit.py --help
```

审计输出位于 `_temp/_fc/data/recipe-item-link-audit.csv` 和
`recipe-item-link-audit-summary.json`。
`--baseline-csv` 可固定补齐前的未关联物品集合，便于对照当前导出结果。
加 `--include-current-unmapped` 同时纳入新版新增的未关联项；统一更新入口自动启用。
未指定 `--db2-dir` 时，优先核验 `current.json` 中的版本、图纸哈希与快照指针，
不按 Build 随意选取某次旧 Hotfix。只有没有该状态文件时才兼容旧的 `db2/<build>/` 布局。
这些分类不会把未知专精改成通用；补上 RecipeSpellID 后，若 RequiredAbility
仍为零或缺失，学习专精仍保持待确认。

`_temp/fc_recipe_item_web_audit.py` 只审计已有、通过哈希及页面身份校验的 Forever 缓存，
按当前未关联集合动态读取 `recipes`、`recipe-items`、`taught-by-item` 与 `teaches`。
它不额外逐物品抓取，也不将网页候选自动写成已确认映射；来源与缺失证据保留在 JSON。

用户提供的 [wuxianwow recipes.json](https://wuxianwow.com/data/recipes.json)
由统一入口缓存更新；独立 DB2 审计可用 `--recipe-catalog-json` 指向已保存的快照，
并配合同目录 `source.json` 记录来源 URL、抓取时间、SHA-256 和独立的来源 Build。
2026-10-21 核验的 2,594 条
`id / spell / skill` 全部匹配本地 `SkillLineAbility`；其中 `id`
对应技能关联记录，`spell` 是法术，`products` 是成品，不能将它们当成
图纸 ItemID 或教学关系，也不能将 `acquire` 直接当作训练师专精要求。
网页没有完整 Build 时保留空值。

## 改成自己的项目

1. 保持 `_temp/` 与 `Core/Data/` 同级，脚本不用改路径
2. 输出文件名和结构在 `fc_gen.py` 的 `ROW_FIELDS` / `ENCHANT_FIELDS` / `STEP_FIELDS` / `NODE_FIELDS` 里，换 UI 就改这几处
3. 站点结构变了：改 `fc_parse.py` 顶部的「页面 → 数据键」映射，然后跑 `fc_fields.py --strict` 看有没有漏字段

## 已知状态（这份快照里）

- `Data_ProfRecipes.lua` 是**惰性建表**（`setmetatable` + `__index` 现场构造）。审计脚本原本用 `pairs` 直接取键，只能拿到空表，会把 `detail` 的 `rows/groups/enchants` 全报成漏发。本包已修：加载后显式调一次 `ns.EnsureProfRecipes()`。你自己写类似审计时要注意同一个坑。
- 文案表里仍有 29 条英文未登记，`fc_gen.py --dry-run` 末尾会列出来，不影响生成。

## 常见问题

**fc_parse 报字段缺失 / JSON 解析失败**
站点改版了。先看 `_fc/reports/` 下的报告，再改 `fc_parse.py` 的页面映射与白名单。

**跑出来的产物和 `Core/Data/` 里的不一样**
正常。`_fc/cache` 是某个时间点的页面快照，联网 `--apply` 才会反映站点最新数据。

**只想更新一个专业**
可以单独跑 `fc_fetch.py` → `fc_parse.py` → `fc_gen.py`，但跳过 `fc_fields.py` 就等于放弃那道保险。

**数据能直接商用/转载吗**
抓的是第三方站点的公开内容，能不能再发布请自己判断，别直接当自己的数据源。
