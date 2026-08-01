"""EXAMPLE_TECHNO - a donor Set read back into a spec.

Reverse engineered from `donors/BerlinTechno/BerlinTechno.als`, a Live
11.0.11 Set at 135 BPM, with `patchbay extract` and one-question scripts
over the parsed tree. Every binding, range, note and macro position below
was read out of that file. Nothing here was written from memory.

    patchbay build examples/techno.py -o build/techno/
    patchbay session examples/techno.py -o build/techno.als

`examples/playgrnd.py` is this project's own target and is designed
from the layout outward. This file is the opposite exercise: somebody
else's Set, read back. What it is for is the comparison, and
`doc/EXAMPLE_TECHNO.md` is where that is written down.

## What this file covers, and what it leaves

The Set is one drum rack plus seven synth tracks. The DRUM rack is the
part with architecture in it, so it is what this rebuilds:

| Built | |
|---|---|
| 8 Select racks | one layout, one engine profile, eight instances |
| 4 FX rack designs | the series racks each pad runs into |
| the kit | 8 pads at their own notes, 4 internal returns |
| the Set | one MIDI track at 135 BPM |

| Not built | why |
|---|---|
| a pad as ONE chain | a chain holds a series of devices OR one nested rack, never a rack followed by devices. Every pad in this Set is that shape |
| Amb 1 | same gap, plus `MxDeviceAudioEffect`, a Max for Live device that is not stock content and is not ours to vendor |
| Perc 1, 2, 3, Bass, Lead, Amb 2 | loose devices on a track, no rack, nothing to learn from |
| the 'Dry' parallel chain of `RIDE_DELAY` | a chain with no devices at all has no syntax |
| return-to-return sends | `ret()` takes no `sends=`; the two delay returns feed the reverb at 0.1413 in the donor |

The pad gap is the one that matters and it is not cosmetic. In the donor a
pad chain is

    [Select rack] -> [FX rack] -> Eq8 -> StereoGain

so the pad racks and the FX racks below are built as SEPARATE presets, and
putting one after the other is by hand until a chain can hold both. That
is one entry in `doc/TODO.md`, not a workaround hiding here.
"""

from __future__ import annotations

from pathlib import Path

from patchbay import live_set, samples
from patchbay.dsl import Engine, Layout, Rack, Range, Slot
from patchbay.live_set import Session, Track

# ===========================================================================
# The samples
# ===========================================================================

#: The donor Project's audio, beside the `.als` it came with.
#:
#: Point this at any folder of drum one-shots and the kit rebuilds from it.
#: Nothing below names a file: the pads carry a CATEGORY word and the first
#: sorted match wins, which is what keeps a vendor's filenames out of a
#: tracked file. `samples/README.md` is the standing rule and it applies to
#: a donor Project folder exactly as it applies to `samples/`.
SAMPLE_ROOT = (
    Path(__file__).resolve().parent.parent / "samples" / "all" / "techno"
)


def find_sample(category: str) -> Path | None:
    """The first audio file whose name contains `category`. None if absent.

    Case insensitive, sorted, recursive. Returning None rather than raising
    is what lets this module import on a machine that has the repo and not
    the audio, the same way `patchbaygrnd_fetch_samples.py` does it: the
    test suite imports this file.
    """
    want = category.lower()
    for path in samples.audio(SAMPLE_ROOT, recursive=True):
        if want in path.name.lower():
            return path
    return None


# ===========================================================================
# The pad layout
# ===========================================================================

