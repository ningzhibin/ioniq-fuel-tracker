#!/usr/bin/env python3
"""Build the Ioniq fuel dashboard from the cleaned CSV.

Usage:
  1. python3 fetch.py        # pull latest data from Google Sheets -> data/ioniq.csv
  2. python3 build.py        # regenerate docs/index.html from data/ioniq.csv
  3. push data/ + docs/ to GitHub
"""
import csv, json, statistics
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "ioniq.csv"
OUT = ROOT / "docs" / "index.html"

def load():
    recs = []
    with open(DATA) as f:
        for r in csv.DictReader(f):
            try:
                d = datetime.strptime(r["date"], "%Y-%m-%d").date()
            except ValueError:
                continue
            def fl(k):
                try: return float(r[k]) if r[k] not in ("", None) else None
                except ValueError: return None
            recs.append({
                "date": d.isoformat(), "litres": fl("litres"),
                "price": fl("price_per_litre"), "cost": fl("cost_cad"),
                "odo": fl("odometer_km"), "trip": fl("trip_km"),
                "eff": fl("l_per_100km"), "comment": (r.get("comment") or "").strip(),
            })
    recs.sort(key=lambda x: x["date"])
    return recs

def season(m):
    return "Winter" if m in (12, 1, 2) else "Spring" if m in (3, 4, 5) \
        else "Summer" if m in (6, 7, 8) else "Fall"

