"""PLAYGRND - the template this project exists to build.

`doc/TEMPLATE_SPEC.md` describes the musical target. This file is the
machine-readable half: the same intent, in a form the compiler can realise.

    patchbay build examples/playgrnd.py -o build/

## How to read this file

The top section is LIVE and compiles today. Everything below the DRAFT
banner is commented out and describes the end target: what the DSL should
look like once the missing pieces exist. It is a design sketch kept in the
repo on purpose, so the shape of the destination is not carried around in
someone's head.

Each draft block names what it is blocked on. Uncomment as the capability
lands, and delete this note when nothing is left commented.

Live today:
  the grammar, complete
  PD1 as a two engine slice, verified loading and mapping in Live 12.4.3

Blocked:
  everything else, mostly on nested racks and on donors for the engines
  the spec actually calls for
"""

from __future__ import annotations

from patchbay.dsl import Grammar, Rack, RackKind

# ===========================================================================
# The grammar
# ===========================================================================

# Identical across every instrument rack, so muscle memory transfers. This
# consistency is the product, more than any individual rack, so it is
# declared once here and every rack takes it as an argument.
#
# Push shows 8 macros per page. Slots 1-8 are page one, 9-13 page two.
# 14-16 are deliberately unassigned: TEMPLATE_SPEC.md does not name them,
# and inventing slots would be inventing intent.
PLAYGRND = Grammar(
    # page one, the eight knobs that matter during a jam
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

# The drum rack's top level is NOT the instrument grammar. Eight pads times
# eight parameters cannot fit eight knobs, so the top level is kit-wide
# moves only and per-pad control is reached by diving into the pad on Push.
KIT = Grammar(
    "Tune", "Decay", "Drive", "Send A", "Send B", "Punch", "Space", "Character",
)


# ===========================================================================
# LIVE - compiles and loads today
# ===========================================================================

def pd1() -> Rack:
    """Pads. Wavetable-based per the spec; Operator and Simpler for now.

    Both engines bind the same grammar slots to their own parameters, which
    is what makes variation index N mean the same musical idea rendered
    through different synthesis.
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


# ===========================================================================
# DRAFT - the end target
# ===========================================================================
#
# Nothing below runs. It is the shape the DSL should reach, written out so
# the destination is concrete and so each missing capability has a caller
# waiting for it.


# ---------------------------------------------------------------------------
# Variations. Blocked on: nothing in the format, this is the next build task.
# ---------------------------------------------------------------------------
#
# The highest value module in the project. ~692 sounds across 18 engines
# means a sound is a VARIATION, not a chain.
#
# The sound family constraint says variation N is the same musical idea in
# every engine. Because every engine binds the same grammar slots, one
# vector expressed in slot terms renders through all of them, and the
# constraint is satisfied by construction rather than by discipline.
#
# from itertools import product
# from patchbay.dsl import Variation
#
# def dark_family() -> list[Variation]:
#     """A grid over four slots. 4 x 4 x 3 x 2 = 96 sounds per rack."""
#     out = []
#     for i, (cut, dec, drv, mov) in enumerate(product(
#             (20, 55, 90, 120),     # Cutoff
#             (10, 45, 80, 115),     # Decay
#             (0, 64, 127),          # Drive
#             (0, 90))):             # Movement
#         out.append(Variation(
#             # The name encodes its own values, so culling by ear is
#             # informed rather than blind. KICKOFF.md asks for this.
#             name=f"{i:03d} c{cut} d{dec} v{drv} m{mov}",
#             cutoff=cut, decay=dec, drive=drv, movement=mov,
#         ))
#     return out
#
# rack.variations(*dark_family())


# ---------------------------------------------------------------------------
# Samples. Blocked on: binding sample retargeting into the DSL.
# Phase 3 is small: S7 showed only the two path fields on each of a
# sample's two FileRefs are required.
# ---------------------------------------------------------------------------
#
# with rack.engine("Sample", "OriginalSimpler") as e:
#     e.sample("samples/kicks/ebm_01.wav")
#     e.bind(cutoff="Filter/Slot/Value/SimplerFilter/Freq")


# ---------------------------------------------------------------------------
# Aftertouch. Blocked on: SPIKES.md Q2, nothing is known about how it is
# stored. Probably a sibling of the KeyMidi mechanism, but that is a guess.
# ---------------------------------------------------------------------------
#
# Every sound maps aftertouch to filter and pitch. Drum pads are excluded,
# because Push does not send per pad aftertouch there.
#
# with rack.engine("FM", "Operator") as e:
#     e.aftertouch(filter="Filter/Frequency", pitch="Pitch/Transpose")


# ---------------------------------------------------------------------------
# DR1. Blocked on: rack-inside-chain in the DSL, and SPIKES.md Q1b.
# The three level pattern is verified to EXIST in racks/s1_source.adg. What
# is unproven is whether a nested rack we WRITE is accepted, since lifting
# one out produced a file Live refused to even accept as a drop.
# ---------------------------------------------------------------------------
#
# from patchbay.dsl import DrumRack, PadSpec
#
# PADS = [
#     PadSpec("KICK",  note=36, samples=["samples/kicks/ebm_01.wav", ...]),
#     PadSpec("SNARE", note=38, samples=[...]),
#     PadSpec("CLAP",  note=39, samples=[...]),
#     PadSpec("HAT",   note=42, samples=[...]),
#     PadSpec("OHAT",  note=46, samples=[...]),
#     PadSpec("TOM",   note=41, samples=[...]),
#     PadSpec("RIM",   note=37, samples=[...]),
#     PadSpec("PERC",  note=43, samples=[...]),
# ]
#
# def dr1() -> DrumRack:
#     """Three levels of nesting per pad, eight pads.
#
#         Drum Rack                    kit macros only
#         └─ Pad chain
#            └─ Pad rack "KICK"        the 8 pad knobs
#               ├─ MidiPitcher         Tune
#               ├─ Engine rack         Sound, decay, filter
#               │  ├─ Simpler x4       sample chains, zones distributed
#               │  └─ Operator         FM layer, zone spans full 0-127
#               └─ Saturator           Drive
#
#     Macros chain to macros: kit Sound drives pad Sound drives engine
#     Sound drives the chain selector. Verified working three levels deep
#     in racks/s1_source.adg.
#     """
#     kit = DrumRack("DR1", KIT, pads=16)
#
#     for pad in PADS:
#         with kit.pad(pad.name, note=pad.note) as p:
#             with p.rack("PAD", PLAYGRND) as pad_rack:
#                 pad_rack.device("MidiPitcher").bind(
#                     tune="Pitch/TransposeKey")
#
#                 with pad_rack.rack("ENGINE", PLAYGRND) as engines:
#                     for i, wav in enumerate(pad.samples):
#                         with engines.engine(f"S{i + 1}", "OriginalSimpler") as e:
#                             e.sample(wav)
#                             e.bind(
#                                 cutoff="Filter/Slot/Value/SimplerFilter/Freq",
#                                 decay="Filter/Slot/Value/SimplerFilter/Envelope/DecayTime",
#                             )
#                     # The FM layer spans the whole selector rather than
#                     # taking a slice, so it can blend under any sample.
#                     with engines.engine("FM", "Operator") as e:
#                         e.zone(0, 127)
#                         e.bind(cutoff="Filter/Frequency",
#                                decay="Filter/Envelope/DecayTime")
#
#                 pad_rack.device("Saturator").bind(drive="PreDrive")
#
#             # Per pad sends. Adding a return seeds a send entry on every
#             # chain, so these indices exist once the returns below do.
#             p.send(0, 0.25)     # reverb
#             p.send(1, 0.10)     # delay
#
#     # DR1's returns live inside the drum rack. Each holds a SELECTOR
#     # across several reverbs and delays, so a macro swaps the effect
#     # rather than only its send level. Blocked additionally on Q6.
#     with kit.return_chain("SPACE") as r:
#         r.selector(["Reverb", "Reverb", "Delay"], macro="Space")
#
#     return kit


# ---------------------------------------------------------------------------
# The other instrument racks. Blocked on: donors. The library holds
# Operator, Simpler, Saturator, Reverb and MidiPitcher, harvested from
# spike files. Wavetable, Drift and Meld need racks saved into donors/.
# ---------------------------------------------------------------------------
#
# def bs1() -> Rack:
#     """Multi engine bass."""
#     rack = Rack("BS1", PLAYGRND, kind=RackKind.INSTRUMENT)
#     with rack.engine("Wavetable", "InstrumentVector") as e:
#         e.bind(cutoff="Filter1/Freq", resonance="Filter1/Res", ...)
#     with rack.engine("Operator", "Operator") as e:
#         e.bind(cutoff="Filter/Frequency", ...)
#     with rack.engine("Drift", "Drift") as e:
#         e.bind(...)
#     return rack
#
# def ld1() -> Rack:
#     """FM leads, mono with glide. Glide is grammar slot 9."""
#     rack = Rack("LD1", PLAYGRND, kind=RackKind.INSTRUMENT)
#     with rack.engine("FM", "Operator") as e:
#         e.bind(glide="PortamentoTime", detune="Detune", ...)
#     return rack
#
# def sr1() -> Rack:
#     """Sampler, built in sounds plus a hot swap slot."""
#     ...
#
# def va1(name: str) -> Rack:
#     """Various. Nests all five instrument racks as chains.
#
#     Blocked on rack-in-rack composition, same as DR1: a Rack has to be
#     placeable INTO another rack's chain.
#     """
#     rack = Rack(name, PLAYGRND, kind=RackKind.INSTRUMENT)
#     for inner in (dr1(), bs1(), pd1(), ld1(), sr1()):
#         rack.nest(inner)
#     return rack


# ---------------------------------------------------------------------------
# The Set. Blocked on: extending the ableton-mcp remote script.
# NOT generated as .als. doc/MCP.md establishes that track creation,
# routing and clips ARE in the Live API, so a Set is built by driving a
# running Live rather than by writing XML that breaks on every update.
# ---------------------------------------------------------------------------
#
# from patchbay.live import LiveSet, TrackKind
#
# def playgrnd_set() -> LiveSet:
#     s = LiveSet("PLAYGRND", tempo=128)
#
#     s.track("DR1", dr1())
#     s.track("BS1", bs1())
#     s.track("PD1", pd1())
#     s.track("LD1", ld1())
#     s.track("SR1", sr1())
#     s.track("VA1", va1("VA1"))
#     s.track("VA2", va1("VA2"))
#
#     # PM1 exists because the Master track has no Session clip slots, so
#     # master bus moves cannot be automated in Session view. Everything
#     # routes here instead, and silent dummy clips carry the automation.
#     pm1 = s.track("PM1", kind=TrackKind.AUDIO)
#     for name in ("DR1", "BS1", "PD1", "LD1", "SR1", "VA1", "VA2"):
#         s.route(name, to=pm1)
#
#     s.returns(8)
#
#     # Sidechain source is absent from the Live Object Model AND not yet
#     # found in the file format. It stays manual: set the channel strip
#     # compressor on each track to sidechain from DR1, low band only.
#     s.note_manual_step("sidechain every channel strip from DR1")
#
#     return s
