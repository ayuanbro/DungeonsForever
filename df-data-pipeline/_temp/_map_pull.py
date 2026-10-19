# -*- coding: utf-8 -*-
"""分页拉全 Map 表（enUS + zhCN），建 uiMapID 双语名索引。"""
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PIN = 'PIN-b3939f70f141fd3b2b7e18591b5e1bb751c280b323ba680dd2bb5f763360a1ff'
INST = 'D:/Game/World of Warcraft/_classic_beta_'
CLI = r'C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2-6\node_modules\lycheedev\bin\lycheedev.mjs'
NODE = r'C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2-6\node.exe'
ENV = dict(os.environ)
ENV['HTTPS_PROXY'] = 'http://127.0.0.1:7897'
ENV['HTTP_PROXY'] = 'http://127.0.0.1:7897'


def pull(locale):
    rows = {}
    after = None
    for _ in range(40):
        cmd = [NODE, CLI, 'data', 'db2', '--table', 'Map', '--snapshot', PIN,
               '--installation', INST, '--limit', '500', '--format', 'json']
        if after is not None:
            cmd += ['--after-id', str(after)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=ENV)
        try:
            d = json.loads(r.stdout)
        except Exception:
            print('parse fail', r.stdout[:200])
            break
        res = d.get('result') or {}
        page = res.get('page') or {}
        got = page.get('rows') or []
        for row in got:
            rows[row['ID']] = row.get('MapName_lang') or ''
        print(locale, 'page got', len(got), 'total', len(rows), 'next', page.get('next'))
        if not page.get('more'):
            break
        after = page.get('next')
    return rows


def main():
    en = pull('enUS')
    zh = pull('zhCN')
    out = {'en': en, 'zh': zh}
    json.dump(out, open(os.path.join(HERE, '_map_names.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=0)
    print('en rows:', len(en), 'zh rows:', len(zh))


if __name__ == '__main__':
    main()
