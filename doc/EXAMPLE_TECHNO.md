# EXAMPLE_TECHNO

A donor Set read back into a spec, and what it says about EXAMPLE_PLAYGRND.

`donors/BerlinTechno/BerlinTechno.als` is a Live 11.0.11 Set at 135 BPM: a
drum rack on one track and seven synth tracks. `examples/techno.py`
is the drum rack rebuilt as a declaration.

Read this alongside `doc/EXAMPLE_PLAYGRND.md`, which is the same kind of
document for our own target. This one is comparison, not a target: nothing
here is a plan to build anything.

## Why bother

EXAMPLE_PLAYGRND was designed from the layout outward, and its arguments are
recorded next to the decisions they justify. That makes them hard to test.
A second Set, built by somebody else, by hand, for a different genre, is
the nearest thing to a control: where it AGREES the idea is probably
structural, and where it DIVERGES the argument was taste.

It is also much simpler, which is the point. One rack with real
architecture in it, against EXAMPLE_PLAYGRND's fifty-two.

## What was rebuilt

| | Racks | Mappings verified against the donor |
|---|---|---|
| Select racks | 8 | 10 each, exact |
| FX racks | 5 | 10, 15, 16, 4, 9 - exact |
| the kit | 1 | 0, it has none |

Every mapping matches the donor on macro index, device POSITION in the
series, device tag, parameter path and range. Pad notes match: 92, 91, 90,
89, 88, 87, 86, 85 as stored.

Not rebuilt: Amb 1, Perc 1, and the five tracks carrying loose devices.
The reasons are in the spec's docstring and the open work is in `TODO.md`.

## Where the two Sets AGREE

These were reached twice, independently, from opposite directions.

**One layout, repeated.** The eight Select racks are not eight designs.
They carry the same ten bindings over the same ten ranges, macro for macro,
and differ only in where four knobs are parked and which sample is loaded.
That is `doc/DSL.md`'s central claim, arrived at by hand in a Set with no
code in it - which is the strongest evidence available that the shape is
not an artefact of having a compiler.

**The kit sits on notes 36..43.** Both. Push's bottom two rows, four to a
row. EXAMPLE_PLAYGRND argues for this from what a hand plays; this Set just
does it.

**A start position is part of the design.** Every pad parks PAN at 63.5
(centre over -1..1), PITCH at 63.5 (0 semitones over -48..48) and LPF at
127. `doc/DSL.md` argues a slot must say where its knob opens because an
unplaced macro reads 0 and 0 is the BOTTOM of the range. This Set places
every bipolar knob at its centre and every filter at its neutral end, for
exactly that reason and without writing it down.

**Ranges are narrowed, and narrowed hard.** Overdrive at 0..50 of a 0..100
DryWet, Amp at 0..0.3, Reverb at 0..0.5, Erosion at 0..200. Live 12.4.3 has
no UI for `MidiControllerRange` at all, so every one of these was set
through the mapping browser deliberately. A knob that reaches a third of
its target is a knob you cannot ruin the sound with - the same argument
EXAMPLE_PLAYGRND's capped volume ranges make, applied to effects.

**One knob, two parameters, one idea.** DECAY drives decay AND release.
BRIGHT lifts a band 0..4 dB while dropping global gain 0..-4, so it tilts
at constant loudness. EQ 2 FREQ moves two bands together. EXAMPLE_PLAYGRND
pairs cutoff with resonance and argues the case at length; this Set does it
four times without comment.

**A mapped macro is not a working macro.** `SAMPLE SELECTR` is bound on all
eight pads to `Player/SampleSelector`, over a correct 0..127 range,
resolving to a real parameter. Six pads hold ONE multisample zone and CLAP
and SNARE hold none, so the knob moves nothing on any pad. That is Q16
found in someone else's Set. It also means the DSL's one-sample-per-device
limit (Q3) costs this rebuild nothing: there is no second zone to lose.

## Where they DIVERGE

The interesting half. In each case both answers are defensible and the
difference is what the Set is FOR.

### A rack as a series, not a selector

The sharpest one.

EXAMPLE_PLAYGRND's `AFX1` is eight effects behind one selector: eight
alternatives, one in circuit, a macro swaps which. Its comment gives the
reason - "parallel audio chains are expensive; a selector is not".

