#!/usr/bin/env python3
"""Generate SALodLights MinGW inputs under build/mingw. Does not modify sources."""

import hashlib
import re
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "build" / "mingw" / "gen"
HEX = Path(__file__).resolve().parent / "LightVolumes.cso.hex"
SOURCE_SHA256 = "fc198b03f1bd85d2a1e9bd850a58d0b9b603e4fd00cf404ac322ad886f8e8931"
BYTECODE_SHA256 = "a79ae1064339c7c91f390ce3cd28a69ba4b457b7d47ba3f8bd899adc39127b11"

MODULE_RE = re.compile(r"^\s*export\s+module\s+(\w+)\s*;\s*$")
IMPORT_RE = re.compile(r"^\s*import\s+(\w+)\s*;\s*$")
INCLUDE_RE = re.compile(r'^(\s*#include\s*")([^"]+)(".*)$')


def write_if_changed(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else None
    if existing != text:
        path.write_text(text, encoding="utf-8", newline="\n")


def replace_count(text: str, old: str, new: str, label: str, expected: int) -> str:
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{label} no longer matches ({count} occurrences, expected {expected})")
    return text.replace(old, new)


def flatten(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    module = next((match.group(1) for line in text.splitlines() if (match := MODULE_RE.match(line))), path.stem)
    raw = text.splitlines()
    lines = []
    index = 0
    while index < len(raw):
        line = raw[index]
        if re.match(r"\s*module\s*;\s*$", line) or MODULE_RE.match(line) or IMPORT_RE.match(line):
            line = ""
        elif re.match(r"\s*export\s*$", line):
            nxt = index + 1
            while nxt < len(raw) and raw[nxt].strip() == "":
                nxt += 1
            if nxt < len(raw) and raw[nxt].strip() == "{":
                lines.append(f"inline namespace flattened_{module}")
                lines.append("{")
                index = nxt + 1
                continue
            line = ""
        else:
            opened = re.match(r"^(\s*)export\s*\{\s*$", line)
            if opened:
                lines.append(f"{opened.group(1)}inline namespace flattened_{module}")
                lines.append(f"{opened.group(1)}{{")
                index += 1
                continue
            line = re.sub(r"^(\s*)export\b\s*", r"\1", line, count=1)
            included = INCLUDE_RE.match(line)
            if included:
                target = (path.parent / included.group(2)).resolve()
                if target.is_file():
                    line = f'{included.group(1)}{target.as_posix()}{included.group(3)}'
        lines.append(line)
        index += 1
    return f'#line 1 "{path.resolve().as_posix()}"\n' + "\n".join(lines) + "\n"


def module_sources() -> list[Path]:
    return sorted((ROOT / "source").glob("*.ixx")) + sorted((ROOT / "source" / "SALodLights").glob("*.ixx"))


def ordered_modules() -> list[Path]:
    files = {}
    imports = {}
    for path in module_sources():
        text = path.read_text(encoding="utf-8-sig")
        name = next((match.group(1) for line in text.splitlines() if (match := MODULE_RE.match(line))), None)
        if not name:
            raise SystemExit(f"Missing module declaration: {path}")
        if name in files:
            raise SystemExit(f"Duplicate module {name}: {files[name]} and {path}")
        files[name] = path
        imports[name] = [match.group(1) for line in text.splitlines() if (match := IMPORT_RE.match(line))]
    for name, deps in imports.items():
        missing = [dep for dep in deps if dep not in files]
        if missing:
            raise SystemExit(f"{name} imports unknown modules: {', '.join(missing)}")
    pending = set(files)
    ordered = []
    while pending:
        ready = sorted(name for name in pending if all(dep not in pending for dep in imports[name]))
        if not ready:
            raise SystemExit("Cyclic module imports: " + ", ".join(sorted(pending)))
        pending.difference_update(ready)
        ordered.extend(files[name] for name in ready)
    return ordered


def shader_header() -> str:
    source = (ROOT / "source" / "LightVolumes.ps").read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise SystemExit("source/LightVolumes.ps changed; update mingw/LightVolumes.cso.hex from an fxc ps_3_0 /O3 build")
    bytecode = bytes.fromhex(HEX.read_text(encoding="ascii"))
    if hashlib.sha256(bytecode).hexdigest() != BYTECODE_SHA256 or len(bytecode) != 2080:
        raise SystemExit("mingw/LightVolumes.cso.hex does not match the SALodLights ps_3_0 bytecode")
    rows = []
    for offset in range(0, len(bytecode), 16):
        rows.append("    " + ", ".join(f"0x{byte:02x}" for byte in bytecode[offset:offset + 16]) + ",")
    return (
        "// ps_3_0 bytecode for source/LightVolumes.ps at 7eedd5f. fxc is not available on macOS.\n"
        "#pragma once\n"
        "alignas(4) inline constexpr unsigned char LightVolumesShader[] = {\n"
        + "\n".join(rows)
        + "\n};\n"
    )


def compat_headers() -> None:
    stdafx = (ROOT / "includes" / "stdafx.h").read_text(encoding="utf-8")
    stdafx = replace_count(stdafx, '#include <stacktrace>\n', "", "stdafx.h stacktrace include", 1)
    stdafx = replace_count(stdafx, "injector\\", "injector/", "stdafx.h injector include", 5)
    stdafx = replace_count(
        stdafx,
        """inline bool IsUALPresent()
{
    for (const auto& entry : std::stacktrace::current())
    {
        HMODULE hModule = NULL;
        if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCSTR)entry.native_handle(), &hModule))
        {
            if (IsModuleUAL(hModule))
                return true;
        }
    }
    return false;
}""",
        """inline bool IsUALPresent()
{
    // This MinGW libstdc++ declares std::stacktrace but does not ship its implementation.
    void* frames[64];
    const auto count = CaptureStackBackTrace(0, 64, frames, nullptr);
    for (USHORT i = 0; i < count; ++i)
    {
        HMODULE hModule = NULL;
        if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCSTR)frames[i], &hModule))
        {
            if (IsModuleUAL(hModule))
                return true;
        }
    }
    return false;
}
""",
        "stdafx.h IsUALPresent",
        1,
    )
    write_if_changed(GEN / "stdafx.h", stdafx)

    ini = (ROOT / "external" / "IniReader" / "IniReader.h").read_text(encoding="utf-8")
    ini = replace_count(ini, "mINI\\src\\mini\\ini.h", "mINI/src/mini/ini.h", "IniReader.h include", 1)
    write_if_changed(GEN / "IniReader.h", ini)

    gameref = (ROOT / "external" / "FusionFixUtils" / "include" / "gameref.hpp").read_text(encoding="utf-8")
    gameref = replace_count(gameref, "injector\\injector.hpp", "injector/injector.hpp", "gameref.hpp include", 1)
    write_if_changed(GEN / "gameref.hpp", gameref)

    callbacks = (ROOT / "external" / "FusionFixUtils" / "include" / "callbacks.h").read_text(encoding="utf-8")
    # GCC parses earlier member definitions before it can deduce these auto returns.
    for name, result in {
        "GetOnModuleLoadCallbackList": "std::map<std::wstring, std::function<void()>, Comparator>&",
        "GetOnModuleUnloadCallbackList": "std::map<std::wstring, std::function<void()>, Comparator>&",
        "GetOnAnyModuleLoadCallbackList": "std::vector<std::function<void(HMODULE)>>&",
        "GetOnAnyModuleUnloadCallbackList": "std::vector<std::function<void(std::wstring_view)>>&",
        "GetCallbackParamsList": "std::vector<ThreadParams>&",
        "GetCallbackParamsMutex": "std::recursive_mutex&",
    }.items():
        callbacks = replace_count(
            callbacks,
            f"static inline auto& {name}()",
            f"static inline {result} {name}()",
            f"callbacks.h {name}",
            1,
        )
    callbacks = replace_count(
        callbacks,
        "LdrRegisterDllNotification(0, LdrDllNotification,",
        "LdrRegisterDllNotification(0, reinterpret_cast<PVOID>(LdrDllNotification),",
        "callbacks.h function-pointer conversion",
        1,
    )
    write_if_changed(GEN / "callbacks.h", callbacks)


def patterns() -> None:
    text = (ROOT / "external" / "hooking" / "Hooking.Patterns.cpp").read_text(encoding="utf-8")
    helper = """#include <cstdint>
#include <limits>
// MinGW has no MSVC __try/__except. Stop at an unreadable page instead of catching an access violation.
static bool PatternMemoryReadable(uintptr_t address, size_t size, uintptr_t& readableEnd)
{
    if (size > std::numeric_limits<uintptr_t>::max() - address)
        return false;
    const auto end = address + size;
    while (end > readableEnd)
    {
        MEMORY_BASIC_INFORMATION info{};
        const auto probe = address > readableEnd ? address : readableEnd;
        if (!VirtualQuery(reinterpret_cast<void*>(probe), &info, sizeof(info)) ||
            info.State != MEM_COMMIT || (info.Protect & (PAGE_GUARD | PAGE_NOACCESS)) ||
            !(info.Protect & (PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY |
                              PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY)))
            return false;
        const auto next = reinterpret_cast<uintptr_t>(info.BaseAddress) + info.RegionSize;
        if (next <= probe)
            return false;
        readableEnd = next;
    }
    return true;
}

"""
    text = replace_count(text, "#include <Windows.h>\n", "#include <Windows.h>\n" + helper, "Hooking.Patterns.cpp include", 1)
    text = replace_count(
        text,
        """\t__try
\t{
\t\tfor (uintptr_t i = executable.begin(), end = executable.end() - maskSize; i <= end;)
\t\t{
\t\t\tuint8_t* ptr = reinterpret_cast<uint8_t*>(i);""",
        """\t\tuintptr_t readableEnd = 0;
\t\tfor (uintptr_t i = executable.begin(), end = executable.end() - maskSize; i <= end;)
\t\t{
\t\t\tif (!PatternMemoryReadable(i, maskSize, readableEnd)) break;
\t\t\tuint8_t* ptr = reinterpret_cast<uint8_t*>(i);""",
        "Hooking.Patterns.cpp __try",
        1,
    )
    text = replace_count(
        text,
        """\t\t}
\t}
\t__except ((GetExceptionCode() == EXCEPTION_ACCESS_VIOLATION) ? EXCEPTION_EXECUTE_HANDLER : EXCEPTION_CONTINUE_SEARCH)
\t{
\t}
""",
        "\t\t}\n",
        "Hooking.Patterns.cpp __except",
        1,
    )
    write_if_changed(GEN / "Hooking.Patterns.cpp", text)


def resources() -> None:
    rc_dir = GEN / "rc"
    for name in ("VersionInfo.rc", "VersionInfo.h"):
        write_if_changed(rc_dir / name, (ROOT / "resources" / name).read_text(encoding="utf-16"))
    now = datetime.now()
    revision = now.hour * 100 + now.minute
    try:
        githash = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        githash = ""
    product = f"{now.day}.{now.month}.{now.year}.{revision}"
    if githash:
        product += f"-{githash}"
    defines = {
        "rsc_CompanyName": '"ThirteenAG"',
        "rsc_LegalCopyright": '"MIT License"',
        "rsc_InternalName": '"SALodLights"',
        "rsc_ProductName": '"SALodLights"',
        "rsc_OriginalFilename": '"SALodLights.asi"',
        "rsc_FileDescription": '"https://thirteenag.github.io/p2dfx"',
        "rsc_UpdateUrl": '"https://github.com/ThirteenAG/III.VC.SA.IV.Project2DFX"',
        "rsc_FileVersion_MAJOR": str(now.day),
        "rsc_FileVersion_MINOR": str(now.month),
        "rsc_FileVersion_BUILD": str(now.year),
        "rsc_FileVersion_REVISION": str(revision),
        "rsc_FileVersion": f'"{now.day}.{now.month}.{now.year}"',
        "rsc_ProductVersion": f'"{product}"',
        "rsc_GitSHA1": f'"{githash}"',
    }
    lines = [f"#define {key} {value}" for key, value in defines.items()]
    lines.append('#include "VersionInfo.rc"')
    settings = ROOT / "source" / "SALodLights" / "Settings.rc"
    for line in settings.read_text(encoding="utf-8").splitlines():
        match = re.match(r'^(\S+)\s+(\S+)\s+"([^"]+)"\s*$', line)
        if not match:
            continue
        name, kind, relative = match.groups()
        path = (settings.parent / relative).resolve()
        if not path.is_file():
            raise SystemExit(f"Missing settings resource: {path}")
        lines.append(f'{name} {kind} "{path.as_posix()}"')
    write_if_changed(rc_dir / "SALodLights.rc", "\n".join(lines) + "\n")


def main() -> None:
    parts = [flatten(path) for path in ordered_modules()]
    parts.append(flatten(ROOT / "source" / "SALodLights" / "dllmain.cpp"))
    write_if_changed(GEN / "SALodLights.cpp", "\n".join(parts))
    write_if_changed(GEN / "LightVolumesShader.hpp", shader_header())
    compat_headers()
    patterns()
    resources()


if __name__ == "__main__":
    main()
