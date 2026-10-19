# -*- coding: utf-8 -*-
"""向 _wh_guide_raw.json 注入 onyxias_lair 手工条目 + 向 _wh_spell_icons.json 补图标兜底。

奥巢的 wowhead 攻略页没有标准 Abilities 段（技能写在打法叙述里），
对照攻略页内联法术链接手工登记 5 个技能 id（wowhead 页序）：
  Tail Sweep 15847 / Wing Buffet 18500 / Fireball 18392 /
  Breath (Deep Breath) 17086 / Bellowing Roar → 恐惧效果行
Bellowing Roar 的 wowhead id 18431 在 forever 客户端 SpellName 里不存在
（GetSpellInfo 返回 nil，实机显示「法术 #18431」）；客户端静态表里
恐惧类咆哮 = 14100（Terrifying Roar / 恐吓咆哮，Apply Aura: Fear），用之。
2026-10-11 lycheedev 实测：SpellName 无 18431、有 14100；14100 的官方图标
（nether tooltip）= ability_devour，共享图标表已有，无需兜底。
图标 slug 取自攻略页内联图标（仅客户端查不到时的兜底）。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GUIDE = os.path.join(HERE, "_wh_guide_raw.json")
ICONS = os.path.join(HERE, "_wh_spell_icons.json")

ENTRY = {
    "text": "Onyxia's Lair raid strategy (wowhead onyxia-onyxias-lair-strategy). "
            "Abilities referenced inline in the strategy guide: Tail Sweep, Wing Buffet, "
            "Fireball, Breath (Deep Breath), Bellowing Roar (client id 14100).",
    "spells": [15847, 18500, 18392, 17086, 14100],
}

ICON_ADD = {
    "15847": "inv_misc_monsterscales_05",
    "18500": "inv_misc_monsterscales_14",
    "18392": "spell_fire_flamebolt",
    "17086": "spell_fire_fire",
}


def main():
    g = json.load(open(GUIDE, encoding="utf-8"))
    # 已有条目整体覆盖（ spells 变更时旧 id 不会残留）
    g.setdefault("onyxias_lair", {})["Onyxia"] = ENTRY
    with open(GUIDE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(g, f, ensure_ascii=False, indent=1)
        f.write("\n")

    ic = json.load(open(ICONS, encoding="utf-8"))
    changed = 0
    for sid, slug in ICON_ADD.items():
        if sid not in ic:
            ic[sid] = slug
            changed += 1
    if ic.pop("18431", None) is not None:
        changed += 1
    with open(ICONS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ic, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print("guide injected:", "onyxias_lair" in g, "| icons added:", changed)


if __name__ == "__main__":
    main()
