#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <vector>
#include <map>
#include <set>
#include <algorithm>
#include <random>
#include <chrono>
#include <ctime>
#include <cmath>
#include <numbers>

#pragma warning(disable:4201)
#pragma warning(disable:4458)

#include "IniReader.h"

#include "injector/injector.hpp"
#include "injector/assembly.hpp"
#include "injector/calling.hpp"
#include "injector/hooking.hpp"
#include "injector/utility.hpp"

#include "Hooking.Patterns.h"

#include "gameref.hpp"
#include "callbacks.h"

#include "rw.h"

inline bool IsModuleUAL(HMODULE mod)
{
    if (GetProcAddress(mod, "IsUltimateASILoader") != NULL || (GetProcAddress(mod, "DirectInput8Create") != NULL && GetProcAddress(mod, "DirectSoundCreate8") != NULL && GetProcAddress(mod, "InternetOpenA") != NULL))
        return true;
    return false;
}

inline bool IsUALPresent()
{
    // MinGW's libstdc++ does not provide std::stacktrace on every toolchain.
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