# EIGHT SLOTS, IDENTICAL ON ALL EIGHT PADS.
# Select racks in the donor carry the same ten bindings over the same ten
# ranges, macro for macro, and differ only in where the knobs are parked and
# which sample is loaded. One design, eight instances, arrived at by hand in
# a Set that has no code in it.
#
# Here there is one engine per pad (a Sampler), so a slot is named
# for the signal path it moves - HPF, LPF, PAN, VOLUME, DECAY.
# A layout is only as abstract as it has to be.
#
# No slot selects. `SAMPLE SELECTR` looks like a selector and is not one: it
# drives the Sampler's own `Player/SampleSelector`, which walks multisample
# ZONES inside one device rather than chains inside a rack. See the note on
# `VOICE`.
#
# The starts here are the ones every pad shares; a pad overrides its own
# below. PAN at 63.5 is centre over -1..1 and PITCH at 63.5 is 0 semitones
# over -48..48, because they are bipolar parameters. HPF at 0 and LPF at
# 127 park both filters wide open, which makes the pair neutral on a fresh drop.
SELECT = Layout(
    Slot("SAMPLE SELECTR"),  # 1  multisample zone, not a chain
    Slot("PITCH", start=63.5),  # 2  0 st, bipolar
    Slot("DECAY", start=85),  # 3  amp decay AND release together
    Slot("SAMPLE START"),  # 4  an aux envelope, see below
    Slot("HPF"),  # 5  Eq8 band 1, high-pass
    Slot("LPF", start=127),  # 6  Eq8 band 8, low-pass
    Slot("PAN", start=63.5),  # 7  centre
    Slot("VOLUME", start=75.9140625),
)


# ===========================================================================
# The ranges
# ===========================================================================

#: Milliseconds. Operator and Simpler keep envelope times in ms over
#: 1..60000. This donor writes the full native span on the mapping,
#: so DECAY sweeps 1 ms to 60 s.
DECAY_MS = Range(1.0, 60000.0, "ms")

#: Semitones. Bipolar, which is why the slot carries a start.
PITCH_ST = Range(-48.0, 48.0, "st")

#: Eq8's full band range, both ends. HPF at 10 Hz and LPF at 22 kHz are
#: outside the audible band, so each knob has a genuine no-op end.
BAND_HZ = Range(10.0, 22000.0, "Hz")

#: Decibels. The donor writes Simpler's whole native span rather than
#: capping at unity, so VOLUME reaches +36 dB. With one engine and a mixer
#: underneath, the wider knob is a defensible call.
VOLUME_DB = Range(-36.0, 36.0, "dB")

#: Linear amplitude, the third scale. Rides along on VOLUME.
LEVEL = Range(0.0003162277571, 1.0, "amplitude")

#: How far SAMPLE START reaches. 0.3 of an aux envelope's decay level.
START_DEPTH = Range(0.0, 0.3000000119, "")


# ===========================================================================
# The voice
# ===========================================================================

# A Sampler into an Eq8, and the Eq8 is not an EQ here. It is a FILTER PAIR
# built out of two bands parked at the ends of their range:
#
#   band 1  mode 1, high-pass, at 10 Hz    HPF sweeps it up
#   band 8  mode 6, low-pass,  at 22000 Hz LPF sweeps it down
#
# Both bands are ON and both are inaudible until a knob moves, so the pad
# gets a playable filter pair without a filter device and without a switch
# in front of it. `playgrnd.py` reaches for the same trick once, in
# `VOL1`, where Sub Cut drives band 1 of an Eq8 after `sets` puts it in mode
# 1. Q21 established that mode number and this donor uses it eight times.
#
# Mode 6 is the donor Eq8's OWN default for band 8, so only `IsOn` is
# written there. Mode 1 is not the default for band 1, which ships as mode
# 2, so that one is set.
#
# DECAY drives decay AND release from one knob. On a one-shot they are the
# same musical idea - how long the hit rings - and splitting them would
# spend two of eight slots on it. The same reasoning as PB's paired
# Filter slot, and it carries the same cost: neither half can be automated
# alone.
#
# **SAMPLE SELECTR moves nothing in this donor, and it is not a bug in the
# rebuild.** `Player/SampleSelector` walks the multisample zones of one
# Sampler. Six of the eight pads hold exactly ONE zone and CLAP and SNARE
# hold none at all, so the knob resolves, carries a 0..127 range, and has
# nowhere to go. That is Q16 exactly - a mapped macro is not a working
# macro - found in somebody else's Set rather than in ours.
#
# It also means the DSL's one-sample-per-device limit (Q3) costs this
# rebuild nothing. There is no second zone to lose.
#
# Declared as its two halves rather than as one series, because `sample`
# belongs to an Engine and `then` returns a Series: once the Eq8 is
# attached there is no Sampler left to point at a file. So a pad composes
# `SAMPLER.sample(path).then(PAD_EQ)` and the order is forced.
SAMPLER = (
    Engine("MultiSampler")
    .drives(SELECT.sample_selectr, "Player/SampleSelector", over=Range(0.0, 127.0))
    .drives(SELECT.pitch, "Pitch/TransposeKey", over=PITCH_ST)
    .drives(
        SELECT.decay,
        "VolumeAndPan/Envelope/DecayTime",
        "VolumeAndPan/Envelope/ReleaseTime",
        over=DECAY_MS,
    )
    # Not a start offset. It is an aux envelope's decay LEVEL, which
    # on a one-shot bites the front off the sound. The knob is named
    # for what it does rather than for what it drives, which is the
    # label-versus-slot split `doc/DSL.md` argues for.
    #
    # **This binding is why `donors/MultiSampler.adg` was replaced
    # out of this very Set.** A Sampler's LFO, Shaper and AuxEnv are
    # SLOTS, and an empty slot contributes no parameters, so a
    # donor's vocabulary depends on which slots were filled when it
    # was saved. The old donor had LFO and Shaper filled, AuxEnv
    # empty, and no `SampleRef` at ALL - 97 parameters, and unable to
    # hold a sample. So parameter count is the wrong tie-break for
    # this device, and the 95-parameter copy is the better donor.
    .drives(
        SELECT.sample_start,
        "AuxEnv/Slot/Value/SimplerAuxEnvelope/DecayLevel",
        over=START_DEPTH,
    )
    .drives(SELECT.pan, "VolumeAndPan/Panorama", over=Range(-1.0, 1.0))
    .drives(SELECT.volume, "VolumeAndPan/Volume", over=VOLUME_DB)
    .drives(SELECT.volume, "VolumeAndPan/Envelope/DecayLevel", over=LEVEL)
)

