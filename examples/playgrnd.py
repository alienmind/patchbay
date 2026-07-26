"""PLAYGRND — the template this project exists to build.

The musical target is described in `doc/TEMPLATE_SPEC.md`. This file is
the machine-readable half: the same intent, in a form the compiler can
realise.

    patchbay build examples/playgrnd.py -o build/

Status: **partial and tentative.** The grammar below is settled; the
engine bindings are not. Only racks whose engines exist in the device
library can be built today, and the library currently holds Operator,
Simpler, Saturator, Reverb and MidiPitcher — harvested from spike files
rather than curated donors. Wavetable, Drift, Meld and the rest need
donors saved before BS1, PD1 and LD1 can be declared properly.

What is real here: the grammar, the two-engine PD1 slice that compiles and
loads, and the shape the rest will take.
"""

from __future__ import annotations

from patchbay.dsl import Grammar, Rack, RackKind

# ---------------------------------------------------------------------------
# The grammar
# ---------------------------------------------------------------------------

# Identical across every instrument rack, so muscle memory transfers. This
# consistency is the product, more than any individual rack — so it is
# declared once, here, and every rack below takes it as an argument.
#
# Push shows 8 macros per page. Slots 1-8 are page one, 9-13 page two.
# 14-16 are deliberately unassigned: TEMPLATE_SPEC.md does not name them,
# and inventing slots would be inventing intent.
PLAYGRND = Grammar(
    # page one — the eight knobs that matter during a jam
    "Engine",      # 1  chain selector: sweeps engines, and therefore sounds
    "Cutoff",      # 2
    "Resonance",   # 3
    "Decay",       # 4  decay or release, whichever the engine has
    "Drive",       # 5
    "Movement",    # 6  LFO or mod depth
    "Space",       # 7  reverb send
    "Character",   # 8  per rack wildcard
    # page two
    "Glide",       # 9
    "Detune",      # 10
    "Delay",       # 11 delay feedback
    "Width",       # 12
    "Transient",   # 13
)


# ---------------------------------------------------------------------------
# PD1 — polyphonic pads
# ---------------------------------------------------------------------------

def pd1() -> Rack:
    """Pads. Wavetable-based per the spec; Operator and Simpler for now.

    Both engines bind the same grammar slots to their own parameters, which
    is what makes variation index N mean the same musical idea through
    different synthesis.
    """
    rack = Rack("PD1", PLAYGRND, kind=RackKind.INSTRUMENT)

    with rack.engine("FM", "Operator") as e:
        e.bind(
            cutoff=("Filter/Frequency", 200, 8000),
            resonance="Filter/Resonance",
            decay="Filter/Envelope/DecayTime",
        )

    with rack.engine("Sample", "OriginalSimpler") as e:
        e.bind(
            cutoff=("Filter/Slot/Value/SimplerFilter/Freq", 200, 8000),
            resonance="Filter/Slot/Value/SimplerFilter/Res",
            decay="Filter/Slot/Value/SimplerFilter/Envelope/DecayTime",
        )

    return rack


RACKS: list[Rack] = [pd1()]


# ---------------------------------------------------------------------------
# Not yet declarable
# ---------------------------------------------------------------------------
#
# DR1  drum rack, three levels of nesting per pad, eight pads.
#      Needs: nested Rack-inside-Chain in the DSL, and per-pad sends.
#      The nesting pattern itself is verified — racks/s1_source.adg has it.
#
# BS1  multi engine bass.      Needs donors.
# LD1  FM leads, mono, glide.  Needs donors and a mono/glide binding.
# SR1  sampler plus hotswap.   Needs Phase 3 sample retargeting.
# VA1  nests the five above.   Needs rack-in-rack composition.
# VA2  second instance of VA1.
# PM1  audio track, pre-master. Not a rack — built through ableton-mcp.
#
# Variations are absent everywhere: the highest-value module per
# TEMPLATE_SPEC.md, and the next thing to build.
