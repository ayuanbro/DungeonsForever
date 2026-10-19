# -*- coding: utf-8 -*-
"""第七刀：实机 /dfprofperf rep 定论后的两处产品改动 + 一条新探针。

实机数据（13:25/13:26，两轮 rep）：
  · 工具P  从「切页签那一次 20.8~22.2ms」掉到「rep 热路径 0.1ms」
    ⇒ **工具行那 21ms 是「建/换皮」的一次性成本，不是每帧必做**。
  · 铺行 / 上数据：热路径 300 行 37~42ms（≈125µs/行，且每次重渲都要再来一遍）；
    从别的页签切回配方页那一次更是「铺行 111.6ms」。
  · 工具P 为何随「签名变化」跳回 21ms —— 数量级恰好 = 20 颗按钮 × ~1ms：
    `ns.hui.SkinButton` 把 TryBuild 挂在 SetSize/SetWidth/SetHeight/OnSizeChanged 上，
    而 TryBuild 是**无条件** BuildBorderFrame + BuildHoverFrame（销毁重建两副圆角边框帧，
    各 8 个新纹理 + 1 个新 Frame）⇒ **每一次 SetSize 都是一次建帧**。

本补丁：
  A/B/C  Core/Hui.lua —— TryBuild 幂等（边框帧 SetAllPoints + 所有角/边纹理都锚在帧上
         ⇒ 尺寸一变自己就跟着走，重建是纯浪费）；外加 `ns.hui.__skinBuilds` 计数，
         让实机能把「这一次入口重建了几副边框帧」直接打出来。
  D/E/F  Core/ProfessionUI.lua —— 视口优先：行帧**已在池里**的那些，只同步绑首屏
         （`i <= PD.SyncRows()`），其余进同一张待建表交既有分帧器。判据必须**同时**
         吃「行帧已存在」，否则会把还没建的首屏行拖进这一帧 CreateFrame。
  G/H/I  探针 —— PF_SKIN0 入口快照 + 收尾打印「皮按钮边框帧重建 N次」。
  J/K    双 harness 各加 2 条断言。
  L/M/N  df_mut_check 变异定义 + 登记 + DEFAULT_WANT。

★ 全部是插入型改动（新串含旧串）⇒ 幂等靠**哨兵串**判，不靠 count(old)。
"""

import sys

HUI = 'Core/Hui.lua'
PROF = 'Core/ProfessionUI.lua'
CHECK = '_temp/df_dungeon_check.py'
MK = '_temp/mk_df_check.py'
MUT = '_temp/df_mut_check.py'
WANT = '_temp/df_check_new_muts.py'

# ────────────────────────────── Core/Hui.lua ──────────────────────────────

OLD_TB = ("        local function TryBuild()\n"
          "            local w, h = bt:GetWidth() or 0, bt:GetHeight() or 0\n"
          "            if w > 0 and h > 0 then\n"
          "                BuildBorderFrame()\n"
          "                BuildHoverFrame()\n"
          "            end\n"
          "        end\n")

NEW_TB = ("        local function TryBuild()\n"
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
          "            if borderFrame then return end\n"
          "            local w, h = bt:GetWidth() or 0, bt:GetHeight() or 0\n"
          "            if w > 0 and h > 0 then\n"
          "                BuildBorderFrame()\n"
          "                BuildHoverFrame()\n"
          "            end\n"
          "        end\n")

OLD_BB = "        local function BuildBorderFrame()\n"
NEW_BB = ("        local function BuildBorderFrame()\n"
          "            -- ★ 第七刀：计数给探针（/dfprofperf 收尾打「皮按钮边框帧重建 N次」）。\n"
          "            ns.hui.__skinBuilds = (ns.hui.__skinBuilds or 0) + 1\n")

OLD_HF = "        local function BuildHoverFrame()\n"
NEW_HF = ("        local function BuildHoverFrame()\n"
          "            -- ★ 第七刀：与 BuildBorderFrame 同一笔账（一副悬浮边也是 8 个新纹理）。\n"
          "            ns.hui.__skinBuilds = (ns.hui.__skinBuilds or 0) + 1\n")

# ────────────────────────── Core/ProfessionUI.lua ──────────────────────────

OLD_SYNC = "PD.__pendRows = {}\nPD.ROW_SYNC_MAX = 20\n"

