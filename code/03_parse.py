"""Parse every page-2 PDF into data/units.csv and check each day's parsed sums against the printed
'National Grid Total' line -> data/day_check.csv. Also pulls key page-1 fields -> data/system.csv."""
import csv, re, sys
from concurrent.futures import ThreadPoolExecutor  # work is pdftotext subprocesses
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); import parse_lib as P
ROOT = Path(__file__).resolve().parents[1]
TOT = re.compile(r"National\s+Grid\s+Total\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)", re.I)
TOT2 = re.compile(r"^\s*Total\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s*$", re.M)
P1 = {"energy_mkwh": r"Energy\s+Generated\s+([\d.,]+)", "unserved_mkwh": r"Energy\s+Unser\w*\s+([\d.,]+)",
      "eve_peak_dem_mw": r"Evening\s+Peak\s+Demand\s+([\d.,]+)", "eve_peak_gen_mw": r"Evening\s+Peak\s+Generation\s+([\d.,]+)",
      "day_peak_dem_mw": r"Day\s+Peak\s+Demand\s+([\d.,]+)", "max_temp_c": r"Maximum\s+Temperature\s+([\d.,]+)",
      "gas_mmcfd": r"Gas\s+Supplied\s+([\d.,]+)", "cost_tk_kwh": r"Cost\s+per\s+KWHr\.?\s+([\d.,]+)",
      "load_shed_mw": r"Load\s*[- ]?\s*shed\w*[^\d\n]{0,40}([\d.,]+)"}
# 2019-2024 layout ("DAILY REPORT Page -1") uses different labels
P1_OLD = {"energy_mkwh": r"Total\s+Gen\.?\s*\(MKWH\)\s*:\s*([\d.,]+)", "eve_peak_dem_mw": r"E\.P\.\s*Demand[^:]*:\s*([\d.,]+)",
          "eve_peak_gen_mw": r"Evening\s+Peak\s+Generation\s*:\s*([\d.,]+)", "gas_mmcfd": r"Gas\s+Consumed\s*:\s*Total\s*=\s*([\d.,]+)",
          "avail_max_gen_mw": r"Available\s+Max\s+Generation\s*:\s*([\d.,]+)", "max_temp_c": r"Max(?:imum)?\.?\s+Temp\w*[^\d\n]{0,20}([\d.]+)"}
DATE = re.compile(r"Date\s*:\s*(\d{1,2}[-/][A-Za-z0-9]{2,3}[-/]\d{2,4})")

def one(pdf):
    d = pdf.stem
    rows, miss = P.parse(pdf)
    t = P.text(pdf); m = TOT.search(t) or TOT2.search(t)
    tot = [P.num(x) for x in m.groups()] if m else [None] * 3
    chk = dict(date=d, n_rows=len(rows), cap=sum(r["cap"] or 0 for r in rows), peak=sum(r["peak"] or 0 for r in rows),
               energy=sum(r["energy"] or 0 for r in rows), tot_cap=tot[0], tot_peak=tot[1], tot_energy=tot[2],
               n_miss=sum(1 for l in miss if re.match(r"^(\d+|\*+)\s", l)))
    m = DATE.search(t); printed = m.group(1) if m else ""
    sysrow = {"date": d, "p2_printed_date": printed}
    p1 = ROOT / "data/raw/p1" / pdf.name
    if p1.exists():
        t1 = re.sub(r"[ \t]+", " ", P.text(p1))
        old = "DAILY REPORT" in t1
        m = re.search(r"Summary of Yesterday'?s?\s+(\S+)", t1) if old else DATE.search(t1)
        sysrow["p1_data_date"] = m.group(1) if m else ""
        for k, rx in {**P1, **(P1_OLD if old else {})}.items():
            mm = re.search(rx, t1, re.I); sysrow[k] = P.num(mm.group(1)) if mm else None
    return [dict(date=d, **r) for r in rows], chk, sysrow

if __name__ == "__main__":
    pdfs = sorted((ROOT / "data/raw/p2").glob("*.pdf"))
    with ThreadPoolExecutor(8) as ex: res = list(ex.map(one, pdfs))
    def dump(name, rows):
        with open(ROOT / "data" / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    dump("units.csv", [r for u, _, _ in res for r in u]); dump("day_check.csv", [c for _, c, _ in res])
    keys = ["date", "p2_printed_date", "p1_data_date"] + list(P1) + ["avail_max_gen_mw"]; dump("system.csv", [{k: s.get(k) for k in keys} for _, _, s in res])
    print(len(pdfs), "days,", sum(len(u) for u, _, _ in res), "unit-rows")
