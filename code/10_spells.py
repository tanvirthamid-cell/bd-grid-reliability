"""Outage spells and the planned/forced rule -> data/spells.csv, data/trips_linked.csv.
Spell = consecutive days a unit is fully off (gaps of one missing report day are bridged) WITH THE SAME CAUSE GROUP:
a change of stated cause (e.g. gas shortage -> machine problem) starts a new spell; days without a remark inherit the
previous day's cause. Cause groups: fuel (gas/other fuel/finance), maintenance (forced/planned/unspecified shutdown),
reserve, contract, grid, test, water, other.
Spells longer than 180 days WITHOUT any fault remark and not trip-initiated are classed 'inactive' (mothballed /
long-term unavailable, IEEE 762 inactive states). Long spells that name a fault stay forced outages. Column mclass_base
gives the classification without the inactive rule, and fault_any flags spells with a fault remark, for sensitivity analysis. Maintenance spells are split:
  planned  : any remark with overhaul / HGPI / inspection / scheduled / annual / AOH / renovation / BMRE / development
  forced   : any remark naming a fault (problem, fault, trip, leak, failure, ...)  OR a generator trip for that unit
             logged on the spell's first day or the day before (trip-initiated)
  maint_unspecified : plain 'Under maint.' with neither signal."""
import csv, re, difflib, collections, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PLANNED = re.compile(r"overhaul|hgpi|inspection|\bmi\b|\bci\b|schedul|annual|\baoh\b|renovat|rehab|bmre|development|major\s*maint", re.I)
FAULT = re.compile(r"problem|fault|trip|leak|fail|damage|vibrat|break\s*down|burn|defect|abnormal|crack|emergency|exciter|forced", re.I)
D = dt.date.fromisoformat
units = {m["unit_id"]: m for m in csv.DictReader(open(ROOT / "data/units_master.csv"))}
by = collections.defaultdict(list)
for r in csv.DictReader(open(ROOT / "data/panel.csv")): by[r["unit_id"]].append(r)

# ---- link trips to units: same leading location token, best name similarity among units alive that day
SPONSORS = ("summit", "united", "orion", "unique", "confidence", "doreen", "energypac", "max", "regent", "aggreko", "acorn", "baraka",
            "midland", "precision", "powerpac", "paramount", "jera", "reliance", "rpcl", "kpcl", "hpl", "mpl", "edra", "sinha")
def sponsors(s): return {x for x in re.findall(r"[a-z]+", s.lower()) if x in SPONSORS}
def toks(s): return re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()
LOCFIX = {"ghorashal": "ghorasal", "siddirganj": "siddhirganj", "siddhirgonj": "siddhirganj", "sikalbaha": "sikalbaha", "shikalbaha": "sikalbaha",
          "bibiyana": "bibiyana", "fenchugonj": "fenchuganj", "sirajgonj": "sirajganj", "b": "", "bhola": "bhola"}
def loc(s):
    t = [LOCFIX.get(x, x) for x in toks(s) if x not in ("a", "b", "c", "the", "-")]
    t = [x for x in t if x and x not in SPONSORS]
    t = [x for x in t if not x.isdigit()]
    return re.sub(r"h", "", t[0])[:5] if t else ""
def side(s):
    s = s.lower()
    return "s" if re.search(r"\(s\)|south", s) else "n" if re.search(r"\(n\)|north", s) else "e" if re.search(r"\(e\)|east", s) else ""
alive = collections.defaultdict(set)
for uid, rs in by.items():
    for r in rs: alive[r["op_date"]].add(uid)
