# 数据维护入口与来源索引

专业统一入口与外部输入见 [SCRIPT_INPUTS.md](SCRIPT_INPUTS.md)，70450候选安装包的检查结果见 [CSV_CHECK_REPORT.md](CSV_CHECK_REPORT.md)。
70450正式发布与最新安装包见 [PUBLISH_70450.md](PUBLISH_70450.md)。
人工维护记录及新增相对位置见 [MANUAL_MAINTENANCE.md](MANUAL_MAINTENANCE.md)。
按模块列出的完整保留清单见 [MAINTENANCE_FILES.md](MAINTENANCE_FILES.md)。

正式插件数据位于仓库根 `Core/Data/`。工具包不再跟踪重复运行样例；需要独立工具工作副本时，在仓库根运行 `python -B df-data-pipeline/prepare_workspace.py`。它复制当前正式数据及语言目录到 `df-data-pipeline/Core/Data/`，任一目标已存在则拒绝覆盖。生成结果应从生成器或维护输入修订；没有完整生成器的增量维护表仍须保留当前正式基线。

- 下表列出保留的生成器、采集器及人工输入。除专业统一链与下面的路线保存链外，不代表已验证的一键更新顺序。
- 「增量维护」表示仍依赖正式基线或手工来源，不能删除这些数据后只靠一个脚本重建。
- 旧独立工具仍可能含固定 D 盘路径、浏览器 CDP、代理或外部插件要求。执行前核对代码里的输入输出，将写入目标限定在当前仓库；准备工作副本不会批量修复这些路径。
- 本地化词典、人工坐标、路线基线及 override、已保存且无法离线重采的来源继续跟踪。已完成 UI 构建、迁移、定点补丁、旧轮次探针和部署工具已移除，历史通过 Git 查询。

## 来源代号

| 代号 | 来源及边界 |
| --- | --- |
| CLIENT | 游戏客户端 CSV/DB2 或外部插件的数据，如 ClassQuestsForever、Questie、BGLite；必须核对客户端版本。外部安装目录仅可只读取源。 |
| FOREVERCHANGES | `foreverchanges.pro` 的页面及 RSC 数据；保留采集和解析入口，专业刷新按统一入口管理。 |
| WOWHEAD | NPC、物品、任务、法术 tooltip 及页面/评论；部分旧采集器依赖代理或浏览器 CDP。 |
| WUXIANWOW | 任务页面及 JSON，供中文名称补充；不能用名称来源替代任务可用性证据。 |
| WAGO | `wago.tools` 的客户端表数据，如 AreaTable；需要匹配构建版本。 |
| 手工 | 坐标校准、路线编辑、翻译、说明和规则；这些输入不可当作抓取缓存删除。 |

---

## 一、副本结构

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_Dungeons.lua` | 增量维护，保留正式基线 | 手工整理 + CLIENT 副本 id |
| `Data_DungeonEntry.lua` | `gen_dungeon_entry.py` | CLIENT 地图坐标 + 手工校准 |
| `Data_MapPins.lua` | `fc_pins.py`（含 `_route_qicons.py` / `_route_write_pins.py` 分支） | 手工标注 + 路线编辑器导出 |
| `Data_Route.lua` | `gen_route_lua.py`，路线编辑保存见下文 | `_route_plan/data/` 路线基线 + `_route_override.json` |
| `Data_AreaMap.lua` | `gen_area_map.py` | WAGO 的 AreaTable + CLIENT |

## 二、首领

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_BossModel.lua` | `gen_boss_model.py` | WOWHEAD NPC 模型 id |
| `Data_BossPos.lua` | `gen_boss_pos.py` | WOWHEAD 地图坐标 + 手工校准 |
| `Data_BossSkills.lua` | `gen_boss_skills.py` | WOWHEAD 法术 id + 自写说明 |

