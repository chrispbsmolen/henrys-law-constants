"""Errata patch layer for the v5.0.0 tables.

Usage: python3 -I errata.py <outdir> <livedir> <errata_dir>

Reads the saved live errata page, the live species pages it concerns and
the live notes and references pages
(fetched by fetch_live.py, listed with hashes in <livedir>/fetch_log.csv),
compares each live page with the base tables, and writes:

  errata_entries.csv   every entry on the errata page, with its section
  patches.csv          one row per changed field, citing the errata entry,
                       the errata URL and the live page used as evidence
  live_differences_not_in_errata.csv
                       differences between the live site and v5.0.0 that no
                       errata entry covers (reported, not patched); found on
                       the species pages read for the errata and on the live
                       notes and references pages (whole-site lists)
  errata_checks.csv    machine checks of the older entries (stated on the
                       page as already corrected) against the v5.0.0 tables
  patched/             copies of the affected tables with the patches applied

The base tables are never modified.
"""
import csv
import json
import os
import re
import sqlite3
import sys
from decimal import Decimal

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from htmltext import to_text  # noqa: E402
from livepage import parse_species_page  # noqa: E402
from build import parse_hominus  # noqa: E402

ERRATA_URL = "https://www.henrys-law.org/henry/errata.html"
LAYER_VERSION = "1"


def read_csv(d, name):
    return pd.read_csv(os.path.join(d, "csv", name + ".csv"), dtype=str, keep_default_na=False, encoding="utf-8")


def parse_errata(html):
    entries = []
    for m in re.finditer(r"<h3>(Errata for version ([^ <]+)[^<]*)</h3>\s*<ul>(.*?)</ul>", html, re.S | re.I):
        heading, version, body = m.group(1), m.group(2), m.group(3)
        items = re.split(r"<li>", body, flags=re.I)[1:]
        for k, it in enumerate(items, start=1):
            it = re.sub(r"</li>\s*$", "", it.strip(), flags=re.I).strip()
            entries.append(dict(entry_id="%s-%d" % (version, k), version=version, section=heading.strip(),
                                applies_to_v5_0_0=version == "5.0.0",
                                text_html=it, text=to_text(it)))
    return entries


def norm_note(s):
    """Normalise a note for comparison: plain text, '&' and 'and' treated alike."""
    return re.sub(r"\s+", " ", to_text(s).replace(" & ", " and ")).strip()


