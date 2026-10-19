# Ioniq Fuel Tracker

A long-term, hand-logged fuel consumption record of a Hyundai Ioniq hybrid,
from delivery (August 2019) to today — every fill-up, with dates, volumes,
prices, odometer readings and notes.

**Live dashboard:** https://ningzhibin.github.io/ioniq-fuel-tracker/

## What's here

| Path | What |
|---|---|
| `docs/index.html` | The dashboard (published via GitHub Pages) |
| `data/ioniq.csv` | Cleaned fill-up records, one row per fill-up |
| `fetch.py` | Pulls the latest data from the Google Sheet → `data/ioniq.csv` |
| `build.py` | Regenerates `docs/index.html` from `data/ioniq.csv` |

## Updating

The master log lives in a Google Sheet ("ioniq gas record"), updated by hand
at every fill-up. To refresh the repo and dashboard:

```sh
python3 fetch.py   # Google Sheets -> data/ioniq.csv
python3 build.py   # data/ioniq.csv -> docs/index.html
git add data docs && git commit -m "update" && git push
```

## Data columns

`date, litres, price_per_litre, cost_cad, odometer_km, trip_km, l_per_100km, comment`

- `trip_km` — distance driven since the previous fill-up
- `l_per_100km` — fuel efficiency for that tank (lower is better)
- The first row (2019-08-09) is the delivery full tank, not a real fill-up

## Headline numbers

- ~107 fill-ups over 7+ years, ~83,000 km
- Lifetime average ≈ 4.6 L/100 km
- Winter ≈ 5.5 vs summer ≈ 4.1 L/100 km (Ottawa winters cost ~⅓ more fuel)
- No meaningful efficiency degradation with age/mileage
