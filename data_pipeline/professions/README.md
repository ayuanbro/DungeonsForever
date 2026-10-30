# Forever 专业学习资料流水线

急救现已纳入来源发现和统一运行时校验。32条制作配方的生成、字段证据、定向发布及剩余学习来源缺口见[急救数据修复](../../docs/first-aid-data-20261030.md)。`publish_profession`仅负责保留未选中专业并发布指定专业的新生成记录，不参与采集或用旧文件填补来源缺失。

此包从 Wago 的 **Forever (`wowf`) 最新版本**重新发现专业技能和教材关系，再获取 Wowhead Forever 的技能、教材、任务和 NPC 证据。生成器不读取原有 Lua、modularization 目录、历史候选 JSON、数据库字节码或本地客户端。

原始 CSV/HTML 是可复现输入；新下载过程中暂存的同版本原始响应可以恢复。生成后的 Lua、审计报告与旧配方目录均不能替代来源输入。

当前规则6支持各专业的明确自动技能奖励，以及金币/通货/物品兑换的教材商人来源。教材职业掩码若已覆盖同版本全部职业，不再因预留职业位被判为未知；受限且含未映射位的掩码仍保留未知。明确列出的商人、任务或掉落不再标成获取来源缺失，获取条件的未知状态仍保留。自动习得门槛通过独立索引应用于运行时视图，原始Data和黄/绿/灰节点不变；角色条件继续按完整路径检查。8项游戏实测确认及验证见[自动习得门槛修正](reports/automatic-skill-ranks-2026-10-30.md)，逐专业来源清单见[来源修正记录](reports/source-origins-2026-10-30.md)，规则6及采购提示修复见[配方采购问题记录](../../docs/profession-formula-purchase-fix-20261030.md)。

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
- `fetch --out DIR`：取得 `GET https://wago.tools/api/builds/wowf/latest`；固定产品、版本和 build config，下载 22 张相关 DB2 表，发现教材及世界来源。默认两个处理 worker，全局网页实体请求间隔 1 秒，临时错误最多尝试 3 次。同一主机请求由共享调度器串行发出；前一个响应的解析和写盘可以与下一次网络等待重叠。
- `build --raw DIR_OR_ZIP --output LUA --report JSON`：检查版本、输入身份、SHA-256、CSV 列与关联，再独立生成补充 Data 和审计报告。不会修改旧配方数组或添加新的原生制作配方。若输出目录名是 `Data`，仅允许写 `Data_ProfLearningSources.lua`。
- `check`：同样参数，重新构建并逐字节比对现有 Lua 和报告，失败返回非零退出码。

正式采集前后都复查 Wago latest；版本变化会保留原批次并重新采集，连续三批变化则失败。关键 DB2 的访问、表头、请求版本或校验不通过时，不生成正式产物；网页缺失和受阻允许保留明确缺口。

`fetch` 默认不覆盖已存在的原始包。中断后使用 `--resume` 恢复 `<DIR>.partial`。同一版本已结束的采集如需稍后重试受阻、解析错误或未完成页面：

```sh
python -m data_pipeline.professions fetch --out dist/prof-learning/raw \
  --resume --retry-failed
```

`--retry-failed` 包含实际 404 的再次核对，不能把旧 404 当作永久删除证据。需要完整刷新网页（含旧成功页、历史失败与旧引用）时使用：

```sh
python -m data_pipeline.professions fetch --out dist/prof-learning/raw \
  --resume --refresh-web
```

已知普通 HTTP 会被校验或拒绝时，可从第一次请求开始使用原生浏览器，并显式降低实体请求频率。以下命令仍可在无 GUI 的 Linux 运行：

```sh
python -m data_pipeline.professions fetch --out dist/prof-learning/raw \
  --resume --refresh-web --web-transport browser --workers 1 --web-interval 2
```

`auto` 是默认传输；`browser` 不先发送 curl 请求，不把浏览器 Cookie 复制到另一套网络栈。请求 URL 优先采用本次同版本 Wago 名称，或本轮已验证关系列表中的名称，减少多余跳转；名称只作 URL 提示，实体仍按最终类型、ID 和正文校验。浏览器等待主文档响应后读取完整正文，不等待广告脚本的页面生命周期事件。连续失败保护在两种模式下均生效。

该命令从可携带的原始包目录启动新一轮网页刷新，不读取旧 Lua 或生成报告。相同 `.partial` 中断后使用同样命令继续本轮，已经实际完成的成功页和 404 不从头重抓。旧网页原始响应保留为扁平 `attemptHistory` 并逐个校验、归档；刷新失败或未请求时不会回退使用旧成功页生成。采集只追踪明确支持的教学、商人、掉落及奖励关系，迭代到队列闭包，不再使用固定四层截断，也不遍历任意站内链接。

