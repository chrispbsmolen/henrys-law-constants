# Data dictionary

Edition of R. Sander's compilation of Henry's law constants, version 5.0.0. Tables are in `out/csv/` (UTF-8, comma-separated, header row, LF line ends), `out/parquet/` (same tables, typed) and `out/henry_5.0.0.sqlite` (same tables, with primary and foreign keys). The same content is in `data_dictionary.csv`.

Conventions: text fields copied from the dump are exact (HTML and character references kept, SQL quote doubling undone). Columns ending in `_text` are plain-text renderings. In CSV, an empty field means an empty string for text columns and a missing value for numeric columns. Ids are the ids PostgreSQL assigns when the dump is loaded into an empty database. `sql_seq` gives the order of the INSERT statements, which is needed because note links refer to the most recent henry row.

## categories

Top-level groups of species, as in the SQL dump.

| column | type | description |
|---|---|---|
| `category_id` | integer | Row id, 1-based in insert order (PostgreSQL SERIAL). |
| `category` | text | Category name (catname). |
| `sql_seq` | integer | Position of the INSERT statement in henry-5.0.0.sql (1 = first INSERT). |

## subcategories

Subgroups of species.

| column | type | description |
|---|---|---|
| `subcategory_id` | integer | Row id, 1-based in insert order. |
| `subcategory` | text | Subcategory name (subcatname). |
| `category_id` | integer | categories.category_id, resolved from the name lookup in the dump. |
| `category_key` | text | The category name used in the lookup, as written in the dump. |
| `sql_seq` | integer | Position of the INSERT statement in the dump. |

## species

One row per species (10,173).

| column | type | description |
|---|---|---|
| `species_id` | integer | Row id, 1-based in insert order; henry.species_id refers to it. |
| `iupac` | text (HTML) | Systematic name exactly as in the dump; may contain HTML such as <i>tert</i>. |
| `iupac_text` | text | Plain-text rendering of iupac (tags removed, entities decoded). |
| `formula` | text (HTML) | Chemical formula exactly as in the dump, e.g. O<sub>2</sub>. |
| `formula_text` | text | Plain-text rendering of formula, e.g. O2. |
| `trivial` | text (HTML) | Trivial name(s) as in the dump; empty if none. |
| `trivial_text` | text | Plain-text rendering of trivial. |
| `casrn` | text | CAS Registry Number; empty if none is given. |
| `inchikey` | text | Standard InChIKey; empty if none is given. Two keys are corrected in the errata layer. |
| `subcategory_id` | integer | subcategories.subcategory_id, resolved from the name lookup. |
| `subcategory_key` | text | The subcategory name used in the lookup, as written in the dump. |
| `sql_seq` | integer | Position of the INSERT statement in the dump. |
| `n_henry_rows` | integer | Number of henry rows for this species. |
| `patched` | boolean | (patched copy only) True if an errata patch changed this row. |

## literature

One row per reference (1,076).

| column | type | description |
|---|---|---|
| `literature_id` | integer | Row id, 1-based in insert order; henry.literature_id refers to it. |
| `bibtexkey` | text | Reference key used by the compilation (usually a number). |
| `quotation` | text (HTML) | Short citation, e.g. Abraham et&nbsp;al. (2007). |
| `quotation_text` | text | Plain-text rendering of quotation. |
| `bibliography` | text (HTML) | Full reference exactly as in the dump. |
| `bibliography_text` | text | Plain-text rendering of bibliography. |
| `doi` | text | DOI taken from the first https://doi.org/ link in bibliography; empty if there is none. The dump's own doi column is never filled, so it is not carried over. |
| `doi_url` | text | https://doi.org/ + doi; empty if there is no DOI. |
| `n_doi_links` | integer | Number of doi.org links found in bibliography. |
| `sql_seq` | integer | Position of the INSERT statement in the dump. |
| `n_henry_rows` | integer | Number of henry rows citing this reference. |

## notes

One row per note (826).

| column | type | description |
|---|---|---|
| `note_id` | integer | Row id, 1-based in insert order. Note: the live website numbers notes independently; its numbers can differ. |
| `notelabel` | text | Note label used for the lookup in the dump. |
| `noterefs` | text | Comma-separated bibtexkeys cited by the note, as in the dump (split out in note_references). |
| `notetext_html` | text (HTML) | Note text exactly as in the dump (HTML kept). Three-parameter temperature fits appear only here. |
| `notetext_text` | text | Plain-text rendering: tags removed, <sup>x</sup> written as ^x or ^(xy), entities decoded, non-breaking spaces made ordinary spaces. |
| `sql_seq` | integer | Position of the INSERT statement in the dump (empty for notes added by the errata layer). |
| `n_henry_rows` | integer | Number of henry rows linked to this note. |

## note_references

The noterefs field of notes split into one row per cited key.

| column | type | description |
|---|---|---|
| `note_id` | integer | notes.note_id. |
| `position` | integer | Order of the key within noterefs (1-based). |
| `bibtexkey` | text | Cited key. |
| `literature_id` | integer | literature.literature_id for that key; empty if the key is not in literature. |

## henry

One row per Henry's law constant (46,434).

