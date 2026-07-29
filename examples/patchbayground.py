"""PATCHBAYGROUND - the template this project exists to build.

`doc/PATCHBAYGROUND.md` describes the musical target. This file is the
machine-readable half: the same intent, in a form the compiler can realise.

Inspired by PLAYGRND, an Ableton Live Set by Andri Sören:
https://www.youtube.com/watch?v=plQ9F-0RmDw

The architecture that Set demonstrates: one macro layout across every rack,
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

## Three things this file decides that the layout does not

**Slot 3 drives cutoff AND resonance.** One knob, two parameters that
belong together, which is what frees slot 6 to be a real wildcard instead
of a permanent home for resonance. The cost is that a paired slot cannot be
automated to move one half.

**Slot 6 is chosen per rack from a role table.** Attack on pads, glide on
leads, morph where Meld lands. An engine that cannot serve the role leaves
the slot empty rather than substituting something else, which is why BS1's
slot 6 moves on Meld and on nothing else. Each engine states what it
`offers`; each rack `spends` its wildcard on one of them.

**Labels are local, positions are not.** A kick's slot 4 reads
"Drive + Snap" where a hat's reads "Drive": same slot, same chaining, same
muscle memory. Without it, change 1 would ship a knob called Filter that
also moves resonance and never says so.

Not relitigated here, because they are gated: the eight names, the selector
slot, the ranges, DR1's pad layout.
"""

from __future__ import annotations

from itertools import product
from pathlib import Path

from patchbay.dsl import Engine, Layout, Rack, Range, Slot

# ===========================================================================
# The layout
# ===========================================================================

# Identical across every instrument rack, so muscle memory transfers. This
# consistency is the product, more than any individual rack, so it is
# declared once here and every rack takes it as an argument.
#
# Eight slots, one Push page. A rack has 16 macros and Push will show a
# second page, but a page flip mid-jam costs more than the extra knobs are
# worth. Slots 1, 2, 7 and 8 are fixed on every rack; 3 to 6 are character.
#
# Each slot carries everything about itself: where it opens, what the
# hardware calls it, and whether it drives the chain selector.
#
# `start` is where the knob sits on a fresh drop. Without it every macro
# reads 0, and 0 through a binding is the BOTTOM of the parameter's range,
# so the rack loads silent with the filter shut. Gated in Live 12.4.3: A1
# to A5 all had to be turned up by hand before anything was audible.
#
# Volume and Filter open at 127 because the top of each binding's range IS
# the neutral position, not a loud one: every volume binding is capped at
# its engine's unity. Drive and Movement open at 0 because their
# neutral is off. Release opens at 30, roughly 0.4 s on the shared
# 0.01..20 s range: short enough to play, long enough to hear the knob move
# in either direction. Instrument and Sound open at 0, the first chain.
#
# Slot 1 STEPS where every other knob SWEEPS, and there is no mark for that.
# This project used to prefix the selector with `>`. It went after I1 to I4
# in Live 12.4.3: Push rendered it, Live truncated `> Instrument` to
# `> Instrum`, and asked whether it read as "this one steps" the answer was
# no. So it cost two characters on the one field that truncates and bought
# nothing. Nothing in the format distinguishes a selector on the display,
# and the honest position is that nothing here does either.
PB = Layout(
    Slot("Instrument", selects=True),  # 1  which engine
    Slot("Sound"),                    # 2  which sound within that engine
    Slot("Filter", start=127),        # 3  cutoff, paired with resonance
    Slot("Drive"),                    # 4  filter drive
    Slot("Movement"),                 # 5  LFO or mod depth
    Slot("Character"),                # 6  per rack wildcard
    Slot("Release", start=30),        # 7  release, or decay where there is none
    Slot("Volume", start=127),        # 8  always
)

# Slot 3 drives cutoff AND resonance, and slot 4 drives drive; a knob whose
# label under-describes what it moves is the thing labels exist to stop.
# Applied per rack rather than declared on the layout because a rack that
# spends slot 6 on resonance instead would not pair, and then the plain
# name is the true one.
#
# The cost of pairing, stated once: a paired slot cannot be automated to
# move one half. Where that matters, split them and spend the wildcard.
PAIRED = "Filter + Res"


# ===========================================================================
# The ranges
# ===========================================================================

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
CUTOFF = Range(30.0, 18500.0, "Hz")

# The same reasoning as CUTOFF, applied to the other slots whose engines
# disagree. Each is the INTERSECTION of the native ranges, measured with
# library.Device.range_of, so one knob position means one result on every
# engine. Q14 is what happens when this is skipped: a Volume slot bound
# correctly on both engines that silenced one and not the other.
#
#   Release   Wavetable 0.0015..20 s, Drift 0.01..60 s, Meld 0.0015..40 s
#   Resonance Wavetable 0..1.25,      Drift 0..1.01,    Meld 0..1
#   Volume    Wavetable 0..1,         Drift 0..1,       Meld 0..1.995
RELEASE = Range(0.01, 20.0, "s")
RESONANCE = Range(0.0, 1.0, "")
VOLUME = Range(0.0, 1.0, "amplitude")

