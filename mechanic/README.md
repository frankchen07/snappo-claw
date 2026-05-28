# Mechanic Folder

This folder tracks the 2003 Subaru WRX.

## Source of truth
- `canonical/subaru-impreza-wrx-2003-maintenance-checklist.csv`
  - canonical maintenance history
  - latest service row carries the latest odometer
  - service line items here are what calculations should use

## Folder structure
- `canonical/`
  - canonical and structured files
  - maintenance checklist, costs, parts, derived maintenance plan
- `raw/`
  - raw reference material and intake
  - `manuals/` OEM manuals and CEL docs
  - `receipts/` service receipts and invoices
  - `ownership/` title, sale, carfax, initial checks
  - `placeholders/` future-dated placeholder docs for planned parts/services
- `reports/`
  - `CURRENT.md` is a working notes file
  - dated snapshots and reconciliation notes live here too
- `scripts/`
  - helper scripts

## Interpretation rules
- If `CURRENT.md` and the checklist disagree, trust the checklist.
- Dated reports and snapshots are analysis/history, not source of truth.
- Placeholder files are intentional and separated from real receipts.
- Do not flatten maintenance into one naive mileage timeline.

## Maintenance modeling rule
Use a layered lifecycle model when reconciling what is due:
- engine program anchor
- replaced-component anchors by part/date/odometer
- legacy chassis/body/non-engine anchors

This means due calculations should come from canonical service rows plus part-specific reset logic, not just the most recent odometer alone.

## Current conventions
- Preserve raw filenames exactly as originally stored.
- Add new official service history to the checklist CSV.
- Use `CURRENT.md` for running notes when logging events.
- When notes are ready to freeze, rename `CURRENT.md` into a dated snapshot in `reports/`.
