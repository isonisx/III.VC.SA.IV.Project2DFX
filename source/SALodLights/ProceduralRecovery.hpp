// Procedural tracking-entry recovery, moved from Open Limit Adjuster.
// Licensed under the MIT License.
#pragma once
#include <cstdint>

namespace ProceduralRecovery
{
    struct ObjectEntry
    {
        ObjectEntry *prev, *next;
        void* object;
        void* triangle;
        bool allocatedMatrix;
    };

    struct ObjectList
    {
        ObjectEntry *head, *tail;
        uint32_t count;

        void Add(ObjectEntry& item)
        {
            item.prev = nullptr;
            item.next = head;
            if (head) head->prev = &item;
            else tail = &item;
            head = &item;
            ++count;
        }
    };

    struct SurfaceInfo
    {
        uint8_t properties[0x3C];
        ObjectList objects;
    };

    struct AllocationSnapshot
    {
        ObjectEntry *head, *next;
        uint32_t count;

        explicit AllocationSnapshot(const ObjectList& list)
            : head(list.head), next(head ? head->next : nullptr), count(list.count)
        {}

        void RecoverFailure(ObjectList& list, const SurfaceInfo& surface) const
        {
            // AddObject can pop an entry before rejecting creation. Recover
            // only that single unowned entry; do not duplicate another fix.
            if (head && count && list.count == count - 1 && list.head == next &&
                !head->object && surface.objects.head != head)
            {
                *head = {};
                list.Add(*head);
            }
        }
    };
}