Every FX rack here is the other shape. Eight to ten effects IN SERIES, all
in circuit, one macro each. The signal goes through all ten. A knob is not
"which effect" but "how much of this one", so the eight knobs are a mixing
desk over a fixed chain.

| | EXAMPLE_PLAYGRND `AFX1` | EXAMPLE_TECHNO `PERC FX` |
|---|---|---|
| chains | 8 | 1 |
| devices in circuit | 1 | 8 |
| what a macro means | which effect | how much of effect N |
| what the rack is | a chooser | a channel strip |

What makes the series affordable is the technique below, and without it the
comparison is unfair: ten devices always running is exactly the cost
`AFX1`'s comment refuses to pay.

### A macro drives the BYPASS as well as the amount

**One macro drives a device's `DryWet` AND its `On` switch.** At macro 0 the
device is bypassed, not merely dry. So ten effects in series cost nothing
until a knob is turned, and the rack is a menu that charges for what you
use. `PERC FX` does it on all eight devices, `CLAP FX` on seven.

EXAMPLE_PLAYGRND sets `On` STATICALLY in six places - `Lfo/LfoOn`,
`Filter_On`, `FilterOn`, `SideChain/OnOff` - always as a `sets`, never as a
binding. Those exist to stop Q16, a knob bound behind a switch that is off.
This Set puts the switch ON THE SAME KNOB, which solves the same problem
and buys the CPU back.

**That mapping is a different element**, and it is a format finding this
project did not have. A boolean's mapping range is `MidiCCOnOffThresholds`,
not `MidiControllerRange`:

```xml
<On>
  <KeyMidi>... <NoteOrController Value="4"/> ...</KeyMidi>
  <Manual Value="false"/>
  <MidiCCOnOffThresholds><Min Value="1"/><Max Value="0"/></MidiCCOnOffThresholds>
</On>
```

`Range` writes `MidiControllerRange` and nothing else, and nothing in
`patchbay/` has ever written or read the threshold element. So the `On`
bindings in the rebuilt racks carry a `KeyMidi` and leave the thresholds to
whatever the donor device happens to have. **What `Min=1 Max=0` means is
not settled** - the natural reading is inverted, and guessing is rule 1.
That is the one thing in this rebuild a person has to check, and the one
open item it put in `TODO.md`.

### Returns inside the rack, not on the Set

This Set has **no return tracks at all**. Four returns live INSIDE the drum
rack, so the whole kit's effects travel with the preset and a Set built
around it needs nothing.

EXAMPLE_PLAYGRND puts six returns on the Set and two inside DR1.

A rack carrying its own returns is a self-contained instrument, which is
the argument for doing it this way; returns on the Set are shared across
tracks, which is the argument for the other. Both Sets do both, in
different proportions.

Naming diverges with it. EXAMPLE_PLAYGRND names a return for its CHARACTER,
`A-Rvb:Short`. This Set names two of four for WHAT FEEDS THEM: `b Delay
C/S` and `c Delay Hats` are the same device tuned for clap/snare and for
hats. Character naming survives re-use; source naming documents intent.

### A kit knob is not worth having

**The drum rack has no macros at all.** Sixteen, unnamed, unbound, all at
zero. Every knob lives one level down, inside a pad.

DR1 argues the opposite at length: kit macros chaining into all eight pads
so one knob filters the whole kit. This Set's answer is legible from its
own pads - eight pads with eight different decays and volumes is a kit
tuned per pad, and a kit-wide knob would move all eight off their settings
together.

Both agree on the one structural point: no slot SELECTS, because a pad is
chosen by its note and a drum rack has no chain selector.

### A layout names a signal path, not an idea

| EXAMPLE_PLAYGRND `PB` | EXAMPLE_TECHNO `SELECT` |
|---|---|
| Instrument, Sound, Filter, Drive, Movement, Character, Release, Volume | SAMPLE SELECTR, PITCH, DECAY, SAMPLE START, HPF, LPF, PAN, VOLUME |

`PB` has to survive Operator, Simpler, Wavetable, Drift and Meld answering
the same knob, so a slot is named for the musical IDEA and each engine
binds its own parameter. Here there is one engine, a Sampler, so a slot is
named for the thing it moves. **A layout is only as abstract as it has to
be**, and paying for abstraction you do not need shows up as a wildcard
slot called Character.

### A rack used as a parallel mixer

