"""Build the tidy tables from the published SQL dump of Sander's compilation v5.0.0.

Usage: python3 -I build.py <henry_5.0.0_sql.zip> <paper.pdf> <outdir> <live species page>

Any other release can be built the same way: pass its zip (or the .sql file itself)
and set HENRY_ANY_VERSION=1. The version is read from the file name inside
(henry-X.Y.Z.sql) and the SQLite file is named henry_X.Y.Z.sqlite.

The live species page is only used for the short type labels (its legend); pass - to skip it.

Every value comes from the SQL file (or, for the type-code legend and the
unit conversion factor, from the text of the 2023 paper). Nothing is typed in
by hand.
"""
import hashlib
import html
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import zipfile
from decimal import Decimal

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sqldump import execute  # noqa: E402
from htmltext import to_text  # noqa: E402

ZIP_SHA256 = "d90b7264a55ebb2c42fcca4b3483d0cc5361caa177224685cc66f3f7d7fb9d1b"
SQL_MEMBER = "henry-5.0.0.sql"
SOURCE_URL = "https://henrys-law.org/henry_data/henry_5.0.0_sql.zip"

RE_HOMINUS = re.compile(
    r"^(?:(?P<lim>&gt;|&lt;) )?(?P<mant>\d+\.\d+)(?:&times;10<sup>(?P<neg>&#8722;)?(?P<exp>\d+)</sup>)?$")
RE_MINDHR = re.compile(r"^-?\d+$")
RE_DOI_HREF = re.compile(r'href="https?://(?:dx\.)?doi\.org/([^"]+)"')


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def read_sql(path, data):
    """Return (bytes, member name) of the SQL file: the zip member henry-*.sql, or the file itself."""
    if not zipfile.is_zipfile(io.BytesIO(data)):
        return data, os.path.basename(path)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        member = SQL_MEMBER if SQL_MEMBER in names else None
        if member is None:
            sql = [n for n in names if n.lower().endswith(".sql")]
            if len(sql) != 1:
                sys.exit("expected one .sql file in the zip, found %r" % sql)
            member = sql[0]
        return z.read(member), member


def sql_version(member):
    m = re.search(r"henry[-_](.+?)\.sql$", os.path.basename(member))
    return m.group(1) if m else "unknown"


def parse_hominus(s):
    """Return dict(status, limit, mantissa, exponent, exact, value)."""
    if s == "":
        return dict(status="empty", limit="", mantissa=None, exponent=None, exact="", value=None)
    if s == "&#8734;":  # the infinity sign, used for "infinitely soluble" estimates
        return dict(status="infinity", limit="", mantissa=None, exponent=None, exact="inf",
                    value=Decimal("Infinity"))
    m = RE_HOMINUS.match(s)
    if not m:
        return dict(status="parse_failure", limit="", mantissa=None, exponent=None, exact="", value=None)
    lim = {"&gt;": ">", "&lt;": "<", None: ""}[m.group("lim")]
    mant = m.group("mant")
    if m.group("exp") is None:
        exp = None
        dec = Decimal(mant)
        exact = mant
    else:
        exp = int(m.group("exp")) * (-1 if m.group("neg") else 1)
        dec = Decimal(mant).scaleb(exp)
        exact = "%se%d" % (mant, exp)
    return dict(status="ok", limit=lim, mantissa=mant, exponent=exp, exact=exact, value=dec)


def render_hominus(limit, mantissa, exponent):
    """Inverse of parse_hominus for status ok (used by the round-trip check)."""
    pre = {">": "&gt; ", "<": "&lt; ", "": ""}[limit]
    if exponent is None:
        return pre + mantissa
    return pre + mantissa + "&times;10<sup>" + ("&#8722;" if exponent < 0 else "") + str(abs(exponent)) + "</sup>"


