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

Live today: six racks, all compiling. PD1, PD1W, BS1, LD1 and DR1 have been
loaded, played and corrected in Live 12.4.3; VA1 exercises nesting.

Slot 2, Sound, binds nothing on the instrument racks: they have no sound
chains to select between, and a slot nothing drives writes no mapping. It
earns its place inside a drum pad, where it walks eight samples.

Blocked: SR1, on samples.

## Three things this file decides that the grammar does not

**Slot 3 drives cutoff AND resonance.** One knob, two parameters that
belong together, which is what frees slot 6 to be a real wildcard instead
of a permanent home for resonance. The cost is that a paired slot cannot be
automated to move one half.

**Slot 6 is chosen per rack from a role table.** Attack on pads, glide on
leads, morph where Meld lands. An engine that cannot serve the role leaves
the slot empty rather than substituting something else, which is why BS1's
slot 6 moves on Meld and on nothing else.

**Labels are local, positions are not.** A kick's slot 4 reads
"Drive + Snap" where a hat's reads "Drive": same slot, same chaining, same
muscle memory. Without it, change 1 would ship a knob called Filter that
also moves resonance and never says so.

Not relitigated here, because they are gated: the eight names, the selector
slot, the ranges, the level trims, DR1's pad layout.
"""

from __future__ import annotations

from itertools import product
from pathlib import Path

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
    # Where each knob sits on a fresh drop. Without this every macro reads
    # 0, and 0 through a binding is the BOTTOM of the parameter's range, so
    # the rack loads silent with the filter shut. Gated in Live 12.4.3: A1
    # to A5 all had to be turned up by hand before anything was audible.
    #
    # Volume and Filter open at 127 because the top of each binding's range
    # IS the neutral position, not a loud one: every volume binding is
    # capped at unity or below, see PEAK_DB. Drive and Movement open at 0
    # because their neutral is off. Release opens at 30, roughly 0.4 s on
    # the shared 0.01..20 s range: short enough to play, long enough to hear
    # the knob move in either direction. Instrument and Sound open at 0, the
    # first chain.
    start={"Filter": 127, "Release": 30, "Volume": 127},
    # Slot 1 STEPS where every other knob SWEEPS, and a player wants to
    # know which is which before touching it. `>` is this project's mark
    # for that, not a Live convention: nothing in the format distinguishes
    # a selector on the display, so the distinction has to be spelled.
    labels={"Instrument": "> Instrument"},
)

# Slot 3 drives cutoff AND resonance, and slot 4 drives drive; a knob whose
# label under-describes what it moves is the thing labels exist to stop.
# Applied per rack rather than declared on the grammar because a rack that
# spends slot 6 on resonance instead would not pair, and then the plain
# name is the true one.
#
# The cost of pairing, stated once: a paired slot cannot be automated to
# move one half. Where that matters, split them and spend the wildcard.
PAIRED = {"Filter": "Filter + Res"}


def paired(role: str | None = None) -> dict[str, str]:
    """Labels for a rack: the pairing on slot 3, and slot 6's actual role.

    Slot 6 is called Character in the grammar because that is what the
    CONTRACT is; on the hardware it says which wildcard this rack spent it
    on. A rack that leaves the slot empty for some of its engines still
    names the role, because the knob does work on the engines that have it.
    """
    return {**PAIRED, **({"Character": role.title()} if role else {})}


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

# The same reasoning as CUTOFF, applied to the other slots whose engines
# disagree. Each is the INTERSECTION of the native ranges, measured with
# library.Device.range_of, so one knob position means one result on every
# engine. Q14 is what happens when this is skipped: a Volume slot bound
# correctly on both engines that silenced one and not the other.
#
#   Release   Wavetable 0.0015..20 s, Drift 0.01..60 s, Meld 0.0015..40 s
#   Resonance Wavetable 0..1.25,      Drift 0..1.01,    Meld 0..1
#   Volume    Wavetable 0..1,         Drift 0..1,       Meld 0..1.995
RELEASE = (0.01, 20.0)
RESONANCE = (0.0, 1.0)
VOLUME = (0.0, 1.0)

# What each engine actually PUTS OUT with the Volume slot full right, in
# dBFS, measured in Live 12.4.3 on LD1 and BS1.
#
# The intersection above makes one knob position mean one gain SETTING. It
# cannot make it mean one loudness, because what an engine delivers to its
# volume stage is a property of the engine. Four engines at what each calls
# unity span 12 dB:
#
#   Operator  +4.4    Wavetable  -4.0    Meld  -6.8    Drift  -5.8
#
# Operator's figure is derived, not read: at unity it clips, and a pinned
# meter reports nothing. It was measured at -1.62 through a -6 dB trim.
#
# Every figure here has been confirmed by correcting from it and measuring
# again: Operator, Wavetable and Meld all landed on the target to within
# the meter's resolution. Drift did not, coming back 2.2 dB loud, so its
# entry is the second measurement rather than the first. Meld was measured
# twice on two different racks, -6.74 on LD1 and -6.75 on BS1, which is
# what says these are engine properties and not patch properties.
PEAK_DB = {
    "Operator": 4.38,
    "InstrumentVector": -4.0,
    "InstrumentMeld": -6.75,
    "Drift": -5.78,
}

# Where they all land after correcting.
#
# There is a CEILING on this number and it is not taste. Wavetable's Volume
# and Drift's Global_Volume both max out at 1.0 amplitude natively, so
# neither can be pushed ABOVE its own unity from a range, whatever the
# range says; only Meld and Operator go higher, to 1.995. So the target can
# never exceed the quietest engine that cannot be boosted, which is
# Wavetable at -4.
#
# -8 sits below that ceiling with margin to spare, so every correction is a
# cut and no correction can introduce clipping. It was originally forced
# rather than chosen, from a first Drift reading of -8 that later measured
# -5.78. Left where it is: it is gated, and -8 dBFS per track is
# unremarkable gain staging with eight tracks running.
TARGET_PEAK_DB = -8.0


def trimmed(tag: str, lo: float, hi: float) -> tuple[float, float]:
    """A volume range with this engine's level correction folded into its top.

    Amplitude, so a correction in dB is a ratio on the top of the range.
    Only the top: the bottom is already silence, and scaling silence
    changes nothing.

    An engine absent from `PEAK_DB` is UNMEASURED, not verified equal, and
    passes through untouched. Measuring it is a job for ears in Live.
    """
    if tag not in PEAK_DB:
        return (lo, hi)
    return (lo, hi * 10.0 ** ((TARGET_PEAK_DB - PEAK_DB[tag]) / 20.0))


# The drum rack's top level is NOT the instrument grammar. Eight pads times
# eight parameters cannot fit eight knobs, so the top level is kit-wide
# moves only and per-pad control is reached by diving into the pad on Push.
#
# selector=None because a drum rack has no chain selector to drive: a pad is
# chosen by its ReceivingNote, and Live leaves every pad's zone at 0/0/0/0.
# Macro 1 here chains into each pad's own Sound knob instead.
KIT = Grammar(
    "Sound", "Pitch", "Filter", "Drive", "Send A", "Send B", "Send Vol",
    "Volume", selector=None,
    # Same reasoning as PATCHBAYGROUND, and it matters twice over here: a
    # kit macro at 0 drives the PAD macro to 0, which drives the sample's
    # volume to its floor. Pitch and the sends are unbound, so their start
    # is not written.
    start={"Filter": 127, "Volume": 127},
    # The kit's Filter chains into each pad's Filter, which is paired, so
    # the kit knob moves cutoff and resonance on eight pads at once and
    # says so. Sound STEPS rather than sweeps: it walks the sample list.
    labels={"Sound": "> Sound", "Filter": "Filter + Res"},
)

# Inside a pad the axis is WHICH SAMPLE, so the selector slot is Sound
# rather than Instrument. Same eight names as PATCHBAYGROUND so the kit can
# chain slot to slot by identity; only which slot drives the selector moves.
PAD = Grammar(*PATCHBAYGROUND.slots, selector="Sound",
              start=dict(PATCHBAYGROUND.start),
              # The selector mark moves with the selector: inside a pad it
              # is Sound that steps, and Instrument is not bound at all.
              labels={"Sound": "> Sound"})

# Pad layout, and the folder each pad draws from. The names are the ones
# samples/README.md documents, not a vendor's.
#
# The reference is Live's own 808 Core Kit, because a Push player reads the
# 4x4 grid by position before reading any label. That kit lays out:
#
#   48..51  maracas   cymbal    cow bell   claves
#   44..47  low tom   mid tom   OPEN HAT   hi tom
#   40..43  low conga mid conga CLOSED HAT hi conga
#   36..39  kick      rim       snare      clap
#
# so the bottom row is the backbeat, hats stack in column 3, percussion sits
# on row 2 and toms on row 3. Eight sounds fill the bottom row plus the two
# hats in their column, PERC on the conga row and TOM on the tom row.
# Putting TOM at 41 instead, which is a conga slot in every kit Live ships,
# read as wrong on the grid.
PADS = (
    ("KICK", 36, "kick"),
    ("RIM", 37, "rim"),
    ("SNARE", 38, "snare"),
    ("CLAP", 39, "clap"),
    ("PERC", 41, "perc"),
    ("HAT", 42, "hat"),
    ("TOM", 44, "tom"),
    ("OHAT", 46, "ohat"),
)

SAMPLES_PER_PAD = 8


# ===========================================================================
# LIVE - compiles and loads today
# ===========================================================================

# What each engine offers for slot 6, by role. A rack asks for a role; an
# engine that does not have it leaves the slot EMPTY rather than
# substituting something else, which is what makes the wildcard a decision
# instead of a leftover.
#
# Every path here was read from library.Device.search, not from memory. The
# gaps are real:
#
#   saturation  only Operator has a shaper. Drift, Wavetable and Meld have
#               nothing that is a saturator rather than a waveshaper or an
#               oscillator control.
#   morph       only Meld, whose filter Macro2 is the L-B-H-N morph. Q10.
#   glide       everywhere, under four different names.
#
# Meld's entries are pairs, driven together for the same reason its filter
# is: this grammar has one knob, not an A knob and a B knob.
WILDCARD: dict[str, dict[str, object]] = {
    "Operator": {
        "attack": "Operator.0/Envelope/AttackTime",
        "glide": "Globals/PortamentoTime",
        "saturation": "Shaper/Drive",
    },
    "OriginalSimpler": {
        "attack": "VolumeAndPan/Envelope/AttackTime",
        "glide": "Globals/PortamentoTime",
    },
    "InstrumentVector": {
        "attack": "Voice_Modulators_AmpEnvelope_Times_Attack",
        "glide": "Voice_Global_Glide",
    },
    "Drift": {
        "attack": "Envelope1_Attack",
        "glide": "Global_Glide",
    },
    "InstrumentMeld": {
        "attack": ["MeldVoice_EngineA_AmpEnvelope_Times_Attack",
                   "MeldVoice_EngineB_AmpEnvelope_Times_Attack"],
        "glide": ["MeldVoice_EngineA_GlideTime",
                  "MeldVoice_EngineB_GlideTime"],
        "morph": ["MeldVoice_EngineA_Filter_Macro2",
                  "MeldVoice_EngineB_Filter_Macro2"],
    },
}


def _bind(e, tag: str, paths: dict, role: str | None) -> None:
    """Apply an engine's common shape, dropping what it cannot serve.

    Returning nothing for a missing role rather than raising is the point:
    a rack asks the whole family for one role, and the engines that lack it
    stay silent. Raising would force every rack to know what every engine
    has.
    """
    slots = {k: v for k, v in paths.items() if v is not None}
    extra = WILDCARD.get(tag, {}).get(role) if role else None
    if extra is not None:
        slots["character"] = extra
    e.bind(**slots)


def fm(rack: Rack, name: str = "FM", character: str | None = None) -> Rack:
    """An Operator chain bound to the grammar."""
    with rack.engine(name, "Operator") as e:
        _bind(e, "Operator", dict(
            filter=[("Filter/Frequency", *CUTOFF),
                    ("Filter/Resonance", *RESONANCE)],
            drive="Filter/Drive",
            movement="Lfo/LfoAmount",
            release="Operator.0/Envelope/ReleaseTime",
            # Linear amplitude, native range 0.000316..1.995. The floor is
            # -70 dB, well below Simpler's -36. The top is set by PEAK_DB:
            # capping at 1.0 was the right gain SETTING and still clipped,
            # because Operator is the hottest engine here by 12 dB.
            volume=("Globals/Volume", *trimmed("Operator", 0.0003162277571, 1.0)),
        ), character)
    return rack


def sampler(rack: Rack, name: str = "Sample",
            character: str | None = None) -> Rack:
    """A Simpler chain bound to the SAME grammar slots as `fm`.

    That correspondence is the sound family constraint: one knob moves the
    same musical idea through different synthesis.
    """
    with rack.engine(name, "OriginalSimpler") as e:
        _bind(e, "OriginalSimpler", dict(
            filter=[("Filter/Slot/Value/SimplerFilter/Freq", *CUTOFF),
                    ("Filter/Slot/Value/SimplerFilter/Res", *RESONANCE)],
            drive="Filter/Slot/Value/SimplerFilter/Drive",
            movement="Pitch/PitchLfoAmount",
            release="VolumeAndPan/Envelope/ReleaseTime",
            # Decibels, native range -36..+36. Capped at unity for the same
            # reason as the FM engine. The floor is -36 dB because that is
            # all Simpler offers: audible, where Operator's floor is -70.
            #
            # No `trimmed`: this range is in dB and that helper multiplies an
            # AMPLITUDE. A trim here is a subtraction from the top. Simpler
            # also plays whatever sample it is given, so any figure measured
            # once would only hold for that sample.
            volume=("VolumeAndPan/Volume", -36.0, 0.0),
        ), character)
    return rack


def wavetable(rack: Rack, name: str = "Wave",
              character: str | None = None) -> Rack:
    """A Wavetable chain. Leaves Movement empty, deliberately.

    Wavetable's LFO depth lives in a modulation matrix that is not in the
    parameter list at all. `Lfo1_Shape_Amount` is a waveshaper, not a
    depth, so binding it would be inventing intent. A rack that cannot use
    a slot leaves it empty.
    """
    with rack.engine(name, "InstrumentVector") as e:
        _bind(e, "InstrumentVector", dict(
            filter=[("Voice_Filter1_Frequency", *CUTOFF),
                    ("Voice_Filter1_Resonance", *RESONANCE)],
            drive="Voice_Filter1_Drive",
            release=("Voice_Modulators_AmpEnvelope_Times_Release", *RELEASE),
            volume=("Volume", *trimmed("InstrumentVector", *VOLUME)),
        ), character)
    return rack


def drift(rack: Rack, name: str = "Drift",
          character: str | None = None) -> Rack:
    """A Drift chain. No Drive: Drift exposes no drive parameter at all."""
    with rack.engine(name, "Drift") as e:
        _bind(e, "Drift", dict(
            filter=[("Filter_Frequency", *CUTOFF),
                    ("Filter_Resonance", *RESONANCE)],
            movement="Lfo_Amount",
            # Envelope1 is Drift's amp envelope, which was inferred from
            # Envelope2 having a Global_Envelope2Mode and Envelope1 not, and
            # is now gated in Live 12.4.3: C1 held a note and heard the tail
            # follow this macro.
            release=("Envelope1_Release", *RELEASE),
            volume=("Global_Volume", *trimmed("Drift", *VOLUME)),
        ), character)
    return rack


def meld(rack: Rack, name: str = "Meld",
         character: str | None = None) -> Rack:
    """A Meld chain. Both engines, driven together off one macro each.

    Meld is two synthesis engines behind one device, and every A-side path
    has a B twin. Binding only A was gated in Live 12.4.3 as C2 and failed
    exactly as suspected: Macro 3 filtered half the sound and left the
    other half open, which passes every structural check there is.

    Both sides move together because this grammar has one Filter knob, not
    an A knob and a B knob. Splitting them would be a second axis, and a
    Push page has no room for one.

    Q10: the filter's two knobs are `Macro1` (Q) and `Macro2` (L-B-H-N
    morph), and that pairing holds for FilterType 0 only. A rack asking for
    `morph` on a Meld whose filter type has been changed gets a valid
    mapping onto a different control. Nothing detects that.
    """
    with rack.engine(name, "InstrumentMeld") as e:
        _bind(e, "InstrumentMeld", dict(
            filter=[("MeldVoice_EngineA_Filter_Frequency", *CUTOFF),
                    ("MeldVoice_EngineB_Filter_Frequency", *CUTOFF),
                    ("MeldVoice_EngineA_Filter_Macro1", *RESONANCE),
                    ("MeldVoice_EngineB_Filter_Macro1", *RESONANCE)],
            # Drive is device-wide on Meld, one parameter for both engines.
            drive="MeldVoice_Drive",
            release=[("MeldVoice_EngineA_AmpEnvelope_Times_Release", *RELEASE),
                     ("MeldVoice_EngineB_AmpEnvelope_Times_Release", *RELEASE)],
            # Volume is device-wide too.
            volume=("Volume", *trimmed("InstrumentMeld", *VOLUME)),
        ), character)
    return rack


def pd1() -> Rack:
    """Pads. Operator and Simpler, the pair gated in Live 12.4.3.

    Kept as the verified slice: 96 variations, both engines answering one
    grammar. `pd1_wave` below is what the spec actually calls for.
    """
    rack = Rack("PD1", PATCHBAYGROUND, kind=RackKind.INSTRUMENT,
                labels=paired("attack"))
    sampler(fm(rack, character="attack"), character="attack")
    rack.variations(*sound_family(rack))
    return rack


def pd1_wave() -> Rack:
    """Pads proper: lush wavetable. Slot 6 is ATTACK, because a pad is
    played into: a pad you cannot soften is a stab, and softening is most
    of what separates the two.
    """
    rack = Rack("PD1W", PATCHBAYGROUND, kind=RackKind.INSTRUMENT,
                labels=paired("attack"))
    return drift(wavetable(rack, character="attack"), character="attack")


def bs1() -> Rack:
    """Multi engine bass. Three syntheses, one grammar. Slot 6 is MORPH.

    Only Meld can serve morph, so Wavetable and Drift leave slot 6 empty.
    That is the rule working, not a hole: the alternative is binding three
    different ideas to one knob and calling it consistency.

    `PATCHBAYGROUND.md` asks for saturation as the bass wildcard, and it is
    not available. Of the engines in this file only Operator has a shaper,
    and Operator is not in this rack.
    """
    rack = Rack("BS1", PATCHBAYGROUND, kind=RackKind.INSTRUMENT,
                labels=paired("morph"))
    return meld(drift(wavetable(rack)), character="morph")


def ld1() -> Rack:
    """Leads. FM first, per the spec, with Meld as the second colour.

    Slot 6 is GLIDE, the one control a lead needs that a pad does not, and
    the rack where the wildcard pays best: a mono lead lives on portamento.
    """
    rack = Rack("LD1", PATCHBAYGROUND, kind=RackKind.INSTRUMENT,
                labels=paired("glide"))
    return meld(fm(rack, character="glide"), character="glide")


def pad_samples(sound: str, n: int = SAMPLES_PER_PAD) -> list[Path]:
    """The first n files for one pad sound, in sorted order.

    Asks the filesystem rather than a checked-in list. `samples/` is never
    committed, not even as an index of filenames, so a manifest in the repo
    would be the thing CLAUDE.md forbids. The naming convention documented
    in samples/README.md is the interface: `<sound>/<sound>_NNN.wav`,
    numbered from 1 and stable once written, so a path in a spec keeps
    pointing at the same audio.
    """
    folder = Path(__file__).resolve().parent.parent / "samples" / "drums" / sound
    if not folder.is_dir():
        return []
    return sorted(folder.glob(f"{sound}_*.wav"))[:n]


# What a pad calls its knobs, over the shared PAIRED labels. The grammar is
# positional: same slot, same chaining, different word, which is the drum
# rack form of the slot 6 wildcard. A kick's slot 4 is where its snap
# lives, so it says so; a hat's is plain drive.
PAD_LABELS: dict[str, dict[str, str]] = {
    "KICK": {"Drive": "Drive + Snap"},
    "SNARE": {"Drive": "Drive + Snap"},
}


def pad_rack(name: str, sound: str) -> Rack | None:
    """One pad: a rack whose chains are samples, selected by the Sound knob.

    This is where slot 2 finally earns its place. Every other rack in this
    file leaves Sound unbound because it has nothing to select between; a
    pad has eight samples and one knob to walk them.

    Slot 6 is attack, for the same reason PD1 spends it there: it turns a
    sample into a softer version of itself without reaching for the sample
    list.
    """
    files = pad_samples(sound)
    if not files:
        return None

    rack = Rack(name, PAD, kind=RackKind.INSTRUMENT,
                labels={**paired("attack"), **PAD_LABELS.get(name, {})})
    for i, wav in enumerate(files):
        with rack.engine(f"S{i + 1}", "OriginalSimpler") as e:
            e.sample(wav)
            _bind(e, "OriginalSimpler", dict(
                filter=[("Filter/Slot/Value/SimplerFilter/Freq", *CUTOFF),
                        ("Filter/Slot/Value/SimplerFilter/Res", *RESONANCE)],
                drive="Filter/Slot/Value/SimplerFilter/Drive",
                release="VolumeAndPan/Envelope/ReleaseTime",
                volume=("VolumeAndPan/Volume", -36.0, 0.0),
            ), "attack")
    return rack


def dr1() -> Rack | None:
    """The drum rack: eight pads, each a rack of samples. Three levels.

    Returns None when `samples/` is absent, so this file still imports on a
    machine that has the repo and not the audio. That is not politeness: the
    test suite imports this module.

    Kit macros chain into every pad at once. Sound is the interesting one -
    one knob walks the sample choice across the whole kit, and a pad can be
    dived into on Push to move its own.
    """
    kit = Rack("DR1", KIT, kind=RackKind.DRUM)
    chained = dict(sound="sound", filter="filter", drive="drive",
                   volume="volume")

    built = 0
    for name, note, sound in PADS:
        inner = pad_rack(name, sound)
        if inner is None:
            continue
        kit.pad(name, note, rack=inner).bind(**chained)
        built += 1

    return kit if built else None


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
            (0, 64, 127))):         # Character, which on PD1 is attack
        out.append(Variation(
            # The name encodes its own values, so culling by ear is informed
            # rather than blind. KICKOFF.md asks for this.
            name=f"{i:03d} {eng[0]} f{cut} r{rel} c{chr_}",
            instrument=rack.engine_macro(eng),
            filter=cut, release=rel, character=chr_,
        ))
    return out


RACKS: list[Rack] = [r for r in (pd1(), pd1_wave(), bs1(), ld1(), dr1(), va1())
                     if r is not None]


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
