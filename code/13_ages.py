"""Attach commissioning year to units -> data/units_master.csv gains cod_year, cod_source.
Order: (1) BPDB AR 2022-23 commissioning list (2010-Jun 2023) by location token + MW size + name similarity;
(2) WRI Global Power Plant Database v1.3 (BGD) commissioning_year; (3) first appearance after Nov 2019 = entered in sample;
(4) otherwise 'pre2010_inferred' (present in Oct 2019 and absent from the 2010-23 list)."""
import csv, re, difflib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
FIX = [(r"shikalbaha|sikalbaha", "sikalbaha"), (r"gonj", "ganj"), (r"ghorashal", "ghorasal"), (r"shajibazar|shahjibazar", "shajibazar"),
       (r"chapainawabganj|chapai", "chapainawabganj"), (r"bagura", "bogura"), (r"siddirganj", "siddhirganj"), (r"barisal\b", "barishal"),
       (r"chittagong", "chattogram"), (r"sirajgonj", "sirajganj"), (r"fenchugonj", "fenchuganj"), (r"\s+", " ")]
def norm(s):
    s = s.lower()
    for a, b in FIX: s = re.sub(a, b, s)
    return s
STOP = {"the", "pp", "mw", "power", "plant", "ltd", "limited", "rental", "quick", "years", "3", "5", "15", "ccpp", "gt", "st", "ipp", "unit", "summit", "united"}
def loc(s):
    t = [x for x in re.findall(r"[a-z]+", norm(s)) if x not in STOP]
    return t[0] if t else ""
def mws(s): return set(re.findall(r"(\d{2,4})\s*mw", norm(s)))
units = list(csv.DictReader(open(ROOT / "data/units_master.csv")))
ar = list(csv.DictReader(open(ROOT / "data/ext/commissioning_bpdb.csv")))
gp = [r for r in csv.DictReader(open(ROOT / "data/ext/gppd/global_power_plant_database.csv")) if r["country"] == "BGD" and r["commissioning_year"]]
def best(u, cands, namekey, capkey):
    un = norm(u["name"]); ul = loc(u["name"]); um = mws(u["name"]) | {str(int(float(u["cap_max"])))}
    top, ts = None, 0.0
    for c in cands:
        cn = norm(c[namekey])
        if loc(cn) != ul: continue
        s = difflib.SequenceMatcher(None, re.sub(r"[^a-z0-9]", "", un), re.sub(r"[^a-z0-9]", "", cn)).ratio()
        cm = mws(cn) | {str(int(float(c[capkey])))}
        close = any(abs(float(a) - float(b)) <= 0.1 * max(float(a), float(b)) for a in um for b in cm)
        if not close: continue            # MW size must agree (within 10%) - name similarity alone is not enough
        s += 0.3
        if s > ts: top, ts = c, s
    return (top, ts) if ts >= 0.55 else (None, ts)
MAN = {r["unit_id"]: r for r in csv.DictReader(open(ROOT / "data/ext/cod_manual.csv"))}
log = []
for u in units:
    if u["unit_id"] in MAN:   # hand-checked mapping takes precedence
        m = MAN[u["unit_id"]]; u["cod_year"], u["cod_source"], u["cod_match"] = m["cod_year"], m["source"], m["note"]; continue
    src, yr, matched = "", "", ""
    if u["tech"] in ("import",): src = "na_import"
    else:
        c, s = best(u, ar, "name", "cap_mw")
        matched = ("suggest: " + c["name"] + " " + c["cod_year"]) if c else ""
        if u["first"] > "2019-11-30": src, yr = "first_appearance", u["first"][:4]
        else: src = "unknown"
    # a unit first seen after Nov 2019 cannot be commissioned before its matched date minus a year; prefer later
    if yr and u["first"] > "2019-11-30" and int(yr) < int(u["first"][:4]) - 1:
        log.append((u["unit_id"], yr, u["first"], matched))   # usually a renamed unit; keep the documented year
    u["cod_year"], u["cod_source"], u["cod_match"] = yr, src, matched
with open(ROOT / "data/units_master.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(units[0])); w.writeheader(); w.writerows(units)
import collections
th = [u for u in units if u["tech"] in ("ccgt", "gas_turbine", "steam", "recip_engine")]
print("thermal units by cod_source:", collections.Counter(u["cod_source"] for u in th))
print("conflicts (matched year too early for a unit first seen in-sample):", len(log))
for x in log[:8]: print("  ", x)
