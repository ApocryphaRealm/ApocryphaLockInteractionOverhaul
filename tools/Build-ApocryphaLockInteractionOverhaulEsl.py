#!/usr/bin/env python3
r"""
Build-ApocryphaLockInteractionOverhaulEsl.py - authors LockInteractionOverhaul.esp, the carrier for the unlock
spell. Two NEW records, one master (Skyrim.esm), light-flagged, no vanilla overrides, no scripts:

    0x800  MGEF  ALO_ManipulateLockEffect   Script-archetype effect with NO script: aimed, fire-and-forget,
                                            Alteration, the vanilla Paralyze projectile so it can hit a chest
    0x801  SPEL  ALO_ManipulateLock         the spell "Manipulate Lock" (DLL contract: LookupForm(0x801, "LockInteractionOverhaul.esp"))

Everything the spell DOES lives in ApocryphaLockInteractionOverhaul.dll (it watches TESHitEvent for its own
spell); the plugin only has to make the spell exist. Byte-level writer on the primitives proven by
this project's earlier plugin builders (Potion of Clarity); every vanilla FormID below was read out
of the live Skyrim.esm by EDID on 2026-09-06, not guessed. The MGEF DATA layout was copied from
the vanilla ParalysisFFAimed effect (0x0001EA6E) and re-pointed.

Usage:  python Build-ApocryphaLockInteractionOverhaulEsl.py [out.esl]
"""
import struct, sys, os

FORM_VER = 44
NEW_MGEF = 0x01000800
NEW_SPEL = 0x01000801

# --- vanilla references (Skyrim.esm, scanned by EDID 2026-09-06) ---
PROJ_ParalyzeProjectile   = 0x0006EBC8
EQUP_EitherHand           = 0x00013F44
KYWD_MagicSchoolAlteration = 0x001076F1
ARTO_CastingArt_Paralyze  = 0x0006DE85   # the vanilla Paralyze casting art, borrowed for a visual
ARTO_HitArt_Paralyze      = 0x0006DE86
PERK_AlterationHalfCost   = 0x000C44B9   # the same half-cost perk chain vanilla Alteration spells use (Adept)

AV_Alteration = 18
ARCHETYPE_Script = 1
CAST_FireAndForget = 1
DELIVERY_Aimed = 2


def sub(sig, data):
    assert len(data) < 0x10000, sig
    return sig.encode() + struct.pack('<H', len(data)) + data


def rec(sig, formid, body, flags=0):
    return (sig.encode() + struct.pack('<I', len(body)) + struct.pack('<I', flags)
            + struct.pack('<I', formid) + struct.pack('<HHHH', 0, 0, FORM_VER, 0) + body)


def grup(label, gtype, payload):
    return (b'GRUP' + struct.pack('<I', len(payload) + 24) + label
            + struct.pack('<i', gtype) + b'\x00' * 8 + payload)


