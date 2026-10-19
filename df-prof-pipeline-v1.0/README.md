# 无限副本手册 · 专业页数据流水线

把 **foreverchanges.pro** 的专业页抓下来，归一化成 JSON，再生成插件用的 `Data_Prof*.lua`。
一条命令串完「抓取 → 解析 → 字段审计 → 文案对账 → 生成」，也可以分步跑。

> 数据源是 foreverchanges.pro（Next.js App Router，业务数据内嵌在 RSC 载荷里），**不是 wowhead**。
> wowhead 只在这套流程之外用来补个别物品名 / 任务名，不在本包里。

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
  strip_comments.py / strip_lua_comments.py   生成物去注释（--apply 后自动跑）
  _fc/cache/            原始页面缓存（--offline 重放用，约 39MB）
  _fc/data/             归一化后的 JSON（生成器的唯一输入）
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

## 七步各干什么

| 步骤 | 做什么 | 关键点 |
|---|---|---|
| fc_fetch | 抓首页 → 拿到 13 个专业清单 → 抓各子页 | 顺序请求，单页间隔 0.8s；已缓存且 >20KB 默认跳过，联网模式自动加 `--force` |
| fc_parse | 从 RSC 载荷切出业务数据 | **只取会显示的字段**（白名单）；物品只存 ID 不存名字 |
| fc_zones | 区域名 → AreaTable ID | 离线时用缓存对照表，否则会因没网拿不到 |
| fc_fields | 静态审计 + 把生成的 Lua 真跑一遍核对落地键 | 抓「声明用了但没发射」的静默丢字段 |
| fc_i18n | 文案对照表对账 | 新增英文文案没登记会在这里提示 |
| fc_gen | 生成 4 个 Lua | 紧凑数组的字段序集中在文件顶部的 `ROW_FIELDS` 等常量 |
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

体积能压到 1MB 左右的关键：**物品名 / 图标 / 品质 / 区域名一律不落盘**，只存 ID，显示时由客户端给中文。

`Core/Data/` 里放的是**随包缓存离线重放**（`--apply --offline`）的产物，可直接对照格式；它与作者仓库当下的线上版会有差异（缓存停在一个较早的时间点），真数据请自己联网跑一遍。

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