# The same range, in the units Operator and Simpler keep their envelope
# times in. Both read 1..60000 on `Operator.0/Envelope/ReleaseTime` and
# `VolumeAndPan/Envelope/ReleaseTime`, against 0.0015..20 on Wavetable and
# 0.01..60 on Drift: milliseconds, not seconds. So the two scales cover the
# same 60 s ceiling and RELEASE is the intersection of all five, expressed
# twice.
#
# Writing RELEASE on these two would bind the slot to 0.01..20 MILLISECONDS,
# a knob whose whole travel is inside one click of the attack. Leaving it
# unranged, which is what the code did until it was measured, gives the full
# 1 ms..60 s instead: playable, and three times the sweep the other engines
# get at the same knob position.
#
# The unit is inferred from the numbers, not read anywhere, which is why
# `Range` states it. What supports it is the donor defaults: Operator sits
# at 400 and Simpler at 50, which are Live's stated 400 ms and 50 ms, and
# are absurd as seconds.
RELEASE_MS = RELEASE.scaled(1000.0)

# Glide, and the same unit split as release: Operator keeps portamento in
# MILLISECONDS at 0.1..10000, Wavetable in seconds at 0..20, Drift in
# seconds at 0..2. So the intersection is 0.01..2 s, and Drift is what
# caps it.
#
# H3b is why this is ranged rather than left native. Operator's full
# 0.1..10000 ms through a logarithmic taper (Q15) puts the geometric mean
# at macro 64, which is 32 ms: a glide nobody can hear across half the
# knob's travel. Ranged, macro 64 lands near 140 ms, which is a glide.
GLIDE = Range(0.01, 2.0, "s")
GLIDE_MS = GLIDE.scaled(1000.0)

# Volume ranges below are capped at each engine's own unity and no lower.
# What an engine PUTS OUT at unity differs by about 12 dB across these four,
# and correcting for that is gain staging: a measurement taken by ear in one
# Set, on one set of patches, that a spec cannot state and a test cannot
# check. It was in this file as a table of measured peaks and is now in
# `THE_BASEMENT.md` with the numbers. Trim on the mixer.


# ===========================================================================
# The engines
# ===========================================================================

# One value per device, declared once and used by every rack that wants it.
# `drives` is what this engine always does; `offers` is what it CAN do if a
# rack spends its wildcard slot on that role. A rack asks the whole family
# for one role and the engines that lack it stay silent, which is what makes
# the wildcard a decision instead of a leftover.
#
# Every path here was read from library.Device.search, not from memory. The
# gaps in `offers` are real:
#
#   saturation  only Operator has a shaper. Drift, Wavetable and Meld have
#               nothing that is a saturator rather than a waveshaper or an
#               oscillator control.
#   morph       only Meld, whose filter Macro2 is the L-B-H-N morph. Q10.
#   glide       everywhere, under four different names.

# The two `sets` are H6, and they are Q16 one device over. Operator ships
# with `Lfo/LfoOn` false and `Filter/LfoOn` false, so Macro 5 drove the
# AMOUNT of a switched-off LFO into a filter it was not connected to. The
# knob moved, the mapping resolved, nothing happened. Both are plain
# booleans read off the donor, not an enum anybody guessed.
#
# Safe on every rack that uses FM, because Movement declares no start: the
# macro opens at 0, so the LFO is enabled and contributing nothing until
# the knob is turned.
FM = (Engine("Operator")
      .sets("Lfo/LfoOn", True)
      .sets("Filter/LfoOn", True)
      .drives(PB.filter, "Filter/Frequency", over=CUTOFF)
      .drives(PB.filter, "Filter/Resonance", over=RESONANCE)
      .drives(PB.drive, "Filter/Drive")
      .drives(PB.movement, "Lfo/LfoAmount")
      .drives(PB.release, "Operator.0/Envelope/ReleaseTime", over=RELEASE_MS)
      # Linear amplitude, native range 0.000316..1.995, capped at unity.
      # The floor is -70 dB, well below Simpler's -36.
      .drives(PB.volume, "Globals/Volume",
              over=Range(0.0003162277571, 1.0, "amplitude"))
      .offers("attack", "Operator.0/Envelope/AttackTime")
      .offers("glide", "Globals/PortamentoTime", over=GLIDE_MS)
      .offers("saturation", "Shaper/Drive"))