NEW_SYNC = (
    "PD.__pendRows = {}\n"
    "PD.ROW_SYNC_MAX = 20\n"
    "-- ★★ 视口优先（2026-10-09 第七刀；实机 /dfprofperf rep）。\n"
    "--   行帧**已经在池里**的那些，原来一律在渲染这一帧里同步重绑：实机「上数据 300次 /\n"
    "--   37~42ms」，而从别的页签切回配方页那一次更到「铺行 111.6ms」（那一帧还会顺手建出\n"
    "--   每行 mn/mz 那几格材料帧）。现在只同步绑**首屏画得出来的那几十行**，其余进同一张\n"
    "--   待建表，交由既有分帧器按每帧预算（DG.Loader.budgetMs）补齐 ⇒ 单帧硬卡被摊平，\n"
    "--   而屏上第一屏内容**当帧就是对的**（行池里本来就画着上一页的东西，不是空白）。\n"
    "--   ★ 判据必须**同时**吃「行帧已存在」：光看 `i <= syncN` 会把**还没建**的首屏行\n"
    "--     拖回这一帧来 CreateFrame（首屏 30 行 ≈ 18ms 建帧，正是分帧要避开的那笔）。\n"
    "PD.SYNC_ROWS_BUF = 6\n"
    "function PD.SyncRows()\n"
    "    local h = 0\n"
    "    local sf = PD.scroll\n"
    "    if sf and type(sf.GetHeight) == \"function\" then\n"
    "        local ok, v = pcall(sf.GetHeight, sf)\n"
    "        if ok and type(v) == \"number\" then h = v end\n"
    "    end\n"
    "    if h <= 0 then h = 420 end          -- 量不到（桩 / 没建好）就按 420px 兜底\n"
    "    local per = PD.ROW_H1 or PD.ROW_H or 20\n"
    "    if type(per) ~= \"number\" or per <= 0 then per = 20 end\n"
    "    return math.ceil(h / per) + PD.SYNC_ROWS_BUF\n"
    "end\n")

OLD_ROWW = "    local ROW_W = PD.RIGHT_W - 2 * PD.LIST_PAD\n"
NEW_ROWW = ("    local ROW_W = PD.RIGHT_W - 2 * PD.LIST_PAD\n"
            "    local syncN = PD.SyncRows()          -- ★ 第七刀：本帧同步绑的行数上限\n")

OLD_BR = ("            if r then\n"
          "                r:ClearAllPoints()\n"
          "                r:SetPoint(\"TOPLEFT\", PD.child, \"TOPLEFT\", x, -top)\n"
          "                r:SetSize(w, h)\n"
          "                r:Show()\n"
          "                PD.BindRow(r, spec, h)\n")

NEW_BR = ("            -- ★★ 视口优先（第七刀）：行帧在池里 **且** 落在首屏预算内，才当帧同步重绑；\n"
          "            --   其余（含池里已有但排到首屏之外的）一律进待建表 —— 它们这一轮不改\n"
          "            --   观感，由分帧器后续补齐。\n"
          "            if r and i <= syncN then\n"
          "                r:ClearAllPoints()\n"
          "                r:SetPoint(\"TOPLEFT\", PD.child, \"TOPLEFT\", x, -top)\n"
          "                r:SetSize(w, h)\n"
          "                r:Show()\n"
          "                PD.BindRow(r, spec, h)\n")

# ────────────────────────────── 探针（ProfessionUI 尾部） ──────────────────────────────

OLD_PFDECL = ("local PF_SUB, PF_SET = nil, nil   -- 细分计时 / setter 计数（每次入口重置）\n")
NEW_PFDECL = (OLD_PFDECL +
              "local PF_SKIN0 = nil              -- ★ 第七刀：皮按钮「圆角边框帧重建」的入口快照\n")

OLD_PFBEGIN = "        PF_SUB, PF_SET = {}, {}\n"
NEW_PFBEGIN = ("        PF_SUB, PF_SET = {}, {}\n"
               "        PF_SKIN0 = (ns.hui and ns.hui.__skinBuilds) or 0\n")

OLD_PFEND = ("    if #st > 0 then pfOut(\"  └ setter 调用：\" .. table.concat(st, \" · \")) end\n")
NEW_PFEND = (OLD_PFEND +
             "    -- ★ 第七刀：这一段入口内「皮按钮圆角边框帧」被重建了几副（每次 8 个新纹理）。\n"
             "    --   改动前工具行每次换文案/宽度 = 每颗一次 SetSize = 每颗两副 ⇒ 20 颗 ≈ 20ms。\n"
             "    local sk = ((ns.hui and ns.hui.__skinBuilds) or 0) - (PF_SKIN0 or 0)\n"
             "    if sk > 0 then\n"
             "        pfOut(string.format(\"  └ 皮按钮边框帧重建：%d 次（SetSize 一次就是一次建帧）\", sk))\n"
             "    end\n")

# ────────────────────────────── 双 harness 断言 ──────────────────────────────

