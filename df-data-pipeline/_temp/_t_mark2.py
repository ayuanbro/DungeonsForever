# -*- coding: utf-8 -*-
import io
import json

from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8766/tune.html#blackfathom_deeps/221'
res = {'console': [], 'steps': []}


def step(name, data):
    res['steps'].append({'name': name, 'data': data})
    print('%-22s %s' % (name, json.dumps(data, ensure_ascii=False)[:500]), flush=True)


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
    step('marks', pg.evaluate("S.marks[S.floor].list"))
    step('notes_q', pg.evaluate("S.marks[S.floor].notes.map(n=>[n.text.slice(0,10),n.q])"))
    step('counts', pg.evaluate(
        "({mk:document.querySelectorAll('g.mk').length, bp:document.querySelectorAll('g.bp').length,"
        "qn:document.querySelectorAll('g.qn').length, qi:document.querySelectorAll('g.qi').length,"
        "markRows:document.querySelectorAll('#markList .mrow').length,"
        "noteRows:document.querySelectorAll('#noteList .nrow').length,"
        "qRows:document.querySelectorAll('#qList .nrow').length})"))
    step('ovr_keys', pg.evaluate("Object.keys(OVR)"))

    box = pg.query_selector('.mapbox').bounding_box()
    cx, cy = box['x'] + box['width'] * 0.40, box['y'] + box['height'] * 0.26
    pg.click('#mMark')
    pg.mouse.click(cx, cy)
    pg.wait_for_timeout(200)
    pg.evaluate("document.querySelectorAll('#mkPick button')[2].click()")
    pg.wait_for_timeout(200)
    step('added_prev', pg.evaluate("S.marks[S.floor].list.length"))

    pg.click('#mMove')
    mp = center(pg, "g.mk[data-k='prev']")
    pg.mouse.move(mp['x'], mp['y'])
    pg.mouse.down()
    pg.mouse.move(mp['x'] + 40, mp['y'] + 30, steps=5)
    pg.mouse.up()
    pg.wait_for_timeout(200)
    step('moved_prev', pg.evaluate("S.marks[S.floor].list"))

    mp2 = center(pg, "g.mk[data-k='prev']")
    pg.mouse.click(mp2['x'], mp2['y'], button='right')
    pg.wait_for_timeout(200)
    step('rightclick_del', pg.evaluate(
        "({n:S.marks[S.floor].list.length, dm:S.marks[S.floor].dirtyMarks,"
        " status:document.getElementById('stat').textContent})"))

    pg.click('#bUndo')
    pg.wait_for_timeout(200)
    step('undo', pg.evaluate("({n:S.marks[S.floor].list.length, dm:S.marks[S.floor].dirtyMarks})"))

    step('export', pg.evaluate("document.getElementById('out').value")[:400])
    step('console', res['console'])
    pg.screenshot(path='D:/workspace/DungeonsForever/_temp/_mark_ui.png')
    b.close()
print('done')
