# -*- coding: utf-8 -*-
"""把 Data_DungeonGuide.lua 渲成卡片式版面预览（模拟插件内暗色 HUI 版面）。"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lupa import lua51  # noqa: E402

SRC = os.path.join(os.path.dirname(HERE), 'Core', 'Data')
OUT = os.path.join(HERE, 'GUIDE_PREVIEW.html')

L = lua51.LuaRuntime(unpack_returned_tuples=True, encoding='utf-8')


def ev(name, expr):
    src = io.open(os.path.join(SRC, name), encoding='utf-8').read()
    body = src.split('local _, ns = ...', 1)[1]
    L.execute(('ns = {}\n' + body + '\n_OUT = ns.' + expr).encode('utf-8'))
    return L.eval('_OUT')


guide = ev('Data_DungeonGuide.lua', 'DungeonGuide')['ruins_of_lordaeron']
loot = ev('Data_DungeonLoot.lua', 'DungeonLoot')['ruins_of_lordaeron']

cn = {}
for i in range(1, len(loot) + 1):
    cn[loot[i][1]] = loot[i][2] or loot[i][1]


def ary(t):
    return [t[i] for i in range(1, len(t) + 1)]


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


ACCENT = ['#6bb8f0', '#31a078', '#d9a621', '#c77364']


def card(idx, label, count, body):
    return ('<div class="card" style="--ac:%s">'
            '<div class="hd"><span class="ttl">%s</span>'
            '<span class="cnt">%s</span></div>%s</div>'
            % (ACCENT[idx], label, count, body))


body_tips = '<p>· %s</p>' % esc(guide['tagline'])
body_tips += ''.join('<p>· %s</p>' % esc(t) for t in ary(guide['tips']))
body_ent = '<p><b>部落：</b>%s</p>' % esc(guide['entrance']['H'])
body_ent += '<p><b>联盟：</b></p>'
body_ent += ''.join('<p class="ind">%d. %s</p>' % (i, esc(s))
                    for i, s in enumerate(ary(guide['entrance']['A']), 1))

body_boss = ''
for b in ary(guide['bosses']):
    en = b['en']
    label = ('%s（%s）' % (cn.get(en, en), en)) if cn.get(en, en) != en else en
    body_boss += '<p class="nm">%s</p><p>%s</p>' % (esc(label), esc(b['text']))

body_trash = ''.join('<p class="nm">%s</p><p>%s</p>' % (esc(t['title']), esc(t['text']))
                     for t in ary(guide['trash']))

cards = (card(0, '副本须知', '%d 条' % (len(ary(guide['tips'])) + 1), body_tips)
         + card(1, '怎么进本', '双阵营', body_ent)
         + card(2, 'BOSS 打法', '%d 个' % len(ary(guide['bosses'])), body_boss)
         + card(3, '小怪应对', '%d 组' % len(ary(guide['trash'])), body_trash))

html = '''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>副本攻略页 · 卡片式版面预览（洛丹伦废墟）</title>
<style>
  * { box-sizing: border-box; }
  body { margin:0; padding:26px 16px 40px; background:#0d0d0d;
         font-family:"Microsoft YaHei","PingFang SC",sans-serif; }
  .note { max-width:1000px; margin:0 auto 16px; color:#7a7a7a; font-size:13px; line-height:1.75; }
  .note b { color:#ffd100; }
  .note code { color:#9ad; font-family:Consolas,monospace; }
  .win { max-width:1000px; margin:0 auto; background:#161616; border:1px solid #2f2f2f;
         border-radius:8px; padding:16px 20px 22px; }
  .tabs { display:flex; justify-content:flex-end; gap:8px; margin-bottom:14px; }
  .tabs span { padding:5px 18px; border:1px solid #3a3a3a; border-radius:3px;
               color:#8c8c8c; font-size:14px; }
  .tabs .on { border-color:#ffd100; color:#ffd100; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
  .card { position:relative; background:rgba(255,255,255,0.03);
          border:1px solid rgba(255,255,255,0.05); border-radius:8px;
          padding:10px 10px 10px 13px; }
  .card::before { content:""; position:absolute; left:1px; top:1px; bottom:1px;
                  width:3px; border-radius:8px 0 0 8px; background:var(--ac); }
  .hd { display:flex; align-items:baseline; gap:8px; margin-bottom:9px; }
  .ttl { font-size:16px; color:#ffd100; font-weight:600; }
  .cnt { margin-left:auto; font-size:11px; color:#7a7a7a; }
  p { margin:0 0 5px; font-size:14px; line-height:1.7; color:#e0e0e0; }
  p.nm { color:#ffd100; font-weight:600; }
  p.ind { padding-left:12px; }
  b { color:#f2f2f2; }
  .spec { max-width:1000px; margin:16px auto 0; color:#7a7a7a; font-size:12.5px;
          line-height:1.9; border-top:1px solid #262626; padding-top:14px; }
  .spec code { color:#9ad; font-family:Consolas,monospace; }
  .spec b { color:#c9c9c9; }
</style></head><body>

<div class="note">
  这是 <b>副本攻略</b> 子页签改成卡片式后的版面预览（真实数据取自 <code>Core/Data/Data_DungeonGuide.lua</code>）。
  四张卡按 <b>2 列 × 2 行</b> 排布，页签条示意它在详情页里的位置 —— <b>任务 / 掉落的左边</b>。
  BOSS 中文名运行时从掉落表反查（此处已按反查结果渲染）。目前只有<b>洛丹伦废墟</b>有条目，其余副本显示空态。
  定位语（"洛丹伦废城地下的亡灵废墟：…"）已<b>并入「副本须知」首条</b>，卡片列<b>紧贴内容区顶部</b>起排，不再留空档。
</div>

<div class="win">
  <div class="tabs"><span class="on">攻略</span><span>任务</span><span>掉落</span></div>
  <div class="grid">
%s
  </div>
</div>

<div class="spec">
  <b>版面参数</b>（源码 <code>DungeonUI.lua</code> 常量）：
  内容区 <code>DG.CHILD_W = 908</code> ·
  网格宽 <code>DG.GUIDE_GRID_W = 920</code>（detail 实宽 936 − 左右留白 8×2）·
  卡宽 <code>DG.GUIDE_CARD_W = 456</code> ·
  列距 <code>DG.GUIDE_GAP_X = 8</code> ·
  行距 <code>DG.GUIDE_GAP_Y = 8</code> ·
  卡内边距 <code>DG.GUIDE_PAD = 10</code> ·
  标题行高 <code>DG.GUIDE_HDR_H = 26</code> ·
  左侧色条 <code>DG.GUIDE_STRIPE = 3</code>。
  <br><b>等高规则</b>：<code>行内两卡等高</code>（取较高者），行随内容自适应 —— 上图为浏览器原生 grid
  行为，与插件内实际逻辑一致（内容少的卡底部留白，不做拉伸）。
  <br><b>安全线</b>：卡宽必须 ≤ 520 —— 暴雪 backdrop 的 edgeFile 在 760px 宽时会触发
  <code>TexCoord out of range</code> 炸整次 Build（520px 实测安全）。因此不做「奇数卡通栏」。
</div>
</body></html>''' % cards

io.open(OUT, 'w', encoding='utf-8', newline='\n').write(html)
print('已生成：%s' % OUT)
print('行数 %d / 字节 %d' % (html.count('\n') + 1, len(html.encode('utf-8'))))
