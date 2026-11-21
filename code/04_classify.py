"""Classify free-text unit remarks into outage causes -> data/units_classified.csv.
Operating date = date printed on page 2 (normally the file date minus one day)."""
import csv, datetime as dt, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
# order = priority when a remark carries several causes (used only for `primary`)
RULES = [
    ("contract", r"contr?act\s*(?:is\s*)?expir|contact expir|ppa\s*expir|tariff\s*expir"),
    ("finance",  r"bill\s*delay|late\s*pay|payment|fund\s*crisis|exchange\s*rate|neo\s*cut|\bdues\b|outstanding"),
    ("fuel_gas", r"gas\s*short|gas\s*restr|low\s*gas|gas\s*press|allocation\s*limit|titas|gas\s*\(?rms|rms\s*problem|dirty\s*gas|gas\s*suppl|gas\s*crisis|gas\s*limit|bgfcl|lng"),
    ("fuel_other", r"fuel\s*short|fuel\s*shortage|liquid\s*fuel|hfo\s*short|coal\s*short|fuel\s*conserv|oil\s*short|diesel\s*short|hsd\s*short|lack\s*of\s*fuel|coal\s*suppl|fuel\s*oil|fuel\s*sho\w*tage|bad\s*quality\s*coal|dirty\s*fuel|fuel\s*transfer|running\s*on\s*hsd"),
    ("forced",   r"problem|fault|trip|forced|leak|damage|fail|vibrat|dp\s*high|high\s*temp|flame|break\s*down|breakdown|burn|defect|abnormal|crack|tube|jammed|not\s*available\s*due|outage\s*due|emergency|fire\b|explos"),
    ("planned",  r"maint|overhaul|hgpi|inspection|\bmi\b|\bci\b|schedul|annual|\bu/?m\b|renovat|rehab|\bbmre\b|repower|\baoh\b|development\s*work|ti\s*works?"),
    ("grid",     r"line\s*o/?l|overload|over\s*load|line\s*fault|high\s*volt|low\s*volt|feeder|transformer\s*o/?l|bus\s*section|mvar|grid\s*volt|evacuat|\beif\b|interconnect|dead\s*bus|grid\s*constr|s/s|sub-?station|transmission|t/l|ckt"),
    ("water",    r"water\s*level|low\s*water|reservoir|rule\s*curve"),
    ("dispatch", r"reserv|low\s*demand|stand\s*-?by|nldc|authority\s*instruct|ready\s*to\s*dispatch|will\s*be\s*dispatch|to\s*be\s*dispatch|dispatching|demand\s*0|bad\s*weather|condenser\s*mode|economic|merit|\brsd\b|bed\s*weather|as\s*per\s*bpdb\s*instruct|nenp"),
    ("shutdown_unspec", r"shut\s*-?\s*down|\bs/?d\b|availability\s*(?:is\s*)?(?:less|zero)|blackout"),
    ("test",     r"on\s*test|testing|commission|trial|synchron|cod\b"),
    ("mode",     r"fgmo|agc|frequency\s*control|available|\bref\b"),
]
RX = [(k, re.compile(v, re.I)) for k, v in RULES]
EMPTY = re.compile(r"^[\s\-–.*0/:]*$|^none$|^1/1/1904$", re.I)

def classify(rem):
    if EMPTY.match(rem or ""): return [], "blank"
    cats = [k for k, rx in RX if rx.search(rem)]
    return cats, (cats[0] if cats else "unclassified")

def pdate(x):
    for f in ("%d-%m-%Y", "%d-%b-%y", "%d/%m/%Y", "%d-%b-%Y", "%d-%m-%y"):
        try: return dt.datetime.strptime(x, f).date()
        except ValueError: pass

def ukey(name):  # crude unit key; a hand crosswalk comes later
    return re.sub(r"[^a-z0-9]", "", name.lower())

if __name__ == "__main__":
    printed = {r["date"]: pdate(r["p2_printed_date"]) for r in csv.DictReader(open(ROOT / "data/system.csv"))}
    out = []
    for r in csv.DictReader(open(ROOT / "data/units.csv")):
        fd = dt.date.fromisoformat(r["date"]); pd = printed.get(r["date"])
        lag = (fd - pd).days if pd else None
        op = pd if lag in (0, 1, 2) else fd - dt.timedelta(days=1)   # implausible printed dates -> assume file-1
        cats, prim = classify(r["remark"])
        cap = float(r["cap"] or 0); peak = float(r["peak"] or 0); en = float(r["energy"] or 0)
        out.append(dict(op_date=op, file_date=r["date"], ukey=ukey(r["name"]), name=r["name"], producer=r["producer"],
                        cfg=r["cfg"], cap=cap, peak=peak, energy=en, off=int(peak <= 0 and en <= 0),
                        remark=r["remark"], cats="|".join(cats), primary=prim))
    with open(ROOT / "data/units_classified.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print(len(out), "rows")
