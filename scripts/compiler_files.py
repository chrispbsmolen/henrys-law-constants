"""Files for the compiler, made from a built edition.

Usage: python3 -I compiler_files.py <outdir> <reportdir> [<erratadir>]

Writes to <reportdir>/for_the_compiler/:
  doi_updates.sql              PostgreSQL UPDATE statements that fill the empty doi
                               column of the literature table from the doi.org link
                               written in each bibliography (one statement per
                               reference that has a link).
  species_without_inchikey.csv species with an empty inchikey.
  live_site_differences.csv    (with <erratadir>) the differences between the live
                               references and notes pages and the SQL file that the
                               errata page does not mention, other than digit-only
                               changes in notes, with what changed in each.

Where the live references page gives a different DOI for a reference than the
SQL file (for example a Discussion paper later published), the live DOI is used
and the SQL file's DOI is named in a comment above the statement.

Nothing here changes the tables; the SQL file is for the compiler to review and
run on his own database if he wants to.
"""
import csv
import difflib
import html
import json
import os
import re
import sys

import pandas as pd


RE_DOI_HREF = re.compile(r'href="https?://(?:dx\.)?doi\.org/([^"]+)"')


def visible(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", "", s))).strip()


def what_changed(a, b):
    a, b = visible(a), visible(b)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    parts = ['"%s" -> "%s"' % (a[i1:i2], b[j1:j2]) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal"]
    return "; ".join(parts) or "same visible text, different markup"


def q(s):
    return "'" + str(s).replace("'", "''") + "'"


def main():
    outdir, repdir = sys.argv[1:3]
    erratadir = sys.argv[3] if len(sys.argv) > 3 else None
    dest = os.path.join(repdir, "for_the_compiler")
    os.makedirs(dest, exist_ok=True)
    meta = json.load(open(os.path.join(outdir, "build_meta.json"), encoding="utf-8"))
    version = meta.get("version", "5.0.0")
    lit = pd.read_csv(os.path.join(outdir, "csv", "literature.csv"), dtype=str, keep_default_na=False)
    sp = pd.read_csv(os.path.join(outdir, "csv", "species.csv"), dtype=str, keep_default_na=False)

    # DOIs that the live references page gives differently (one DOI link on each side)
    live_doi = {}
    if erratadir:
        diffs = pd.read_csv(os.path.join(erratadir, "live_differences_not_in_errata.csv"), dtype=str, keep_default_na=False)
        for r in diffs[(diffs.table == "literature") & (diffs.column == "bibliography")].itertuples():
            a = [html.unescape(x) for x in RE_DOI_HREF.findall(r.base_value)]
            b = [html.unescape(x) for x in RE_DOI_HREF.findall(r.live_value)]
            if len(a) == 1 and len(b) == 1 and a[0].lower() != b[0].lower():
                live_doi[r.context] = (b[0], r.evidence_url, r.evidence_fetched_utc[:10])
    have = lit[lit.doi != ""].copy()
    have["sort"] = have.literature_id.astype(int)
    have = have.sort_values("sort")
    keys = have.bibtexkey
    if keys.duplicated().any():
        sys.exit("bibtexkey not unique; cannot key the updates on it")
    with open(os.path.join(dest, "doi_updates.sql"), "w", encoding="utf-8", newline="\n") as f:
        f.write("-- Fill literature.doi from the doi.org link in each bibliography.\n")
        f.write("-- Source: %s (%s), %d of %d references have a link.\n"
                % (meta.get("sql_member", ""), version, len(have), len(lit)))
        f.write("-- Each DOI is the link target as written, with HTML entities decoded, except where a\n")
        f.write("-- comment says the live references page gives a newer one.\n")
        f.write("-- Review before running. Wrapped in one transaction.\n")
        f.write("BEGIN;\n")
        for r in have.itertuples():
            doi = r.doi
            if r.bibtexkey in live_doi:
                doi, url, day = live_doi[r.bibtexkey]
                f.write("-- %s: the SQL file has %s; the live references page (%s, read %s) has %s, used here.\n"
                        % (r.bibtexkey, r.doi, url, day, doi))
            f.write("UPDATE literature SET doi = %s WHERE bibtexkey = %s AND (doi IS NULL OR doi = '');\n"
                    % (q(doi), q(r.bibtexkey)))
        f.write("COMMIT;\n")

    miss = sp[sp.inchikey == ""]
    with open(os.path.join(dest, "species_without_inchikey.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["species_id", "iupac", "trivial", "formula", "casrn"])
        for r in miss.itertuples():
            w.writerow([r.species_id, r.iupac_text, r.trivial_text, r.formula_text, r.casrn])
    if erratadir:
        diffs = pd.read_csv(os.path.join(erratadir, "live_differences_not_in_errata.csv"), dtype=str, keep_default_na=False)
        keep = diffs[~((diffs.table == "notes") & diffs.difference_kind.str.startswith("digits"))]
        with open(os.path.join(dest, "live_site_differences.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["table", "key", "field", "kind", "what_changed", "value_in_sql_file", "value_on_live_site", "live_page"])
            for r in keep.itertuples():
                key = r.context.split("'")[1] if r.table == "notes" else r.context
                w.writerow([r.table, key, r.column, r.difference_kind, what_changed(r.base_value, r.live_value),
                            r.base_value, r.live_value, r.evidence_url])
        print("live-site differences listed: %d (of %d; digit-only note changes left out)" % (len(keep), len(diffs)))
    print("doi updates: %d (%d from the live site); species without InChIKey: %d" % (len(have), len(live_doi), len(miss)))


if __name__ == "__main__":
    main()
