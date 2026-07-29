"""The five sample-free racks of patchbayground, in T9's proposed syntax.

The same racks as `examples/patchbayground.py`, declared through
`patchbay.experimental.dsl2` instead. Both build byte-identical output,
which is what T9 rests on. DR1 is absent because it needs `samples/`.

Read the two files side by side to see what the migration buys: no `_bind`,
no `character=` threaded through five engine functions, no
`meld(drift(wavetable(rack)))` read inside out.

    uv run patchbay build examples/experimental/patchbayground2.py -o build/new

This is T9a's gate. `test_the_new_surface_builds_the_same_bytes` digests
these five racks and compares them with `tests/golden.txt`, which the old
spec writes, so the two surfaces are held to one output.

T9b moves `examples/patchbayground.py` onto these types, and this file goes
with the move.
"""

from __future__ import annotations

from itertools import product

from patchbay.dsl import Engine, Layout, Range, Rack, Slot

# Everything about a slot in one place: position, label, opening knob
# position, and which one drives the chain selector.
PB = Layout(
    Slot("Instrument", label="> Instrument", selects=True),
    Slot("Sound"),
    Slot("Filter", start=127),
    Slot("Drive"),
    Slot("Movement"),
    Slot("Character"),
    Slot("Release", start=30),
    Slot("Volume", start=127),
)

CUTOFF = Range(30.0, 18500.0, "Hz")
RELEASE = Range(0.01, 20.0, "s")
RELEASE_MS = RELEASE.scaled(1000.0)
RESONANCE = Range(0.0, 1.0, "")
VOLUME = Range(0.0, 1.0, "amplitude")

PEAK_DB = {"Operator": 4.38, "InstrumentVector": -4.0,
           "InstrumentMeld": -6.75, "Drift": -5.78}
TARGET_PEAK_DB = -8.0


def trimmed(tag: str, r: Range) -> Range:
    if tag not in PEAK_DB:
        return r
    return r.capped(r.hi * 10.0 ** ((TARGET_PEAK_DB - PEAK_DB[tag]) / 20.0))


# Engine profiles. A value each, declared once, used by every rack that
# wants that engine. `offers` is what the engine can serve for whichever
# role a rack spends its wildcard slot on.
FM = (Engine("Operator")
      .drives(PB.filter, "Filter/Frequency", over=CUTOFF)
      .drives(PB.filter, "Filter/Resonance", over=RESONANCE)
      .drives(PB.drive, "Filter/Drive")
      .drives(PB.movement, "Lfo/LfoAmount")
      .drives(PB.release, "Operator.0/Envelope/ReleaseTime", over=RELEASE_MS)
      .drives(PB.volume, "Globals/Volume",
              over=trimmed("Operator", Range(0.0003162277571, 1.0)))
      .offers("attack", "Operator.0/Envelope/AttackTime")
      .offers("glide", "Globals/PortamentoTime")
      .offers("saturation", "Shaper/Drive"))

SAMPLER = (Engine("OriginalSimpler")
           .drives(PB.filter, "Filter/Slot/Value/SimplerFilter/Freq", over=CUTOFF)
           .drives(PB.filter, "Filter/Slot/Value/SimplerFilter/Res", over=RESONANCE)
           .drives(PB.drive, "Filter/Slot/Value/SimplerFilter/Drive")
           .drives(PB.movement, "Pitch/PitchLfoAmount")
           .drives(PB.release, "VolumeAndPan/Envelope/ReleaseTime", over=RELEASE_MS)
           .drives(PB.volume, "VolumeAndPan/Volume", over=Range(-36.0, 0.0, "dB"))
           .offers("attack", "VolumeAndPan/Envelope/AttackTime")
           .offers("glide", "Globals/PortamentoTime"))

WAVE = (Engine("InstrumentVector")
        .drives(PB.filter, "Voice_Filter1_Frequency", over=CUTOFF)
        .drives(PB.filter, "Voice_Filter1_Resonance", over=RESONANCE)
        .drives(PB.drive, "Voice_Filter1_Drive")
        .drives(PB.release, "Voice_Modulators_AmpEnvelope_Times_Release",
                over=RELEASE)
        .drives(PB.volume, "Volume", over=trimmed("InstrumentVector", VOLUME))
        .offers("attack", "Voice_Modulators_AmpEnvelope_Times_Attack")
        .offers("glide", "Voice_Global_Glide"))

