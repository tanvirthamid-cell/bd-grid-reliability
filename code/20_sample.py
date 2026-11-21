"""Analysis sample -> data/analysis.parquet
Thermal units (ccgt, gas_turbine, steam, recip_engine), operating dates 2019-10-01 .. 2024-12-31 (before the Jan 2025 reporting change).
Adds: yesterday's state, onset indicators, system load for the day, weather bins."""
import pandas as pd, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
p = pd.read_csv(ROOT / "data/panel_full.csv", low_memory=False)
p = p[p.tech.isin(["ccgt", "gas_turbine", "steam", "recip_engine"]) & (p.op_date >= "2019-10-01") & (p.op_date <= "2024-12-31") & (p.cap > 0)].copy()   # 2 days carry day/month-swapped dates
p["date"] = pd.to_datetime(p.op_date)
p = p.sort_values(["unit_id", "date"])
g = p.groupby("unit_id")
p["prev_state"] = g.state.shift(1); p["prev_date"] = g.date.shift(1)
p["prev_ok"] = (p.date - p.prev_date).dt.days == 1
p["ran_yday"] = p.prev_ok & (p.prev_state == "running")
p["forced_onset"] = (p.state == "forced").astype(int)
p["inactive"] = (p.state == "inactive").astype(int)
p["any_off_onset"] = (p.state != "running").astype(int)
p["nonfuel_off_onset"] = (~p.state.isin(["running", "fuel_gas", "fuel_other", "finance", "dispatch", "contract", "inactive"])).astype(int)
p["trip_any"] = (p.trip > 0).astype(int)
# engine plants: capacity share lost while running with a fault remark ('Engine problem', 'Machine problem')
run = p.state == "running"
p["derate_share"] = np.where(run, ((p.cap - p.peak) / p.cap).clip(0, 1), np.nan)
p["fault_derate_share"] = np.where(run, np.where(p.primary == "forced", p.derate_share, 0.0), np.nan)
# system conditions (system.csv is keyed by file date = op date + 1)
s = pd.read_csv(ROOT / "data/system.csv")
# operating date the page-1 figures describe: the printed 'summary of yesterday' date when plausible, else file date - 1
fd = pd.to_datetime(s.date)
pdt = pd.to_datetime(s.p1_data_date, format="mixed", dayfirst=True, errors="coerce")
ok = (fd - pdt).dt.days.between(0, 2)
s["date"] = pdt.where(ok, fd - pd.Timedelta(days=1))
s = s.drop_duplicates("date", keep="last")
s = s[["date", "eve_peak_dem_mw", "load_shed_mw", "gas_mmcfd"]].rename(columns={"eve_peak_dem_mw": "sys_demand_mw"})
p = p.merge(s, on="date", how="left")
p["ym"] = p.date.dt.strftime("%Y-%m"); p["month"] = p.date.dt.month; p["year"] = p.date.dt.year; p["dow"] = p.date.dt.day_of_week
p["tmax"] = pd.to_numeric(p.t2m_max, errors="coerce"); p["rh"] = pd.to_numeric(p.rh2m, errors="coerce"); p["prcp"] = pd.to_numeric(p.prcp, errors="coerce")
p["tbin"] = pd.cut(p.tmax, [-1, 27, 30, 33, 36, 60], labels=["lt27", "27_30", "30_33", "33_36", "ge36"], right=False).astype(str)
p["age"] = pd.to_numeric(p.age, errors="coerce")
p["agebin"] = pd.cut(p.age, [-1, 5, 10, 20, 80], labels=["0_4", "5_9", "10_19", "20plus"], right=False).astype(str)
p["logcap"] = np.log(p.cap)
p["shed_day"] = (p.load_shed_mw > 0).astype(int)
p["dem_z"] = (p.sys_demand_mw - p.groupby("ym").sys_demand_mw.transform("mean")) / 1000   # GW deviation from month mean
p.to_parquet(ROOT / "data/analysis.parquet")
print(p.shape, "\n", p.groupby("tech").agg(units=("unit_id", "nunique"), rows=("unit_id", "size"), ran_yday=("ran_yday", "sum"),
      forced_onsets=("forced_onset", lambda x: int(x[p.loc[x.index, "ran_yday"]].sum())), trips=("trip_any", "sum")))
