#!/usr/bin/env python3
"""Describe original C++ modules to clangd, independently of the MinGW build."""

import argparse
import json
from pathlib import Path
import shutil

PROJECTS = ("IIILodLights", "VCLodLights", "SALodLights", "IVLodLights")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", choices=PROJECTS, default="SALodLights")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        database = json.loads((root / "compile_commands.json").read_text())
    except (OSError, ValueError) as error:
        parser.error(f"Generate the MinGW compilation database first (build.sh): {error}")
    generated = root / "build" / "compat" / args.project / "dllmain.cpp"
    template = next((entry for entry in database
                     if (Path(entry["directory"]) / entry["file"]).resolve() == generated), None)
    if template is None:
        parser.error(f"No MinGW command for {generated}; regenerate with build.sh")
    flags = []
    skip = False
    for arg in template["arguments"][1:]:
        if skip:
            skip = False
            continue
        if arg in ("-o", "-MF", "-MT", "-MQ"):
            skip = True
        elif arg not in ("-MD", "-MMD", "-MP", "-c") and (Path(template["directory"]) / arg).resolve() != generated:
            flags.append(arg)
    compiler = shutil.which(template["arguments"][0])
    if not compiler:
        parser.error("MinGW compiler is not on PATH")
    sources = sorted((root / "source" / args.project).glob("*.cpp"))
    sources += sorted((root / "source" / args.project).glob("*.ixx"))
    if args.project == "IVLodLights":
        sources += [root / "source" / name for name in ("FileMgr.ixx", "LamppostInfo.ixx", "Timer.ixx")]
    else:
        sources += sorted((root / "source").glob("*.ixx"))
    output = root / "build" / "clangd" / "compile_commands.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    # Keep directly compiled sources (third-party libraries and DataGrabber).
    # Exclude all translated game units to avoid indexing two representations.
    entries = []
    seen = set()
    game_dirs = {root / "build" / "compat" / project for project in PROJECTS}
    for entry in database:
        source = (Path(entry["directory"]) / entry["file"]).resolve()
        if source.parent not in game_dirs and source not in seen:
            entries.append(entry)
            seen.add(source)
    for source in sources:
        # Explicit C++ handles .ixx without asking GCC to query an unsupported
        # c++-module language. clangd recognizes `export module` in the source
        # and builds the module interface itself. Apple disables this language
        # feature by default even with -std=c++23, hence -fcxx-modules.
        language = "c++"
        entries.append({"directory": template["directory"], "file": str(source),
                        "arguments": [compiler, *flags, "-fcxx-modules", "-x", language, "-c", str(source)]})
    output.write_text(json.dumps(entries, indent=2) + "\n")
    print(f"clangd: {args.project} (Debug), {len(sources)} original source/module commands → {output}")


if __name__ == "__main__":
    main()
