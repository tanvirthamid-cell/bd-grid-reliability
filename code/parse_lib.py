"""Parsing helpers for NLDC page-2 unit tables (pdftotext -layout output).
A unit row is: [serial] name producer CFG CAP PEAK ENERGY [remark], where CFG is the unit configuration
('2*105', '1*217+118', '100 MW', or '0'). Rows are found by scanning whitespace tokens from the left for
the first CFG followed by three numbers (no backtracking regex)."""
import re, subprocess
CFG1 = re.compile(r"\d+(?:\.\d+)?(?:[*xX×]\d+(?:\.\d+)?)?(?:[+&]\d+(?:\.\d+)?(?:[*xX×]\d+(?:\.\d+)?)?)*(?:MW)?")
NUMT = re.compile(r"-?\d[\d,]*(?:\.\d+)?|-")
SERIAL = re.compile(r"\d+|\*+")

def text(pdf):
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout

def num(s):
    s = s.replace(",", "")
    try: return float(s)
    except ValueError: return None

def parse_line(line):
    # glue '1*217 + 118' and '100 MW' into single tokens before splitting
    s = re.sub(r"\s*([*xX×+&])\s*(?=\d)", r"\1", line.strip())
    s = re.sub(r"(\d)\s+MW\b", r"\1MW", s)
    s = re.sub(r"(\s\d{4,}(?:\.\d+)?)(?=[A-Za-z])", r"\1 ", s)   # energy glued to remark: '14176362Partial'
    s = re.sub(r"(\s\d[\d.]*)MW(?=[A-Za-z])", r"\1MW ", s)
    tok = s.split()
    if len(tok) < 5 or "Total" in tok: return None
    start = 1 if SERIAL.fullmatch(tok[0]) else 0
    for i in range(start + 1, len(tok) - 3):
        if CFG1.fullmatch(tok[i]) and all(NUMT.fullmatch(t) for t in tok[i + 1:i + 4]) and tok[i + 1] != "-":
            pre = tok[start:i]
            if not pre or not re.search(r"[A-Za-z]", " ".join(pre)): return None
            name, prod = (" ".join(pre[:-1]), pre[-1]) if len(pre) > 1 else (pre[0], "")
            return dict(sl=tok[0] if start else "", name=name, producer=prod, cfg=tok[i],
                        cap=num(tok[i + 1]), peak=num(tok[i + 2]), energy=num(tok[i + 3]), remark=" ".join(tok[i + 4:]))
    # second pass: energy pushed onto the next line by a long remark -> CFG CAP PEAK <remark>
    for i in range(start + 1, len(tok) - 2):
        if CFG1.fullmatch(tok[i]) and all(NUMT.fullmatch(t) for t in tok[i + 1:i + 3]) and tok[i + 1] != "-" \
                and (i + 3 == len(tok) or not NUMT.fullmatch(tok[i + 3])):
            pre = tok[start:i]
            if not pre or not re.search(r"[A-Za-z]", " ".join(pre)): return None
            name, prod = (" ".join(pre[:-1]), pre[-1]) if len(pre) > 1 else (pre[0], "")
            return dict(sl=tok[0] if start else "", name=name, producer=prod, cfg=tok[i], cap=num(tok[i + 1]),
                        peak=num(tok[i + 2]), energy=None, remark=" ".join(tok[i + 3:]), _need_energy=True)
    return None

def parse(pdf):
    rows, miss = [], []
    lines = [l for l in text(pdf).splitlines() if l.strip()]
    for k, line in enumerate(lines):
        r = parse_line(line)
        if r and r.pop("_need_energy", False):
            nxt = lines[k + 1].strip() if k + 1 < len(lines) else ""
            if re.fullmatch(r"\d[\d,]*(?:\.\d+)?", nxt): r["energy"] = num(nxt)
            else: r["energy"] = 0.0 if r["peak"] == 0 else None   # unrecoverable; flagged by day check
        (rows.append(r) if r else miss.append(line.strip()))
    return rows, miss
