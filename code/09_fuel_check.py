"""Check inferred unit fuels against page-1 'Zone-wise Generation Summary' fuel totals (2025-26 layout only)."""
import csv, re, sys, collections, json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); import parse_lib as P
ROOT = Path(__file__).resolve().parents[1]
COLS = ["gas", "coal", "hfo", "hsd", "hydro", "solar", "import", "wind", "nuclear", "total"]
def one(pdf):
    t = P.text(pdf)
    i = t.find("Zone-wise Generation Summary")
    if i < 0: return None
    seg = t[i:i + 4000]
    h = re.search(r"^\s*(Gas\s+Coal.*Total)\s*$", seg, re.M)
    m = re.search(r"^\s*Total\s+([\d.\s]+)$", seg, re.M)
    if not (h and m): return None
    cols = [c.lower() for c in h.group(1).split()]; vals = [float(x) for x in m.group(1).split()]
    if len(cols) != len(vals): return None
    d = dict.fromkeys(COLS, 0.0); d.update(zip(cols, vals))
    return pdf.stem, d
with ThreadPoolExecutor(8) as ex: off = dict(x for x in ex.map(one, sorted((ROOT / "data/raw/p1").glob("2025-*.pdf")) + sorted((ROOT / "data/raw/p1").glob("2026-*.pdf"))) if x)
mine = collections.defaultdict(collections.Counter)
for r in csv.DictReader(open(ROOT / "data/panel.csv")):
    if r["file_date"] in off: mine[r["file_date"]][r["fuel"]] += float(r["energy"] or 0) / 1e6
# keep days where the official table total agrees with the unit-table total (drops misparsed / kWh-scaled days)
good = {d: o for d, o in off.items() if o["total"] and abs(sum(mine[d].values()) / o["total"] - 1) < 0.02}
tot = collections.Counter(); ref = collections.Counter()
for d, o in good.items():
    for k, v in mine[d].items(): tot[k] += v
    ref["gas"] += o["gas"]; ref["coal"] += o["coal"]; ref["oil"] += o["hfo"] + o["hsd"]; ref["hydro"] += o["hydro"]
    ref["solar"] += o["solar"]; ref["import"] += o["import"]; ref["wind"] += o["wind"]; ref["nuclear"] += o["nuclear"]
res = {k: dict(official_gwh=round(ref[k]), inferred_gwh=round(tot[k]), ratio=round(tot[k] / ref[k], 3) if ref[k] else None) for k in ref}
res["unknown"] = dict(inferred_gwh=round(tot["unknown"]))
res["days_parsed"] = len(off); res["days_used"] = len(good)
json.dump(res, open(ROOT / "out/fuel_check.json", "w"), indent=1); print(json.dumps(res, indent=1))
