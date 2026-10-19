# -*- coding: utf-8 -*-
"""生成「全仓图标倒圆角」对照预览（_temp/ICON_ROUND_PREVIEW.html）。

用**真实素材** Media/LibHUI/HUIRoundRectMask.tga 当 CSS mask，对每个实际用到的图标尺寸
（16/18/20/24/26/30/36）做「旧：蒙版挂父帧（方角） / 新：蒙版挂贴图（圆角）」对照。
"""
import base64
import io
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B64 = open(os.path.join(ROOT, '_temp', '_roundmask_b64.txt')).read().strip()

im = Image.open(os.path.join(ROOT, 'Media', 'LibHUI', 'HUIRoundRectMask.tga')).convert('RGBA')
W, H = im.size
# 量一下圆角半径（左上角第一个不透明像素的 x 偏移，在 y=0 行）
px = im.load()
y = 0
r = 0
for x in range(W):
    if px[x, y][3] > 250:
        r = x
        break

SIZES = [
    (16, '快捷栏专业条目 QB.ICON'),
    (18, '探索页 背包清单 / 套装行'),
    (20, '专业页 列表行 / 左列导航；探索页 收藏链节点 / 兑换行'),
    (24, '专业页 总览卡片 / 材料格；探索页 收藏 chip'),
    (26, 'BIS 部位卡片；探索页 奖励行'),
    (30, 'BIS 装备清单行'),
    (36, '探索页 收藏首件卡片'),
]


def icon_box(px_size, rounded, label):
    """一个方块图标：底色渐变 + 斜纹，圆角版走真实蒙版。"""
    style = [
        'width:%dpx' % px_size, 'height:%dpx' % px_size,
        'background:linear-gradient(135deg,#7ec8e3,#3f8fb0 45%,#2b6b88)',
        'position:relative', 'flex:0 0 auto',
        'box-shadow:inset 0 0 0 1px rgba(0,0,0,.18)',
    ]
    if rounded:
        style += [
            'mask-image:url(data:image/png;base64,%s)' % B64,
            'mask-size:100% 100%', 'mask-repeat:no-repeat',
            '-webkit-mask-image:url(data:image/png;base64,%s)' % B64,
            '-webkit-mask-size:100% 100%', '-webkit-mask-repeat:no-repeat',
        ]
    return ('<div class="ico" style="%s" title="%s"><b>%d</b></div>'
            % (';'.join(style), label, px_size))


def cell(px_size, note):
    return (
        '<tr>'
        '<td class="n">%d px</td>'
        '<td class="note">%s</td>'
        '<td>%s</td>'
        '<td>%s</td>'
        '</tr>' % (px_size, note, icon_box(px_size, False, '方角'), icon_box(px_size, True, '圆角'))
    )


rows = '\n'.join(cell(s, n) for s, n in SIZES)

HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>全仓图标倒圆角 · 对照预览</title>
<style>
  :root { color-scheme: light; }
  body { margin:0; padding:28px 32px 60px; background:#f5f6f8; color:#20242b;
         font:14px/1.7 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif; }
  h1 { font-size:20px; margin:0 0 4px; }
  .sub { color:#6b7280; margin:0 0 22px; }
  .card { background:#fff; border:1px solid #e3e6ea; border-radius:10px;
          padding:18px 20px; margin:0 0 18px; }
  .card h2 { font-size:15px; margin:0 0 10px; }
  code { background:#eef1f4; padding:1px 5px; border-radius:4px;
         font:12px/1.6 ui-monospace,Consolas,monospace; }
  .kv { display:flex; gap:26px; flex-wrap:wrap; align-items:flex-start; }
  .kvi { font-size:13px; color:#4b5563; }
  .kvi b { display:block; font-size:19px; color:#20242b; }
  table { border-collapse:collapse; width:100%; }
  th, td { text-align:left; padding:9px 10px; border-bottom:1px solid #eceff2;
           vertical-align:middle; font-size:13px; }
  th { color:#6b7280; font-weight:600; background:#fafbfc; }
  td.n { color:#111827; font-weight:600; white-space:nowrap; }
  td.note { color:#6b7280; }
  .ico { display:flex; align-items:center; justify-content:center; }
  .ico b { font-size:9px; color:#fff; opacity:.9; font-weight:600; }
  .maskwrap { display:flex; gap:22px; align-items:center; flex-wrap:wrap; }
  .maskimg { width:128px; height:128px; image-rendering:pixelated;
             border:1px solid #e3e6ea; border-radius:6px; background:
             repeating-conic-gradient(#eef1f4 0 25%, #fff 0 50%) 0 0/16px 16px; }
  .badge { display:inline-block; padding:1px 7px; border-radius:999px; font-size:11px;
           background:#e6f4ea; color:#1e7b3c; border:1px solid #bfe3cb; }
  .badge.bad { background:#fdecec; color:#a12b2b; border-color:#f3c9c9; }
  ul { margin:8px 0 0 18px; padding:0; }
  li { margin:3px 0; }
</style></head><body>

<h1>全仓图标倒圆角 · 对照预览</h1>
<p class="sub">用户实机反馈：「专业页面，你所有图标都没有倒圆角啊 / BIS 配装里面也是啊」
&nbsp;·&nbsp; 2026-09-30</p>

<div class="card">
  <h2>病根与解法（一行）</h2>
  <p><span class="badge bad">旧</span>
     <code>mask:SetAllPoints(tex:GetParent())</code> —— 圆角蒙版按 <b>父帧</b> 尺寸裁。
     图标贴在「行 / 卡片 / 按钮」上时父帧远大于图标，<b>圆角落在父帧四个角</b>，
     图标那一小块区域全是实心 ⇒ 看上去就是方角。</p>
  <p><span class="badge">新</span>
     <code>mask:SetAllPoints(tex)</code> —— 蒙版按 <b>贴图</b> 尺寸裁，圆角正好压在图标四角。</p>
  <p style="color:#6b7280">与官方 XML 同构：
     <code>Blizzard_AzeriteEssenceUI</code> 的 CircleMask 用 TOPLEFT / BOTTOMRIGHT 锚
     <code>relativeKey="$parent.Icon"</code>；<code>ActionButtonTemplate</code> 的 IconMask 用
     CENTER 锚 <code>$parent.icon</code>。所以这次是「照官方改锚点」，不是新造机制。</p>
  <p style="color:#6b7280">★ 只改锚点、<b>不新增帧</b>：早先试过「给每个图标套一层等大帧」，
     那样每行多一个帧，会把所有「新建帧计数 / 材料块不是帧」类动态断言打红 —— 已弃。</p>
</div>

<div class="card">
  <h2>蒙版本体（真实素材）</h2>
  <div class="maskwrap">
    <img class="maskimg" src="data:image/png;base64,__B64__" alt="HUIRoundRectMask">
    <div>
      <div class="kv">
        <div class="kvi"><b>__WH__</b>纹理尺寸</div>
        <div class="kvi"><b>__R__ px</b>左上圆角半径</div>
        <div class="kvi"><b>__PCT__%</b>占边长（半径 / 边长）</div>
      </div>
      <p style="color:#6b7280;margin:12px 0 0">
        <code>Media/LibHUI/HUIRoundRectMask.tga</code>（64×64）被拉伸到图标尺寸，
        所以半径 = 图标边长 × __PCT__%：16px → 5.0px、20px → 6.3px、30px → 9.4px。
        左边是棋盘底上的原始 alpha，右边一列就是按它裁出来的效果。</p>
    </div>
  </div>
</div>

<div class="card">
  <h2>按实际图标尺寸对照（左：旧方角 / 右：新圆角）</h2>
  <table>
    <thead><tr><th>尺寸</th><th>用在哪</th><th>旧</th><th>新</th></tr></thead>
    <tbody>
__ROWS__
    </tbody>
  </table>
</div>

<div class="card">
  <h2>这一轮补挂 <code>RoundIcon</code> 的 22 处（另有 5 处原本就有）</h2>
  <ul>
    <li><b>专业页 6</b>：列表行 <code>r.icon</code>20 · 职业版对照表行 <code>r.icon</code>15 ·
        总览卡片 <code>c.icon</code>24 · 左列专业导航 <code>bt.__icon</code>20 ·
        设置齿轮 <code>gear.__icon</code>14 · 材料格 <code>b.ic</code>24</li>
    <li><b>BIS 配装 2</b>：部位卡片 <code>c.icon</code>26 · 装备清单行 <code>r.icon</code>30</li>
    <li><b>探索页 11</b>：收集清单行 · 三个子页导航（40本书 / 背包 / 战斗法师）· 奖励行 ·
        背包清单条目 · 收藏首件卡 · 收藏 chip · 收藏链节点 · 套装行 · 兑换行</li>
    <li><b>副本页 2</b>：掉落卡片 · 任务详情奖励</li>
    <li><b>掉落过滤 1</b>：图标按钮 <code>bt.tex</code>（★ 同页翻页箭头也叫 <code>bt.tex</code>，
        那是 arrow.tga 四角旋转坐标，<b>不能</b>圆角）</li>
    <li><b>原本就有 5</b>：快捷栏专业条目 · 职业排行格子 / 专精头像 · 团本套装职业徽记
        （它们的帧本来就与图标等大，行为不变）</li>
  </ul>
</div>

</body></html>
"""

HTML = (HTML.replace('__B64__', B64)
            .replace('__WH__', '%d×%d' % (W, H))
            .replace('__R__', str(r))
            .replace('__PCT__', ('%.2f' % (r * 100.0 / W)).rstrip('0').rstrip('.'))
            .replace('__ROWS__', rows))

out = os.path.join(ROOT, '_temp', 'ICON_ROUND_PREVIEW.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(HTML)
print('written:', out, '| mask radius %d/%d' % (r, W))