## 三、掉落 / 装备

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_DungeonLoot.lua` | 增量维护；`_df_wh_align.py`、`_fc_loot_apply_1007b.py` 保留来源合并能力 | WOWHEAD 掉落表 + FOREVERCHANGES；先检查具体合并范围 |
| `Data_Gear.lua` | `gen_gear_src.py` → `gen_gear_pack.py` / `gen_gear_scrape.py` | FOREVERCHANGES + WOWHEAD |
| `Data_GearVendors.lua` | `gen_gear_vendors.py` | CLIENT 商人 NPC + 手工 |
| `Data_GearRareSpawns.lua` | `gen_gear_rare.py` | CLIENT 稀有刷新点 |
| `Data_RaidSets.lua` | `gen_raidsets.py` | FOREVERCHANGES 套装 |
| `Data_BIS.lua` | `fc_bis.py` | FOREVERCHANGES |
| `Data_ProfItems.lua` | `fc_prof_items.py`，统一入口同批发布 | 商人/NPC/客户端CSV；替代已停用旧商人报价表 |
| `Data_Plunder.lua` | `gen_plunder_data.py` | CLIENT 掠夺品 |
| `Data_Crates.lua` | `gen_crates_data.py` | CLIENT 箱子 |
| `Data_LootFilter.lua` | 多脚本增量维护 | 手工规则（分类/品质/职业） |

## 四、任务

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_DungeonQuests.lua` | 多脚本增量维护（`_wh_qend_batch.py` / `fc_quest_gap_classify.py` …） | WOWHEAD 任务 + CLIENT |
| `Data_QuestStartNpc.lua` | `gen_quest_start_npc.py` | CLIENT 任务给予者 |
| `Data_QuestStartLoc.lua` | `gen_quest_start_loc.py` | CLIENT NPC 坐标 |
| `Data_QuestEndNpc.lua` | `gen_quest_end_npc.py` | CLIENT NPC 坐标 |
| `Data_ClassQuest.lua` | `gen_class_quest.py` | CLIENT(ClassQuestsForever) + WOWHEAD 评论 |
| `Data_FactionQM.lua` | `gen_faction_qm.py` | CLIENT 阵营军需官 |

## 五、职业 / 配装

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_ClassGuide.lua` | `fc_guide.py` | FOREVERCHANGES |
| `Data_ClassCombat.lua` | `gen_class_combat.py` | CLIENT 法术书 + 手工循环 |
| `Data_ClassTier.lua` | `fc_tier.py` | FOREVERCHANGES |

## 六、专业（当前受管链）

统一入口 `_temp/fc_update.py`；当前维护输入、输出、语言及事务说明见 `README.md`。每个活动脚本的文件输入见 [SCRIPT_INPUTS.md](SCRIPT_INPUTS.md)。五份CSV默认读取本包`_temp/_fc/inputs/`，不调用外部生产脚本。当前六表由 `fc_gen.py` 合并版本化维护规则生成；下表的来源辅助脚本说明数据来历，不是统一入口之外的必跑步骤。

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_Professions.lua` | `fc_gen.py`（总控 `fc_update.py`） | FOREVERCHANGES |
| `Data_ProfRecipes.lua` | `fc_gen.py` | FOREVERCHANGES |
| `Data_ProfLeveling.lua` | `fc_gen.py` | FOREVERCHANGES |
| `Data_ProfGathering.lua` | `fc_gen.py` | FOREVERCHANGES |
| `Data_ProfVendors.lua` | `fc_gen.py` + 同轮 `fc_prof_items.py` | 维护规则、FOREVERCHANGES、冻结 NPC CSV |
| `Data_ProfTrainers.lua` | `fc_gen.py` + 版本化训练师维护输入 | CLIENT 训练师 NPC 的已保存来源 |
| `Data_ProfSpecializations.lua` | `fc_refresh_specializations.py` 准备后统一发布 | DB2图纸、有效配方目录、训练师网页及审计 |
| `Data_ProfMaterialSupply.lua` | `fc_material_vendors.py`，统一入口同批发布 | 独立材料商人供货证据与货架价格 |
| 专业六表 zhTW/enUS | `fc_locales.py` | 同轮基础数据、术语表及人工语言维护输入 |

