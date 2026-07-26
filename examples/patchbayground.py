"""PATCHBAYGROUND - the template this project exists to build.

`doc/PATCHBAYGROUND.md` describes the musical target. This file is the
machine-readable half: the same intent, in a form the compiler can realise.

Inspired by PLAYGRND, an Ableton Live Set by Andri Soren:
https://www.youtube.com/watch?v=plQ9F-0RmDw

The architecture that Set demonstrates: one macro grammar across every rack,
engines as chains, a sound addressed by two knobs. Rebuilt here to our own
taste, from a declaration, because doing it by hand is thousands of macro
mappings entered by mouse.

    patchbay build examples/patchbayground.py -o build/

## How to read this file

The top section is LIVE and compiles today. Everything below the DRAFT
banner is commented out and describes the end target: what the DSL should
look like once the missing pieces exist. It is a design sketch kept in the
repo on purpose, so the shape of the destination is not carried around in
someone's head.

Each draft block names what it is blocked on. Uncomment as the capability
lands, and delete this note when nothing is left commented.

Live today:
  the eight slot grammar, complete
  PD1 as a two engine slice
  96 variations over four slots, one of them the instrument choice
  VA1 as a two level nest, macros chaining into the selected sub-rack

  Both racks are gated in Live 12.4.3 under this grammar, ranges included.
  Slot 2, Sound, binds nothing yet: neither rack has sound chains to select
  between, and a slot nothing drives writes no mapping.

Blocked:
  BS1, LD1 and PD1 proper are no longer blocked on donors: Wavetable,
  Drift and Meld are harvested. They are blocked on being written.
  SR1 still waits on samples.
"""

from __future__ import annotations

from itertools import product

from patchbay.dsl import Grammar, Rack, RackKind, Variation

# ===========================================================================
# The grammar
# ===========================================================================

# Identical across every instrument rack, so muscle memory transfers. This
# consistency is the product, more than any individual rack, so it is
# declared once here and every rack takes it as an argument.
#
# Eight slots, one Push page. A rack has 16 macros and Push will show a
# second page, but a page flip mid-jam costs more than the extra knobs are
# worth. Slots 1, 2, 7 and 8 are fixed on every rack; 3 to 6 are character.
PATCHBAYGROUND = Grammar(
    "Instrument",  # 1  chain selector: which engine
    "Sound",       # 2  chain selector: which sound within that engine
    "Filter",      # 3  cutoff
    "Drive",       # 4  filter drive
    "Movement",    # 5  LFO or mod depth
    "Character",   # 6  per rack wildcard
    "Release",     # 7  release, or decay where an engine has no release
    "Volume",      # 8  always
    selector="Instrument",
)

# Cutoff range shared by every engine, in Hz.
#
# The intersection of what the four engines offer natively: Operator
# 30..18500, Simpler 30..22000, Wavetable 20..20480, Drift 20..20000. Using
# the intersection rather than each engine's own maximum is what keeps one
# knob position meaning one frequency across engines, which is the sound
# family constraint. Nothing audible is lost at the top; 18.5 kHz is above
# where a filter sweep reads as pitch.
#
# Q15: the macro follows the parameter's LOGARITHMIC taper, so a wide range
# costs no resolution where it matters. Macro 64 over 200..8000 measured
# 1.28 kHz, the geometric mean, not the arithmetic one. The old 200..8000
# cap reached 43% of Operator's range and meant the filter never opened.
CUTOFF = (30.0, 18500.0)

# The drum rack's top level is NOT the instrument grammar. Eight pads times
# eight parameters cannot fit eight knobs, so the top level is kit-wide
# moves only and per-pad control is reached by diving into the pad on Push.
KIT = Grammar(
    "Tune", "Decay", "Drive", "Send A", "Send B", "Punch", "Space", "Character",
)


# ===========================================================================
# LIVE - compiles and loads today
# ===========================================================================