PAD_EQ = (
    Engine("Eq8")
    .sets("Bands.0/ParameterA/IsOn", True)
    .sets("Bands.0/ParameterA/Mode", 1)  # high-pass, Q21
    .sets("Bands.0/ParameterA/Freq", 10.0)
    .sets("Bands.7/ParameterA/IsOn", True)  # mode 6 is the default
    .sets("Bands.7/ParameterA/Freq", 22000.0)
    .drives(SELECT.hpf, "Bands.0/ParameterA/Freq", over=BAND_HZ)
    .drives(SELECT.lpf, "Bands.7/ParameterA/Freq", over=BAND_HZ)
)


# ===========================================================================
# The eight pads
# ===========================================================================

# Note, category, and the knob positions this pad differs on.
#
# MIDI notes, which is not what the file stores. `ReceivingNote` counts DOWN
# from 128 (Q42), so the donor holds 92, 91, 90 ... and those are notes 36,
# 37, 38. Reading the stored numbers as notes puts the kit off the top of
# the grid, and Live neither refuses nor warns - it opens with eight named
# chains and an empty pad layout.
#
# Decoded, this kit sits on 36..43: the SAME two rows `playgrnd.py`
# lays DR1 out on, reached independently. What differs is the assignment
# inside them. Four to a row from the bottom left:
#
#            A       B       C       D
#   row 7    40 SNARE 41 RIDE 42 TOM  43 PERC
#   row 8    36 KICK  37 CHH  38 OHH  39 CLAP
#
# So the bottom row is kick, both hats and clap, with the hat PAIR adjacent
# in columns B and C. DR1 puts kick, tom, snare and hat on the bottom and
# argues for the strong fingers taking kick and snare. This kit gives that
# second slot to the hats instead, which is the techno reading: the hats
# carry the pattern and the snare is an accent.
#
# `select` is only nonzero on PERC, where it selects nothing (see SAMPLER)
# and is a knob somebody left where they last turned it.
PADS = (
    # name   note category  pitch        decay        lpf          volume      select
    ("KICK", 36, "kick", 63.5, 100.875, 127.0, 71.4492188, 0.0),
    ("CHH", 37, "chh", 63.9960938, 64.6601562, 127.0, 75.9140625, 0.0),
    ("OHH", 38, "ohh", 59.53125, 76.0703125, 127.0, 75.9140625, 0.0),
    ("CLAP", 39, None, 63.5, 85.0, 127.0, 75.9140625, 0.0),
    ("SNARE", 40, None, 63.5, 85.0, 127.0, 75.9140625, 0.0),
    ("RIDE", 41, "ride", 65.484375, 123.695312, 127.0, 58.0546875, 0.0),
    ("TOM", 42, "tom", 63.5, 85.0, 36.2148438, 69.9609375, 0.0),
    ("PERC", 43, "perc", 62.5078125, 91.9453125, 127.0, 50.6132812, 104.675781),
)


