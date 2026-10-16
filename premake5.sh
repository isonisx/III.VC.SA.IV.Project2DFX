#!/bin/bash
set -euo pipefail

rm -rf build
premake5 gmake --file=premake5.lua
