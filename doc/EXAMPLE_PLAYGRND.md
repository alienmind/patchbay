# PLAYGRND

Some inspiration of this project came while trying to recreate the amazing **PLAYGRND**, an Ableton Live Set
by **Andri Sören**: https://www.youtube.com/watch?v=plQ9F-0RmDw (please support the author and buy his product!).

Based on the information publicly made available from him, what that Set demonstrates
is worth taking: one macro layout repeated across every rack, engines as chains,
using knobs to quickly switch between instruments, a semi fixed channel strip on every track,
and racks nested inside racks so one instrument reaches all the others.

[`examples/playgrnd.py`](examples/playgrnd.py) is this
project's attempt at rebuilding something with that complexity with the obvious non intention
of copying the author intelectual property.

It primarily serves as **one big example, and the end-to-end test** that puts this idea into stress:
Twelve racks, six instruments and a six rack channel strip, three levels of nesting, 96 variations, eight drum pads
- if a change breaks something real, it breaks there first. All twelve have been loaded into Live 12.4.3 and played.

## Goal

What that Set demonstrates is an ARCHITECTURE: A hyper-mapped Live template for Push 3.
The design goal is that the mouse is never needed during a jam: every meaningful control sits on a
macro, reachable from a Push encoder.

PLAYGRND has one macro layout repeated across every rack, engines as
chains, sounds as selector positions, a fixed channel strip on every track,
and racks nested inside racks so one instrument can reach all the others.

Assembling a template of this kind by hand is thousands of macro mappings
and tens of thousands of parameter values, entered one at a time by mouse.

Our own build of that idea helps automate the tedious parts: the tracks, the slot names,
the engine choices and the sound design are yours.

## The eight tracks

| Track | Type | Role |
|---|---|---|
| DR | MIDI | Drum rack, RYTM inspired, per pad sends and FM |
| BS | MIDI | Multi engine bass |
| PD | MIDI | Polyphonic pads, Wavetable based |
| LD | MIDI | Leads, FM based, mono with glide |
| SR | MIDI | Sampler, built in sounds plus a hot swap slot |
| VA1 | MIDI | Various, nests all five instruments above |
| VA2 | MIDI | Various, second instance |
| PM | **Audio** | Pre master |

Two VA tracks rather than one, because the whole point of a nesting rack is
that you want a second one the moment you have used the first.

## The channel strip

Every track carries the same devices in the same order. The instrument sits
third, after the MIDI effects that feed it:

    ARP   MFX   <instrument>   EQC   AFX   AFXS   Channel EQ   VOL

| Device | Kind | Carries |
|---|---|---|
| ARP | MIDI rack | Style, Rate, Retrigger, Random Notes, Jitter, Transpose Steps, Gates, Velocity Random |
| MFX | MIDI rack | Velocity Range, Velocity Random, Pitch, Scale Selector, Scale Root |
| EQC | Audio rack | Lo-Hi EQ, EQ Dry-Wet, Compressor Dry-Wet, Gain, and the sidechain |
| AFX | Audio rack | Eight character effects, one selector |
| AFXS | Audio rack | Second effect slot, freely editable |
| Channel EQ | Stock Live | Left stock. Not everything needs wrapping |
| VOL | Audio rack | Sub-Cut, Pre-Gain, Limiter |

The arpeggiator is a DEVICE, not a track. Putting it in the strip means any
track can be arpeggiated without routing anything.

**Naming rule:** an instance of the strip is named for the track it sits
on, `EQC_BS` on BS. Copying a strip between tracks without renaming is
how you end up staring at `EQC_LD` on a pad track wondering what it means.

Six return tracks. Sends live on the channel strip and on DR pads, NOT on
the instrument rack, so an instrument's eight knobs stay spent on sound.

**Returns are named for character, not device.** A return called
`A-Rvb:Short` says what it does to a sound; one called `Reverb 1` says
nothing you cannot already see. Push shows the send name next to the knob,
so this is the difference between choosing a send by ear and choosing it by
counting. Two reverbs and two delays of contrasting length is the minimum
useful spread; the remaining two returns are ours to spend.

## Macro layout

Identical across every instrument rack so muscle memory transfers. This
consistency is the actual product, more than any individual rack.

**Eight slots. One Push page. There is no page two.**

Racks support 16 macros and Push will happily show a second page, but a
page flip during a jam costs more than the knobs are worth. Fitting eight
is the design, not a limitation being tolerated.

| # | Slot | Notes |
|---|---|---|
| 1 | Instrument | Chain selector: which engine |
| 2 | Sound | Chain selector: which sound within that engine |
| 3 | Filter | Cutoff, with resonance folded in where a rack can spare it |
| 4 | Drive | Filter drive and filter envelope |
| 5 | Movement | LFO depth, or the rack's modulation wildcard |
| 6 | Character | Per rack wildcard. Saturation, glide, attack, whatever that rack needs |
| 7 | Release | Decay or release, whichever the engine has |
| 8 | Volume | Always |

