"""Page-1 'Planned / Forced shut-down' unit lists and trip events -> data/shutdown_lists.csv, data/trip_events.csv.
Columns are split at the horizontal position of the 'Forced' header."""
import csv, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); import parse_lib as P
ROOT = Path(__file__).resolve().parents[1]
START = re.compile(r"under\s+shut\s*down|Status of unavailable", re.I)
END = re.compile(r"Additional Information|Event Summary|Total Unavailable|Sub Divisional", re.I)
TRIP = re.compile(r"\btripp?ed\b", re.I)

def one(pdf):
    lines = P.text(pdf).splitlines(); out, trips = [], []
    i = next((k for k, l in enumerate(lines) if START.search(l)), None)
    if i is not None:
        hdr = next((k for k in range(i, min(i + 6, len(lines))) if re.search(r"Forced", lines[k])), None)
        if hdr is not None:
            cut = lines[hdr].index(re.search(r"Forced", lines[hdr]).group(0)) - 8
            for l in lines[hdr + 1:]:
                if END.search(l): break
                for side, seg in (("planned", l[:cut]), ("forced", l[cut:])):
                    seg = seg.strip()
                    seg = re.sub(r"^(?:\d+\s*[).]?\s+)", "", seg)            # drop serial
                    seg = re.sub(r"\s{2,}[\d.]+$", "", seg)                   # drop capacity column
                    if seg and re.search(r"[A-Za-z]", seg) and not re.match(r"^(Sl|Plant Name|Total|Capacity)\b", seg):
                        out.append(dict(file_date=pdf.stem, side=side, entry=re.sub(r"\s+", " ", seg)))
    for l in lines:
        if TRIP.search(l): trips.append(dict(file_date=pdf.stem, text=re.sub(r"\s+", " ", l.strip())))
    return out, trips

if __name__ == "__main__":
    with ThreadPoolExecutor(8) as ex: res = list(ex.map(one, sorted((ROOT / "data/raw/p1").glob("*.pdf"))))
    for name, rows in (("shutdown_lists.csv", [r for a, _ in res for r in a]), ("trip_events.csv", [r for _, b in res for r in b])):
        with open(ROOT / "data" / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        print(name, len(rows))
