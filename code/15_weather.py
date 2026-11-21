"""Daily weather per unit location from NASA POWER (no account): T2M, T2M_MAX, RH2M, PRECTOTCORR, Oct 2019 - latest.
-> data/ext/power/<lat>_<lon>.json, data/weather_daily.csv (lat, lon, date, ...)"""
import csv, json, subprocess, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PARAMS = "T2M,T2M_MAX,RH2M,PRECTOTCORR"
pts = sorted({(u["lat"], u["lon"]) for u in csv.DictReader(open(ROOT / "data/units_master.csv")) if u["lat"]})
def fetch(p):
    out = ROOT / f"data/ext/power/{p[0]}_{p[1]}.json"
    if out.exists() and out.stat().st_size > 10000: return p, "skip"
    url = (f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters={PARAMS}&community=RE"
           f"&latitude={p[0]}&longitude={p[1]}&start=20191001&end=20261118&format=JSON&time-standard=LST")
    for k in range(4):
        r = subprocess.run(["curl", "-sfL", "-m", "180", "-o", str(out), url])
        if r.returncode == 0: return p, "ok"
        time.sleep(5 * (k + 1))
    return p, "fail"
with ThreadPoolExecutor(3) as ex: res = list(ex.map(fetch, pts))
print({s: sum(1 for _, x in res if x == s) for s in ("ok", "skip", "fail")})
rows = []
for p in pts:
    f = ROOT / f"data/ext/power/{p[0]}_{p[1]}.json"
    if not f.exists(): continue
    d = json.load(open(f))["properties"]["parameter"]
    for day in d["T2M"]:
        vals = {k.lower(): d[k][day] for k in PARAMS.split(",")}
        if any(v == -999 for v in vals.values()): continue
        rows.append(dict(lat=p[0], lon=p[1], date=f"{day[:4]}-{day[4:6]}-{day[6:]}", **vals))
with open(ROOT / "data/weather_daily.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(pts), "points,", len(rows), "point-days, last date", max(r["date"] for r in rows))
