"""County -> kategori atamalarını CSV/Excel dosyasından okur ve county'lerle eşler."""
import csv
import io
import re

COUNTY_HEADERS = {"county", "name", "fips", "ilce", "ilçe", "county_name", "countyname"}
CATEGORY_HEADERS = {"category", "kategori", "signal", "sinyal"}


def norm(text):
    s = str(text).lower().strip()
    s = re.sub(r"\bsaint\b", "st", s)
    s = re.sub(r"\bsainte\b", "ste", s)
    s = re.sub(r"\b(county|parish|city|borough)\b", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def _squash(text):
    return " ".join(str(text).lower().split())


class CountyMatcher:
    def __init__(self, counties):
        self.by_fips = {c.fips: c for c in counties}
        self.by_code = {c.fips[2:]: c for c in counties}
        self.by_full = {_squash(f"{c.name} {c.lsad}"): c for c in counties}
        self.by_norm = {}
        for c in counties:
            self.by_norm.setdefault(norm(c.name), []).append(c)

    def match(self, text):
        """(County, []) tek eşleşme; (None, adaylar) belirsiz; (None, []) bulunamadı."""
        t = str(text).strip()
        if re.fullmatch(r"\d{1,5}(\.0+)?", t):
            d = t.split(".")[0]
            c = self.by_fips.get(d.zfill(5)) if len(d) > 3 else self.by_code.get(d.zfill(3))
            return (c, []) if c else (None, [])
        c = self.by_full.get(_squash(t))
        if c:
            return c, []
        cands = self.by_norm.get(norm(t), [])
        if len(cands) == 1:
            return cands[0], []
        return None, list(cands)


def read_rows(filename, data):
    if filename.lower().endswith((".xlsx", ".xlsm")):
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        rows = [["" if v is None else str(v) for v in r] for r in wb.worksheets[0].iter_rows(values_only=True)]
    else:
        text = data.decode("utf-8-sig", errors="replace")
        lines = text.splitlines()
        first = lines[0] if lines else ""
        delim = max([",", ";", "\t"], key=first.count)
        rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    return [r for r in rows if any(str(x).strip() for x in r)]


def parse_assignments(filename, data, counties, categories):
    rows = read_rows(filename, data)
    if not rows:
        raise ValueError("Dosya boş.")
    head = [h.strip().lower() for h in rows[0]]
    ci = next((i for i, h in enumerate(head) if h in COUNTY_HEADERS), None)
    ki = next((i for i, h in enumerate(head) if h in CATEGORY_HEADERS), None)
    if ci is None or ki is None:
        ci, ki = 0, 1
    lookup = {}
    for c in categories:
        lookup[c["key"].lower()] = c["key"]
        lookup[c["label"].strip().lower()] = c["key"]
    matcher = CountyMatcher(counties)
    assign, unmatched, ambiguous = {}, [], []
    for n, r in enumerate(rows[1:], start=2):
        cname = r[ci].strip() if ci < len(r) else ""
        cat = r[ki].strip() if ki < len(r) else ""
        key = lookup.get(cat.lower())
        if key is None:
            unmatched.append({"row": n, "county": cname, "category": cat, "reason": "kategori bulunamadı"})
            continue
        c, cands = matcher.match(cname)
        if c:
            assign[c.fips] = key
        elif cands:
            ambiguous.append({"row": n, "county": cname, "candidates": [x.display for x in cands]})
        else:
            unmatched.append({"row": n, "county": cname, "category": cat, "reason": "county bulunamadı"})
    return {"assign": assign, "unmatched": unmatched, "ambiguous": ambiguous}
