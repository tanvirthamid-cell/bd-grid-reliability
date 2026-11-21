"""Write every number quoted in the paper to paper/numbers.tex as LaTeX macros, plus table rows. No number is typed by hand."""
import json, csv, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; A = ROOT / "out/analysis"
M = json.load(open(A / "main.json")); I = json.load(open(A / "ieee.json")); D = json.load(open(A / "durations.json"))
F = json.load(open(ROOT / "out/fuel_check.json")); C = json.load(open(ROOT / "out/checks.json"))
mac = {}
def put(k, v): mac[k] = v
f0 = lambda x: f"{x:,.0f}"; f1 = lambda x: f"{x:.1f}"; f2 = lambda x: f"{x:.2f}"; f3 = lambda x: f"{x:.3f}"
def pv(p): return "<0.001" if p < 0.001 else f"{p:.3f}"
# sample
units = pd.read_csv(ROOT / "data/units.csv", usecols=["date"]); put("nDays", f0(units.date.nunique()))
panel = pd.read_csv(ROOT / "data/panel.csv", usecols=["unit_id"]); put("nUnitDays", f0(len(panel))); put("nUnits", f0(panel.unit_id.nunique()))
tl = pd.read_csv(ROOT / "data/trips_linked.csv"); put("nTrips", f0(len(tl))); put("nTripsLinked", f0(tl.unit_id.notna().sum()))
put("nTripsStated", f0((~tl.cause_cat.isin(["unstated"])).sum()))
for k, v in tl.cause_cat.value_counts().items(): put("trip" + k.replace("_", "").title(), f0(v))
sp = pd.read_csv(ROOT / "data/spells.csv"); s19 = sp[(sp.start >= "2019-10-01") & (sp.start <= "2024-12-31")]
for c in ["forced", "planned", "maint_unspecified", "inactive"]: put("sp" + c.replace("_", "").title(), f0((s19.maint_class == c).sum()))
fs = s19[s19.maint_class == "forced"]; put("spForcedMedian", f0(fs.days.median())); put("spPlannedMedian", f0(s19[s19.maint_class == "planned"].days.median()))
put("spUnspecMedian", f0(s19[s19.maint_class == "maint_unspecified"].days.median()))
# fuel and remark checks
put("fuelGas", f3(F["gas"]["ratio"])); put("fuelCoal", f3(F["coal"]["ratio"])); put("fuelOil", f3(F["oil"]["ratio"])); put("fuelDays", f0(F["days_used"]))
put("corrGasFuel", f2(C["corr_within_month(fuel_gas_MW, gas_supply)"][0])); put("corrGasFuelLev", f2(C["corr_levels(fuel_gas_MW, gas_supply)"][0]))
put("corrGasForced", f2(C["corr_within_month(forced_MW, gas_supply)"][0])); put("corrGasOther", f2(C["corr_within_month(fuel_other_MW, gas_supply)"][0]))
put("corrGasPlanned", f2(C["corr_within_month(planned_MW, gas_supply)"][0]))
put("resNoShed", f0(C["mean dispatch/reserve MW on days shed=0"][0])); put("resLowShed", f0(C["mean dispatch/reserve MW on days shed 1-500"][0])); put("resHighShed", f0(C["mean dispatch/reserve MW on days shed>500"][0]))
# ownership
A_ = M["A"]
def own(prefix, key, scale=f1):
    r = A_[key]; p = r["private"]
    put(prefix + "B", scale(p["b"])); put(prefix + "SE", scale(p["se"])); put(prefix + "P", pv(p["p"])); put(prefix + "Mean", scale(r["mean"]))
    if "p_wild" in p and not isinstance(p["p_wild"], str): put(prefix + "Pw", pv(p["p_wild"]))
    put(prefix + "N", f0(r["n"])); put(prefix + "Units", f0(r["units"])); put(prefix + "PrivUnits", f0(r["private_units"]))
own("ownForced", "forced_state"); own("ownTrip", "trips"); own("ownNonfuel", "nonfuel_unavail"); own("ownZero", "zero_output_any_label")
own("ownZeroExcl", "zero_output_excl_reserve_contract_inactive"); own("ownCcgt", "forced_state|ccgt_only"); own("ownCcgtTrip", "trips|ccgt_only")
own("ownNoSteam", "forced_state|no_steam"); own("ownFuelIdle", "fuel_idle")
put("ownLooLo", f1(A_["forced_state"]["loo_range"][0])); put("ownLooHi", f1(A_["forced_state"]["loo_range"][1]))
age = A_["forced_state"]["age"]; put("ageOldB", f1(age["20plus"]["b"])); put("ageOldSE", f1(age["20plus"]["se"])); put("ageOldP", pv(age["20plus"]["p"]))
put("newUnitB", f1(M["C"]["new_units_nonfuel_excl_test"]["b"])); put("newUnitSE", f1(M["C"]["new_units_nonfuel_excl_test"]["se"])); put("newUnitP", pv(M["C"]["new_units_nonfuel_excl_test"]["p"]))
cx = D["cox_return_hazard"]
for k, n in [("private", "Priv"), ("old", "Old"), ("tech_steam", "Steam"), ("tech_gas_turbine", "GT"), ("maint_class_maint_unspecified", "Unspec")]:
    put("cox" + n + "HR", f2(cx[k]["hr"])); put("cox" + n + "P", pv(cx[k]["p"]))
