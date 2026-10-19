# -*- coding: utf-8 -*-
"""把本轮任务注释新字符串的 enUS 翻译追加到 enus_data_quests2.py（QUESTS2B）。
zh 键直接取自当前数据文件缺映射的真实字符串，保证逐字节一致。幂等：已有 QUESTS2B 则跳过。
"""
import json
import enus_data as D1, enus_data_prof, enus_data_quests as DQ1, enus_data_quests2 as DQ2
import enus_data_names as DN, enus_data_names2 as DN2, enus_data_names3 as DN3
import enus_data_names_hand as DH, enus_data_prose as DP, enus_data_resid as DR
import enus_data_whguide as DW, enus_data_guide19 as DG19, enus_data_tier as DT

PATH = 'enus_data_quests2.py'

EXACT = dict(D1.EXACT); EXACT.update(enus_data_prof.PROF); EXACT.update(D1.ZONES)
EXACT.update(D1.DUNGEONS); EXACT.update(D1.BOSSES); EXACT.update(D1.TOKENS)
EXACT.update(DN.Q); EXACT.update(DN.N); EXACT.update(DN2.Q); EXACT.update(DN2.N); EXACT.update(DN3.H)
EXACT.update(DQ1.QUESTS); EXACT.update(DQ2.QUESTS2); EXACT.update(DH.HAND)
EXACT.update(DP.FREE); EXACT.update(DR.RESID); EXACT.update(DW.FREE); EXACT.update(DG19.FREE)

