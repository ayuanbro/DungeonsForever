# -*- coding: utf-8 -*-
import io
import json

from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8766/tune.html#blackfathom_deeps/221'
OUT = 'D:/workspace/DungeonsForever/_temp/_mark_check.json'

res = {'console': [], 'steps': []}


def step(name, data):
    res['steps'].append({'name': name, 'data': data})
    print('%-24s %s' % (name, json.dumps(data, ensure_ascii=False)[:520]), flush=True)


def center(pg, sel):
    return pg.evaluate(
        "(()=>{const g=document.querySelector(%s);if(!g)return null;"
        "const r=g.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()" % json.dumps(sel))


with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    pg = b.new_page(viewport={'width': 1560, 'height': 940})
    pg.on('console', lambda m: res['console'].append(m.type + ': ' + m.text)
          if m.type in ('error', 'warning') else None)
    pg.on('pageerror', lambda e: res['console'].append('pageerror: ' + str(e)))
    pg.goto(URL, wait_until='networkidle')
    pg.wait_for_timeout(700)

    step('marks_init', pg.evaluate("S.marks[S.floor].list"))
    step('counts', pg.evaluate(
        "({mk:document.querySelectorAll('g.mk').length, bp:document.querySelectorAll('g.bp').length,"
        "qn:document.querySelectorAll('g.qn').length, qi:document.querySelectorAll('g.qi').length,"
        "markRows:document.querySelectorAll('#markList .mrow').length,"
        "noteRows:document.querySelectorAll('#noteList .nrow').length,"
        "qRows:document.querySelectorAll('#qList .nrow').length})"))

    box = pg.query_selector('.mapbox').bounding_box()
    cx, cy = box['x'] + box['width'] * 0.46, box['y'] + box['height'] * 0.34

    pg.click('#mMark')
    pg.mouse.click(cx, cy)
    pg.wait_for_timeout(200)
    step('picker', pg.evaluate(
        "[...document.querySelectorAll('#mkPick button')].map(b=>b.textContent)"))
    pg.evaluate("document.querySelectorAll('#mkPick button')[1].click()")
    pg.wait_for_timeout(250)
    step('after_add', pg.evaluate(
        "({n:S.marks[S.floor].list.length, sel:S.selMark, dm:S.marks[S.floor].dirtyMarks})"))

    pg.click('#mMove')
    mp = center(pg, "g.mk[data-k='next']")
    pg.mouse.move(mp['x'], mp['y'])
    pg.mouse.down()
    pg.mouse.move(mp['x'] + 70, mp['y'] + 46, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(250)
    step('mark_dragged', pg.evaluate("S.marks[S.floor].list"))

    bp = center(pg, 'g.bp')
    pg.mouse.move(bp['x'], bp['y'])
    pg.mouse.down()
    pg.mouse.move(bp['x'] + 50, bp['y'] - 40, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(250)
    step('pin_dragged', pg.evaluate(
        "({pins:S.marks[S.floor].pins, dp:S.marks[S.floor].dirtyPins})"))

    step('note_edit', pg.evaluate(
        "(()=>{const i=document.querySelector('#noteList input.qt');const old=i.value;"
        "i.value='洛迦利斯手稿（任务道具）·改';i.dispatchEvent(new Event('change'));"
        "return {old:old, now:i.value};})()"))
    step('tip_edit', pg.evaluate(
        "(()=>{const i=document.querySelector('#qList input.qt');i.value='自定义提示 ABC';"
        "i.dispatchEvent(new Event('change'));"
        "const q=(S.qi||[]).find(x=>x.qid==i.dataset.q);return {qid:i.dataset.q, tip:q.tip};})()"))
    pg.wait_for_timeout(200)

    txt = pg.evaluate("document.getElementById('out').value")
    step('out_flags', {'marks': '"marks"' in txt, 'pins': '"pins"' in txt,
                       'notes': '"notes"' in txt, 'qtips': '"qtips"' in txt})
    res['export'] = txt

    pg.click('#bExp')
    pg.wait_for_timeout(1500)
    for _ in range(60):
        if '已保存' in pg.evaluate("document.getElementById('saveMsg').textContent") or \
           '失败' in pg.evaluate("document.getElementById('saveMsg').textContent"):
            break
        pg.wait_for_timeout(500)
    step('save_msg', pg.evaluate("document.getElementById('saveMsg').textContent")[:300])

    pg.reload(wait_until='networkidle')
    pg.wait_for_timeout(700)
    step('after_reload', pg.evaluate(
        "({marks:S.marks[S.floor].list, pins:S.marks[S.floor].pins.slice(0,2),"
        " notes:S.marks[S.floor].notes.slice(0,2),"
        " tips:(S.qi||[]).filter(q=>q.tip).map(q=>[q.qid,q.tip])})"))

    qb = center(pg, 'g.qi')
    pg.mouse.move(qb['x'], qb['y'])
    pg.mouse.down()
    pg.mouse.move(qb['x'] - 60, qb['y'] + 44, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(250)
    step('qi_dragged', pg.evaluate(
        "({qd:S.qdirty, sel:S.selQi, hasQi:document.getElementById('out').value.includes('qicons')})"))

    pg.screenshot(path='D:/workspace/DungeonsForever/_temp/_mark_ui.png')
    step('console', res['console'])
    b.close()

io.open(OUT, 'w', encoding='utf-8', newline='\n').write(
    json.dumps(res, ensure_ascii=False, indent=1))
print('done')
