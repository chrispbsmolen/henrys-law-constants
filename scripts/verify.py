"""Verify the tidy tables against the SQL dump and list internal inconsistencies.

Usage: python3 -I verify.py <henry_5.0.0_sql.zip> <supplement.zip> <outdir> <reportdir>

The tables are read back from the CSV files (not from memory), and every
INSERT statement of the dump is regenerated from them and compared byte for
byte with the original. The Parquet and SQLite copies are compared with the
CSV copy. The values are also compared with the Fortran declarations in the
paper's supplement (output/HscpSI.f90 in mol/(m3 Pa), output/Hscp.f90 in
M/atm), which were produced by the same program as the SQL dump.
"""
import collections
import io
import json
import math
import os
import re
import sqlite3
import sys
import zipfile
from decimal import Decimal

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import ZIP_SHA256, SQL_MEMBER, render_hominus, sha256  # noqa: E402
from sqldump import sql_quote  # noqa: E402

SUPPL_SHA256 = "fb0bdedf7ff59afb1ac012b8bc0b64c58e2c6cf666b00a48d26d173aeb6149c7"
EXPECTED = dict(henry=46434, species=10173, henry_notes=45471, literature=1076)
KILL_PARSE_RATE = 0.001

TABLES = ["categories", "subcategories", "species", "literature", "notes", "note_references",
          "henry", "henry_notes", "htype_legend"]


def read_csv(d, name):
    return pd.read_csv(os.path.join(d, "csv", name + ".csv"), dtype=str, keep_default_na=False,
                       encoding="utf-8")


def regenerate(t):
    """Rebuild every INSERT statement from the CSV tables, keyed by sql_seq."""
    out = {}
    cat = dict(zip(t["categories"].category_id, t["categories"].category))
    sub = dict(zip(t["subcategories"].subcategory_id, t["subcategories"].subcategory))
    spn = dict(zip(t["species"].species_id, t["species"].iupac))
    bib = dict(zip(t["literature"].literature_id, t["literature"].bibtexkey))
    nlab = dict(zip(t["notes"].note_id, t["notes"].notelabel))
    q = sql_quote
    for r in t["literature"].itertuples():
        out[int(r.sql_seq)] = ("INSERT INTO literature (bibtexkey, quotation, bibliography) VALUES (\n    "
                               + q(r.bibtexkey) + ",\n    " + q(r.quotation) + ",\n    " + q(r.bibliography) + ");")
    for r in t["categories"].itertuples():
        out[int(r.sql_seq)] = "INSERT INTO categories (catname) VALUES (\n    " + q(r.category) + ");"
    for r in t["subcategories"].itertuples():
        out[int(r.sql_seq)] = ("INSERT INTO subcategories (subcatname, cat_id) VALUES (\n    " + q(r.subcategory)
                               + ",\n    (SELECT id from categories WHERE catname=" + q(cat[r.category_id]) + "));")
    for r in t["species"].itertuples():
        out[int(r.sql_seq)] = ("INSERT INTO species (iupac, formula, trivial, casrn, inchikey, subcat_id) VALUES (\n    "
                               + ",\n    ".join(q(x) for x in (r.iupac, r.formula, r.trivial, r.casrn, r.inchikey))
                               + ",\n    (SELECT id from subcategories WHERE subcatname=" + q(sub[r.subcategory_id]) + "));")
    for r in t["notes"].itertuples():
        out[int(r.sql_seq)] = ("INSERT INTO notes (notelabel, noterefs, notetext) VALUES (\n    " + q(r.notelabel)
                               + ",\n    " + q(r.noterefs) + ", " + q(r.notetext_html) + ");")
    for r in t["henry"].itertuples():
        # the literature lookup key is taken from the literature table when resolved,
        # and from the recorded key when the reference does not exist ('this')
        key = bib[r.literature_id] if r.literature_id else r.bibtexkey
        out[int(r.sql_seq)] = ("INSERT INTO henry(Hominus, mindHR, htype, species_id, literature_id) VALUES (\n    "
                               + q(r.hominus_raw) + ",\n    " + q(r.mindhr_raw) + ",\n    " + q(r.htype)
                               + ",\n    (SELECT id from species WHERE iupac=" + q(spn[r.species_id]) + "),"
                               + "\n    (SELECT id from literature WHERE bibtexkey=" + q(key) + "));")
    for r in t["henry_notes"].itertuples():
        out[int(r.sql_seq)] = ("INSERT INTO henry_notes (henry_id, notes_id) VALUES (\n"
                               "    (SELECT CURRVAL('henry_id_seq')),\n"
                               "    (SELECT id from notes WHERE notelabel=" + q(nlab[r.note_id]) + "));")
    return out


