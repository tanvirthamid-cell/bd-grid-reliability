"""Assign each thermal/coal unit a town coordinate (hand table data/ext/town_coords.csv, ~0.05 deg accuracy;
NASA POWER cells are 0.5 x 0.625 deg, so town level is enough) -> units_master.csv gains lat, lon, town."""
import csv, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
towns = {r["town"]: (r["lat"], r["lon"]) for r in csv.DictReader(open(ROOT / "data/ext/town_coords.csv"))}
ALIAS = {"ghorashal": "ghorasal", "shikalbaha": "sikalbaha", "shahjibazar": "shajibazar", "bagura": "bogura", "bogra": "bogura",
         "bramhangoan": "brahmangaon", "kulna": "khulna", "siddirganj": "siddhirganj", "julda": "juldah", "bibiana": "bibiyana",
         "fenchugonj": "fenchuganj", "sirajgonj": "sirajganj", "manikgonj": "manikganj", "keranigonj": "keraniganj", "barisal": "barishal",
         "rpcl": "mymensingh", "potiya": "chattogram", "ecpv": "chattogram", "bhairob": "bhairob", "kalaish": "dohazari", "ctg": "chattogram",
         "jera": "meghnaghat", "unique": "meghnaghat", "reliance": "meghnaghat", "rnpl": "patuakhali", "bifpcl": "rampal", "cpgcbl": "matarbari",
         "lanka": "lankapower", "max": "ghorasal", "regent": "ghorasal", "chapai": "chapainawabganj", "nawabganj": "chapainawabganj", "b baria": "bbaria"}
units = list(csv.DictReader(open(ROOT / "data/units_master.csv")))
miss = []
for u in units:
    s = re.sub(r"[^a-z ]", " ", u["name"].lower() + " " + u["unit_id"])
    for a, b in ALIAS.items(): s = re.sub(rf"\b{a}\w*", b, s)
    words = s.split(); hit = next((w for w in words if w in towns), None)
    if not hit: hit = next((t for t in towns if t in u["unit_id"]), None)
    u["town"], (u["lat"], u["lon"]) = (hit, towns[hit]) if hit else ("", ("", ""))
    if not hit and u["tech"] not in ("import", "solar", "wind", "hydro", "nuclear"): miss.append(u["unit_id"])
with open(ROOT / "data/units_master.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(units[0])); w.writeheader(); w.writerows(units)
print("located", sum(bool(u["town"]) for u in units), "of", len(units), "| thermal unlocated:", miss)
