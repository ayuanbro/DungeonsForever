# Forever 专业学习资料流水线

此包从 Wago 的 **Forever (`wowf`) 最新版本**重新发现专业技能和教材关系，再获取 Wowhead Forever 的技能、教材、任务和 NPC 证据。生成器不读取原有 Lua、modularization 目录、历史候选 JSON、数据库字节码或本地客户端。

原始 CSV/HTML 是可复现输入；新下载过程中暂存的同版本原始响应可以恢复。生成后的 Lua、审计报告与旧配方目录均不能替代来源输入。

## Linux 无图形环境运行

推荐容器入口。基础镜像按摘要固定，Python 包包括传递依赖均以版本和发布文件 SHA-256 锁定；Playwright 包与浏览器版本一致。

```sh
docker build -f data_pipeline/professions/Dockerfile -t df-prof-learning .
mkdir -p dist/prof-learning
docker run --rm -v "$PWD/dist/prof-learning:/output" df-prof-learning \
  fetch --out /output/raw
docker run --rm -v "$PWD/dist/prof-learning:/output" df-prof-learning \
  build --raw /output/raw.zip \
  --output /output/Data_ProfLearningSources.lua --report /output/report.json
docker run --rm -v "$PWD/dist/prof-learning:/output" df-prof-learning \
  check --raw /output/raw.zip \
  --output /output/Data_ProfLearningSources.lua --report /output/report.json
```

也可以使用 Python 3.12+ 虚拟环境：

```sh
python -m venv .venv
.venv/bin/pip install --require-hashes -r data_pipeline/professions/requirements.lock
.venv/bin/python -m playwright install --with-deps chromium-headless-shell
env -u DISPLAY -u WAYLAND_DISPLAY .venv/bin/python -m data_pipeline.professions \
  fetch --out dist/prof-learning/raw
```

无 GUI、Xvfb 或 Windows 浏览器要求。容器不需要宿主机安装浏览器。Cookie 只存在当前匿名会话内，不保存到源码、manifest、生成 Data 或审计报告。`check` 和离线 `build` 本身只需要 Python 标准库，不联网。

## 命令

- `probe --out DIR`：与正式采集使用相同接口，默认只请求 8 个新发现的网页实体。未请求项记录为 `notFetched`，不能把探测包说成全量覆盖。
- `fetch --out DIR`：取得 `GET https://wago.tools/api/builds/wowf/latest`；固定产品、版本和 build config，下载 22 张相关 DB2 表，发现教材及世界来源。默认两个 HTTP worker，全局网页实体请求间隔 1 秒，临时错误最多尝试 3 次。
- `build --raw DIR_OR_ZIP --output LUA --report JSON`：检查版本、输入身份、SHA-256、CSV 列与关联，再独立生成补充 Data 和审计报告。不会修改旧配方数组或添加新的原生制作配方。若输出目录名是 `Data`，仅允许写 `Data_ProfLearningSources.lua`。
- `check`：同样参数，重新构建并逐字节比对现有 Lua 和报告，失败返回非零退出码。

正式采集前后都复查 Wago latest；版本变化会保留原批次并重新采集，连续三批变化则失败。关键 DB2 的访问、表头、请求版本或校验不通过时，不生成正式产物；网页缺失和受阻允许保留明确缺口。

`fetch` 默认不覆盖已存在的原始包。中断后使用 `--resume` 恢复 `<DIR>.partial`。同一版本已结束的采集如需稍后重试受阻、解析错误或未完成页面：

```sh
python -m data_pipeline.professions fetch --out dist/prof-learning/raw \
  --resume --retry-failed
```

恢复先验证已有响应校验值及最新版本，保留已验证原始响应，不读取生成文件。`--web-limit N` 只限制当前调用新发出的网页请求，适合小范围探测；正式全量采集不要设置。连续两次校验恢复失败会打开当前调用的主机熔断器，剩余实体记为 `sourceBlocked`，避免几千次无意义的 403 请求。稍后再显式重试，不循环刷站。

每 25 个网页实体保存 manifest 检查点。`fetchComplete=true` 只表示本批次已关闭并复查版本；**不是资料完整证明**。请查看 `sourceCoverageComplete`、每条响应状态和生成报告中的逐专业缺口。

## 来源判定和保留边界

HTTP 202/WAF 校验页、403、429、访问超时为 `sourceBlocked`；真实实体 404 为 `sourceMissing`；结构或实体不匹配为 `parseError`。最终 URL、实体标题、类型和技能 ID 必须一致。跳转后的通用列表即便带有 `WH.Gatherer` 也不能作为目标实体。

