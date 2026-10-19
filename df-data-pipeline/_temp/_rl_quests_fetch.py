# -*- coding: utf-8 -*-
"""抓 wowhead forever 任务页（10 条洛丹伦废墟任务）→ 本地缓存。

wowhead 现走 CloudFront + AWS WAF，代理节点被地区拦，curl_cffi 拿不到；
改用文本提取通道（服务端在美国，不受地区限制）。慢，但一次性摸底够用。
"""
import os
import time
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '_rl_quests')
PROXY = 'http://127.0.0.1:7897'

QUESTS = [92401, 92415, 92421, 92422, 95189, 95195, 95204, 95216, 95250, 97288]


def main():
    if not os.path.isdir(CACHE):
        os.makedirs(CACHE)
    for q in QUESTS:
        out = os.path.join(CACHE, 'q%d.txt' % q)
        if os.path.exists(out) and os.path.getsize(out) > 400:
            print('skip', q)
            continue
        url = 'https://www.wowhead.com/forever/cn/quest=%d' % q
        cmd = ['curl', '-s', '--max-time', '90', '-x', PROXY,
               'https://r.jina.ai/' + url, '-o', out,
               '-w', '%{http_code} %{size_download}']
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(q, r.stdout.strip())
        time.sleep(2)
    print('done ->', CACHE)


if __name__ == '__main__':
    main()
