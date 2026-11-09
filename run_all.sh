#!/bin/sh
# Rebuild the whole edition from the published files. Run from this directory.
# Inputs: inputs/henry_5.0.0_sql.zip, inputs/acp-23-10901-2023-supplement.zip,
#         inputs/acp-23-10901-2023.pdf, live/ (saved pages, see live/fetch_log.csv).
# To read the live pages again (one request every 5 s): python3 -I scripts/fetch_live.py live
set -e
python3 -I scripts/build.py inputs/henry_5.0.0_sql.zip inputs/acp-23-10901-2023.pdf out live/casrn_3907-98-0.html
python3 -I scripts/errata.py out live errata
python3 -I scripts/verify.py inputs/henry_5.0.0_sql.zip inputs/acp-23-10901-2023-supplement.zip out reports > /dev/null
python3 -I scripts/compiler_files.py out reports
python3 -I scripts/make_docs.py .