`RIDE DELAY` has two chains, `Wet` and `Dry`, both at zone `0/0/0/0`, so
both sound at once. The Dry chain holds no devices - it is a bypass path.

EXAMPLE_PLAYGRND uses a rack as a SELECTOR everywhere and distributes zones
evenly across 0..127. Same construct, opposite reading, and the tell is
that every zone is `0/0/0/0` rather than a share.

### A filter pair built out of an EQ

Every pad's HPF and LPF are two Eq8 bands parked at the ends of their
range: band 1 in mode 1 (high-pass, Q21) at 10 Hz, band 8 in mode 6
(low-pass) at 22 kHz. Both on, both inaudible until a knob moves.

So the pad gets a playable filter pair with no filter device and no switch
in front of it. EXAMPLE_PLAYGRND reaches for the same trick exactly once, in
`VOL1`'s Sub Cut, and this Set uses it eight times. It is the cheaper
answer to "a filter on every pad" than the Simpler filter DR1 binds.

## What the exercise cost, and what it found

Three things in `patchbay/` were wrong or missing, and all three were found
by pointing the toolchain at a file it had not seen.

**A drum pad lost its note reading a Set.** `extract.preset_from_set` moved
`ZoneSettings` and `BranchInfo` only where BOTH forms carry the tag, and a
drum branch carries one on each side. So all eight pads kept the template's
note, 92, and the kit extracted as one pad holding eight chains. Q40 is the
format fact and `live_set._branch_from_preset` had the translation; only
the write direction did. Fixed, and 124 tests held, so nothing else moved.

**`donors/MultiSampler.adg` could not hold a sample.** A Sampler's LFO,
Shaper and AuxEnv are SLOTS, and an empty slot contributes no parameters,
so a donor's vocabulary depends on which slots were filled when it was
saved. The shipped donor had LFO and Shaper filled, AuxEnv empty, and no
`SampleRef` at all: 97 parameters and unable to play anything. The copy in
this Set is the mirror image at 95. **Parameter count is the wrong
tie-break for a device with optional slots**, and it is the rule
`Library.harvest` uses. Replaced out of this Set.

**`FrequencyShifter` was not in the library at all**, which is why one Set
is worth dozens of hand-saved racks: `patchbay harvest` indexed it in one
pass.

## What could not be rebuilt

**A chain cannot hold a rack followed by devices.** This is the one that
matters, because it is the shape of this whole Set. Every pad chain is

    [Select rack] -> [FX rack] -> Eq8 -> StereoGain

and the DSL's `then` chains Engines while `Nested` wraps one rack, with no
way to write the concatenation. So `examples/techno.py` builds the
Select racks and the FX racks as SEPARATE presets and putting one after the
other is by hand.

Worse than the limit is how it fails: `patchbay extract` drops the extra
devices SILENTLY. Amb 1's chain holds eleven devices and extracts as one.
The preset conversion is fine - `preset_from_set` keeps all eleven - so it
is the DSL emitter, and "fail loudly" says it should refuse rather than
emit a rack that is missing ten devices. In `TODO.md`.

Also unexpressible, and smaller: a chain with NO devices (the `Dry` path
above), and a send from one return to another (`b Delay C/S` and `c Delay
Hats` both feed the reverb at 0.1413; `ret()` takes no `sends=`).

**`MxDeviceAudioEffect`** is a Max for Live device on Amb 1. It is not
stock Live content and is not ours to vendor, so that rack is out of scope
rather than blocked.

## The one thing a person has to check

Everything above is a fact in a file and was tested against one. This is
not.

> Load **`build/bt/PERC_FX.adg`** onto an **audio track**, with something
> playing through it.
>
> | # | Do this | Should happen |
> |---|---|---|
> | 1 | Leave every macro at 0 | All eight devices read BYPASSED |
> | 2 | Turn Macro 5 (SATURATION) up from 0 | Saturator switches ON and goes wet together |
> | 3 | Return Macro 5 to 0 | Saturator switches OFF again |
>
> Expected still broken: nothing. If check 2 shows the device switching OFF
> as the knob rises, `MidiCCOnOffThresholds` is inverted from the natural
> reading and the finding is that `Min`/`Max` are the ON and OFF ends in
> that order.

Nothing else here needs Live. The mappings, ranges, notes and structure are
all facts in the file, and `patchbay mappings` reads them with no Live
open.
