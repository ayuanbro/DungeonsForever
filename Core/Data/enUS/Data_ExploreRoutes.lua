local gl = (type(GetLocale) == 'function') and GetLocale() or 'zhCN'
if gl ~= 'enUS' then return end

local _, ns = ...

ns.ExploreRoutes = {
    h = {
        { name = "Brill", mapID = 1420, fp = "Tirisfal Glades · Brill", time = "~2 min",
          dst = { 1420, 61.7, 53.3 },
          ovl = { "布瑞尔复活点" },
          races = {
            { race = "Undead", steps = {
              { t = "First death", k = "die", x = 50, y = 56,
                d = "Leave the Deathknell starting area and head to the marked spot; any nearby undead mob works for the first death." },
              { t = "Graveyard resurrect", k = "grave", d = "Resurrect weakened at the Brill graveyard with the spirit healer — no penalty before level 10." },
              { t = "Open flight path", k = "fp", d = "Open the Brill flight path, then set your hearthstone to the Brill inn for later returns.",
                m = { 1420, 61.7, 53.3 } },
            } },
            { race = "Other", steps = {
              { t = "Take the zeppelin", k = "travel", d = "Board the zeppelin tower outside Orgrimmar; it flies straight to Tirisfal Glades and lands at Brill's doorstep." },
              { t = "Open flight path", k = "fp", d = "Enter town, open the Brill flight path and set your hearthstone to the Brill inn.",
                m = { 1420, 61.7, 53.3 } },
            } },
        } },
        { name = "Tarren Mill", mapID = 1424, fp = "Hillsbrad Foothills · Tarren Mill", time = "~4 min",
          dst = { 1424, 62, 20 },
          ovl = { "幽暗城到塔伦米尔" },
          races = {
            { race = "Undead", steps = {
              { t = "Hug the wall", k = "travel", x = 61.3, y = 62.1, m = { 1420, 61.3, 62.1 }, d = "Keep to the right of the Undercity main gate and follow the outer wall; hop onto the wall steps where the ground is rough, switch to walk mode and creep along carefully." },
              { t = "First death", k = "die", x = 68.5, y = 81.5, m = { 1420, 68.5, 81.5 },
                d = "Follow the outer wall until the Alterac Mountains zone banner pops, then die to the owls by the road." },
              { t = "Open flight path", k = "fp", d = "The weakened resurrect lands you at Tarren Mill; open the flight path immediately.",
                m = { 1424, 62, 20 } },
            } },
            { race = "Other", steps = {
              { t = "Hug the wall", k = "travel", x = 61.3, y = 62.1, m = { 1420, 61.3, 62.1 }, d = "Start from Brill; the route is identical to the Undead one — take the zeppelin first if Brill is not open yet. Keep to the right of the Undercity main gate and follow the outer wall; hop onto the wall steps where the ground is rough, switch to walk mode and creep along carefully." },
              { t = "First death", k = "die", x = 68.5, y = 81.5, m = { 1420, 68.5, 81.5 },
                d = "Follow the outer wall until the Alterac Mountains zone banner pops, then die to the owls by the road." },
              { t = "Open flight path", k = "fp", d = "The weakened resurrect lands you at Tarren Mill; open the flight path immediately.",
                m = { 1424, 62, 20 } },
            } },
            { race = "Earthen", time = "~3 min",
              steps = {
              { t = "Board the ship", k = "travel", x = 66.6, y = 83.3, m = { 2521, 66.6, 83.3 },
                d = "Head to the marked spot near Val'zar and hitch the Dalaran ship." },
              { t = "Jump ship", k = "die", d = "Jump off when the ship flies over Hillsbrad Foothills; glide down if you have a glider." },
              { t = "Open flight path", k = "fp", d = "Resurrect at the graveyard, open the Tarren Mill flight path and done.",
                m = { 1424, 62, 20 } },
            } },
        } },
        { name = "Sepulcher", mapID = 1421, fp = "Silverpine Forest · Sepulcher", time = "~5 min",
          dst = { 1421, 43, 40 },
          races = {
            { race = "Undead", steps = {
              { t = "Hearth to Brill", k = "item", d = "After Tarren Mill, hearth back to Brill and head toward Silverpine Forest." },
              { t = "First death", k = "die", d = "Cross into Silverpine Forest and die to the worgs by the road." },
              { t = "Open flight path", k = "fp", d = "Resurrect at the graveyard, open the Sepulcher flight path and fly back to Undercity.",
                m = { 1421, 43, 40 } },
            } },
            { race = "Other", steps = {
              { t = "Hearth to Brill", k = "item", d = "After Tarren Mill, hearth back to Brill and head toward Silverpine Forest." },
              { t = "First death", k = "die", d = "Cross into Silverpine Forest and die to the worgs by the road." },
              { t = "Open flight path", k = "fp", d = "Resurrect at the graveyard, open the Sepulcher flight path and fly back to Undercity.",
                m = { 1421, 43, 40 } },
            } },
        } },
        { name = "Crossroads", mapID = 1413, fp = "The Barrens · Crossroads", time = "~4 min",
          dst = { 1413, 51, 30 },
          ovl = { "十字路口复活点" },
          races = {
            { race = "Other", steps = {
              { t = "Bind hearthstone", k = "item", d = "Leave the starting area for Razor Hill and bind your hearthstone there as the hub." },
              { t = "First death", k = "die", d = "Head west across the Southfury River bridge into the Barrens and die to the zebras by the road." },
              { t = "Open flight path", k = "fp", d = "Drop into the Crossroads graveyard, resurrect weakened and open the flight path.",
                m = { 1413, 51, 30 } },
            } },
            { race = "Tauren",
              steps = {
              { t = "First death", k = "die", x = 50, y = 45,
                d = "Get to Camp Taurajo first, then push north to the Crossroads; die to the tallstriders and hyenas at the graveyard region by the Crossroads on the map." },
              { t = "Open flight path", k = "fp", d = "Resurrect at the Crossroads graveyard and open the flight path.",
                m = { 1413, 51, 30 } },
            } },
        } },
        { name = "Camp Taurajo", mapID = 1413, fp = "The Barrens · Camp Taurajo", time = "~4 min",
          dst = { 1413, 44, 59 },
          ovl = { "陶拉祖营地复活点" },
          races = {
            { race = "Other", steps = {
              { t = "First death", k = "die", x = 51, y = 50,
                d = "Head south from the Crossroads past the marked spot and die there." },
              { t = "Open flight path", k = "fp", d = "The graveyard is beside the camp; get up and open the Camp Taurajo flight path.",
                m = { 1413, 44, 59 } },
            } },
            { race = "Tauren",
              steps = {
              { t = "Enter the Barrens (death)", k = "die", x = 43, y = 60,
                d = "Push east into the Barrens and die to any mob." },
              { t = "Open flight path", k = "fp", d = "Get up and open the Camp Taurajo flight path — the first point of the Tauren line.",
                m = { 1413, 44, 59 } },
            } },
        } },
        { name = "Bloodhoof Village", mapID = 1412, fp = "Mulgore · Bloodhoof Village", time = "~3 min",
          dst = { 1412, 47, 61 },
          ovl = { "血蹄村复活点" },
          races = {
            { race = "Tauren", time = "~1 min", steps = {
              { t = "Bloodhoof Village (death)", k = "die", d = "Die inside the blue area and resurrect at Bloodhoof Village." },
            } },
            { race = "Other", steps = {
              { t = "Cross the bridge south", k = "travel", x = 44, y = 54, m = { 1412, 44, 54 },
                d = "Enter Mulgore over the Southfury River bridge on the west side of the Barrens and follow the main road south." },
              { t = "First death", k = "die", x = 45, y = 62, m = { 1412, 45, 62 },
                d = "Prairie wolves and plainstriders line both sides of the road; die to any of them at the marked spot." },
              { t = "Graveyard resurrect", k = "grave", d = "The weakened resurrect lands you at the Bloodhoof Village graveyard, right by the village." },
              { t = "Bind hearthstone", k = "item", d = "Bind your hearthstone in Bloodhoof Village as the base point, then head for 'Thunder Bluff'." },
            } },
        } },
        { name = "Thunder Bluff", mapID = 1456, fp = "Thunder Bluff · City flight path", time = "~6 min",
          dst = nil,
          races = {
            { race = "Tauren", steps = {
              { t = "First death", k = "die", x = 39.8, y = 41.1, m = { 1412, 39.8, 41.1 },
                d = "Start from Bloodhoof Village (hearthstone bound there); the prairie lions at the marked spot bring you back right below Thunder Bluff." },
              { t = "Open flight path", k = "fp", d = "Resurrect at the graveyard below, ride the lift up and unlock the city flight path." },
            } },
            { race = "Earthen",
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
          dst = { 1454, 49.4, 50.4 },
          ovl = { "奥格瑞玛复活点", "剃刀岭复活点", "试炼谷复活点", "森金村复活点" },
          races = {
            { race = "Tauren", steps = {
              { t = "First death", k = "die", m = { 1411 }, d = "Charge east from the Crossroads into Durotar; after the river, die to the boars." },
              { t = "Open flight path", k = "fp", d = "Resurrect at Razor Hill, run north to Orgrimmar and open the city flight path.",
                m = { 1454, 49.4, 50.4 } },
            } },
        } },
    },
    a = {
        { name = "Silverpine Forest", mapID = 1421, fp = "Silverpine Forest · Graveyard",
          dst = { 1421, 44.2, 41.4 },
          races = {
            { race = "Other", steps = {
              { t = "Set out", k = "travel", x = 17.6, y = 74.8, m = { 1426, 17.6, 74.8 },
                d = "Gather at the novice rest stop and head for Silverpine Forest." },
              { t = "Drown", k = "die",
                d = "Once the zone banner switches to Silverpine Forest, get into the water and drown." },
              { t = "Graveyard resurrect", k = "grave",
                d = "The weakened resurrect lands you at the Silverpine graveyard — the rest of the run is skipped." },
            } },
        } },
    },
}
