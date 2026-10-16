-- Windows console SDK builds: premake5 --file=premake5-consoles.lua vs2022
-- The macOS MinGW PC build uses premake5.lua instead.
require "vstudio"
premake.vstudio.vs2010_architectures.ps2 = "PS2"
premake.vstudio.vs2010_architectures.psp = "PSP"
premake.api.addAllowed("system", { "ps2", "psp" })

local envkeys = {}
for line in (io.readfile(path.join(_SCRIPT_DIR, ".env")) or ""):gmatch("[^\r\n]+") do
   local k, v = line:match("^%s*([%w_]+)%s*=%s*(.-)%s*$")
   if k and v ~= "" then
      envkeys[k] = v:gsub('^"', ""):gsub('"$', ""):gsub("^'", ""):gsub("'$", "")
   end
end
local function envdir(key)
   local value = envkeys[key]
   if not value then return nil end
   value = value:gsub("[%s\\/]+$", "")
   if value == "" then return nil end
   return path.getabsolute(value, _SCRIPT_DIR)
end

-- MIPS modules built by the SDK submodules from source/console/<name>/module.json.
function ConsoleSetup(name, platform)
   workspace (name)
      configurations { "Release", "Debug" }
      platforms { platform }
      system (platform:lower())
      bindirs { "$(PATH)" }
      location "build"
      kind "Makefile"
      language "C++"
      includedirs { "external/injector/include" }
      files { "source/console/%{prj.name}/*.h", "source/console/%{prj.name}/*.hpp", "source/console/%{prj.name}/*.c",
              "source/console/%{prj.name}/*.cpp", "source/console/%{prj.name}/module.json", "source/console/%{prj.name}/*.exp",
              "source/console/shared/**.hpp", "data/%{prj.name}/**.ini" }
      filter "configurations:Debug"
         defines { "DEBUG" }
      filter "configurations:Release"
         defines { "NDEBUG" }
      filter {}
end

function consolepaths(sdk, key, output, exepath)
   local manifest = '"%{wks.location}/../source/console/%{prj.name}/module.json"'
   local command = 'powershell -NoProfile -ExecutionPolicy Bypass -File "%{wks.location}/../external/' .. sdk .. '/plugins/build-module.ps1" -Project ' .. manifest
   if sdk == "pspsdk" then
      command = command .. ' -Configuration "%{cfg.buildcfg}"'
   end
   local gamepath = envdir(key)
   local deploy = {}
   if gamepath then
      local target = gamepath .. "\\" .. path.translate(path.getdirectory(output))
      deploy = { 'if not exist "' .. target .. '" mkdir "' .. target .. '"',
         'copy /y "$(NMakeOutput)" "' .. target .. '"' }
      debugdir (gamepath)
      debugcommand (gamepath .. "\\" .. exepath)
   end
   buildcommands { command, 'if errorlevel 1 exit /b %errorlevel%', deploy }
   rebuildcommands { command .. ' -Clean', 'if errorlevel 1 exit /b %errorlevel%', command,
      'if errorlevel 1 exit /b %errorlevel%', deploy }
   cleancommands { command .. ' -Clean' }
   targetdir ("data/%{prj.name}/" .. path.getdirectory(output))
   targetname (path.getbasename(output))
   targetextension (path.getextension(output))
end

ConsoleSetup("Project2DFX.PS2", "PS2")
   includedirs { "external/ps2sdk/ps2sdk/ee" }
project "GTAVCS.PCSX2F.Project2DFX"
   consolepaths("ps2sdk", "PCSX2F_DIR", "PLUGINS/GTAVCS.PCSX2F.Project2DFX.elf", "pcsx2-qtx64.exe")
project "GTALCS.PCSX2F.Project2DFX"
   consolepaths("ps2sdk", "PCSX2F_DIR", "PLUGINS/GTALCS.PCSX2F.Project2DFX.elf", "pcsx2-qtx64.exe")

ConsoleSetup("Project2DFX.PSP", "PSP")
   includedirs { "external/pspsdk/usr/local/pspdev/psp/sdk/include" }
project "GTAVCS.PPSSPP.Project2DFX"
   consolepaths("pspsdk", "PPSSPP_DIR", "memstick/PSP/PLUGINS/GTAVCS.PPSSPP.Project2DFX/GTAVCS.PPSSPP.Project2DFX.prx", "PPSSPPWindows64.exe")
project "GTALCS.PPSSPP.Project2DFX"
   consolepaths("pspsdk", "PPSSPP_DIR", "memstick/PSP/PLUGINS/GTALCS.PPSSPP.Project2DFX/GTALCS.PPSSPP.Project2DFX.prx", "PPSSPPWindows64.exe")
