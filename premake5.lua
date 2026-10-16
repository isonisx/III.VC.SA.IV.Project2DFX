-- macOS host (including Apple Silicon), 32-bit Windows target:
--   brew install premake mingw-w64
--   git submodule update --init --recursive
--   premake5 gmake
--   make -C build config=release -j$(sysctl -n hw.logicalcpu)
-- Use config=debug for symbols, or append SALodLights to build only that plugin.
-- Outputs: build/bin/<Release|Debug>/<project>/<project>.asi (or .exe).
-- Rerun Premake after adding files, updating submodules, or editing .env; ordinary
-- source/header/module edits are picked up by make. Clean with make -C build clean.
-- Optional .env keys use macOS paths to a game inside a Wine/CrossOver bottle,
-- e.g. GTA_SAN_ANDREAS_DIR="/Users/me/Games/GTA San Andreas".
-- The Windows binaries must be run in the game (e.g. through Wine/CrossOver).
if os.host() ~= "macosx" then
   error("This build requires a macOS host.")
end
newoption { trigger = "prepare-project", value = "NAME", description = "Internal: regenerate a project's MinGW sources" }
newaction { trigger = "prepare", description = "Internal: regenerate MinGW compatibility sources", execute = function() end }
if _ACTION and _ACTION ~= "gmake" and _ACTION ~= "gmake2" and _ACTION ~= "prepare" then
   error("Use premake5 gmake to generate the MinGW makefiles.")
end
_OPTIONS["os"] = "windows"
if _ACTION ~= "prepare" then
   for _, tool in ipairs({ "i686-w64-mingw32-g++", "i686-w64-mingw32-windres", "iconv" }) do
      local _, status = os.outputof("command -v " .. tool)
      assert(status == 0, "Missing tool on PATH: " .. tool .. ". Install premake and mingw-w64 with Homebrew.")
   end
end

-- IniReader uses a Windows include separator. Normalize a build-local copy so
-- the pinned submodule stays untouched on a POSIX host.
os.mkdir("build/compat")
local function writeChanged(filename, text)
   if io.readfile(filename) == text then return end
   local f = assert(io.open(filename, "wb"))
   f:write(text)
   f:close()
end
if _ACTION ~= "prepare" then
   -- Fail visibly if a future submodule update invalidates a compatibility patch.
   local function replace(text, pattern, replacement, expected)
      local result, count = text:gsub(pattern, replacement)
      assert(count == (expected or 1), "Submodule compatibility patch no longer matches: " .. pattern)
      return result
   end
   local notice = "// Generated MinGW adaptation; original source and license are in external/.\n"
   local ini = assert(io.readfile("external/IniReader/IniReader.h"), "Run git submodule update --init --recursive first")
   ini = replace(ini, 'mINI\\src\\mini\\ini.h', 'mINI/src/mini/ini.h')
   writeChanged("build/compat/IniReader.h", notice .. ini)

   -- Make Facade's SFINAE depend on a function-template parameter, not just the
   -- enclosing class. GCC otherwise rejects array field wrappers at instantiation.
   local facade = assert(io.readfile("external/ModUtils/Facade.hpp"))
   facade = replace(facade, 'template<typename%.%.%. Args, typename = std::enable_if_t<!std::is_array_v<T>>>',
      'template<typename U = T, typename... Args, typename = std::enable_if_t<!std::is_array_v<U>>>', 2)
   writeChanged("build/compat/Facade.hpp", notice .. facade)

   -- windres expects UTF-8, while the original resources are UTF-16LE.
   for _, filename in ipairs({ "VersionInfo.rc", "VersionInfo.h" }) do
      local text, status = os.outputof('iconv -f UTF-16 -t UTF-8 "resources/' .. filename .. '"')
      assert(status == 0 and text ~= "", "Unable to convert resources/" .. filename)
      writeChanged("build/compat/" .. filename, text)
   end

   -- MinGW has no MSVC __try/__except. Stop scanning at unreadable regions using
   -- page protection checks; do not substitute C++ catch for access-violation SEH.
   local patterns = assert(io.readfile("external/hooking/Hooking.Patterns.cpp"))
   patterns = replace(patterns, '#define NOMINMAX', '#include "PatternMemory.hpp"')
   patterns = replace(patterns, "__try", "")
   patterns = replace(patterns, "__except %(%(GetExceptionCode%(%) == EXCEPTION_ACCESS_VIOLATION%) %? EXCEPTION_EXECUTE_HANDLER : EXCEPTION_CONTINUE_SEARCH%)%s*{%s*}", "")
   patterns = replace(patterns, "for %(uintptr_t i = executable.begin%(%)", "uintptr_t readableEnd = 0;\n\t\tfor (uintptr_t i = executable.begin()")
   patterns = replace(patterns, "uint8_t%* ptr = reinterpret_cast<uint8_t%*>%(i%);", "if (!PatternMemoryReadable(i, maskSize, readableEnd)) break;\n\t\t\tuint8_t* ptr = reinterpret_cast<uint8_t*>(i);")
   writeChanged("build/compat/Hooking.Patterns.cpp", notice .. patterns)
