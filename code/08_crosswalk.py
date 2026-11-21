"""Unit crosswalk: map every unit-day row to a stable unit_id, then attach technology, fuel, owner, size.
-> data/unit_xwalk.csv (raw name/cfg -> unit_id), data/units_master.csv (one row per unit), data/panel.csv (unit-day)."""
import csv, re, difflib, collections, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SPELL = [(r"gonj", "ganj"), (r"ghorashal", "ghorasal"), (r"shikalbaha|sikalbaha", "sikalbaha"), (r"bagura", "bogura"),
         (r"bramhangoan|brahmanga\w*", "brahmangaon"), (r"sonargoan", "sonargaon"), (r"meghnaghat|megnaghat", "meghnaghat"),
         (r"chattogram|chittagong", "chattogram"), (r"barisal\b", "barishal"), (r"power\s*plant", "pp"), (r"power\s*station", "pp"),
         (r"\blimited\b|\bltd\.?", ""), (r"\b(?:ipp|pdb|bpdb|rpcl|egcb|apscl|nwpgcl|sipp|reb|qrpp|rpp|sbu)\b,?", ""), (r"\s*mw\b", "mw")]
def nkey(name):
    s = name.lower()
    for a, b in SPELL: s = re.sub(a, b, s)
    return re.sub(r"[^a-z0-9]", "", s)

rows = [r for r in csv.DictReader(open(ROOT / "data/units_classified.csv"))
        if not (r["producer"] == "Zone" or re.search(r"\bZone\s*$", r["name"]))]          # a day where page 1 was uploaded as page 2
# hand merges: same plant reported under a new name (checked by capacity and date ranges)
MANUAL = {"summitpowermadhabdiashulia": None, "meghnaghatuniquepower": "uniquemeghnaghatpowerumpl",
          "summitmeghanghat2589mwgas": "meghnaghatccppsummit2", "mirsharai150mwgas": "mirsharai150mw",
          "malanchactgepz": "malanchactgepzunited", "summitpowermadhabdi": None,
          # renamed when the report layout changed (Dec 2024 / Jan 2025): old id ends as new id starts
          "ashuganjccpp225mw": "ashuganj225mwccpp", "sikalbaha225mwccpp": "sikalbaha225mw",
          "sirajganj225mwccppunit1": "sirajganjunit1225mw", "sirajganj225mwccppunit2": "sirajganjunit2225mw",
          "sirajganj225mwccppunit3": "sirajganjunit3225mw", "siddhirganj210mwtpp": "210mwsiddhirganjtpp",
          "manikganj162mwpp": "manikganj162mwppmpgl", "juldahunit2": "juldahunit2acorn", "ashuganjtsk50mwpp": "ashuganj50mwpp",
          "sspoweriss": "sspower", "matarbari2600mwcpgcl": "matarbari2600mwcpgcbl", "sreepur150mw": "sreepur150mwppbrpl"}
for r in rows: r["nk"] = nkey(r["name"]); r["cfgk"] = r["cfg"].replace("MW", "").replace("×", "*").lower()
stats = collections.defaultdict(lambda: dict(n=0, first="9999", last="0000", cfg=collections.Counter(), cap=collections.Counter(), names=collections.Counter()))
for r in rows:
    s = stats[r["nk"]]; s["n"] += 1; s["first"] = min(s["first"], r["op_date"]); s["last"] = max(s["last"], r["op_date"])
    s["cfg"][r["cfgk"]] += 1; s["cap"][r["cap"]] += 1; s["names"][r["name"]] += 1
core = {k for k, s in stats.items() if s["n"] >= 60 and len(re.sub(r"\d", "", k)) >= 5}
# 1) merge core keys that are spelling variants: similar key, shared modal cfg, ranges overlapping < 10 days
parent = {k: k for k in core}
def find(k):
    while parent[k] != k: k = parent[k]
    return k
ck = sorted(core, key=lambda k: -stats[k]["n"])
for i, a in enumerate(ck):
    for b in ck[i + 1:]:
        if stats[a]["cfg"].most_common(1)[0][0] != stats[b]["cfg"].most_common(1)[0][0]: continue
        if difflib.SequenceMatcher(None, a, b).ratio() < 0.85: continue
        ov = (min(stats[a]["last"], stats[b]["last"]) > max(stats[a]["first"], stats[b]["first"]))
        if ov:  # both present at once -> distinct units unless one is tiny
            da = set(); continue
        parent[find(b)] = find(a)
# 2) map non-core rows to a core unit with the same cfg seen within +-7 days and best name similarity
by_cfg_day = collections.defaultdict(set)
for r in rows:
    if r["nk"] in core: by_cfg_day[(r["cfgk"], r["op_date"])].add(find(r["nk"]))