DRIFT = (Engine("Drift")
         .drives(PB.filter, "Filter_Frequency", over=CUTOFF)
         .drives(PB.filter, "Filter_Resonance", over=RESONANCE)
         .drives(PB.movement, "Lfo_Amount")
         .drives(PB.release, "Envelope1_Release", over=RELEASE)
         .drives(PB.volume, "Global_Volume", over=trimmed("Drift", VOLUME))
         .offers("attack", "Envelope1_Attack")
         .offers("glide", "Global_Glide"))

MELD = (Engine("InstrumentMeld")
        .drives(PB.filter, "MeldVoice_EngineA_Filter_Frequency",
                "MeldVoice_EngineB_Filter_Frequency", over=CUTOFF)
        .drives(PB.filter, "MeldVoice_EngineA_Filter_Macro1",
                "MeldVoice_EngineB_Filter_Macro1", over=RESONANCE)
        .drives(PB.drive, "MeldVoice_Drive")
        .drives(PB.release, "MeldVoice_EngineA_AmpEnvelope_Times_Release",
                "MeldVoice_EngineB_AmpEnvelope_Times_Release", over=RELEASE)
        .drives(PB.volume, "Volume", over=trimmed("InstrumentMeld", VOLUME))
        .offers("attack", "MeldVoice_EngineA_AmpEnvelope_Times_Attack",
                "MeldVoice_EngineB_AmpEnvelope_Times_Attack")
        .offers("glide", "MeldVoice_EngineA_GlideTime",
                "MeldVoice_EngineB_GlideTime")
        .offers("morph", "MeldVoice_EngineA_Filter_Macro2",
                "MeldVoice_EngineB_Filter_Macro2"))

PAIRED = "Filter + Res"


def _sound_family(rack: Rack) -> list:
    out = []
    for i, (eng, cut, rel, chr_) in enumerate(product(
            ("FM", "Sample"), (20, 55, 90, 120),
            (10, 45, 80, 115), (0, 64, 127))):
        out.append(PB.variation(
            f"{i:03d} {eng[0]} f{cut} r{rel} c{chr_}",
            instrument=rack.engine_macro(eng),
            filter=cut, release=rel, character=chr_))
    return out


_PD1 = (Rack.instrument("PD1", PB)
        .spends(PB.character, "attack")
        .label(PB.filter, PAIRED)
        .chain("FM", FM)
        .chain("Sample", SAMPLER))
PD1 = _PD1.variations(*_sound_family(_PD1))

PD1W = (Rack.instrument("PD1W", PB)
        .spends(PB.character, "attack")
        .label(PB.filter, PAIRED)
        .chain("Wave", WAVE)
        .chain("Drift", DRIFT))

BS1 = (Rack.instrument("BS1", PB)
       .spends(PB.character, "morph")
       .label(PB.filter, PAIRED)
       .chain("Wave", WAVE)
       .chain("Drift", DRIFT)
       .chain("Meld", MELD))

LD1 = (Rack.instrument("LD1", PB)
       .spends(PB.character, "glide")
       .label(PB.filter, PAIRED)
       .chain("FM", FM)
       .chain("Meld", MELD))

# VA1: the outer Instrument knob picks a sub-rack, every other slot chains
# into whichever is selected. Instrument is left out of the chaining so one
# knob does not do two jobs.
PADS = (Rack.instrument("PADS", PB).chain("Sample", SAMPLER).chain("FM", FM))
KEYS = (Rack.instrument("KEYS", PB).chain("FM", FM))

CHAINED = (PB.filter, PB.drive, PB.movement, PB.character,
           PB.release, PB.volume)

_VA1 = (Rack.instrument("VA1", PB)
        .chain("PADS", PADS.chaining(*CHAINED))
        .chain("KEYS", KEYS.chaining(*CHAINED)))

VA1 = _VA1.variations(
    PB.variation("A bright", instrument=_VA1.engine_macro("PADS"),
                 filter=115, release=20, character=10),
    PB.variation("A dark", instrument=_VA1.engine_macro("PADS"),
                 filter=25, release=110, character=90),
    PB.variation("B bright", instrument=_VA1.engine_macro("KEYS"),
                 filter=115, release=20, character=10),
    PB.variation("B dark", instrument=_VA1.engine_macro("KEYS"),
                 filter=25, release=110, character=90),
)

RACKS = [PD1, PD1W, BS1, LD1, VA1]


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "build/new"
    for rack in RACKS:
        print(rack.save(f"{out}/{rack.name}.adg"))
