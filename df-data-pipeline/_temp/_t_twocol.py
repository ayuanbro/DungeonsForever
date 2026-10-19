import json, sys
from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8766/tune.html'
res = {'console': []}

with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    pg = b.new_page(viewport={'width': 1560, 'height': 940})
    pg.on('console', lambda m: res['console'].append(m.type + ': ' + m.text)
          if m.type in ('error', 'warning') else None)
    pg.on('pageerror', lambda e: res['console'].append('pageerror: ' + str(e)))
    pg.goto(URL, wait_until='networkidle')
    pg.wait_for_timeout(600)

    res['opts'] = pg.evaluate("()=>Array.from(document.querySelectorAll('#dun option')).map(o=>o.value+'|'+o.textContent)")
    tgt = pg.evaluate("""()=>{
      const os=Array.from(document.querySelectorAll('#dun option'));
      const hit=os.find(o=>o.textContent.indexOf('黑暗深渊')>=0)||os[0];
      const s=document.querySelector('#dun'); s.value=hit.value;
      s.dispatchEvent(new Event('change')); return hit.value;
    }""")
    pg.wait_for_timeout(900)
    res['dun'] = tgt

    res['geo'] = pg.evaluate("""()=>{
      const r=e=>{const b=e.getBoundingClientRect();return {x:Math.round(b.x),y:Math.round(b.y),w:Math.round(b.width),h:Math.round(b.height)};};
      const side=document.querySelector('.side');
      const cards=Array.from(document.querySelectorAll('.side .card'));
      const cols=Array.from(document.querySelectorAll('.side > .col'));
      return {
        docW: document.documentElement.scrollWidth,
        docH: document.documentElement.scrollHeight,
        map: r(document.querySelector('.mapbox')),
        side: r(side),
        sideCols: getComputedStyle(side).gridTemplateColumns,
        cols: cols.map(r),
        cards: cards.map(c=>({cls:c.className, ...r(c)})),
        qListH: Math.round(document.querySelector('#qList').getBoundingClientRect().height),
        amp: Math.round(document.querySelector('.card:nth-of-type(1)')?0:0)
      };
    }""")

    pg.screenshot(path='_twocol.png', full_page=True)
    b.close()

print(json.dumps(res, ensure_ascii=False, indent=1))
