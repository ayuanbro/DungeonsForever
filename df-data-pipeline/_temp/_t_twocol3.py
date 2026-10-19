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
    pg.wait_for_timeout(700)

    res['before'] = pg.evaluate("()=>{const g=document.querySelector('.segList');return 0;}")
    r = pg.evaluate("""()=>{
      const rows=document.querySelectorAll('.segrow');
      rows[2].dispatchEvent(new MouseEvent('click',{bubbles:true}));
      return {n:rows.length};
    }""")
    pg.wait_for_timeout(300)
    res['click'] = pg.evaluate("""()=>{
      const on=document.querySelector('.segrow.on');
      return {sel: on?on.textContent.trim():null,
              amp: document.querySelector('#ampV').textContent,
              ctrl: document.querySelector('#ctrlCount').textContent};
    }""")

    pg.evaluate("()=>document.querySelector('#mDraw').click()")
    pg.wait_for_timeout(250)
    res['draw'] = pg.evaluate("()=>({mode:S.mode,bar:getComputedStyle(document.querySelector('#drawbar')).display})")
    pg.evaluate("()=>document.querySelector('#mDraw').click()")
    pg.wait_for_timeout(200)
    res['back'] = pg.evaluate("()=>({mode:S.mode,bar:getComputedStyle(document.querySelector('#drawbar')).display})")

    res['geo'] = pg.evaluate("""()=>{
      const r=e=>{const b=e.getBoundingClientRect();return {x:Math.round(b.x),y:Math.round(b.y),w:Math.round(b.width),h:Math.round(b.height)};};
      const side=document.querySelector('.side');
      return {docH:document.documentElement.scrollHeight,
              side:r(side), grid:getComputedStyle(side).gridTemplateColumns,
              cards:Array.from(document.querySelectorAll('.side .card')).map(c=>({cls:c.className,...r(c)}))};
    }""")
    pg.screenshot(path='_twocol_final.png', full_page=True)
    pg.screenshot(path='_twocol_top.png')
    b.close()

print(json.dumps(res, ensure_ascii=False, indent=1))