# The SAME layout slots as FM, on different synthesis. That correspondence
# is the sound family constraint: one knob moves the same musical idea
# through Operator and through Simpler.
SAMPLER = (Engine("OriginalSimpler")
           .drives(PB.filter, "Filter/Slot/Value/SimplerFilter/Freq", over=CUTOFF)
           .drives(PB.filter, "Filter/Slot/Value/SimplerFilter/Res", over=RESONANCE)
           .drives(PB.drive, "Filter/Slot/Value/SimplerFilter/Drive")
           .drives(PB.movement, "Pitch/PitchLfoAmount")
           .drives(PB.release, "VolumeAndPan/Envelope/ReleaseTime", over=RELEASE_MS)
           # Decibels, native range -36..+36, capped at unity. The floor is
           # -36 dB because that is all Simpler offers: audible, where
           # Operator's floor is -70.
           .drives(PB.volume, "VolumeAndPan/Volume", over=Range(-36.0, 0.0, "dB"))
           .offers("attack", "VolumeAndPan/Envelope/AttackTime")
           .offers("glide", "Globals/PortamentoTime", over=GLIDE_MS))

# Wavetable leaves Movement empty, deliberately. Its LFO depth lives in a
# modulation matrix that is not in the parameter list at all, and
# `Lfo1_Shape_Amount` is a waveshaper rather than a depth, so binding it
# would be inventing intent. An engine that cannot serve a slot leaves it
# empty.
WAVE = (Engine("InstrumentVector")
        .drives(PB.filter, "Voice_Filter1_Frequency", over=CUTOFF)
        .drives(PB.filter, "Voice_Filter1_Resonance", over=RESONANCE)
        .drives(PB.drive, "Voice_Filter1_Drive")
        .drives(PB.release, "Voice_Modulators_AmpEnvelope_Times_Release",
                over=RELEASE)
        .drives(PB.volume, "Volume", over=VOLUME)
        .offers("attack", "Voice_Modulators_AmpEnvelope_Times_Attack")
        .offers("glide", "Voice_Global_Glide", over=GLIDE))

# No Drive: Drift exposes no drive parameter at all.
#
# Envelope1 is Drift's amp envelope, which was inferred from Envelope2
# having a Global_Envelope2Mode and Envelope1 not, and is now gated in Live
# 12.4.3: C1 held a note and heard the tail follow this macro.
#
# The three `sets` are Q16. Drift's modulation ROUTING is not in the
# parameter list: `ModulationMatrix_Target1` is a bare Value with no
# `Manual`, so nothing can drive it and a rack has to state it. Source 2 is
# the LFO and target 6 is LP Frequency, both read off `racks/q16_a.adg`
# rather than counted off Live's dropdown. Without them Macro 5 bound
# `Lfo_Amount`, resolved, wrote a valid mapping and moved nothing.
#
# Row 1 at full depth, because the macro is the depth control: Macro 5
# scales the LFO's own output into a route that is already wide open.
# Whether `Lfo_Amount` really gates the row is Q16b and is the one thing
# here that ears decide.
#
# Writing the row also stamps out the donor's, `Source1=5, Target1=8`,
# which is something modulating the HIGH-PASS at 80% that nobody asked for
# and that every Drift built here carried until this existed.
DRIFT = (Engine("Drift")
         .sets("ModulationMatrix_Source1", 2)
         .sets("ModulationMatrix_Target1", 6)
         .sets("ModulationMatrix_Amount1", 1.0)
         .drives(PB.filter, "Filter_Frequency", over=CUTOFF)
         .drives(PB.filter, "Filter_Resonance", over=RESONANCE)
         .drives(PB.movement, "Lfo_Amount")
         .drives(PB.release, "Envelope1_Release", over=RELEASE)
         .drives(PB.volume, "Global_Volume", over=VOLUME)
         .offers("attack", "Envelope1_Attack")
         .offers("glide", "Global_Glide", over=GLIDE))