EN = {
    17: "The Magenta Fungus Caps are scattered in the cave BEFORE the instance (not inside), mostly by campfires and behind tents; with Herbalism tracking on they show up on the minimap. Each step also grants 250 Ironforge reputation. The prerequisite quest is taken from the same NPC.",
    167: "Badges drop from Foreman Thistlenettle right by the dungeon entrance. ◎ For solo runs wait until level 23 or so: the elites hit hard and chain-pull, and the quest mob is linked to another add.",
    168: "Union cards drop from the undead near the dungeon entrance. ◎ The drop rate is very low and they are NOT shared among the group (everyone loots their own) — expect a long grind.",
    386: "Targorr is inside the dungeon. He usually spawns in the first cell on the right or the second cell on the left of the central wing; rarely, in the northernmost cell between the two wings.",
    914: "The chain starts with Hamuul Runetotem (Thunder Bluff - Elder Rise 78,28). The four gem-dropping druids are spread across four separate chambers inside the dungeon. ◎ The gems are for everyone: each of the four leaders drops one gem for every party member on the quest.",
    971: "The manuscript lies in a pool inside the dungeon — in the water area of the turtle-king room: an underwater alcove chest on the right as you enter, guarded by 1-2 naga (single-pullable).",
    1013: "The book is on the bookshelf in Fenrus' (the great worg) room — bottom shelf of the first bookcase on the left as you enter, a blue book. ◎ It respawns after about 10 seconds, so every party member can loot one (not shared). ◎ When Fenrus dies he summons 4 Voidwalkers (non-elite but they hit hard; rogues/cats can drop combat early with Vanish/Prowl).",
    1098: "Deathstalker Adamant is inside the dungeon; Deathstalker Vincent is to the right after entering the courtyard. For the first part you must release the imprisoned deathstalker before the courtyard door opens; the second one can be seen tormented by Arugal right as you enter — work your way around to free him.",
    1109: "Only the Kraul Bats in the far-west chamber (just before the last boss, Charlga Razorflank) drop the guano — with a very high drop rate — and you must fight through most of the dungeon to reach them.",
    1139: "The tablet is inside the dungeon, right beside Galgann Firehammer.",
    1144: "The escort fails if you get too far ahead of him or fall too far behind. Turn right from the entrance through the boar area to reach Willix — no bosses need to be cleared.",
    1160: "The chain starts with Dorn Plainstalker (Thousand Needles 53,41). The book is in the Scarlet Monastery Library: an open book on the table in the first room on the left as you enter the Gallery of Treasures.",
    1198: "Thaelrid is inside the dungeon. He is underwater on the southwest side of the turtle pool.",
    1199: "Every Twilight's Hammer enemy in the dungeon drops a pendant. ◎ Players report the current turn-in awards all 3 reward items at once (likely a bug).",
    1318: "Doable in one run. Recommended route: North first (tribute run — bring the ogre-suit materials and the broken trap) → West (kill Immol'thar) → Library (kill Prince Tortheldrin) → back to North, turn in to Fengus on the way out.",
    1446: "Jammal'an is inside the dungeon. You must first clear the ring of ghosts on the balconies (the undead trolls holding his barrier) before he can be engaged.",
    1475: "Take the prerequisite here. The tablets can all be looted BEFORE the instance: 1 underwater in the center of the entrance hall and 1 on each of the two side tables, respawning about every 8 minutes — wait a bit and even a full group gets theirs.",
    1701: "Warrior only! The phosphorus comes from Roogug; Scorched Spider Fangs from Wetlands spiders, and Charred and Sleek Chimera Horns from chimera cubs and females in Stonetalon Mountains. Roogug location: take the first left inside the dungeon, follow the curve over the vine bridge — he is right there on the other side.",
    1956: "Mage only! The power source drops from the Obsidian Sentinel. The sentinel is right inside the back door — enter from the Badlands back entrance (67,44) and it is the first thing you see, with no guarding adds.",
    2200: "The paladin is inside the dungeon: the body is in the northwest corner of the Hall of the Keepers (the first sideways-'8' shaped area), marked with a yellow '?' — no searching required.",
    2280: "After killing Archaedas, walk into the vault behind him and click the disc on the pedestal to accept the quest; after listening to the summoned ghost's full story, click the disc AGAIN to receive the miniature — miss this step and you have to run the dungeon again. Turn in at Thunder Bluff (NPC around 35,47).",
    2284: "The paladin is inside the dungeon: enter and keep hugging the wall on your right — it leads straight to the body.",
    2398: "Ballog is inside the dungeon. Breadcrumb quest: it cannot be completed if you have already accepted or completed 'The Hidden Chamber'.",
    2418: "Dark Iron enemies inside and outside the dungeon drop the power stones. No need to enter the dungeon — killing the Dark Iron dwarves at the dig site outside the entrance is enough.",
    2843: "The prerequisite is from Sovik (Orgrimmar - Valley of Honor 75,25). Completing it lets you use the Booty Bay teleporter. ◎ The goblin transponder can be discarded after use; if you lose it, just tell Scooty and you get another.",
    2865: "The optional prerequisite starts with Krazek (Stranglethorn Vale - Booty Bay 25,77) — not required, the quest can be taken directly. Every scarab drops a shell; the scarab hall has the densest concentration.",
    2904: "Escort quest. Scooty is in Stranglethorn Vale - Booty Bay (27,77). The escort ends at the dungeon's FRONT entrance (deliver him to the door; no need to go through); the little gnome won't pull adds on his own, so stealth classes can do the whole quest while stealthed.",
    2930: "The optional prerequisite is from Gaxim Rustfizzle (Stonetalon Mountains 59,67). Punch-card relay: the White Punch Card drops from the wandering elites on the upper level outside the instance; insert it into the card reader outside the instance, and each reader gives you the card for the next one — grab Techbot's brain along the way.",
    2936: "The chain begins with the Vial series from the troll village in the Hinterlands. The tablet is inside the dungeon. Stealth classes can sneak straight to the tablet and finish reading it without fighting Theka the Martyr; the scarabs are neutral — just avoid AOE.",
    2991: "The chain starts with the gryphon master at Aerie Peak, Hinterlands (9,44). Nekrum is inside the dungeon: he spawns in the final wave that comes up the great stairs after Bly is freed.",
    3446: "The altar is on the map. Inside the dungeon take the right-hand stairs down into the 'Pit of Refuse' — the Altar of Hakkar is right there.",
    3447: "The statues are inside the dungeon; activate them in this order: South → North → Southwest → Southeast → Northwest → Northeast.",
    3523: "This is not the escort quest itself — complete this one first, and only then the real escort quest 'Extinguishing the Idol' becomes available. Make sure EVERYONE in the party finishes this quest before starting the escort segment, or those who haven't will miss the follow-up.",
    3636: "He is the final boss of Razorfen Downs. ★ This quest cannot be shared — everyone in the party must pick it up for themselves.",
    4024: "The chain starts with Kharan Mighthammer (Burning Steppes 39,38). Bael'Gar is inside the dungeon. Don't forget to use the molt item from your bags while standing on Bael'Gar's corpse — it's easy to miss.",
    4134: "The prerequisite is given by Apothecary Zinge (Undercity - The Apothecarium 50,68). After smashing the barrels Hurley shows up with elite guards, and EVERY spawned guard drops a recipe (one per party member); if you wipe, the barrels despawn and the instance must be reset to try again.",
    4143: "The prerequisite 'Muigin and Larion' starts with Muigin (Un'Goro Crater - Marshal's Refuge 42,9). Temple deep lurkers, dark crawlers and fused oozes all drop it. You MUST go inside the instance — the oozes outside don't drop it. Take the right-hand stairs down inside the entrance to reach the lurker/ooze area.",
    4146: "The prerequisite 'Larion and Muigin' starts with Larion (Un'Goro Crater 45,8). Temple deep lurkers, dark crawlers and oozes all drop it. You MUST go inside the instance — the oozes outside don't drop it. Take the right-hand stairs down inside the entrance to reach the lurker/ooze area.",
    4242: "Marshal Windsor is held in a cell inside the dungeon (the key drops from High Interrogator Gerstahn). There is no immediate follow-up after turning this in: go back into BRD and keep killing mobs until 'A Crumpled Up Note' drops to continue the chain.",
    4264: "'A Crumpled Up Note' drops randomly inside BRD. Marshal Windsor is in the BRD prison — don't mix the two up: Marshal Maxwell is at Morgan's Vigil in the Burning Steppes.",
    4322: "Before starting the Jail Break (the Windsor escort), make sure everyone in the party has turned in the previous quest, or some members won't get credit. After completing it you MUST talk to Windsor before leaving the dungeon — running straight out means doing it all over again.",
    4734: "The eggs are in the Father Flame's room. After freezing an egg do NOT click it — use the device from your backpack; after killing General Drakkisath you can jump straight down to the rookery and finish it separately.",
    4735: "The eggs are all in the Father Flame's room. After freezing an egg, get close and use the device from your backpack (don't click the egg); if the raid won't wait, jump down to the rookery after the General to finish it solo.",
    4743: "Use the Unforged Seal in the water below the dragon to start the forging event. Each event yields only ONE lootable forged seal, and the dragon has a 3-hour cooldown — only one person can do it per night.",
    4764: "The prerequisite can be taken from Lord Remington Ridgewell (Stormwind City - Stormwind Keep 77,47). The clasp is in the chest in the Father Flame's room. The chest respawns about every 20 seconds, so multiple party members can open it in turn.",
    4768: "The prerequisite can be taken from Apothecary Zinge (Undercity - The Apothecarium 50,68). The tablet is in the UBRS rookery (the hatchery).",
    4788: "The 5th tablet is in Shadow Hunter Vosh'gajin's room, the 6th in War Master Voone's room. The reward comes from 'Facing Yeh'kinya'; Yeh'kinya is right beside Prospector Ironboot.",
    4862: "The spider eggs are inside the dungeon. Looting an egg can randomly spawn small spiders — they hit hard and have an AOE, watch out.",
    4867: "Flow: kill Omokk first for the head; the pike is inside the dungeon — use it to summon (several ogre packs spawn first; you can attack them with the pike). ◎ Only ONE person per spawn can turn this in — once turned in, he turns into his ogre form and no longer has the yellow '?'.",
    5127: "Blacksmithing quest. Goraluk is inside the dungeon. Requires Blacksmithing 270 to pick up.",
    5213: "The small box spawns randomly in ONE of the three ziggurats (Nerub'enkan, Baroness Anastari, Maleki); it does not disappear — every party member can loot it.",
    5214: "The tobacco shop is inside the dungeon: keep turning left to the dead end, to the right of the well — clear everything along the way. Fras Siabi appears the moment you open the box.",
    5243: "The holy water is in crates all over the city; some are fakes that burst into a swarm of bugs. Dwarves can use 'Find Treasure' to mark the real crates on the minimap.",
    5251: "The archives and the Archivist are both inside the dungeon. ◎ If you are also doing 'Of Love And Family': grab the painting BEFORE burning the archives — the painting burns together with them.",
    5282: "The prerequisite is from Caretaker Alen (Eastern Plaguelands - Light's Hope Chapel 74,58). Ghostly citizens wander all over the city. About 10 seconds after zapping a ghost with the blaster, a 'Restless Soul' appears beside it — zap that one too and you can loot it.",
    5305: "The Crimson Hammersmith is a triggered spawn: click the 'Blacksmithing Plans' parchment on the ground to trigger it.",
    5307: "The Dark Iron Guardsmith is a triggered spawn: click the 'Blacksmithing Plans' parchment on the ground next to the pawn shop beside Anastari's ziggurat.",
    5341: "Deed locations: Caer Darrow = in the first hall after entering; Southshore = on the desk in the left corner of the first large hall after crossing the bridge; Tarren Mill = on the desk in the right corner of the room before the whelps; Brill = in the room where Ras Frostwhisper is.",
    5382: "After the doctor dies, look at the piles of flesh on both sides of the room — the remains of Eva and Lucien Sarkhoff are inside; clear them to complete.",
    5384: "The vestibule is inside the dungeon. The Blood of Innocents drops 100% from the succubus in the first room; if the summoned Kirtonos doesn't drop the reward you want, abandon and re-take the quest (the instance must be reset to summon again).",
    5463: "The prerequisite is from Magistrate Marduke (Western Plaguelands - Caer Darrow 70,73). The mark is the pentagram on the floor of the Baron's room. See also 'Lich Ras Frostwhisper' in Scholomance.",
    5515: "Jandice Barov is inside the dungeon. Only the real body has a health bar among the clones — turn on nameplates (V) or mark the real one, and only hit the one with the bar.",
    5582: "You must complete 'Plagued Hatchlings' first, otherwise the lootable Healthy Dragon Scales won't appear. The scales drop from Plagued Hatchlings (about 8%). Betina Bigglezink is at Eastern Plaguelands - Light's Hope Chapel (76,54).",
    5724: "Maur Grimtotem is on a raised ledge to the right of a fork deep in the dungeon — walk to the T junction at the end, take the right-hand path up the slope, and the small room on the left of the landing is where he is.",
    5848: "The prerequisite is from Tirion Fordring (Western Plaguelands 7,43). The painting is in the Archivist's room on the living side, on the right as you enter.",
    6521: "The prerequisite is given by Razorfen Kraul's final boss. Ambassador Malcin stands in the open ground before the dungeon entrance (The Barrens - Razorfen Downs 48,92).",
    6921: "The Fathom Core is in the water inside the dungeon. Once you take it, Baron Aquanis will appear and attack — he drops a quest item; bring that to Je'neu Sancrea as well. The core is underwater in the center of the big pool before the last boss (no need to enter the boss's room).",
    7028: "Most enemies in Maraudon drop the figurine; the Nameless Prophet has the best drop rate and respawns nearby almost immediately after dying — great for fast farming.",
    7029: "Fill the vial at the big outdoor pool with orange crystals (not the small pool the dryad stands in); the vines are in the orange area — use the vial next to a flower to summon a flower and an elemental; kill both and the completion is shared by the whole group.",
    7046: "The scepter is crafted by Celebras himself; talk to him after the ritual. If you lose the scepter, kill Celebras again and choose 'I lost my scepter' in the dialog to get another.",
    7067: "'The Pariah's Instructions' mentions the 5 khans. The Nameless Prophet drops the Amulet of Spirits, which is used to materialize the 5 khans.",
    7481: "Kariel Winthalus is in the Dire Maul West library. The skeleton is in the center of the library, next to Lorekeeper Lydros.",
    7482: "Kariel Winthalus is in the Dire Maul West library. His skeleton is in the center of the library, next to Lorekeeper Lydros.",
    7508: "'Foror's Compendium of Dragon Slaying' (drops in Dire Maul, tradeable) triggers the Quel'Serrar quest chain: hand the book to the lorekeeper in the Dire Maul West library to receive the 'Dull and Flat Elven Blade' and begin this epic weapon quest.",
    7629: "Warlock only! The alchemy lab is in the same room as Ras Frostwhisper.",
    7703: "The prince is in Dire Maul West; the strength gauntlets are in the chest near him. Recommended order: North first — do the tribute run and keep the 'Good to be King' buff → West to kill the prince and open the chest → back to North to turn in.",
    8425: "Warrior class quest. The 6 little trolls are the undead trolls holding Jammal'an's barrier — up the stairs and turn right as you enter (not the spiral staircase).",
    8949: "Ogre Warbead drop rates: about 1/10 in Dire Maul North, 1/7 in LBRS (but far fewer ogres there), 1/50 outside the DM arena.",
    8950: "The shadow essence drops from the ghosts in Dire Maul West.",
    9015: "The follow-ups differ by class. Arena event: when the yell goes out, plant the Banner of Provocation in the center of the arena to start the fight. ◎ The chest MUST be looted first by the person on the quest, otherwise nobody can loot the trinket (player-reported).",
    9053: "Druid class quest. The vines drop from the summoned Atal'alarion; you must first solve the statue puzzle correctly. Statue order by minimap clock: 6 → 12 → 8 → 4 → 10 → 2 (correct hits light the statues green).",
    92747: "Part of the toxin-investigation chain: samples from several mines all point to the Deadmines beneath Moonbrook. Collect supplies in Moonbrook and turn them in to Alba Fairmoon, which starts the explosives-materiel phase. Sample points of the prerequisite ring 'Log Test': Morlsen Farm 46.2,38.3 and Jensen Farm 56.7,18.7. ◎ The supply crates are in the cave on the way to the Deadmines entrance, and scattered in buildings all over Moonbrook (including the Moonbrook schoolhouse) — no elites need to be fought.",
    92753: "The dungeon segment of the chain: before entering, the explosives are already prepared by the materiel phase (Sprite Jumpsprocket → Jasper Fel). After planting them, exit the dungeon and meet Alba Fairmoon on the hill behind Moonbrook. ◎ The forge is the room where Gilnid spawns — plant the explosives near the center; after this run do NOT hearth out: leave through the back door and continue the quest at the back entrance.",
    95189: "Starts inside the dungeon (the 'Crest of Lordaeron' has multiple spawn points; looting one starts the quest); turn in back in Stormwind City with Lady Dena Kennedy. ◎ No '!' shows on the minimap — you have to search yourself. Known spawn points: top of the tower by the spider courtyard, top of the tower by The Abandoned, behind the door guarded by the banshee in the spider courtyard, and on the floor of the locked-door room across from Bjork's courtyard.",
    95250: "Captain Truman (Alliance quartermaster, hostile to the Horde) is on the left as you enter the dungeon; the objective is the Baron's head — don't rush out after killing him; turn the quest in to Truman himself.",
    95795: "Pick up directly on Daywin's body inside the dungeon; choose one of two belt rewards.",
    95809: "Started by the Reed-woven Heart (#270901), a token Aldin gives after completing the shrub-search quest.",
    95810: "Started by looting the Titan Relic (#270865); the Alliance turn-in is Prospector Whelgar (#1077) at Whelgar's Excavation Site.",
    96393: "Pick-up start: first loot the 'Dark Iron Map' from the Dark Iron dwarves in the southeast corner of Dun Morogh (about 77,60) and hand it to Earthseer Farsen — only then is this quest offered.",
    96394: "Easily completed in one run. The target NPC is in the newly added dungeon-entrance area to the LEFT of the High Seat (the king's room).",
    96395: "The quest starts and ends inside the dungeon.",
    96403: "The quest items are sprinkled all over the dungeon and don't all look the same — run your mouse over walls, chairs and tables to spot them; the room behind the last boss's vault has the highest concentration.",
    97288: "Starts inside the dungeon (the 'Abomination's Head' dropped by The Baron — looting it starts the quest); turn in back in Undercity with Master Apothecary Faranell. ◎ The head quest can be shared (accepting puts the head straight into party members' bags). Use the quest item at the green ooze pool up the stairs to the right (by the big worm outside the Apothecarium).",
}

