"""IEEE 762-style metrics from the daily-snapshot panel, Oct 2019 - Dec 2024 -> out/analysis/ieee.json, paper/tab_ieee.tex
Day-based analogues (hours = days; evening-peak snapshot):
  AH (active days) = all unit-days except 'inactive' (spells > 180 days)          SH  = running days
  FOH = forced days      POH = planned     MOH = unspecified maintenance          OMC = fuel/finance/grid days (outside management control)
  RSH = reserve days     EFDH = sum over running days with a fault remark of (cap - peak)/cap   (equivalent forced derated days)
  FOR  = FOH/(FOH+SH)    EFOR = (FOH+EFDH)/(FOH+SH)
  EAF  = 1 - (FOH+POH+MOH+EFDH)/AH          EAF_incl_OMC = EAF - OMC/AH
  FOF  = FOH/AH          MTBF = SH / forced-outage onsets (service days per failure)   MTTR = mean forced spell length
Reliability distributions: Weibull fit to service-day intervals between failure events (forced onsets or trips) per technology;
lognormal fit to forced repair durations; Crow-AMSAA (power-law NHPP) shape per technology (pooled time-truncated MLE);
Laplace trend test per unit with >= 5 events."""
import json, numpy as np, pandas as pd
from scipy import stats
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
d = pd.read_parquet(ROOT / "data/analysis.parquet")
d = d[d.tech.isin(["ccgt", "gas_turbine", "steam", "recip_engine"])].copy()
FUEL = ["fuel_gas", "fuel_other", "finance", "grid"]
d["efdh"] = np.where((d.state == "running") & (d.primary == "forced"), ((d.cap - d.peak) / d.cap).clip(0, 1), 0.0)
d["epdh"] = np.where((d.state == "running") & d.primary.isin(["planned", "shutdown_unspec"]), ((d.cap - d.peak) / d.cap).clip(0, 1), 0.0)
sp = pd.read_csv(ROOT / "data/spells.csv")
sp = sp[(sp.start >= "2019-10-01") & (sp.start <= "2024-12-31")]
def metrics(g, spells):
    AH = (g.state != "inactive").sum(); SH = (g.state == "running").sum()
    FOH = (g.state == "forced").sum(); POH = (g.state == "planned").sum(); MOH = (g.state == "maint_unspecified").sum()
    OMC = g.state.isin(FUEL).sum(); RSH = (g.state == "dispatch").sum(); EFDH = g.efdh.sum(); EPDH = g.epdh.sum()
    fs = spells[spells.maint_class == "forced"]; n_fail = len(fs)
    return dict(units=int(g.unit_id.nunique()), active_unit_years=round(AH / 365.25, 1), inactive_share=round(1 - AH / len(g), 3),
                FOR=round(FOH / max(1, FOH + SH), 3), EFOR=round((FOH + EFDH) / max(1, FOH + SH), 3),
                EAF=round(1 - (FOH + POH + MOH + EFDH + EPDH) / AH, 3), EAF_incl_OMC=round(1 - (FOH + POH + MOH + EFDH + EPDH + OMC) / AH, 3),
                FOF=round(FOH / AH, 3), POF=round(POH / AH, 3), MOF=round(MOH / AH, 3), OMC_F=round(OMC / AH, 3), RSF=round(RSH / AH, 3),
                n_forced_outages=int(n_fail), MTBF_service_days=round(SH / max(1, n_fail), 0),
                MTTR_days_mean=round(float(fs.days.mean()), 1) if n_fail else None, MTTR_days_median=float(fs.days.median()) if n_fail else None)
res = {"by_tech": {}, "by_tech_owner": {}}
for t, g in d.groupby("tech"): res["by_tech"][t] = metrics(g, sp[sp.tech == t])
for (t, o), g in d.groupby(["tech", "owner"]):
    if g.unit_id.nunique() >= 3: res["by_tech_owner"][f"{t}|{o}"] = metrics(g, sp[(sp.tech == t) & (sp.owner == o)])