# Meld is two synthesis engines behind one device, and every A-side path has
# a B twin, so each slot names both. Binding only A was gated in Live 12.4.3
# as C2 and failed exactly as suspected: Macro 3 filtered half the sound and
# left the other half open, which passes every structural check there is.
#
# Both sides move together because this layout has one Filter knob, not an A
# knob and a B knob. Splitting them would be a second axis, and a Push page
# has no room for one.
#
# Q10: the filter's two knobs are `Macro1` (Q) and `Macro2` (L-B-H-N morph),
# and that pairing holds for FilterType 0 only. A rack asking for `morph` on
# a Meld whose filter type has been changed gets a valid mapping onto a
# different control. Nothing detects that.
MELD = (Engine("InstrumentMeld")
        .drives(PB.filter, "MeldVoice_EngineA_Filter_Frequency",
                "MeldVoice_EngineB_Filter_Frequency", over=CUTOFF)
        .drives(PB.filter, "MeldVoice_EngineA_Filter_Macro1",
                "MeldVoice_EngineB_Filter_Macro1", over=RESONANCE)
        # Drive is device-wide on Meld, one parameter for both engines.
        .drives(PB.drive, "MeldVoice_Drive")
        .drives(PB.release, "MeldVoice_EngineA_AmpEnvelope_Times_Release",
                "MeldVoice_EngineB_AmpEnvelope_Times_Release", over=RELEASE)
        # Volume is device-wide too.
        .drives(PB.volume, "Volume", over=VOLUME)
        .offers("attack", "MeldVoice_EngineA_AmpEnvelope_Times_Attack",
                "MeldVoice_EngineB_AmpEnvelope_Times_Attack")
        .offers("glide", "MeldVoice_EngineA_GlideTime",
                "MeldVoice_EngineB_GlideTime", over=GLIDE)
        .offers("morph", "MeldVoice_EngineA_Filter_Macro2",
                "MeldVoice_EngineB_Filter_Macro2"))


# ===========================================================================
# The instrument racks
# ===========================================================================

def sound_family(rack: Rack) -> list:
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
        out.append(PB.variation(
            # The name encodes its own values, so culling by ear is informed
            # rather than blind. KICKOFF.md asks for this.
            f"{i:03d} {eng[0]} f{cut} r{rel} c{chr_}",
            instrument=rack.engine_macro(eng),
            filter=cut, release=rel, character=chr_))
    return out


# Pads. Operator and Simpler, the pair gated in Live 12.4.3. Kept as the
# verified slice: 96 variations, both engines answering one layout. PD1W
# below is what the spec actually calls for.
_PD1 = (Rack.instrument("PD1", PB)
        .spends(PB.character, "attack")
        .label(PB.filter, PAIRED)
        .chain("FM", FM)
        .chain("Sample", SAMPLER))
PD1 = _PD1.variations(*sound_family(_PD1))

# Pads proper: lush wavetable. Slot 6 is ATTACK, because a pad is played
# into: a pad you cannot soften is a stab, and softening is most of what
# separates the two.
PD1W = (Rack.instrument("PD1W", PB)
        .spends(PB.character, "attack")
        .label(PB.filter, PAIRED)
        .chain("Wave", WAVE)
        .chain("Drift", DRIFT))

# Multi engine bass. Three syntheses, one layout. Slot 6 is MORPH.
#
# Only Meld can serve morph, so Wavetable and Drift leave slot 6 empty. That
# is the rule working, not a hole: the alternative is binding three different
# ideas to one knob and calling it consistency.
#
# `PATCHBAYGROUND.md` asks for saturation as the bass wildcard, and it is not
# available. Of the engines in this file only Operator has a shaper, and
# Operator is not in this rack.
BS1 = (Rack.instrument("BS1", PB)
       .spends(PB.character, "morph")
       .label(PB.filter, PAIRED)
       .chain("Wave", WAVE)
       .chain("Drift", DRIFT)
       .chain("Meld", MELD))

# Leads. FM first, per the spec, with Meld as the second colour. Slot 6 is
# GLIDE, the one control a lead needs that a pad does not, and the rack where
# the wildcard pays best: a mono lead lives on portamento.
# H3: the glide TIME moved and nothing glided, because Operator ships with
# `Globals/PortamentoOn` false. The enable sits on the rack rather than in
# `FM`, because it belongs to the ROLE: PD1 and VA1 use the same profile
# and spend slot 6 on attack, and turning portamento on there would smear
# every pad they play. Only the rack that spends glide wants it.
#
# Meld's half is NOT here. Its `MeldVoice_Engine{A,B}_GlideMode` is 0, an
# enum nobody has diffed, and rule 1 says a mode that is probably off is
# exactly what must not be guessed. See E6.
LD1 = (Rack.instrument("LD1", PB)
       .spends(PB.character, "glide")
       .label(PB.filter, PAIRED)
       .chain("FM", FM.sets("Globals/PortamentoOn", True))
       .chain("Meld", MELD))


# ===========================================================================
# VA1 - nesting
# ===========================================================================

# Various. Each chain is a rack in its own right.
#
# Two levels rather than the five racks the spec eventually wants, which are
# blocked on donors. What this exercises is the nesting itself: the outer
# Instrument macro picks a sub-rack, and every other slot chains
# macro-to-macro into whichever sub-rack is selected.
#
# Instrument is left OUT of the chaining. The identity default would also
# drive each sub-rack's own Instrument macro, which is the pattern
# racks/s1_source.adg uses, but here it would mean one knob doing two jobs
# at once.
VA_PADS = Rack.instrument("PADS", PB).chain("Sample", SAMPLER).chain("FM", FM)
VA_KEYS = Rack.instrument("KEYS", PB).chain("FM", FM)