def main():
    recs = load()
    effs = [r for r in recs if r["eff"]]
    n = len(effs)

    total_l = sum(r["litres"] for r in recs if r["litres"])
    total_cost = sum(r["cost"] for r in recs if r["cost"])
    total_km = (recs[-1]["odo"] or 0) - (recs[0]["odo"] or 0)
    life_eff = total_l / total_km * 100 if total_km else None

    # seasonal averages
    seas = {}
    for r in effs:
        s = season(int(r["date"][5:7]))
        seas.setdefault(s, []).append(r["eff"])
    seas_avg = {k: round(statistics.mean(v), 2) for k, v in seas.items()}

    # yearly averages
    yrs = {}
    for r in effs:
        y = r["date"][:4]
        yrs.setdefault(y, []).append(r["eff"])
    yrs_avg = {k: round(statistics.mean(v), 2) for k, v in sorted(yrs.items())}

    # rolling 5-fill average for the trend line
    roll = []
    ev = [r["eff"] for r in effs]
    for i in range(len(ev)):
        w = ev[max(0, i - 4):i + 1]
        roll.append({"date": effs[i]["date"], "v": round(statistics.mean(w), 2)})

    # linear trend of efficiency vs odometer (age effect), L/100km per 10k km
    xs = [r["odo"] for r in effs if r["odo"]]
    ys = [r["eff"] for r in effs if r["odo"]]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    slope_10k = round(slope * 10000, 3)

    # cost per 100 km over time
    cpk = [{"date": r["date"], "v": round(r["eff"] * r["price"], 2)}
           for r in effs if r["eff"] and r["price"]]

    payload = {
        "records": recs,
        "stats": {
            "fills": n,
            "span": f'{recs[0]["date"]} → {recs[-1]["date"]}',
            "total_km": round(total_km),
            "total_l": round(total_l, 1),
            "total_cost": round(total_cost, 2),
            "life_eff": round(life_eff, 2) if life_eff else None,
            "best": round(min(ev), 2), "worst": round(max(ev), 2),
            "slope_10k": slope_10k,
        },
        "seasonal": seas_avg, "yearly": yrs_avg, "rolling": roll, "cost_per_100km": cpk,
        "updated": datetime.now().strftime("%Y-%m-%d"),
    }

    html = HTML.replace("__PAYLOAD__", json.dumps(payload))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print(f"wrote {OUT} ({len(html)//1024} KB), {n} fill-ups")

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ioniq Fuel Tracker — 7 years of real-world hybrid fuel economy</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<style>
  body{font-family:-apple-system,system-ui,"Segoe UI",Roboto,sans-serif;max-width:980px;margin:0 auto;padding:20px;color:#222;background:#fafafa}
  h1{font-size:1.6em;margin-bottom:0} .sub{color:#666;margin:4px 0 20px}
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
  .card{background:#fff;border:1px solid #e3e3e3;border-radius:10px;padding:12px 14px}
  .card .v{font-size:1.5em;font-weight:700} .card .l{color:#666;font-size:.85em}
  .chart{background:#fff;border:1px solid #e3e3e3;border-radius:10px;padding:14px;margin:18px 0}
  .chart h2{font-size:1.1em;margin:0 0 4px} .chart p{color:#666;font-size:.88em;margin:0 0 10px}
  canvas{max-height:340px}
  table{width:100%;border-collapse:collapse;font-size:.85em;background:#fff}
  th,td{padding:6px 8px;border-bottom:1px solid #eee;text-align:right}
  th:first-child,td:first-child{text-align:left}
  footer{color:#888;font-size:.8em;margin-top:24px}
  a{color:#1a73e8}
</style>
</head>
<body>
<h1>🚗 Ioniq Fuel Tracker</h1>
<p class="sub">Every fill-up of a Hyundai Ioniq hybrid since delivery (Aug 2019), logged by hand. Updated <span id="updated"></span>.</p>

<div class="cards" id="cards"></div>

<div class="chart"><h2>Fuel efficiency per fill-up</h2>
<p>Each dot is one tank (L/100 km, lower is better). The line is a 5-fill rolling average — the winter sawtooth is hard to miss.</p>
<canvas id="c1"></canvas></div>

<div class="chart"><h2>Seasonal effect</h2>
<p>Average consumption by season. Ottawa winters cost roughly a third more fuel than summers.</p>
<canvas id="c2"></canvas></div>

<div class="chart"><h2>Does the car get thirstier with age?</h2>
<p>Efficiency vs odometer reading. Trend: <b id="slope"></b> L/100 km per 10,000 km — essentially flat, no meaningful degradation over 7 years / 74k km.</p>
<canvas id="c3"></canvas></div>

<div class="chart"><h2>What driving costs</h2>
<p>Fuel price (CAD/L) and cost per 100 km over time.</p>
<canvas id="c4"></canvas></div>

<div class="chart"><h2>Yearly averages</h2><canvas id="c5"></canvas></div>

<div class="chart"><h2>Recent fill-ups</h2>
<table><thead><tr><th>Date</th><th>Litres</th><th>$/L</th><th>Cost</th><th>Trip km</th><th>L/100km</th><th>Note</th></tr></thead>
<tbody id="recent"></tbody></table></div>

<footer>Data: hand-logged at every fill-up · Analysis: automatic ·
<a href="https://github.com/ningzhibin/ioniq-fuel-tracker">Source &amp; raw CSV on GitHub</a></footer>

<script>
const D = __PAYLOAD__;
document.getElementById('updated').textContent = D.updated;
const s = D.stats;
const cards = [
  [s.life_eff + ' L/100km', 'lifetime average'],
  [s.total_km.toLocaleString() + ' km', 'driven'],
  [s.fills + ' fill-ups', D.span],
  ['$' + s.total_cost.toLocaleString(), 'total fuel cost'],
  [s.best + ' – ' + s.worst, 'best – worst (L/100km)'],
];
document.getElementById('cards').innerHTML = cards.map(c =>
  `<div class="card"><div class="v">${c[0]}</div><div class="l">${c[1]}</div></div>`).join('');
document.getElementById('slope').textContent = (s.slope_10k >= 0 ? '+' : '') + s.slope_10k;

const pts = D.records.filter(r => r.eff).map(r => ({x: r.date, y: r.eff}));
new Chart(document.getElementById('c1'), {type: 'scatter',
  data: {datasets: [
    {label: 'per fill-up', data: pts, pointRadius: 3, backgroundColor: '#1a73e880'},
    {label: '5-fill rolling avg', type: 'line', data: D.rolling.map(p => ({x: p.date, y: p.v})),
     borderColor: '#d93025', borderWidth: 2, pointRadius: 0, tension: 0.2}]},
  options: {scales: {x: {type: 'time', time: {unit: 'year'}}, y: {title: {display: true, text: 'L/100 km'}}}, plugins: {legend: {display: true}}}});

const order = ['Winter', 'Spring', 'Summer', 'Fall'];
new Chart(document.getElementById('c2'), {type: 'bar',
  data: {labels: order, datasets: [{data: order.map(k => D.seasonal[k]),
    backgroundColor: ['#8ab4f8', '#81c995', '#fdd663', '#f6aea9']}]},
  options: {scales: {y: {title: {display: true, text: 'L/100 km'}}}, plugins: {legend: {display: false}}}});

new Chart(document.getElementById('c3'), {type: 'scatter',
  data: {datasets: [{label: 'fill-ups', data: D.records.filter(r => r.eff && r.odo).map(r => ({x: r.odo, y: r.eff})),
    pointRadius: 3, backgroundColor: '#1a73e880'}]},
  options: {scales: {x: {title: {display: true, text: 'odometer (km)'}}, y: {title: {display: true, text: 'L/100 km'}}}, plugins: {legend: {display: false}}}});

new Chart(document.getElementById('c4'), {type: 'line',
  data: {datasets: [
    {label: 'price (CAD/L)', data: D.records.filter(r => r.price).map(r => ({x: r.date, y: r.price})),
     borderColor: '#f9ab00', pointRadius: 0, tension: 0.2, yAxisID: 'y'},
    {label: 'cost per 100 km (CAD)', data: D.cost_per_100km.map(p => ({x: p.date, y: p.v})),
     borderColor: '#d93025', pointRadius: 0, tension: 0.2, yAxisID: 'y1'}]},
  options: {scales: {x: {type: 'time', time: {unit: 'year'}}, y: {position: 'left'}, y1: {position: 'right', grid: {drawOnChartArea: false}}}}});

new Chart(document.getElementById('c5'), {type: 'bar',
  data: {labels: Object.keys(D.yearly), datasets: [{data: Object.values(D.yearly), backgroundColor: '#81c995'}]},
  options: {scales: {y: {title: {display: true, text: 'L/100 km'}}}, plugins: {legend: {display: false}}}});

document.getElementById('recent').innerHTML = D.records.filter(r => r.litres).slice(-10).reverse().map(r =>
  `<tr><td>${r.date}</td><td>${r.litres ?? ''}</td><td>${r.price ?? ''}</td><td>${r.cost ?? ''}</td><td>${r.trip ?? ''}</td><td><b>${r.eff ?? ''}</b></td><td>${r.comment}</td></tr>`).join('');
</script>
</body>
</html>"""

if __name__ == "__main__":
    main()