Slots 1, 2, 7 and 8 are FIXED across every rack. Slots 3 to 6 are where a
rack spends its character. A rack that cannot use a slot leaves it empty
rather than inventing a use for it.

SR is the deliberate exception: a sampler has no instrument axis, so slots
1 and 2 become Samples and Start Point, and slots 3 to 6 become Filter,
Pitch, Loop Length and Attack. Same shape, different content.

### One knob may drive two parameters

Eight slots do not cover a synth with more than eight things worth
reaching, so a slot is allowed to move a PAIR that belongs together:
cutoff with resonance on slot 3, drive with the filter envelope on slot 4.

This is the alternative to spending a whole slot on resonance, and it is
what frees slot 6 to be a real wildcard rather than a dumping ground.
Mature templates of this kind pair exactly these two, which is a reasonable
signal that the pairing survives contact with playing.

The cost is that a paired slot cannot be automated to move one half. Where
that matters, split them and spend the wildcard.

### Slot 6 is genuinely per rack

The wildcard earns its name only if racks disagree about it. They should:
a pad wants an attack knob, a bass wants saturation, a lead wants glide.
A rack that has nothing to put there leaves it empty.

Slot 5 may also carry a second function where the rack has one worth
reaching, such as pairing modulation depth with a re-roll of the sound
selector. That is the one case where a slot reaches back into slot 2's
territory, and it is deliberate rather than an accident of naming.

Slot 1 is the selector on every rack that has something to select between,
and it is worth marking as such on the display so a glance tells you which
knob steps rather than sweeps.

The layout is a CONTRACT, not a template. A rack does not "have" these
macros, it BINDS its own parameters to these slots:

```python
with rack.engine("FM", "Operator") as e:
    e.bind(filter=("Filter/Frequency", 30, 18500),
           release="Operator.0/Envelope/ReleaseTime")
```

Ranges are optional and scope what the macro reaches. Live 12.4.3 has no UI
for them, so they exist only in code.

Push renders a value in whatever unit reads best, switching between
milliseconds and seconds on the same control as it crosses one second. That
is display only. Bindings are written in stored units, which for envelope
times is seconds. See Q13 in `SCHEMA.md`.

Every sound also maps aftertouch to filter and pitch. Exception: drum rack
pads, since Push does not send per pad aftertouch there.

## A sound has a two part address

The single most important structural decision, and the one most worth
getting right before generating anything.

A sound is NOT one number. It is **(instrument, sound)**: slot 1 picks the
engine, slot 2 picks the position within it. Slot 2 is a macro, 0..127, so
it steps a chain selector. Sounds are therefore CHAIN POSITIONS.

The arithmetic that follows:

- 128 macro positions on slot 2
- a selector of N chains inside each engine
- with 3 engines and about 65 chains each, roughly 2 macro steps per chain,
  and about 196 sounds on that one rack

Two consequences worth stating plainly.

**Sounds are not Macro Variations.** A variation is recalled by clicking a
name in a list; nothing maps a knob to one. A sound you can dial in while a
clip plays cannot be a variation. This kills an earlier argument in this
document, which divided a total sound count by an engine count and
concluded a sound must be a variation. The premise was that one knob
carries both axes. Two knobs do.

**Variations remain useful, for something else.** A variation carries a
whole VECTOR of macro values at once, where a selector position carries
one. That makes variations the right mechanism for presets and snapshots
across the entire layout, and the wrong one for a sound browser. We use
them for the former.

## Sound families

Sounds are built in parallel across engines, not independently. Engine 0
position 73 and engine 1 position 73 are deliberately the same musical idea
rendered through different synthesis, with the last engine usually being
the FM treatment.

Consequence: the Instrument knob becomes a *timbre* control rather than a
jump into unrelated territory. Any generator must produce sound sets
index-aligned across engines, not independently randomised per engine.

CPU works out because instrument chains receiving no MIDI idle at near
nothing. Many instrument chains are cheap. Many parallel audio effect
chains are not, which is why effect racks use selectors instead of stacks.

## VA1

VA1 nests the other instrument racks and selects between them on slot 1. So
slot 1 addresses a whole rack, and every other slot chains macro-to-macro
into whichever rack is selected.

This is what makes a two part address pay off twice: inside VA1, the first
number is which instrument family you are in, and sweeping it walks from
percussion into bass into leads without leaving the track.

## DR structure

Three levels of nesting per pad:

```
Drum Rack                      global kit macros only
└─ Pad chain
   └─ Pad rack (e.g. "KICK")   the 8 pad knobs
      ├─ Pitch                 Tune
      ├─ Engine rack           Sound, decay, filter
      │  ├─ Simpler x4         sample chains, zones distributed
      │  └─ Operator           FM layer, zone spans full 0-127
      └─ Saturator             Drive
```

Macros chain to macros: Drum Rack Sound drives pad rack Sound drives engine
rack Sound drives the chain selector.

### One pad, one family

