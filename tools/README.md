# clangd on macOS

Run the existing workflow:

```sh
./premake5.sh
./build.sh
```

`build.sh` now generates two databases before running the existing SA Release
build:

- `compile_commands.json`: Bear's MinGW Debug commands, including translated
  sources under `build/compat`.
- `build/clangd/compile_commands.json`: Debug commands for the original sources
  and named modules of the selected game, plus directly compiled support sources.

The tooling generator requires Python 3 and the MinGW compiler on PATH. It derives
flags from Bear's database rather than maintaining another copy of the project's
include paths and defines. Run Premake again when adding/removing source files.

## Selecting a game

The default tooling project is `SALodLights`. To select another:

```sh
CLANGD_PROJECT=IIILodLights ./build.sh
```

Or regenerate only the tooling database, using the existing MinGW database:

```sh
python3 tools/clangd_database.py --project VCLodLights
```

Choices are `IIILodLights`, `VCLodLights`, `SALodLights`, and `IVLodLights`.
This selection affects editor analysis only; `build.sh` still builds SA Release.
Only the selected game's modules are included because the games reuse module
names and shared source files. Open files from other games are not reliably
analyzed until that game is selected. Restart Zed's language server after switching.

## Language server setup

`.clangd` selects the tooling database. `.zed/settings.json` associates `.ixx`
with C++ and starts the installed Apple clangd with:

- `--query-driver=/opt/homebrew/bin/i686-w64-mingw32-g++` to discover Windows x86
  target information and system headers.
- `--experimental-modules-support` to discover module dependencies and build
  Clang module artifacts on demand.

The tooling commands explicitly enable `-fcxx-modules` (Apple clangd otherwise
disables standard C++ modules even with C++23). They use `-x c++` for `.ixx` too:
clangd recognizes `export module` and builds interfaces, while the MinGW driver
can still answer include-path queries. GCC does not accept `-x c++-module`.

Validated with Apple clangd 21.0.0 (clang-2100.3.34.2). Module support is
experimental; first analysis can take tens of seconds while dependencies build.
No prebuilt GCC/MSVC module artifacts are used. Save module edits before expecting
dependent translation units to see them; restart clangd if dependent analysis
remains stale. Regenerate the databases when compilation flags or file lists change.

## Current validation and remaining diagnostics

The SA `Entity.ixx` check passes. A live language-server check of the original SA
`dllmain.cpp` resolves `CEntity` to `Entity.ixx` and completes `GetModelIndex()`.
It reports two diagnostics:

- `NOMINMAX` is defined both on the command line and in the source.
- `CSimpleTransform` needs a direct `import Placeable;` in SA's `dllmain.cpp`.
  The MinGW translation masks this dependency by including all module headers.

Checks of the other configurations found:

- III/VC: Clang rejects exporting `CVehicle` after an earlier declaration with
  module linkage in `Vehicle.ixx`. This prevents dependent modules from building.
- IV: Clang reports inconsistent definitions of libstdc++'s
  `std::__format::_Sink_iter` across module global fragments.

These diagnostics are not suppressed. The C++ sources are untouched; correcting
the source-level module declarations and investigating the IV Clang/libstdc++
interaction are separate follow-up work. This setup repairs module discovery,
not every source/toolchain compatibility issue.

To reproduce a check (after selecting the corresponding game):

```sh
/usr/bin/clangd --check=source/SALodLights/dllmain.cpp \
  --experimental-modules-support \
  --query-driver=/opt/homebrew/bin/i686-w64-mingw32-g++
```

`--check` also exercises editor refactoring actions; its final error count can
include failed actions that are not compiler diagnostics. Use the actual
diagnostics or the language-server results to distinguish them.
