# -*- coding: utf-8 -*-
"""2026-10-10 注释红线清理：
1) 所有文件头注释精简为「这个文件是干什么的」；
2) 行内注释清除对其他插件的引用/溯源措辞；
3) Hui.lua 大段历史考证注释压缩为 1-3 行功能说明。
字节级读写，保留各文件原有行尾（LF/CRLF）。
"""
import io, os, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

HEADERS = {
    "Core/AuctionatorBridge.lua": [
        "-- DungeonsForever · Auctionator 购物清单导出桥接",
        "-- 把插件内购物清单经 Auctionator 官方公开 API 推送为其购物清单；",
        "-- 未安装时降级为可复制的导入串弹窗。只对无限服加载。",
    ],
    "Core/BisUI.lua": [
        "-- DungeonsForever · BIS配装页（界面层）",
        "-- 读取 Data_BIS 的配装数据并渲染配装与方案管理；只对无限服加载。",
    ],
    "Core/CollectionUI.lua": [
        "-- DungeonsForever · 藏品页（坐骑 / 宠物）",
        "-- 读取藏品数据表并渲染列表与详情（含 3D 模型展示、NPC 点击定位）；只对无限服加载。",
    ],
    "Core/ExploreMap.lua": [
        "-- 无限副本手册 · 探索页 · 世界地图书钉 + 收集路线 + 追踪条 + 地图设置",
        "-- 独立层，由探索页驱动；帧与线全部池化复用，缺 API 时逐路降级不报错。",
    ],
    "Core/ExploreUI.lua": [
        "-- DungeonsForever · 探索页（界面层）",
        "-- 读取 Data_Explore 的 40 本书数据并渲染打卡进度；只对无限服加载。",
    ],
    "Core/LootFilter.lua": [
        "-- 无限副本手册 · 掉落页「装备过滤」判定引擎   ns.LootFilter",
        "-- 数据 / 引擎 / 界面三层分离；状态全部落在角色级存档。",
    ],
    "Core/LootFilterUI.lua": [
        "-- 无限副本手册 · 掉落页「装备过滤」界面   ns.LootFilterUI",
        "-- 方案图标行 + 配置面板 + 方案弹窗；弹窗父级 = 主窗口。",
    ],
    "Core/MapUI.lua": [
        "-- 无限副本手册 · 详情页「地图」页签（副本内地图 + 首领）",
        "-- 图源 = 客户端自带世界地图瓦片 + 自制手绘地图；左侧地图、右侧首领栏（列表 / 详情）。",
    ],
    "Core/ProfFollow.lua": [
        "-- DungeonsForever · 专业升级 HUD（冲专业 1~300 跟随弹窗）",
        "-- 跟随专业页当前路线逐段提示制作与购物清单，实时跟随技能进度；只对无限服加载。",
    ],
    "Core/ProfRouteAuto.lua": [
        "-- DungeonsForever · 专业升级自动路线（按拍卖行价格）",
        "-- 输入专业与过滤设置，输出与固定路线同构的分段路线与成本汇总；不持有任何 UI。",
    ],
    "Core/ProfessionUI.lua": [
        "-- DungeonsForever · 专业页（界面层）",
        "-- 渲染 13 个专业的总览 / 营地 / 配方 / 采集 / 升级 / Legacy / 说明；只对无限服加载。",
    ],
    "Core/PvPUI.lua": [
        "-- DungeonsForever · PvP 页（界面层）",
        "-- 军衔 / 本周 / 声望 / 套装四个子页，数据来自 Data_PvP*；只对无限服加载。",
    ],
    "Core/QuickBar.lua": [
        "-- DungeonsForever · 主窗口右侧「快捷按钮栏」",
        "-- 常驻窄栏：推荐五人本 / 专业 / 探索快捷入口，随「设置」「装备过滤」弹窗让位换槽。",
    ],
    "Core/RaidUI.lua": [
        "-- DungeonsForever · 团本页（界面层）",
        "-- 时间线 / 列表两个子页，渲染本文件内联的团本排期静态表；全端可见。",
    ],
    "Core/TierUI.lua": [
        "-- 无限副本手册 · 职业指南页（界面层）",
        "-- 职业排行与专精指南的渲染层，数据来自 Data_ClassTier / Data_ClassGuide；只对无限服 / 正式服加载。",
    ],
    "Core/VendorPriceDB.lua": [
        "-- DungeonsForever · 商人直售价动态采集库",
        "-- 打开商人窗口时自动记录货架售价，供升级路线取商人价兜底。",
    ],
    "Core/Data/Data_AreaMap.lua": [
        "-- 无限副本手册 · 区域 ID → 世界地图 ID（areaID → uiMapID）",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 用途：点坐标 / 点区域名 → 打开对应世界地图并落航点。",
    ],
    "Core/Data/Data_BIS.lua": [
        "-- 无限副本手册 · BIS配装（20级 / 30级 两卷 · 各部位最佳装备）",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 只存 ID 与排名；名字 / 图标 / 品质运行期由客户端提供。",
    ],
    "Core/Data/Data_BossSkills.lua": [
        "-- 无限副本手册 · 首领技能表",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 结构：ns.BossSkills[副本 id][首领英文名] = { 行, … }；只存法术 ID，文案运行期问客户端。",
    ],
    "Core/Data/Data_ClassGuide.lua": [
        "-- 无限副本手册 · 职业指南页 · 专精指南",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 结构：ns.ClassGuide.specs[职业][专精] = 板块流（段落 / 表格 / 列表等）；法术名运行期问客户端。",
    ],
    "Core/Data/Data_ClassTier.lua": [
        "-- 无限副本手册 · 职业指南页 · 职业排行",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 结构：ns.ClassTier = 元信息 + 输出 / 坦克 / 治疗 三页排行。",
    ],
    "Core/Data/Data_CollectionMounts.lua": [
        "-- 无限副本手册 · 藏品页 · 坐骑",
        "-- 手写数据：坐骑条目（ID / 分组 / 来源说明 / 模型 ID / 相机距离倍数）。",
        "-- 名字与图标不落盘，运行期问客户端。",
    ],
    "Core/Data/Data_CollectionPets.lua": [
        "-- 无限副本手册 · 藏品页 · 宠物（探索页小动物之外的宠物）",
        "-- 手写数据：行结构与探索页小动物同形（字段顺序即索引）；名字与图标运行期问客户端。",
    ],
    "Core/Data/Data_DungeonEntry.lua": [
        "-- 无限副本手册 · 副本入口坐标（仅无限服：世界地图标记用）",
        "-- 结构：ns.DungeonEntry[副本id] = { uiMapID, x%, y%, 地图名 }；多段指引见 ns.DungeonEntryRoute。",
    ],
    "Core/Data/Data_DungeonLoot.lua": [
        "-- 无限副本手册 · 副本掉落明细（无限版 13–60 级）",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 结构：ns.DungeonLoot[副本 id] = { 掉落来源, ... }；名字 / 品质 / 图标一律由客户端提供。",
    ],
    "Core/Data/Data_DungeonQuests.lua": [
        "-- 无限副本手册 · 副本任务清单（无限版）",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 结构：ns.DungeonQuests[副本 id] = { 任务, ... }。",
    ],
    "Core/Data/Data_Dungeons.lua": [
        "-- 无限副本手册 · 副本数据（无限版 13–60 级）",
        "-- 结构：ns.DungeonData = { dungeons = { { id, name, nameEn, levelMin, levelMax,",
        "--         isNew, zone, bossCount, dropCount, art, bosses }, ... } }",
    ],
    "Core/Data/Data_Explore.lua": [
        "-- 无限副本手册 · 探索页 · 40 本书（图书馆之友）",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 只存 itemID + AreaTable ID + 坐标；书名 / 图标 / 品质 / 区域名运行期由客户端提供。",
    ],
    "Core/Data/Data_ExploreBanner.lua": [
        "-- 无限副本手册 · 探索页 · 血色旗帜（隐藏寻宝）",
        "-- 手写数据，行结构与探索页小动物同形；坐标纪律同宠物页（未明写坐标一律 false）。",
    ],
    "Core/Data/Data_ExplorePets.lua": [
        "-- 无限副本手册 · 探索页 · 小动物（宠物获取）",
        "-- 手写数据。名称与区域名不落盘，运行期问客户端；",
        "-- x / y 只在资料页明写坐标时落盘，否则 false（只开区域地图不落航点）。",
    ],
    "Core/Data/Data_ExploreToys.lua": [
        "-- 无限副本手册 · 探索页 · 玩具（守夜人火炬）",
        "-- 手写数据，行结构与探索页小动物同形；坐标纪律同宠物页（未明写坐标一律 false）。",
    ],
    "Core/Data/Data_LootFilter.lua": [
        "-- 无限副本手册 · 掉落页「装备过滤」静态数据（简体源，加载于所有语言端）",
        "-- 只放常量与预设（子类名 / 职业可用清单 / 词缀 / 预设），不含逻辑。",
    ],
    "Core/Data/Data_MapPins.lua": [
        "-- 无限副本手册 · 副本内地图钉点（入口 / 任务 / 任务物品）",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 坐标 = 地图画布百分比；任务名 / 物品名运行期问客户端，数据侧只存 ID。",
    ],
    "Core/Data/Data_NPCLoc.lua": [
        "-- 无限副本手册 · 起始 NPC 地图坐标",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 用途：任务页点击 NPC 名字 → 地图自动打开该 NPC 所在地图并放下航点。",
    ],
    "Core/Data/Data_NameOverrides.lua": [
        "-- 无限副本手册 · 客户端取名失败的 ID→名称兜底",
        "-- 仅 zhCN 客户端加载；无限服自定义法术 / 物品客户端查不到名字时用本表兜底。",
    ],
    "Core/Data/Data_ProfGathering.lua": [
        "-- 无限副本手册 · 专业页 · 采集节点表",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 只存 ID；名字 / 图标 / 品质 / 区域名运行期由客户端提供。",
    ],
    "Core/Data/Data_ProfLeveling.lua": [
        "-- 无限副本手册 · 专业页 · 升级路线与营地坐标",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 只存 ID；名字 / 图标 / 品质 / 区域名运行期由客户端提供。",
    ],
    "Core/Data/Data_ProfRecipes.lua": [
        "-- 无限副本手册 · 专业页 · 配方与附魔",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 只存 ID 与技能阈值；名字 / 图标运行期由客户端提供。",
    ],
    "Core/Data/Data_Professions.lua": [
        "-- 无限副本手册 · 专业页 · 专业元信息",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
    ],
    "Core/Data/Data_ProfVendors.lua": [
        "-- 无限副本手册 · 专业页 · 商人定位表（配方来源点图用）",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 行字段：{ 区域AreaID, 图uiMapID, x, y }，x/y 为 0..100 地图百分比。",
    ],
    "Core/Data/Data_PvPHonor.lua": [
        "-- DungeonsForever · 荣誉冲刺数据",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 全部纯数字、语言中立；口径与经典旧世荣誉系统一致。",
    ],
    "Core/Data/Data_PvPRanks.lua": [
        "-- 无限副本手册 · PvP 数据 · 军衔与周上限（ns.PvPRankData）",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 只存 itemID 与数字、语言中立键名；名字 / 图标 / 品质运行期从客户端取。",
    ],
    "Core/Data/Data_PvPSets.lua": [
        "-- 无限副本手册 · PvP 数据 · 职业套装与暗矛声望（ns.PvPSetData）",
        "-- ★ 本文件由脚本生成，请勿手改 ★",
        "-- 只存 itemID 与语言中立键名；名字 / 图标 / 品质运行期从客户端取。",
    ],
    "Core/Data/Data_RaidSets.lua": [
        "-- 无限副本手册 · 团本套装数据（ns.RaidSetData）",
        "-- 手写数据（id 对齐客户端 setID 体系）；一套 6 件、四项效果，职业名与职业色运行期取自客户端。",
    ],
    "Core/Data/Data_VendorPrices.lua": [
        "-- 无限副本手册 · 商人直售价 · 静态种子表（离线兜底层）",
        "-- 单位：铜，[itemID] = 单件价；运行时动态采集（VendorPriceDB）优先于本表。",
    ],
}