# ---- failure events on a service-day clock (forced onsets + linked trips), per unit
tr = pd.read_csv(ROOT / "data/trips_linked.csv").dropna(subset=["unit_id"])
tr = tr[(tr.op_date >= "2019-10-01") & (tr.op_date <= "2024-12-31")][["unit_id", "op_date"]].drop_duplicates()
d = d.sort_values(["unit_id", "date"])
d["svc_clock"] = d.groupby("unit_id").state.transform(lambda s: (s == "running").cumsum())
ev = pd.concat([d.loc[d.ran_yday & (d.state == "forced"), ["unit_id", "op_date"]], tr]).drop_duplicates()
ev = ev.merge(d[["unit_id", "op_date", "svc_clock", "tech"]], on=["unit_id", "op_date"])
res["weibull_tbf"] = {}; res["crow_amsaa"] = {}; res["laplace"] = {}
for t, g in ev.groupby("tech"):
    gaps, n_tot, s_log = [], 0, 0.0
    lap = dict(units_tested=0, deteriorating=0, improving=0)
    for u, e in g.groupby("unit_id"):
        tt = np.sort(e.svc_clock.values.astype(float)); tt = tt[tt > 0]
        T = float(d.loc[d.unit_id == u, "svc_clock"].max())
        if len(tt) >= 2: gaps += list(np.diff(tt)[np.diff(tt) > 0])
        if len(tt) >= 1 and T > 0: n_tot += len(tt); s_log += float(np.sum(np.log(T / tt)))
        if len(tt) >= 5 and T > 0:
            U = (tt.mean() - T / 2) / (T * np.sqrt(1 / (12 * len(tt))))
            lap["units_tested"] += 1; lap["deteriorating"] += int(U > 1.96); lap["improving"] += int(U < -1.96)
    gaps = np.array(gaps)
    if len(gaps) >= 20:
        c, loc, sc = stats.weibull_min.fit(gaps, floc=0)
        bs = [stats.weibull_min.fit(np.random.default_rng(i).choice(gaps, len(gaps)), floc=0)[0] for i in range(200)]
        res["weibull_tbf"][t] = dict(n_intervals=int(len(gaps)), shape_beta=round(c, 3), beta_ci95=[round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)],
                                     scale_eta_service_days=round(sc, 1), mean_interval=round(float(gaps.mean()), 1))
    if n_tot: res["crow_amsaa"][t] = dict(events=int(n_tot), beta=round(n_tot / s_log, 3))
    res["laplace"][t] = lap
# repair durations of forced spells (completed), lognormal
res["repair_lognormal"] = {}
for t, g in sp[(sp.maint_class == "forced") & (sp.right_censored == 0)].groupby("tech"):
    x = g.days.values.astype(float)
    if len(x) >= 20:
        s, loc, sc = stats.lognorm.fit(x, floc=0)
        res["repair_lognormal"][t] = dict(n=int(len(x)), median_days=round(sc, 2), sigma=round(s, 3), p90_days=round(float(stats.lognorm.ppf(.9, s, 0, sc)), 1))
json.dump(res, open(ROOT / "out/analysis/ieee.json", "w"), indent=1)
# LaTeX table
names = {"ccgt": "Combined cycle", "gas_turbine": "Gas turbine", "steam": "Steam", "recip_engine": "Recip.\\ engine$^a$"}
rows = []
for t in ["ccgt", "gas_turbine", "steam", "recip_engine"]:
    m = res["by_tech"][t]; w = res["weibull_tbf"].get(t, {}); ca = res["crow_amsaa"].get(t, {}); rl = res["repair_lognormal"].get(t, {})
    f = lambda v, k=3: "--" if v is None else (f"{v:.{k}f}" if isinstance(v, float) else str(v))
    rows.append(f"{names[t]} & {m['units']} & {m['active_unit_years']:.0f} & {100*m['inactive_share']:.0f} & {m['EFOR']:.3f} & {m['EAF']:.2f} & {m['EAF_incl_OMC']:.2f} & "
                f"{m['MTBF_service_days']:.0f} & {f(m['MTTR_days_median'],0)} & {f(w.get('shape_beta'),2)} & {f(ca.get('beta'),2)} \\\\")
(ROOT / "paper/tab_ieee_rows.tex").write_text("\n".join(rows) + "\n")
print(json.dumps(res, indent=1)[:5000])

# =================== sensitivity and robustness additions (second review) ===================
sens = {}
# (1) inactive rule: thresholds 90 / 180 / 365 days, and no inactive class (long spells keep their cause class)
raw = pd.read_parquet(ROOT / "data/analysis.parquet")
raw = raw[raw.tech.isin(["ccgt", "gas_turbine", "steam"])].copy()
allsp = pd.read_csv(ROOT / "data/spells.csv")
allsp = allsp[allsp.tech.isin(["ccgt", "gas_turbine", "steam"])]
def states_for(th):
    st = {}
    for s_ in allsp.itertuples():
        lab = ("inactive" if (th is not None and s_.days > th and not s_.fault_any) else (s_.mclass_base if isinstance(s_.mclass_base, str) and s_.mclass_base else s_.cause))
        d0 = pd.Timestamp(s_.start)
        for k in range(int(s_.days)): st[(s_.unit_id, (d0 + pd.Timedelta(days=k)).strftime("%Y-%m-%d"))] = lab
    return st
