"""Preview reliability table by technology, Oct 2019 - Dec 2024 (pre reporting change) -> out/preview_by_tech.csv.
Unit-day states: running (peak>0 or energy>0); off by spell class. Thermal units only (ccgt, gas_turbine, steam, recip_engine)."""
import csv, collections, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
END = "2024-12-31"; TH = ("ccgt", "gas_turbine", "steam", "recip_engine")
units = {m["unit_id"]: m for m in csv.DictReader(open(ROOT / "data/units_master.csv"))}
state = {}
for s in csv.DictReader(open(ROOT / "data/spells.csv")):
    lab = s["maint_class"] or s["cause"]
    d0, d1 = dt.date.fromisoformat(s["start"]), dt.date.fromisoformat(s["end"])
    for k in range((d1 - d0).days + 1): state[(s["unit_id"], str(d0 + dt.timedelta(days=k)))] = lab
agg = collections.defaultdict(collections.Counter)
for r in csv.DictReader(open(ROOT / "data/panel.csv")):
    if r["op_date"] > END or r["tech"] not in TH or float(r["cap"]) <= 0: continue
    st = "running" if r["off"] == "0" else state.get((r["unit_id"], r["op_date"]), "blank")
    a = agg[r["tech"]]; a[st] += 1; a["unit_days"] += 1; a["units"] = a["units"]
    a["mw_days"] += float(r["cap"]); a["energy"] += float(r["energy"] or 0)
uc = collections.Counter(units[u]["tech"] for u in units if units[u]["tech"] in TH and units[u]["first"] <= END)
trips = collections.Counter()
for l in csv.DictReader(open(ROOT / "data/trips_linked.csv")):
    if l["unit_id"] and l["op_date"] <= END and units[l["unit_id"]]["tech"] in TH: trips[units[l["unit_id"]]["tech"]] += 1
rows = []
for t in TH:
    a = agg[t]; n = a["unit_days"]
    fuel_off = a["fuel_gas"] + a["fuel_other"] + a["finance"]
    rows.append(dict(tech=t, units=uc[t], unit_years=round(n / 365.25, 1), running_pct=round(100 * a["running"] / n, 1),
                     fuel_off_pct=round(100 * fuel_off / n, 1), forced_pct=round(100 * a["forced"] / n, 1),
                     maint_unspec_pct=round(100 * a["maint_unspecified"] / n, 1), planned_pct=round(100 * a["planned"] / n, 1),
                     reserve_pct=round(100 * a["dispatch"] / n, 1), blank_pct=round(100 * a["blank"] / n, 1),
                     FOR_daily=round(a["forced"] / max(1, a["forced"] + a["running"]), 3),
                     trips_per_unit_year=round(trips[t] / (n / 365.25), 2),
                     capacity_factor=round(a["energy"] / 1000 / (a["mw_days"] * 24), 3)))
with open(ROOT / "out/preview_by_tech.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows: print(r)
