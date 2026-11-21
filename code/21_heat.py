"""Within-unit effects of heat and system stress on trips and forced-outage onsets.
Linear probability models, outcomes x1000 (per 1,000 unit-days), risk set = units that ran the previous day.
FE: unit + year-month (absorbs seasonality, fuel-supply regimes, unit-specific levels). SE clustered by unit.
Engines: fault-derate share of capacity on running days (x100 = percentage points)."""
import pandas as pd, numpy as np, pyfixest as pf, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
d = pd.read_parquet(ROOT / "data/analysis.parquet")
d = d[d.tmax.notna()]
r = d[d.ran_yday].copy()
r["trip1000"] = 1000 * r.trip_any; r["forced1000"] = 1000 * r.forced_onset; r["event1000"] = 1000 * ((r.trip_any + r.forced_onset) > 0)
r["nonfuel1000"] = 1000 * r.nonfuel_off_onset
RHS = "i(tbin, ref='30_33') + rh + prcp + dem_z + shed_day"
out = {}
def run(name, y, data, rhs=RHS, fe="unit_id + ym"):
    m = pf.feols(f"{y} ~ {rhs} | {fe}", data=data, vcov={"CRV1": "unit_id"})
    t = m.tidy()
    out[name] = dict(n=int(m._N), units=int(data.unit_id.nunique()), mean=round(float(data[y].mean()), 3),
                     coefs={k: dict(b=round(float(v["Estimate"]), 3), se=round(float(v["Std. Error"]), 3), p=round(float(v["Pr(>|t|)"]), 3)) for k, v in t.iterrows()})
    return m
nonengine = r[r.tech != "recip_engine"]
for y in ["trip1000", "forced1000", "event1000", "nonfuel1000"]:
    run(f"{y}|large_thermal", y, nonengine)
    for t in ["ccgt", "gas_turbine", "steam"]: run(f"{y}|{t}", y, nonengine[nonengine.tech == t])
# continuous: per +1C Tmax, with month-of-year x unit trends absorbed by unit + ym
for y in ["trip1000", "event1000"]:
    run(f"{y}|large_thermal|linear", y, nonengine, rhs="tmax + rh + prcp + dem_z + shed_day")
    run(f"{y}|ccgt|linear", y, nonengine[nonengine.tech == "ccgt"], rhs="tmax + rh + prcp + dem_z + shed_day")
# engines
e = d[(d.tech == "recip_engine") & (d.state == "running")].copy(); e["fault_derate_pp"] = 100 * e.fault_derate_share
run("fault_derate_pp|recip_engine", "fault_derate_pp", e)
run("fault_derate_pp|recip_engine|linear", "fault_derate_pp", e, rhs="tmax + rh + prcp + dem_z + shed_day")
json.dump(out, open(ROOT / "out/analysis/heat.json", "w"), indent=1)
for k, v in out.items():
    keep = {c: f'{x["b"]:+.2f} ({x["se"]:.2f}){"*" if x["p"] < .05 else ""}' for c, x in v["coefs"].items()}
    print(f"{k:38s} n={v['n']:>6} mean={v['mean']:>7}", keep)
