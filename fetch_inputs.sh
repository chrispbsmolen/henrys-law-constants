#!/bin/sh
# Download the published inputs (not redistributed here) and check their SHA-256.
set -e
mkdir -p inputs
curl -fL -o inputs/henry_5.0.0_sql.zip https://henrys-law.org/henry_data/henry_5.0.0_sql.zip
curl -fL -o inputs/acp-23-10901-2023-supplement.zip https://acp.copernicus.org/articles/23/10901/2023/acp-23-10901-2023-supplement.zip
curl -fL -o inputs/acp-23-10901-2023.pdf https://acp.copernicus.org/articles/23/10901/2023/acp-23-10901-2023.pdf
sha256sum -c inputs.sha256 2>/dev/null || shasum -a 256 -c inputs.sha256
# The live website pages used for the errata layer are read again with:
#   python3 -I scripts/fetch_live.py live    (one request every 5 s)
