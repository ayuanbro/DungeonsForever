# Fishing-only cooking and preferred fishing waters

Geography references collected 2026-10-19; procurement notes updated 2026-10-20.
These are reference routes and geography, not current-client catch-rate
observations. The client still overrides recipe materials, yields, learned
state, availability and learning level. Old NPC shelves have been removed;
NPC procurement now uses only the generated schema 2 item/NPC records.

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

## Blueprint and ingredient procurement

`Data_ProfFishingRoutes.lua` contains route and fishery information, with no old
blueprint shelf appended. `ProfFormulaOffers` and other old catalogue records
are no longer procurement inputs. Ingredient and formula NPC purchases require
an explicit `Data_ProfItems[item_id].offers[npc_id]` row, a finite nonnegative
integer `cost_copper`, and a positive integer `VendorStackCount`.

Any nonempty `currency_kind`, `currency_id` or `currency_amount`, including zero,
excludes a gold quotation. `stock=-1` is required for unlimited NPC ingredients;
positive formula stock is a refresh cap, never a reading of current inventory.
An item-level cost without an NPC row establishes no supplier. Map coordinates,
the geography references above, and independent formula quest records cannot
supply a missing purchase source or price. See the current
[NPC procurement path](vendor-offers-audit.md) for bundle comparison and source
rules. AH formula quotes and learned-recipe exemptions remain available.

## Validation boundary

Lua 5.1 regressions are intended to check source separation, fishery coverage,
quantities, recipe costs, persistence, imports and map actions; the current full
suite result is recorded separately in `tests/README.md`. No live game fishing,
profession crafting, character bank/bag inspection or server catch-rate testing
was performed. Fishing time has no gold purchase price in this special route;
it never creates free fish supplies in the ordinary cheapest-route solver.
