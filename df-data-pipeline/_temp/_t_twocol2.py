import json
from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8766/tune.html'
out = {}

with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    for W in (1560, 1440, 1366, 1280, 1200):
        pg = b.new_page(viewport={'width': W, 'height': 940})
        pg.goto(URL, wait_until='networkidle')
        pg.wait_for_timeout(500)
        pg.evaluate("""()=>{const s=document.querySelector('#dun');
          s.value='blackfathom_deeps'; s.dispatchEvent(new Event('change'));}""")
        pg.wait_for_timeout(700)
        g = pg.evaluate("""()=>{
          const r=e=>{const b=e.getBoundingClientRect();return [Math.round(b.width),Math.round(b.height)];};
          const side=document.querySelector('.side');
          const seg=Array.from(document.querySelectorAll('.segrow'));
          const ov=seg.filter(e=>e.scrollWidth>e.clientWidth+1).length;
          const rows=Array.from(document.querySelectorAll('.mrow,.nrow,.qrow'));
          const ovr=rows.filter(e=>e.scrollWidth>e.clientWidth+1).length;
          return {
            sideW: r(side)[0],
            grid: getComputedStyle(side).gridTemplateColumns,
            mapW: r(document.querySelector('.mapbox'))[0],
            segW: seg.length?r(seg[0]):null,
            segOverflow: ov, rowOverflow: ovr, rows: rows.length,
            docH: document.documentElement.scrollHeight,
            helpW: r(document.querySelector('.card.wide'))[0]
          };
        }""")
        out[W] = g
        if W == 1366:
            pg.screenshot(path='_twocol_1366.png')
        pg.close()
    b.close()

print(json.dumps(out, ensure_ascii=False, indent=1))
