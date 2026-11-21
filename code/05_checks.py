"""Consistency checks on the classified remarks -> out/checks.json and out/daily.csv.
Daily lost MW by cause = off units' capacity + running units' (capacity - evening peak), evening-peak snapshot."""
import csv, json, datetime as dt, collections, math
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
u = list(csv.DictReader(open(ROOT / "data/units_classified.csv")))
sysr = {r["date"]: r for r in csv.DictReader(open(ROOT / "data/system.csv"))}
CATS = ["fuel_gas", "fuel_other", "finance", "forced", "planned", "dispatch", "grid", "contract", "blank", "other"]
fold = lambda c: c if c in CATS else "other"
day = collections.defaultdict(lambda: collections.Counter())
fdate = {}
for r in u:
    cap, peak = float(r["cap"]), float(r["peak"])
    if cap <= 0: continue
    lost = cap if r["off"] == "1" else max(0.0, cap - peak)
    d = r["op_date"]; day[d][fold(r["primary"])] += lost; day[d]["cap"] += cap; day[d]["peak"] += peak
    day[d]["n_off_" + ("blank" if r["primary"] == "blank" else "cause")] += r["off"] == "1"
    fdate[d] = r["file_date"]
f = lambda x: float(x) if x not in ("", "None", None) else np.nan
rows = []
for d in sorted(day):
    s = sysr.get(fdate[d], {})
    rows.append(dict(op_date=d, **{k: round(day[d][k], 1) for k in CATS + ["cap", "peak"]},
                     load_shed_mw=f(s.get("load_shed_mw")), unserved_mkwh=f(s.get("unserved_mkwh")), gas_mmcfd=f(s.get("gas_mmcfd")),
                     eve_dem=f(s.get("eve_peak_dem_mw")), avail_max=f(s.get("avail_max_gen_mw"))))
with open(ROOT / "out/daily.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

D = {k: np.array([r[k] for r in rows], float) for k in rows[0] if k != "op_date"}
ym = np.array([r["op_date"][:7] for r in rows])
def demean(x):  # within calendar-month deviations
    y = x.copy()
    for m in np.unique(ym):
        i = ym == m; y[i] = x[i] - np.nanmean(x[i])
    return y
def corr(a, b):
    ok = ~np.isnan(a) & ~np.isnan(b)
    return round(float(np.corrcoef(a[ok], b[ok])[0, 1]), 3), int(ok.sum())
res = {}
gas = D["gas_mmcfd"]
for c in ["fuel_gas", "fuel_other", "forced", "planned", "dispatch", "blank"]:
    res[f"corr_within_month({c}_MW, gas_supply)"] = corr(demean(D[c]), demean(gas))
    res[f"corr_levels({c}_MW, gas_supply)"] = corr(D[c], gas)
shed = D["load_shed_mw"]
ok = ~np.isnan(shed)
for lab, sel in [("shed=0", ok & (shed == 0)), ("shed 1-500", ok & (shed > 0) & (shed <= 500)), ("shed>500", ok & (shed > 500))]:
    res[f"mean dispatch/reserve MW on days {lab}"] = (round(float(np.mean(D["dispatch"][sel])), 0), int(sel.sum()))
    res[f"mean fuel_gas MW on days {lab}"] = (round(float(np.mean(D["fuel_gas"][sel])), 0), int(sel.sum()))
# yearly means of lost MW by cause
yr = np.array([r["op_date"][:4] for r in rows])
res["yearly_mean_lost_MW"] = {y: {c: round(float(np.mean(D[c][yr == y]))) for c in CATS + ["cap", "peak"]} for y in sorted(set(yr))}
mo = sorted(set(ym))
res["monthly_fuel_gas_MW"] = {m: round(float(np.mean(D["fuel_gas"][ym == m]))) for m in mo}
res["monthly_gas_mmcfd"] = {m: (round(float(np.nanmean(gas[ym == m]))) if not np.all(np.isnan(gas[ym == m])) else None) for m in mo}
res["monthly_load_shed_mw"] = {m: (round(float(np.nanmean(shed[ym == m]))) if not np.all(np.isnan(shed[ym == m])) else None) for m in mo}
json.dump(res, open(ROOT / "out/checks.json", "w"), indent=1, default=str)
for k, v in res.items():
    if not k.startswith(("monthly", "yearly")): print(k, v)
print("yearly"); [print(y, v) for y, v in res["yearly_mean_lost_MW"].items()]
