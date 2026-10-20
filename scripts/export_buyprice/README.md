# Forever 物品及三语基础购买价 CSV 导出

从仓库根目录运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\export_buyprice\export-item-buy-prices.ps1"
```

从其他目录启动时使用脚本绝对路径。兼容 Windows PowerShell 5.1，无需安装 Python。默认使用 `C:\Users\yewei\Downloads\Release-win-x64\wow.tools.local.exe` 和 `http://127.0.0.1:5000`：服务已启动则复用，未启动则隐藏启动；结束时只关闭本次启动的进程。

## 输出

文件写入脚本旁的 `output/`，均使用 UTF-8 BOM：

| 文件 | 内容 |
| --- | --- |
| `item.csv` | 当前 Item 表的完整字段与记录，包括 `ID`、`ClassID`、`SubclassID`；保持工具返回的原始列，供上层 `gen_vendors.py` 筛选配方物品 |
| `item-buy-prices.csv` | 合并 enUS、zhTW、zhCN 名称及 ItemSparse 的原始基础购买价、组数、状态和版本 |

三语价格表字段：

```text
ItemID,Name_enUS,Name_zhTW,Name_zhCN,BuyPriceCopper,VendorStackCount,PriceStatus,Build,HotfixBuild
```

`BuyPriceCopper` 保留数据库整组购买价，不除以 `VendorStackCount`。`PriceStatus` 区分 `priced`、`zero`、`missing_item_sparse`；缺少数据的数值留空。缺少某种语言名称时留空，不用英文替换。价格为零不表示免费，基础价也不证明任何 NPC 实际出售、无限量供应或角色折扣。

脚本只输出 CSV，不生成 Lua，不导入插件或写入游戏安装目录。插件中的旧 NPC 购买价格已删除，当前仅保留供货/位置/库存性质等非价格资料，等待重新设计购买价格方法；商人窗口不采价，Auctionator 的 AH 行情与数量继续保留。

## 数据校验与运行规则

每次读取本机当前加载的 Forever build，下载最新 `classic_beta` Hotfix，并核验本次新缓存的文件头、版本及 SHA-256。下载失败、没有新缓存、损坏或 build 不匹配时停止，不使用旧缓存冒充成功。

重载 Hotfix 后只导出一次 Item，再依次读取 enUS、zhTW、zhCN 的 ItemSparse。所有请求串行，显式指定 build、locale 与 `useHotfixes=true`；三语价格和组数必须一致。两个输出都验证成功且版本/缓存未变才发布；第二个文件发布失败时回滚第一个，保留旧输出。回滚若被操作系统阻止，会报错并保留备份供恢复。

导出期间避免在 wow.tools.local 页面切换版本或手动重载缓存。不同缓存按 Hotfix PushID 合并，下载文件不等同于完全独立的数据库快照。控制台和 `output/logs/` 记录版本、缓存哈希、行数及名称缺失数量。输出和日志不进入 Git；同一服务或输出文件的并发导出会被阻止。

## 参数

所有相对路径均相对于脚本目录，不受当前工作目录影响：

```powershell
.\scripts\export_buyprice\export-item-buy-prices.ps1 `
  -ToolDirectory 'C:\Users\yewei\Downloads\Release-win-x64' `
  -BaseUrl 'http://127.0.0.1:5000' `
  -OutputPath 'output\item-buy-prices.csv' `
  -ItemOutputPath 'output\item.csv' `
  -StartupTimeoutSec 180 `
  -RequestTimeoutSec 300
```

后续商人数据工具示例：

```powershell
python scripts/gen_vendors.py --item-db2 scripts/export_buyprice/output/item.csv --plan
```

## 离线回归

测试使用模拟 HTTP 服务及临时目录，Python 仅为开发测试依赖：

```powershell
python -m unittest discover -s tests -p 'test_item_price_export.py' -v
```
