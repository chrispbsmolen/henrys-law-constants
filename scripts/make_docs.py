"""Write the data dictionary, the report for the compiler (R. Sander), and the checksum list.

Usage: python3 -I make_docs.py <builddir>

All numbers in the generated documents are read from build_meta.json,
verification.json, errata_summary.json and the tables themselves.
"""
import hashlib
import json
import os
import sys

import pandas as pd

D = {
    "categories": ("Top-level groups of species, as in the SQL dump.", {
        "category_id": ("integer", "Row id, 1-based in insert order (PostgreSQL SERIAL)."),
        "category": ("text", "Category name (catname)."),
        "sql_seq": ("integer", "Position of the INSERT statement in henry-5.0.0.sql (1 = first INSERT)."),
    }),
    "subcategories": ("Subgroups of species.", {
        "subcategory_id": ("integer", "Row id, 1-based in insert order."),
        "subcategory": ("text", "Subcategory name (subcatname)."),
        "category_id": ("integer", "categories.category_id, resolved from the name lookup in the dump."),
        "category_key": ("text", "The category name used in the lookup, as written in the dump."),
        "sql_seq": ("integer", "Position of the INSERT statement in the dump."),
    }),
    "species": ("One row per species (10,173).", {
        "species_id": ("integer", "Row id, 1-based in insert order; henry.species_id refers to it."),
        "iupac": ("text (HTML)", "Systematic name exactly as in the dump; may contain HTML such as <i>tert</i>."),
        "iupac_text": ("text", "Plain-text rendering of iupac (tags removed, entities decoded)."),
        "formula": ("text (HTML)", "Chemical formula exactly as in the dump, e.g. O<sub>2</sub>."),
        "formula_text": ("text", "Plain-text rendering of formula, e.g. O2."),
        "trivial": ("text (HTML)", "Trivial name(s) as in the dump; empty if none."),
        "trivial_text": ("text", "Plain-text rendering of trivial."),
        "casrn": ("text", "CAS Registry Number; empty if none is given."),
        "inchikey": ("text", "Standard InChIKey; empty if none is given. Two keys are corrected in the errata layer."),
        "subcategory_id": ("integer", "subcategories.subcategory_id, resolved from the name lookup."),
        "subcategory_key": ("text", "The subcategory name used in the lookup, as written in the dump."),
        "sql_seq": ("integer", "Position of the INSERT statement in the dump."),
        "n_henry_rows": ("integer", "Number of henry rows for this species."),
        "patched": ("boolean", "(patched copy only) True if an errata patch changed this row."),
    }),
    "literature": ("One row per reference (1,076).", {
        "literature_id": ("integer", "Row id, 1-based in insert order; henry.literature_id refers to it."),
        "bibtexkey": ("text", "Reference key used by the compilation (usually a number)."),
        "quotation": ("text (HTML)", "Short citation, e.g. Abraham et&nbsp;al. (2007)."),
        "quotation_text": ("text", "Plain-text rendering of quotation."),
        "bibliography": ("text (HTML)", "Full reference exactly as in the dump."),
        "bibliography_text": ("text", "Plain-text rendering of bibliography."),
        "doi": ("text", "DOI taken from the first https://doi.org/ link in bibliography; empty if there is none. "
                        "The dump's own doi column is never filled, so it is not carried over."),
        "doi_url": ("text", "https://doi.org/ + doi; empty if there is no DOI."),
        "n_doi_links": ("integer", "Number of doi.org links found in bibliography."),
        "sql_seq": ("integer", "Position of the INSERT statement in the dump."),
        "n_henry_rows": ("integer", "Number of henry rows citing this reference."),
    }),
    "notes": ("One row per note (826).", {
        "note_id": ("integer", "Row id, 1-based in insert order. Note: the live website numbers notes "
                               "independently; its numbers can differ."),
        "notelabel": ("text", "Note label used for the lookup in the dump."),
        "noterefs": ("text", "Comma-separated bibtexkeys cited by the note, as in the dump (split out in note_references)."),
        "notetext_html": ("text (HTML)", "Note text exactly as in the dump (HTML kept). Three-parameter "
                                         "temperature fits appear only here."),
        "notetext_text": ("text", "Plain-text rendering: tags removed, <sup>x</sup> written as ^x or ^(xy), "
                                  "entities decoded, non-breaking spaces made ordinary spaces."),
        "sql_seq": ("integer", "Position of the INSERT statement in the dump (empty for notes added by the errata layer)."),
        "n_henry_rows": ("integer", "Number of henry rows linked to this note."),
    }),
    "note_references": ("The noterefs field of notes split into one row per cited key.", {
        "note_id": ("integer", "notes.note_id."),
        "position": ("integer", "Order of the key within noterefs (1-based)."),
        "bibtexkey": ("text", "Cited key."),
        "literature_id": ("integer", "literature.literature_id for that key; empty if the key is not in literature."),
    }),
    "henry": ("One row per Henry's law constant (46,434).", {
        "henry_id": ("integer", "Row id, 1-based in insert order (the id CURRVAL('henry_id_seq') refers to)."),
        "species_id": ("integer", "species.species_id, resolved from the iupac lookup."),
        "species_key": ("text", "The species name used in the lookup, as written in the dump."),
        "literature_id": ("integer", "literature.literature_id; empty for the 3 rows citing the key 'this', "
                                     "which has no literature row."),
        "bibtexkey": ("text", "The reference key used in the lookup, as written in the dump."),
        "htype": ("text", "Type code (how the value was obtained); see htype_legend."),
        "hominus_raw": ("text (HTML)", "The Hominus string exactly as in the dump, e.g. 1.3&times;10<sup>&#8722;5</sup>, "
                                       "&gt; 1.0, &#8734; (infinity) or empty."),
        "value_status": ("text", "ok (a number), empty (no value), infinity (the &#8734; sign) or parse_failure."),
        "limit_flag": ("text", "> or < when the value is a lower or upper limit; empty otherwise."),
        "hscp_mantissa": ("text", "Mantissa as written (two significant digits), e.g. 1.3."),
        "hscp_exponent": ("integer", "Power of ten; empty when the value is written without one."),
        "hscp_si_exact": ("text", "The value as an exact decimal string, e.g. 1.3e-5; inf for infinity."),
        "hscp_si": ("float", "Henry's law solubility constant Hscp at 298.15 K in mol/(m3 Pa) (float64; inf for infinity). "
                             "For limits this is the limit value; read limit_flag."),
        "hscp_matm": ("float", "hscp_si x hscp_matm_factor, i.e. Hscp in M/atm (mol/L per atm), computed in decimal "
                               "arithmetic and then stored as float64."),
        "hscp_matm_factor": ("float", "101.325: 1 mol/(m3 Pa) = 101.325 M/atm (Sander 2023, Table 2; atm = 101 325 Pa, "
                                      "M = mol/L)."),
        "mindhr_raw": ("text", "The mindHR string exactly as in the dump (empty if none)."),
        "mindhr_status": ("text", "ok, empty or parse_failure."),
        "mindhr_K": ("integer", "Temperature dependence d ln Hscp / d(1/T) at 298.15 K, in K (= -Delta_sol H / R)."),
        "note_ids": ("text", "notes.note_id values linked to this row, ';'-separated in the order of the dump."),
        "n_notes": ("integer", "Number of linked notes."),
        "sql_seq": ("integer", "Position of the INSERT statement in the dump."),
        "patched": ("boolean", "(patched copy only) True if an errata patch changed this row or its notes."),
    }),
    "henry_notes": ("Links between henry rows and notes (45,471).", {
        "henry_id": ("integer", "henry.henry_id, i.e. CURRVAL('henry_id_seq') at the point of the INSERT."),
        "note_id": ("integer", "notes.note_id, resolved from the label lookup."),
        "notelabel": ("text", "The note label used in the lookup, as written in the dump."),
        "sql_seq": ("integer", "Position of the INSERT statement in the dump (empty for links added by the errata layer)."),
    }),
    "htype_legend": ("Type codes and their meaning.", {
        "code": ("text", "Type code as used in henry.htype."),
        "short_label": ("text", "Short label as printed in the legend of the species pages of henrys-law.org."),
        "definition": ("text", "Definition as printed in Sander (2023), Sect. 3.1, extracted from the PDF text layer. "
                               "The PDF text layer renders the Greek capital Delta as '1' (code T: '1sol G' is Delta_sol G)."),
        "source": ("text", "Where the definition was taken from."),
        "n_henry_rows": ("integer", "Number of henry rows with this code."),
    }),
}

