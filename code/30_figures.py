"""Figures for the paper -> paper/fig/*.pdf"""
import json, pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; F = ROOT / "paper/fig"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "font.family": "serif"})
# Fig 1: monthly mean unavailable capacity by cause (evening-peak snapshot), Oct 2019 - Dec 2024
d = pd.read_csv(ROOT / "out/daily.csv"); d = d[d.op_date <= "2024-12-31"]; d["m"] = pd.to_datetime(d.op_date).dt.to_period("M").dt.to_timestamp()
cols = [("fuel_gas", "Gas shortage"), ("fuel_other", "Oil/coal shortage"), ("finance", "Payment/finance"), ("forced", "Forced (fault)"),
        ("planned", "Maintenance"), ("dispatch", "Reserve/low demand"), ("grid", "Grid constraint"), ("blank", "No remark"), ("other", "Other")]
m = d.groupby("m")[[c for c, _ in cols]].mean() / 1000
fig, ax = plt.subplots(figsize=(6.5, 3.0))
ax.stackplot(m.index, *[m[c] for c, _ in cols], labels=[l for _, l in cols], colors=plt.cm.tab20.colors[:len(cols)], linewidth=0)
ax.set_ylabel("GW not generating at evening peak"); ax.legend(ncol=3, fontsize=7, frameon=False, loc="upper left")
ax.set_xlim(m.index.min(), m.index.max()); fig.tight_layout(); fig.savefig(F / "fig1_lost_capacity.pdf"); plt.close(fig)
# Fig 2: trip rate by cause and rainfall
a = pd.read_parquet(ROOT / "data/analysis.parquet"); a = a[(a.tech != "recip_engine") & a.ran_yday & a.prcp.notna()]
t = pd.read_csv(ROOT / "data/trips_linked.csv")[["unit_id", "op_date", "cause_cat"]].dropna(subset=["unit_id"]).drop_duplicates(["unit_id", "op_date", "cause_cat"])
x = a.merge(t, on=["unit_id", "op_date"], how="left")
x["wet"] = pd.cut(x.prcp, [-1, 1, 10, 30, 1000], labels=["<1", "1–10", "10–30", ">30"])
cats = [("electrical", "Electrical"), ("grid", "Grid"), ("boiler", "Boiler/HRSG"), ("turbine", "Turbine"), ("fuel_supply", "Fuel supply")]
g = x.groupby("wet", observed=True)
fig, ax = plt.subplots(figsize=(6.0, 2.8)); w = 0.15
for i, (c, l) in enumerate(cats):
    ax.bar(np.arange(4) + (i - 2) * w, [1000 * (v.cause_cat == c).sum() / len(v) for _, v in g], w, label=l)
ax.set_xticks(range(4)); ax.set_xticklabels([f"{k} mm\n(n={len(v):,})" for k, v in g]); ax.set_ylabel("Trips per 1,000 unit-days")
ax.legend(fontsize=7, frameon=False, ncol=5, loc="upper left"); fig.tight_layout(); fig.savefig(F / "fig2_rain_causes.pdf"); plt.close(fig)
# Fig 3: Poisson incidence-rate ratios by Tmax bin (unit + year-month FE), from out/analysis/main.json
h = json.load(open(ROOT / "out/analysis/main.json"))["B"]
bins = ["lt27", "27_30", "30_33", "33_36", "ge36"]; lab = ["<27", "27–30", "30–33\n(ref.)", "33–36", "≥36"]
fig, axs = plt.subplots(1, 2, figsize=(6.5, 2.6))
for ax, (key, title) in zip(axs, [("trip_any", "Trips"), ("forced_onset", "Forced-outage onsets")]):
    for j, (grp, mk) in enumerate([("large_thermal", "o"), ("ccgt", "s")]):
        co = h[f"{key}|{grp}|bins"]
        irr = np.array([1 if k == "30_33" else co[k]["irr"] for k in bins]); lo = np.array([1 if k == "30_33" else co[k]["lo"] for k in bins]); hi = np.array([1 if k == "30_33" else co[k]["hi"] for k in bins])
        ax.errorbar(np.arange(5) + (j - .5) * .15, irr, yerr=[irr - lo, hi - irr], fmt=mk, ms=4, capsize=2, label="All large thermal" if grp == "large_thermal" else "Combined cycle")
    ax.axhline(1, color="grey", lw=.6); ax.set_yscale("log"); ax.set_yticks([0.25, 0.5, 1, 2, 4, 8]); ax.set_yticklabels(["0.25", "0.5", "1", "2", "4", "8"]); ax.minorticks_off(); ax.set_xticks(range(5)); ax.set_xticklabels(lab, fontsize=7); ax.set_title(title, fontsize=9)
    ax.set_xlabel("Daily maximum temperature (°C)")
axs[0].set_ylabel("Incidence-rate ratio vs 30–33 °C"); axs[0].legend(fontsize=7, frameon=False)
fig.tight_layout(); fig.savefig(F / "fig3_heat.pdf"); plt.close(fig)
print("figures written")
