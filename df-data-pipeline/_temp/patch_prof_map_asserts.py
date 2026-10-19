# df_dungeon_check 地图标记断言块重写：合并后每阵营一行（军需官行优先，营地行兜底）
P = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"
d = open(P, "rb").read().decode("utf-8")
crlf = d.count("\r\n")
t = d.replace("\r\n", "\n")

def rep(old, new, n=1):
    global t
    assert t.count(old) == n, "anchor x%d (want %d): %s" % (t.count(old), n, old[:70])
    t = t.replace(old, new)

# ① 同列断言：军需官行/营地行都算坐标行（有军需官出军需官行，否则兜底营地行）
rep("""            -- ★★ 联盟/部落坐标同列直出（2 行、阵营字体色互异）
            local _campRows = {}
            for _, sp in ipairs(PD.specs or {}) do
              if type(sp.text) == "string" and sp.text:find("营地 · ", 1, true) then
                _campRows[#_campRows + 1] = sp
              end
            end
            ck("★★ 联盟/部落营地坐标同列（2 行、字体色互异）",
               #_campRows == 2 and _campRows[1].nameColor ~= nil
               and (_campRows[1].nameColor[1] ~= _campRows[2].nameColor[1]
                    or _campRows[1].nameColor[3] ~= _campRows[2].nameColor[3]),
               tostring(#_campRows))
""",
"""            -- ★★ 联盟/部落坐标行同列直出（每阵营一行：有军需官出军需官行，否则兜底营地行）
            local _campRows = {}
            for _, sp in ipairs(PD.specs or {}) do
              if type(sp.text) == "string"
                 and (sp.text:find("军需官 · ", 1, true) or sp.text:find("营地 · ", 1, true)) then
                _campRows[#_campRows + 1] = sp
              end
            end
            ck("★★ 联盟/部落坐标行同列（2 行、字体色互异）",
               #_campRows == 2 and _campRows[1].nameColor ~= nil
               and (_campRows[1].nameColor[1] ~= _campRows[2].nameColor[1]
                    or _campRows[1].nameColor[3] ~= _campRows[2].nameColor[3]),
               tostring(#_campRows))
""")

# ② 汉化/落点断言：两行都是军需官行（副行 = 组织·区域·地点）
rep("""              local _vspec, _cspec
              for _, sp in ipairs(PD.specs or {}) do
                if type(sp.text) == "string" and sp.text:find("军需官 · ", 1, true) then _vspec = sp end
                if type(sp.text) == "string" and sp.text:find("营地 · ", 1, true) then _cspec = sp end
              end
              ck("★ 军需官行已汉化（zh.json 套用：名/职责中文）",
                 _vspec ~= nil and _vspec.text == "军需官 · 妮娜·神火" and _vspec.sub == "军需官",
                 _vspec and (_vspec.text .. " | " .. tostring(_vspec.sub)) or "nil")
              ck("★ 营地行区域名走客户端（GetAreaInfo 解析 AreaID 44 → 赤脊山）",
                 _cspec ~= nil and _cspec.sub == "赤脊山 · 艾泽拉斯商会",
                 _cspec and tostring(_cspec.sub) or "nil")
              ck("★★ 两行都可点且带悬停提示（act + lines）",
                 _vspec ~= nil and type(_vspec.act) == "function" and _vspec.lines ~= nil
                 and _cspec ~= nil and type(_cspec.act) == "function" and _cspec.lines ~= nil)
              C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
              _vspec.act()
              ck("★★ 点军需官行 → 航点落赤脊山(1433) 10.8,72.4 并开图（静态映射主路径）",
                 C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.uiMapID == 1433
                 and C_MAP_MARK.wp.x == 10.8 / 100 and C_MAP_MARK.wp.y == 72.4 / 100
                 and C_MAP_MARK.opened == 1433,
                 C_MAP_MARK.wp and tostring(C_MAP_MARK.wp.uiMapID) or "nil")
              C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
              _cspec.act()
              ck("★★ 点营地行 → 航点落赤脊山(1433) 10.3,72.5",
                 C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.uiMapID == 1433
                 and C_MAP_MARK.wp.x == 10.3 / 100 and C_MAP_MARK.wp.y == 72.5 / 100)
""",
"""              local _vspecA, _vspecH
              for _, sp in ipairs(PD.specs or {}) do
                if type(sp.text) == "string" and sp.text:find("军需官 · 妮娜·神火", 1, true) then _vspecA = sp end
                if type(sp.text) == "string" and sp.text:find("军需官 · 药剂师杜蕾尔", 1, true) then _vspecH = sp end
              end
              ck("★ 军需官行副行 = 组织·区域·地点（zh.json + GetAreaInfo 套用）",
                 _vspecA ~= nil and _vspecA.sub == "艾泽拉斯商会 · 赤脊山 · 三岔口"
                 and _vspecH ~= nil and _vspecH.sub == "杜隆塔尔补给与后勤 · 贫瘠之地 · 十字路口外",
                 _vspecA and tostring(_vspecA.sub) or "nil")
              ck("★★ 两行都可点且带悬停提示（act + lines）",
                 _vspecA ~= nil and type(_vspecA.act) == "function" and _vspecA.lines ~= nil
                 and _vspecH ~= nil and type(_vspecH.act) == "function" and _vspecH.lines ~= nil)
              C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
              _vspecA.act()
              ck("★★ 点联盟军需官行 → 航点落赤脊山(1433) 10.8,72.4 并开图（静态映射主路径）",
                 C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.uiMapID == 1433
                 and C_MAP_MARK.wp.x == 10.8 / 100 and C_MAP_MARK.wp.y == 72.4 / 100
                 and C_MAP_MARK.opened == 1433,
                 C_MAP_MARK.wp and tostring(C_MAP_MARK.wp.uiMapID) or "nil")
              C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
              _vspecH.act()
              ck("★★ 点部落军需官行 → 航点落贫瘠之地(1413) 49.8,29.4",
                 C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.uiMapID == 1413
                 and C_MAP_MARK.wp.x == 49.8 / 100 and C_MAP_MARK.wp.y == 29.4 / 100)
""")

# ③ 区域名回退断言：改抓联盟军需官行（营地行已并入）
rep("""              local _cspec2
              for _, sp in ipairs(PD.specs or {}) do
                if type(sp.text) == "string" and sp.text:find("营地 · ", 1, true) then _cspec2 = sp end
              end
              ck("★ 区域名回落数据原文（zh.json 兜底仍是中文）",
                 _cspec2 ~= nil and _cspec2.sub == "赤脊山 · 艾泽拉斯商会",
                 _cspec2 and tostring(_cspec2.sub) or "nil")
""",
"""              local _vspecA2
              for _, sp in ipairs(PD.specs or {}) do
                if type(sp.text) == "string" and sp.text:find("军需官 · 妮娜·神火", 1, true) then _vspecA2 = sp end
              end
              ck("★ 区域名回落数据原文（zh.json 兜底仍是中文）",
                 _vspecA2 ~= nil and _vspecA2.sub == "艾泽拉斯商会 · 赤脊山 · 三岔口",
                 _vspecA2 and tostring(_vspecA2.sub) or "nil")
""")

if crlf:
    t = t.replace("\n", "\r\n")
open(P, "wb").write(t.encode("utf-8"))
print("map block rewritten")
