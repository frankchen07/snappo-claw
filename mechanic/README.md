# Mechanic Folder

This folder tracks the 2003 Subaru WRX.

## Source of truth
- `data/subaru-impreza-wrx-2003-maintenance-checklist.csv`
  - canonical maintenance history
  - latest service row carries the latest odometer

## Folder structure
- `data/`
  - canonical and structured files
  - maintenance checklist, costs, parts, derived maintenance plan
- `raw/`
  - raw reference material and intake
  - `manuals/` OEM manuals and CEL docs
  - `receipts/` service receipts and invoices
  - `ownership/` title, sale, carfax, initial checks
  - `placeholders/` future-dated placeholder docs for planned parts/services
  - `exports/` raw CSV exports that are not canonical
- `processed/`
  - `current/` live human-readable snapshot
  - `reports/` dated analysis and reconciliation notes
- `scripts/`
  - helper scripts

## Interpretation rules
- If `CURRENT.md` and the checklist disagree, trust the checklist.
- Dated reports are analysis snapshots, not source of truth.
- Placeholder files are intentional and separated from real receipts.

## Current conventions
- Preserve raw filenames exactly as originally stored.
- Add new official service history to the checklist CSV.
- Use processed notes for summaries, dashboards, and reconciled views.