CHAINED = (PB.filter, PB.drive, PB.movement, PB.character,
           PB.release, PB.volume)

_VA1 = (Rack.instrument("VA1", PB)
        .chain("PADS", VA_PADS.chaining(*CHAINED))
        .chain("KEYS", VA_KEYS.chaining(*CHAINED)))

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


# ===========================================================================
# DR1 - the drum rack, three levels
# ===========================================================================

# The drum rack's top level is NOT the instrument layout. Eight pads times
# eight parameters cannot fit eight knobs, so the top level is kit-wide
# moves only and per-pad control is reached by diving into the pad on Push.
#
# No slot selects: a drum rack has no chain selector to drive, because a pad
# is chosen by its ReceivingNote and Live leaves every pad's zone at
# 0/0/0/0. Macro 1 here chains into each pad's own Sound knob instead.
#
# The starts matter twice over here: a kit macro at 0 drives the PAD macro
# to 0, which drives the sample's volume to its floor. Pitch and the sends
# are unbound, so their start is not written.
#
# The kit's Filter chains into each pad's Filter, which is paired, so the kit
# knob moves cutoff and resonance on eight pads at once and says so.
KIT = Layout(
    Slot("Sound"),
    Slot("Pitch"),
    Slot("Filter", start=127, label=PAIRED),
    Slot("Drive"),
    Slot("Send A"),
    Slot("Send B"),
    Slot("Send Vol"),
    Slot("Volume", start=127),
)

# Inside a pad the axis is WHICH SAMPLE, so the selector slot is Sound
# rather than Instrument. Same eight slots as PB, carrying the same starts,
# so the kit can chain slot to slot by identity; only which slot drives the
# selector moves, and the `>` mark moves with it.
PAD = PB.deriving(selects=PB.sound)

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

# What a pad calls its knobs, over the shared pairing. The layout is
# positional: same slot, same chaining, different word, which is the drum
# rack form of the slot 6 wildcard. A kick's slot 4 is where its snap lives,
# so it says so; a hat's is plain drive.
PAD_LABELS = {
    "KICK": "Drive + Snap",
    "SNARE": "Drive + Snap",
}

# A pad's Simpler is the SAMPLER profile without Movement: inside a pad that
# slot is spent on the sample list, not on an LFO.
PAD_VOICE = (Engine("OriginalSimpler")
             .drives(PB.filter, "Filter/Slot/Value/SimplerFilter/Freq",
                     over=CUTOFF)
             .drives(PB.filter, "Filter/Slot/Value/SimplerFilter/Res",
                     over=RESONANCE)
             .drives(PB.drive, "Filter/Slot/Value/SimplerFilter/Drive")
             .drives(PB.release, "VolumeAndPan/Envelope/ReleaseTime",
                     over=RELEASE_MS)
             .drives(PB.volume, "VolumeAndPan/Volume", over=Range(-36.0, 0.0, "dB"))
             .offers("attack", "VolumeAndPan/Envelope/AttackTime"))


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

    rack = (Rack.instrument(name, PAD)
            .spends(PB.character, "attack")
            .label(PB.filter, PAIRED))
    if name in PAD_LABELS:
        rack = rack.label(PB.drive, PAD_LABELS[name])
    for i, wav in enumerate(files):
        rack = rack.chain(f"S{i + 1}", PAD_VOICE.sample(wav))
    return rack


# The two returns every pad can reach, and the selector inside each. A
# return is a chain like any other, so a rack goes in one and the knob swaps
# the EFFECT rather than only its level.
#
# Short and long, because that is the pair worth having on one kit: a room
# that thickens a snare without smearing the grid, and a tail that survives
# past the next hit.
FX = Layout(Slot("Effect", selects=True), Slot("Amount"), Slot("Tone", start=64))

SHORT_FX = (Rack.audio_effect("A-Short", FX)
            .chain("room", Engine("Hybrid")
                   .drives(FX.amount, "DryWet")
                   .drives(FX.tone, "Algorithm_Damping"))
            .chain("slap", Engine("Delay")
                   .drives(FX.amount, "DryWet")
                   .drives(FX.tone, "Filter_Frequency")
                   .sets("Filter_On", True)))

LONG_FX = (Rack.audio_effect("A-Long", FX)
           .chain("hall", Engine("Hybrid")
                  .drives(FX.amount, "DryWet")
                  .drives(FX.tone, "Algorithm_Decay"))
           .chain("echo", Engine("Echo")
                  .drives(FX.amount, "DryWet")
                  .drives(FX.tone, "Filter_LowPassFrequency")
                  .sets("Filter_On", True)))


