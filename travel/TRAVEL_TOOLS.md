# Travel Maps Tools

All tools live in `workspace/travel/`. Import from workspace root:

```python
from travel.cli import (
    create_map,
    add_place,
    categorize_place_query,
    list_maps,
    get_map,
    remove_place,
    get_api_stats,
)
```

---

## create_map

```python
create_map(map_id: str, name: str) -> dict
```

Creates a new travel map with three default layers: Eat, Drink, Do.

| Param | Description |
|-------|-------------|
| `map_id` | URL-safe ID, e.g. `"paris-trip"` |
| `name`   | Human-readable name, e.g. `"Paris Trip"` |

Returns the map dict. `map_url` is populated after Drive sync (or `warning` if Drive not configured).

---

## categorize_place_query

```python
categorize_place_query(query: str, location_bias: str | None = None) -> dict
```

Look up a place via Places API and auto-detect its category. **Use this before `add_place` when the category is unknown.** If `followup_question` is non-null, ask the user that question before calling `add_place`.

| Param | Description |
|-------|-------------|
| `query` | Place name or search string |
| `location_bias` | Optional city/region hint, e.g. `"Paris"` |

Returns:
```json
{
  "place": { "name": "...", "address": "...", "lat": 48.8, "lng": 2.3, "place_id": "ChIJ...", "types": [...] },
  "category": "Drink" | "Eat" | "Do" | null,
  "subcategory": "coffee" | "cocktails" | "dessert" | null,
  "followup": "eat_drink_do" | "is_dessert" | "coffee_or_cocktails" | null,
  "followup_question": "Is this a dessert spot?" | null
}
```

---

## add_place

```python
add_place(
    map_id: str,
    query: str,
    category: str,
    subcategory: str | None = None,
    description: str | None = None,
    location_bias: str | None = None,
    manual_address: str | None = None,
) -> dict
```

Add a place to a map. Category and subcategory must be resolved before calling (use `categorize_place_query` + follow-up if needed).

| Param | Description |
|-------|-------------|
| `map_id` | Target map ID |
| `query` | Place name for Places API search |
| `category` | `"Eat"`, `"Drink"`, or `"Do"` |
| `subcategory` | `"dessert"` / `"coffee"` / `"cocktails"` / `None` |
| `description` | Optional note |
| `location_bias` | City hint for Places API |
| `manual_address` | Skip Places API, use this address |
| `place_data` | Pre-fetched place dict from `categorize_place_query`; **pass this to avoid a second API call** |

Returns `{ "place": {...}, "map": {...} }`. Syncs KML to Drive automatically.

**Cost tip:** Always pass `place_data=result["place"]` from `categorize_place_query` into `add_place`. This cuts the API cost per place in half (1 call instead of 2).

### Color rules

| Category | Subcategory | Color |
|----------|-------------|-------|
| Eat | _(default)_ | Blue |
| Eat | dessert | Pink |
| Drink | coffee | Brown |
| Drink | cocktails | Purple |
| Do | _(any)_ | Black |

---

## list_maps

```python
list_maps() -> list[dict]
```

Returns all maps with `id`, `name`, `place_count`, `map_url`, `created_at`.

---

## get_map

```python
get_map(map_id: str) -> dict
```

Returns full map data including all places.

---

## remove_place

```python
remove_place(map_id: str, place_name: str) -> dict
```

Remove a place by exact name. Syncs KML to Drive.

---

## get_api_stats

```python
get_api_stats() -> dict
```

Returns Places API usage counters and estimated cost.

```json
{
  "api_calls": 5,
  "cache_hits": 2,
  "estimated_cost_usd": 0.085
}
```

Cost is estimated at $0.017 per Text Search call. Cache hits are free. Stats persist across sessions in `cache/api_stats.json`.

---

## Conversation patterns

### Creating a map
```
User: "I'm going to Paris, create [paris-trip]"
→ create_map("paris-trip", "Paris Trip")
```

### Adding a place (full flow — cost-optimal)
```
result = categorize_place_query("Café de Flore", location_bias="Paris")
# result.followup is None → auto-resolved as Drink/coffee
# Pass place_data to skip a second API call (saves $0.017)
→ add_place("paris-trip", "Café de Flore", category="Drink",
            subcategory="coffee", location_bias="Paris",
            place_data=result["place"])
```

### Adding an ambiguous place
```
result = categorize_place_query("Angelina", location_bias="Paris")
# result.followup == "eat_drink_do" → ask user
# User says "Eat" → ask "Is this a dessert spot?"
# User says "yes"
→ add_place("paris-trip", "Angelina", category="Eat",
            subcategory="dessert", location_bias="Paris")
```

### Place not found
```
result = categorize_place_query("tiny hidden bar no one knows")
# result.error → "No results found"
# Ask user: "I couldn't find that place. What's the address?"
→ add_place("paris-trip", "Secret Bar", category="Drink",
            subcategory="cocktails",
            manual_address="12 Rue XYZ, 75001 Paris")
```

### Multiple active maps
```
result = list_maps()
# More than one → ask "Which map? [list]"
```
