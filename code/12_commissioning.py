"""Commissioning dates from BPDB Annual Report 2022-23, 'Year Wise Commissioning Status of Generation Projects'
(2010 - June 2023) -> data/ext/commissioning_bpdb.csv"""
import csv, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
T = (ROOT / "data/ext/ar_651fabb73895432c99a7f6760e1b381d.txt").read_text().splitlines()
i0 = next(i for i, l in enumerate(T) if "Year Wise Commissioning Status" in l)
MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
DATE = re.compile(rf"(\d{{1,2}})\s*(?:st|nd|rd|th)?\s+({MONTH})\s*,?\s*(\d{{4}})", re.I)
ROW = re.compile(r"^\s*(\d{1,3})\.\s+(.+?)\s{2,}([\d.]+)\s{2,}(.+?)\s{2,}(\S.*?)\s{2,}(.+)$")
out, year = [], None
for k in range(i0, min(i0 + 900, len(T))):
    l = T[k]
    m = re.search(r"Projects\s+commissioned\s+in\s+(\d{4})", l, re.I)
    if m: year = int(m.group(1))
    m = ROW.match(l)
    if not m: continue
    d = DATE.search(m.group(6)) or DATE.search(l)
    out.append(dict(section_year=year, name=m.group(2).strip(), cap_mw=m.group(3), ownership=m.group(4).strip(),
                    fuel=m.group(5).strip(), date_text=m.group(6).strip(),
                    cod_year=int(d.group(3)) if d else year))
out = [r for r in out if DATE.search(r["date_text"])]   # undated rows are the pipeline table, not commissioned
with open(ROOT / "data/ext/commissioning_bpdb.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print(len(out), "commissioning rows;", sum(1 for r in out if DATE.search(r["date_text"])), "with a parsed date")