put("coxN", f0(D["n_spells"])); put("coxPrivN", f0([x for x in D["medians"]["owner"] if x["owner"] == "private"][0]["count"]))
# weather
B = M["B"]
put("tmaxSDraw", f1(B["tmax_sd_raw"])); put("tmaxSDwithin", f1(B["tmax_sd_within_unit_month"]))
put("heatTrips", f0(B["events"]["trips"])); put("heatOnsets", f0(B["events"]["forced_onsets"])); put("heatUnitDays", f0(B["events"]["unit_days"]))
put("heatTripsHot", f0(B["events_by_tbin"]["trip_any"]["ge36"])); put("heatOnsetsHot", f0(B["events_by_tbin"]["forced_onset"]["ge36"]))
def irr(prefix, r):
    put(prefix, f2(r["irr"])); put(prefix + "Lo", f2(r["lo"])); put(prefix + "Hi", f2(r["hi"])); put(prefix + "P", pv(r["p"]))
irr("heatTripIRR", B["trip_any|large_thermal|per_degC_irr"]); irr("heatTripCcgtIRR", B["trip_any|ccgt|per_degC_irr"])
irr("heatOnsetIRR", B["forced_onset|large_thermal|per_degC_irr"]); irr("heatOnsetCcgtIRR", B["forced_onset|ccgt|per_degC_irr"])
irr("hotTripIRR", B["trip_any|large_thermal|bins"]["ge36"]); irr("hotTripCcgtIRR", B["trip_any|ccgt|bins"]["ge36"])
irr("warmOnsetIRR", B["forced_onset|large_thermal|bins"]["33_36"]); put("warmOnsetPholm", pv(B["forced_onset|large_thermal|bins"]["33_36"]["p_holm"]))
irr("rainTripIRR", B["trip_any|large_thermal|rain_per10mm_irr"]); irr("rainTripCcgtIRR", B["trip_any|ccgt|rain_per10mm_irr"]); irr("rainOnsetIRR", B["forced_onset|large_thermal|rain_per10mm_irr"])
for k, n in [("electrical", "Elec"), ("grid", "Grid"), ("mechanical", "Mech"), ("fuel_supply", "Fuel"), ("control", "Ctrl")]:
    r = B[f"rain_cause|{k}"]; irr("rain" + n, r); put("rain" + n + "N", f0(r["events"]))
put("rainLpmB", f2(B["lpm_trip"]["prcp"]["b"])); put("rainLpmSE", f2(B["lpm_trip"]["prcp"]["se"])); put("tripMean", f1(B["lpm_trip_mean"]))
put("demB", f2(B["lpm_trip"]["dem_z"]["b"])); put("demSE", f2(B["lpm_trip"]["dem_z"]["se"]))
# IEEE
for t, n in [("ccgt", "Cc"), ("gas_turbine", "Gt"), ("steam", "St"), ("recip_engine", "Re")]:
    m = I["by_tech"][t]
    for k in ["EFOR", "EAF", "EAF_incl_OMC", "FOR"]: put(f"ieee{n}{k.replace('_','').replace('inclOMC','omc')}", f3(m[k]) if k in ("EFOR", "FOR") else f2(m[k]))
    put(f"ieee{n}Inactive", f0(100 * m["inactive_share"])); put(f"ieee{n}MTBF", f0(m["MTBF_service_days"]))
    w = I["weibull_tbf"].get(t)
    if w: put(f"wb{n}", f2(w["shape_beta"])); put(f"wb{n}Lo", f2(w["beta_ci95"][0])); put(f"wb{n}Hi", f2(w["beta_ci95"][1])); put(f"wb{n}Eta", f0(w["scale_eta_service_days"]))
    ca = I["crow_amsaa"].get(t);  put(f"ca{n}", f2(ca["beta"])) if ca else None
    lp = I["laplace"][t]; put(f"lap{n}Tested", f0(lp["units_tested"])); put(f"lap{n}Det", f0(lp["deteriorating"])); put(f"lap{n}Imp", f0(lp["improving"]))
for t, n in [("ccgt|private", "CcPriv"), ("ccgt|public", "CcPub")]:
    m = I["by_tech_owner"][t]; put(f"ieee{n}EFOR", f3(m["EFOR"])); put(f"ieee{n}EAF", f2(m["EAF"])); put(f"ieee{n}MTBF", f0(m["MTBF_service_days"]))
