# For the compiler

This page is for Rolf Sander, and for anyone who maintains the compilation after him. Everything
here is optional. The code in this repository is under the MIT licence, so it can be copied,
changed and used in any way, including inside your own workflow, without asking.

## Checking a new release

The same checks that produced the report for 5.0.0 can be run on any new SQL file, before or
after it is published:

```
sh fetch_inputs.sh                              # once: the 5.0.0 zip and the 2023 paper
pip install -r requirements.txt                 # once: pandas and pyarrow
sh check_release.sh henry_5.1.0_sql.zip         # or the .sql file itself
```

It also needs `pdftotext` (from poppler), which reads the type-code legend from the 2023 paper.
A run takes about a minute. Everything it writes goes into `release_check/<file name>/`:

| file | what it is |
|---|---|
| `reports/inconsistencies.csv` | the same kinds of points as in the 5.0.0 report, one row each, with a category |
| `reports/changes_5.0.0_to_X.csv` | every species, reference, note and value that was added, removed or changed since 5.0.0 |
| `reports/verification.json` | every check and its result, including that every INSERT statement was read back byte for byte |
| `reports/for_the_compiler/doi_updates.sql` | see below |
| `reports/for_the_compiler/species_without_inchikey.csv` | species with an empty InChIKey |
| `out/` | the tables in CSV, Parquet and SQLite |

To compare with a release other than 5.0.0, give its built directory as a second argument:
`sh check_release.sh henry_5.2.0_sql.zip release_check/henry_5.1.0_sql/out`.

The checks only report; nothing is changed in the SQL file.

## Filling the doi column

The `literature` table in the SQL file has a `doi` column, but no INSERT sets it, so it is empty
for all 1,076 references. 942 bibliographies contain a doi.org link. `doi_updates.sql`
(in `reports/for_the_compiler/`) has one statement per reference with a link, for example

```
UPDATE literature SET doi = '10.1021/JE00044A027' WHERE bibtexkey = '2291' AND (doi IS NULL OR doi = '');
```

wrapped in one transaction, so it can be read through and then run on the database with `psql`.
Each DOI is the link target as written in the bibliography, with HTML entities decoded (two DOIs
contain `<` and `>`, which is correct for those publishers). Statements only fill empty fields.

## Missing InChIKeys

`species_without_inchikey.csv` lists the 13 species without one in 5.0.0, and
`inchikey_suggestions.csv` (same folder) has a suggestion for 7 of them:

- The seven dinitrates have explicit stereo descriptors in their names. Each structure was taken
  from PubChem by its name (or CAS RN), the InChIKey was recomputed with RDKit, and the script checks
  that the CIP labels match the name. Two needed care: the CAS RN of (2R,4R)-2,4-pentanediol
  dinitrate leads to a hydrate in PubChem, and the CAS RN of (1R,3R)-1,3-cyclohexanediol dinitrate
  leads to the (1S,3S) enantiomer; the suggestions use the compound as named in the table.
  Three of the seven are meso compounds. For the four chiral ones the key is for the enantiomer
  named; if the measured compound was the racemic trans isomer, a note may fit better.
- The other six (triadimenol A and B, cis- and trans-propiconazole, the two bromuconazole isomers)
  are racemic diastereomers. A standard InChIKey describes absolute configuration and cannot express
  "racemic, relative configuration", and the parent compounds already carry the stereo-free key, so
  no suggestion is made. Leaving them empty may well be the right choice.

The suggestions are made by `scripts/inchikey_suggestions.py` (needs RDKit), which lists every
structure and where it came from.

## Keeping this edition current

When a new release appears, the tables here can be rebuilt from it with the same scripts and
published as a new version, with the changes listed. Corrections and requests from the compiler
are acted on without discussion (see CORRECTIONS.md).
