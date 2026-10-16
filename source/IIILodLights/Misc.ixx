module;

#include <stdafx.h>
#include "rw.h"

export module Misc;

import Entity;
import ComVars;
export import Physical;

using RwV3D = RwV3d;

export enum SShadType
{
    SSHADT_NONE,
    SSHADT_DEFAULT,		// SSHAD_RM_COLORONLY (shad_car, shad_ped, shad_heli, shad_bike, shad_rcbaron, bloodpool_64, wincrack_32, lamp_shad_64)
    SSHADT_INTENSIVE,	// SSHAD_RM_OVERLAP (shad_exp, headlight, headlight1, handman)
    SSHADT_NEGATIVE,	// SSHAD_RM_INVCOLOR
    SSHADT4,			// SSHAD_RM_COLORONLY
    SSHADT5,			// SSHAD_RM_COLORONLY
    SSHADT6,			// SSHAD_RM_COLORONLY
    SSHADT8 = 8			// SSHAD_RM_COLORONLY
};

export enum SShadRenderMode
{
    SSHAD_RM_NONE,		// Shadow type: <0, 0, >8.
    SSHAD_RM_COLORONLY, // Shadow type: 1, 4, 5, 6, 8. The texture alpha is present if the alpha channel is set.
    SSHAD_RM_OVERLAP,	// Shadow type: 2. Any shadow alpha greater than 0 does not make any difference.
    SSHAD_RM_INVCOLOR	// Shadow type: 3. Same tip above goes here.
};

export struct RxObjSpace3dVertex	// sizeof = 0x24
{
    RwV3D objVertex;
    RwV3D objNormal;
    DWORD color;
    float u;
    float v;
};

export class CObjectInfo
{
public:
    float m_fMass;
    float m_fTurnMass;
    float m_fAirResistance;
    float m_fElasticity;
    float m_fBuoyancy;
    float m_fUprootLimit;
    float m_fCollisionDamageMultiplier;
    uint8_t m_nCollisionDamageEffect;
    uint8_t m_nSpecialCollisionResponseCases;
    bool m_bCameraToAvoidThisObject;
};

export class CObject : public CPhysical
{
public:
    CMatrix m_objectMatrix;
    float m_fUprootLimit;
    int8_t ObjectCreatedBy;
    int8_t bIsPickup : 1;
    int8_t bPickupObjWithMessage : 1;
    int8_t bOutOfStock : 1;
    int8_t bGlassCracked : 1;
    int8_t bGlassBroken : 1;
    int8_t bHasBeenDamaged : 1;
    int8_t bUseVehicleColours : 1;
    int8_t m_nBonusValue;
    float m_fCollisionDamageMultiplier;
    uint8_t m_nCollisionDamageEffect;
    uint8_t m_nSpecialCollisionResponseCases;
    bool m_bCameraToAvoidThisObject;
    uint32_t m_obj_unused1;
    uint32_t m_nEndOfLifeTime;
    int16_t m_nRefModelIndex;
    CEntity* m_pCurSurface;
    CEntity* m_pCollidingEntity;
    int8_t m_colour1, m_colour2;
};

export namespace CWeather
{
    GameRef<float> Rain;
    GameRef<float> Foggyness;
}

export namespace CDraw
{
    GameRef<float> ms_fNearClipZ;
    GameRef<float> ms_fFarClipZ;
}

export namespace CSprite
{
    GameRef<float> m_f2DNearScreenZ;
    GameRef<float> m_f2DFarScreenZ;
}

export RwTexture** gpCoronaTexture;

export GameRef<CScene> Scene;

export GameRef<RwGlobals*> RwEngineInstance;

export bool(__cdecl* RwRenderStateGet)(RwRenderState nState, void* pParam) = nullptr;
export bool(__cdecl* RwRenderStateSet)(RwRenderState nState, void* pParam) = nullptr;

export struct RsGlobalType
{
    const char* appName;
    std::int32_t  width;
    std::int32_t  height;
    std::int32_t  maximumWidth;
    std::int32_t  maximumHeight;
    std::int32_t  maxFPS;
    bool          quit;
    void* ps;
    RsInputDevice keyboard;
    RsInputDevice mouse;
    RsInputDevice pad;
};

export GameRef<RsGlobalType> RsGlobal([]() -> RsGlobalType*
    {
        auto pattern = hook::pattern("8B 0D ? ? ? ? 6A ? 6A ? 52");
        if (!pattern.empty())
            return *pattern.get_first<RsGlobalType*>(2);
        return nullptr;
    });

export namespace CRenderer
{
    GameRef<float> ms_lodDistScale;
}

export namespace CShadows
{
    RwTexture** gpShadowExplosionTex = nullptr;
    bool(__cdecl* StoreStaticShadow)(unsigned int id, unsigned char type, RwTexture* particle, CVector* pos, float x1, float y1, float x2, float y2, short alpha, unsigned char red, unsigned char green, unsigned char blue, float, float, float drawdist, bool lifetime, float updist) = nullptr;
}

export namespace CGeneral
{
    constexpr int MYRAND_MAX = 65535;

    unsigned int __cdecl GetRandomNumber()
    {
        return rand();
    }

    float GetRandomNumberInRange(float low, float high)
    {
        return low + (high - low) * (CGeneral::GetRandomNumber() / float(MYRAND_MAX + 1));
    }

    int32_t GetRandomNumberInRange(int32_t low, int32_t high)
    {
        return low + (high - low) * (CGeneral::GetRandomNumber() / float(MYRAND_MAX + 1));
    }
}

export namespace CStats
{
    GameRef<int> IndustrialPassed;
}