# sensitivity (second review)
S = I["sensitivity"]
for th, n in [(90, "Ninety"), (180, "OneEighty"), (365, "ThreeSixFive"), (None, "None")]:
    for t, tn in [("ccgt", "Cc"), ("gas_turbine", "Gt"), ("steam", "St")]:
        v = S[f"inactive_threshold_{th}"][t]; put(f"inact{n}{tn}EAF", f2(v["EAF"])); put(f"inact{n}{tn}Share", f0(100 * v["inactive_share"]))
for k, n in [("no_derates", "None"), ("all_fault_derates", "All"), ("shed_days_only", "Shed"), ("shortfall_ge_10pct", "Ten")]:
    for t, tn in [("ccgt", "Cc"), ("gas_turbine", "Gt"), ("steam", "St")]: put(f"efor{n}{tn}", f3(S["efor_derate_variants"][k][t]))
for t, tn in [("ccgt", "Cc"), ("gas_turbine", "Gt"), ("steam", "St"), ("recip_engine", "Re")]:
    w = S["weibull_per_unit"][t]; put(f"wbUnit{tn}", f2(w["median_unit_beta"])); put(f"wbUnit{tn}N", f0(w["units_fitted"])); put(f"wbUnit{tn}Lt", f0(100 * w["share_units_beta_lt1"]))
    put(f"wbBoot{tn}Lo", f2(w["pooled_beta_unit_bootstrap_ci"][0])); put(f"wbBoot{tn}Hi", f2(w["pooled_beta_unit_bootstrap_ci"][1]))
ry = S["rates_by_year"]
put("onsetRateNineteen", f1(ry["2019"]["forced_onsets_per_1000"])); put("onsetRateTwenty", f1(ry["2020"]["forced_onsets_per_1000"]))
put("onsetRateTwentyFour", f1(ry["2024"]["forced_onsets_per_1000"])); put("tripRateNineteen", f1(ry["2019"]["trips_per_1000"])); put("tripRateTwentyFour", f1(ry["2024"]["trips_per_1000"]))
for t, n in [("ccgt", "Cc"), ("gas_turbine", "Gt"), ("steam", "St"), ("recip_engine", "Re")]:
    m = I["by_tech"][t]; put(f"ieee{n}MTTRmean", f0(m["MTTR_days_mean"])); put(f"ieee{n}MTTRmed", f0(m["MTTR_days_median"]))
an = pd.read_parquet(ROOT / "data/analysis.parquet"); gfd = an[(an.tech == "gas_turbine") & (an.state == "forced")].unit_id.value_counts()
put("gtTopThreeShare", f0(100 * gfd.head(3).sum() / gfd.sum()))
# previously hard-coded numbers
dc = pd.read_csv(ROOT / "data/day_check.csv"); put("nCheckDays", f0(dc.tot_energy.notna().sum()))
uc = pd.read_csv(ROOT / "data/units_classified.csv", usecols=["remark"]); import re as _re
put("nRemarks", f0(uc.remark.fillna("").str.lower().map(lambda x: _re.sub(r"[^a-z0-9/+ ]", "", _re.sub(r"\s+", " ", x)).strip()).nunique()))
aw = json.load(open(ROOT / "out/age_weather_checks.json"))["dhaka_tmax_report_vs_power"]
put("dhakaR", f2(aw["corr"])); put("dhakaBias", f1(aw["mean_report"] - aw["mean_power"]))
um = pd.read_csv(ROOT / "data/units_master.csv"); th = um[um.tech.isin(["ccgt", "gas_turbine", "steam", "recip_engine"])]
put("nUndated", f0(th.cod_year.isna().sum()))
put("nPrivCcgt", f0(((um.tech == "ccgt") & (um.owner == "private")).sum()))
# audits
au = pd.read_csv(ROOT / "out/trip_link_audit_sample.csv"); put("auditN", f0(len(au))); put("auditCorrect", f0((au.audit == "correct").sum()))
tmpl = (ROOT / "paper/tab_ieee.tex").read_text().split("\n")
hdr_end = next(i for i, l in enumerate(tmpl) if l.strip() == "\\midrule"); bot = next(i for i, l in enumerate(tmpl) if l.strip() == "\\bottomrule")
rows = (ROOT / "paper/tab_ieee_rows.tex").read_text().rstrip().split("\n")
(ROOT / "paper/tab_ieee.tex").write_text("\n".join(tmpl[:hdr_end + 1] + rows + tmpl[bot:]) + "\n")
lines = [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(mac.items())]
(ROOT / "paper/numbers.tex").write_text("% generated by code/31_numbers.py - do not edit\n" + "\n".join(lines) + "\n")
print(len(mac), "macros")