def select_rack(name, category, pitch, decay, lpf, volume, select) -> Rack:
    """One pad's Select rack: the shared voice, parked where this pad wants.

    CLAP and SNARE pass `category=None` and get no sample. That is faithful:
    both hold an empty Sampler in the donor and take their sound from the
    Corpus in the FX rack behind them. A pad that loads silent is what the
    donor does, so it is what this writes.
    """
    sampler = SAMPLER
    if category is not None:
        found = find_sample(category)
        if found is not None:
            sampler = sampler.sample(found)
    return (
        Rack.instrument(f"{name} Select", SELECT)
        .chain(name, sampler.then(PAD_EQ))
        .start(SELECT.pitch, pitch)
        .start(SELECT.decay, decay)
        .start(SELECT.lpf, lpf)
        .start(SELECT.volume, volume)
        .start(SELECT.sample_selectr, select)
    )


SELECT_RACKS = [select_rack(*row[:1], *row[2:]) for row in PADS]


# ===========================================================================
# The FX racks
# ===========================================================================
#
# THE TECHNIQUE THIS SET IS ACTUALLY ABOUT.
#
# Every FX rack here puts eight to ten effects IN SERIES, all of them in
# circuit, one macro per effect. The signal goes through all ten. A knob
# is not "which effect" but "how much of this one", so the eight knobs
# are a mixing desk over a fixed chain.
#
# What makes that affordable is the second technique. **One macro drives a
# device's `DryWet` AND its `On` switch.** At 0 the device is BYPASSED, not
# merely dry, so ten devices in series cost nothing until a knob is turned
# and the rack is a menu that pays for what it uses.
#
# That mapping is not a `MidiControllerRange`. A boolean's mapping range is
# `MidiCCOnOffThresholds`, a different element, and this project has never
# written one - `Range` emits the continuous element and nothing else. So
# the `On` bindings below write a `KeyMidi` into the switch and leave the
# thresholds to whatever the donor device carries. Whether that behaves is
# the one thing in this file a person has to check; see the check table in
# `doc/EXAMPLE_TECHNO.md`.
#
# The ranges are the donor's own and several are narrow on purpose:
# Overdrive at 0..50 of a 0..100 DryWet, Amp at 0..0.3, Reverb at 0..0.5.
# A knob that reaches only a third of its target is a knob you cannot ruin
# the sound with.

HAT_FX = Layout(
    Slot("WARM"),
    Slot("ENHANCER"),
    Slot("BRIGHT"),
    Slot("PUNCH"),
    Slot("WIDE NOISE"),
    Slot("AMP"),
    Slot("CRUSH"),
    Slot("REVERB"),
)

# CHH, OHH and RIDE share this one. Ten devices, six macros reaching seven
# of them; the two bare Eq8s at the ends are fixed shaping nobody drives.
#
# BRIGHT is the one worth reading: it lifts a band AND drops the global gain
# over an inverted range, `0..4` against `0..-4`, so the knob tilts the
# spectrum at constant loudness instead of just adding 4 dB. Two parameters,
# one idea, one knob.
HAT_STRIP = Rack.audio_effect("HAT FX", HAT_FX).chain(
    "Chain",
    Engine("Eq8")
    .then(Engine("Saturator").drives(HAT_FX.warm, "DryWet", over=Range(0.0, 1.0)))
    .then(Engine("Overdrive").drives(HAT_FX.enhancer, "DryWet", over=Range(0.0, 50.0)))
    .then(Engine("Amp").drives(HAT_FX.amp, "DryWet", over=Range(0.0, 0.3000000119)))
    .then(Engine("Redux").drives(HAT_FX.crush, "SampleResSoft", over=Range(1.0, 5.0)))
    .then(
        Engine("Eq8")
        .drives(HAT_FX.bright, "Bands.3/ParameterA/Gain", over=Range(0.0, 4.0))
        .drives(HAT_FX.bright, "GlobalGain", over=Range(0.0, -4.0))
    )
    .then(
        Engine("Erosion")
        .drives(HAT_FX.wide_noise, "On")
        .drives(HAT_FX.wide_noise, "Amplitude", over=Range(0.0, 200.0))
    )
    .then(Engine("Reverb").drives(HAT_FX.reverb, "MixDirect", over=Range(0.0, 0.5)))
    .then(Engine("Eq8"))
    .then(
        Engine("Compressor2").drives(
            HAT_FX.punch, "DryWet", over=Range(0.0, 0.6999999881)
        )
    ),
)


