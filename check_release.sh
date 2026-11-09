#!/bin/sh
# Check a new release of the compilation before (or after) it is published.
#
#   sh check_release.sh <henry_X_sql.zip or henry-X.sql> [previous edition, default: out]
#
# Builds the tables from the given file into release_check/<file name>/, runs the
# same checks as for 5.0.0, writes the files for the compiler, and lists what
# changed since the previous edition. Needs Python 3 with pandas and pyarrow, and
# pdftotext (poppler) for reading the type-code legend from the 2023 paper.
# Run from this directory. Nothing outside release_check/ is changed.
set -e
SQL="$1"
PREV="${2:-out}"
if [ -z "$SQL" ]; then
    echo "usage: sh check_release.sh <henry_X_sql.zip or henry-X.sql> [previous edition directory]" >&2
    exit 1
fi
PDF=inputs/acp-23-10901-2023.pdf
[ -f "$PDF" ] || { echo "missing $PDF: run sh fetch_inputs.sh first" >&2; exit 1; }
NAME=$(basename "$SQL" .zip)
DEST="release_check/$NAME"
mkdir -p "$DEST"
HENRY_ANY_VERSION=1 python3 -I scripts/build.py "$SQL" "$PDF" "$DEST/out" - > "$DEST/build.log"
python3 -I scripts/verify.py "$SQL" - "$DEST/out" "$DEST/reports" > "$DEST/verify.log"
python3 -I scripts/compiler_files.py "$DEST/out" "$DEST/reports"
python3 -I scripts/compare_versions.py "$PREV" "$DEST/out" "$DEST/reports"
echo
echo "Done. Look at:"
echo "  $DEST/reports/inconsistencies.csv     (the same kinds of points as in the 5.0.0 report)"
echo "  $DEST/reports/changes_*.csv            (what changed since the previous edition)"
echo "  $DEST/reports/for_the_compiler/        (doi_updates.sql, species_without_inchikey.csv)"
echo "  $DEST/reports/verification.json        (every check and its result)"