def check_link_order(t):
    """Each henry_notes row must follow its henry row with no other henry row in between (CURRVAL)."""
    hseq = sorted((int(s), int(i)) for s, i in zip(t["henry"].sql_seq, t["henry"].henry_id))
    import bisect
    seqs = [s for s, _ in hseq]
    bad = 0
    for s, hid in zip(t["henry_notes"].sql_seq, t["henry_notes"].henry_id):
        k = bisect.bisect_left(seqs, int(s)) - 1
        if k < 0 or hseq[k][1] != int(hid):
            bad += 1
    return bad


def cas_ok(c):
    m = re.match(r"^(\d{2,7})-(\d\d)-(\d)$", c)
    if not m:
        return False
    digits = (m.group(1) + m.group(2))[::-1]
    return sum((i + 1) * int(d) for i, d in enumerate(digits)) % 10 == int(m.group(3))


def parse_f90(text, prefix):
    """Yield blocks: dict(name, casrn, inchikey, rows=[(value, mindhr, type, ref)])."""
    blocks = []
    cur = None
    rx = re.compile(r"^" + prefix + r"_+\w* = +([0-9.]+E[-+]\d+)(?: \* EXP\( *(-?\d+)\.\*\(1\./T-1\./298\.15\)\))? *"
                    r"! \[[^\]]*\] type: (.), ref: (\S+)$")
    for line in text.split("\n"):
        if line.startswith("! species:"):
            cur = dict(name=line[10:].strip(), rows=[])
            blocks.append(cur)
        elif line.startswith("! casrn:"):
            cur["casrn"] = line[8:].strip()
        elif line.startswith("! inchikey:"):
            cur["inchikey"] = line[11:].strip()
        elif line.startswith(prefix):
            m = rx.match(line)
            if not m:
                raise ValueError("unparsed f90 line: " + line)
            cur["rows"].append((m.group(1), m.group(2) or "", m.group(3), m.group(4)))
    return blocks


def sig2(x):
    """Format like the Fortran output: two significant digits, E notation."""
    s = "%.1E" % x
    mant, exp = s.split("E")
    return "%sE%+03d" % (mant, int(exp))