## 七、收藏 / 探索 / PvP / 杂项

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_CollectionMounts.lua` | `_gen_mounts_apply.py` / `_gen_mounts_npcs_apply.py` 为辅助构建器，原替换锚点需核对 | CLIENT + WOWHEAD + 手工；保留正式基线 |
| `Data_CollectionPets.lua` | `_build_pets_src.py`；`_build_collection_pets.py` 为新增条目辅助 | CLIENT + WOWHEAD + 手工 |
| `Data_Explore.lua` | `explore_gen.py` | CLIENT + 手工坐标 |
| `Data_ExploreBanner.lua` | 基础数据增量维护；`enus_data_banner.py` 仅提供英语词典 | 手工 |
| `Data_ExplorePets.lua` | 多脚本增量维护 | 手工 |
| `Data_ExploreToys.lua` | 基础数据增量维护；`enus_data_toys.py` 仅提供英语词典 | 手工 |
| `Data_PvPSets.lua` | `gen_pvp_data.py` | FOREVERCHANGES + CLIENT |
| `Data_PvPRanks.lua` | `gen_pvp_data.py` | FOREVERCHANGES |
| `Data_PvPHonor.lua` | `gen_pvp_honor.py` | FOREVERCHANGES + 手工系数 |
| `Data_Factions.lua` | `gen_factions_data.py` | CLIENT 阵营表 |
| `Data_NPCLoc.lua` | 增量维护；保留 `_fetch_wh_wotlk_npcloc.py` 等来源采集器 | CLIENT NPC 坐标 + WOWHEAD + 手工校准 |
| `Data_NameOverrides.lua` | 版本化人工覆盖；旧清洗脚本已完成 | 手工覆盖 |

> `Data_SpellBook` 是扫描脚本 `gen_spells_from_book.py` 的中间产物，不单独成表。

---

## 路线编辑与保存

在仓库根运行：

```powershell
python -B df-data-pipeline/prepare_workspace.py
python -B df-data-pipeline/_temp/_route_serve.py
```

已有工具工作区时跳过第一条，准备命令不会覆盖它。打开 `http://127.0.0.1:8766/tune.html` 编辑并保存。保存链使用当前解释器和仓库相对路径，拒绝路径逃逸及符号链接/junction；不会部署到客户端。

- 保存路段、标记、任务图标、提示及隐藏状态到 `_route_override.json`、`_route_qicon_override.json`、`_route_qtip_override.json`、`_route_qi_hide.json`。编辑页提交当前副本完整楼层快照，保留未编辑楼层和其他副本的已有修改；`floors` 接口不接受只发一层的增量补丁语义。
- 任务图标变动由 `_route_write_pins.py` 写入工具工作区的 `Data_MapPins.lua`，再由 `_route_qicons.py` 刷新图标清单。
- `_route_make_tune.py` 将当前 override 注入编辑页；重新打开页面时覆盖 `_route_plan/data/index.json` 中的旧坐标。保存不重写路线基线。
- `amp` 自动扰动使用基线中保留的原始点和首领锚点，复用 `_route_gen.py` 的几何算法；页面和 Lua 使用同一重放结果，手工 `pts` 与删段优先。同层多条主路线的重复段号按原顺序保留，同一参数作用于所有同号自动段。缺少原始点或基线不能对应时，在写入前报错。
- 保留原有自动导出条件：保存 `blackfathom_deeps` 时运行 `gen_route_lua.py`。保存其他副本会持久化编辑，但不会自动运行 Lua 导出；需要导出时显式运行 `python -B df-data-pipeline/_temp/gen_route_lua.py`。该生成器合并全部已保存路线与 override，写入工具工作区的 `Data_Route.lua`。
- 正式 `Core/Data/` 不由这条保存链写入。比较、验证工具工作区结果后，再把确认的变更纳入正式数据。

`_route_build_all.py` → `_route_gen.py` 是独立的原始路线导入工具，依赖外部 ForeverDungeonRoutes 的 `DefaultRoutes.lua` 及原路径设置；`_route_bake_maps.py` 另依赖地图源文件。它们用于有来源变更时重新导入，不是保存按钮的步骤。调用前核对路径、来源及手工输入；不要为了保存一次编辑而重采全部路线。

