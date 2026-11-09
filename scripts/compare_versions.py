"""Compare two built editions (for example 5.0.0 and a new release).

Usage: python3 -I compare_versions.py <old outdir> <new outdir> <reportdir>

Writes <reportdir>/changes_<old>_to_<new>.csv with one row per difference and
prints a summary. Rows are matched by content, not by id, because ids are
assigned in file order and shift when anything is inserted:
  species     by IUPAC name (fields compared: formula, trivial, casrn, inchikey, subcategory)
  literature  by bibtexkey (quotation, bibliography)
  notes       by notelabel (text)
  henry       by (species IUPAC name, bibtexkey, type, value, temperature dependence),
              counted, so a row that appears twice in one version and once in the
              other shows as one added or removed row.
"""
import collections
import csv
import json
import os
import sys

import pandas as pd


def load(outdir):
    meta = json.load(open(os.path.join(outdir, "build_meta.json"), encoding="utf-8"))
    t = {n: pd.read_csv(os.path.join(outdir, "csv", n + ".csv"), dtype=str, keep_default_na=False)
         for n in ("species", "literature", "notes", "henry")}
    return meta.get("version", "5.0.0"), t


def keyed(df, key, fields):
    d = {}
    for r in df.itertuples(index=False):
        k = getattr(r, key)
        d[k] = tuple(getattr(r, f) for f in fields)
    return d


def main():
    a_dir, b_dir, repdir = sys.argv[1:4]
    va, A = load(a_dir)
    vb, B = load(b_dir)
    rows = []

    def compare(table, key, fields):
        a, b = keyed(A[table], key, fields), keyed(B[table], key, fields)
        for k in sorted(set(a) - set(b)):
            rows.append([table, "removed", k, "", "", ""])
        for k in sorted(set(b) - set(a)):
            rows.append([table, "added", k, "", "", ""])
        for k in sorted(set(a) & set(b)):
            for f, x, y in zip(fields, a[k], b[k]):
                if x != y:
                    rows.append([table, "changed", k, f, x, y])

    compare("species", "iupac", ["formula", "trivial", "casrn", "inchikey", "subcategory_key"])
    compare("literature", "bibtexkey", ["quotation", "bibliography"])
    compare("notes", "notelabel", ["notetext_html"])

    def hkeys(t):
        sp = dict(zip(t["species"].species_id, t["species"].iupac))
        h = t["henry"]
        return collections.Counter(zip(h.species_id.map(sp), h.bibtexkey, h.htype, h.hominus_raw, h.mindhr_raw))

    ha, hb = hkeys(A), hkeys(B)
    for k in sorted(set(ha) | set(hb), key=str):
        d = hb.get(k, 0) - ha.get(k, 0)
        if d:
            rows.append(["henry", "added" if d > 0 else "removed", " | ".join(k), "count", ha.get(k, 0), hb.get(k, 0)])

    os.makedirs(repdir, exist_ok=True)
    path = os.path.join(repdir, "changes_%s_to_%s.csv" % (va, vb))
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["table", "change", "key", "field", "old", "new"])
        w.writerows(rows)
    summary = collections.Counter((r[0], r[1]) for r in rows)
    print("%s -> %s: %d differences, written to %s" % (va, vb, len(rows), path))
    for (t, c), n in sorted(summary.items()):
        print("  %-10s %-8s %d" % (t, c, n))


if __name__ == "__main__":
    main()