def pdate(x):
    for f in ("%d-%b-%y", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d-%m-%y", "%d/%m/%y"):
        try: return dt.datetime.strptime(x.strip(" ,.'"), f).date()
        except ValueError: pass
P1DATE = {}
for r in csv.DictReader(open(ROOT / "data/system.csv")):
    pd_ = pdate(r.get("p1_data_date", "") or ""); fd = D(r["date"])
    P1DATE[r["date"]] = pd_ if pd_ and 0 <= (fd - pd_).days <= 2 else fd - dt.timedelta(days=1)
NOT_TRIP = re.compile(r"for\s+the\s+first\s+time|first\s+synchroni", re.I)
trips = [t for t in csv.DictReader(open(ROOT / "data/gen_trips.csv")) if not NOT_TRIP.search(t["text"])]
linked = []
for t in trips:
    od = str(P1DATE.get(t["file_date"], D(t["file_date"]) - dt.timedelta(days=1)))   # date the narrative describes
    lt = loc(t["plant"])
    cands = [u for u in alive.get(od, ()) if lt and (loc(units[u]["name"]) == lt or re.sub("h", "", units[u].get("town", ""))[:5] == lt)]
    un = re.search(r"unit\s*[-#]?\s*(\d)\b", t["plant"], re.I)               # 'Ghorasal Unit-7' must go to a unit-7 row
    if un:
        keep = [u for u in cands if re.search(rf"unit\s*[-#]?\s*{un.group(1)}\b", units[u]["name"], re.I)]
        if keep: cands = keep
    if re.search(r"bibiyana\s*-\s*3\b", t["plant"], re.I): t = dict(t, plant=re.sub(r"(?i)bibiyana\s*-\s*3", "Bibiyana-III", t["plant"]))
    rom = re.search(r"-\s*(iii|ii|iv)\b|\b(iii|ii|iv)\b", t["plant"].lower())
    if rom:                                                                 # Bibiyana-II vs Bibiyana-III
        rr = rom.group(1) or rom.group(2)
        keep = [u for u in cands if re.search(rf"(?<![a-z]){rr}(?![a-z])", units[u]["name"].lower())]
        if keep: cands = keep
    ts = sponsors(t["plant"])
    if ts and any(sponsors(units[u]["name"]) & ts for u in cands):          # a named sponsor must match
        cands = [u for u in cands if sponsors(units[u]["name"]) & ts]
    best, sim = "", 0.0
    nums = set(re.findall(r"(\d{2,4})\s*MW", t["plant"], re.I))
    for u in cands:
        s = difflib.SequenceMatcher(None, re.sub(r"[^a-z0-9]", "", t["plant"].lower()), u).ratio()
        unums = set(re.findall(r"(\d{2,4})\s*MW", units[u]["name"], re.I)) | {str(int(float(units[u]["cap_max"])))}
        if nums: s += 0.5 if nums & unums else -0.3        # the MW size in the trip text must agree with the unit
        if side(t["plant"]) and side(units[u]["name"]): s += 0.4 if side(t["plant"]) == side(units[u]["name"]) else -0.4
        if ts and sponsors(units[u]["name"]) & ts: s += 0.4                  # named sponsor agrees
        if s > sim: best, sim = u, s
    if sim < 0.55: best = ""                                                  # weak matches stay unlinked
    linked.append(dict(op_date=od, unit_id=best, link_sim=round(sim, 2), n_cands=len(cands), **{k: t[k] for k in ("plant", "trip_time", "sync_time", "cause_cat", "cause")}))
# de-duplicate: same unit, date and clock time; and a narrative repeated on the next day's report
seen, dedup = set(), []
for l in sorted(linked, key=lambda l: (l["unit_id"], l["op_date"], l["trip_time"])):
    if not l["unit_id"]:                                   # unlinked: de-duplicate on date, plant text and time
        k = ("?" + re.sub(r"[^a-z0-9]", "", l["plant"].lower()), l["op_date"], l["trip_time"])
        if k in seen: continue
        seen.add(k); dedup.append(l); continue
    if l["unit_id"]:
        k = (l["unit_id"], l["op_date"], l["trip_time"]); kprev = (l["unit_id"], str(D(l["op_date"]) - dt.timedelta(days=1)), l["trip_time"])
        if k in seen or (l["trip_time"] and kprev in seen): continue
        seen.add(k)
    dedup.append(l)
n_dup = len(linked) - len(dedup); linked = dedup
trip_days = collections.defaultdict(set)
for l in linked:
    if l["unit_id"]: trip_days[l["unit_id"]].add(l["op_date"])

# ---- spells
GROUP = {"fuel_gas": "fuel", "fuel_other": "fuel", "finance": "fuel", "forced": "maint", "planned": "maint", "shutdown_unspec": "maint",
         "dispatch": "reserve", "contract": "contract", "grid": "grid", "test": "test", "water": "water", "unclassified": "other"}
spells = []
for uid, rs in by.items():
    rs.sort(key=lambda r: r["op_date"]); cur = []
    def close():
        if not cur: return
        causes = collections.Counter(r["primary"] for r in cur if r["primary"] not in ("blank", "mode"))
        cause = causes.most_common(1)[0][0] if causes else "blank"
        rem = " | ".join(sorted({r["remark"] for r in cur if r["remark"].strip(" -")}))[:300]
        start = D(cur[0]["op_date"]); prev_ran = None
        i0 = rs.index(cur[0])
        if i0 > 0: prev_ran = int(rs[i0 - 1]["off"] == "0")
        trip_init = any(str(start - dt.timedelta(days=k)) in trip_days[uid] for k in (0, 1))
        days_ = (D(cur[-1]["op_date"]) - start).days + 1
        fault_any = bool(FAULT.search(rem) or trip_init or cause == "forced")
        base = ""
        if cause in ("planned", "forced", "shutdown_unspec"):
            base = "planned" if PLANNED.search(rem) else "forced" if fault_any else "maint_unspecified"
        mclass = "inactive" if (days_ > 180 and not fault_any) else base
        u = units[uid]
        spells.append(dict(unit_id=uid, tech=u["tech"], fuel=u["fuel"], owner=u["owner"], cap=max(float(r["cap"]) for r in cur),
                           start=cur[0]["op_date"], end=cur[-1]["op_date"], days=(D(cur[-1]["op_date"]) - start).days + 1,
                           n_reports=len(cur), cause=cause, maint_class=mclass, mclass_base=base, fault_any=int(fault_any), trip_initiated=int(trip_init), prev_day_ran=prev_ran,
                           left_censored=int(i0 == 0), right_censored=int(rs.index(cur[-1]) == len(rs) - 1), remarks=rem))
    grp = None
    for r in rs:
        if float(r["cap"]) <= 0: continue
        g = GROUP.get(r["primary"])                       # None for blank / running modes -> inherit
        if r["off"] == "1" and cur and (D(r["op_date"]) - D(cur[-1]["op_date"])).days <= 2 and (g is None or grp is None or g == grp):
            cur.append(r); grp = grp or g; continue
        close(); cur = [r] if r["off"] == "1" else []; grp = g if r["off"] == "1" else None
    close()
def dump(name, rows):
    with open(ROOT / "data" / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
dump("spells.csv", spells); dump("trips_linked.csv", linked)
print("trips kept", len(linked), "(dropped duplicates:", n_dup, ") linked", sum(bool(l["unit_id"]) for l in linked))
print("spells", len(spells))
m = collections.Counter(); md = collections.Counter()
for s in spells:
    if s["maint_class"]: m[s["maint_class"]] += 1; md[s["maint_class"]] += s["days"] * s["cap"]
T = sum(md.values())
print("maintenance-type spells:", dict(m), "| MW-day shares:", {k: round(100 * v / T, 1) for k, v in md.items()})