恢复先验证已有响应校验值及最新版本，保留已验证原始响应，不读取生成文件。`--web-limit N` 只限制当前调用新发出的网页实体请求，适合小范围探测；正式全量采集不要设置。连续两次来源拒绝或传输失败会打开当前调用的主机熔断器。新版默认最多进行两次冷却恢复（`--host-recoveries 2`），每次至少等待 120 秒（`--host-cooldown 120`），然后只放行一个探测请求；探测失败立即再次熔断。达到上限后，未发送请求的实体记为 `notFetched`、`attempted=false`、`errorCode=hostCircuitOpen`。`--host-recoveries 0` 保留立即停止模式。交互验证码直接停止自动恢复。若已有实际 HTTP 响应，保留原证据并将未发送的重试写入 `lastAttempt`。

`Retry-After` 按不区分大小写的响应头读取，支持秒数和 HTTP 日期，不再把服务器要求的等待缩短为 30 秒。等待约束也作用于下一个实体，其他 worker 不能提前穿过等待窗口。冷却恢复次数在本次调用内有硬上限，成功不会重新填满次数；原失败实体继续保留失败证据，最后可用定点重试再次核对。

每 25 个网页实体保存 manifest 检查点。`fetchComplete=true` 只表示本批次已关闭并复查版本；**不是资料完整证明**。请查看 `sourceCoverageComplete`、每条响应状态和生成报告中的逐专业缺口。

`webRun` 保存本轮 `targetCount`、`attempted`、`notAttempted`、各状态和跳过原因；`requestCoverageComplete` 仅表示本轮全部已发现目标都已实际尝试，包含连接失败的 `sourceError`，不代表全部取得正文或字段齐全。`sourceCoverageComplete` 表示当前响应都通过解析验证，仍不证明学习条件与获取条件完整，最终还须检查生成报告的逐项缺口。

允许离线复用同一原始包、同一 Wago build/config 的旧批次 verified 页面：

```sh
python -m data_pipeline.professions reuse-verified --raw RAW_DIR --report reuse-and-source-gaps.json
python -m data_pipeline.professions status --raw RAW_DIR
```

命令从原始清单发现候选，校验 DB2、网页 SHA-256、实体身份及当前解析器结果后登记复用，不使用旧生成 Lua，也不联网。原 `webRunID`、采集时间和请求历史保留。`newlyRequested` 等于原 `attempted`；`reused` 单列，二者不重复；`covered=newlyRequested+reused`，`uncovered=targetCount-covered`。`notAttempted` 仍表示本轮未发送请求的数量，包含复用项；`requestCoverageComplete` 不因复用而变为 true。`acquisitionCoverageComplete` 表示全部目标均被本轮尝试或有效复用，失败响应仍在 sourceGaps 中。报告分别列出来源缺口、未新抓且未复用的实体，以及复用证据。状态或 SHA/build/config 改变会使旧复用登记失效。

对已关闭但请求未覆盖完整的目录，`fetch --resume` 可恢复原 acquire 批次并跳过已接受的复用；显式 `--refresh-web` 则重新请求旧批次页面。规则3支持安全读取对象字面量中未加引号的键与单引号字符串，并在生成物内部共享重复的嵌套来源描述；不会执行网页 JavaScript，也不改变 provider 的公开结构。

规则3的完整审计 facts 保留全部掉落 NPC 证据。运行时投影不携带该完整名单，改为 `dropSourceCount` 和 `dropDetailsOffline`；教材、学习路径、条件、训练师、任务、商人报价及非拍卖限制仍保留。投影不会提供 `acquisition.drops` 覆盖 dev 原有掉落资料，也不会把未知获取方式确认成可执行采购。运行时指纹基于实际投影事实，原始包与完整审计可离线复查全部名单。`tests/verify_generated.py --data LUA --audit JSON --output JSON` 在 Lua5.1 中逐项对比所有运行时公开字段。

全量请求已完成后，可以只复核本轮某个被拒绝的 HTTP 状态，而不重新请求成功页、404 和解析错误页：

```sh
python -m data_pipeline.professions fetch --out dist/prof-learning/raw \
  --resume --retry-current-http 403 --web-transport browser --workers 1 --web-interval 2
```

该模式仅接受 `403`、`429`、`202`，输入须有已完成的全量请求记录，且 latest 版本和 build config 仍一致；不能与 `--refresh-web` 或 `--retry-failed` 混用。它保留本轮 ID 和全量覆盖记录，在 `webRun.currentHttpRetry` 及分段记录中单列选中项、实际尝试项与新发现关联。`currentHttpRetry.complete` 表示这次定点操作已全部尝试，不代表全部成功。若重试被保护机制跳过，原始真实拒绝证据保留，未发送的重试另记，不把它算作成功或新的实际请求。

仅 ZIP 封包失败、原始目录已经完成时，可以离线重建归档，不需要重新采集。封包会核对当前及历史响应的路径和 SHA-256，写好临时 ZIP 后再替换：

```sh
python -c 'from pathlib import Path; from data_pipeline.professions.fetch import snapshot_archive; p=Path("dist/prof-learning/raw"); snapshot_archive(p, p.with_suffix(".zip"))'
```

## 来源判定和保留边界