ANCHOR_READ = ("    profui = open(os.path.join(ADDON, 'Core', 'ProfessionUI.lua'), encoding='utf-8',\n"
               "                  errors='replace').read().replace('\\r\\n', '\\n')\n")

NEW_READ = (ANCHOR_READ +
            "    hui = open(os.path.join(ADDON, 'Core', 'Hui.lua'), encoding='utf-8',\n"
            "               errors='replace').read().replace('\\r\\n', '\\n')\n")

ANCHOR_GAP = ("    ck('★ 间距行（kind == \"gap\"）也进待建表（跳号会在行池里留空洞）',\n"
              "       'PD.__pendRows[#PD.__pendRows + 1] = { idx = i, gap = true }' in profui)\n")

NEW_CKS = (
    "    # ★★ 2026-10-09 第七刀：实机 /dfprofperf rep 的「工具P」在**签名变化**的帧上恒为\n"
    "    #   ~21ms、签名不变的帧 0.1ms ⇒ 那 21ms 是「建/换皮」的一次性成本。数量级 20 颗按钮\n"
    "    #   × ~1ms 恰好对上 `ns.hui.SkinButton` 的 TryBuild：它挂在 SetSize/SetWidth/\n"
    "    #   SetHeight/OnSizeChanged 四样上，而函数体是**无条件**销毁重建两副圆角边框帧。\n"
    "    #   ★ 重建是纯浪费：两副边框帧都是 SetAllPoints()，所有角/边纹理都锚在帧上\n"
    "    #     （DrawRoundBorder 里 `t:SetPoint(point, f, point, ox, oy)`）⇒ 尺寸自己跟。\n"
    "    ck('★★ 皮按钮圆角边框帧不许在 SetSize 时重建（SetAllPoints，会自己跟尺寸走）',\n"
    "       'if borderFrame then return end' in hui\n"
    "       and 'ns.hui.__skinBuilds' in hui)\n"
    "    # ★★ 2026-10-09 第七刀：行帧**已在池里**的那些原来一律在本帧同步重绑（实机 300 行\n"
    "    #   上数据 37~42ms；从别的页签切回来那一次铺行 111.6ms）。现在只同步绑首屏。\n"
    "    #   ★ 判据必须**同时**吃「行帧已存在」——光看 i 会把还没建的首屏行拖回来建帧。\n"
    "    ck('★★ 行帧已在池里也只同步绑首屏，其余交分帧器（单帧不再重绑 300 行）',\n"
    "       'function PD.SyncRows()' in profui\n"
    "       and 'PD.SYNC_ROWS_BUF' in profui\n"
    "       and 'local syncN = PD.SyncRows()' in _paintlive\n"
    "       and 'if r and i <= syncN then' in _paintlive)\n"
)

# ────────────────────────────── 变异 ──────────────────────────────

MUT_KEY = ("MUT_PROF_SCAN_ALL_ROWS = ('Core/ProfessionUI.lua', (\n"
           "    b'                if n <= PD.ROW_CAP then\\n',\n"
           "    b'                if true then  -- MUT: scan measures every row\\n'))\n")

MUT_DEF = (
    "\n"
    "# ★★ 皮按钮边框帧重建（2026-10-09 第七刀）：把幂等摘掉 = 每次 SetSize 都销毁重建\n"
    "#   两副圆角边框帧（各 8 个新纹理）—— 专业页工具行 20 颗按钮切页时一次 ≈ 20ms。\n"
    "MUT_HUI_SKIN_REBUILD = ('Core/Hui.lua', (\n"
    "    b'            if borderFrame then return end\\n',\n"
    "    b'            -- MUT: border frames rebuilt on every SetSize\\n'))\n"
    "\n"
    "# ★★ 视口优先（2026-10-09 第七刀）：把闸拿掉 = 行帧已在池里的一律本帧同步重绑\n"
    "#   （实机 300 行 37~42ms，切页那一次 111.6ms）。\n"
    "MUT_PROF_ROW_SYNC_ALL = ('Core/ProfessionUI.lua', (\n"
    "    b'            if r and i <= syncN then\\n',\n"
    "    b'            if r then  -- MUT: rebind every pooled row inline\\n'))\n"
)

MUT_REG_ANCHOR = ("    ('专业页：扫描又给全量行量宽（只画 300 行却量 511 行）',"
                  " MUT_PROF_SCAN_ALL_ROWS),\n")
MUT_REG_NEW = (MUT_REG_ANCHOR +
               "    ('Hui：皮按钮边框帧每次 SetSize 都重建（工具行换文案 = 20 颗各建两副）',"
               " MUT_HUI_SKIN_REBUILD),\n"
               "    ('专业页：行帧已在池里也本帧全量重绑（切回配方页那一下又 100ms+）',"
               " MUT_PROF_ROW_SYNC_ALL),\n")