解析器只读取 JSON 字面量和页面中的条件文字，不执行来源提供的任意数据脚本。种族优先使用页面明确 ID 或当前 `ChrRaces.PlayableRaceBit` 映射；未映射位、模糊的采集 mask、非零的未验证 PlayerCondition 及其他未支持条件保持未知。Python 保留大整数精度；生成到 Lua 的整数必须处于安全范围，Lua 解码不依赖平台的 `strtoul` 或浮点大数位运算。

学习来源采用“多路径任选其一、同路径条件全部满足”。教材学习限制、制作条件与商人/任务/掉落获取限制分别处理。任务奖励或掉落关系不等于免费且保证可得的库存；网页缺详情也不证明游戏内实体删除。商人费用必须有明确 NPC、金币价格和已知 `VendorStackCount`，不把缺失包量补为 1。

商人列表即便有 NPC、金币价格和包量，仍只作为参考报价：单凭这些字段无法确认该角色的任务、阵营、事件或阶段访问资格。因此网页 acquisition 保持未知，由既有明确供应记录或当前角色的实际商人观察独立确认可采购路径。

原生数值优先级在插件适配层处理。生成器保留本次来源事实及审计，不读取原生 Data 来决定数据生成结果。网页 patch 注释是证据元数据，不冒充精确 build 的全字段确认。

## 生成 Data 接口

补充文件只在 `ns.IsForever` 下注册：

```lua
local provider = ns.ProfLearningSources
local info = provider.Get("alchemy", spellID)
local sameInfo = provider.ForProfession("alchemy")[spellID]
for spell, record in provider.Each("alchemy") do
    -- Explicit streaming enumeration; normal lookups do not expand all records.
end
local plain = provider.Materialize(info)
```

`info` 公开字段为 `spell, profession, coverage, routes, missingReasons`；学习路径字段为 `id, kind, status, conditionsKnown, conditions`，以及对应的教材、训练师、任务、费用和 `acquisition`。详细用法以源码和测试中的结构化对象为准。

查询返回只读约定的紧凑视图，以数组、共享条件模板和延迟解码控制内存。请通过命名字段访问，不能把 `pairs(info)` 当作序列化方法。冻结/持久化使用 `provider.Materialize`，或识别 metatable 的 `__profLearningMaterialize(value)` 浅投影，再递归复制。这样保存的历史是普通命名表，不依赖运行时 provider 或今日角色 API。

`ForProfession` 是惰性索引，不立即展开所有参考技能；Lua 5.1 没有 `__pairs`，需要明确枚举时使用 `Each`。生成物指纹不含抓取时间、Cookie、广告或网页动态标识；相同规范化事实具有相同运行时身份。

## 测试与真实覆盖

```sh
python -m pip install --require-hashes -r data_pipeline/professions/requirements-dev.lock
python -m unittest discover -s data_pipeline/professions/tests -p 'test_*.py' -q
# Container source-parser and codec tests:
docker build --build-arg WITH_TESTS=1 -f data_pipeline/professions/Dockerfile -t df-prof-learning-tests .
docker run --rm --entrypoint python df-prof-learning-tests \
  -m unittest data_pipeline.professions.tests.test_source_pipeline -q
```

测试使用合成原始输入覆盖中断、版本变化、错误响应、缺失详情、路径差异、未支持条件、ZIP 路径、精确整数及 Lua 5.1 序列化。它们不是正式生成的旧文件回退。

本次真实采集的源文件覆盖率、逐专业确认路径、缺口与 HTTP 证据以根任务交付的 raw snapshot 和 report 为准。站点受阻时仍可交付来源已确认的部分，但不能宣称完整覆盖；插件严格排除缺少确认学习路径的未学配方。离线检查与真实游戏内学习、采购、执行验收分别报告。

实施记录见 [2026-10-28 验收报告](reports/implementation-2026-10-28.md)，逐专业摘要见 [coverage](reports/coverage-2026-10-28.json)，具体门槛差异见 [native conflicts](reports/native-conflicts-2026-10-28.json)。当前报告保留未通过或未执行的验收项，不能只根据测试数量判断可直接合并。

可选的原生数据对比只在生成后运行，不参与采集、补缺或生成：

```sh
python data_pipeline/professions/tests/audit_native_conflicts.py \
  --report dist/prof-learning/report.json --output dist/prof-learning/native-conflicts.json
```

性能复测脚本为 `tests/benchmark_delivery.py` 和 `tests/benchmark_callbacks.py`。前者的 `--baseline` 接受修改前源码快照，用于对比而非来源输入；后者需明确指定专业、目标和运行上限，避免无限搜索。所有场景为离线模拟客户端，真实游戏验收单独进行。
