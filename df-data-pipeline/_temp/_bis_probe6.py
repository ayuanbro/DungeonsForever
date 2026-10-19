import re
h = open('_bis_rogue.html', encoding='utf-8').read()
print(re.findall(r'<section class="bis-slot" id="slot-([a-z0-9-]+)">', h))
i = h.find('bis-weapons')
print(h[i:i+2200].replace('\n',' '))
