#!/usr/bin/env python3
import csv
import argparse
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "maintenance-plan.csv"


def to_int(v):
    try:
        return int(str(v).strip())
    except Exception:
        return None


def main():
    p = argparse.ArgumentParser(description="Show maintenance table + next 3-5k checklist")
    p.add_argument("mileage", type=int, help="Current odometer mileage")
    p.add_argument("--horizon", type=int, default=5000, help="Lookahead miles (default 5000)")
    args = p.parse_args()

    rows = list(csv.DictReader(DATA.open()))
    cur = args.mileage
    horizon = args.horizon

    print(f"Current mileage: {cur:,}")
    print(f"Window: now to +{horizon:,} miles ({cur:,} to {cur+horizon:,})\n")

    print("=== Maintenance Table (Mileage-based items) ===")
    print("Item | Due | Miles Left | Priority | Status")
    print("---|---:|---:|---|---")

    due_now = []
    due_window = []

    for r in rows:
        due = to_int(r.get("due_mileage"))
        if due is None:
            continue
        left = due - cur
        print(f"{r['item']} | {due:,} | {left:+,} | {r['priority']} | {r['status']}")

        if left <= 0:
            due_now.append((left, r))
        elif left <= horizon:
            due_window.append((left, r))

    due_now.sort(key=lambda x: x[0])
    due_window.sort(key=lambda x: x[0])

    print("\n=== Checklist: Do Now ===")
    if not due_now:
        print("- None")
    else:
        for left, r in due_now:
            print(f"- {r['item']} (over by {abs(left):,} mi) [{r['priority']}, {r['status']}]")

    print("\n=== Checklist: Next 3-5k Miles ===")
    if not due_window:
        print("- None")
    else:
        for left, r in due_window:
            print(f"- {r['item']} (in {left:,} mi at {int(r['due_mileage']):,}) [{r['priority']}, {r['status']}]")

    print("\n=== Time/Condition Items (manual check) ===")
    for r in rows:
        if to_int(r.get("due_mileage")) is None:
            print(f"- {r['item']}: {r['notes']}")


if __name__ == "__main__":
    main()