HTTP 202/WAF 校验页、403、429 为 `sourceBlocked`；连接或超时异常为 `sourceError`；真实实体 404 为 `sourceMissing`；结构或实体不匹配为 `parseError`。最终 URL、实体标题、类型和技能 ID 必须一致。跳转后的通用列表即便带有 `WH.Gatherer` 也不能作为目标实体。

普通 HTTP 请求保留 curl 配套的浏览器请求头，不再硬写另一个浏览器版本。遇到 JavaScript 校验时，切到专用线程持有的 Chromium 匿名会话；UA 从实际浏览器版本派生，校验与后续取页面都使用浏览器自己的网络栈。Cookie 不再转交给另一套 HTTP 客户端，也不再把浏览器请求拦截后交给 curl。所有浏览器操作与关闭都在同一个所属线程执行；采集结束或失败时释放资源。交互验证码不自动点击或求解，普通 403 拒绝也不冒充 JavaScript 校验。

解析器只读取 JSON 字面量和页面中的条件文字，不执行来源提供的任意数据脚本。种族优先使用页面明确 ID 或当前 `ChrRaces.PlayableRaceBit` 映射；未映射位、模糊的采集 mask、非零的未验证 PlayerCondition 及其他未支持条件保持未知。Python 保留大整数精度；生成到 Lua 的整数必须处于安全范围，Lua 解码不依赖平台的 `strtoul` 或浮点大数位运算。规则 2 将 DB2 `MinReputation` 的 0..7 转为客户端 `reaction` 的 1..8；缺失、空值与越界不当作有效门槛。这是字段索引转换，不修改 dev 原始数值。

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

采集会话恢复、规则 2 声望修正及最新有限实测见 [2026-10-29 修复记录](reports/recovery-2026-10-29.md)。历史验收记录保留原范围，不能当作新版本已完成全量采集的证明。

可选的原生数据对比只在生成后运行，不参与采集、补缺或生成：

```sh
python data_pipeline/professions/tests/audit_native_conflicts.py \
  --report dist/prof-learning/report.json --output dist/prof-learning/native-conflicts.json
```

性能复测脚本为 `tests/benchmark_delivery.py` 和 `tests/benchmark_callbacks.py`。前者的 `--baseline` 接受修改前源码快照，用于对比而非来源输入；后者需明确指定专业、目标和运行上限，避免无限搜索。所有场景为离线模拟客户端，真实游戏验收单独进行。

## 采集效率改进与批次结束后的在线对照

新版使用有界任务窗口，同时保留的 future 数量不超过 worker 数；新响应只解析一次，解析结果在内存中交给关系发现，不写进原始包。已保存响应在恢复时仍重新校验和解析，不把临时解析缓存当成可复现输入。每个运行分段记录恢复次数、等待时间、最终 HTTP 状态计数和浏览器一致性诊断。诊断不修改浏览器属性，也不宣称自动化不可识别。

两项试验能力默认关闭：

- `--web-transport browser-fetch`：第一次使用完整导航建立浏览器会话，后续在同一原生浏览器、同一来源内读取完整响应字节；JavaScript 校验或读取失败最多回退一次原生导航，普通 403 交给主机调度器。最终 URL、实体和正文仍经过相同解析校验。
- `--browser-assets light`：只阻断图片、字体和媒体，保留文档、脚本、样式和校验请求。Playwright 路由会关闭 HTTP 缓存，因此该模式必须比较冷、热两遍的传输开销，不能仅凭图片请求减少判断更快。

现有采集进程不会热重载这些改动；不要为了应用新版中断当前批次。批次完成后，在 Linux 环境显式运行：

```sh
env -u DISPLAY -u WAYLAND_DISPLAY .venv/bin/python -m data_pipeline.professions compare \
  --after-raw .pipeline-runtime/prof-learning-full-20261029 \
  --out dist/prof-learning/transport-comparison-20261029 \
  --limit 12 --rounds 2 --interval 2
```

`compare` 是一次性命令，不启动监控或定时任务。它在任何联网前检查原批次全量请求已完成、归档与目录 manifest 一致，并通过 Linux `/proc` 排除仍运行的采集/对照进程；未满足条件就退出，原始包不变。在线前后复查 Wago latest，版本变化则不接受结果。输出目录必须全新且独立，任何对照数据都标记 `generationInput=false`。

对照固定相同样本、请求间隔、解析器和浏览器版本，比较原生导航、同会话轻量读取和资源裁剪三种方式；样本覆盖实体类型及来源失败类型，两轮交换执行顺序，每组分别进行冷、热两遍。遇到拒绝或连接错误保存已获得的证据并停止整场对照，不通过更换会话继续刷出更高成功率。

`report.json` 记录有效资料/分钟、验证通过率、受阻率、耗时、网络请求数、传输字节、缓存命中、浏览器一致性信息，以及逐实体字段/状态差异。网络字节来自页面目标 CDP，包含该目标的子资源，但不包含其他目标和协议开销；这是明确范围的流量指标，不等同于系统总流量。未出现真实 202 校验则标记 `challengeObserved=false`，不能宣称校验兼容性已通过。对照只度量传输模式，不冒充旧、新整个流水线的端到端性能比较，也不会自动改变默认配置或正式 Data。
