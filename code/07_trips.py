"""Generator trip events from the page-1 narratives -> data/gen_trips.csv.
Items start with 'a)'-style letters (2019-2023 layout) or a clock time (event table); continuation lines are joined.
Keeps items that say 'trip' about a generating unit (not a kV circuit, transformer, bus or substation),
extracts trip time, resync time and a cause phrase, and codes the cause into a small mechanical taxonomy."""
import csv, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); import parse_lib as P
ROOT = Path(__file__).resolve().parents[1]
BLOCK = re.compile(r"Additional Information|Event Summary", re.I)
STOP = re.compile(r"Sub Divisional Engineer|Executive Engineer|Superintend|Evening Peak Generation|Day Peak Generation", re.I)
NEWITEM = re.compile(r"^\s*(?:[a-z]{1,2}\)|\d{1,2}:\d{2})\s")
HDR = re.compile(r"QF-LDC|Power Grid|National Load|System Summary|^\s*Date\s*:|Outage\s+Rest|Description of Event|page \d", re.I)
TRIP = re.compile(r"\btripp?(?:ed|ing)?\b", re.I)
GEN = re.compile(r"CCPP|GTPP|STPP|\bGT\b|\bGT-?\d|\bST\b|\bSTG\b|\bGTG\b|TPP|\bPP\b|Unit|\bU-?#?\d|\bMW\b|Power\s*(?:Plant|Station|Ltd)|Engine|Rental|IPP", re.I)
NETW = re.compile(r"\d+\s*/?\s*\d*\s*kV|\bCkt\b|transformer|\bT-?\d+\b|\bBus\b|S/S|feeder|Interconnector|HVDC", re.I)
TIME = r"(\d{1,2}[:.]\d{2})"
CAUSES = [
    ("boiler",      r"feed\s*water|\bBFP\b|boiler|drum|\bMFT\b|furnace|flame|tube\s*leak|burner|economi[sz]er|super\s*heat|reheat|\bID\s*fan|\bFD\s*fan|\bPA\s*fan|coal\s*mill|mill\b"),
    ("cooling",     r"cooling\s*temp|cooling\s*water|\bCW\b|CWP|condens|vacuum|cooling\s*tower|circulat"),
    ("turbine",     r"turbine|vibrat|over\s*speed|lube|lub\.?\s*oil|bearing|exhaust\s*temp|axial|thrust|blade|compressor|seal\s*oil|hydraulic"),
    ("electrical",  r"\bo/[vc]\b|over\s*(?:voltage|current)|unit\s*transformer|auxiliary\s*(?:power|failure)|generator|exci|\bAVR\b|E/F|earth\s*fault|differential|\b87\b|relay|protection|aux\.?\s*(?:iliary)?\s*transformer|\bUAT\b|\bGT\s*transformer|breaker|\bCB\b|reverse\s*power|loss\s*of\s*excitation|stator|rotor"),
    ("fuel_supply", r"\bGBC\b|gas\s*(?:booster|buster|short|problem|line|concentr)|booster|gas\s*press|low\s*gas|fuel|\bDP\s*high|filter|\bRMS\b|gas\s*valve|gas\s*supply|oil\s*press|diesel"),
    ("control",     r"gas\s*detect|fire\s*detect|\bDCS\b|control|signal|sensor|transmitter|instrument|PLC|communicat|card|logic|valve"),
    ("grid",        r"tripping\s+of\s+.*(?:kV|Ckt|line|bus)|grid|frequency|system\s*disturb|line\s*trip|blackout|islanding|voltage|evacuation|dead\s*bus"),
    ("engine",      r"engine|cylinder|piston|crank|turbo\s*charg|radiator"),
]
CRX = [(k, re.compile(v, re.I)) for k, v in CAUSES]

def items(text):
    lines = text.splitlines()
    k = next((i for i, l in enumerate(lines) if BLOCK.search(l)), None)
    if k is None: return []
    out, cur = [], None
    for l in lines[k + 1:]:
        if STOP.search(l) and not NEWITEM.match(l): 
            if cur: out.append(cur); cur = None
            continue
        if HDR.search(l) or not l.strip(): continue
        left = re.split(r"\s{12,}", l.strip())          # drop far-right side notes
        seg = " ".join(left[:2]) if NEWITEM.match(l) and len(left) > 1 and re.fullmatch(r"\d{1,2}:\d{2}", left[0]) else left[0]
        if NEWITEM.match(l):
            if cur: out.append(cur)
            cur = re.sub(r"\s+", " ", l.strip())
        elif cur is not None:
            cur += " " + re.sub(r"\s+", " ", seg)
    if cur: out.append(cur)
    return out

def parse_item(s):
    m = TRIP.search(s)
    if not m: return None
    before = s[:m.start()]
    if not GEN.search(before) or NETW.search(before): return None
    t_old = re.search(r"tripp?ed\s+at\s+" + TIME, s, re.I)
    t_new = re.match(r"^\s*" + TIME, s)
    sync = re.search(r"synchroni[sz]ed\s+at\s+" + TIME + r"(?:\s*\(([\d/]+)\))?", s, re.I)
    cause = re.search(r"(?:due\s+to|showing|with\s+remarks\s*:?-?|for)\s+(.+?)(?:\s+and\s+(?:was|were)\b|\.\s|$)", s[m.start():], re.I)
    cause = cause.group(1).strip(" .") if cause else ""
    plant = re.sub(r"^\s*(?:[a-z]{1,2}\)|\d{1,2}:\d{2}(?:\s+\d{1,2}:\d{2})?)\s*", "", before).strip(" ,")
    plant = re.sub(r"\b(?:was|were|is|has been)\s*$", "", plant).strip()
    if re.fullmatch(r"(?:GT|ST|STG|GTG|unit|U)?\s*[-#]?\s*\d*(?:\s*(?:&|and)\s*(?:GT|ST|U|unit)?\s*[-#]?\d*)*|(?:GT|ST|STG|GTG)", cause, re.I):
        cause = ""            # 'with remarks:- GT-2' names the unit, not the cause
    cats = [k for k, rx in CRX if rx.search(cause)]
    return dict(plant=plant, trip_time=(t_old or t_new).group(1).replace(".", ":") if (t_old or t_new) else "",
                sync_time=sync.group(1).replace(".", ":") if sync else "", sync_date_note=(sync.group(2) or "") if sync else "",
                cause=cause, cause_cat=cats[0] if cats else ("unstated" if not cause else "other"), cause_all="|".join(cats), text=s)

def one(pdf):
    rows, seen = [], set()
    for it in items(P.text(pdf)):
        r = parse_item(it)
        if not r: continue
        key = (re.sub(r"[^a-z]", "", r["plant"].lower())[:8], r["trip_time"])
        if key in seen:   # event table repeats a short and a detailed line; keep the more informative
            prev = next(x for x in rows if (re.sub(r"[^a-z]", "", x["plant"].lower())[:8], x["trip_time"]) == key)
            if len(r["cause"]) > len(prev["cause"]): rows[rows.index(prev)] = dict(file_date=pdf.stem, **r)
            continue
        seen.add(key); rows.append(dict(file_date=pdf.stem, **r))
    return rows

if __name__ == "__main__":
    with ThreadPoolExecutor(8) as ex: res = [r for rs in ex.map(one, sorted((ROOT / "data/raw/p1").glob("*.pdf"))) for r in rs]
    with open(ROOT / "data/gen_trips.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0])); w.writeheader(); w.writerows(res)
    print(len(res), "generator trip events")