| column | type | description |
|---|---|---|
| `henry_id` | integer | Row id, 1-based in insert order (the id CURRVAL('henry_id_seq') refers to). |
| `species_id` | integer | species.species_id, resolved from the iupac lookup. |
| `species_key` | text | The species name used in the lookup, as written in the dump. |
| `literature_id` | integer | literature.literature_id; empty for the 3 rows citing the key 'this', which has no literature row. |
| `bibtexkey` | text | The reference key used in the lookup, as written in the dump. |
| `htype` | text | Type code (how the value was obtained); see htype_legend. |
| `hominus_raw` | text (HTML) | The Hominus string exactly as in the dump, e.g. 1.3&times;10<sup>&#8722;5</sup>, &gt; 1.0, &#8734; (infinity) or empty. |
| `value_status` | text | ok (a number), empty (no value), infinity (the &#8734; sign) or parse_failure. |
| `limit_flag` | text | > or < when the value is a lower or upper limit; empty otherwise. |
| `hscp_mantissa` | text | Mantissa as written (two significant digits), e.g. 1.3. |
| `hscp_exponent` | integer | Power of ten; empty when the value is written without one. |
| `hscp_si_exact` | text | The value as an exact decimal string, e.g. 1.3e-5; inf for infinity. |
| `hscp_si` | float | Henry's law solubility constant Hscp at 298.15 K in mol/(m3 Pa) (float64; inf for infinity). For limits this is the limit value; read limit_flag. |
| `hscp_matm` | float | hscp_si x hscp_matm_factor, i.e. Hscp in M/atm (mol/L per atm), computed in decimal arithmetic and then stored as float64. |
| `hscp_matm_factor` | float | 101.325: 1 mol/(m3 Pa) = 101.325 M/atm (Sander 2023, Table 2; atm = 101 325 Pa, M = mol/L). |
| `mindhr_raw` | text | The mindHR string exactly as in the dump (empty if none). |
| `mindhr_status` | text | ok, empty or parse_failure. |
| `mindhr_K` | integer | Temperature dependence d ln Hscp / d(1/T) at 298.15 K, in K (= -Delta_sol H / R). |
| `note_ids` | text | notes.note_id values linked to this row, ';'-separated in the order of the dump. |
| `n_notes` | integer | Number of linked notes. |
| `sql_seq` | integer | Position of the INSERT statement in the dump. |
| `patched` | boolean | (patched copy only) True if an errata patch changed this row or its notes. |

## henry_notes

Links between henry rows and notes (45,471).

| column | type | description |
|---|---|---|
| `henry_id` | integer | henry.henry_id, i.e. CURRVAL('henry_id_seq') at the point of the INSERT. |
| `note_id` | integer | notes.note_id, resolved from the label lookup. |
| `notelabel` | text | The note label used in the lookup, as written in the dump. |
| `sql_seq` | integer | Position of the INSERT statement in the dump (empty for links added by the errata layer). |

## htype_legend

Type codes and their meaning.

| column | type | description |
|---|---|---|
| `code` | text | Type code as used in henry.htype. |
| `short_label` | text | Short label as printed in the legend of the species pages of henrys-law.org. |
| `definition` | text | Definition as printed in Sander (2023), Sect. 3.1, extracted from the PDF text layer. The PDF text layer renders the Greek capital Delta as '1' (code T: '1sol G' is Delta_sol G). |
| `source` | text | Where the definition was taken from. |
| `n_henry_rows` | integer | Number of henry rows with this code. |

## Errata layer (`errata/`)

The patch layer is kept separate from the base tables. `errata/patched/` holds copies of the species, henry, notes and henry_notes tables with the patches applied (derived columns recomputed).

### errata_entries

Every entry of the live errata page.

| column | description |
|---|---|
| `entry_id` | Version and position on the page, e.g. 5.0.0-1. |
| `errata_url` | URL of the errata page. |
| `errata_page_sha256` | SHA-256 of the saved page. |
| `errata_fetched_utc` | When the page was read. |
| `version` | Version the entry belongs to. |
| `section` | Section heading on the page. |
| `applies_to_v5_0_0` | True for entries listed under version 5.0.0; older entries are stated on the page as already corrected. |
| `text` | Entry text (plain). |
| `text_html` | Entry text (HTML as on the page). |
| `species` | Species of the tables named in a v5.0.0 entry. |
| `n_patches` | Number of patch rows citing the entry. |
| `consistency` | For the InChIKey entry: whether the base value equals the old key and the live page shows the new key. |

### patches

The patch layer: one row per changed field or inserted row.

| column | description |
|---|---|
| `patch_id` | Patch identifier. |
| `layer_version` | Version of the patch layer. |
| `op` | update (change one column of an existing row) or insert (add a row; patched_value holds it as JSON). |
| `table` | Base table the patch applies to. |
| `row_id` | Id of the row in that table (henry_id;note_id for henry_notes). |
| `column` | Column changed ('*' for inserts). |
| `base_value` | Value in the v5.0.0 tables. |
| `patched_value` | Value after the patch. |
| `errata_entry_id` | errata_entries.entry_id of the entry that justifies the patch. |
| `errata_url` | URL of the errata page. |
| `errata_text` | Text of that entry. |
| `evidence_url` | Live page showing the corrected value. |
| `evidence_file` | Saved copy of that page (live/). |
| `evidence_sha256` | SHA-256 of the saved copy. |
| `evidence_fetched_utc` | When it was read. |
| `remark` | Free-text remark. |

### live_differences_not_in_errata

Differences between the live site and v5.0.0 that no errata entry covers. Reported, not patched.

| column | description |
|---|---|
| `table` | Base table concerned. |
| `difference_kind` | digits only, letter case only, text, or added or removed. |
| `row_id` | Row id in the base table. |
| `column` | Column concerned. |
| `base_value` | Value in v5.0.0. |
| `live_value` | Value on the live site. |
| `evidence_url` | Live page. |
| `evidence_sha256` | SHA-256 of the saved copy. |
| `evidence_fetched_utc` | When it was read. |
| `context` | Where the difference was seen. |

### errata_checks

Machine checks of older errata entries against v5.0.0.

| column | description |
|---|---|
| `entry_id` | errata_entries.entry_id. |
| `check` | What was checked. |
| `result` | pass, FAIL, or not checked (entry has no machine-checkable statement). |
