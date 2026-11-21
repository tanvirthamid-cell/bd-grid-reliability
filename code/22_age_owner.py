"""Cross-unit differences: age, owner, size, within technology and calendar month (tech x year-month FE).
Outcomes on unit-days:
  forced_state1000 : unit is in a forced outage (x1000), among days it is running or forced (daily forced-outage rate)
  trip1000         : trip that day, among days it ran yesterday
  nonfuel_unavail100: off for a non-fuel, non-dispatch reason (forced, maintenance, test, grid, blank) x100, all days
SE clustered by unit. Engines are excluded from outage models (one row = many engines); their fault-derate model is separate."""
import pandas as pd, numpy as np, pyfixest as pf, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
d = pd.read_parquet(ROOT / "data/analysis.parquet")
d = d[d.agebin != "nan"].copy()
d["owner2"] = np.where(d.owner == "private", "private", "public")
NONFUEL = ~d.state.isin(["running", "fuel_gas", "fuel_other", "finance", "dispatch", "contract"])
d["nonfuel_unavail100"] = 100 * NONFUEL
out = {}
def run(name, y, data, rhs, fe="tech^ym"):
    m = pf.feols(f"{y} ~ {rhs} | {fe}", data=data, vcov={"CRV1": "unit_id"})
    t = m.tidy()
    out[name] = dict(n=int(m._N), units=int(data.unit_id.nunique()), mean=round(float(data[y].mean()), 3),
                     coefs={k: dict(b=round(float(v["Estimate"]), 3), se=round(float(v["Std. Error"]), 3), p=round(float(v["Pr(>|t|)"]), 3)) for k, v in t.iterrows()})
big = d[d.tech != "recip_engine"]
a = big[big.state.isin(["running", "forced"])].copy(); a["forced_state1000"] = 1000 * (a.state == "forced")
RHS = "i(agebin, ref='5_9') + i(owner2, ref='public') + logcap"
run("forced_state1000|large_thermal", "forced_state1000", a, RHS)
t = big[big.ran_yday].copy(); t["trip1000"] = 1000 * t.trip_any
run("trip1000|large_thermal", "trip1000", t, RHS)
run("nonfuel_unavail100|large_thermal", "nonfuel_unavail100", big, RHS)
for tech in ["ccgt", "gas_turbine", "steam"]:
    run(f"forced_state1000|{tech}", "forced_state1000", a[a.tech == tech], RHS, fe="ym")
    run(f"nonfuel_unavail100|{tech}", "nonfuel_unavail100", big[big.tech == tech], RHS, fe="ym")
# technology gaps at the same age/owner/size (reference: ccgt), month FE only
run("forced_state1000|tech_gap", "forced_state1000", a, "i(tech, ref='ccgt') + " + RHS, fe="ym")
run("nonfuel_unavail100|tech_gap", "nonfuel_unavail100", big, "i(tech, ref='ccgt') + " + RHS, fe="ym")
e = d[(d.tech == "recip_engine") & (d.state == "running")].copy(); e["fault_derate_pp"] = 100 * e.fault_derate_share
run("fault_derate_pp|recip_engine", "fault_derate_pp", e, RHS, fe="ym")
json.dump(out, open(ROOT / "out/analysis/age_owner.json", "w"), indent=1)
for k, v in out.items():
    keep = {c.replace("agebin::", "age").replace("owner2::", "").replace("tech::", ""): f'{x["b"]:+.1f} ({x["se"]:.1f}){"*" if x["p"] < .05 else ""}' for c, x in v["coefs"].items()}
    print(f"{k:34s} n={v['n']:>6} units={v['units']:>3} mean={v['mean']:>7}", keep)