def paper_legend_and_factor(pdf, codes):
    """Extract the type-code legend (Sect. 3.1) and the SI -> M/atm factor (Table 2).

    A legend entry is a line of the form “X” text..., where X is one of the
    type codes that occur in the SQL dump; the definition runs to the next
    blank line, the next entry, or the first line that ends a sentence
    (in the PDF text layer the paragraph after the list follows without a
    blank line).
    """
    pages = {}
    for p in range(1, 16):
        pages[p] = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), pdf, "-"],
                                  capture_output=True, text=True, check=True).stdout
    legend = []
    for p, txt in pages.items():
        lines = txt.split("\n")
        k = 0
        while k < len(lines):
            m = re.match(r"^“(.)” (.*)$", lines[k])
            if m and m.group(1) in codes and m.group(1) not in {l["code"] for l in legend}:
                code, text = m.group(1), [m.group(2)]
                k += 1
                while not text[-1].rstrip().endswith(".") and k < len(lines) and lines[k].strip() \
                        and not re.match(r"^“(.)” ", lines[k]):
                    text.append(lines[k].strip())
                    k += 1
                legend.append(dict(code=code, definition=re.sub(r"\s+", " ", " ".join(text)).strip(),
                                   pdf_page=p, journal_page=10900 + p))
                continue
            k += 1
    factor = None
    for p, txt in pages.items():
        m = re.search(r"= 1 mol m−3 Pa−1 ⇔ Hs\s*= ([0-9.]+) M atm−1", txt)
        if m:
            factor = (m.group(1), p, 10900 + p)
            break
    return legend, factor


def site_short_labels(page):
    """Short labels from the legend printed on every species page of the live site."""
    t = to_text(open(page, encoding="utf-8").read())
    m = re.search(r"listing the most reliable type first: (.*?)\. See Section 3\.1", t)
    if not m:
        return {}
    return {a: b.strip() for a, b in re.findall(r"(\S)\) ([^,]+)", m.group(1))}