def near(cfgk, d):
    d0 = dt.date.fromisoformat(d); c = set()
    for k in range(-7, 8): c |= by_cfg_day.get((cfgk, str(d0 + dt.timedelta(days=k))), set())
    return c
xw = {}
for r in rows:
    key = (r["nk"], r["cfgk"])
    if key in xw: continue
    if r["nk"] in core: xw[key] = (find(r["nk"]), "core"); continue
    cand = near(r["cfgk"], r["op_date"])
    if cand:
        best = max(cand, key=lambda c: difflib.SequenceMatcher(None, r["nk"], c).ratio())
        sim = difflib.SequenceMatcher(None, r["nk"], best).ratio()
        if len(cand) == 1 or sim >= 0.6:
            xw[key] = (best, f"cfg+name({sim:.2f},{len(cand)})"); continue
    xw[key] = (r["nk"] or "unknown", "unmatched")
for r in rows:
    r["unit_id"], r["match"] = xw[(r["nk"], r["cfgk"])]
    if MANUAL.get(r["unit_id"]): r["unit_id"], r["match"] = MANUAL[r["unit_id"]], "manual"
# drop duplicate (unit, day) rows created by mapping: keep the row with the larger capacity
seen = {}
for r in rows:
    k = (r["unit_id"], r["op_date"])
    if k not in seen or float(r["cap"]) > float(seen[k]["cap"]): seen[k] = r
panel = list(seen.values())

# ---- attributes
COAL = r"(?<!united)payra|rampal|maitree|bifpcl|matarbari|cpgcbl|barapukuria|sspower|banshkhali|barishal307|barishalelectric|patuakhali|rnpl|1320|bcpcl"
def tech_of(name, cfg, cap):
    n = name.lower()
    if re.search(r"solar|\bpv\b", n): return "solar"
    if re.search(r"wind", n): return "wind"
    if re.search(r"kaptai(?!.*solar)|hydro", n): return "hydro"
    if re.search(r"import|tripura|hvdc|bheramara\s*\(hvdc|adani|godda|nepal", n): return "import"
    if re.search(r"rooppur|nuclear", n): return "nuclear"
    if re.search(r"ccpp|combined|repower", n): return "ccgt"
    if re.search(r"\bgt\b|gtpp|\bgt-?\d|peaking|simple\s*cycle|gas\s*turbine", n): return "gas_turbine"
    if re.search(r"\btpp\b|steam|\bst\b|stpp|thermal", n) or re.search(COAL, re.sub(r"[^a-z0-9]", "", n)): return "steam"
    m = re.match(r"(\d+(?:\.\d+)?)\*(\d+(?:\.\d+)?)", cfg)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        if min(a, b) <= 25 and max(a, b) >= 2 and (a * b) / max(1, min(a, b) if min(a,b) >= 2 else 1) and min(a, b) <= 25 and not (a == 1 or b == 1): return "recip_engine"
    return "unknown"
def owner_of(p, name=""):
    """Ownership of the generating company, not the contract type: state companies that sell as IPPs (RPCL) are public;
    small IPPs listed under 'SIPP, PDB/REB' (Summit, Doreen, Regent...) are private."""
    p = p.upper(); n = name.upper()
    if "IMPORT" in p or "IMPORT" in n: return "import"
    if re.search(r"BCPCL|RNPL|BIFPCL|NTPC", p + " " + n): return "public_jv"
    if re.search(r"\bRPCL\b|EGCB|APSCL|NWPGCL|CPGCL|CPGCBL|NPCBL|ROOPPUR", p + " " + n) and not re.search(r"\(UNITED|SUMMIT|ORION", n): return "public"
    if re.search(r"IPP|QRPP|RPP|RENTAL|SIPP|PRIVATE|NENP|\(UNITED\)", p): return "private"
    if re.search(r"SUMMIT|DOREEN|REGENT|UNITED|ORION|AGGREKO|CONFIDENCE|ENERGYPRIMA|PRECISION|MIDLAND|LAKDANAVI|RAJLANKA|BARAKA|POWERPAC|SINHA|DESH|EPL|GBB|MAX\)|ACORN|DIGITAL|BANCO|NORTHERN|SOUTHERN|PARAMOUNT|ECPV|CLC|KHANJAHAN|BANGLA TRAC|VENTURE|COFIDENCE", n): return "private"
    if re.search(r"PDB|SBU|REB|BPDB", p): return "public"
    return "unknown"
agg = collections.defaultdict(lambda: dict(n=0, name=collections.Counter(), prod=collections.Counter(), cfg=collections.Counter(),
                                           capmax=0.0, first="9999", last="0000", gas=0, oil=0, coal=0, energy=0.0))