m = json.load(open('_q_notes_map.json', encoding='utf-8'))
def has_cjk(s): return any('\u4e00' <= ch <= '\u9fff' for ch in s)
missing = {}
for d, rows in m.items():
    for r in rows:
        n = r['note']
        if n and has_cjk(n) and n not in EXACT:
            missing.setdefault(n, []).append(r['id'])

src = open(PATH, encoding='utf-8').read()
if 'QUESTS2B' in src:
    print('QUESTS2B already present — skip append')
else:
    lines = ['', '', '# ===== 2026-10-04 全任务评论精选（方案 1 全量采纳）：注释注释新稿 =====', 'QUESTS2B = {']
    n_ok = 0
    for zh in sorted(missing, key=lambda k: missing[k][0]):
        qid = missing[zh][0]
        en = EN.get(qid)
        if en is None:
            print('!! no EN for qid', qid, zh[:40]); continue
        key = zh if '"' not in zh else repr(zh)
        val = '"' + en.replace('\\', '\\\\').replace('"', '\\"') + '"'
        lines.append('    %s:\n        %s,' % (repr(zh), val))
        n_ok += 1
    lines.append('}')
    lines.append('QUESTS2.update(QUESTS2B)')
    with open(PATH, 'a', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('appended %d entries' % n_ok)