def main():
    zpath, pdf, outdir, site_page = sys.argv[1:5]
    zbytes = open(zpath, "rb").read()
    is_v500 = sha256(zbytes) == ZIP_SHA256
    if not is_v500 and os.environ.get("HENRY_ANY_VERSION") != "1":
        sys.exit("zip SHA-256 mismatch: %s (set HENRY_ANY_VERSION=1 to build another release)" % sha256(zbytes))
    raw, member = read_sql(zpath, zbytes)
    version = sql_version(member)
    src = raw.decode("utf-8")
    tables, events, spans = execute(src)

    # ---------- categories / subcategories ----------
    cats = pd.DataFrame([dict(category_id=r["id"], category=r["catname"], sql_seq=r["sql_seq"])
                         for r in tables["categories"]])
    subcats = pd.DataFrame([dict(subcategory_id=r["id"], subcategory=r["subcatname"],
                                 category_id=r["cat_id"], category_key=r["cat_id__key"], sql_seq=r["sql_seq"])
                            for r in tables["subcategories"]])

    # ---------- species ----------
    sp = []
    for r in tables["species"]:
        sp.append(dict(species_id=r["id"], iupac=r["iupac"], iupac_text=to_text(r["iupac"]),
                       formula=r["formula"], formula_text=to_text(r["formula"]),
                       trivial=r["trivial"], trivial_text=to_text(r["trivial"]),
                       casrn=r["casrn"], inchikey=r["inchikey"],
                       subcategory_id=r["subcat_id"], subcategory_key=r["subcat_id__key"],
                       sql_seq=r["sql_seq"]))
    species = pd.DataFrame(sp)

    # ---------- literature ----------
    lit = []
    for r in tables["literature"]:
        dois = [html.unescape(d) for d in RE_DOI_HREF.findall(r["bibliography"])]
        lit.append(dict(literature_id=r["id"], bibtexkey=r["bibtexkey"],
                        quotation=r["quotation"], quotation_text=to_text(r["quotation"]),
                        bibliography=r["bibliography"], bibliography_text=to_text(r["bibliography"]),
                        doi=dois[0] if dois else "", doi_url=("https://doi.org/" + dois[0]) if dois else "",
                        n_doi_links=len(dois), sql_seq=r["sql_seq"]))
    literature = pd.DataFrame(lit)

    # ---------- notes ----------
    nt = []
    for r in tables["notes"]:
        nt.append(dict(note_id=r["id"], notelabel=r["notelabel"], noterefs=r["noterefs"],
                       notetext_html=r["notetext"], notetext_text=to_text(r["notetext"]),
                       sql_seq=r["sql_seq"]))
    notes = pd.DataFrame(nt)
    bib2id = {r["bibtexkey"]: r["id"] for r in tables["literature"]}
    nref = []
    for r in tables["notes"]:
        if r["noterefs"] == "":
            continue
        for pos, key in enumerate(r["noterefs"].split(","), start=1):
            nref.append(dict(note_id=r["id"], position=pos, bibtexkey=key,
                             literature_id=bib2id.get(key)))
    note_refs = pd.DataFrame(nref, columns=["note_id", "position", "bibtexkey", "literature_id"])

    # ---------- henry + links ----------
    links = []
    by_henry = {}
    for r in tables["henry_notes"]:
        links.append(dict(henry_id=r["henry_id"], note_id=r["notes_id"], notelabel=r["notes_id__key"],
                          sql_seq=r["sql_seq"]))
        by_henry.setdefault(r["henry_id"], []).append(r["notes_id"])
    henry_notes = pd.DataFrame(links)
    codes = sorted({r["htype"] for r in tables["henry"]})
    legend, factor = paper_legend_and_factor(pdf, set(codes))
    if factor is None or len(legend) != len(codes):
        sys.exit("could not extract legend/factor from the paper (%d codes)" % len(legend))
    fac = Decimal(factor[0])
    hrows = []
    for r in tables["henry"]:
        p = parse_hominus(r["hominus"])
        mh = r["mindhr"]
        mh_ok = mh == "" or bool(RE_MINDHR.match(mh))
        hrows.append(dict(
            henry_id=r["id"], species_id=r["species_id"], species_key=r["species_id__key"],
            literature_id=r["literature_id"], bibtexkey=r["literature_id__key"],
            htype=r["htype"],
            hominus_raw=r["hominus"], value_status=p["status"], limit_flag=p["limit"],
            hscp_mantissa=p["mantissa"] or "", hscp_exponent=p["exponent"],
            hscp_si_exact=p["exact"],
            hscp_si=float(p["value"]) if p["value"] is not None else None,
            hscp_matm=float(p["value"] * fac) if p["value"] is not None else None,
            hscp_matm_factor=float(fac),
            mindhr_raw=mh,
            mindhr_status="empty" if mh == "" else ("ok" if mh_ok else "parse_failure"),
            mindhr_K=int(mh) if (mh != "" and mh_ok) else None,
            note_ids=";".join(str(x) for x in by_henry.get(r["id"], [])),
            n_notes=len(by_henry.get(r["id"], [])),
            sql_seq=r["sql_seq"]))
    henry = pd.DataFrame(hrows)
    for c in ["species_id", "literature_id", "hscp_exponent", "mindhr_K"]:
        henry[c] = henry[c].astype("Int64")
    for df, c in [(note_refs, "literature_id"), (subcats, "category_id"), (species, "subcategory_id"),
                  (henry_notes, "henry_id"), (henry_notes, "note_id")]:
        df[c] = df[c].astype("Int64")

    # usage counts
    lit_use = henry["literature_id"].value_counts()
    literature["n_henry_rows"] = literature["literature_id"].map(lit_use).fillna(0).astype(int)
    note_use = henry_notes["note_id"].value_counts()
    notes["n_henry_rows"] = notes["note_id"].map(note_use).fillna(0).astype(int)
    sp_use = henry["species_id"].value_counts()
    species["n_henry_rows"] = species["species_id"].map(sp_use).fillna(0).astype(int)

    htcount = henry["htype"].value_counts()
    short = site_short_labels(site_page) if site_page != "-" else {}  # "-": no saved page, labels left empty
    htype_legend = pd.DataFrame([dict(code=l["code"], short_label=short.get(l["code"], ""),
                                      definition=l["definition"],
                                      source="Sander (2023), Atmos. Chem. Phys. 23, Sect. 3.1 (p. %d)" % l["journal_page"],
                                      n_henry_rows=int(htcount.get(l["code"], 0))) for l in legend])

    # ---------- write ----------
    os.makedirs(os.path.join(outdir, "csv"), exist_ok=True)
    os.makedirs(os.path.join(outdir, "parquet"), exist_ok=True)
    out = dict(categories=cats, subcategories=subcats, species=species, literature=literature,
               notes=notes, note_references=note_refs, henry=henry, henry_notes=henry_notes,
               htype_legend=htype_legend)
    for name, df in out.items():
        df.to_csv(os.path.join(outdir, "csv", name + ".csv"), index=False, encoding="utf-8", lineterminator="\n")
        df.to_parquet(os.path.join(outdir, "parquet", name + ".parquet"), index=False)
    sqlite_file = "henry_%s.sqlite" % version
    write_sqlite(os.path.join(outdir, sqlite_file), out)

    meta = dict(source_url=SOURCE_URL if is_v500 else os.path.basename(zpath),
                zip_sha256=sha256(zbytes), sql_member=member, version=version, sqlite_file=sqlite_file,
                sql_sha256=sha256(raw), sql_bytes=len(raw), statements=len(spans),
                conversion_factor_si_to_matm=factor[0],
                conversion_factor_source="Sander (2023), Table 2 (p. %d)" % factor[2],
                legend_source_pages=sorted({l["journal_page"] for l in legend}),
                paper_pdf_sha256=sha256(open(pdf, "rb").read()),
                events=events,
                counts={k: int(len(v)) for k, v in out.items()})
    json.dump(meta, open(os.path.join(outdir, "build_meta.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: meta[k] for k in ("statements", "counts", "conversion_factor_si_to_matm")}, indent=1))
    print("events:", len(events))
    for e in events:
        print(" ", e)


SQLITE_SCHEMA = {
    "categories": ("category_id INTEGER PRIMARY KEY", []),
    "subcategories": ("subcategory_id INTEGER PRIMARY KEY", ["FOREIGN KEY(category_id) REFERENCES categories(category_id)"]),
    "species": ("species_id INTEGER PRIMARY KEY", ["FOREIGN KEY(subcategory_id) REFERENCES subcategories(subcategory_id)"]),
    "literature": ("literature_id INTEGER PRIMARY KEY", []),
    "notes": ("note_id INTEGER PRIMARY KEY", []),
    "note_references": (None, ["PRIMARY KEY(note_id, position)", "FOREIGN KEY(note_id) REFERENCES notes(note_id)",
                                "FOREIGN KEY(literature_id) REFERENCES literature(literature_id)"]),
    "henry": ("henry_id INTEGER PRIMARY KEY", ["FOREIGN KEY(species_id) REFERENCES species(species_id)",
                                               "FOREIGN KEY(literature_id) REFERENCES literature(literature_id)"]),
    "henry_notes": (None, ["PRIMARY KEY(henry_id, note_id)", "FOREIGN KEY(henry_id) REFERENCES henry(henry_id)",
                           "FOREIGN KEY(note_id) REFERENCES notes(note_id)"]),
    "htype_legend": ("code TEXT PRIMARY KEY", []),
}


def sqlite_type(dtype):
    s = str(dtype)
    if s.startswith("int") or s.startswith("Int"):
        return "INTEGER"
    if s.startswith("float"):
        return "REAL"
    return "TEXT"


def py(v):
    """Convert a pandas/numpy scalar to a plain Python value for sqlite3."""
    if v is None or v is pd.NA:
        return None
    if isinstance(v, float) and v != v:
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def write_sqlite(path, out):
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys=ON")
    for name, df in out.items():
        pk, extra = SQLITE_SCHEMA[name]
        cols = []
        for c in df.columns:
            if pk and pk.split()[0] == c:
                cols.append(pk)
            else:
                cols.append('"%s" %s' % (c, sqlite_type(df[c].dtype)))
        con.execute('CREATE TABLE "%s" (%s)' % (name, ", ".join(cols + extra)))
        recs = [tuple(py(v) for v in row) for row in df.itertuples(index=False)]
        con.executemany('INSERT INTO "%s" VALUES (%s)' % (name, ",".join("?" * len(df.columns))), recs)
    con.execute("CREATE INDEX henry_species ON henry(species_id)")
    con.execute("CREATE INDEX henry_literature ON henry(literature_id)")
    con.commit()
    bad = con.execute("PRAGMA foreign_key_check").fetchall()
    con.execute("VACUUM")
    con.close()
    if bad:
        print("sqlite foreign_key_check rows:", len(bad))


if __name__ == "__main__":
    main()
