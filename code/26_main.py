"""Main estimates for the revised paper -> out/analysis/main.json
(A) Ownership: technology x year-month FE; private vs public/JV; age bins, log capacity. Outcomes: forced state (among running|forced),
    trips (ran yesterday), non-fuel unavailability, and two label-free measures (any zero-output day; zero output excluding only
    reserve/contract/inactive days). CRV1 by unit plus wild cluster bootstrap p-values (Webb weights, 9,999 draws). Variants:
    CCGT only; without steam; leave-one-private-unit-out range.
(B) Weather within units: Poisson FE (unit + year-month) for trip counts and forced onsets on Tmax bins; Holm-adjusted p-values;
    per-degree linear; cause-specific Poisson for rain (per 10 mm).
(C) New units excluding commissioning/test days."""
import json, warnings, numpy as np, pandas as pd, pyfixest as pf
from pathlib import Path
from statsmodels.stats.multitest import multipletests
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
d = pd.read_parquet(ROOT / "data/analysis.parquet")
d["private"] = (d.owner == "private").astype(int)
big = d[d.tech != "recip_engine"].copy()
dated = big[big.age.notna()].copy()
out = {"A": {}, "B": {}, "C": {}}
def tid(m, k):
    t = m.tidy().loc[k]; return dict(b=round(float(t["Estimate"]), 3), se=round(float(t["Std. Error"]), 3), p=round(float(t["Pr(>|t|)"]), 4),
                                      lo=round(float(t["2.5%"]), 3), hi=round(float(t["97.5%"]), 3))
WEBB = np.array([-np.sqrt(1.5), -1, -np.sqrt(.5), np.sqrt(.5), 1, np.sqrt(1.5)])
from pyfixest.estimation import demean as _demean
def wild_p(y, rhs_other, fe, data, reps=4999, seed=1, batch=250):
    """Wild cluster restricted (WCR) bootstrap p-value for 'private' (Webb weights, clusters = units).
    M = annihilator of the fixed effects and the other regressors. Restricted residuals e_r = M y.
    Each draw: v = e_r * w_g, re-partialled (M v) exactly as the original outcome, then the same CRV1 t-statistic."""
    data = data.dropna(subset=[y]).copy()
    if "agebin" in rhs_other: data = data[data.agebin.notna()]
    Z = pd.get_dummies(data[["agebin"]], drop_first=False).drop(columns=[c for c in ["agebin_5_9"] if c in pd.get_dummies(data[["agebin"]]).columns]).astype(float) if "agebin" in rhs_other else pd.DataFrame(index=data.index)
    if "logcap" in rhs_other: Z["logcap"] = data.logcap
    fcols = fe.split("^")
    fl = pd.factorize(data[fcols].astype(str).agg("|".join, axis=1))[0].astype(np.uint64).reshape(-1, 1)
    wts = np.ones(len(data))
    def M(A):
        A = np.asarray(A, float).reshape(len(data), -1)
        Ad = _demean(A, fl, wts)[0]
        if Zd.shape[1]: Ad = Ad - Zd @ np.linalg.lstsq(Zd, Ad, rcond=None)[0]
        return Ad
    Zd = np.zeros((len(data), 0)); 
    if Z.shape[1]: Zd = _demean(Z.values, fl, wts)[0]
    xt = M(data.private.values)[:, 0]; er = M(data[y].values)[:, 0]
    g = pd.factorize(data.unit_id)[0]; G = g.max() + 1; xx = (xt ** 2).sum()
    def tstats(R):                     # R: n x B partialled outcomes
        b = xt @ R / xx; E = R - np.outer(xt, b)
        S = np.zeros((G, R.shape[1])); np.add.at(S, g, xt[:, None] * E)
        return b / np.sqrt((S ** 2).sum(0) / xx ** 2 * G / (G - 1))
    t0 = tstats(er[:, None])[0]
    rng = np.random.default_rng(seed); ts = []
    for k in range(0, reps, batch):
        B = min(batch, reps - k); W = rng.choice(WEBB, (G, B))[g]
        ts.append(tstats(M(er[:, None] * W)))
    ts = np.concatenate(ts)
    return round(float((np.sum(np.abs(ts) >= abs(t0)) + 1) / (reps + 1)), 4)