end

-- The folder a project is deployed to,
-- is the path of one machine and does not belong in the repository. It is read from a
-- `.env` file next to this script, which is not tracked by git and holds one
-- `<KEY>=<folder>` line per game (quotes and a trailing slash are optional). A project
-- whose key is missing is not deployed at all.
local envkeys = nil
function envdir(key)
   if not envkeys then
      envkeys = {}
      local text = io.readfile(path.join(_SCRIPT_DIR, ".env")) or ""
      for line in text:gmatch("[^\r\n]+") do
         local k, v = line:match("^%s*([%w_]+)%s*=%s*(.-)%s*$")
         if k and v ~= "" then
            v = v:gsub('^"', ""):gsub('"$', ""):gsub("^'", ""):gsub("'$", "")
            envkeys[k] = v
         end
      end
   end

   local value = envkeys[key]
   if not value then return nil end

   value = value:gsub("[%s\\/]+$", "")
   if value == "" then return nil end

   return path.getabsolute(value, _SCRIPT_DIR)
end

-- Deploys the built .asi into the script folder of the game that `key` names in the .env
-- file (a macOS filesystem path). Only a plugin that is already
-- installed in the game folder is replaced, a folder without one is left alone.
function setpaths(key, scriptspath)
   scriptspath = scriptspath or "scripts/"
   local gamepath = envdir(key)
   if gamepath then
      local target = path.join(gamepath, scriptspath)
      postbuildcommands {
         'if [ -f "' .. target .. '/%{cfg.buildtarget.name}" ]; then cp -f "%{cfg.buildtarget.abspath}" "' .. target .. '/"; fi',
      }
   end
end

workspace "III.VC.SA.IV.Project2DFX"
   configurations { "Release", "Debug" }
   system "windows"
   toolset "gcc"
   gccprefix "i686-w64-mingw32-"
   architecture "x86"
   location "build"
   objdir "build/mingw-obj/%{prj.name}/%{cfg.buildcfg}"
   cppdialect "C++23"
   buildoptions { "-fms-extensions" }
   linkoptions { "-static", "-static-libgcc", "-static-libstdc++" }
   links { "psapi", "shlwapi" }
   
   kind "SharedLib"
   language "C++"
   targetdir "build/bin/%{cfg.buildcfg}/%{prj.name}"
   targetprefix ""
   targetextension ".asi"
   characterset ("Unicode")
   staticruntime "On"

   local major = os.date("%d")
   local minor = os.date("%m")
   local build = os.date("%Y")
   local revision = os.date("%H") .. os.date("%M")

   local githash = ""
   local f = io.popen("git rev-parse --short HEAD")
   if f then
      githash = f:read("*a"):gsub("%s+", "")
      f:close()
   end

   local productVersion = major .. "." .. minor .. "." .. build .. "." .. revision
   if githash ~= "" then
      productVersion = productVersion .. "-" .. githash
   end

   defines { "_CRT_SECURE_NO_WARNINGS", "NOMINMAX", "UNICODE", "_UNICODE" }

   files { "source/%{prj.name}/*.h", "source/%{prj.name}/*.cpp" }
   files { "source/%{prj.name}/*.hpp", "source/%{prj.name}/*.ixx" }
   files { "source/*.hpp", "source/*.ixx" }
   files { "external/hooking/Hooking.Patterns.h", "build/compat/Hooking.Patterns.cpp" }
   files { "external/injector/safetyhook/include/**.hpp", "external/injector/safetyhook/src/**.cpp" }
   files { "external/injector/zydis/**.h", "external/injector/zydis/**.c" }
   files { "data/**/*.ini" }
   includedirs { "build/compat", "includes", "source/compat" }
   includedirs { "external/hooking" }
   includedirs { "external/injector/safetyhook/include" }
   includedirs { "external/injector/zydis" }
   includedirs { "external/injector/include" }
   includedirs { "external/IniReader" }
   includedirs { "external/filewatch" }
   includedirs { "external/ModUtils" }

   vpaths {
      ["source"] = { "source/**.*" },
      ["shaders"] = { "source/**.fx", "source/**.vs", "source/**.ps", "source/**.hlsl" },
      ["ini"] = { "data/**.ini" },
      ["data"] = { "data/**.cfg", "data/**.dat" },
      ["resources/*"] = { "resources/*" },
      ["includes/*"] = { "includes/**" },
      ["external/*"] = { "external/**" },
   }

   filter "configurations:Debug"
       defines { "DEBUG", "_DEBUG" }
      symbols "On"

   filter "configurations:Release"
       defines "NDEBUG"
       optimize "On"
   filter {}