# (file, old, new) —— 全部为 \n 文本，写回时按文件行尾转换
INLINE = [
    # ── Core.lua：BiaoGe 改名史 + 手柄定责里点名一串插件 ──
    ("Core/Core.lua",
     "-- 2026-10-09：由 BiaoGe 改名版切回原版 LibUIDropDownMenu-4.0（两份代码逐字节一致，仅注册名不同）\nns.LibBG",
     "ns.LibBG"),
    ("Core/Core.lua",
     "-- Ace3 / BiaoGeX / BlizzMove / EllesmereUIChat / TargetDistance / ForeverToolbox / DungeonsForever\n-- ——七个互不相关的插件挨个背锅；调用点 100% 在暴雪帧",
     "-- 一串互不相关的插件（含本插件）挨个背锅；调用点 100% 在暴雪帧"),
    # ── DungeonUI.lua：tooltip 重入守卫（去插件名）+ 下拉库旧版口径 + 溯源措辞 ──
    ("Core/DungeonUI.lua",
     "    -- ★★ 第九刀（Auctionator 共存炸栈，2026-10-03 用户实机 287x C stack overflow）：\n"
     "    --   实机堆栈：ShowItemTip → GameTooltip:SetItemByID →（Auctionator 挂在 GameTooltip\n"
     "    --   上的钩子 → ShowTipWithPricing → DBKeyFromLink → ContinueOnItemLoad：物品数据\n"
     "    --   已就绪时 AsyncCallbackSystem **同步**派发回调）→ 我们的到货处理（行还悬着）\n"
     "    --   再调 ShowItemTip → 再 SetItemByID ⇒ 无限同步递归直到 C stack overflow。\n"
     "    --   对策：重入即忽略 —— 正在显示的这一遍，数据刚就绪 SetItemByID 必然成功，\n"
     "    --   再入的那遍是纯冗余。pcall 包住本体保证 flag 无论成败都复位（错误原样上抛）。",
     "    -- ★★ 重入守卫：物品数据就绪时，提示框钩子链可能同步派发回调 → 再入 ShowItemTip\n"
     "    --   ⇒ 无限同步递归。对策：重入即忽略 —— 正在显示的这一遍数据刚就绪必然成功，\n"
     "    --   再入的那一遍是纯冗余。pcall 包住本体保证 flag 无论成败都复位（错误原样上抛）。"),
    ("Core/DungeonUI.lua",
     "--   根因：BiaoGe 版 LibUIDropDownMenu 只在 retail 挂 GLOBAL_MOUSE_DOWN 关闭钩",
     "--   根因：下拉库在本端没有挂 GLOBAL_MOUSE_DOWN 关闭钩"),
    ("Core/DungeonUI.lua",
     "--   参考地图界面 一个 boss 一张卡片」）",
     "--   一个 boss 一张卡片」）"),
    # ── RaidUI.lua ──
    ("Core/RaidUI.lua",
     "--   Auctionator 重入防护白嫖同款）/ Shift+点击链接进聊天框（DG.ItemShiftClick）。",
     "--   自带 tooltip 重入守卫）/ Shift+点击链接进聊天框（DG.ItemShiftClick）。"),
    # ── ExploreUI.lua ──
    ("Core/ExploreUI.lua",
     "-- ShowItemTip 自带 Auctionator 重入守卫（第九刀），PetTip(false) 的 Hide 对两者通用。",
     "-- ShowItemTip 自带重入守卫，PetTip(false) 的 Hide 对两者通用。"),
    # ── ProfRouteAuto.lua：溯源措辞 ──
    ("Core/ProfRouteAuto.lua",
     "-- 物品卖店价（直接卖给 NPC 的收益）：三通道依次尝试（2026-10-10 对照 Auctionator\n"
     "-- 源码修——它取卖店价用的是 C_Item.GetItemInfo 现代命名空间版（SELL_PRICE = 第 11 个\n"
     "-- 返回值）；本客户端全局 GetItemInfo 不可靠，再兜 C_Item.GetItemSellPrice）。",
     "-- 物品卖店价（直接卖给 NPC 的收益）：三通道依次尝试。\n"
     "-- 本客户端全局 GetItemInfo 不可靠，优先 C_Item.GetItemInfo 现代命名空间版\n"
     "-- （SELL_PRICE = 第 11 个返回值），再兜 C_Item.GetItemSellPrice。"),
    ("Core/ProfRouteAuto.lua",
     "    -- ① C_Item.GetItemInfo（Auctionator 同款，现代命名空间）",
     "    -- ① C_Item.GetItemInfo（现代命名空间）"),
    # ── ProfFollow.lua：YUI 溯源 + 插件名 ──
    ("Core/ProfFollow.lua",
     "--   - 施法兜底走法术书扫描出的「制作入口法术」（YUI GetProfessionSpellID 同款）",
     "--   - 施法兜底走法术书扫描出的「制作入口法术」"),
    ("Core/ProfFollow.lua",
     "-- 从法术书找专业的「制作入口法术」ID（YUI GetProfessionSpellID 同款）",
     "-- 从法术书找专业的「制作入口法术」ID"),
    ("Core/ProfFollow.lua",
     "--   A) OpenTradeSkill(skillLineID) —— YUI ToggleRetailProfessionFrame 同款",
     "--   A) OpenTradeSkill(skillLineID)"),
    ("Core/ProfFollow.lua",
     "--   B) 法术书入口法术施放 —— YUI YBar Forever 分支的 spell 属性等价（运行时施法版）",
     "--   B) 法术书入口法术施放（运行时施法版）"),
    ("Core/ProfFollow.lua",
     "--   · 自动 = 设置「自动计算路线」开 + Auctionator 可用 + 算得出结果且已有价格数据；",
     "--   · 自动 = 设置「自动计算路线」开 + 拍卖行价格数据可用 + 算得出结果；"),
    # ── CollectionUI.lua：溯源措辞 ──
    ("Core/CollectionUI.lua",
     "-- 阵营 / 难度 文案与配色：照抄探索页（PET_FAC_* / PET_DIFF_*），",
     "-- 阵营 / 难度 文案与配色：与探索页共用（PET_FAC_* / PET_DIFF_*），"),
    ("Core/CollectionUI.lua",
     "--   探索页小动物卡同款机制（PetSplit / PetSeg / PetFlow 的最小移植）：",
     "--   探索页小动物卡同款机制（PetSplit / PetSeg / PetFlow）："),
    # ── Hui.lua：大段历史考证压缩 + 去 Lootified ──
    ("Core/Hui.lua",
     "-- ★★ UTF-8 按「字」估宽 / 截断（双端通用，2026-10-03 从 ProfessionUI 上移）：\n"
     "--   ProfessionUI 只对无限端加载（ns.LoadForeverPages 守卫），但副本掉落页 4 列卡片\n"
     "--   的名称截断（DG.FitText）两端都要用 —— 泰坦端取不到 ns.ProfModule 时会退回原串溢出。\n"
     "--   估宽口径：全角 1.0×字号 / 半角 0.55×字号（与专业页同一套）。",
     "-- UTF-8 按「字」估宽 / 截断（双端通用）：全角 1.0×字号 / 半角 0.55×字号。"),
    ("Core/Hui.lua",
     "    -- ★★ 第九刀（rev15）：像素条复算的计数与耗时。\n"
     "    --   实机「点页签 recipe」时工具行 16 颗按钮 Hide→Show，`工具P 25.0ms`\n"
     "    --   里 `显示 24.5ms` 全在 `bt:Show()` **一句**上 —— 引擎 Show 沿「Show 链」\n"
     "    --   把 OnShow 打到子帧，而子帧（按钮的圆角边框帧）挂的正是\n"
     "    --   ReapplyStripPixels，它是**全表扫描**。这组数字用来把这条链钉死\n"
     "    --   （没有这组数就只剩「读代码猜」，项目铁律不允许）。",
     "    -- 像素条复算的计数与耗时（探针用）：OnShow 沿 Show 链打到子帧触发复算。"),
    ("Core/Hui.lua",
     "    -- ★★ 手柄/高频悬停加固（2026-10-07，真机 C stack overflow 现场）\n"
     "    -- 本函数被挂在 strip 父帧的 OnShow 上；OnShow 会落在暴雪 tooltip 管线里\n"
     "    -- （TooltipDataHandler:300 → Show 链 / NineSlice:Show），而我们在这里改纹理尺寸\n"
     "    -- 会反向触发布局/Show ⇒ 再入自身 ⇒ 无界递归 ⇒ C stack overflow（真机表现=整机假死）。\n"
     "    -- 加「单次通道」守卫：再入一律放弃本轮，尺寸由下一次 OnShow 兜底补齐。",
     "    -- 重入守卫：本函数挂在 strip 父帧的 OnShow 上，会落在 tooltip 显示链里；\n"
     "    -- 在链内改纹理尺寸会反向再入自身 ⇒ 无界递归。再入一律放弃本轮，由下一次 OnShow 兜底。"),
    ("Core/Hui.lua",
     "        -- ★★ 第九刀（rev15）：给了 frame 就只扫**本帧**挂的条（帧内索引）。\n"
     "        --   原实现无论 frame 给不给都是 `for tex in pairs(pixelStrips)`\n"
     "        --   **全表扫**，而 pixelStrips 是**全插件一张弱表**（每个直角边框帧\n"
     "        --   注册 4 条：2 横 + 2 竖，见 DrawRoundBorder 的 thick==1 分支）。\n"
     "        --   实机代价：工具行 16 颗按钮 Hide→Show 时子边框帧 OnShow 各触发\n"
     "        --   一次全表扫 ⇒ 16 × 全表 ≈ 24.5ms，正好等于「工具P」的全部。\n"
     "        --   ★ 语义不变：仍复核 tex:GetParent() == frame（换父后的旧索引项会被\n"
     "        --     这条挡掉），尺寸仍按本帧算一次；变的只有「扫多少条」：\n"
     "        --     从 O(全插件) 降到 O(本帧 4 条)。",
     "        -- 给了 frame 就只扫本帧挂的条（帧内索引），复算从 O(全插件) 降到 O(本帧 4 条)；\n"
     "        -- 仍复核 tex:GetParent() == frame，尺寸按本帧算一次。"),
    ("Core/Hui.lua",
     "            -- ★★ 第九刀（rev15）：帧内索引 —— 供 OnShow 的 O(本帧) 复算用\n"
     "            --   （原来那条 OnShow 路径是 O(全插件) 全表扫）。",
     "            -- 帧内索引：供 OnShow 的 O(本帧) 复算用。"),
    ("Core/Hui.lua",
     "            -- ★ 9-slice 圆角环：四角取象限、四直边取同一张环贴图的中段——\n"
     "            --   直边与角弧在纹理上本就连续，接缝零错位。旧法直边用纯色条，\n"
     "            --   硬边 1px 压在软边弧线的切点上，必出「小亮点」拼接痕。",
     "            -- 9-slice 圆角环：四角取象限、四直边取同一张环贴图的中段，接缝零错位。"),
    ("Core/Hui.lua",
     "                -- ★ 本客户端 4 参 SetTexCoord 是 (l, r, t, b)（Lootified 全库佐证），\n"
     "                --   照 retail 文档 (l, t, r, b) 写必炸；直边一律用 8 参 UL,LL,UR,LR",
     "                -- ★ 本客户端 4 参 SetTexCoord 是 (l, r, t, b)，照 retail 文档\n"
     "                --   (l, t, r, b) 写必炸；直边一律用 8 参 UL,LL,UR,LR"),
    ("Core/Hui.lua",
     "    -- 玻璃渐变（2026-10-10，对标 Lootified）：填充九宫按行分色，不再平涂——\n"
     "    --   上排/顶条 = 提亮，下排/底条 = 基色，中排竖向 SetGradient（WoW VERTICAL：minColor 在底）。\n"
     "    -- 半透明白填充（页内玻璃卡 {1,1,1,~0.03}）走 alpha 阶梯（上亮下淡），实色深灰走 RGB 向白混色。\n"
     "    -- 颜色表保持活引用（g.c），主题切换原地改表后 repaint 自动跟随（GlassPaint 每次现读）。",
     "    -- 玻璃渐变：填充九宫按行分色（上排提亮、下排基色、中排竖向渐变）。\n"
     "    -- 半透明白填充走 alpha 阶梯，实色深灰走 RGB 向白混色；颜色表保持活引用，主题切换自动跟随。"),
    ("Core/Hui.lua",
     "    -- 九宫软投影（垫 BACKGROUND sublevel -8，外扩 spread）。对标 Lootified：\n"
     "    -- 大窗 22/0.8、弹层 18/0.75、小浮层 14/0.7；页内卡片不加。",
     "    -- 九宫软投影（垫 BACKGROUND sublevel -8，外扩 spread）：\n"
     "    -- 大窗 22/0.8、弹层 18/0.75、小浮层 14/0.7；页内卡片不加。"),
    ("Core/Hui.lua",
     "    -- ★★ 手柄/高频悬停加固（2026-10-07，真机 C stack overflow 现场）\n"
     "    -- 为什么必须守卫：暴雪把所有**插件（不安全）** tooltip 回调都集中到一个共享禁区帧上做\n"
     "    -- 「同步属性分发」—— TooltipDataHandler 的 `AttributeDelegate:SetAttribute(process-tooltip-post-call, …)`\n"
     "    -- 会立刻在 C 侧派发 OnAttributeChanged → ProcessInsecureCalls → securecallfunction(我们的 post-call)。\n"
     "    -- 这条链**不可重入**：我们在这个栈里动帧（SetShown/SetVertexColor/SetAlpha）若触发第二次\n"
     "    -- tooltip 数据派发，就会再次走进同一个 SetAttribute ⇒ 无界递归 ⇒ C stack overflow。\n"
     "    -- 真机栈（!BugGrabber 存档，10-03）：Hui.lua:1443 ← :1463 UnskinItemTooltip ← securecallfunction\n"
     "    -- ← TooltipDataHandler:67 ← :87 ← :123 ← [C]SetAttribute ← :148 ← :242 ProcessTooltipPostCalls（循环）。\n"
     "    -- 对策：逻辑状态 s.on 先落地（保证幂等、不会来回抖动），**动帧部分加单次通道守卫**；\n"
     "    -- 再入即放弃本轮，下一次 tooltip 事件（OnShow/HookItemUnskin/Refresh）会补。",
     "    -- 重入守卫：tooltip 回调经引擎共享帧同步派发，这条链不可重入 ——\n"
     "    -- 在派发栈里动帧若触发第二次派发 ⇒ 无界递归。\n"
     "    -- 对策：逻辑状态先落地（幂等），动帧部分加单次通道守卫；再入即放弃本轮，由下一次事件补。"),
    ("Core/Hui.lua",
     "                -- ★★ 严禁在本钩子里直接动帧（2026-10-07）：SharedTooltip_SetBackdropStyle\n"
     "                -- 内部会 `NineSliceUtil.ApplyLayout(self.NineSlice, layout)` + `self.NineSlice:Show()`\n"
     "                -- （SharedTooltipTemplates.lua:47-53），我们若在同一栈里同步 SetAlpha/Show，会\n"
     "                -- 反向再入自身 ⇒ NineSlice.lua ApplyLayout 无界递归（真机 counter=49 的 C stack overflow）。\n"
     "                -- 改走带守卫的 ApplyTooltipSkin（重入即放弃本轮），由下一次事件兜底。",
     "                -- 严禁在本钩子里同步动帧（会反向再入 NineSlice 布局应用 ⇒ 无界递归）；\n"
     "                -- 改走带守卫的 ApplyTooltipSkin（重入即放弃本轮），由下一次事件兜底。"),
    ("Core/Hui.lua",
     "            -- ★ 第七刀：计数给探针（/dfprofperf 收尾打「皮按钮边框帧重建 N次」）。",
     "            -- 计数给探针（收尾打「皮按钮边框帧重建 N次」）。"),
    ("Core/Hui.lua",
     "            -- ★ 第七刀：与 BuildBorderFrame 同一笔账（一副悬浮边也是 8 个新纹理）。",
     "            -- 与 BuildBorderFrame 同一笔账（一副悬浮边也是 8 个新纹理）。"),
    ("Core/Hui.lua",
     "            -- ★★ 2026-10-09 第七刀（实机 /dfprofperf rep 定论）：**幂等**。\n"
     "            --   原来这里无条件 BuildBorderFrame + BuildHoverFrame，而 TryBuild 被\n"
     "            --   挂在下头 SetSize / SetWidth / SetHeight / OnSizeChanged 四样上 ⇒\n"
     "            --   **每一次 SetSize 都把两副圆角边框帧销毁重建**（各 4 角 + 2 横条 +\n"
     "            --   2 竖条 = 8 个新纹理，外加一个 CreateFrame）。\n"
     "            --   实机证据：专业页工具行 20 颗按钮，从别的页签切回配方页时文案/宽度\n"
     "            --   全变 ⇒ 每颗一次 SetSize ⇒ 「工具P」在**签名变化**的那些帧上恒为\n"
     "            --   ~21ms，而签名不变的帧（rep 热路径）是 0.1ms。20 × ~1ms 恰好对上。\n"
     "            --   ★ 重建是**纯浪费**：两副边框帧都是 SetAllPoints()，且所有角/边纹理\n"
     "            --     都锚在帧上（见 DrawRoundBorder：`t:SetPoint(point, f, point, ox, oy)`）\n"
     "            --     ⇒ 尺寸一变它们自己就跟着走，根本不需要重建。\n"
     "            --   ★ 描边色是**编译期常量**（C_BORDER / ns.hui.ACCENT），不跟主题走 ⇒\n"
     "            --     也不存在「靠重建换色」这条隐式依赖。\n"
     "            -- ★ 第八刀（rev14）：计数给探针 —— 看工具行闸门里那 16 次 SetSize\n"
     "            --   到底有没有真的走进这条链（第七刀时只能靠猜）。",
     "            -- 幂等：边框帧全部 SetAllPoints、纹理锚在帧上，尺寸变化自行跟随，无需销毁重建；\n"
     "            -- TryBuild 挂在 SetSize / SetWidth / SetHeight / OnSizeChanged 上，签名未变的重画直接跳过。\n"
     "            -- 计数给探针。"),
    ("Core/Hui.lua",
     "        -- ★★ 蒙版必须按**贴图**的尺寸裁，不是父帧的尺寸。\n"
     "        --    图标贴在「行 / 卡片 / 按钮」上时父帧远大于图标 —— 蒙版挂父帧的话圆角落在父帧四个角上，\n"
     "        --    图标看上去就是「没倒圆角」（用户 2026-09-30 实机截图报的正是这个）。\n"
     "        --    锚到贴图与官方 XML 同构（Blizzard_AzeriteEssenceUI 的 CircleMask 用\n"
     "        --    TOPLEFT / BOTTOMRIGHT 锚 relativeKey=\"$parent.Icon\"；动作条 IconMask 用 CENTER）。",
     "        -- ★ 蒙版必须按贴图的尺寸裁，不是父帧的尺寸：图标贴在行 / 卡片 / 按钮上时\n"
     "        --   父帧远大于图标，蒙版挂父帧会让圆角落在父帧四角、图标看上去没倒角。"),
]

