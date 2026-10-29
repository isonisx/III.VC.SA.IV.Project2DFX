#!/usr/bin/env python3
"""Write a clangd database for the original SALodLights sources. Editor-only."""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "build" / "mingw" / "gen"
OUT = ROOT / "build" / "clangd"


def compiler() -> str:
    path = shutil.which("i686-w64-mingw32-g++")
    if not path:
        raise SystemExit("i686-w64-mingw32-g++ is not on PATH")
    return path


def overlay() -> list[str]:
    original = ROOT / "external" / "FusionFixUtils" / "asi_settings" / "asi_settings_json.hpp"
    text = original.read_text(encoding="utf-8")
    # Clang instantiates pair<string, Value> before Value's implicit members are complete.
    declarations = """        Value();
        ~Value();
        Value(const Value&);
        Value(Value&&) noexcept;
        Value& operator=(const Value&);
        Value& operator=(Value&&) noexcept;

"""
    definitions = """    inline Value::Value() = default;
    inline Value::~Value() = default;
    inline Value::Value(const Value&) = default;
    inline Value::Value(Value&&) noexcept = default;
    inline Value& Value::operator=(const Value&) = default;
    inline Value& Value::operator=(Value&&) noexcept = default;

"""
    for marker, insertion in (("        enum class Kind", declarations), ("    struct Error", definitions)):
        if text.count(marker) != 1:
            raise SystemExit("ASI Settings clangd patch no longer matches " + marker)
        text = text.replace(marker, insertion + marker, 1)
    patched = OUT / "asi_settings_json.hpp"
    patched.write_text(text, encoding="utf-8")
    overlay_path = OUT / "headers.json"
    overlay_path.write_text(json.dumps({
        "version": 0,
        "roots": [{"type": "file", "name": str(original), "external-contents": str(patched)}],
    }, indent=2) + "\n", encoding="utf-8")
    return ["-ivfsoverlay", str(overlay_path)]


def sources() -> list[Path]:
    files = []
    for pattern in ("*.cpp", "*.hpp", "*.ixx"):
        files += sorted((ROOT / "source" / "SALodLights").glob(pattern))
        if pattern != "*.cpp":
            files += sorted((ROOT / "source").glob(pattern))
    files.append(GEN / "Hooking.Patterns.cpp")
    files += sorted((ROOT / "external" / "injector" / "safetyhook" / "src").glob("*.cpp"))
    return files


def main() -> None:
    if not (GEN / "stdafx.h").is_file():
        raise SystemExit("Run mingw/prepare.py first")
    OUT.mkdir(parents=True, exist_ok=True)
    includes = [
        GEN, ROOT / "includes", ROOT / "source", ROOT / "source" / "SALodLights",
        ROOT / "external" / "FusionFixUtils" / "include", ROOT / "external" / "FusionFixUtils",
        ROOT / "external" / "hooking", ROOT / "external" / "injector" / "safetyhook" / "include",
        ROOT / "external" / "injector" / "zydis", ROOT / "external" / "injector" / "include",
        ROOT / "external" / "IniReader", ROOT / "external" / "ModUtils",
    ]
    flags = [
        "-std=c++23", "-msse2", "-mfpmath=sse", "-fms-extensions", "-Wno-unknown-pragmas",
        "-D_CRT_SECURE_NO_WARNINGS", "-DNOMINMAX", "-DUNICODE", "-D_UNICODE",
        "-g", "-O0", "-DDEBUG", "-D_DEBUG",
        *(f"-I{path}" for path in includes),
        *overlay(),
        "-fcxx-modules",
    ]
    gxx = compiler()
    entries = [{
        "directory": str(ROOT),
        "file": str(source),
        "arguments": [gxx, *flags, "-x", "c++", "-c", str(source)],
    } for source in sources()]
    zydis = ROOT / "external" / "injector" / "zydis" / "Zydis.c"
    entries.append({
        "directory": str(ROOT),
        "file": str(zydis),
        "arguments": [gxx, "-g", "-O0", "-DDEBUG", "-D_DEBUG", f"-I{ROOT / 'external' / 'injector' / 'zydis'}", "-x", "c", "-c", str(zydis)],
    })
    (OUT / "compile_commands.json").write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"clangd: {len(entries)} commands → {OUT / 'compile_commands.json'}")


if __name__ == "__main__":
    main()
