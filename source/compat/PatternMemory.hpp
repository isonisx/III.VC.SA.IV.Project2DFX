#pragma once
#include <windows.h>
#include <cstdint>
#include <limits>

// Cache the end of readable regions so pattern scanning only queries memory at
// region boundaries. Reject guard/uncommitted pages rather than triggering SEH.
inline bool PatternMemoryReadable(uintptr_t address, size_t size, uintptr_t& readableEnd)
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