def dr1() -> Rack | None:
    """The drum rack: eight pads, each a rack of samples. Three levels.

    Returns None when `samples/` is absent, so this file still imports on a
    machine that has the repo and not the audio. That is not politeness: the
    test suite imports this module.

    Kit macros chain into every pad at once. Sound is the interesting one:
    one knob walks the sample choice across the whole kit, and a pad can be
    dived into on Push to move its own.

    **Slots 5 and 6 mean different things at different depths, and that is
    decided rather than accidental.** At kit level they are the two sends,
    because a send is a kit-level idea: it exists once per return and every
    pad has one. Inside a pad they stay Movement and Character, which is
    what a single voice has to offer. The cost is that the layout is a
    contract per LEVEL rather than per rack, and the label on each knob is
    what says which level you are on.
    """
    kit = (Rack.drum("DR1", KIT)
           # `unchained`, not `chaining`: a return's effects answer their
           # own three knobs and no kit knob at all. The kit reaches a return
           # through its send, which is what `sending` writes.
           .ret("A-Rvb:Short", SHORT_FX.unchained())
           .ret("A-Dly:Long", LONG_FX.unchained())
           .sending(KIT.send_a, "A-Rvb:Short")
           .sending(KIT.send_b, "A-Dly:Long"))
    chained = (KIT.sound, KIT.filter, KIT.drive, KIT.volume)

    built = 0
    for name, note, sound in PADS:
        inner = pad_rack(name, sound)
        if inner is None:
            continue
        kit = kit.pad(name, note, inner.chaining(*chained))
        built += 1

    return kit if built else None


DR1 = dr1()


# ===========================================================================
# The channel strip
# ===========================================================================
#
# Every track carries the same devices in the same order:
#
#     ARP1   MFX1   <instrument>   EQC   AFX1   AFXS1   Channel EQ   VOL1
#
# These four are racks with their own layouts. They do NOT share PB: an
# arpeggiator has no Filter knob and pretending otherwise would put the word
# on a macro that moves nothing. What they share is the shape - eight slots
# at most, one Push page, a slot left empty rather than invented.
#
# A strip rack is a SERIES: several devices in one chain, one set of macros
# across all of them. That is the opposite shape from an instrument rack,
# where each chain is an alternative rather than a stage.


ARP = Layout(
    Slot("Style"),          # which arpeggio pattern
    Slot("Rate"),
    Slot("Retrigger"),
    Slot("Chance"),         # how often a note is replaced
    Slot("Choices"),        # how far the replacement may stray
    Slot("Steps"),
    Slot("Gate"),
    Slot("Vel Rand"),
)

# Three MIDI devices in series. Style and Retrigger sweep enums rather than
# switching them on: Live stores both as plain numbered modes, and a knob
# that walks the mode list is a control in its own right. Nothing here
# guesses which number means which mode, because nothing here has to.
ARP1 = Rack.midi_effect("ARP1", ARP).chain(
    "strip",
    Engine("MidiArpeggiator")
    .drives(ARP.style, "Mode")
    .drives(ARP.rate, "SyncedRate")
    .drives(ARP.retrigger, "Retrigger")
    .drives(ARP.steps, "TransposeSteps")
    .drives(ARP.gate, "Gate", over=Range(1.0, 200.0, "%"))
    .then(Engine("MidiRandom")
          .drives(ARP.chance, "Chance")
          .drives(ARP.choices, "Choices"))
    .then(Engine("MidiVelocity")
          .drives(ARP.vel_rand, "Random")))


MFX = Layout(
    Slot("Vel Range"),
    Slot("Vel Rand"),
    Slot("Pitch"),
    Slot("Root"),
    Slot("Transpose"),
)

# Scale Selector is in PATCHBAYGROUND.md and is NOT here: MidiScale stores a
# scale as twelve `Mapping.N` parameters, one per semitone, and no single
# parameter selects a named scale. Binding one knob to twelve mappings would
# be a different control from the one the spec asks for. Root and Transpose
# are real parameters and are bound.
MFX1 = Rack.midi_effect("MFX1", MFX).chain(
    "strip",
    Engine("MidiVelocity")
    .drives(MFX.vel_range, "Range")
    .drives(MFX.vel_rand, "Random")
    .then(Engine("MidiPitcher").drives(MFX.pitch, "Pitch"))
    .then(Engine("MidiScale")
          .drives(MFX.root, "Base")
          .drives(MFX.transpose, "Transpose")))


EQ = Layout(
    Slot("Lo", start=64),
    Slot("Mid", start=64),
    Slot("Hi", start=64),
    Slot("Comp", start=127),
    Slot("Duck", start=127),
    Slot("Gain", start=64),
)

#: The sidechain band. 100 Hz tracks a kick and misses a hat, which is what
#: PATCHBAYGROUND.md asks the EQC compressor to hear. Q is the donor's own.
SIDECHAIN_HZ = 100.0

