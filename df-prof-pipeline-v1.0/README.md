# 无限副本手册 · 专业页数据流水线

把 **foreverchanges.pro** 的专业页抓下来，归一化成 JSON，再生成插件用的 `Data_Prof*.lua`。
一条命令串完「抓取 → 解析 → 字段审计 → 文案对账 → 生成」，也可以分步跑。
另外合并本地客户端价格、商人和 NPC 三份 CSV，生成物品购买资料。

> 网页专业数据来自 foreverchanges.pro（Next.js App Router，业务数据内嵌在 RSC 载荷里）。
> 本地 CSV 另包含上游采集的 Wowhead 商人资料和客户端物品资料；CSV 合并脚本不联网抓取。

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
  strip_comments.py / strip_lua_comments.py   生成物去注释（--apply 后自动跑）
  _fc/cache/            原始页面缓存（--offline 重放用，约 39MB）
  _fc/data/             归一化后的 JSON，以及合并物品表 DataProfItems.csv
  _fc/i18n/zh.json      中文文案表
  questie/              区域数据（fc_gen 取区域用）
  tools/                最小化 Lua 干跑桩（复检时用，不用装游戏）
Core/Data/              产物样例（随包缓存离线重放生成）
```

脚本全部用 `HERE = 本文件所在目录`、`ROOT = 上一级` 定位，**只要保持 `_temp/` 与 `Core/Data/` 同级就能直接跑**，不用改任何路径。

## 跑起来

```bash
python _temp/fc_update.py --check             # 联网抓取 + 解析 + 审计，不落盘
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
