"""Files for the compiler, made from a built edition.

Usage: python3 -I compiler_files.py <outdir> <reportdir>

Writes to <reportdir>/for_the_compiler/:
  doi_updates.sql              PostgreSQL UPDATE statements that fill the empty doi
                               column of the literature table from the doi.org link
                               written in each bibliography (one statement per
                               reference that has a link).
  species_without_inchikey.csv species with an empty inchikey.

Nothing here changes the tables; the SQL file is for the compiler to review and
run on his own database if he wants to.
"""
import csv
import json
import os
import sys

import pandas as pd


def q(s):
    return "'" + str(s).replace("'", "''") + "'"


def main():
    outdir, repdir = sys.argv[1:3]
    dest = os.path.join(repdir, "for_the_compiler")
    os.makedirs(dest, exist_ok=True)
    meta = json.load(open(os.path.join(outdir, "build_meta.json"), encoding="utf-8"))
    version = meta.get("version", "5.0.0")
    lit = pd.read_csv(os.path.join(outdir, "csv", "literature.csv"), dtype=str, keep_default_na=False)
    sp = pd.read_csv(os.path.join(outdir, "csv", "species.csv"), dtype=str, keep_default_na=False)

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
        f.write("-- Each DOI is the link target as written, with HTML entities decoded.\n")
        f.write("-- Review before running. Wrapped in one transaction.\n")
        f.write("BEGIN;\n")
        for r in have.itertuples():
            f.write("UPDATE literature SET doi = %s WHERE bibtexkey = %s AND (doi IS NULL OR doi = '');\n"
                    % (q(r.doi), q(r.bibtexkey)))
        f.write("COMMIT;\n")

    miss = sp[sp.inchikey == ""]
    with open(os.path.join(dest, "species_without_inchikey.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["species_id", "iupac", "trivial", "formula", "casrn"])
        for r in miss.itertuples():
            w.writerow([r.species_id, r.iupac_text, r.trivial_text, r.formula_text, r.casrn])
    print("doi updates: %d; species without InChIKey: %d" % (len(have), len(miss)))


if __name__ == "__main__":
    main()