# The three shelf knobs open at centre rather than at full: an EQ's neutral
# is 0 dB in the middle of its range, not the top of it.
#
# The sidechain is CONFIGURED here and its SOURCE is not, because a device
# preset does not carry one - see Q18 in SCHEMA.md. Dropped on a track this
# arrives with External on, the band set, and one dropdown left to fill.
EQC = Rack.audio_effect("EQC", EQ).chain(
    "strip",
    Engine("ChannelEq")
    .drives(EQ.lo, "LowShelfGain")
    .drives(EQ.mid, "MidGain")
    .drives(EQ.hi, "HighShelfGain")
    .then(Engine("Compressor2")
          .drives(EQ.comp, "DryWet")
          .drives(EQ.duck, "SideChain/DryWet")
          .sets("SideChain/OnOff", True)
          .sets("SideChainEq/On", True)
          .sets("SideChainEq/Freq", SIDECHAIN_HZ))
    .then(Engine("StereoGain")
          .drives(EQ.gain, "Gain", over=Range(-12.0, 12.0, "dB"))))


AFX = Layout(
    Slot("Effect", selects=True),
    Slot("Amount"),
    Slot("Tone", start=64),
    Slot("Motion"),
)

# Eight character effects behind ONE selector, so the knob swaps the effect
# rather than layering it. Parallel audio chains are expensive; a selector is
# not, and eight chains cost one macro instead of eight.
#
# Every chain answers the same three knobs. That is the instrument-rack idea
# one level up: Amount means "how much of whatever is selected", so the pair
# of knobs is playable before you know which effect you landed on.
#
# Which device serves which role is a taste call. This is a first pass over
# the spread PATCHBAYGROUND.md asks for - degradation, time and space rather
# than eight flavours of one idea - and swapping one is a one-line edit.
AFX1 = (Rack.audio_effect("AFX1", AFX)
        .chain("glitch", Engine("BeatRepeat")
               .drives(AFX.amount, "Chance")
               .drives(AFX.tone, "MidFreq")
               .drives(AFX.motion, "Grid")
               # The filter is what Tone reaches, and it ships off. A knob
               # bound to a switched-off filter is Q16 all over again.
               .sets("FilterOn", True))
        .chain("tear", Engine("Roar")
               .drives(AFX.amount, "Stage1_Shaper_Amount")
               .drives(AFX.tone, "Input_ToneAmount")
               .drives(AFX.motion, "Feedback_FeedbackAmount"))
        .chain("erode", Engine("Erosion")
               .drives(AFX.amount, "Amplitude")
               .drives(AFX.tone, "Freq")
               .drives(AFX.motion, "BandQ"))
        .chain("grind", Engine("Overdrive")
               .drives(AFX.amount, "Drive")
               .drives(AFX.tone, "Tone")
               .drives(AFX.motion, "DryWet"))
        .chain("reduce", Engine("Redux2")
               .drives(AFX.amount, "DryWet")
               .drives(AFX.tone, "SampleRate")
               .drives(AFX.motion, "Jitter"))
        .chain("soak", Engine("Hybrid")
               .drives(AFX.amount, "DryWet")
               .drives(AFX.tone, "Algorithm_Damping")
               .drives(AFX.motion, "Algorithm_Decay"))
        .chain("stretch", Engine("Spectral")
               .drives(AFX.amount, "DryWet")
               .drives(AFX.tone, "Delay_FrequencyShift")
               .drives(AFX.motion, "Delay_Feedback"))
        .chain("fade", Engine("GrainDelay")
               .drives(AFX.amount, "NewDryWet")
               .drives(AFX.tone, "Pitch")
               .drives(AFX.motion, "Spray")))


# The second effect slot. Same layout as AFX1, so the two knobs mean the
# same thing in both, and a deliberately different spread: AFX1 is
# degradation, this is movement and space. `PATCHBAYGROUND.md` calls AFXS1
# "freely editable", which is a rack to REPLACE chains in rather than a rack
# to leave alone, and a shared layout is what makes replacing one cheap.
AFXS1 = (Rack.audio_effect("AFXS1", AFX)
         .chain("swirl", Engine("Chorus2")
                .drives(AFX.amount, "DryWet")
                .drives(AFX.tone, "Warmth")
                .drives(AFX.motion, "Rate"))
         .chain("sweep", Engine("PhaserNew")
                .drives(AFX.amount, "DryWet")
                .drives(AFX.tone, "CenterFrequency")
                .drives(AFX.motion, "Modulation_Amount"))
         .chain("ring", Engine("Resonator")
                .drives(AFX.amount, "DryWet")
                .drives(AFX.tone, "ResColor")
                .drives(AFX.motion, "ResDecay"))
         .chain("echo", Engine("Echo")
                .drives(AFX.amount, "DryWet")
                .drives(AFX.tone, "Filter_LowPassFrequency")
                .drives(AFX.motion, "Feedback")
                # Echo's filter section ships off, so Tone would reach a
                # bypassed filter. Q16 again, on a third device.
                .sets("Filter_On", True)))