def main():
    zpath, suppl, outdir, repdir = sys.argv[1:5]
    os.makedirs(repdir, exist_ok=True)
    res = collections.OrderedDict()
    issues = []

    def issue(category, severity, table, key, detail, **extra):
        d = dict(category=category, severity=severity, table=table, key=key, detail=detail)
        d.update(extra)
        issues.append(d)

    zb = open(zpath, "rb").read()
    res["zip_sha256_ok"] = sha256(zb) == ZIP_SHA256
    src = zipfile.ZipFile(io.BytesIO(zb)).read(SQL_MEMBER).decode("utf-8")
    meta = json.load(open(os.path.join(outdir, "build_meta.json"), encoding="utf-8"))
    t = {n: read_csv(outdir, n) for n in TABLES}

    # ---- 1. counts ----
    res["counts"] = {n: len(t[n]) for n in TABLES}
    res["counts_expected"] = EXPECTED
    res["counts_ok"] = all(len(t[k]) == v for k, v in EXPECTED.items())

    # ---- 2. byte-for-byte regeneration of every INSERT ----
    regen = regenerate(t)
    spans = []
    for m in re.finditer(r"^INSERT INTO ", src, re.M):
        spans.append(m.start())
    res["insert_statements_in_file"] = len(spans)
    res["statements_regenerated"] = len(regen)
    # statement k ends where the next begins (minus whitespace/comments between)
    mism = []
    pos = spans[0]
    prefix = src[:pos]
    seqs = sorted(regen)
    res["regenerated_seq_contiguous"] = seqs == list(range(1, len(spans) + 1))
    for k in seqs:
        stmt = regen[k]
        if src.startswith(stmt, pos):
            pos += len(stmt)
        else:
            mism.append(k)
            # resynchronise on the next statement start
            nxt = spans[k] if k < len(spans) else len(src)
            pos = nxt
            continue
        # skip the gap to the next statement; it may contain only whitespace and -- comments
        nxt = spans[k] if k < len(spans) else len(src)
        gap = src[pos:nxt]
        if any(l.strip() and not l.strip().startswith("--") for l in gap.split("\n")):
            mism.append(("gap", k))
        pos = nxt
    res["statement_mismatches"] = len(mism)
    res["statement_mismatch_examples"] = [str(x) for x in mism[:10]]
    res["ddl_prefix_has_no_inserts"] = "INSERT" not in prefix
    res["henry_notes_follow_their_henry_row"] = check_link_order(t) == 0

    # ---- 3. value round trip ----
    h = t["henry"]
    nonempty = h[h.hominus_raw != ""]
    st = h.value_status.value_counts().to_dict()
    res["hominus_status_counts"] = st
    fails = int((h.value_status == "parse_failure").sum())
    res["hominus_nonempty"] = len(nonempty)
    res["hominus_parse_failures"] = fails
    res["hominus_parse_failure_rate"] = fails / max(1, len(nonempty))
    mh_nonempty = int((h.mindhr_raw != "").sum())
    mh_fail = int((h.mindhr_status == "parse_failure").sum())
    res["mindhr_nonempty"] = mh_nonempty
    res["mindhr_parse_failures"] = mh_fail
    res["kill_parse_rate_exceeded"] = (fails + mh_fail) / max(1, len(nonempty) + mh_nonempty) > KILL_PARSE_RATE
    fac = Decimal(meta["conversion_factor_si_to_matm"])
    rt_bad = []
    for r in h.itertuples():
        if r.value_status == "ok":
            exp = int(r.hscp_exponent) if r.hscp_exponent != "" else None
            if render_hominus(r.limit_flag, r.hscp_mantissa, exp) != r.hominus_raw:
                rt_bad.append((r.henry_id, "render"))
            d = Decimal(r.hscp_si_exact)
            if float(r.hscp_si) != float(d):
                rt_bad.append((r.henry_id, "si"))
            if float(r.hscp_matm) != float(d * fac):
                rt_bad.append((r.henry_id, "matm"))
            if not (float(r.hscp_si) > 0):
                rt_bad.append((r.henry_id, "nonpositive"))
        elif r.value_status == "infinity":
            if not (r.hominus_raw == "&#8734;" and math.isinf(float(r.hscp_si))):
                rt_bad.append((r.henry_id, "inf"))
        elif r.value_status == "empty":
            if r.hominus_raw != "" or r.hscp_si != "":
                rt_bad.append((r.henry_id, "empty"))
        if r.mindhr_status == "ok" and str(int(r.mindhr_K)) != r.mindhr_raw:
            rt_bad.append((r.henry_id, "mindhr"))
        if r.mindhr_status == "empty" and r.mindhr_K != "":
            rt_bad.append((r.henry_id, "mindhr_empty"))
        if float(r.hscp_matm_factor) != float(fac):
            rt_bad.append((r.henry_id, "factor"))
    res["value_roundtrip_failures"] = len(rt_bad)
    res["value_roundtrip_failure_examples"] = rt_bad[:10]

    # ---- 4. unit checks ----
    res["factor_from_paper"] = str(fac)
    res["factor_equals_101325_over_1000"] = fac == Decimal(101325) / Decimal(1000)
    # supplement cross-check
    sb = open(suppl, "rb").read()
    res["supplement_sha256_ok"] = sha256(sb) == SUPPL_SHA256
    zs = zipfile.ZipFile(io.BytesIO(sb))
    si = parse_f90(zs.read("output/HscpSI.f90").decode("utf-8"), "HscpSI")
    ma = parse_f90(zs.read("output/Hscp.f90").decode("utf-8"), "Hscp")
    sp = t["species"]
    res["f90_species_blocks"] = len(si)
    hh = h.copy()
    hh["sid"] = hh.species_id.astype(int)
    hh["hid"] = hh.henry_id.astype(int)
    exported = hh[(hh.value_status == "ok") & (hh.htype != "W")].sort_values("hid")
    res["rows_expected_in_f90"] = len(exported)
    by_sp = {k: g for k, g in exported.groupby("sid")}
    f_si_bad = []
    f_ma_bad = []
    f_meta_bad = []
    n_f90 = 0
    for k, (b, bm) in enumerate(zip(si, ma), start=1):
        s = sp.iloc[k - 1]
        # the Fortran files write UNKNOWN where the SQL has an empty string
        if b["casrn"].replace("UNKNOWN", "") != s.casrn or b["inchikey"].replace("UNKNOWN", "") != s.inchikey:
            f_meta_bad.append(k)
        g = by_sp.get(k)
        rows = [] if g is None else list(g.itertuples())
        n_f90 += len(b["rows"])
        if len(rows) != len(b["rows"]):
            f_si_bad.append((k, "row count %d vs f90 %d" % (len(rows), len(b["rows"]))))
            continue
        for r, fr, fm in zip(rows, b["rows"], bm["rows"]):
            exp = int(r.hscp_exponent) if r.hscp_exponent != "" else 0
            mine = "%sE%+03d" % (r.hscp_mantissa, exp)
            ok = (Decimal(mine) == Decimal(fr[0]) and fr[1] == r.mindhr_raw and fr[2] == r.htype
                  and fr[3] == r.bibtexkey)
            if not ok:
                f_si_bad.append((int(r.henry_id), "SQL %s %s %s %s vs f90 %s" % (mine, r.mindhr_raw, r.htype, r.bibtexkey, fr)))
            # M/atm: the Fortran file shows the conversion of the unrounded value, rounded to
            # two digits; the SQL value is itself rounded to two digits. The allowed difference
            # is half a unit in the last digit of each.
            mv = float(r.hscp_matm)
            fv = float(fm[0])
            tol = (0.5 * 10 ** (exp - 1) * float(fac) + 0.5 * 10 ** (int(fm[0].split("E")[1]) - 1)) * (1 + 1e-9)
            if abs(mv - fv) > tol:
                f_ma_bad.append((int(r.henry_id), r.hscp_matm, fm[0]))
    res["f90_value_lines"] = n_f90
    res["f90_si_mismatches"] = len(f_si_bad)
    res["f90_si_mismatch_examples"] = f_si_bad[:10]
    res["f90_matm_beyond_rounding"] = len(f_ma_bad)
    res["f90_matm_examples"] = f_ma_bad[:10]
    res["f90_species_identifier_mismatches"] = len(f_meta_bad)
    for x in f_si_bad:
        issue("supplement_f90_disagrees", "check", "henry", str(x[0]), x[1])

    # ---- 5. copies agree ----
    pq_ok = {}
    for n in TABLES:
        p = pd.read_parquet(os.path.join(outdir, "parquet", n + ".parquet"))
        c = t[n]
        same = list(p.columns) == list(c.columns) and len(p) == len(c)
        if same:
            for col in c.columns:
                a = p[col].astype(object).where(p[col].notna(), "")
                a = a.map(lambda v: repr(v) if isinstance(v, float) else str(v))
                b = c[col].map(lambda v: repr(float(v)) if pd.api.types.is_float_dtype(p[col]) and v != "" else v)
                if not (a.values == b.values).all():
                    same = False
                    break
        pq_ok[n] = bool(same)
    res["parquet_equals_csv"] = pq_ok
    con = sqlite3.connect(os.path.join(outdir, "henry_5.0.0.sqlite"))
    res["sqlite_counts"] = {n: con.execute('SELECT COUNT(*) FROM "%s"' % n).fetchone()[0] for n in TABLES}
    res["sqlite_foreign_key_violations"] = len(con.execute("PRAGMA foreign_key_check").fetchall())
    s1 = con.execute("SELECT SUM(hscp_si) FROM henry WHERE value_status='ok'").fetchone()[0]
    res["sqlite_sum_hscp_si_matches"] = math.isclose(s1, h[h.value_status == "ok"].hscp_si.astype(float).sum(), rel_tol=1e-12)
    con.close()

    # ---- 6. internal inconsistencies (for the compiler; nothing is fixed) ----
    for e in meta["events"]:
        r = h[h.sql_seq == str(e["sql_seq"])].iloc[0]
        issue("dangling_reference", "error", "henry", r.henry_id,
              "bibtexkey %r has no literature row; species %r, H=%r, mindHR=%r, type %s" % (
                  r.bibtexkey, r.species_key, r.hominus_raw, r.mindhr_raw, r.htype))
    num = h[h.value_status == "ok"].copy()
    grp = h.groupby(["species_id", "bibtexkey"])
    nconf = 0
    nexact = 0
    for (sid, key), g in grp:
        if len(g) < 2:
            continue
        combos = g[["hominus_raw", "mindhr_raw"]].drop_duplicates()
        full = g[["hominus_raw", "mindhr_raw", "htype", "note_ids"]]
        if len(full.drop_duplicates()) < len(full):
            nexact += 1
            issue("duplicate_identical_rows", "warning", "henry", ";".join(g.henry_id),
                  "species %r, reference %s: %d rows, of which some are identical in value, mindHR, type and notes" % (
                      g.species_key.iloc[0], key, len(g)))
        if len(combos) > 1:
            nconf += 1
            same_notes = g.note_ids.nunique() == 1
            same_type = g.htype.nunique() == 1
            # rows that differ only in value cannot be told apart by type or note
            issue("same_species_reference_different_values", "warning" if (same_notes and same_type) else "info", "henry",
                  ";".join(g.henry_id),
                  "species %r, reference %s: values %s; notes %s" % (
                      g.species_key.iloc[0], key,
                      ", ".join("%s|%s|%s" % (a or "(empty)", b or "-", c) for a, b, c in zip(g.hominus_raw, g.mindhr_raw, g.htype)),
                      "identical for all rows" if same_notes else "differ between rows") +
                  ("; same type" if same_type else "; types differ"))
    res["species_reference_pairs_with_differing_values"] = nconf
    res["species_reference_pairs_differing_only_in_value"] = sum(
        1 for i in issues if i["category"] == "same_species_reference_different_values" and i["severity"] == "warning")
    res["species_reference_pairs_with_identical_rows"] = nexact
    neg = h[h.mindhr_K.str.startswith("-")]
    for r in neg.itertuples():
        issue("negative_mindHR", "info", "henry", r.henry_id,
              "d ln H/d(1/T) = %s K (solubility increases with temperature); species %r, reference %s, type %s, notes %s" % (
                  r.mindhr_raw, r.species_key, r.bibtexkey, r.htype, r.note_ids or "-"))
    res["negative_mindHR"] = len(neg)
    w = h[(h.htype == "W") & (h.hominus_raw != "")]
    for r in w.itertuples():
        issue("type_W_with_value", "info", "henry", r.henry_id,
              "type W ('probably wrong, not listed') but the dump carries H=%s; species %r, reference %s" % (
                  r.hominus_raw, r.species_key, r.bibtexkey))
    res["type_W_rows"] = int((h.htype == "W").sum())
    res["type_W_rows_with_value"] = len(w)
    x = h[(h.hominus_raw == "") & (h.mindhr_raw != "")]
    for r in x.itertuples():
        issue("mindHR_without_H", "info", "henry", r.henry_id,
              "mindHR %s but no H value; species %r, reference %s, type %s" % (r.mindhr_raw, r.species_key, r.bibtexkey, r.htype))
    res["mindHR_without_H"] = len(x)
    x = h[(h.limit_flag != "") & (h.mindhr_raw != "")]
    for r in x.itertuples():
        issue("limit_with_mindHR", "info", "henry", r.henry_id,
              "limit value %s with temperature dependence %s; species %r, reference %s" % (
                  r.hominus_raw, r.mindhr_raw, r.species_key, r.bibtexkey))
    res["limit_with_mindHR"] = len(x)
    res["empty_H_rows"] = int((h.hominus_raw == "").sum())
    blank = h[(h.hominus_raw == "") & (h.mindhr_raw == "") & (h.note_ids == "")]
    res["rows_without_H_mindHR_or_note"] = len(blank)
    for r in blank.itertuples():
        issue("row_without_any_data", "warning", "henry", r.henry_id,
              "no H value, no temperature dependence and no note; species %r, reference %s, type %s" % (
                  r.species_key, r.bibtexkey, r.htype))
    # species-level spread
    num["lg"] = num.hscp_si.astype(float).map(math.log10)
    plain = num[(num.limit_flag == "") & (num.htype != "W")]
    med = plain.groupby("species_id").lg.agg(["median", "count"])
    plain = plain.join(med, on="species_id")
    out3 = plain[(plain["count"] >= 3) & ((plain.lg - plain["median"]).abs() > 3)]
    for r in out3.itertuples():
        issue("value_far_from_species_median", "check", "henry", r.henry_id,
              "H=%s differs from the median of the %d values for %r by a factor of %.0f; reference %s, type %s" % (
                  r.hscp_si_exact, r.count, r.species_key, 10 ** abs(r.lg - r.median), r.bibtexkey, r.htype))
    res["values_more_than_1000x_from_species_median"] = len(out3)
    # species
    sp = t["species"]
    for col in ["casrn", "inchikey"]:
        d = sp[(sp[col] != "") & sp.duplicated(col, keep=False)]
        for v, g in d.groupby(col):
            issue("duplicate_" + col, "warning", "species", ";".join(g.species_id),
                  "%s %s shared by: %s" % (col, v, "; ".join(g.iupac_text)))
        res["species_sharing_" + col] = int(d[col].nunique())
    bad_cas = sp[(sp.casrn != "") & ~sp.casrn.map(cas_ok)]
    for r in bad_cas.itertuples():
        issue("casrn_check_digit", "error", "species", r.species_id, "CAS RN %r fails the check-digit test (%s)" % (r.casrn, r.iupac_text))
    res["casrn_invalid"] = len(bad_cas)
    bad_ik = sp[(sp.inchikey != "") & ~sp.inchikey.str.match(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")]
    for r in bad_ik.itertuples():
        issue("inchikey_format", "error", "species", r.species_id, "InChIKey %r is malformed (%s)" % (r.inchikey, r.iupac_text))
    res["inchikey_malformed"] = len(bad_ik)
    res["species_without_casrn"] = int((sp.casrn == "").sum())
    res["species_without_inchikey"] = int((sp.inchikey == "").sum())
    res["species_without_henry_rows"] = int((sp.n_henry_rows == "0").sum())
    for r in sp[sp.n_henry_rows == "0"].itertuples():
        issue("species_without_data", "info", "species", r.species_id, "no henry rows for %r" % r.iupac_text)
    res["species_iupac_duplicates"] = int(sp.iupac.duplicated().sum())
    # literature
    lit = t["literature"]
    res["literature_unused"] = int((lit.n_henry_rows == "0").sum())
    nr = t["note_references"]
    used_in_notes = set(nr.bibtexkey)
    unused = lit[(lit.n_henry_rows == "0") & ~lit.bibtexkey.isin(used_in_notes)]
    res["literature_unused_anywhere"] = len(unused)
    for r in unused.itertuples():
        issue("reference_unused", "info", "literature", r.literature_id,
              "reference %s (%s) is cited by no henry row and no note" % (r.bibtexkey, r.quotation_text))
    res["literature_with_doi"] = int((lit.doi != "").sum())
    d = lit[(lit.doi != "") & lit.doi.str.upper().duplicated(keep=False)]
    for v, g in d.groupby(d.doi.str.upper()):
        issue("duplicate_doi", "warning", "literature", ";".join(g.literature_id),
              "DOI %s used by references %s" % (v, ", ".join(g.bibtexkey + " (" + g.quotation_text + ")")))
    res["dois_shared_by_several_references"] = int(d.doi.str.upper().nunique())
    q = lit[lit.quotation.duplicated(keep=False)]
    for v, g in q.groupby("quotation"):
        issue("duplicate_quotation", "warning", "literature", ";".join(g.literature_id),
              "citation label %r used by references %s" % (g.quotation_text.iloc[0], ", ".join(g.bibtexkey)))
    res["citation_labels_shared"] = int(q.quotation.nunique())
    # notes
    nt = t["notes"]
    res["notes_unused"] = int((nt.n_henry_rows == "0").sum())
    for r in nt[nt.n_henry_rows == "0"].itertuples():
        issue("note_unused", "info", "notes", r.note_id, "note %r is linked to no henry row" % r.notelabel)
    miss = nr[nr.literature_id == ""]
    for r in miss.itertuples():
        issue("note_reference_missing", "error", "notes", r.note_id,
              "note %s cites bibtexkey %r, which is not in the literature table" % (
                  nt.set_index("note_id").notelabel[r.note_id], r.bibtexkey))
    res["note_reference_keys_missing"] = len(miss)

    res["issues_by_category"] = collections.Counter(i["category"] for i in issues)
    pd.DataFrame(issues).to_csv(os.path.join(repdir, "inconsistencies.csv"), index=False, lineterminator="\n")
    json.dump(res, open(os.path.join(repdir, "verification.json"), "w"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