-- GCC currently fails to merge libstdc++ declarations imported through these
-- modules. Generate ordinary, guarded headers and one translation unit per game.
-- The originals remain the source of truth; make regenerates on .ixx edits.
function modules(name, shared)
   if _OPTIONS["prepare-project"] and _OPTIONS["prepare-project"] ~= name then return end
   local sources = os.matchfiles("source/" .. name .. "/*.ixx")
   for _, source in ipairs(shared) do table.insert(sources, source) end
   local names = {}
   for _, source in ipairs(sources) do
      local text = io.readfile(source)
      local mod = text:match("export%s+module%s+([%w_]+)%s*;")
      assert(mod, "Missing module declaration: " .. source)
      names[mod] = source
   end
   local dir = path.getabsolute("build/compat/" .. name)
   os.mkdir(dir)
   local function translate(source)
      local text = assert(io.readfile(source))
      text = text:gsub("^\239\187\191", "")
      local lines = {}
      for line in (text .. "\n"):gmatch("([^\n]*)\n") do
         if line:match("^%s*module%s*;") or line:match("^%s*export%s+module%s+") then
            line = ""
         elseif line:match("^%s*export%s*$") or line:match("^%s*export%s*{") then
            line = line:gsub("export", "inline namespace Project2DFX_" .. path.getbasename(source), 1)
         else
            line = line:gsub("^(%s*)export%s+", "%1")
            line = line:gsub("^(%s*)import%s+([%w_]+)%s*;", function(indent, mod)
               assert(names[mod], "Unknown module " .. mod .. " in " .. source)
               return indent .. '#include "' .. dir .. '/' .. mod .. '.hpp"'
            end)
            line = line:gsub('^(%s*#include%s*")([^"\n]+)(")', function(prefix, include, suffix)
               local resolved = path.join(path.getdirectory(source), include)
               if os.isfile(resolved) then include = path.getabsolute(resolved) end
               return prefix .. include .. suffix
            end)
         end
         table.insert(lines, line)
      end
      return '#line 1 "' .. path.getabsolute(source) .. '"\n' .. table.concat(lines, "\n")
   end
   local headers = {}
   for mod, source in pairs(names) do
      writeChanged(dir .. '/' .. mod .. '.hpp', '#pragma once\n' .. translate(source))
      table.insert(headers, '#include "' .. dir .. '/' .. mod .. '.hpp"\n')
   end
   table.sort(headers)
   local inputs = table.join(sources, { "premake5.lua" })
   for _, source in ipairs(os.matchfiles("source/" .. name .. "/*.cpp")) do
      local generated = dir .. '/' .. path.getname(source)
      writeChanged(generated, '#include <stdafx.h>\n' .. table.concat(headers) .. translate(source))
      filter("files:" .. source)
         buildmessage("Compiling " .. name .. " (MinGW translation unit)")
         buildcommands {
            '"' .. _PREMAKE_COMMAND .. '" --file="' .. path.getabsolute("premake5.lua") .. '" --prepare-project=' .. name .. ' prepare',
            '$(CXX) $(ALL_CXXFLAGS) -MMD -MP -MF "%{cfg.objdir}/' .. path.getbasename(source) .. '.d" -c "' .. generated .. '" -o "%{cfg.objdir}/' .. path.getbasename(source) .. '.o"',
         }
         buildinputs(inputs)
         buildoutputs { "%{cfg.objdir}/" .. path.getbasename(source) .. ".o" }
         linkbuildoutputs "On"
      filter {}
   end
