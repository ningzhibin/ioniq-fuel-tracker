#!/usr/bin/env python3
"""Fetch the latest Ioniq fuel log from Google Sheets and save a cleaned CSV.

Source: Google Sheet 'ioniq gas record', tab 'ioniq'.
Output: data/ioniq.csv with columns:
  date(YYYY-MM-DD), litres, price_per_litre, cost_cad, odometer_km,
  trip_km, l_per_100km, comment
"""
import csv, json, subprocess
from datetime import datetime
from pathlib import Path

SPREADSHEET = "1kOeDtHtvXEmGqllXpJLLNYIibnf7B6ClFp-pSevQHOQ"
ROOT = Path(__file__).parent
OUT = ROOT / "data" / "ioniq.csv"

def main():
    r = subprocess.run(
        ["/opt/hatch/bin/hatch_gws_cli", "sheets", "+read",
         "--spreadsheet", SPREADSHEET, "--range", "ioniq!A1:J1104", "--format", "csv"],
        capture_output=True, text=True, check=True)
    vals = json.loads(r.stdout)["values"]
    rows = []
    for raw in vals[2:]:  # skip blank row + header
        if len(raw) < 2 or not raw[1].strip() or raw[1].strip().lower() == "in total":
            continue
        try:
            d = datetime.strptime(raw[1].strip(), "%m/%d/%Y").date()
        except ValueError:
            try:
                d = datetime.strptime(raw[1].strip(), "%m/%d/%y").date()
            except ValueError:
                print("skip unparseable date:", raw[1]); continue
        def get(i):
            return raw[i].strip() if len(raw) > i else ""
        rows.append({
            "date": d.isoformat(), "litres": get(2), "price_per_litre": get(3),
            "cost_cad": get(4), "odometer_km": get(5), "trip_km": get(6),
            "l_per_100km": get(7), "comment": get(9),
        })
    rows.sort(key=lambda x: x["date"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {OUT}: {len(rows)} records, {rows[0]['date']} → {rows[-1]['date']}")

if __name__ == "__main__":
    main()