CLAP_FX = Layout(
    Slot("TUNE", start=63.5),
    Slot("DISTO"),
    Slot("COLOR 1"),
    Slot("COLOR 2"),
    Slot("PUNCH"),
    Slot("BRIGHT"),
    Slot("ANALOG"),
    Slot("REVERB"),
)

# CLAP and SNARE share this one, and it is the rack that MAKES those two
# sounds rather than colouring them: both pads hold an empty Sampler, so
# Corpus behind BRIGHT is the resonator doing the work.
#
# Every device but the Limiter and the output gain has its `On` on a macro.
# Seven bypasses on seven knobs.
CLAP_STRIP = Rack.audio_effect("CLAP FX", CLAP_FX).chain(
    "Chain",
    # Fine, not Coarse: a few hundredths of a Hz either way detunes a clap
    # without shifting it. Coarse is what PERC uses for the opposite effect.
    Engine("FrequencyShifter")
    .drives(CLAP_FX.tune, "Fine", over=Range(-499.999969, 499.999969))
    .then(
        Engine("Erosion")
        .drives(CLAP_FX.analog, "On")
        .drives(CLAP_FX.analog, "Amplitude", over=Range(0.0, 200.0))
    )
    .then(
        Engine("GlueCompressor")
        .drives(CLAP_FX.punch, "On")
        .drives(CLAP_FX.punch, "DryWet", over=Range(0.0, 1.0))
    )
    .then(
        Engine("Overdrive")
        .drives(CLAP_FX.disto, "On")
        .drives(CLAP_FX.disto, "DryWet", over=Range(0.0, 30.0))
    )
    .then(
        Engine("Tube")
        .drives(CLAP_FX.color_1, "On")
        .drives(CLAP_FX.color_1, "DryWet", over=Range(0.0, 1.0))
    )
    .then(
        Engine("Corpus")
        .drives(CLAP_FX.bright, "On")
        .drives(CLAP_FX.bright, "DryWet", over=Range(0.0, 1.0))
    )
    .then(
        Engine("MultibandDynamics")
        .drives(CLAP_FX.color_2, "On")
        .drives(CLAP_FX.color_2, "GlobalAmount", over=Range(0.0, 1.0))
    )
    .then(
        Engine("Reverb")
        .drives(CLAP_FX.reverb, "On")
        .drives(CLAP_FX.reverb, "MixDirect", over=Range(0.0, 0.400000006))
    )
    .then(Engine("Limiter"))
    .then(Engine("StereoGain")),
)


PERC_FX = Layout(
    Slot("PITCH", start=63.5),
    Slot("RING"),
    Slot("REDUX"),
    Slot("NOISE"),
    Slot("SATURATION"),
    Slot("FUZZ"),
    Slot("DELAY"),
    Slot("REVERB"),
)

