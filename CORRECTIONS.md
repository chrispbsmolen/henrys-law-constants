# Corrections, credit and removal

All credit for the compilation of Henry's law constants belongs to Rolf Sander (Max Planck Institute for Chemistry, Mainz). This repository is a conversion of his published SQL file into plain tables; it is not an official release and is not endorsed by him.

If you find an error in the conversion, or if you are the compiler and would like anything corrected, credited differently, or this edition withdrawn, please write to Christopher Smolen, chrispbsmolen@gmail.com. Requests from the compiler are acted on without discussion.

Corrections to the data themselves belong with the compiler (https://henrys-law.org). Issues found during the conversion are listed, unchanged, in reports/REPORT_FOR_SANDER.md and reports/inconsistencies.csv. These points were sent to the compiler on 7 November 2026. His replies of 9 November 2026 are summarised below.


## The compiler's replies (9 November 2026)

Rolf Sander answered the points in reports/REPORT_FOR_SANDER.md. In short:

- **Reference key `this`** means "this work": values calculated for Sander (2023).
- **Rows for the same species and reference that cannot be told apart** come from large data tables in the sources; it is unclear why some species appear there more than once.
- **Negative temperature dependence (14 rows)** is suspicious but reproduced as given in the original papers.
- **The 14 references not cited in the tables** are cited in the text of Sander (2023), which uses the same bibliography file. **DOIs shared by several references** belong to chapters of the same book. Neither is an error.
- **Values far from the median for their species** are most likely QSPR outliers or effective rather than intrinsic constants.
- **Rows with a temperature dependence but no Hscp value** are expected; many come from a paper that predicts only the temperature dependence. **Rows with neither** are data the compiler judged wrong (explained in a note) or, for some strong acids such as HCl, solubility data that cannot be converted to Hscp and are given in the notes instead.
- **Type W** means wrong; the values are deliberately not reproduced. **∞ (type E)** means infinite solubility is assumed.
- **Missing CAS RNs** are normal. **Missing InChIKeys (13 species)** should be added; the list has been sent to the compiler.
- **Live site vs. henry_5.0.0_sql.zip:** the 200 digit-only differences in notes come from refitted coefficients and are far smaller than the experimental uncertainty. The remaining 15 differences (errata/live_differences_not_in_errata.csv) have been sent to the compiler to check.
