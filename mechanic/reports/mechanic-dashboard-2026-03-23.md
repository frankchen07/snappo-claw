# Mechanic Dashboard — 2003 Subaru WRX
Date: 2026-03-23

## Snapshot
- Current odometer: **150,211** (user-provided)
- Recent major work: **2026-03-20 @ 150,181 mi** — remachined head + new short block (per notes)
- New engine break-in guidance (user-provided):
  - Keep RPM in **2.5k–3.5k** for first **5,000 mi**
  - Return for oil check in about **3,000 mi** (target ~153,200)
- Incident log:
  - **2026-03-23 16:00** — P0301 cylinder 1 misfire at low RPM/low speed; currently running fine

## Priority Queue (first-pass from checklist CSV)

### Overdue now (by mileage records)
1. Brake fluid flush — next listed at 136,400 (overdue)
2. Clutch fluid flush — next listed at 136,400 (overdue)
3. Oil change + oil filter — next listed at 139,587 (overdue)
4. Wheel alignment — next listed at 140,833 (overdue)
5. Power steering fluid flush — next listed at 142,506 (overdue)
6. Spark plugs — next listed at 142,506 (overdue)

### Due soon
1. Oil change + oil filter + smog entry — next listed at 152,255 (~2,044 mi)
2. Tire rotation — next listed at 155,704 (~5,493 mi)
3. Timing belt + water pump — listed at 156,745 (~6,534 mi), but likely superseded by 2026-01-19 service entry

### Time-based
- Smog check — listed next 2025-06 (likely completed elsewhere; needs verification)
- Battery replacement — listed next 2029-03

## Data Quality / Reconciliation Flags
- Checklist appears to have conflicting/repeated oil entries around 2025-06 and 2025-01 with different "next" values.
- Some intervals likely superseded by engine rebuild timeline (2026-01 to 2026-03); needs a "post-rebuild reset" layer.
- `subaru-impreza-wrx-2003-maintenance-costs.csv` is not normalized (single-column ledger style), so category totals require cleanup before trustable reporting.
- `subaru-impreza-wrx-2003-latest-fixes-20260323.txt` includes mixed narrative/advice content; treat as notes, not authoritative records.

## Recommended Next Actions (immediate)
1. Confirm with mechanic the **post-rebuild service schedule override** (what resets, what carries forward).
2. Set hard check at **153,200 mi** for new-engine oil check and add planned service row now.
3. Add a dedicated row for **P0301 on 2026-03-23** as monitoring incident (with follow-up outcome).
4. Rebuild checklist into two tracks:
   - Historical completed services
   - Current active schedule post-rebuild
5. Normalize costs CSV into tabular schema (date, vendor, category, parts, labor, registration, notes) before deriving totals.

## Confidence (v1)
- High confidence: raw mileage-based due extraction from checklist CSV
- Medium confidence: "overdue" interpretation due to likely superseded records post-rebuild
- Low confidence: cumulative cost category splits until costs file is normalized
