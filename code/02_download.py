"""Download page-1 (system summary) and page-2 (unit table) PDFs for every dated archive row.
Saves data/raw/p{1,2}/YYYY-MM-DD.pdf; skips files already present; placeholders are skipped."""
import csv, datetime as dt, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
UA = "Mozilla/5.0 (research data collection)"
jobs = []
for x in csv.DictReader(open(ROOT / "data/index.csv")):
    try: d = dt.datetime.strptime(x["date"], "%d/%m/%Y").date()
    except ValueError: continue
    for k in ("page1", "page2"):
        u = x[k]
        if u and "no_pdf_found" not in u:
            jobs.append((u, ROOT / f"data/raw/p{k[-1]}/{d}.pdf"))
def fetch(job):
    u, out = job
    if out.exists() and out.stat().st_size > 1000: return "skip"
    for k in range(4):
        r = subprocess.run(["curl", "-sfL", "-m", "120", "-A", UA, "-o", str(out), u])
        if r.returncode == 0 and out.read_bytes()[:4] == b"%PDF": return "ok"
        time.sleep(3 * (k + 1))
    print("FAILED", u, out.name, file=sys.stderr); return "fail"
with ThreadPoolExecutor(4) as ex:
    res = list(ex.map(fetch, jobs))
print({s: res.count(s) for s in set(res)})