A pad is a family, not a slot. The kick pad holds kicks, the snare pad
holds snares, and its Sound knob walks that family. Open and closed hats
are therefore SEPARATE PADS with separate families, not two ends of one
knob. The tempting design is a hat pad whose Sound sweeps closed to open;
it is the wrong shape, because a kit needs both at once.

Eight pads, eight families:

    KICK   RIM   SNARE   CLAP   TOM   HAT   PERC   OHAT

### Pad slot names are local

The layout is positional. A pad LABELS its own slots for what they
actually drive, so a kick can read "Filter and Envelope" and "Drive and
Snap" where a hat reads plain "Filter" and "Drive". Same knob positions,
same chaining, different words on the display.

This is the drum rack equivalent of the slot 6 wildcard: the position is
the contract, the label is local.

Top level macros are reserved for kit wide moves, because 8 pads times 8
parameters cannot fit 8 knobs:

    Sound   Pitch   Filter   Drive+Env   Send A FX   Send B FX   Send Vol   Volume

Per pad, reached by diving into the pad on Push, which is free:

    Filter+Drive   Send A   Send B   Decay   Volume

Send A and Send B at kit level are **FX SELECTORS**, not send levels. The
knob swaps which effect the send feeds. DR return chains live inside the
Drum Rack via Show Return Chains, and each holds a selector across several
reverbs and delays.

Pads are pitched, playable instruments, not fixed kit slots. A tuned tom
should be usable as a bassline.

### What a slot means may depend on depth

Our layout fixes a slot's meaning for a whole rack. Inside a drum pad that
may be too rigid: the useful controls at the pad level are the two sends,
and the useful controls one level down are the FM pair, and there are only
eight knobs at either level.

Letting slots 5 and 6 mean sends at the pad level and FM inside the sound
buys four controls without a page flip, at the cost of the one property the
layout exists to guarantee. Muscle memory is the product, and a knob that
changes meaning as you dive is the thing muscle memory cannot absorb.

**Decided: meaning per LEVEL.** At kit level slots 5 and 6 are the two
sends, because a send is a kit-level idea - it exists once per return and
every pad has one. Inside a pad they stay Movement and Character, which is
what one voice has to offer. So the layout is a contract per LEVEL rather
than per rack, and the label on each knob is what says which level you are
looking at.

Three things settled it. Slot 6 was already a per-rack role rather than a
fixed meaning, so meaning varied by rack before it varied by depth. Labels
are local, so a pad can say what its own slot 5 does. And the conservative
branch was not free: it left the first knob inside every pad dead and the
kit and pad rows offset by one.

## AFX

Eight character effects behind one selector, so a knob swaps the effect
rather than layering it. Parallel audio chains are expensive; a selector is
not.

The eight are a spread across degradation, time and space rather than eight
flavours of the same idea. Glitch, tear, erode, grind, reduce, soak,
stretch and fade is the kind of spread that works: each one should be
reachable in a jam and obviously different from its neighbours.

## Sidechain

No ghost track. The EQC compressor sidechains from DR with the sidechain
EQ set to a low band only, so it tracks the kick and ignores hats. Reverb
returns are sidechained too, not just instrument channels.

## PM

The Master track has no Session clip slots, so master bus moves cannot be
automated in Session view. PM solves this: an audio track that all seven
other tracks route into, carrying the master chain, with silent dummy clips
holding automation envelopes. Requires Session Automation Recording enabled
in Record/Warp/Launch preferences.

## Playing considerations

Two behaviours the design has to respect, both of which shape what a macro
is for:

- **A macro's parked position is a performance tool.** Push returns a knob
  to where it was physically left. Parking a filter low at the start of a
  clip buys a drop with no automation recorded. Macro defaults are
  therefore part of the instrument, not housekeeping.
- **Sounds are the compositional unit.** The template succeeds when a whole
  track can be built without opening the browser once.

## Not built yet, but within reach

Not blockers. Decisions deferred, listed so they are chosen deliberately
rather than by accident:

- **How many chains sit behind the Sound macro, and whether the selector
  steps or crossfades.** Stepping gives clean recall; crossfading gives a
  sweep. The choice changes what the knob is for.
- **Per pad unlinking of DR's global Sound and Pitch.** The global knob
  chains into every pad, and a pad should be able to opt out without
  breaking the chain for its neighbours.
- **Per engine parameter ranges.** Every binding currently reaches a
  parameter's full range. Scoped ranges are what make one knob feel the
  same across engines that disagree about units.
- **The slot 6 wildcard, per rack.** PD spends `Character` on resonance,
  because Operator and Simpler both have one and slot 3 is cutoff alone.
  That is a default, not a decision. Pairing resonance onto slot 3 frees
  slot 6 for what it is actually for: attack on a pad, saturation on a
  bass, glide on a lead, and Meld's L-B-H-N morph wherever Meld lands.
- **Whether a slot may change meaning with depth.** Fixed per rack is the
  current rule. Per level buys four more controls inside DR and costs the
  guarantee that a knob means one thing. See DR structure above.
- **A second effect slot on the strip.** AFXS exists in the layout and has
  no contents.