"""Scrape the BPDB daily-generation-archive listing into data/index.csv (date + file URLs)."""
import csv, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BASE = "https://misc.bpdb.gov.bd/daily-generation-archive?page={}"
UA = {"User-Agent": "Mozilla/5.0 (research data collection)"}
ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
HREF = re.compile(r'href="([^"]+)"')

def get(p, tries=4):
    # curl, not urllib: the server's certificate chain only verifies against the macOS keychain
    for k in range(tries):
        r = subprocess.run(["curl", "-sL", "-m", "60", "-A", UA["User-Agent"], BASE.format(p)], capture_output=True)
        if r.returncode == 0 and b"<tbody" in r.stdout:
            return r.stdout.decode("utf-8", "replace")
        time.sleep(2 * (k + 1))
    print("FAILED page", p, file=sys.stderr); return ""

def parse(p):
    out = []
    for row in ROW.findall(get(p)):
        tds = TD.findall(row)
        if len(tds) < 3 or not re.fullmatch(r"\s*\d+\s*", tds[0]): continue
        links = [ (HREF.search(t).group(1) if HREF.search(t) else "") for t in tds[2:] ]
        links += [""] * (6 - len(links))
        out.append([p, tds[0].strip(), tds[1].strip()] + links[:6])
    return out

with ThreadPoolExecutor(4) as ex:
    rows = [r for res in ex.map(parse, range(1, 695)) for r in res]
with open(ROOT / "data/index.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["page", "sl", "date", "page1", "page2", "page3", "report", "energy_gif", "load_gif"]); w.writerows(rows)
print(len(rows), "rows")
