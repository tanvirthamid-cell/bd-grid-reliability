"""Robustness: (1) ownership gap with operator-recorded trips only and with clustered-by-plant-site SE;
(2) heat with lagged / 3-day Tmax and alternative FE; (3) age with documented years only (bpdb_ar, web_verified)."""
import pandas as pd, numpy as np, pyfixest as pf, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
d = pd.read_parquet(ROOT / "data/analysis.parquet")
d["owner2"] = np.where(d.owner == "private", "private", "public")
big = d[d.tech != "recip_engine"].copy()
out = {}
def run(name, f, data, vc):
    m = pf.feols(f, data=data, vcov=vc); t = m.tidy()
    out[name] = {k: f'{v["Estimate"]:+.2f} ({v["Std. Error"]:.2f}) p={v["Pr(>|t|)"]:.3f}' for k, v in t.iterrows()}
    out[name]["n"] = int(m._N)
# (1) ownership
a = big[big.state.isin(["running", "forced"]) & (big.agebin != "nan")].copy(); a["forced_state1000"] = 1000 * (a.state == "forced")
run("own|forced_state|site_cluster", "forced_state1000 ~ i(owner2, ref='public') + i(agebin, ref='5_9') + logcap | tech^ym", a, {"CRV1": "town"})
run("own|forced_state|no_age_ctrl_all_units", "forced_state1000 ~ i(owner2, ref='public') + logcap | tech^ym",
    big[big.state.isin(["running", "forced"])].assign(forced_state1000=lambda x: 1000 * (x.state == "forced")), {"CRV1": "unit_id"})
t = big[big.ran_yday & (big.agebin != "nan")].copy(); t["trip1000"] = 1000 * t.trip_any
run("own|operator_trips|site_cluster", "trip1000 ~ i(owner2, ref='public') + i(agebin, ref='5_9') + logcap | tech^ym", t, {"CRV1": "town"})
z = big.copy(); z["zero_gen100"] = 100 * ((z.energy <= 0) & ~z.state.isin(["fuel_gas", "fuel_other", "finance", "dispatch", "contract"]))
run("own|zero_output_nonfuel_any_label", "zero_gen100 ~ i(owner2, ref='public') + logcap | tech^ym", z, {"CRV1": "unit_id"})
# (2) heat, CCGT and all large thermal, risk set ran yesterday
r = big[big.ran_yday & big.tmax.notna()].sort_values(["unit_id", "date"]).copy()
r["tmax_l1"] = r.groupby("unit_id").tmax.shift(1); r["tmax_3d"] = r.groupby("unit_id").tmax.transform(lambda x: x.rolling(3, min_periods=2).mean())
r["event1000"] = 1000 * ((r.trip_any + r.forced_onset) > 0); r["trip1000"] = 1000 * r.trip_any
for y in ["trip1000", "event1000"]:
    run(f"heat|{y}|lag_and_3day", f"{y} ~ tmax + tmax_l1 + rh + prcp + dem_z | unit_id + ym", r, {"CRV1": "unit_id"})
    run(f"heat|{y}|unit_x_month_of_year+tech_x_ym", f"{y} ~ tmax + rh + prcp + dem_z | unit_id^month + tech^ym", r, {"CRV1": "unit_id"})
    run(f"heat|{y}|no_shed_days", f"{y} ~ tmax + rh + prcp + dem_z | unit_id + ym", r[r.shed_day == 0], {"CRV1": "unit_id"})
    run(f"heat|{y}|twoway_cluster", f"{y} ~ tmax + rh + prcp + dem_z | unit_id + ym", r, {"CRV3": "unit_id"} if False else {"CRV1": "unit_id+op_date"})
# (3) age with documented years only
src = pd.read_csv(ROOT / "data/units_master.csv")[["unit_id", "cod_source"]]
a2 = a.drop(columns=["cod_source"], errors="ignore").merge(src, on="unit_id")
a2 = a2[a2.cod_source.isin(["bpdb_ar", "web_verified"])]
run("age|forced_state|documented_years_only", "forced_state1000 ~ i(agebin, ref='5_9') + i(owner2, ref='public') + logcap | tech^ym", a2, {"CRV1": "unit_id"})
json.dump(out, open(ROOT / "out/analysis/robust.json", "w"), indent=1)
for k, v in out.items(): print(k, v)