VOL = Layout(
    Slot("Sub Cut"),
    Slot("Pre Gain", start=64),
    Slot("Ceiling", start=127),
    Slot("Release", start=64),
)

# Last on the strip. Sub-Cut is Channel EQ's high-pass SWITCH rather than a
# swept frequency: it is a plain boolean, where a swept cut would need
# Eq8's band Mode, an enum nothing here has diffed. Q21.
#
# The limiter is what makes this the last device: Pre Gain pushes into it
# and Ceiling says where the output stops.
VOL1 = Rack.audio_effect("VOL1", VOL).chain(
    "strip",
    Engine("ChannelEq").drives(VOL.sub_cut, "HighpassOn")
    .then(Engine("StereoGain")
          .drives(VOL.pre_gain, "Gain", over=Range(-12.0, 12.0, "dB")))
    .then(Engine("Limiter")
          .drives(VOL.ceiling, "Ceiling", over=Range(-24.0, 0.0, "dB"))
          .drives(VOL.release, "Release", over=Range(10.0, 3000.0, "ms"))
          # Release is bound, so the limiter must not be choosing its own.
          .sets("AutoRelease", False)))


STRIP: list[Rack] = [ARP1, MFX1, EQC, AFX1, AFXS1, VOL1]

RACKS: list[Rack] = [r for r in (PD1, PD1W, BS1, LD1, DR1, VA1) if r is not None] + STRIP


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
# Movement are in the layout but nothing binds them, and a variation may
# only set a slot something answers to - the DSL refuses the rest rather
# than writing a knob wired to nothing. Adding those bindings widens the
# grid with no change to the variation code.


# ---------------------------------------------------------------------------
# Aftertouch. Blocked on: SPIKES.md Q2, nothing is known about how it is
# stored. Probably a sibling of the KeyMidi mechanism, but that is a guess.
# ---------------------------------------------------------------------------
#
# Every sound maps aftertouch to filter and pitch. Drum pads are excluded,
# because Push does not send per pad aftertouch there.
#
# FM.aftertouch(PB.filter, "Filter/Frequency").aftertouch(PB.pitch, ...)


# ---------------------------------------------------------------------------
# DR1's deeper pad. Blocked on: donors for MidiPitcher and Saturator in a
# pad, and Q6 for the return selectors. The pad shape below is what
# PATCHBAYGROUND.md asks for and what DR1 is a two-device slice of.
# ---------------------------------------------------------------------------
#
#     Drum Rack                    kit macros only
#     └─ Pad chain
#        └─ Pad rack "KICK"        the 8 pad knobs
#           ├─ MidiPitcher         Tune
#           ├─ Engine rack         Sound, decay, filter
#           │  ├─ Simpler x4       sample chains, zones distributed
#           │  └─ Operator         FM layer, zone spans full 0-127
#           └─ Saturator           Drive
#
# Macros chain to macros: kit Sound drives pad Sound drives engine Sound
# drives the chain selector. Verified working three levels deep in
# racks/s1_source.adg.
#
# engines = (Rack.instrument("ENGINE", PAD)
#            .chain("S1", PAD_VOICE.sample(wav))
#            # The FM layer spans the whole selector rather than taking a
#            # slice, so it can blend under any sample.
#            .chain("FM", FM.zone(0, 127)))
#
# pad = (Rack.instrument("PAD", PAD)
#        .chain("Tune", Engine("MidiPitcher").drives(PAD.pitch, "Pitch/TransposeKey"))
#        .chain("ENGINE", engines.chaining(PAD.sound, PAD.filter, PAD.release))
#        .chain("Drive", Engine("Saturator").drives(PAD.drive, "PreDrive")))
#
# DR1's returns live inside the drum rack. Each holds a SELECTOR across
# several reverbs and delays, so a macro swaps the effect rather than only
# its send level. Blocked additionally on Q6.


# ---------------------------------------------------------------------------
# The other instrument racks. Blocked on: donors and samples.
# ---------------------------------------------------------------------------
#
# SR1 is a sampler rack with built in sounds plus a hot swap slot, and wants
# a sample set chosen by ear rather than by the loop in `pad_rack`.
#
# VA1 above holds two sub-racks. Widening it to the five the spec names is
# `for inner in (DR1, BS1, PD1, LD1, SR1)`, and waits only on those racks
# existing.


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
#     s.track("DR1", DR1)
#     s.track("BS1", BS1)
#     s.track("PD1", PD1)
#     s.track("LD1", LD1)
#     s.track("SR1", sr1())
#     s.track("VA1", VA1)
#     s.track("VA2", VA1)
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