RHS = "private + i(agebin, ref='5_9') + logcap"
def own(name, y, data, rhs=RHS, fe="tech^ym", boot=True):
    data = data.dropna(subset=[y])
    m = pf.feols(f"{y} ~ {rhs} | {fe}", data=data, vcov={"CRV1": "unit_id"})
    used = data.dropna(subset=["agebin"]) if "agebin" in rhs else data
    r = dict(n=int(m._N), units=int(used.unit_id.nunique()), private_units=int(used[used.private == 1].unit_id.nunique()),
             mean=round(float(data[y].mean()), 3), private=tid(m, "private"))
    if boot: r["private"]["p_wild"] = wild_p(y, rhs.replace("private + ", "").replace("private", ""), fe, data)
    if "agebin" in rhs:
        r["age"] = {k: tid(m, f"agebin::{k}") for k in ["0_4", "10_19", "20plus"] if f"agebin::{k}" in m.tidy().index}
    out["A"][name] = r; return m
dated["agebin"] = dated.agebin.replace("nan", np.nan)
a = dated[dated.state.isin(["running", "forced"])].copy(); a["forced_state1000"] = 1000 * (a.state == "forced")
own("forced_state", "forced_state1000", a)
t = dated[dated.ran_yday].copy(); t["trip1000"] = 1000 * t.trip_any
own("trips", "trip1000", t)
nf = dated[dated.state != "inactive"].copy(); nf["nonfuel100"] = 100 * nf.nonfuel_off_onset
own("nonfuel_unavail", "nonfuel100", nf)
lf = big.copy(); lf["zero100"] = 100 * (lf.energy <= 0)
own("zero_output_any_label", "zero100", lf, rhs="private + logcap")
lf2 = big[~big.state.isin(["dispatch", "contract", "inactive"])].copy(); lf2["zero100"] = 100 * (lf2.energy <= 0)
own("zero_output_excl_reserve_contract_inactive", "zero100", lf2, rhs="private + logcap")
own("forced_state|ccgt_only", "forced_state1000", a[a.tech == "ccgt"], fe="ym")
own("trips|ccgt_only", "trip1000", t[t.tech == "ccgt"], fe="ym")
own("forced_state|no_steam", "forced_state1000", a[a.tech != "steam"])
# leave-one-private-unit-out
loo = []
for u in a[a.private == 1].unit_id.unique():
    m = pf.feols(f"forced_state1000 ~ {RHS} | tech^ym", data=a[a.unit_id != u], vcov={"CRV1": "unit_id"}); loo.append(float(m.coef()["private"]))
out["A"]["forced_state"]["loo_range"] = [round(min(loo), 1), round(max(loo), 1)]
# fuel idling by ownership (gas priority check)
fi = big[big.state != "inactive"].copy(); fi["fuel_idle100"] = 100 * fi.state.isin(["fuel_gas", "fuel_other", "finance"])
own("fuel_idle", "fuel_idle100", fi, rhs="private + logcap", boot=False)