WANT_ANCHOR = "    '专业页：扫描又给全量行量宽（只画 300 行却量 511 行）',\n"
WANT_NEW = (WANT_ANCHOR +
            "    'Hui：皮按钮边框帧每次 SetSize 都重建（工具行换文案 = 20 颗各建两副）',\n"
            "    '专业页：行帧已在池里也本帧全量重绑（切回配方页那一下又 100ms+）',\n")

# (文件, 名字, 旧, 新, 哨兵) —— 哨兵只在「已应用」后出现。
JOBS = [
    (HUI, 'A Hui TryBuild 幂等', OLD_TB, NEW_TB, 'if borderFrame then return end'),
    (HUI, 'B Hui 建框计数', OLD_BB, NEW_BB, '皮按钮边框帧重建 N次'),
    (HUI, 'C Hui 悬浮框计数', OLD_HF, NEW_HF, '与 BuildBorderFrame 同一笔账'),
    (PROF, 'D PD.SyncRows', OLD_SYNC, NEW_SYNC, 'function PD.SyncRows()'),
    (PROF, 'E PaintRows 取 syncN', OLD_ROWW, NEW_ROWW, 'local syncN = PD.SyncRows()'),
    (PROF, 'F PaintRows 视口闸', OLD_BR, NEW_BR, 'if r and i <= syncN then'),
    (PROF, 'G 探针 PF_SKIN0 声明', OLD_PFDECL, NEW_PFDECL, 'local PF_SKIN0 = nil'),
    (PROF, 'H pfBegin 快照', OLD_PFBEGIN, NEW_PFBEGIN, 'PF_SKIN0 = (ns.hui and ns.hui.__skinBuilds)'),
    (PROF, 'I pfEnd 打印', OLD_PFEND, NEW_PFEND, '皮按钮边框帧重建：'),
    (CHECK, 'J harness 读 Hui', ANCHOR_READ, NEW_READ, "hui = open(os.path.join(ADDON, 'Core', 'Hui.lua')"),
    (MK, 'K 生成器读 Hui', ANCHOR_READ, NEW_READ, "hui = open(os.path.join(ADDON, 'Core', 'Hui.lua')"),
    (CHECK, 'L harness 加 2 条断言', ANCHOR_GAP, ANCHOR_GAP + NEW_CKS, '皮按钮圆角边框帧不许'),
    (MK, 'M 生成器加 2 条断言', ANCHOR_GAP, ANCHOR_GAP + NEW_CKS, '皮按钮圆角边框帧不许'),
    (MUT, 'N 变异定义', '', '', 'MUT_HUI_SKIN_REBUILD = '),
    (MUT, 'O 变异登记', MUT_REG_ANCHOR, MUT_REG_NEW, 'MUT_HUI_SKIN_REBUILD),'),
    (WANT, 'P DEFAULT_WANT', WANT_ANCHOR, WANT_NEW, '皮按钮边框帧每次 SetSize 都重建'),
]


def main():
    check = '--check' in sys.argv
    bad, plans, raws = 0, {}, {}
    for path, name, old, new, key in JOBS:
        if path not in raws:
            raws[path] = open(path, 'rb').read()
        raw = raws[path]
        src = plans.get(path) or raw.decode('utf-8')
        nl = '\r\n' if b'\r\n' in raw else '\n'

        def fx(s):
            return s if nl == '\n' else s.replace('\n', nl)

        if key and fx(key) in src:
            print('  [SKIP] %-24s 已应用' % name)
            continue

        if name.startswith('N'):
            k = fx(MUT_KEY)
            if src.count(k) != 1:
                print('  [BAD ] %-24s 变异定义插入锚点 %d 次' % (name, src.count(k)))
                bad += 1
                continue
            plans[path] = src.replace(k, k + fx(MUT_DEF), 1)
            print('  [OK  ] %-24s 锚点 1 次' % name)
            continue

        o, n = fx(old), fx(new)
        if src.count(o) != 1:
            print('  [BAD ] %-24s 锚点 %d 次' % (name, src.count(o)))
            bad += 1
            continue
        plans[path] = src.replace(o, n, 1)
        print('  [OK  ] %-24s 锚点 1 次' % name)

    if bad:
        print('  \u2717 %d 处未通过，未落盘' % bad)
        return 1
    if check:
        print('  [OK  ] 预检通过（未落盘）')
        return 0
    for path, src in plans.items():
        if src != raws[path].decode('utf-8'):
            with open(path, 'wb') as f:
                f.write(src.encode('utf-8'))
            print('  [OK  ] 已写入 %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
