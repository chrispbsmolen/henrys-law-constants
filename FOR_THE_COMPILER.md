# For the compiler

This page is for Rolf Sander, and for anyone who maintains the compilation after him. Everything
here is optional. The code in this repository is under the MIT licence, so it can be copied,
changed and used in any way, including inside your own workflow, without asking.

## Checking a new release

Most of the checks that produced the report for 5.0.0 can be run on any new SQL file, before or
after it is published:

```
sh fetch_inputs.sh                              # once: the 5.0.0 zip and the 2023 paper
pip install -r requirements.txt                 # once: pandas and pyarrow
sh check_release.sh henry_5.1.0_sql.zip         # or the .sql file itself
```

It also needs `pdftotext` (from poppler), which reads the type-code legend from the 2023 paper.
A run takes about a minute. It runs every check that needs only the SQL file, including reading
every INSERT statement back byte for byte. It does not compare with the paper's Fortran supplement
or with the live website, which need files of that release, and it leaves the short type labels
empty. Everything it writes goes into `release_check/<file name>/`:

| file | what it is |
|---|---|
| `reports/inconsistencies.csv` | the same kinds of points as in the 5.0.0 report, one row each, with a category |
| `reports/changes_5.0.0_to_X.csv` | the species, references, notes and constants that were added, removed or changed since 5.0.0 (not yet: changes in which notes are linked to which rows, or in category names) |
| `reports/verification.json` | every check and its result, including that every INSERT statement was read back byte for byte |
| `reports/for_the_compiler/doi_updates.sql` | see below |
| `reports/for_the_compiler/species_without_inchikey.csv` | species with an empty InChIKey |
| `out/` | the tables in CSV, Parquet and SQLite |

To compare with a release other than 5.0.0, give its built directory as a second argument:
`sh check_release.sh henry_5.2.0_sql.zip release_check/henry_5.1.0_sql/out`.

The checks only report; nothing is changed in the SQL file.

## Filling the doi column

The `literature` table in the SQL file has a `doi` column, but no INSERT sets it, so it is empty
for all 1,076 entries. 942 bibliographies contain a doi.org link. `doi_updates.sql`
(in `reports/for_the_compiler/`) has one statement per entry with a link, for example

```
UPDATE literature SET doi = '10.1021/JE00044A027' WHERE bibtexkey = '2291' AND (doi IS NULL OR doi = '');
```

wrapped in one transaction, so it can be read through and then run on the database with `psql`.
It was tested by loading henry-5.0.0.sql into PostgreSQL 16 and running it: all 942 fields are
filled, each with the DOI of its own bibliography's link, and running it again changes nothing.
Each DOI is the link target as written, with HTML entities decoded (two DOIs contain `<` and `>`,
which is correct for those publishers). One exception: for Wieser, Sander and Taraborrelli the SQL
file has the Discussion paper (10.5194/GMD-2023-102) and the live references page the final paper
(10.5194/GMD-17-4311-2024); the statement uses the live one, and a comment above it says so.
A bibliography with more than one doi.org link would be listed in `inconsistencies.csv`
(category several_doi_links); 5.0.0 has none.

## Missing InChIKeys

`species_without_inchikey.csv` lists the 13 species without one in 5.0.0, and
`inchikey_suggestions.csv` (same folder) suggests a key for each, with where its structure came
from and a note:

- Three are meso compounds (cis dinitrates), which have a single key.
- The other ten are chiral and were most likely measured as racemates: the four trans dinitrates,
  triadimenol A and B, cis- and trans-propiconazole, and the two bromuconazole isomers. A standard
  InChIKey states an absolute configuration and cannot say "racemic", so the key suggested is that
  of one enantiomer, standing in for the pair (the Henry's law constants of two enantiomers are
  equal). For the dinitrates it is the (R,R) enantiomer the name gives; for the azoles, the
  enantiomer PubChem records for that diastereomer. The stereo-free key would not do: it is the same
  for the cis and trans isomer of each compound and is already used by the parent compounds.
- Each structure comes from a PubChem record named in the file. RDKit recomputes every key and
  checks the stereocentres against the name (exactly for the dinitrates; alike or unlike for the
  azoles). PubChem's name and CAS RN lookups were not always right: for (2R,4R)-2,4-pentanediol
  dinitrate both give a hydrate, the CAS RN of (1R,3R)-1,3-cyclohexanediol dinitrate gives the
  (1S,3S) enantiomer, and the 1,3-cyclohexanediol names are not found, so those structures were
  checked by their computed keys instead.
- Two CAS RNs may be worth a look: PubChem lists 82200-72-4 (triadimenol B in the table) as a
  synonym of triadimenol A, and does not know 112721-87-6 (cis-propiconazole in the table).

The suggestions are made by `scripts/inchikey_suggestions.py` (needs RDKit), which lists every
structure and where it came from. Leaving the racemates empty is a reasonable choice too.

## Keeping this edition current

When a new release appears, the tables here can be rebuilt from it with the same scripts and
published as a new version, with the changes listed. Corrections and requests from the compiler
are acted on without discussion (see CORRECTIONS.md).