for th in [90, 180, 365, None]:
    st = states_for(th); x = raw.copy()
    x["st"] = [("running" if o == 0 else st.get((u, dd), "blank")) for u, dd, o in zip(x.unit_id, x.op_date, x.off)]
    x["efdh"] = np.where((x.st == "running") & (x.primary == "forced"), ((x.cap - x.peak) / x.cap).clip(0, 1), 0.0)
    r_ = {}
    for t, g in x.groupby("tech"):
        AH = (g.st != "inactive").sum(); SH = (g.st == "running").sum(); FOH = (g.st == "forced").sum()
        MOH = (g.st == "maint_unspecified").sum(); POH = (g.st == "planned").sum()
        r_[t] = dict(FOR=round(FOH / max(1, FOH + SH), 3), EFOR=round((FOH + g.efdh.sum()) / max(1, FOH + SH), 3),
                     EAF=round(1 - (FOH + POH + MOH + g.efdh.sum()) / max(1, AH), 3), inactive_share=round(1 - AH / len(g), 3))
    sens[f"inactive_threshold_{th}"] = r_
# (2) derate sensitivity for EFOR: derates counted (a) never, (b) all running fault-remark days, (c) only days with load
#     shedding (all available capacity was called, so the shortfall is not dispatch), (d) only shortfalls of >= 10% of capacity
dd = d[d.tech.isin(["ccgt", "gas_turbine", "steam"])].copy()
short = ((dd.cap - dd.peak) / dd.cap).clip(0, 1); fr = (dd.state == "running") & (dd.primary == "forced")
variants = {"no_derates": np.zeros(len(dd)), "all_fault_derates": np.where(fr, short, 0),
            "shed_days_only": np.where(fr & (dd.load_shed_mw > 0), short, 0), "shortfall_ge_10pct": np.where(fr & (short >= 0.1), short, 0)}
der = {}
for k, v in variants.items():
    dd["_e"] = v; der[k] = {}
    for t, g in dd.groupby("tech"):
        FOH = (g.state == "forced").sum(); SH = (g.state == "running").sum()
        if k == "shed_days_only":   # rate on shedding days only, so numerator and denominator match
            gs = g[g.load_shed_mw > 0]; FOH = (gs.state == "forced").sum(); SH = (gs.state == "running").sum(); e = gs._e.sum()
        else: e = g._e.sum()
        der[k][t] = round((FOH + e) / max(1, FOH + SH), 3)
sens["efor_derate_variants"] = der
# (3) Weibull per unit (units with >= 8 complete intervals) and unit-cluster bootstrap for the pooled shape
wb = {}
for t, g in ev.groupby("tech"):
    per, pools = [], {}
    for u, e in g.groupby("unit_id"):
        tt = np.sort(e.svc_clock.values.astype(float)); gaps = np.diff(tt); gaps = gaps[gaps > 0]
        pools[u] = gaps
        if len(gaps) >= 8: per.append(stats.weibull_min.fit(gaps, floc=0)[0])
    units_ = [u for u in pools if len(pools[u])]
    bs = []
    rng = np.random.default_rng(7)
    for i in range(300):
        pick = rng.choice(units_, len(units_)); x_ = np.concatenate([pools[u] for u in pick])
        if len(x_) >= 20: bs.append(stats.weibull_min.fit(x_, floc=0)[0])
    wb[t] = dict(units_fitted=len(per), median_unit_beta=round(float(np.median(per)), 3) if per else None,
                 share_units_beta_lt1=round(float(np.mean(np.array(per) < 1)), 2) if per else None,
                 pooled_beta_unit_bootstrap_ci=[round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)] if bs else None)
sens["weibull_per_unit"] = wb
# (4) labelling drift: forced onsets and trips per 1,000 running unit-days by year (large thermal)
lt = d[d.tech.isin(["ccgt", "gas_turbine", "steam"]) & d.ran_yday]
sens["rates_by_year"] = {int(y): dict(forced_onsets_per_1000=round(1000 * g.forced_onset.mean(), 2), trips_per_1000=round(1000 * g.trip_any.mean(), 2))
                         for y, g in lt.groupby(lt.date.dt.year)}
res["sensitivity"] = sens
json.dump(res, open(ROOT / "out/analysis/ieee.json", "w"), indent=1)
print(json.dumps(sens, indent=1))
