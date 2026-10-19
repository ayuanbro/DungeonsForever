import re, collections
h = open('_bis_warrior.html', encoding='utf-8').read()
i = h.find('联盟')
print('SIDE CTRL:', h[i-500:i+400].replace('\n',' ')[:900])
print()
types = re.findall(r'bis-from"><p><a href="([^"]+)"', h)
c = collections.Counter(re.sub(r'[0-9]+', 'N', t.split('#')[0]) for t in types)
print('FROM TYPES:', c.most_common(20))
print()
# 一个掉落来源样例
for t in types:
    if '/item=' in t or 'npc=' in t:
        k = h.find(t)
        print('DROP SAMPLE:', h[k-300:k+400].replace('\n',' '))
        break
