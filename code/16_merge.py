"""Merge age and weather into the unit-day panel -> data/panel_full.csv; sanity checks -> out/age_weather_checks.json.
Daily state per unit-day: running / forced (spell class forced) / other off. Thermal units, Oct 2019 - Dec 2024."""
import csv, json, collections, datetime as dt
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
units = {u["unit_id"]: u for u in csv.DictReader(open(ROOT / "data/units_master.csv"))}
wx = {(r["lat"], r["lon"], r["date"]): r for r in csv.DictReader(open(ROOT / "data/weather_daily.csv"))}
state = {}
for s in csv.DictReader(open(ROOT / "data/spells.csv")):
    lab = s["maint_class"] or s["cause"]; d0 = dt.date.fromisoformat(s["start"])
    for k in range(int(s["days"])): state[(s["unit_id"], str(d0 + dt.timedelta(days=k)))] = lab
trips = collections.Counter((l["unit_id"], l["op_date"]) for l in csv.DictReader(open(ROOT / "data/trips_linked.csv")) if l["unit_id"])
out = []
for r in csv.DictReader(open(ROOT / "data/panel.csv")):
    u = units[r["unit_id"]]; w = wx.get((u["lat"], u["lon"], r["op_date"]), {})
    age = int(r["op_date"][:4]) - int(u["cod_year"]) if u.get("cod_year") else ""
    out.append(dict(r, state="running" if r["off"] == "0" else state.get((r["unit_id"], r["op_date"]), "blank"),
                    trip=trips.get((r["unit_id"], r["op_date"]), 0), cod_year=u.get("cod_year", ""), cod_source=u.get("cod_source", ""),
                    age=age, town=u.get("town", ""), t2m=w.get("t2m", ""), t2m_max=w.get("t2m_max", ""), rh2m=w.get("rh2m", ""), prcp=w.get("prectotcorr", "")))
with open(ROOT / "data/panel_full.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(out[0])); wr.writeheader(); wr.writerows(out)

TH = ("ccgt", "gas_turbine", "steam", "recip_engine")
S = [r for r in out if r["tech"] in TH and r["op_date"] <= "2024-12-31" and float(r["cap"]) > 0]
res = {"panel_rows": len(out), "thermal_rows_2019_24": len(S),
       "share_with_weather": round(sum(r["t2m_max"] != "" for r in S) / len(S), 3),
       "share_with_age": round(sum(r["age"] != "" for r in S) / len(S), 3)}
# check 1: NASA POWER Dhaka-area Tmax vs the report's printed Dhaka max temperature (2025-26 reports)
sysr = {r["date"]: r for r in csv.DictReader(open(ROOT / "data/system.csv"))}
dk = [(float(sysr[d]["max_temp_c"]), float(wx[("23.70", "90.35", str(dt.date.fromisoformat(d) - dt.timedelta(days=1)))]["t2m_max"]))
      for d in sysr if sysr[d]["max_temp_c"] not in ("", "None") and ("23.70", "90.35", str(dt.date.fromisoformat(d) - dt.timedelta(days=1))) in wx]
if dk:
    a = np.array(dk); res["dhaka_tmax_report_vs_power"] = dict(n=len(a), corr=round(float(np.corrcoef(a[:, 0], a[:, 1])[0, 1]), 3),
                                                               mean_report=round(float(a[:, 0].mean()), 1), mean_power=round(float(a[:, 1].mean()), 1))
# check 2: forced-outage onset and trips by Tmax bin (unit-days that ran the previous day)
prev = {}
for r in sorted(S, key=lambda r: (r["unit_id"], r["op_date"])):
    r["_prev_run"] = prev.get(r["unit_id"]) == ("running", str(dt.date.fromisoformat(r["op_date"]) - dt.timedelta(days=1)))
    prev[r["unit_id"]] = (r["state"], r["op_date"])
bins = [(0, 27), (27, 30), (30, 33), (33, 36), (36, 50)]
tb = {}
for lo, hi in bins:
    x = [r for r in S if r["t2m_max"] != "" and lo <= float(r["t2m_max"]) < hi and r["_prev_run"]]
    if x: tb[f"{lo}-{hi}C"] = dict(unit_days=len(x), forced_onset_per_1000=round(1000 * sum(r["state"] == "forced" for r in x) / len(x), 2),
                                    trips_per_1000=round(1000 * sum(int(r["trip"]) > 0 for r in x) / len(x), 2))
res["by_tmax_bin_given_ran_yesterday"] = tb
ab = {}
for lo, hi in [(0, 5), (5, 10), (10, 20), (20, 70)]:
    x = [r for r in S if r["age"] != "" and lo <= int(r["age"]) < hi and r["state"] in ("running", "forced")]
    if x: ab[f"age {lo}-{hi}"] = dict(unit_days=len(x), daily_FOR=round(sum(r["state"] == "forced" for r in x) / len(x), 4),
                                       trips_per_unit_year=round(365.25 * sum(int(r["trip"]) > 0 for r in x) / len(x), 2))
res["by_age_running_or_forced_days"] = ab
json.dump(res, open(ROOT / "out/age_weather_checks.json", "w"), indent=1); print(json.dumps(res, indent=1))
