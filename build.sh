#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

LC_ALL=C make -C build config=debug -Bnw | bear parse-sh
python3 tools/clangd_database.py --project "${CLANGD_PROJECT:-SALodLights}"
make -C build config=release SALodLights -j$(sysctl -n hw.logicalcpu)