# ---- (B) weather within units, Poisson FE
r = big[big.ran_yday & big.tmax.notna()].copy()
r["tmax_within_sd"] = r.tmax - r.groupby(["unit_id", "ym"]).tmax.transform("mean")
out["B"]["tmax_sd_raw"] = round(float(r.tmax.std()), 2); out["B"]["tmax_sd_within_unit_month"] = round(float(r.tmax_within_sd.std()), 2)
out["B"]["events"] = dict(trips=int(r.trip_any.sum()), forced_onsets=int(r.forced_onset.sum()), unit_days=int(len(r)))
out["B"]["events_by_tbin"] = r.groupby("tbin")[["trip_any", "forced_onset"]].sum().astype(int).to_dict()
r["prcp10"] = r.prcp / 10
for y in ["trip_any", "forced_onset"]:
    for grp, data in [("large_thermal", r), ("ccgt", r[r.tech == "ccgt"])]:
        m = pf.fepois(f"{y} ~ i(tbin, ref='30_33') + rh + prcp10 + dem_z + shed_day | unit_id + ym", data=data, vcov={"CRV1": "unit_id"})
        tt = m.tidy(); bins = [k for k in tt.index if k.startswith("tbin::")]
        holm = multipletests([tt.loc[k, "Pr(>|t|)"] for k in bins], method="holm")[1]
        out["B"][f"{y}|{grp}|bins"] = {k.replace("tbin::", ""): dict(irr=round(float(np.exp(tt.loc[k, "Estimate"])), 3),
                                        lo=round(float(np.exp(tt.loc[k, "2.5%"])), 3), hi=round(float(np.exp(tt.loc[k, "97.5%"])), 3),
                                        p=round(float(tt.loc[k, "Pr(>|t|)"]), 4), p_holm=round(float(h), 4)) for k, h in zip(bins, holm)}
        out["B"][f"{y}|{grp}|rain_per10mm_irr"] = dict(irr=round(float(np.exp(tt.loc["prcp10", "Estimate"])), 3), lo=round(float(np.exp(tt.loc["prcp10", "2.5%"])), 3),
                                                    hi=round(float(np.exp(tt.loc["prcp10", "97.5%"])), 3), p=round(float(tt.loc["prcp10", "Pr(>|t|)"]), 4))
        m2 = pf.fepois(f"{y} ~ tmax + rh + prcp10 + dem_z + shed_day | unit_id + ym", data=data, vcov={"CRV1": "unit_id"})
        t2 = m2.tidy().loc["tmax"]
        out["B"][f"{y}|{grp}|per_degC_irr"] = dict(irr=round(float(np.exp(t2["Estimate"])), 3), lo=round(float(np.exp(t2["2.5%"])), 3), hi=round(float(np.exp(t2["97.5%"])), 3), p=round(float(t2["Pr(>|t|)"]), 4))
# linear-probability rain coefficient for comparability (per 1,000 unit-days per mm)
r["trip1000"] = 1000 * r.trip_any
m = pf.feols("trip1000 ~ tmax + rh + prcp + dem_z + shed_day | unit_id + ym", data=r, vcov={"CRV1": "unit_id"})
out["B"]["lpm_trip"] = {k: tid(m, k) for k in ["tmax", "prcp", "dem_z"]}
out["B"]["lpm_trip_mean"] = round(float(r.trip1000.mean()), 2)
# cause-specific rain
tl = pd.read_csv(ROOT / "data/trips_linked.csv").dropna(subset=["unit_id"])[["unit_id", "op_date", "cause_cat"]]
GROUPS = {"electrical": ["electrical"], "grid": ["grid"], "mechanical": ["turbine", "boiler", "cooling"], "fuel_supply": ["fuel_supply"], "control": ["control"]}
for gname, cats in GROUPS.items():
    k = tl[tl.cause_cat.isin(cats)].groupby(["unit_id", "op_date"]).size().rename("k").reset_index()
    x = r.merge(k, on=["unit_id", "op_date"], how="left"); x["k"] = x.k.fillna(0)
    m = pf.fepois("k ~ prcp10 + tmax + rh + dem_z | unit_id + ym", data=x, vcov={"CRV1": "unit_id"})
    tt = m.tidy().loc["prcp10"]
    out["B"][f"rain_cause|{gname}"] = dict(events=int(x.k.sum()), irr=round(float(np.exp(tt["Estimate"])), 3), lo=round(float(np.exp(tt["2.5%"])), 3),
                                            hi=round(float(np.exp(tt["97.5%"])), 3), p=round(float(tt["Pr(>|t|)"]), 4))
# ---- (C) new units excluding commissioning/test days
c = nf[nf.state != "test"].copy()
m = pf.feols(f"nonfuel100 ~ {RHS} | tech^ym", data=c, vcov={"CRV1": "unit_id"})
out["C"]["new_units_nonfuel_excl_test"] = tid(m, "agebin::0_4")
json.dump(out, open(ROOT / "out/analysis/main.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str)[:9000])