end

project "2DFXDataGrabber"
   kind "ConsoleApp"
   targetextension ".exe"
   characterset ("MBCS")
   undefines { "UNICODE", "_UNICODE" }
   removefiles { "source/*.hpp", "source/*.ixx" }
project "IIILodLights"
   modules("IIILodLights", os.matchfiles("source/*.ixx"))
   setpaths("GTAIII_DIR")
project "VCLodLights"
   modules("VCLodLights", os.matchfiles("source/*.ixx"))
   setpaths("GRAND_THEFT_AUTO_VICE_CITY_DIR")
project "SALodLights"
   modules("SALodLights", os.matchfiles("source/*.ixx"))
   setpaths("GTA_SAN_ANDREAS_DIR")
project "IVLodLights"
   removefiles { "source/*.hpp", "source/*.ixx" }
   files { "source/FileMgr.ixx", "source/LamppostInfo.ixx", "source/Timer.ixx" }
   -- the plugins of GTA IV are loaded from the plugins folder
   modules("IVLodLights", { "source/FileMgr.ixx", "source/LamppostInfo.ixx", "source/Timer.ixx" })
   setpaths("GTA_IV_DIR", "plugins/")

-- Console projects use the Windows SDK toolchains, not MinGW. Their standalone
-- Visual Studio entry point is premake5-consoles.lua.

-- Put resource string macros in a source file, avoiding windres' second round of
-- shell parsing of -D values (which otherwise loses embedded string quotes).
for _, name in ipairs({ "2DFXDataGrabber", "IIILodLights", "VCLodLights", "SALodLights", "IVLodLights" }) do
   project(name)
   local ext = name == "2DFXDataGrabber" and ".exe" or ".asi"
   local values = {
      rsc_CompanyName = '"ThirteenAG"', rsc_LegalCopyright = '"MIT License"',
      rsc_InternalName = '"' .. name .. '"', rsc_ProductName = '"' .. name .. '"',
      rsc_OriginalFilename = '"' .. name .. ext .. '"',
      rsc_FileDescription = '"https://thirteenag.github.io/p2dfx"',
      rsc_UpdateUrl = '"https://github.com/ThirteenAG/III.VC.SA.IV.Project2DFX"',
      rsc_FileVersion_MAJOR = tonumber(major), rsc_FileVersion_MINOR = tonumber(minor),
      rsc_FileVersion_BUILD = tonumber(build), rsc_FileVersion_REVISION = tonumber(revision),
      rsc_FileVersion = '"' .. major .. '.' .. minor .. '.' .. build .. '"',
      rsc_ProductVersion = '"' .. productVersion .. '"', rsc_GitSHA1 = '"' .. githash .. '"',
   }
   local lines = {}
   for key, value in pairs(values) do table.insert(lines, '#define ' .. key .. ' ' .. value .. '\n') end
   table.sort(lines)
   local rc = "build/compat/" .. name .. ".rc"
   if _ACTION ~= "prepare" then
      writeChanged(rc, table.concat(lines) .. '#include "VersionInfo.rc"\n')
   end
   files { rc }
   filter("files:" .. rc)
      buildcommands { '$(RESCOMP) "%{file.abspath}" -I../build/compat %{cfg.buildcfg == "Debug" and "-D_DEBUG" or ""} -O coff -o "%{cfg.objdir}/VersionInfo.o"' }
      buildinputs { "build/compat/VersionInfo.rc", "build/compat/VersionInfo.h" }
      buildoutputs { "%{cfg.objdir}/VersionInfo.o" }
      linkbuildoutputs "On"
   filter {}
end
