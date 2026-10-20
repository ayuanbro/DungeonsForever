# scripts/ —— 商人定位采集（gen_vendors.py）

本机 Forever 表导出入口为 [`export_buyprice/export-item-buy-prices.ps1`](export_buyprice/README.md)：同次运行产生三语基础购买价 `export_buyprice/output/item-buy-prices.csv` 和完整物品表 `export_buyprice/output/item.csv`。本目录工具链只输出 CSV，不生成或导入 Lua，也不写游戏安装目录。插件中的旧 NPC 购买价格已删除，等待新的购买价格设计，不从商人窗口或历史缓存补价；AH 行情与数量保留。下文游戏 API 的“售价”专指卖店收益，与 NPC 购买价格不同。

为 **Item.csv（wow.tools 导出）里的每张图纸/配方** 找出：谁卖它（NPC）、在哪卖
（区域 + 坐标 + 阵营），并解析出售行的**成本与库存**。只输出 CSV，不写 Lua，
不取售价（售价由游戏内 API 取得）。

## 链路

```
Item.csv（ClassID=9 配方物品，默认排除书籍 sub=0）
        │ --ids / --id-file 可额外追加
        ▼
Wowhead Forever 物品页 Sold by（本机 Chrome，playwright 渠道 + 代理过 WAF，
        │   缓存 .cache/soldby/<id>.html；每行解析 NPC/区域/阵营/英文名/成本/库存）
        ▼
NPC 信息：nether.wowhead.com/forever/tooltip/npc/<id>
        │（默认英文名，--locale zhCN 可切；map.zone + 首组坐标；缓存 .cache/nether/）
        │  QuestieDB questie_forever.json 的 npc_spawns 兜底（--questie）
        ▼
产物：scripts/out/vendors.csv + scripts/out/npcs.csv（不写任何 Lua）
```

## 运行

前置：`pip install playwright`（无需 `playwright install`，走本机 Chrome 渠道）、
本机安装 Chrome（或 Edge，用 `--channel msedge`）。
nether 走 `--proxy`（Windows 默认 `http://127.0.0.1:7897`；无代理时传 `--proxy ""`）。

```bash
# 自检（无网络，校验解析器）
python scripts/gen_vendors.py --selftest

# 预演（只读 Item.csv，打印数量与缓存命中，不抓取）
python scripts/gen_vendors.py --item-db2 "C:/Users/yewei/Downloads/item.csv" --plan

# 全量：Item.csv 的配方 → Chrome 抓 wowhead → 写两个 CSV
python scripts/gen_vendors.py --item-db2 "C:/Users/yewei/Downloads/item.csv"

# 中文名 + 连书籍一起
python scripts/gen_vendors.py --item-db2 "C:/Users/yewei/Downloads/item.csv" --locale zhCN --keep-books

# 少量试水
python scripts/gen_vendors.py --ids 85,193 --dry

# 离线重算（用已抓的缓存，不联网）
python scripts/gen_vendors.py --item-db2 "C:/Users/yewei/Downloads/item.csv" --soldby-provider cache
```

## 产物 CSV 格式

`scripts/out/vendors.csv`（物品 → 商人，一行一个商人）：

```csv
item_id,npc_id,zone_id,side,name_en,name_locale,cost_copper,cost_text,currency_kind,currency_id,currency_amount,stock
10713,3492,17,a,Vexspindle,,12345,1g23s45c,,,,5
264237,248200,17,h,Fizzlefuse,,, ,currency,3402,360,-1
```

- `cost_copper` 总铜币（成本），`cost_text` 可读格式（如 `1g23s45c`）；普通金币价都存铜；
- 非金币价格（如「商人青睐」）：`currency_kind=currency`、`currency_id` 为链接里
  `currency=` 的 ID（以物易物则是 `item=` 的 ID，`currency_kind=item`）、
  `currency_amount` 为数量（链接文本）；此时 `cost_copper` 留空；
- `stock` 库存/储藏量：**`-1` = 不限量（页面 ∞）**，`N` = 限量 N 个，空 = 未知；
- 售价（sellprice）**不采集**，由你在游戏内用 API 获取。

`scripts/out/npcs.csv`（NPC → 坐标，一行一个刷新点）：

```csv
npc_id,name_en,name_locale,zone_id,ui_map_id,x,y
2113,Archibald Kava,,85,1420,32.4,65.6
```

## 可切换接口（provider 契约）

| 层 | 选项 | 说明 |
|---|---|---|
| Sold by | `--soldby-provider wowhead`（默认） | Chrome 抓取，缓存 `.cache/soldby/` |
| | `--soldby-provider cache` | 只读缓存（离线重算） |
| | `--soldby-provider json --soldby-json f` | 导入 `{item: [{npc,zone,side,name,cost,stock}]}`（如游戏内采集导出） |
| NPC 信息 | `--npc-provider nether`（默认） | 名称 + 区域 + 坐标 |
| | `--npc-provider questie --questie f` | QuestieDB npc_spawns |
| | `--npc-provider json --npc-json f` | 导入 `{npc: {name, coords:[[zone,x,y]]}}` |

