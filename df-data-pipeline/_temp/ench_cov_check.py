# 一次性分析：对比 Data_BIS enchs 与 ProfRecipes enchanting.enchants 覆盖率
import re

bis = open('Core/Data/Data_BIS.lua', encoding='utf-8').read()
pat = re.compile(r'enchs=\{(.*?)\}\s*,\s*rows=', re.S)
bis_entries = []
for m in pat.finditer(bis):
    body = m.group(1)
    for e in re.finditer(r'\{slot="([^"]+)",(?:item=(\d+),)?lvl=(\d+),eff="([^"]+)"', body):
        bis_entries.append((e.group(1), e.group(2), int(e.group(3)), e.group(4)))
print('BIS enchs 条目数:', len(bis_entries), '(解析自', len(pat.findall(bis)), '个专精段)')

pr = open('Core/Data/Data_ProfRecipes.lua', encoding='utf-8').read()
i = pr.find('["enchanting"]')
seg = pr[i:i + 400000]
# 每条: { "EnName", "cnName", "部位", "eff", lvl, ... }
pr_entries = []
for e in re.finditer(r'\{\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)",\s*(\d+),', seg):
    pr_entries.append((e.group(2), e.group(3), e.group(4), int(e.group(5))))
print('ProfRecipes 附魔条目数:', len(pr_entries))

PART = {'护腕': '手腕', '手套': '手部', '武器': '主手', '双手武器': '双手武器',
        '披风': '背部', '胸甲': '胸部', '靴子': '脚', '盾牌': '副手：盾牌',
        '项链': '颈部', '腿部': '腿部', '远程': '远程', '戒指': '戒指'}
pr_set = {}
for name, part, eff, lvl in pr_entries:
    s = PART.get(part, part)
    pr_set.setdefault((s, eff, lvl), 0)
    pr_set[(s, eff, lvl)] += 1

hit = [b for b in bis_entries if (b[0], b[3], b[2]) in pr_set]
miss = [b for b in bis_entries if (b[0], b[3], b[2]) not in pr_set]
print('BIS 中被 ProfRecipes 覆盖:', len(hit), '/', len(bis_entries))
print('BIS 独有(删除即丢失):', len(miss))
for b in miss[:25]:
    print('  ', b)

uniq = sorted(set((s, lvl, eff) for s, item, lvl, eff in miss))
print('独有组合数:', len(uniq))
for u in uniq:
    items = sorted(set(i for s, i, l, e in miss if (s, l, e) == u))
    print('  ', u, 'items=', items)
