# -*- coding: utf-8 -*-
"""BuildCapsule 改造探针：dump 四角贴图路径/尺寸/UV 与直边锚点（换新体系后核对）。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _dbg_qbadge import build_lua  # noqa: E402

DUMP = r'''
(function()
  local out = {}
  local hui = TF_NS.hui
  local root = CreateFrame("Frame", nil, UIParent)
  local function dump(cs, label)
    local pcs = hui.BuildCapsule(root, cs, { 1, 1, 1, 1 })
    out[#out+1] = string.format('%s（半径 %s）：件数 %d', label, tostring(cs), #pcs)
    for i, t in ipairs(pcs) do
      local pts = t.__pts
      out[#out+1] = string.format('   [%d] %s  %sx%s  %s->%s (%s,%s)',
        i, tostring(t.__tex), tostring(t.__w), tostring(t.__h),
        tostring(pts and pts[1]), tostring(pts and pts[3]),
        tostring(pts and pts[4]), tostring(pts and pts[5]))
    end
  end
  dump(8, '任务页 iOS 开关轨道')
  dump(6, '危险/强调按钮')
  dump(2, '滑杆圆钮')
  dump(3, '滑杆轨道')
  dump(12, '悬停药丸')
  return table.concat(out, '\n')
end)()
'''


def main():
    lua = build_lua()
    print(lua.eval(DUMP))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