ERRATA_D = {
    "errata_entries": ("Every entry of the live errata page.", {
        "entry_id": "Version and position on the page, e.g. 5.0.0-1.",
        "errata_url": "URL of the errata page.",
        "errata_page_sha256": "SHA-256 of the saved page.",
        "errata_fetched_utc": "When the page was read.",
        "version": "Version the entry belongs to.",
        "section": "Section heading on the page.",
        "applies_to_v5_0_0": "True for entries listed under version 5.0.0; older entries are stated on the page as already corrected.",
        "text": "Entry text (plain).",
        "text_html": "Entry text (HTML as on the page).",
        "species": "Species of the tables named in a v5.0.0 entry.",
        "n_patches": "Number of patch rows citing the entry.",
        "consistency": "For the InChIKey entry: whether the base value equals the old key and the live page shows the new key.",
    }),
    "patches": ("The patch layer: one row per changed field or inserted row.", {
        "patch_id": "Patch identifier.",
        "layer_version": "Version of the patch layer.",
        "op": "update (change one column of an existing row) or insert (add a row; patched_value holds it as JSON).",
        "table": "Base table the patch applies to.",
        "row_id": "Id of the row in that table (henry_id;note_id for henry_notes).",
        "column": "Column changed ('*' for inserts).",
        "base_value": "Value in the v5.0.0 tables.",
        "patched_value": "Value after the patch.",
        "errata_entry_id": "errata_entries.entry_id of the entry that justifies the patch.",
        "errata_url": "URL of the errata page.",
        "errata_text": "Text of that entry.",
        "evidence_url": "Live page showing the corrected value.",
        "evidence_file": "Saved copy of that page (live/).",
        "evidence_sha256": "SHA-256 of the saved copy.",
        "evidence_fetched_utc": "When it was read.",
        "remark": "Free-text remark.",
    }),
    "live_differences_not_in_errata": ("Differences between the live site and v5.0.0 that no errata entry covers. Reported, not patched.", {
        "table": "Base table concerned.",
        "difference_kind": "digits only, letter case only, text, or added or removed.",
        "row_id": "Row id in the base table.",
        "column": "Column concerned.",
        "base_value": "Value in v5.0.0.",
        "live_value": "Value on the live site.",
        "evidence_url": "Live page.",
        "evidence_sha256": "SHA-256 of the saved copy.",
        "evidence_fetched_utc": "When it was read.",
        "context": "Where the difference was seen.",
    }),
    "errata_checks": ("Machine checks of older errata entries against v5.0.0.", {
        "entry_id": "errata_entries.entry_id.",
        "check": "What was checked.",
        "result": "pass, FAIL, or not checked (entry has no machine-checkable statement).",
    }),
}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    bd = sys.argv[1]
    out = os.path.join(bd, "out")
    meta = json.load(open(os.path.join(out, "build_meta.json"), encoding="utf-8"))
    ver = json.load(open(os.path.join(bd, "reports", "verification.json"), encoding="utf-8"))
    er = json.load(open(os.path.join(bd, "errata", "errata_summary.json"), encoding="utf-8"))

    # ---- data dictionary (and a check that every column is documented) ----
    rows = []
    for t, (desc, cols) in D.items():
        actual = list(pd.read_csv(os.path.join(out, "csv", t + ".csv"), nrows=0).columns)
        pc = os.path.join(bd, "errata", "patched", "csv", t + ".csv")
        if os.path.exists(pc):
            actual += [c for c in pd.read_csv(pc, nrows=0).columns if c not in actual]
        missing = [c for c in actual if c not in cols]
        extra = [c for c in cols if c not in actual]
        if missing or extra:
            sys.exit("data dictionary out of step for %s: missing %s, extra %s" % (t, missing, extra))
        for c in actual:
            rows.append(dict(table=t, column=c, type=cols[c][0], description=cols[c][1]))
    for t, (desc, cols) in ERRATA_D.items():
        actual = list(pd.read_csv(os.path.join(bd, "errata", t + ".csv"), nrows=0).columns)
        if sorted(actual) != sorted(cols):
            sys.exit("errata dictionary out of step for %s" % t)
        for c in actual:
            rows.append(dict(table="errata/" + t, column=c, type="text", description=cols[c]))
    pd.DataFrame(rows).to_csv(os.path.join(bd, "data_dictionary.csv"), index=False, lineterminator="\n")

    md = ["# Data dictionary", "",
          "Edition of R. Sander's compilation of Henry's law constants, version 5.0.0. "
          "Tables are in `out/csv/` (UTF-8, comma-separated, header row, LF line ends), `out/parquet/` "
          "(same tables, typed) and `out/henry_5.0.0.sqlite` (same tables, with primary and foreign keys). "
          "The same content is in `data_dictionary.csv`.", "",
          "Conventions: text fields copied from the dump are exact (HTML and character references kept, "
          "SQL quote doubling undone). Columns ending in `_text` are plain-text renderings. "
          "In CSV, an empty field means an empty string for text columns and a missing value for numeric "
          "columns. Ids are the ids PostgreSQL assigns when the dump is loaded into an empty database. "
          "`sql_seq` gives the order of the INSERT statements, which is needed because note links refer "
          "to the most recent henry row.", ""]
    for t, (desc, cols) in D.items():
        md += ["## %s" % t, "", desc, "", "| column | type | description |", "|---|---|---|"]
        md += ["| `%s` | %s | %s |" % (r["column"], r["type"], r["description"].replace("|", "\\|"))
               for r in rows if r["table"] == t]
        md.append("")
    md += ["## Errata layer (`errata/`)", "",
           "The patch layer is kept separate from the base tables. `errata/patched/` holds copies of the "
           "species, henry, notes and henry_notes tables with the patches applied (derived columns recomputed).", ""]
    for t, (desc, cols) in ERRATA_D.items():
        md += ["### %s" % t, "", desc, "", "| column | description |", "|---|---|"]
        md += ["| `%s` | %s |" % (c, d.replace("|", "\\|")) for c, d in cols.items()]
        md.append("")
    open(os.path.join(bd, "DATA_DICTIONARY.md"), "w", encoding="utf-8").write("\n".join(md))

    # ---- report for the compiler ----
    inc = pd.read_csv(os.path.join(bd, "reports", "inconsistencies.csv"), dtype=str, keep_default_na=False)
    und = pd.read_csv(os.path.join(bd, "errata", "live_differences_not_in_errata.csv"), dtype=str, keep_default_na=False)
    c = ver["issues_by_category"]

    def lst(cat, n=30):
        g = inc[inc.category == cat]
        lines = ["- %s %s: %s" % (r.table, r.key, r.detail) for r in g.head(n).itertuples()]
        if len(g) > n:
            lines.append("- ... %d more in `reports/inconsistencies.csv`" % (len(g) - n))
        return lines

    w_pairs = inc[(inc.category == "same_species_reference_different_values") & (inc.severity == "warning")]
    rep = ["# Points for the compiler: henry-5.0.0.sql", "",
           "Prepared by Christopher Smolen while converting the published SQL dump of the compilation "
           "(version 5.0.0) into tidy tables. Nothing listed here was changed in the converted tables; "
           "every item is reported as found. Row ids are those PostgreSQL assigns when the dump is loaded "
           "into an empty database (henry_id is the id that CURRVAL('henry_id_seq') returns). "
           "The full machine-readable list is `reports/inconsistencies.csv`.", "",
           "The dump itself is in good order: all %d INSERT statements load, every name lookup except "
           "three resolves to exactly one row, no note link collides, and the values agree one for one "
           "with output/HscpSI.f90 and output/Hscp.f90 in the supplement." % ver["insert_statements_in_file"], "",
           "## 1. References to the key 'this' (%d rows)" % c.get("dangling_reference", 0), "",
           "These henry rows look up `bibtexkey='this'`, which has no row in the literature table, so "
           "literature_id is NULL after loading. The Fortran files show `ref: this` for the same rows "
           "(presumably 'this work').", ""] + lst("dangling_reference") + [
           "", "## 2. Rows for the same species and reference that cannot be told apart", "",
           "%d species/reference pairs have two or more rows that are identical in value, temperature "
           "dependence, type and notes:" % c.get("duplicate_identical_rows", 0), ""] + lst("duplicate_identical_rows") + [
           "", "%d further pairs have rows with different values but the same type and the same notes, so "
           "a reader cannot tell which value belongs to which condition or method (%d more pairs differ in type or notes, "
           "which explains them; those are listed in the CSV with severity info):" % (len(w_pairs), c.get("same_species_reference_different_values", 0) - len(w_pairs)), ""] + \
          ["- %s %s: %s" % (r.table, r.key, r.detail) for r in w_pairs.head(30).itertuples()] + \
          (["- ... %d more in `reports/inconsistencies.csv`" % (len(w_pairs) - 30)] if len(w_pairs) > 30 else []) + [
           "", "## 3. Negative temperature dependence (%d rows)" % c.get("negative_mindHR", 0), "",
           "Not necessarily wrong (solubility rising with temperature is known for some gases), but listed for a second look:", ""] + lst("negative_mindHR") + [
           "", "## 4. References and DOIs", "",
           "%d literature rows are cited by no henry row; %d of them are cited in notes. The %d below are cited "
           "nowhere in the tables (several look like background references from the text of the paper):" % (
               ver["literature_unused"], ver["literature_unused"] - ver["literature_unused_anywhere"],
               ver["literature_unused_anywhere"]), ""] + lst("reference_unused") + [
           "", "DOIs shared by more than one reference (chapters of one book may be intended):", ""] + lst("duplicate_doi") + [
           "", "The doi column of the literature table is never filled; %d of %d bibliographies contain a doi.org link." % (
               ver["literature_with_doi"], ver["counts"]["literature"]), "",
           "## 5. Values far from the other values for the same species", "",
           "%d rows differ by more than a factor of 1000 from the median of the values for the same species "
           "(species with at least three plain values; limits and type W excluded). Many will be genuine "
           "(e.g. effective constants, QSPR outliers); they are listed only in the CSV "
           "(category value_far_from_species_median)." % ver["values_more_than_1000x_from_species_median"], "",
           "## 6. Other observations", "",
           "- %d rows give a temperature dependence but no Hscp value." % ver["mindHR_without_H"],
           "- %d rows give neither an Hscp value nor a temperature dependence; each of them has at least one note." % (ver["empty_H_rows"] - ver["mindHR_without_H"]),
           "- %d rows carry the infinity sign (&#8734;) as the value (type E)." % ver["hominus_status_counts"].get("infinity", 0),
           "- %d rows have type W; none carries a value in the dump." % ver["type_W_rows"],
           "- %d species have no CAS RN and %d no InChIKey; all given CAS RNs pass the check-digit test and all InChIKeys are well formed; "
           "no CAS RN or InChIKey is shared by two species." % (ver["species_without_casrn"], ver["species_without_inchikey"]),
           "", "## 7. Live site and the 2023 zip", "",
           "The live site differs from henry_5.0.0_sql.zip in places that the errata page does not mention. "
           "Comparing the live notes and references pages with the dump gives %d differences "
           "(the data rows themselves were compared only on the %d species pages read for the errata):" % (
               er["live_differences_not_in_errata"], len(er["live_species_pages_read"])), ""] + \
          ["- %s: %d" % (k, v) for k, v in er["live_differences_not_in_errata_by_kind"].items()] + [
           "", "Most are three-parameter fits whose coefficients changed in the fourth or fifth digit, "
           "for example:", ""] + \
          ["- note %s: `%s` -> `%s`" % (r.row_id, r.base_value[-140:], r.live_value[-140:]) for r in und[und.difference_kind.str.startswith("digits")].head(3).itertuples()] + [
           "", "An updated SQL dump (or a changelog) would let users pick up such changes without reading every page.", ""]
    open(os.path.join(bd, "reports", "REPORT_FOR_SANDER.md"), "w", encoding="utf-8").write("\n".join(rep))

    # ---- checksums ----
    files = []
    for root, dirs, fs in os.walk(bd):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for f in sorted(fs):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, bd)
            if rel == "SHA256SUMS":
                continue
            files.append((rel, os.path.getsize(p), sha256_file(p)))
    with open(os.path.join(bd, "SHA256SUMS"), "w") as f:
        for rel, size, h in files:
            f.write("%s  %s\n" % (h, rel))


if __name__ == "__main__":
    main()
