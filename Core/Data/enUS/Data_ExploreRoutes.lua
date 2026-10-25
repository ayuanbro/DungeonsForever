local gl = (type(GetLocale) == 'function') and GetLocale() or 'zhCN'
if gl ~= 'enUS' then return end

local _, ns = ...

ns.ExploreRoutes = {
    h = {
        { name = "Brill", mapID = 1420, fp = "Tirisfal Glades · Brill", time = "~2 min",
          mech = "Death-run unlocks: let a mob kill you, resurrect weakened at the nearest graveyard (no penalty before level 10), then open the flight path right beside it.",
          dst = { 1420, 61.7, 53.3 },
          races = {
            { race = "Undead", steps = {
              { t = "First death", k = "die", x = 50, y = 56,
                d = "Leave the Deathknell starting area and head to the marked spot; any nearby undead mob works for the first death." },
              { t = "Graveyard resurrect", k = "grave", d = "Resurrect weakened at the Brill graveyard with the spirit healer." },
              { t = "Open flight path", k = "fp", d = "Open the Brill flight path, then set your hearthstone to the Brill inn for later returns.",
                m = { 1420, 61.7, 53.3 } },
            } },
            { race = "Orc · Troll", steps = {
              { t = "Take the zeppelin", k = "travel", d = "Board the zeppelin tower outside Orgrimmar; it flies straight to Tirisfal Glades and lands at Brill's doorstep." },
              { t = "Open flight path", k = "fp", d = "Enter town, open the Brill flight path and set your hearthstone to the Brill inn.",
                m = { 1420, 61.7, 53.3 } },
            } },
        } },
        { name = "Tarren Mill", mapID = 1424, fp = "Hillsbrad Foothills · Tarren Mill", time = "~4 min",
          mech = "Hug the Undercity outer wall to reach the Alterac Mountains border, die once, and resurrect right at Tarren Mill.",
          dst = { 1424, 62, 20 },
          races = {
            { race = "Undead", steps = {
              { t = "Hug the wall", k = "travel", d = "Keep to the right of the Undercity main gate and follow the outer wall; hop onto the wall steps where the ground is rough, switch to walk mode and creep along carefully." },
              { t = "First death", k = "die", x = 68.5, y = 81.5, m = { 1420, 68.5, 81.5 },
                d = "Follow the outer wall until the Alterac Mountains zone banner pops, then die to the owls by the road." },
              { t = "Open flight path", k = "fp", d = "Resurrect weakened and open the Tarren Mill flight path immediately.",
                m = { 1424, 62, 20 } },
            } },
            { race = "Orc · Troll",
              mech = "Start from Brill; the route is identical to the Undead one. Take the zeppelin first if Brill is still unlocked.",
              steps = {
              { t = "Hug the wall", k = "travel", d = "Keep to the right of the Undercity main gate and follow the outer wall; hop onto the wall steps where the ground is rough, switch to walk mode and creep along carefully." },
              { t = "First death", k = "die", x = 68.5, y = 81.5, m = { 1420, 68.5, 81.5 },
                d = "Follow the outer wall until the Alterac Mountains zone banner pops, then die to the owls by the road." },
              { t = "Open flight path", k = "fp", d = "Resurrect weakened and open the Tarren Mill flight path immediately.",
                m = { 1424, 62, 20 } },
            } },
            { race = "Earthen", time = "~3 min",
              mech = "Earthen shortcut: hitch the Dalaran ship, jump over Hillsbrad Foothills, resurrect at the graveyard and open the flight path — the whole wall walk is skipped.",
              steps = {
              { t = "Board the ship", k = "travel", x = 66.6, y = 83.3, m = { 2521, 66.6, 83.3 },
                d = "Head to the marked spot near Val'zar and hitch the Dalaran ship." },
              { t = "Jump ship", k = "die", d = "Jump off when the ship flies over Hillsbrad Foothills; glide down if you have a glider." },
              { t = "Open flight path", k = "fp", d = "Resurrect at the graveyard, open the Tarren Mill flight path and done.",
                m = { 1424, 62, 20 } },
            } },
        } },
        { name = "Sepulcher", mapID = 1421, fp = "Silverpine Forest · Sepulcher", time = "~5 min",
          mech = "Hearth back to Brill, push south into Silverpine Forest, then fly back to Undercity for quests.",
          dst = { 1421, 43, 40 },
          races = {
            { race = "Undead", steps = {
              { t = "Hearth to Brill", k = "item", d = "After Tarren Mill, hearth back to Brill and head toward Silverpine Forest." },
              { t = "First death", k = "die", d = "Cross into Silverpine Forest and die to the black wolves by the road." },
              { t = "Open flight path", k = "fp", d = "Resurrect at the graveyard, open the Sepulcher flight path and fly back to Undercity.",
                m = { 1421, 43, 40 } },
            } },
            { race = "Orc · Troll", steps = {
              { t = "Hearth to Brill", k = "item", d = "After Tarren Mill, hearth back to Brill and head toward Silverpine Forest." },
              { t = "First death", k = "die", d = "Cross into Silverpine Forest and die to the black wolves by the road." },
              { t = "Open flight path", k = "fp", d = "Resurrect at the graveyard, open the Sepulcher flight path and fly back to Undercity.",
                m = { 1421, 43, 40 } },
            } },
        } },
        { name = "Crossroads", mapID = 1413, fp = "The Barrens · Crossroads", time = "~4 min",
          mech = "Death-drop to the target graveyard and open the flight path on resurrect; bind your hearthstone to Razor Hill as the hub.",
          dst = { 1413, 51, 30 },
          races = {
            { race = "Orc · Troll", steps = {
              { t = "Bind hearthstone", k = "item", d = "Leave the starting area for Razor Hill and bind your hearthstone there as the hub." },
              { t = "First death", k = "die", d = "Head west across the Southfury River bridge into the Barrens and die to the zebras by the road." },
              { t = "Open flight path", k = "fp", d = "Drop into the Crossroads graveyard, resurrect weakened and open the flight path.",
                m = { 1413, 51, 30 } },
            } },
            { race = "Tauren",
              mech = "Tauren do 'Camp Taurajo' first, then push north — only one death and the unlock left here.",
              steps = {
              { t = "First death", k = "die", x = 50, y = 45,
                d = "Push north from Camp Taurajo to the Crossroads; the tallstriders and hyenas at the marked spot work." },
              { t = "Open flight path", k = "fp", d = "Resurrect at the Crossroads graveyard and open the flight path.",
                m = { 1413, 51, 30 } },
            } },
        } },
        { name = "Camp Taurajo", mapID = 1413, fp = "The Barrens · Camp Taurajo", time = "~4 min",
          mech = "Follow the main road south through the Barrens; the graveyard sits right beside the camp.",
          dst = { 1413, 44, 59 },
          races = {
            { race = "Orc · Troll", steps = {
              { t = "First death", k = "die", d = "Follow the main road south and die to the plainstriders at the marked spot." },
              { t = "Open flight path", k = "fp", d = "The graveyard is beside the camp; get up and open the Camp Taurajo flight path.",
                m = { 1413, 44, 59 } },
            } },
            { race = "Tauren",
              mech = "Tauren start in Mulgore; bind the hearthstone to Bloodhoof Village and push east into the Barrens.",
              steps = {
              { t = "First death", k = "die", x = 38, y = 75,
                d = "Leave the starting area for the marked spot and die to the prairie wolves." },
              { t = "Graveyard resurrect", k = "grave", d = "Bind your hearthstone to Bloodhoof Village as the base point." },
              { t = "Second death", k = "die", x = 43, y = 60,
                d = "Push east into the Barrens and die to the lightning lizards at the marked spot." },
              { t = "Open flight path", k = "fp", d = "Get up and open the Camp Taurajo flight path — the first point of the Tauren line.",
                m = { 1413, 44, 59 } },
            } },
        } },
        { name = "Thunder Bluff", mapID = 1456, fp = "Thunder Bluff · City flight path", time = "~6 min",
          mech = "The city sits on the mesa: resurrect at the graveyard below and ride the lift; Earthen glide straight onto the main rise.",
          dst = nil,
          races = {
            { race = "Tauren", steps = {
              { t = "First death", k = "die", x = 39.8, y = 41.1, m = { 1412, 39.8, 41.1 },
                d = "Start from Bloodhoof Village (hearthstone bound there); the prairie lions at the marked spot bring you back right below Thunder Bluff." },
              { t = "Open flight path", k = "fp", d = "Resurrect at the graveyard below, ride the lift up and unlock the city flight path." },
            } },
            { race = "Earthen",
              mech = "Earthen only: take the ship to Thunder Bluff, jump from height and glide onto the main rise; after unlocking, glide down and die once.",
              steps = {
              { t = "Board the ship", k = "travel", x = 58.1, y = 80.3, m = { 2521, 58.1, 80.3 },
                d = "Board the ship at the marked spot near Val'zar." },
              { t = "Jump and glide", k = "travel", d = "When the ship reaches the mesa, face the Spirit Rise and jump; open the glider mid-air to land on the edge." },
              { t = "Open flight path", k = "fp", d = "Run the rises to the main peak and unlock the city flight path." },
              { t = "First death", k = "die", x = 42.5, y = 51.5, m = { 1412, 42.5, 51.5 },
                d = "Skip the lift and glide down to the foot of Thunder Bluff; die at the marked spot." },
              { t = "Graveyard resurrect", k = "grave", d = "After resurrecting at Bloodhoof Village, the rest matches the 'Camp Taurajo' (Tauren) route." },
            } },
        } },
        { name = "Orgrimmar", mapID = 1454, fp = "Orgrimmar · City flight path", time = "~3 min",
          mech = "Tauren line finale: push north from Razor Hill and grab the city flight path to finish the loop.",
          dst = { 1454, 49.4, 50.4 },
          races = {
            { race = "Tauren", steps = {
              { t = "First death", k = "die", d = "Charge east from the Crossroads into Durotar; after the river, die to the boars." },
              { t = "Open flight path", k = "fp", d = "Resurrect at Razor Hill, run north to Orgrimmar and open the city flight path.",
                m = { 1454, 49.4, 50.4 } },
            } },
        } },
    },
    a = {
    },
}