# PERC and TOM. Eight devices, eight macros, every one of them carrying its
# own bypass. The purest statement of the technique in the Set: the rack is
# eight independent effects and the knobs are eight faders.
#
# Two FrequencyShifters in a row doing DIFFERENT jobs, which is why the
# device index matters and a spec cannot name a device by tag alone:
# the first shifts pitch on `Coarse`, the second ring-modulates on
# `RingModCoarse`. `.then()` order IS the identity here.
PERC_STRIP = Rack.audio_effect("PERC FX", PERC_FX).chain(
    "Chain",
    Engine("FrequencyShifter")
    .drives(PERC_FX.pitch, "On")
    .drives(PERC_FX.pitch, "Coarse", over=Range(-10000.0, 10000.0))
    .then(
        Engine("FrequencyShifter")
        .drives(PERC_FX.ring, "On")
        .drives(PERC_FX.ring, "RingModCoarse", over=Range(1.0, 10000.0))
    )
    .then(
        Engine("Redux")
        .drives(PERC_FX.redux, "On")
        .drives(PERC_FX.redux, "SampleResSoft", over=Range(1.0, 20.0))
    )
    .then(
        Engine("Vocoder")
        .drives(PERC_FX.noise, "On")
        .drives(PERC_FX.noise, "DryWet", over=Range(0.0, 0.1000000015))
    )
    .then(
        Engine("Saturator")
        .drives(PERC_FX.saturation, "On")
        .drives(PERC_FX.saturation, "DryWet", over=Range(0.0, 1.0))
    )
    .then(
        Engine("Pedal")
        .drives(PERC_FX.fuzz, "On")
        .drives(PERC_FX.fuzz, "DryWet", over=Range(0.0, 1.0))
    )
    .then(
        Engine("Echo")
        .drives(PERC_FX.delay, "On")
        .drives(PERC_FX.delay, "DryWet", over=Range(0.0, 1.0))
    )
    .then(
        Engine("Reverb")
        .drives(PERC_FX.reverb, "On")
        .drives(PERC_FX.reverb, "MixDirect", over=Range(0.0, 1.0))
    ),
)


HAT_DELAY_FX = Layout(
    Slot("DELAY 1"),
    Slot("DELAY 2"),
    Slot("DELAY 3"),
    Slot("DELAY 4"),
)

# CHH and OHH run this BEFORE the strip above. Four Delay devices, four
# knobs, each capped at half wet.
#
# Four of one device is not padding. Each carries its own time, and mixing
# them in on separate knobs builds a pattern out of one hat rather than
# choosing a delay - so the count IS the instrument. A selector rack cannot
# do this at all, because a selector picks one.
HAT_DELAYS = Rack.audio_effect("HAT DELAYS", HAT_DELAY_FX).chain(
    "Chain",
    Engine("Delay")
    .drives(HAT_DELAY_FX.delay_1, "DryWet", over=Range(0.0, 0.5))
    .then(Engine("Delay").drives(HAT_DELAY_FX.delay_2, "DryWet", over=Range(0.0, 0.5)))
    .then(Engine("Delay").drives(HAT_DELAY_FX.delay_3, "DryWet", over=Range(0.0, 0.5)))
    .then(Engine("Delay").drives(HAT_DELAY_FX.delay_4, "DryWet", over=Range(0.0, 0.5))),
)


RIDE_DELAY_FX = Layout(
    Slot("TIME", start=9),
    Slot("DRY/WET"),
    Slot("LOW SHELF", start=63.5),
    Slot("HI SHELF", start=63.5),
    Slot("EQ 1 FREQ", start=64.5547256),
    Slot("EQ 1 GAIN", start=63.5),
    Slot("EQ 2 FREQ", start=87.4308395),
    Slot("EQ 2 GAIN", start=63.5),
)

# RIDE only. A delay with a six-knob EQ on its tail, which is more EQ than
# anything else in the Set gets.
#
# **The donor runs this as two PARALLEL chains, 'Wet' and 'Dry', both at
# zone 0/0/0/0 so both sound at once.** The Dry chain holds NO DEVICES, and
# a chain with no devices has no syntax here, so this builds the Wet half
# only and the dry path is the Delay's own DryWet.
#
# Zones at 0/0/0/0 across every chain is worth noting on its own: this Set
# uses a rack as a parallel MIXER rather than a selector.
RIDE_DELAY = Rack.audio_effect("RIDE DELAY", RIDE_DELAY_FX).chain(
    "Wet",
    Engine("Delay")
    .drives(
        RIDE_DELAY_FX.time, "DelayLine_SimpleDelayTimeL", over=Range(1.0, 145.828125)
    )
    .drives(RIDE_DELAY_FX["DRY/WET"], "DryWet", over=Range(0.0, 1.0))
    .then(
        Engine("Eq8")
        .drives(
            RIDE_DELAY_FX.low_shelf, "Bands.3/ParameterA/Gain", over=Range(-15.0, 15.0)
        )
        .drives(
            RIDE_DELAY_FX.hi_shelf, "Bands.4/ParameterA/Gain", over=Range(-15.0, 15.0)
        )
        .drives(RIDE_DELAY_FX.eq_1_freq, "Bands.0/ParameterA/Freq", over=BAND_HZ)
        .drives(
            RIDE_DELAY_FX.eq_1_gain, "Bands.0/ParameterA/Gain", over=Range(-15.0, 15.0)
        )
        # One knob, two bands. Same pairing idea as BRIGHT above.
        .drives(
            RIDE_DELAY_FX.eq_2_freq,
            "Bands.1/ParameterA/Freq",
            "Bands.2/ParameterA/Freq",
            over=BAND_HZ,
        )
        .drives(
            RIDE_DELAY_FX.eq_2_gain, "Bands.1/ParameterA/Gain", over=Range(-15.0, 15.0)
        )
    ),
)


