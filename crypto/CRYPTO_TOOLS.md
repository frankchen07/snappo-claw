# Crypto Module — Function Reference

All functions are importable from `crypto.cli`. Run from `/Users/snappo/.openclaw/crypto/` with the venv active (`.venv/bin/python`), or add the module to PYTHONPATH.

---

## `analyze_coin(symbol, confidence_threshold=0) -> dict`

Analyze a single cryptocurrency using Minervini trend template + CANSLIM scoring.

**Args:**
- `symbol`: Ticker string — "BTC", "ETH", "SOL", etc.
- `confidence_threshold`: Minimum confidence score (0–100) to consider actionable

**Returns:** Full `AnalysisOutput` dict:
```json
{
  "symbol": "BTC",
  "timestamp": "2026-05-10T12:00:00Z",
  "market_trend": {"direction": "uptrend", "strength": "strong"},
  "setup": {"type": "VCP", "quality": 8},
  "entry_zone": {"price": 65000.0, "range": [63050.0, 65650.0]},
  "stop_level": {"price": 60800.0, "invalidation_reason": "Close below 50MA"},
  "targets": [
    {"price": 73200.0, "rr_ratio": 2.0},
    {"price": 77400.0, "rr_ratio": 3.0}
  ],
  "confidence_score": 78,
  "key_signals": ["Trend: uptrend (strong, 8/8 criteria)", "Setup: VCP (quality 8/10)", ...],
  "risk_reward": 2.0,
  "disclaimer": "Not financial advice."
}
```

**Example:**
```python
from crypto.cli import analyze_coin
result = analyze_coin("BTC")
print(f"Trend: {result['market_trend']['direction']} | Setup: {result['setup']['type']} | Confidence: {result['confidence_score']}/100")
```

---

## `scan_watchlist(symbols) -> list[dict]`

Analyze multiple coins in sequence. Returns list of `AnalysisOutput` dicts (errors included as `{"symbol": "X", "error": "..."}`).

**Example:**
```python
from crypto.cli import scan_watchlist
results = scan_watchlist(["BTC", "ETH", "SOL"])
for r in results:
    if "error" not in r:
        print(f"{r['symbol']}: {r['market_trend']['direction']} | {r['setup']['type']}")
```

---

## `search_knowledge(query, limit=5) -> list[dict]`

BM25 keyword search over ingested trading documents. Returns matching framework entries.

**Returns:** List of `{"framework_type": "...", "text": "...", "source": "filename"}` dicts.

**Example:**
```python
from crypto.cli import search_knowledge
results = search_knowledge("trend template")
for r in results:
    print(f"[{r['framework_type']}] {r['text'][:120]}")
```

---

## `ingest_new_documents() -> dict`

Scan `knowledge/raw/` for new or changed files and extract trading frameworks.

**Supported formats:** `.pdf`, `.txt`, `.md`, `.json` (OpenAI ChatGPT export format)

**Drop files here:** `/Users/snappo/.openclaw/crypto/knowledge/raw/`

**Returns:** `{"processed": int, "errors": int, "new_frameworks": int}`

**Example:**
```python
from crypto.cli import ingest_new_documents
result = ingest_new_documents()
print(f"Ingested {result['processed']} docs, extracted {result['new_frameworks']} frameworks")
```

---

## `health_check() -> dict`

Check cache and directory status.

**Example:**
```python
from crypto.cli import health_check
print(health_check())
# {"cache_status": {"total_entries": 3, "fresh": 2, "stale": 1}, ...}
```

---

## Minervini Trend Template (8 Criteria)

All must be true for "uptrend" classification:

1. Current price > 150-day MA
2. 150-day MA > 200-day MA
3. 200-day MA slope is positive (30-day proxy)
4. 50-day MA > 150-day MA
5. 50-day MA > 200-day MA
6. Current price > 50-day MA
7. Price within 25% of 52-week high
8. Price at least 30% above 52-week low

**Strength:** strong = 8/8 + steep slope | moderate = 6–7 | weak = 4–5

---

## Setup Types

| Type | Description |
|------|-------------|
| `VCP` | Volatility Contraction Pattern — tightening price range → breakout on volume |
| `breakout` | Price clears recent high on ≥1.3× average volume |
| `flat_base` | Tight sideways consolidation (≤12% range) over 35+ days |
| `none` | No actionable setup detected |

---

## Logs

All function calls are logged as JSON to:
`/Users/snappo/.openclaw/crypto/logs/crypto.log`
