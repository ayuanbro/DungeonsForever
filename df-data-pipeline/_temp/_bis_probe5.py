import re
h = open('_bis_warrior.html', encoding='utf-8').read()
i = h.find('bis-weap')
print(h[i-300:i+2600].replace('\n',' '))