def fm(rack: Rack, name: str = "FM") -> Rack:
    """An Operator chain bound to the grammar."""
    with rack.engine(name, "Operator") as e:
        e.bind(
            filter=("Filter/Frequency", *CUTOFF),
            drive="Filter/Drive",
            movement="Lfo/LfoAmount",
            character="Filter/Resonance",
            release="Operator.0/Envelope/ReleaseTime",
            # Linear amplitude, native range 0.000316..1.995. Capped at
            # unity so full right is 0 dB rather than +6 and clipping.
            volume=("Globals/Volume", 0.0003162277571, 1.0),
        )
    return rack


def sampler(rack: Rack, name: str = "Sample") -> Rack:
    """A Simpler chain bound to the SAME grammar slots as `fm`.

    That correspondence is the sound family constraint: one knob moves the
    same musical idea through different synthesis.
    """
    with rack.engine(name, "OriginalSimpler") as e:
        e.bind(
            filter=("Filter/Slot/Value/SimplerFilter/Freq", *CUTOFF),
            drive="Filter/Slot/Value/SimplerFilter/Drive",
            movement="Pitch/PitchLfoAmount",
            character="Filter/Slot/Value/SimplerFilter/Res",
            release="VolumeAndPan/Envelope/ReleaseTime",
            # Decibels, native range -36..+36. Capped at unity for the same
            # reason as the FM engine. The floor is -36 dB because that is
            # all Simpler offers: audible, where Operator's floor is -70.
            volume=("VolumeAndPan/Volume", -36.0, 0.0),
        )
    return rack


def pd1() -> Rack:
    """Pads. Wavetable-based per the spec; Operator and Simpler for now."""
    rack = sampler(fm(Rack("PD1", PATCHBAYGROUND, kind=RackKind.INSTRUMENT)))
    rack.variations(*sound_family(rack))
    return rack


def va1(name: str = "VA1") -> Rack:
    """Various. Each chain is a rack in its own right.

    Two levels rather than the five racks the spec eventually wants, which
    are blocked on donors. What this exercises is the nesting itself: the
    outer Engine macro picks a sub-rack, and every other slot chains
    macro-to-macro into whichever sub-rack is selected.

    Engine is bound explicitly OUT of the chaining. The identity default
    would also drive each sub-rack's own Engine macro, which is the pattern
    racks/s1_source.adg uses, but here it would mean one knob doing two
    jobs at once.
    """
    rack = Rack(name, PATCHBAYGROUND, kind=RackKind.INSTRUMENT)
    chained = dict(filter="filter", drive="drive", movement="movement",
                   character="character", release="release", volume="volume")

    for inner in (fm(sampler(_inner("PADS"))), fm(_inner("KEYS"))):
        rack.nest(inner.name, inner).bind(**chained)

    rack.variations(
        Variation("A bright", instrument=rack.engine_macro("PADS"),
                  filter=115, release=20, character=10),
        Variation("A dark", instrument=rack.engine_macro("PADS"),
                  filter=25, release=110, character=90),
        Variation("B bright", instrument=rack.engine_macro("KEYS"),
                  filter=115, release=20, character=10),
        Variation("B dark", instrument=rack.engine_macro("KEYS"),
                  filter=25, release=110, character=90),
    )
    return rack


def _inner(name: str) -> Rack:
    return Rack(name, PATCHBAYGROUND, kind=RackKind.INSTRUMENT)


def sound_family(rack: Rack) -> list[Variation]:
    """A grid over the slots this rack drives. 2 x 4 x 4 x 3 = 96 sounds.

    Values are macro positions, 0..127, which is the only scale a variation
    has. Each engine's own parameter range is applied by Live at recall, so
    one vector is one sound in whichever engine the variation selects.

    Engine is a grid axis rather than a separate dimension of the template.
    That is the point of the module: a sound is a variation, not a chain,
    and the engine is part of what a sound is.
    """
    out = []
    for i, (eng, cut, rel, chr_) in enumerate(product(
            ("FM", "Sample"),
            (20, 55, 90, 120),      # Filter
            (10, 45, 80, 115),      # Release
            (0, 64, 127))):         # Character, here resonance
        out.append(Variation(
            # The name encodes its own values, so culling by ear is informed
            # rather than blind. KICKOFF.md asks for this.
            name=f"{i:03d} {eng[0]} f{cut} r{rel} c{chr_}",
            instrument=rack.engine_macro(eng),
            filter=cut, release=rel, character=chr_,
        ))
    return out


