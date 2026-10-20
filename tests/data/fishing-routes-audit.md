# Fishing-only cooking and preferred fishing waters

Verified 2026-10-19. These are reference geography and NPC supplier records,
not current-client catch-rate observations. The client still overrides recipe
materials, yields, learned state, availability and learning level. NPC purchase
prices were removed on 2026-10-20 and await a separate pricing design.

- [Forever cooking guide](https://www.wowhead.com/forever/cn/guide/professions/cooking/overview-leveling):
  four recipes through 225, spells 7751, 7753, 7755, 20916. Guide quantities
  52/55/120/55 are reference reserves; displayed expected crafts use the existing
  probability model and the selected start/target instead of scaling whole-guide
  fish quantities. Expert/Artisan unlocks remain prerequisites. The 225 Artisan
  quest needs non-fish items and is explicitly outside this crafting-only route.
- [Classic fishing farming guide](https://www.wowhead.com/classic/cn/guide/best-fishing-pools-farming-locations-classic-wow):
  starter inland waters, capital cities except Undercity, Dustwallow inland/coast,
  and Steamwheedle Port are preferred. Coastal/inland distinctions are retained.
  Minimum effective fishing and no-getaway thresholds are different fields;
  neither means fishing must move zones at that point or grants skill each cast.
- 225+: common yellowtail (4603, recipe 18238) is the default. The existing
  Forever catalogue gives 225/265/285/305, so it can still grant skill through
  300. Its fishery has no seasonal/time restriction. Redgill is an inland
  alternative. Client-confirmed unavailability/changed materials are respected.
  Time/season-limited fish are not selected automatically. Whitescale salmon
  is a fallback with an explicit threshold conflict note: the same Classic guide
  gives 205/300 in one paragraph and 330/425 in the species section; use the
  conservative latter values, not a claim of a verified Forever requirement.

Map IDs reuse the addon's existing AreaMap entries. Locations without verified
coordinates open the zone map and never fabricate a pin. No drop-table or
fishery API was assumed for information the client cannot provide.

## Blueprint shelves

Read the visible Forever NPC `Sells` tables through the browser. These recipe
rows had no parenthesized limited-stock marker, unlike limited fishing equipment
on the same shelf; all are single-item purchases paid in gold/silver/copper.
The records below retain supplier identity, faction, stock classification and
one-item purchase quantities. They contain no purchase price, price validation
or estimate. They are added only to `ProfFormulaOffers`, not unlimited reagent
supplies; a known supplier does not turn a missing price into a free formula.

| NPC / source | Formula item IDs |
|---|---|
| [5494](https://www.wowhead.com/forever/cn/npc=5494#sells), Alliance | 6325, 6330, 6368 |
| [5162](https://www.wowhead.com/forever/cn/npc=5162#sells), Alliance | 6326, 6328, 6369, 17062 |
| [3027](https://www.wowhead.com/forever/cn/npc=3027#sells), Horde | 6328, 6330, 21099, 21219 |
| [3029](https://www.wowhead.com/forever/cn/npc=3029#sells), Horde | 6325, 6330 |
| [3333](https://www.wowhead.com/forever/cn/npc=3333#sells), Horde | 6368, 6369, 17062 |
| [8137](https://www.wowhead.com/forever/cn/npc=8137#sells), Neutral | 13939, 13942, 13945, 13946 |

## Validation boundary

Lua 5.1 mocks validate source separation, actual catalogue coverage, quantities,
recipe costs, persistence, imports and map actions. No live game fishing,
profession crafting, character bank/bag inspection or server catch-rate testing
was performed. Fishing time has no gold purchase price in this special route;
it never creates free fish supplies in the ordinary cheapest-route solver.