def mgef_data():
    # 38 dwords / 152 bytes, in record order (UESP MGEF DATA). Floats packed as floats.
    d = [0] * 38
    d[0] = 0                          # flags: none (not hostile, not detrimental, no recover)
    d[1] = struct.unpack('<I', struct.pack('<f', 30.0))[0]   # base cost
    d[2] = 0                          # associated item
    d[3] = AV_Alteration              # magic skill
    d[4] = 0xFFFFFFFF                 # resist value: none
    d[5] = 0                          # counter effect count
    d[6] = 0                          # light
    d[7] = struct.unpack('<I', struct.pack('<f', 1.0))[0]    # taper weight
    d[8] = 0                          # hit shader
    d[9] = 0                          # enchant shader
    d[10] = 0                         # minimum skill level
    d[11] = 0                         # spellmaking area
    d[12] = struct.unpack('<I', struct.pack('<f', 0.5))[0]   # casting time
    d[13] = 0                         # taper curve
    d[14] = 0                         # taper duration
    d[15] = 0                         # second AV weight
    d[16] = ARCHETYPE_Script          # archetype
    d[17] = 0xFFFFFFFF                # actor value: none
    d[18] = PROJ_ParalyzeProjectile   # projectile - what lets an aimed effect hit a container
    d[19] = 0                         # explosion
    d[20] = CAST_FireAndForget        # casting type
    d[21] = DELIVERY_Aimed            # delivery
    d[22] = 0xFFFFFFFF                # second AV
    d[23] = ARTO_CastingArt_Paralyze  # casting art
    d[24] = ARTO_HitArt_Paralyze      # hit effect art
    d[25] = 0                         # impact data
    d[26] = struct.unpack('<I', struct.pack('<f', 1.0))[0]   # skill usage mult
    d[27] = 0                         # dual cast data
    d[28] = struct.unpack('<I', struct.pack('<f', 1.0))[0]   # dual cast scale
    d[29] = 0; d[30] = 0; d[31] = 0; d[32] = 0; d[33] = 0; d[34] = 0
    d[35] = 0                         # sound volume
    d[36] = 0; d[37] = 0
    out = struct.pack('<38I', *d)
    assert len(out) == 152
    return out


def build():
    mgef = (sub('EDID', b'ALO_ManipulateLockEffect\x00')
            + sub('FULL', b'Manipulate Lock\x00')
            + sub('KSIZ', struct.pack('<I', 1))
            + sub('KWDA', struct.pack('<I', KYWD_MagicSchoolAlteration))
            + sub('DATA', mgef_data())
            + sub('SNDD', b'')
            + sub('DNAM', b'Works the mechanism of a lock from a distance. Opens it if your Alteration is high enough for the lock.\x00'))

    # SPIT (36 bytes): cost, flags, type, charge time, cast type, delivery, cast duration, range, half-cost perk.
    # flags 0x1 = manual cost calc (keep the 30 above rather than the auto-calculated value).
    spit = struct.pack('<IIIfIIffI', 30, 0x00000001, 0, 0.5, CAST_FireAndForget, DELIVERY_Aimed, 0.0, 0.0, PERK_AlterationHalfCost)
    spel = (sub('EDID', b'ALO_ManipulateLock\x00')
            + sub('OBND', b'\x00' * 12)
            + sub('FULL', b'Manipulate Lock\x00')
            + sub('ETYP', struct.pack('<I', EQUP_EitherHand))
            + sub('DESC', b'Works the mechanism of a lock from a distance. Opens it if your Alteration is high enough for the lock.\x00')
            + sub('SPIT', spit)
            + sub('EFID', struct.pack('<I', NEW_MGEF))
            + sub('EFIT', struct.pack('<fII', 0.0, 0, 0)))   # magnitude, area, duration

    assert b'VMAD' not in mgef + spel

    # top-level groups in the engine's canonical order: MGEF < SPEL
    body = (grup(b'MGEF', 0, rec('MGEF', NEW_MGEF, mgef))
            + grup(b'SPEL', 0, rec('SPEL', NEW_SPEL, spel)))

    num_records = 4  # 2 records + 2 groups, TES4 excluded
    hedr = struct.pack('<fiI', 1.7, num_records, 0x802)
    tes4_body = (sub('HEDR', hedr)
                 + sub('CNAM', b'ApocryphaRealm\x00')
                 + sub('SNAM', b'ApocryphaRealm Lock Interaction Overhaul - spell carrier. All behaviour is in ApocryphaLockInteractionOverhaul.dll.\x00')
                 + sub('MAST', b'Skyrim.esm\x00') + sub('DATA', b'\x00' * 8))
    tes4 = rec('TES4', 0, tes4_body, flags=0x00000200)  # Light
    return tes4 + body


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dist', 'LockInteractionOverhaul.esp')
    blob = build()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, 'wb').write(blob)
    print('wrote %s (%d bytes)' % (os.path.abspath(out), len(blob)))