def main():
    outdir, livedir, edir = sys.argv[1:4]
    os.makedirs(os.path.join(edir, "patched", "csv"), exist_ok=True)
    os.makedirs(os.path.join(edir, "patched", "parquet"), exist_ok=True)
    log = {r["file"]: r for r in csv.DictReader(open(os.path.join(livedir, "fetch_log.csv")))}
    sp = read_csv(outdir, "species")
    h = read_csv(outdir, "henry")
    nt = read_csv(outdir, "notes")
    hn = read_csv(outdir, "henry_notes")
    lit = read_csv(outdir, "literature")
    note_html = dict(zip(nt.note_id, nt.notetext_html))

    entries = parse_errata(open(os.path.join(livedir, "errata.html"), encoding="utf-8").read())
    v5 = [e for e in entries if e["applies_to_v5_0_0"]]

    # species named in each v5.0.0 entry (whole-name match against the base names)
    names = sorted(set(sp.iupac_text), key=len, reverse=True)
    for e in v5:
        found = []
        for n in names:
            if len(n) > 3 and re.search(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", e["text"]):
                if not any(n in f for f in found):
                    found.append(n)
        e["species"] = found

    patches = []
    pages_read = []
    unlisted = []   # live differences that no errata entry covers: reported, not patched

    def add(entry, table, row_id, column, op, base, new, evidence, note=""):
        ev = log[evidence]
        patches.append(dict(patch_id="P%03d" % (len(patches) + 1), layer_version=LAYER_VERSION, op=op,
                            table=table, row_id=row_id, column=column, base_value=base, patched_value=new,
                            errata_entry_id=entry["entry_id"], errata_url=ERRATA_URL,
                            errata_text=entry["text"], evidence_url=ev["url"], evidence_file=evidence,
                            evidence_sha256=ev["sha256"], evidence_fetched_utc=ev["fetched_utc"], remark=note))

    def other(table, row_id, column, base, new, evidence, context=""):
        ev = log[evidence]
        unlisted.append(dict(table=table, row_id=row_id, column=column, base_value=base, live_value=new,
                             evidence_url=ev["url"], evidence_sha256=ev["sha256"],
                             evidence_fetched_utc=ev["fetched_utc"], context=context))

    # live notes page: note number -> (label, html)
    live_notes = {}
    lt = open(os.path.join(livedir, "notes.html"), encoding="utf-8").read()
    for num, label, body in re.findall(r'<TD align="right">(\d+)\)</TD>\s*<!-- <TD>(.*?)</TD> -->\s*<TD>(.*?)</TD>\s*</TR>',
                                       lt, re.S):
        live_notes[int(num)] = (label, body.strip())
    label2id = dict(zip(nt.notelabel, nt.note_id))
    base_labels_all = set(nt.notelabel)
    id2label = dict(zip(nt.note_id, nt.notelabel))
    colword = {"inchikey": "InChIKey", "casrn": "CASRN", "formula": "formula", "iupac": "name"}

    next_note = max(int(x) for x in nt.note_id) + 1
    for e in v5:
        cited = set(lit[lit.quotation_text.map(lambda q: q in e["text"])].bibtexkey)
        for name in e["species"]:
            s = sp[sp.iupac_text == name].iloc[0]
            fn = "casrn_%s.html" % s.casrn
            ctx = "%s (species %s), page read for errata entry %s" % (name, s.species_id, e["entry_id"])
            if fn not in log:
                unlisted.append(dict(table="species", row_id=s.species_id, column="", base_value="", live_value="",
                                     evidence_url="", evidence_sha256="", evidence_fetched_utc="",
                                     context="live page not fetched: " + ctx))
                continue
            pages_read.append(fn)
            p = parse_species_page(open(os.path.join(livedir, fn), encoding="utf-8").read())
            for col, live in (("inchikey", p["inchikey"]), ("casrn", p["casrn"]), ("formula", p["formula_html"]),
                              ("iupac", p["name_html"])):
                if live != s[col]:
                    if colword[col] in e["text"]:
                        add(e, "species", s.species_id, col, "update", s[col], live, fn)
                    else:
                        other("species", s.species_id, col, s[col], live, fn, ctx)
            base = h[h.species_id == s.species_id]
            q2k = {q: v["bibtexkey"] for q, v in p["refs"].items()}
            live_by = {}
            for r in p["rows"]:
                live_by.setdefault(q2k.get(r["quotation"].replace("&amp;", "&")), []).append(r)
            keys = set(base.bibtexkey) | set(live_by)
            for key in keys:
                g = base[base.bibtexkey == key]
                lv = live_by.get(key, [])
                in_scope = key in cited
                if len(lv) != len(g):
                    other("henry", ";".join(g.henry_id), "*", "%d rows" % len(g), "%d rows" % len(lv), fn,
                          ctx + "; reference %s" % key)
                    continue
                for br, lr in zip(g.itertuples(), lv):
                    for col, live in (("hominus_raw", lr["hominus"]), ("mindhr_raw", lr["mindhr"]), ("htype", lr["htype"])):
                        if live != getattr(br, col):
                            if in_scope:
                                add(e, "henry", br.henry_id, col, "update", getattr(br, col), live, fn)
                            else:
                                other("henry", br.henry_id, col, getattr(br, col), live, fn, ctx)
                    base_labels = [id2label[i] for i in br.note_ids.split(";") if i]
                    live_labels = []
                    for n in lr["note_numbers"]:
                        label, body = live_notes[n]
                        if body != p["notes"][n]:
                            raise SystemExit("note %d differs between species page and notes page" % n)
                        live_labels.append(label)
                        if label in base_labels_all:
                            base_txt = note_html[label2id[label]]
                            if norm_note(base_txt) != norm_note(body):
                                other("notes", label2id[label], "notetext_html", base_txt, body, "notes.html",
                                      "note %r (live note %d), linked from henry %s" % (label, n, br.henry_id))
                        elif label not in label2id:
                            nid = str(next_note)
                            next_note += 1
                            label2id[label] = nid
                            payload = json.dumps(dict(note_id=int(nid), notelabel=label, noterefs="",
                                                      notetext_html=body), ensure_ascii=False)
                            if in_scope:
                                add(e, "notes", nid, "*", "insert", "", payload, "notes.html",
                                    "new note; live note number %d; noterefs not published on the site" % n)
                            else:
                                other("notes", nid, "*", "", payload, "notes.html", ctx)
                    for label in live_labels:
                        if label not in base_labels:
                            payload = json.dumps(dict(henry_id=int(br.henry_id), note_id=int(label2id[label])))
                            if in_scope:
                                add(e, "henry_notes", "%s;%s" % (br.henry_id, label2id[label]), "*", "insert", "", payload, fn)
                            else:
                                other("henry_notes", br.henry_id, "*", "", payload, fn, ctx)
                    for label in base_labels:
                        if label not in live_labels:
                            other("henry_notes", br.henry_id, "*", label, "", fn, ctx + "; link removed on live page")

    # whole-site audit of notes and references (one page each)
    live_lab = {lab: (n, body) for n, (lab, body) in live_notes.items()}
    for r in nt.itertuples():
        if r.notelabel not in live_lab:
            other("notes", r.note_id, "*", r.notelabel, "", "notes.html", "note label not on live notes page")
        elif norm_note(r.notetext_html) != norm_note(live_lab[r.notelabel][1]) and not any(
                u["table"] == "notes" and u["row_id"] == r.note_id for u in unlisted):
            other("notes", r.note_id, "notetext_html", r.notetext_html, live_lab[r.notelabel][1], "notes.html",
                  "note %r (live note %d)" % (r.notelabel, live_lab[r.notelabel][0]))
    for lab, (n, body) in live_lab.items():
        if lab not in set(nt.notelabel) and not any(x["table"] == "notes" and lab in x["patched_value"] for x in patches):
            other("notes", "", "*", "", json.dumps(dict(notelabel=lab, notetext_html=body), ensure_ascii=False),
                  "notes.html", "note on live site, not in v5.0.0 (live note %d)" % n)
    rt = open(os.path.join(livedir, "references.html"), encoding="utf-8").read()
    live_refs = {k: (q.strip(), b.strip()) for k, q, b in re.findall(
        r"<!-- <TD>(.*?)</TD> -->\s*<TD>(.*?)</TD>\s*<TD>(.*?)</TD>\s*</TR>", rt, re.S)}
    for r in lit.itertuples():
        if r.bibtexkey not in live_refs:
            other("literature", r.literature_id, "*", r.bibtexkey, "", "references.html",
                  "reference not on live references page (cited by %s henry rows)" % r.n_henry_rows)
            continue
        q, b = live_refs[r.bibtexkey]
        if norm_note(q) != norm_note(r.quotation):
            other("literature", r.literature_id, "quotation", r.quotation, q, "references.html", r.bibtexkey)
        if norm_note(b) != norm_note(r.bibliography):
            other("literature", r.literature_id, "bibliography", r.bibliography, b, "references.html", r.bibtexkey)
    for k, (q, b) in live_refs.items():
        if k not in set(lit.bibtexkey):
            other("literature", "", "*", "", json.dumps(dict(bibtexkey=k, quotation=q, bibliography=b), ensure_ascii=False),
                  "references.html", "reference on live site, not in v5.0.0")
    live_counts = dict(live_notes=len(live_notes), live_references=len(live_refs))

    # cross-check the InChIKey entries against their own wording
    for e in v5:
        e["consistency"] = ""
        for name, new, old in re.findall(r"InChIKey of (.+?) is\s+([A-Z]{14}-[A-Z]{10}-[A-Z]), not\s+([A-Z]{14}-[A-Z]{10}-[A-Z])", e["text"]):
            pr = [x for x in patches if x["errata_entry_id"] == e["entry_id"] and x["column"] == "inchikey"
                  and sp.set_index("species_id").iupac_text[x["row_id"]] == name]
            ok = len(pr) == 1 and pr[0]["base_value"] == old and pr[0]["patched_value"] == new
            e["consistency"] += "%s: base has the old key and live page the new key: %s. " % (name, "yes" if ok else "NO")
        e["n_patches"] = sum(1 for x in patches if x["errata_entry_id"] == e["entry_id"])

    # ---- older entries: machine checks where the entry names a checkable fact ----
    checks = []
    spn = sp.set_index("species_id")
    for e in entries:
        if e["applies_to_v5_0_0"]:
            continue
        txt = e["text"]
        for name, cas in re.findall(r"CASRN for (.+?) is \[?(\d+-\d\d-\d)\]?", txt):
            name = re.sub(r"\s*\(.*?\)\s*$", "", name).strip()
            hit = sp[sp.iupac_text == name]
            ok = len(hit) == 1 and hit.casrn.iloc[0] == cas
            checks.append(dict(entry_id=e["entry_id"], check="species %r has CAS RN %s" % (name, cas),
                               result="pass" if ok else ("species not found" if not len(hit) else "FAIL: %s" % hit.casrn.iloc[0])))
        m = re.search(r"from (\w+ et al\. \(\d{4}\)).*?\(N2O5\) = ([0-9.]+E-?\d+) mol/\(m\^?3\*Pa\).*?= (\d+) K", txt)
        if m:
            quot, val, dep = m.groups()
            rows = h[(h.species_key == "dinitrogen pentoxide") &
                     h.bibtexkey.isin(lit[lit.quotation_text == quot].bibtexkey)]
            ok = len(rows) > 0 and all(Decimal(r.hscp_si_exact) == Decimal(val) and r.mindhr_raw == dep
                                       for r in rows.itertuples())
            checks.append(dict(entry_id=e["entry_id"],
                               check="dinitrogen pentoxide, %s: H = %s mol/(m3 Pa), mindHR = %s K" % (quot, val, dep),
                               result="pass" if ok else "FAIL: %s" % rows[["hominus_raw", "mindhr_raw"]].values.tolist()))
        m = re.search(r"corrected value of .*?\(HOBr\) > ([0-9.]+E\d+) M/atm", txt)
        if m:
            want = Decimal(m.group(1))
            rows = h[(h.species_key == "hypobromous acid") & (h.limit_flag == ">")]
            got = sorted({Decimal(r.hscp_si_exact) * Decimal(r.hscp_matm_factor) for r in rows.itertuples()})
            ok = any(abs(g - want) <= Decimal("0.05") * want for g in got)
            checks.append(dict(entry_id=e["entry_id"],
                               check="hypobromous acid has a lower limit of about %s M/atm (two-digit rounding); "
                                     "v5.0.0 lower limits in M/atm: %s" % (m.group(1), ", ".join(str(g) for g in got)),
                               result="pass" if ok else "FAIL"))
    for e in entries:
        if not any(c["entry_id"] == e["entry_id"] for c in checks) and not e["applies_to_v5_0_0"]:
            checks.append(dict(entry_id=e["entry_id"], check="(no machine-checkable statement)", result="not checked"))

    # ---- write the layer ----
    ent = pd.DataFrame([{k: e.get(k, "") for k in ("entry_id", "version", "section", "applies_to_v5_0_0", "text",
                                                    "text_html", "species", "n_patches", "consistency")}
                        for e in entries])
    ent["species"] = ent["species"].map(lambda x: "; ".join(x) if isinstance(x, list) else "")
    ent["n_patches"] = ent["n_patches"].map(lambda x: "" if x == "" else str(x))
    ent.insert(1, "errata_url", ERRATA_URL)
    ent.insert(2, "errata_page_sha256", log["errata.html"]["sha256"])
    ent.insert(3, "errata_fetched_utc", log["errata.html"]["fetched_utc"])
    pat = pd.DataFrame(patches)
    chk = pd.DataFrame(checks)
    ent.to_csv(os.path.join(edir, "errata_entries.csv"), index=False, lineterminator="\n")
    pat.to_csv(os.path.join(edir, "patches.csv"), index=False, lineterminator="\n")
    chk.to_csv(os.path.join(edir, "errata_checks.csv"), index=False, lineterminator="\n")
    pat.to_parquet(os.path.join(edir, "patches.parquet"), index=False)
    for u in unlisted:
        a, b = norm_note(u["base_value"]), norm_note(u["live_value"])
        nums_a, nums_b = re.findall(r"\d+", a or ""), re.findall(r"\d+", b or "")
        changed = [(x, y) for x, y in zip(nums_a, nums_b) if x != y]
        if not a or not b:
            u["difference_kind"] = "added or removed"
        elif u["base_value"].count("href=") > u["live_value"].count("href="):
            # a link present in the SQL file has lost its target on the live page
            u["difference_kind"] = "link broken on live site"
        elif re.sub(r"\d", "#", a) == re.sub(r"\d", "#", b) and changed and all(
                re.fullmatch(r"(19|20)\d\d", x) and re.fullmatch(r"(19|20)\d\d", y) for x, y in changed):
            u["difference_kind"] = "year only"
        elif re.sub(r"\d", "#", a) == re.sub(r"\d", "#", b):
            u["difference_kind"] = "digits only (e.g. refitted coefficients)"
        elif a.lower() == b.lower():
            u["difference_kind"] = "letter case only"
        else:
            u["difference_kind"] = "text"
    pd.DataFrame(unlisted, columns=["table", "difference_kind", "row_id", "column", "base_value", "live_value", "evidence_url",
                                    "evidence_sha256", "evidence_fetched_utc", "context"]).to_csv(
        os.path.join(edir, "live_differences_not_in_errata.csv"), index=False, lineterminator="\n")
    ent.to_parquet(os.path.join(edir, "errata_entries.parquet"), index=False)

    # ---- apply to copies ----
    sp2, h2, nt2, hn2 = sp.copy(), h.copy(), nt.copy(), hn.copy()
    for x in patches:
        if x["op"] == "update" and x["table"] == "species":
            sp2.loc[sp2.species_id == x["row_id"], x["column"]] = x["patched_value"]
        elif x["op"] == "update" and x["table"] == "henry":
            h2.loc[h2.henry_id == x["row_id"], x["column"]] = x["patched_value"]
        elif x["op"] == "insert" and x["table"] == "notes":
            d = json.loads(x["patched_value"])
            nt2 = pd.concat([nt2, pd.DataFrame([dict(note_id=str(d["note_id"]), notelabel=d["notelabel"], noterefs="",
                                                     notetext_html=d["notetext_html"],
                                                     notetext_text=to_text(d["notetext_html"]),
                                                     sql_seq="", n_henry_rows="0")])], ignore_index=True)
        elif x["op"] == "insert" and x["table"] == "henry_notes":
            d = json.loads(x["patched_value"])
            lab = nt2.set_index("note_id").notelabel.get(str(d["note_id"]), "")
            hn2 = pd.concat([hn2, pd.DataFrame([dict(henry_id=str(d["henry_id"]), note_id=str(d["note_id"]),
                                                     notelabel=lab, sql_seq="")])], ignore_index=True)
    # recompute the derived columns of patched henry rows
    fac = Decimal(h2.hscp_matm_factor.iloc[0])
    touched = {x["row_id"] for x in patches if x["table"] == "henry"} | \
              {json.loads(x["patched_value"])["henry_id"] for x in patches if x["table"] == "henry_notes"}
    touched = {str(t) for t in touched}
    for i in h2.index[h2.henry_id.isin(touched)]:
        r = h2.loc[i]
        pv = parse_hominus(r.hominus_raw)
        h2.loc[i, ["value_status", "limit_flag", "hscp_mantissa", "hscp_exponent", "hscp_si_exact", "hscp_si",
                   "hscp_matm"]] = [pv["status"], pv["limit"], pv["mantissa"] or "",
                                    "" if pv["exponent"] is None else str(pv["exponent"]), pv["exact"],
                                    "" if pv["value"] is None else repr(float(pv["value"])),
                                    "" if pv["value"] is None else repr(float(pv["value"] * fac))]
        mh = r.mindhr_raw
        h2.loc[i, ["mindhr_status", "mindhr_K"]] = ["empty" if mh == "" else "ok", mh]
        ids = list(hn2[hn2.henry_id == r.henry_id].note_id)
        h2.loc[i, ["note_ids", "n_notes"]] = [";".join(ids), str(len(ids))]
    nt2["n_henry_rows"] = nt2.note_id.map(hn2.note_id.value_counts()).fillna(0).astype(int).astype(str)
    h2["patched"] = h2.henry_id.isin(touched)
    sp2["patched"] = sp2.species_id.isin({x["row_id"] for x in patches if x["table"] == "species"})
    for name, df in (("species", sp2), ("henry", h2), ("notes", nt2), ("henry_notes", hn2)):
        df.to_csv(os.path.join(edir, "patched", "csv", name + ".csv"), index=False, lineterminator="\n")
        typed = df.copy()
        for c in typed.columns:
            if c in ("hscp_si", "hscp_matm", "hscp_matm_factor"):
                typed[c] = pd.to_numeric(typed[c].replace("", None), errors="raise").astype("float64")
            elif c.endswith("_id") or c in ("hscp_exponent", "mindhr_K", "n_notes", "sql_seq", "n_henry_rows"):
                typed[c] = pd.to_numeric(typed[c].replace("", None)).astype("Int64")
        typed.to_parquet(os.path.join(edir, "patched", "parquet", name + ".parquet"), index=False)

    # patch tables also go into the SQLite file, next to (not into) the base tables
    con = sqlite3.connect(os.path.join(outdir, "henry_5.0.0.sqlite"))
    for name, df in (("errata_entries", ent), ("errata_patches", pat)):
        con.execute('DROP TABLE IF EXISTS "%s"' % name)
        df.astype(str).to_sql(name, con, index=False)
    con.commit()
    con.close()

    summary = dict(layer_version=LAYER_VERSION, errata_entries_total=len(entries),
                   errata_entries_by_version={v: sum(1 for e in entries if e["version"] == v)
                                              for v in dict.fromkeys(e["version"] for e in entries)},
                   v5_entries=len(v5), patches=len(patches), live_species_pages_read=sorted(set(pages_read)),
                   page_reads_used=len(log),
                   page_reads_needed_for_errata=1 + len(set(pages_read)) + 1,
                   kill_criterion_10000_reads_exceeded=len(log) > 10000,
                   full_live_audit_would_need_species_pages=len(sp),
                   live_pages_counts=live_counts,
                   live_differences_not_in_errata=len(unlisted),
                   live_differences_not_in_errata_by_kind={"%s / %s" % k: v for k, v in
                                                           pd.Series([(u["table"], u["difference_kind"]) for u in unlisted]).value_counts().items()},
                   older_entry_checks={k: int(v) for k, v in chk.result.str.split(":").str[0].value_counts().items()})
    json.dump(summary, open(os.path.join(edir, "errata_summary.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    print(pat[["patch_id", "op", "table", "row_id", "column", "base_value", "patched_value", "errata_entry_id"]].to_string())
    print(chk.to_string())


if __name__ == "__main__":
    main()
