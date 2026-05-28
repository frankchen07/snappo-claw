# Mechanic Active Schedule v2 — 2003 Subaru WRX
Date: 2026-03-23

This version replaces the naive "single timeline" approach.
It uses a **layered lifecycle model** so service intervals match component age/state.

## 1) Lifecycle Layers (authoritative model)

### Layer A — New Engine Program (anchor)
- Anchor event: **2026-03-20 @ 150,181 mi**
- Scope: remachined head + new short block/new engine assembly context
- Driving constraint (user): keep RPM **2.5k–3.5k** for first **5,000 mi**
- Follow-up requirement (mechanic): oil check at about **+3,000 mi**

### Layer B — Recently Replaced Components (carry-forward from replacement date/odo)
Use replacement event odometer/date as new interval anchor for that part.
Examples from records:
- Timing belt / water pump: 2026-01-19 @ 150,050
- Spark plugs + boots: 2026-01-19 @ 150,050
- Fuel filter: 2026-01-19 @ 150,050
- Coolant flush: 2026-01-19 (and additional coolant service 2026-01-21)
- Transmission + rear diff fluid flush: 2026-01-19 @ 150,050
- Engine major work: 2026-03-20 @ 150,181

### Layer C — Legacy Chassis / Body / Non-engine systems (age-based + condition-based)
- Suspension, steering rack history, axles, body electrical, seals, interior, etc.
- 2003-age risk persists even when engine is new.
- For condition-based systems, use inspection cadence + symptom triggers.

## 2) Current Active Anchor Values
- Current odometer: **150,211 mi**
- Engine anchor: **150,181 mi**
- Engine break-in window end: **155,181 mi**
- Engine oil follow-up target: **153,181 mi** (about +3,000)

## 3) Active Schedule (reconciled, lifecycle-aware)

## A. DUE NOW / MONITOR NOW
1. **Post-rebuild monitoring** (now to 155,181)
   - Monitor misfire recurrence (P0301 logged 2026-03-23 16:00 at low speed)
   - Monitor idle quality, cold start behavior, abnormal vibration/noise
   - Record each incident with date/odo/context

2. **Fuel/EVAP vigilance**
   - Prior history of fuel smell + small EVAP leak context in notes
   - Keep as active watch item until no recurring symptoms/codes

## B. DUE IN NEXT ~3,000 MI (highest actionable)
1. **Engine oil check / early service follow-up**
   - Target: **153,181 mi**
   - Basis: mechanic instruction after new engine
   - Priority: **Critical**

2. **Break-in behavior enforcement**
   - Through **155,181 mi**
   - Keep RPM generally within instructed band and avoid abusive load events
   - Priority: **High**

## C. DUE IN NEXT ~5,000 TO 10,000 MI (conditional on mechanic confirmation)
1. Oil + filter normalized interval after break-in service
   - First post-break-in anchor should be set at next completed oil service date/odo

2. Rotation/alignment checks
   - Keep condition-based cadence for tire wear and drivability

## D. RECENTLY RESET ITEMS (not currently overdue)
These should not be treated as overdue from old schedule rows:
- Timing belt / water pump (reset 2026-01-19)
- Spark plugs + boots (reset 2026-01-19)
- Fuel filter (reset 2026-01-19)
- Coolant service (reset 2026-01-19 / 2026-01-21)
- Transmission + rear diff fluid service (reset 2026-01-19)
- Engine major rebuild state (reset 2026-03-20)

## 4) What changed vs v1
- Removed blanket "overdue" interpretation from legacy rows that were superseded by recent rebuild-era service.
- Shifted to per-system anchors (engine/new parts/chassis legacy).
- Prioritized near-term operational needs: 3k oil follow-up + 5k break-in window.

## 5) Confirmations received (applied)
1. Break-in service at +3k is a **full oil + filter change**.
2. No early trans/diff recheck required.
3. Coolant remains on standard interval anchored at **150,050**.
4. Spark plugs remain on standard interval anchored at **150,050**.

## 6) Non-engine services to keep active from checklist
1. **Brake fluid flush** — currently appears overdue from prior anchor (106,400; next 136,400).
2. **Clutch fluid flush** — currently appears overdue from prior anchor (106,400; next 136,400).
3. **Wheel alignment** — currently appears overdue from prior anchor (110,833; next 140,833).
4. **Power steering fluid flush** — currently appears overdue from prior anchor (112,506; next 142,506).
5. **Tire rotation** — due around **155,704** (~+5,493 mi from current odometer).
6. **Smog check** — listed next at **2025-06**; verify if already completed after that date.
7. **Battery** — next around **2029-03** (not near-term).
8. **Strut system** — checklist gives mileage target, but treat as condition-based unless symptoms present.

## 7) Operator-ready next actions
1. Add scheduled reminder now:
   - **153,181 mi** full engine oil + filter service
2. Add scheduled reminder now:
   - **155,181 mi** end of break-in window review
3. Log any misfire event with exact context (speed, RPM, gear, engine temp, fuel brand, CEL behavior).
4. At next service, request mechanic to provide a written post-rebuild interval sheet so this tracker can be locked.

## 8) User-selected priority state (current)
### Track actively, but monitor-first unless symptoms
- Brake fluid flush
- Clutch fluid flush
- Wheel alignment
- Power steering fluid flush

### Track and plan normally
- Tire rotation (near-term)
- Smog check (coming up)
- Battery (new; long horizon)

### Condition-based monitor
- Strut/suspension health (user push-test currently feels okay)
