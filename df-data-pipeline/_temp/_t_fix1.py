import json
from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8766/tune.html'
res = {'err': []}

with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    pg = b.new_page(viewport={'width': 1560, 'height': 940})
    pg.on('pageerror', lambda e: res['err'].append(str(e)))
    pg.on('console', lambda m: res['err'].append('console:' + m.text) if m.type == 'error' else None)
    pg.goto(URL, wait_until='networkidle')
    pg.wait_for_timeout(500)
    pg.evaluate("""()=>{const s=document.querySelector('#dun');
      s.value='blackfathom_deeps'; s.dispatchEvent(new Event('change'));}""")
    pg.wait_for_timeout(800)

    res['cards'] = pg.evaluate("()=>Array.from(document.querySelectorAll('.side .card')).map(c=>c.querySelector('h2')?c.querySelector('h2').textContent.trim():'(help)')")
    res['ampGone'] = pg.evaluate("()=>[!!document.querySelector('#amp'), document.body.innerText.indexOf('本段抖动')]")

    res['lists'] = pg.evaluate("""()=>{
      const q=id=>{const e=document.querySelector('#'+id); if(!e) return null;
        const cs=getComputedStyle(e);
        return {h:Math.round(e.getBoundingClientRect().height), sh:e.scrollHeight,
                ch:e.clientHeight, ov:cs.overflowY, n:e.children.length};};
      return {mark:q('markList'), pin:q('pinList'), note:q('noteList'), q:q('qList'),
              card:Math.round(document.querySelectorAll('.side .card')[1].getBoundingClientRect().height)};
    }""")

    res['draw'] = pg.evaluate("""()=>{
      document.querySelector('#mDraw').click();
      const bar=document.querySelector('#drawbar'), mb=document.querySelector('.mapbox');
      const rb=bar.getBoundingClientRect(), rmb=mb.getBoundingClientRect();
      return {disp:getComputedStyle(bar).display, barTop:Math.round(rb.y), barH:Math.round(rb.height),
              mapBottom:Math.round(rmb.y+rmb.height), barW:Math.round(rb.width), mapW:Math.round(rmb.width),
              overlap: rb.top < rmb.bottom - 1};
    }""")
    pg.wait_for_timeout(300)
    pg.screenshot(path='_fix_draw.png')
    pg.evaluate("()=>document.querySelector('#mDraw').click()")
    pg.wait_for_timeout(200)
    res['drawOff'] = pg.evaluate("()=>({mode:S.mode,disp:getComputedStyle(document.querySelector('#drawbar')).display})")
    res['docH'] = pg.evaluate("()=>document.documentElement.scrollHeight")
    pg.screenshot(path='_fix_full.png', full_page=True)
    b.close()

print(json.dumps(res, ensure_ascii=False, indent=1))
