# -*- coding: utf-8 -*-
import re, sys, glob, os
sys.stdout.reconfigure(encoding='utf-8')
for f in sorted(glob.glob('_temp/_macro_pages/*.html')) + sorted(glob.glob('_temp/_macro_probe/*.html')) + sorted(glob.glob('_temp/_macro_probe2/*.html')):
    h = open(f, encoding='utf-8', errors='replace').read()
    t = re.search(r'<title>([^<]*)</title>', h)
    c = re.search(r'<link rel="canonical" href="([^"]+)"', h)
    h3 = re.findall(r'<h3[^>]*class="heading-size-3"[^>]*>(.*?)</h3>', h, re.S)
    pres = len(re.findall(r'<pre class="code', h))
    print('%-42s %6d  pre=%2d h3=%2d | %s' % (os.path.basename(f), len(h), pres, len(h3),
          (t.group(1).strip() if t else '?')))
    print('     canon:', c.group(1) if c else '?')
