import io, re, sys

PATH = r"D:/workspace/DungeonsForever/Core/Data/Data_DungeonQuests.lua"
src = io.open(PATH, encoding="utf-8").read()
orig = src

main_old = "需要先接取“阿库麦尔水晶#6563”，才会掉落|cff999999（Coupdegrace反馈）|r。便笺由黑暗深渊的海潮祭司掉落（约 5%）。耶努萨克雷在灰谷 - 佐拉姆加前哨站（11,33）。洛古斯·杰特在副本内。"
main_new = "需要先接取《阿库麦尔水晶》，才会掉落|cff999999(Coupdegrace反馈)|r。便笺由黑暗深渊副本门口的海潮祭司掉落（约5%）。耶努萨克雷(灰谷-佐拉姆加前哨站 11,33)。洛古斯·杰特(副本内)。"
if main_old not in src:
    print("MISS main 6564 replacement")
    sys.exit(1)
src = src.replace(main_old, main_new)

manual = [
    ("从荒芜之地的后门（67,44）进去", "从后门(荒芜之地 67,44)进去"),
    ("高图斯在卡加斯瞭望塔顶（荒芜之地 5,47）", "高图斯(荒芜之地-卡加斯瞭望塔顶 5,47)"),
    ("系列始于雷克斯洛特（荒芜之地 - 卡加斯 5,47）", "系列始于雷克斯洛特(荒芜之地-卡加斯 5,47)"),
    ("湖畔镇市政厅（30,44）", "湖畔镇市政厅(赤脊山 30,44)"),
    ("谈完直接回萨尔（31,38）交任务", "谈完直接回萨尔(奥格瑞玛 31,38)交任务"),
    ("洞口在（57,50）", "洞口(冬泉谷-马兹索里尔洞穴 57,50)"),
    ("链从灰谷蓝纳（35.0,48.6）的「寻找凯特林」开始", "链从蓝纳(灰谷 35.0,48.6)的《寻找凯特林》开始"),
]
for a, b in manual:
    if a not in src:
        print("MISS manual:", a)
        sys.exit(1)
    src = src.replace(a, b)

pat_dash = re.compile(r'([\u4e00-\u9fa5·A-Za-z0-9]{2,16})在([\u4e00-\u9fa5·]{2,12}) - ([\u4e00-\u9fa5·]{2,16})（(\d{1,3}(?:\.\d)?[,.]\d{1,3})）')
src, n1 = pat_dash.subn(lambda m: "%s(%s-%s %s)" % (m.group(1), m.group(2), m.group(3), m.group(4)), src)

pat_plain = re.compile(r'([\u4e00-\u9fa5·A-Za-z0-9]{2,16})在([\u4e00-\u9fa5·]{2,12})（(\d{1,3}(?:\.\d)?[,.]\d{1,3})）')
src, n2 = pat_plain.subn(lambda m: "%s(%s %s)" % (m.group(1), m.group(2), m.group(3)), src)

def paren_fix(m):
    inner = m.group(0)[1:-1]
    inner = inner.replace(" - ", "-").replace(" · ", "-")
    inner = re.sub(r'，(?=\d)', ' ', inner)
    return "(" + inner + ")"

src, n3 = re.subn(r'（[^（）]{0,40}?\d{1,3}(?:\.\d)?[,.]\d{1,3}[^（）]{0,12}?）', paren_fix, src)

quests = ["测井", "爆破死亡矿井", "幼鳄鱼皮", "日常供货", "寻找凯特林", "长者知识", "运送失落的圣物",
          "灌木丛里的东西", "迪菲亚兄弟会", "护送迪菲亚叛徒", "当国王真好", "爱与家庭", "颅骨试炼",
          "部落的勇士", "雏龙精华"]
n4 = 0
for q in quests:
    src, k = re.subn("「" + q + "」", "《" + q + "》", src)
    n4 += k

io.open(PATH, "w", encoding="utf-8", newline="") .write(src)
print("merge-dash:", n1, "merge-plain:", n2, "paren:", n3, "questnames:", n4)
print("left full-paren-coord:", len(re.findall(r'（[^（）]{0,40}?\d{1,3}(?:\.\d)?[,.]\d{1,3}[^（）]{0,12}?）', src)))
left = [m.group(0) for m in re.finditer(r'「[^」]+」', src)]
print("left corner:", len(left))
for s in sorted(set(left)):
    print("  keep:", s)