for r in panel:
    a = agg[r["unit_id"]]; a["n"] += 1; a["name"][r["name"]] += 1; a["prod"][r["producer"]] += 1; a["cfg"][r["cfg"]] += 1
    a["capmax"] = max(a["capmax"], float(r["cap"])); a["first"] = min(a["first"], r["op_date"]); a["last"] = max(a["last"], r["op_date"])
    cats = r["cats"]; rem = r["remark"].lower()
    a["gas"] += ("fuel_gas" in cats) or ("gas" in rem); a["coal"] += "coal" in rem
    a["oil"] += bool(re.search(r"liquid|hfo|hsd|furnace\s*oil|diesel|\boil\b|fuel\s*shortage", rem)) and "gas" not in rem
    a["energy"] += float(r["energy"] or 0)
master = []
for uid, a in agg.items():
    name = a["name"].most_common(1)[0][0]; cfg = a["cfg"].most_common(1)[0][0]
    tech = tech_of(" ".join(a["name"]), cfg, a["capmax"])
    flat = re.sub(r"[^a-z0-9]", "", " ".join(a["name"]).lower())
    if tech in ("solar", "wind", "hydro", "import", "nuclear"): fuel = tech
    elif re.search(COAL, flat) or a["coal"] > 5: fuel = "coal"; tech = "steam" if tech in ("unknown", "recip_engine") else tech
    elif a["gas"] >= max(5, a["oil"]): fuel = "gas"
    elif a["oil"] > 5: fuel = "oil"
    elif tech in ("ccgt", "gas_turbine"): fuel = "gas"
    elif re.search(r"SIPP|REB", " ".join(a["prod"])) and tech == "recip_engine": fuel = "gas"
    elif tech == "steam": fuel = "gas"          # non-coal steam units here are the old gas-fired PDB/APSCL sets   # REB small-IPP engines are gas-fired
    else: fuel = "unknown"
    if tech == "unknown" and fuel == "gas": tech = "ccgt" if a["capmax"] >= 150 else "gas_turbine_or_engine"
    if tech == "unknown" and fuel == "oil": tech = "recip_engine"          # liquid-fuel IPPs here are HFO/HSD engines
    master.append(dict(unit_id=uid, name=name, n_names=len(a["name"]), producer=a["prod"].most_common(1)[0][0],
                       owner=owner_of(" ".join(a["prod"]), " ".join(a["name"])), tech=tech, fuel=fuel, cfg=cfg, cap_max=a["capmax"],
                       first=a["first"], last=a["last"], n_days=a["n"], entered_in_sample=int(a["first"] > "2019-11-30"),
                       energy_gwh=round(a["energy"] / 1e6, 1), gas_remark_days=a["gas"], oil_remark_days=a["oil"], coal_remark_days=a["coal"]))
master.sort(key=lambda m: -m["energy_gwh"])
def dump(name, rs, keys=None):
    with open(ROOT / "data" / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys or list(rs[0]), extrasaction="ignore"); w.writeheader(); w.writerows(rs)
dump("units_master.csv", master)
dump("unit_xwalk.csv", [dict(nkey=k[0], cfg=k[1], unit_id=v[0], match=v[1]) for k, v in sorted(xw.items())])
# documented ownership corrections (report's producer column is wrong or ambiguous)
OWNER_FIX = {"barishal307mw": "private"}   # Barisal Electric Power Co. (ISO Tech/PowerChina) IPP; NLDC lists it under BCPCL
# Bhairob 54.5 MW is an HFO engine IPP (3 x 18.2 MW); wrapped 2025 rows ('... Repowered CCPP Unit-3') leaked CCPP into its name list
TECH_FIX = {"bhairob545mw": ("recip_engine", "oil")}
for m in master:
    if m["unit_id"] in OWNER_FIX: m["owner"] = OWNER_FIX[m["unit_id"]]
    if m["unit_id"] in TECH_FIX: m["tech"], m["fuel"] = TECH_FIX[m["unit_id"]]
dump("units_master.csv", master)
info = {m["unit_id"]: m for m in master}
for r in panel:
    for k in ("tech", "fuel", "owner"): r[k] = info[r["unit_id"]][k]
dump("panel.csv", sorted(panel, key=lambda r: (r["unit_id"], r["op_date"])),
     ["unit_id", "op_date", "file_date", "name", "producer", "owner", "tech", "fuel", "cfg", "cap", "peak", "energy", "off", "remark", "cats", "primary", "match"])
print("rows", len(rows), "-> panel", len(panel), "| units", len(master), "| match types",
      collections.Counter(v[1].split("(")[0] for v in xw.values()))