FX_RACKS = [HAT_STRIP, CLAP_STRIP, PERC_STRIP, HAT_DELAYS, RIDE_DELAY]


# ===========================================================================
# The kit
# ===========================================================================

# **The drum rack has NO MACROS AT ALL.** Sixteen unnamed, unbound, all at
# zero. Every knob in this kit lives one level down, inside a pad.
#
# The reason is legible from the pads - eight pads with eight DIFFERENT decays
# and volumes is a kit tuned per pad, and a kit-wide knob would move all
# eight off their settings together.
#
# So the layout is empty rather than absent. A drum rack has no chain
# selector to drive either way (a pad is chosen by its note), which is the
# one thing both kits agree on.
KIT = Layout()

# Four returns INSIDE the drum rack, so the whole kit's effects travel with
# the preset and the Set needs no return tracks at all. A rack that carries
# its own returns is a self-contained instrument, which is the argument for
# doing it this way.
#
# `b Delay C/S` and `c Delay Hats` are the same device on two returns,
# tuned for two sources - clap/snare and hats. Naming a return for WHAT
# FEEDS IT rather than for its character.
REVERB_RETURN = Rack.audio_effect("a Reverb", Layout()).chain(
    "Chain",
    Engine("Reverb")
    .then(Engine("Eq8"))
    .then(Engine("Saturator"))
    .then(Engine("Compressor2")),
)

DRUMS_FX_RETURN = Rack.audio_effect("d Drums Fx 1", Layout()).chain(
    "Chain", Engine("Delay").then(Engine("Reverb"))
)


def kit() -> Rack:
    """The drum rack: eight pads at their own notes, four returns.

    Each pad is its Select rack and nothing else. In the donor a pad chain
    continues into an FX rack, an Eq8 and a StereoGain, and a chain cannot
    hold a rack followed by devices - see the module docstring. The FX racks
    are built beside this one.

    TOM's send to `d Drums Fx 1` is the only send in the donor above the
    silent floor, at full. Every other pad sits on the floor, which is what
    `ret()` writes anyway.
    """
    made = Rack.drum("Drums Selector", KIT)
    for rack, (name, note, *_) in zip(SELECT_RACKS, PADS):
        sends = {"d Drums Fx 1": 1.0} if name == "TOM" else None
        made = made.pad(name, note, rack.unchained(), sends=sends)
    return (
        made.ret("a Reverb", REVERB_RETURN.unchained())
        .ret("b Delay C/S", Engine("Delay"))
        .ret("c Delay Hats", Engine("Delay").then(Engine("Eq8")))
        .ret("d Drums Fx 1", DRUMS_FX_RETURN.unchained())
    )


KIT_RACK = kit()

RACKS: list[Rack] = [KIT_RACK] + SELECT_RACKS + FX_RACKS


# ===========================================================================
# The Set
# ===========================================================================
#
#     patchbay session examples/techno.py -o build/techno.als
#
# One track. The donor has eight, and the other seven carry loose devices
# with no rack on them - a Wavetable and five effects, an Operator and five
# effects. There is nothing in those to declare that placing the device
# would not say, and this file is not a transcription.
#
# 135 BPM is the donor's. No return TRACKS, because this Set's returns are
# inside the drum rack.

#: The donor's own colour for the Drums track.
DRUMS_COLOR = 15


def SESSION() -> Session:
    """EXAMPLE_TECHNO as a Live Set: one MIDI track carrying the kit."""
    return Session(
        [
            Track(
                "Drums",
                "midi",
                [KIT_RACK.build().find("GroupDevicePreset")],
                color=DRUMS_COLOR,
            )
        ],
        returns=[],
        tempo=135.0,
    )