RACKS: list[Rack] = [pd1(), va1()]


# ===========================================================================
# DRAFT - the end target
# ===========================================================================
#
# Nothing below runs. It is the shape the DSL should reach, written out so
# the destination is concrete and so each missing capability has a caller
# waiting for it.


# ---------------------------------------------------------------------------
# Wider variation grids. Blocked on: bindings for the remaining slots.
# ---------------------------------------------------------------------------
#
# `sound_family` above grids over the four slots PD1 drives today. Drive and
# Movement are in the grammar but nothing binds them, and a variation may
# only set a slot something answers to - the DSL refuses the rest rather
# than writing a knob wired to nothing. Adding those bindings widens the
# grid with no change to the variation code.


# ---------------------------------------------------------------------------
# Samples. Blocked on: binding sample retargeting into the DSL.
# Phase 3 is small: S7 showed only the two path fields on each of a
# sample's two FileRefs are required.
# ---------------------------------------------------------------------------
#
# with rack.engine("Sample", "OriginalSimpler") as e:
#     e.sample("samples/kicks/ebm_01.wav")
#     e.bind(filter="Filter/Slot/Value/SimplerFilter/Freq")


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
# DR1. Blocked on: drum pads in the DSL, samples, and Q6. Nesting itself is
# no longer the blocker - VA1 above writes it. What DR1 adds is the pad
# side: ReceivingNote per pad, a sample per chain, and return selectors.
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
#             with p.rack("PAD", PATCHBAYGROUND) as pad_rack:
#                 pad_rack.device("MidiPitcher").bind(
#                     tune="Pitch/TransposeKey")
#
#                 with pad_rack.rack("ENGINE", PATCHBAYGROUND) as engines:
#                     for i, wav in enumerate(pad.samples):
#                         with engines.engine(f"S{i + 1}", "OriginalSimpler") as e:
#                             e.sample(wav)
#                             e.bind(
#                                 filter="Filter/Slot/Value/SimplerFilter/Freq",
#                                 release="Filter/Slot/Value/SimplerFilter/Envelope/DecayTime",
#                             )
#                     # The FM layer spans the whole selector rather than
#                     # taking a slice, so it can blend under any sample.
#                     with engines.engine("FM", "Operator") as e:
#                         e.zone(0, 127)
#                         e.bind(filter="Filter/Frequency",
#                                release="Filter/Envelope/DecayTime")
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
#     rack = Rack("BS1", PATCHBAYGROUND, kind=RackKind.INSTRUMENT)
#     with rack.engine("Wavetable", "InstrumentVector") as e:
#         e.bind(filter="Filter1/Freq", character="Filter1/Res", ...)
#     with rack.engine("Operator", "Operator") as e:
#         e.bind(filter="Filter/Frequency", ...)
#     with rack.engine("Drift", "Drift") as e:
#         e.bind(...)
#     return rack
#
# def ld1() -> Rack:
#     """FM leads, mono with glide. Glide is grammar slot 9."""
#     rack = Rack("LD1", PATCHBAYGROUND, kind=RackKind.INSTRUMENT)
#     with rack.engine("FM", "Operator") as e:
#         e.bind(glide="PortamentoTime", detune="Detune", ...)
#     return rack
#
# def sr1() -> Rack:
#     """Sampler, built in sounds plus a hot swap slot."""
#     ...
#
# VA1 is live above with two sub-racks. Widening it to the five the spec
# names is `for inner in (dr1(), bs1(), pd1(), ld1(), sr1())`, and waits
# only on those racks existing.


# ---------------------------------------------------------------------------
# The Set. Blocked on: extending the ableton-mcp remote script.
# NOT generated as .als. doc/MCP.md establishes that track creation,
# routing and clips ARE in the Live API, so a Set is built by driving a
# running Live rather than by writing XML that breaks on every update.
# ---------------------------------------------------------------------------
#
# from patchbay.live import LiveSet, TrackKind
#
# def patchbayground_set() -> LiveSet:
#     s = LiveSet("PATCHBAYGROUND", tempo=128)
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