## 其他模块的维护顺序

| 模块 | 入口与保留原因 |
| --- | --- |
| 职业任务 | `gen_class_quest.py` 读取任务/任务链和人工 `_cq_notes.json`；`_cq_comments_fetch.py`、`_cq_forever_fetch.py` 采集评论，`_cq_comments_prep.py` 清洗后由人工提炼说明。`_cq_*` 名称、NPC、物品采集器是来源补充；客户端路径与浏览器条件需先确认。 |
| 副本与攻略 | `_fc_dg_fetch_all.py` → `_fc_dg_parse.py`、`_fc_fights_parse.py`、`_fc_hidden_parse.py` 保留站点导入能力；`_df_wh_guide_scrape.py` → `_df_wh_guide_parse.py` / `_df_wh_guide_gen.py` 保留 WOWHEAD 攻略链。采集结果需审核后进入正式表。 |
| 首领模型、坐标、技能 | `gen_boss_model.py`、`gen_boss_pos.py`、`gen_boss_skills.py` 读取已保存来源；`lootified_bosspos.py`、`_df_pin_refetch.py`、`_df_pin_floors2.py` 负责补源。手工楼层/坐标与 `_wh_guide_raw.json` 中的人工技能不可重新抓取覆盖。 |
| 配装与掉落 | `gen_gear_src.py`、`gen_gear_scrape.py` 采集/整理后按目标格式使用 `gen_gear_pack.py`；打包器有输入格式要求，不能把已打包数据反复当作原始输入。`fc_bis.py` / `fc_bis_zh.py`、`gen_raidsets.py` 分别维护 BIS 与套装。 |
| 职业指南与战斗 | `_cg_fetch.py` / `_cg_fetch_all.py` → `_cg_parse_guide.py` → `fc_guide.py`；`gen_class_combat.py` 依赖 `cc_*` 模块及 `rot_zh_notes.py`。保留已解析来源，原网页或客户端输入未准备时不能把它当作可删缓存。 |
| 探索与收藏 | `explore_fetch.py` → `explore_parse.py` / `explore_resolve.py` → `explore_gen.py`；宠物保留 `_pets_fetch.py` / `_pets_parse.py` / `_pets_pins.py`，坐骑保留 `_wh_mount*` 来源处理器。人工坐标继续作为输入。 |
| 普通本地化 | `gen_enus.py` / `gen_zhtw.py` 处理界面语言，`gen_enus_data.py` / `gen_zhtw_data.py` 处理数据语言；`enus_data*.py` 为实际导入的人工词典。专业六表语言仍走 `fc_locales.py`，中文界面源继续维护 `Locales/zhCN.lua`。 |
| 专业辅助采集 | `fc_enchant_ids.py`、`fc_vendors.py` / `fc_vendors_resolve.py`、`fc_vendor_side.py`、`fc_zh_sync.py` 与保留的 `prof_trainer_*` 收集尚无替代的来源。它们不是统一入口之外的必跑步骤；训练师辅助输出须审核后纳入当前 maintenance 输入。 |
| 图标与格式 | 保留图片生成器和 `strip_comments.py` / `strip_lua_comments.py` 等可复用工具。运行前检查目标与写入模式；已有正式资源仍随插件打包。 |

## 清理边界

跟踪运行必需文件、当前维护脚本及其实际依赖、冻结输入、人工维护内容与测试夹具。可重采的网页缓存、日志、构建副本和可重建派生报告由忽略规则管理；清理前必须有对应生产者及明确重建顺序。只有历史注释/旧测试提及的脚本不再作为保留理由。

旧专业包、重复归档、已完成 UI 构建、迁移、定点修复和部署脚本不再保留在当前树；需要研究历史时通过 Git 查询，不作为当前运行入口。当前跟踪名单可运行 `git ls-files df-data-pipeline/_temp` 查看，历史文件数量不作为完整性契约。
