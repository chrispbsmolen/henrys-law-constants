# Henry's law constants (Sander, version 5.0.0) as tidy tables

This is a machine-readable edition of Rolf Sander's compilation of Henry's law
constants for water as solvent, version 5.0.0. It contains the same 46,434
constants for 10,173 species from 1,076 references as the compilation, with
the notes and the type codes, in plain tables (CSV, Parquet and SQLite)
instead of a PostgreSQL dump.

**This is not an official release.** It was prepared independently by
Christopher Smolen and is not endorsed by Rolf Sander or the Max Planck
Institute for Chemistry. The authoritative source is the compilation itself:
the paper and https://www.henrys-law.org.

## Source

Sander, R.: Compilation of Henry's law constants (version 5.0.0) for water as
solvent, Atmos. Chem. Phys., 23, 10901-12440, 2023,
https://doi.org/10.5194/acp-23-10901-2023. The paper is distributed under the
Creative Commons Attribution 4.0 License (CC BY 4.0).

When you use these data, please cite that paper, as the compiler asks.

The tables were built from the SQL file published on the compilation's website:

| file | URL | bytes | SHA-256 |
|---|---|---|---|
| henry_5.0.0_sql.zip | https://henrys-law.org/henry_data/henry_5.0.0_sql.zip | 991,424 | d90b7264a55ebb2c42fcca4b3483d0cc5361caa177224685cc66f3f7d7fb9d1b |
| henry-5.0.0.sql (inside the zip) | | 22,139,462 | c62f0d221f08b22883812b53a0df996b37a9f037c3fc46dd5adb5110b753de85 |

Two further published files were used: the paper's PDF (for the definitions of
the type codes, Sect. 3.1, and the unit conversion factor, Table 2;
`inputs/acp-23-10901-2023.pdf` once fetched, SHA-256
8c059bc311cacb0b4626f1935a06f990303d9af0af50721dd5fb864ddbc88bad) and the
paper's supplement (acp-23-10901-2023-supplement.zip, SHA-256
fb0bdedf7ff59afb1ac012b8bc0b64c58e2c6cf666b00a48d26d173aeb6149c7), whose
Fortran listings of all constants served as an independent check.

## What is in it

| path | contents |
|---|---|
| `out/csv/`, `out/parquet/` | the tables below, in CSV (UTF-8) and Parquet |
| `out/henry_5.0.0.sqlite` | the same tables in one SQLite file, with keys; also the errata tables |
| `errata/` | the errata patch layer (see below) |
| `reports/` | the results of the checks and a list of points for the compiler |
| `DATA_DICTIONARY.md`, `data_dictionary.csv` | every column explained |
| `live/fetch_log.csv` | when each live website page was read, with its hash (the pages themselves are not redistributed; `scripts/fetch_live.py` reads them again) |
| `scripts/`, `fetch_inputs.sh`, `run_all.sh` | the programs that download the published files (checked against `inputs.sha256`) and build everything from them |
| `CORRECTIONS.md`, `LICENSE` | credit, corrections and removal; CC BY 4.0 for the data, MIT for the code |
| `SHA256SUMS` | checksums of all files |

The tables:

- **henry** (46,434 rows): one row per constant, with the species, the
  reference, the type code, the value exactly as written in the source (for
  example `1.3&times;10<sup>&#8722;5</sup>`), the parsed value Hscp in
  mol/(m3 Pa) at 298.15 K, a flag for values given as limits (`>` or `<`),
  the value converted to M/atm (factor 101.325, stated in its own column),
  the temperature dependence d ln Hscp / d(1/T) in K (as written and as a
  number), and the ids of the notes that apply.
- **species** (10,173): names, formulas (as in the source, which uses some
  HTML, and as plain text), CAS numbers, InChIKeys, subcategory.
- **literature** (1,076): the short citation, the full reference, and the DOI
  where the reference contains a doi.org link (942 of them).
- **notes** (826): the note text as in the source (HTML kept) and as plain
  text. Three-parameter temperature fits appear only in the notes.
- **henry_notes** (45,471): which notes apply to which constants.
- **note_references**: the references cited by each note, one per row.
- **categories** (11), **subcategories** (63): the grouping of species.
- **htype_legend** (11): the type codes (L literature review, M measured,
  V vapour pressure/aqueous solubility, R recalculation, T thermodynamical
  calculation, X original paper not available, C citation, Q QSPR,
  E estimate, ? unknown, W probably wrong) with the definitions printed in
  Sander (2023), Sect. 3.1, p. 10908.

A few things to know when reading the values:

- 1,201 constants have no value: 968 give only a temperature dependence and
  233 refer to notes. 12 constants are given as infinitely soluble (the sign
  &#8734; in the source); they are stored as `inf` with `value_status` =
  `infinity`. 92 values are limits; read `limit_flag` before using them.
- Values are rounded to two significant digits in the source; the exact
  decimal string is in `hscp_si_exact`.
- Ids are the ids PostgreSQL gives the rows when the dump is loaded into an
  empty database, so they agree with any database built from the same file.

## How it was converted

A program reads the SQL file statement by statement, in order, and does what
PostgreSQL would do when loading it: every INSERT gets the next id, every
`(SELECT id FROM ... WHERE name='...')` is resolved against the rows inserted
so far, and every note link `(SELECT CURRVAL('henry_id_seq'))` is attached to
the most recent constant. Values are parsed with a strict pattern; nothing
that fails to match is guessed. No value was typed by hand: every number and
text comes from the SQL file, the paper or the saved web pages.

## Errata layer

The SQL file dates from October 2023. The compilation's errata page
(https://www.henrys-law.org/henry/errata.html, read 8 November 2026) lists
27 entries: 2 for version 5.0.0 and 25 for older versions, which the page
states were already corrected before 5.0.0.

The two 5.0.0 entries are applied as a separate, versioned patch layer
(`errata/patches.csv`, layer version 1). The base tables are not changed.
Each patch row cites the errata entry, the errata URL and the live species
page that shows the corrected value, with the page's hash and the time it
was read. There are 6 patches:

- the InChIKeys of 1,2,3-trichlorobenzene-d3 and monochlorine monoxide;
- the Mackay et al. (1993) entry for 2-methyltetrahydrofuran, which on the
  live site no longer has a value, has type W and carries a new note.

`errata/patched/` holds copies of the species, henry, notes and henry_notes
tables with the patches applied. `errata/errata_checks.csv` checks the older
entries against the 5.0.0 tables where an entry states a checkable fact
(7 checks, all pass).

Applying the errata needed 7 page reads (the errata page, four species
pages, and the live notes and references pages), far below the limit of
about 10,000 set for this project. The live notes and references pages also
show 215 changes that the errata page does not mention, mostly refitted
coefficients of three-parameter fits; these are listed in
`errata/live_differences_not_in_errata.csv` and are **not** applied. Finding
all such changes in the data rows would need every species page of the live
site (10,173 pages), which was not attempted.

## Checks

All checks are run by `scripts/verify.py`; the results are in
`reports/verification.json`.

- Row counts: 46,434 constants, 10,173 species, 45,471 note links and 1,076
  references, as expected.
- Round trip: all 104,054 INSERT statements of the SQL file were rebuilt from
  the CSV tables and are identical, byte for byte, to the original.
- Parsing: all 45,233 non-empty values and all 5,327 temperature
  dependences were parsed; 0 failures (the project's limit was 0.1 %).
  Every parsed value, written back in the source's notation, gives the
  original string.
- Units: the M/atm factor 101.325 is read from Table 2 of the paper and
  equals 101 325 Pa/atm divided by 1000 L/m3. All 45,221 numeric values agree
  with the supplement's Fortran listings in mol/(m3 Pa) (HscpSI.f90) and,
  within two-digit rounding, in M/atm (Hscp.f90), including type, reference
  and temperature dependence.
- The Parquet and SQLite copies agree with the CSV copy; the SQLite file has
  no foreign-key violations.
- CAS numbers pass the check-digit test and InChIKeys are well formed.

Points that look inconsistent inside the source (for example 3 constants that
cite a reference key, 'this', that is not in the reference list, rows for the
same species and reference that cannot be told apart, and 14 negative
temperature dependences) are listed for the compiler in
`reports/REPORT_FOR_SANDER.md` and `reports/inconsistencies.csv`. None of
them was changed.

## Licence

The data are by Rolf Sander and are published in the paper above under
CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). This edition is
distributed under the same licence. Attribution: cite Sander (2023) as given
above, and say that the tables were converted by Christopher Smolen from the
published SQL file. The SQL download itself carries no licence statement;
this edition relies on the licence of the paper in which the same data are
published. Short passages of text from the live website (errata entries,
one note, type labels) are quoted in the errata layer with their source.

## Credit, corrections and removal

All credit for the compilation belongs to Rolf Sander. If you find an error
in the conversion, or if you are the compiler and would like something
corrected, credited differently, or this edition withdrawn, please write to
Christopher Smolen, chrispbsmolen@gmail.com.