新增数据源：加一个类实现对应契约即可，主流程不用改：

- sold-by provider：`sold_by(ids) -> {itemID: [{npc,name,zone,side,cost,stock}]}`
- npc provider：`npc_info(npcs) -> {npcID: {name, coords:[(zone,x,y)]}}`

## 其他接口

- `--ids` / `--id-file`：额外指定物品 ID（与 Item.csv 取并集）。
- `--keep-books`：保留 `SubclassID=0` 的书籍（默认排除，它们不是专业配方）。
- `--locale zhCN`：nether 名称语言（默认空=英文）。
- `--refetch` / `--soldby-max-age N`：强制重抓 / 超过 N 天滚动重抓（每日更新建议 7）。
- `--proxy`（环境变量 `DF_PROXY`）、`--channel`（chrome/msedge/chromium）、
  `--browser`（显式 exe 路径）、`--cdp`（附加到已开调试口的 Chrome）、
  `--workers`、`--page-delay`、`--headless`。
- `--csv-out ""` / `--npcs-out ""` 可关掉某个 CSV；`--dry` 只算不写。

## 注意事项

- Item.csv 的配方判定：`ClassID=9`（Recipe），`SubclassID` 细分专业（0 书籍 / 1 制皮 /
  2 裁缝 / 3 工程 / 4 锻造 / 5 烹饪 / 6 炼金 / 7 急救 / 8 附魔 / 9 钓鱼）。
- 成本和库存按 wowhead Sold by 表的真实列结构解析（Stock 列为 `∞` → 不限量存 `-1`；
  数字 → 限量；Cost 列为金/银/铜 span；为 `currency=`/`item=` 链接时存货币单位）。
  正则见脚本顶部 `parse_cost` / `parse_currency` / `parse_stock`。
- wowhead 抓取会被 CloudFront 间歇性封锁：脚本内置 300s 冷却重试；
  建议挂好代理后分批跑，缓存不会白抓。
- 结束时 stderr 可能出现 `EPIPE ... Node.js v24`：playwright 驱动的退出噪音，
  exit=0、产物正常，可忽略。

## Linux 服务器每日更新

同一份脚本在服务器上直接可用：非 Windows 自动 headless chromium、默认直连
（被 CloudFront 拦时配 `DF_PROXY`）。每日运行是增量的：

- `.cache/soldby/` 永久复用；`--soldby-max-age 7` 让超过 7 天的旧页滚动重抓；
- nether 缓存长期有效，只补新 NPC。

### 1. 服务器初始化（Debian/Ubuntu 示例）

```bash
sudo apt-get install -y python3-venv
python3 -m venv ~/dfenv && source ~/dfenv/bin/activate
pip install -r scripts/requirements.txt
playwright install --with-deps chromium      # 系统依赖需要 sudo 时按提示执行
# 上传一次数据文件（wow.tools 导出的 Item.csv；官方出新 build 后重新导出上传即可）
scp item.csv user@server:/data/item.csv
```

### 2. 定时任务（systemd，二选一）

`/etc/systemd/system/gen-vendors.service`：

```ini
[Unit]
Description=DungeonsForever vendor data daily refresh

[Service]
Type=oneshot
WorkingDirectory=/opt/DungeonsForever
Environment=PY=/home/user/dfenv/bin/python
Environment=ITEM_CSV=/data/item.csv
Environment=SOLD_BY_MAX_AGE=7
ExecStart=/bin/bash /opt/DungeonsForever/scripts/run_daily.sh
```

`/etc/systemd/system/gen-vendors.timer`：

```ini
[Unit]
Description=Run gen-vendors daily

[Timer]
OnCalendar=*-*-* 04:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gen-vendors.timer
systemctl list-timers gen-vendors.timer     # 看下次执行时间
journalctl -u gen-vendors.service -n 50     # 看最近日志（也在 scripts/logs/）
```

或 crontab（先 `chmod +x scripts/run_daily.sh`）：
`30 4 * * * ITEM_CSV=/data/item.csv SOLD_BY_MAX_AGE=7 /opt/DungeonsForever/scripts/run_daily.sh`

### 3. 更新后同步回本机

产物是仓库内文件：`scripts/out/vendors.csv` 和 `scripts/out/npcs.csv`。
服务器在 git 仓库里跑时设 `PUSH=1` 自动提交推送；否则每天拉取这两个文件即可。

### 4. 备选：headless 被 wowhead 拦时

服务器 IP 常被 CloudFront 重点照顾。若日志频繁出现「封禁冷却」：
- 给服务器配 `DF_PROXY`（住宅/动态出口）；
- 或分工：Windows 本机（Chrome 有头）负责抓 `Sold by`，服务器只跑合成——
  本机 `python scripts/gen_vendors.py … --csv-out vendors.csv --npcs-out npcs.csv`，
  直接产出同款 CSV。
