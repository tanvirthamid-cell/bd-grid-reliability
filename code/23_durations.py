"""Outage (repair) durations: spells of forced and unspecified maintenance, 2019-10 .. 2024-12, large thermal units.
Cox proportional hazards of returning to service (statsmodels PHReg); right-censored spells kept (status 0).
Also median durations by group and resync times from trip narratives."""
import pandas as pd, numpy as np, json, warnings
from statsmodels.duration.hazard_regression import PHReg
from pathlib import Path
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
s = pd.read_csv(ROOT / "data/spells.csv")
u = pd.read_csv(ROOT / "data/units_master.csv")[["unit_id", "cod_year"]]
s = s.merge(u, on="unit_id", how="left")
s = s[(s.start <= "2024-12-31") & s.tech.isin(["ccgt", "gas_turbine", "steam"]) & s.maint_class.isin(["forced", "maint_unspecified"])].copy()
s = s[s.left_censored == 0]
s["event"] = 1 - s.right_censored
s["age"] = pd.to_datetime(s.start).dt.year - s.cod_year
s["old"] = (s.age >= 20).astype(float); s["new"] = (s.age < 5).astype(float)
s["private"] = (s.owner == "private").astype(float); s["year"] = s.start.str[:4]
res = {"n_spells": int(len(s)), "medians": {}}
for k, g in [("class", "maint_class"), ("tech", "tech"), ("owner", "owner")]:
    res["medians"][k] = s.groupby(g).days.agg(["count", "median", "mean"]).round(1).reset_index().to_dict("records")
res["medians"]["trip_initiated"] = s.groupby("trip_initiated").days.agg(["count", "median", "mean"]).round(1).reset_index().to_dict("records")
X = pd.get_dummies(s[["tech", "maint_class", "year"]], drop_first=True).astype(float)
X["private"] = s.private; X["old"] = s.old.fillna(0); X["new"] = s.new.fillna(0); X["age_missing"] = s.age.isna().astype(float); X["logcap"] = np.log(s.cap)
m = PHReg(s.days.values, X.values, status=s.event.values, ties="efron").fit(groups=s.unit_id.values)
res["cox_return_hazard"] = {c: dict(hr=round(float(np.exp(b)), 3), se=round(float(se), 3), p=round(float(p), 3)) for c, b, se, p in zip(X.columns, m.params, m.bse, m.pvalues)}
# trip resync times (hours) where both times are given and resync is the same day
t = pd.read_csv(ROOT / "data/trips_linked.csv")
um = pd.read_csv(ROOT / "data/units_master.csv")[["unit_id", "tech"]]
t = t.merge(um, on="unit_id", how="left")
def hrs(a, b):
    try:
        h1, m1 = map(int, a.split(":")); h2, m2 = map(int, b.split(":"))
        d = (h2 * 60 + m2 - h1 * 60 - m1) / 60
        return d if d > 0 else np.nan
    except Exception: return np.nan
t["resync_h"] = [hrs(a, b) if isinstance(a, str) and isinstance(b, str) else np.nan  # next-day resyncs come out negative -> NaN
                 for a, b in zip(t.trip_time, t.sync_time)]
res["trip_resync_hours"] = t.groupby("tech").resync_h.agg(["count", "median", "mean"]).round(2).reset_index().to_dict("records")
res["trip_causes_by_tech"] = pd.crosstab(t.tech, t.cause_cat).to_dict("index")
json.dump(res, open(ROOT / "out/analysis/durations.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in res.items() if k != "trip_causes_by_tech"}, indent=1, default=str)[:4000])
print(pd.crosstab(t.tech, t.cause_cat))