import re
PAT = re.compile(r'^--\s*=+\s*$')


def load(path):
    b = open(path, 'rb').read().decode('utf-8')
    eol = '\r\n' if '\r\n' in b else '\n'
    return b.replace('\r\n', '\n'), eol


def save(path, text, eol):
    if eol == '\r\n':
        text = text.replace('\n', '\r\n')
    open(path, 'wb').write(text.encode('utf-8'))


def main():
    fails = []
    # 1) 头注释替换
    for rel, titles in HEADERS.items():
        p = os.path.join(ROOT, rel)
        text, eol = load(p)
        lines = text.split('\n')
        if not PAT.match(lines[0]):
            fails.append((rel, 'first line is not opener'))
            continue
        closer = None
        for i in range(1, len(lines)):
            if PAT.match(lines[i]):
                closer = i
                break
        if closer is None:
            fails.append((rel, 'no closer found'))
            continue
        if closer + 1 < len(lines) and lines[closer + 1].lstrip().startswith('--'):
            fails.append((rel, 'comment continues after closer (line %d): %r' % (closer + 2, lines[closer + 1][:60])))
            continue
        opener = lines[0]
        newhead = [opener] + titles + [opener]
        lines[0:closer + 1] = newhead
        save(p, '\n'.join(lines), eol)
        print('HEADER  ok  %s' % rel)
    # 2) 行内替换
    for rel, old, new in INLINE:
        p = os.path.join(ROOT, rel)
        text, eol = load(p)
        if old not in text:
            fails.append((rel, 'INLINE not found: %r' % old[:60]))
            continue
        text = text.replace(old, new, 1)
        save(p, text, eol)
        print('INLINE  ok  %s  %r...' % (rel, old[:40]))
    print()
    if fails:
        print('=== FAILURES ===')
        for rel, msg in fails:
            print('FAIL', rel, msg)
        sys.exit(1)
    print('all done')


if __name__ == '__main__':
    main()
