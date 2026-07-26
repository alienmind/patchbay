# PATCHBAYGROUND

The musical target that `patchbay` exists to serve, and the spec
`examples/patchbayground.py` compiles. Read this alongside `CLAUDE.md`,
which covers the tooling.

## Inspired by PLAYGRND

The idea came from **PLAYGRND**, an Ableton Live Set for Push by **Andri
Soren**: https://www.youtube.com/watch?v=plQ9F-0RmDw

What that Set demonstrates is an ARCHITECTURE, and the architecture is the
part worth taking: one macro grammar repeated across every rack, engines as
chains, sounds as selector positions, a fixed channel strip on every track,
and racks nested inside racks so one instrument can reach all the others.

PATCHBAYGROUND is our own build of that idea, to our own taste, for our own
music. The tracks, the slot names, the engine choices and the sound design
are ours. What we borrowed is the shape.

Assembling a template of this kind by hand is thousands of macro mappings
and tens of thousands of parameter values, entered one at a time by mouse.
**That tedium is what `patchbay` exists to remove.**

## Goal

A hyper-mapped Live template for Push 3, run tethered to a computer so VSTs
are available. Darkwave and minimal techno. The design goal is that the
mouse is never needed during a jam: every meaningful control sits on a
macro, reachable from a Push encoder.

## The eight tracks

| Track | Type | Role |
|---|---|---|
| DR1 | MIDI | Drum rack, RYTM inspired, per pad sends and FM |
| BS1 | MIDI | Multi engine bass |
| PD1 | MIDI | Polyphonic pads, Wavetable based |
| LD1 | MIDI | Leads, FM based, mono with glide |
| SR1 | MIDI | Sampler, built in sounds plus a hot swap slot |
| VA1 | MIDI | Various, nests all five instruments above |
| VA2 | MIDI | Various, second instance |
| PM1 | **Audio** | Pre master |

Tempo 128.

Two VA tracks rather than one, because the whole point of a nesting rack is
that you want a second one the moment you have used the first.

## The channel strip

Every track carries the same devices in the same order. The instrument sits
third, after the MIDI effects that feed it:

    ARP1   MFX1   <instrument>   EQC   AFX1   AFXS1   Channel EQ   VOL1

| Device | Kind | Carries |
|---|---|---|
| ARP1 | MIDI rack | Style, Rate, Retrigger, Random Notes, Jitter, Transpose Steps, Gates, Velocity Random |
| MFX1 | MIDI rack | Velocity Range, Velocity Random, Pitch, Scale Selector, Scale Root |
| EQC | Audio rack | Lo-Hi EQ, EQ Dry-Wet, Compressor Dry-Wet, Gain, and the sidechain |
| AFX1 | Audio rack | Eight character effects, one selector |
| AFXS1 | Audio rack | Second effect slot, freely editable |
| Channel EQ | Stock Live | Left stock. Not everything needs wrapping |
| VOL1 | Audio rack | Sub-Cut, Pre-Gain, Limiter |

The arpeggiator is a DEVICE, not a track. Putting it in the strip means any
track can be arpeggiated without routing anything.

**Naming rule:** an instance of the strip is named for the track it sits
on, `EQC_BS1` on BS1. Copying a strip between tracks without renaming is
how you end up staring at `EQC_LD1` on a pad track wondering what it means.

Six return tracks. Sends live on the channel strip and on DR1 pads, NOT on
the instrument rack, so an instrument's eight knobs stay spent on sound.

## Macro grammar

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

SR1 is the deliberate exception: a sampler has no instrument axis, so slots
1 and 2 become Samples and Start Point, and slots 3 to 6 become Filter,
Pitch, Loop Length and Attack. Same shape, different content.

The grammar is a CONTRACT, not a template. A rack does not "have" these
macros, it BINDS its own parameters to these slots:

```python
with rack.engine("FM", "Operator") as e:
    e.bind(cutoff=("Filter/Frequency", 200, 8000),
           decay="Filter/Envelope/DecayTime")
```

Ranges are optional and scope what the macro reaches. Live 12.4.3 has no UI
for them, so they exist only in code.

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
across the entire grammar, and the wrong one for a sound browser. We use
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

## DR1 structure

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

Top level macros are reserved for kit wide moves, because 8 pads times 8
parameters cannot fit 8 knobs:

    Sound   Pitch   Filter   Drive+Env   Send A FX   Send B FX   Send Vol   Volume

Per pad, reached by diving into the pad on Push, which is free:

    Filter+Drive   Send A   Send B   Decay   Volume

Send A and Send B at kit level are **FX SELECTORS**, not send levels. The
knob swaps which effect the send feeds. DR1 return chains live inside the
Drum Rack via Show Return Chains, and each holds a selector across several
reverbs and delays.

Pads are pitched, playable instruments, not fixed kit slots. A tuned tom
should be usable as a bassline.

## AFX1

Eight character effects behind one selector, so a knob swaps the effect
rather than layering it. Parallel audio chains are expensive; a selector is
not.

The eight are a spread across degradation, time and space rather than eight
flavours of the same idea. Glitch, tear, erode, grind, reduce, soak,
stretch and fade is the kind of spread that works: each one should be
reachable in a jam and obviously different from its neighbours.

## Sidechain

No ghost track. The EQC compressor sidechains from DR1 with the sidechain
EQ set to a low band only, so it tracks the kick and ignores hats. Reverb
returns are sidechained too, not just instrument channels.

## PM1

The Master track has no Session clip slots, so master bus moves cannot be
automated in Session view. PM1 solves this: an audio track that all seven
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

## Current state

**In Live, by hand:**

- 8 tracks created and named, PM1 recreated as audio
- One DR1 pad built and mapped end to end, three levels deep, verified
  working through all three macro hops. That rack is `racks/s1_source.adg`
  and it is the evidence for the whole nesting model.

**In code, `examples/patchbayground.py`:**

- The grammar, PD1 as a two engine slice, and VA1 as a two level nest.
  Compiles and loads in Live 12.4.3.
- 96 variations on PD1 over engine, cutoff, decay and resonance. All 96
  recall in Live.

**Known gap between this document and the code:** the file still declares a
13 slot grammar with `Space` on the instrument rack. The eight slot
grammar above, with sends moved off the instrument and Volume added, is the
decision; the code has not been reworked to match it yet. Anything
generated before that rework carries the old shape.

**Not yet declarable, and why:**

| rack | blocked on |
|---|---|
| DR1 | rack-inside-chain nesting in the DSL, and per-pad sends |
| BS1, PD1 proper, LD1 | donors for Wavetable, Drift, Meld |
| SR1 | sample retargeting bound into the DSL |
| VA1, VA2 | rack-in-rack composition |
| PM1 | not a rack; built through `ableton-mcp` |

## Not built yet, but within reach

Not blockers. Decisions deferred, listed so they are chosen deliberately
rather than by accident:

- **How many chains sit behind the Sound macro, and whether the selector
  steps or crossfades.** Stepping gives clean recall; crossfading gives a
  sweep. The choice changes what the knob is for.
- **Per pad unlinking of DR1's global Sound and Pitch.** The global knob
  chains into every pad, and a pad should be able to opt out without
  breaking the chain for its neighbours.
- **Per engine parameter ranges.** Every binding currently reaches a
  parameter's full range. Scoped ranges are what make one knob feel the
  same across engines that disagree about units.
- **The slot 6 wildcard, per rack.** It is named `Character` and left open
  on purpose, but no rack has yet argued for what it should be.
- **A second effect slot on the strip.** AFXS1 exists in the layout and has
  no contents.

## What was tried and rejected

- **AbletonMCP for the build.** Can create tracks, load presets, write
  notes, set names and tempo. Cannot group devices, map macros, or set
  chain zones, because the Live API does not expose those. Verified against
  Live's own Object Model in `MCP.md`, not assumed. Still useful for
  loading finished `.adg` presets onto tracks and writing starter clips,
  and it CAN do track routing and audio/return track creation, which is why
  Sets are not generated as `.als`.
- **Building on ableton-inspector.** Read only, `.als` only, and its schema
  coverage stops well short of devices and racks. Useful only as
  confirmation that these files are gzipped XML and that samples live in
  `FileRef` elements.

The 13 slot grammar this document used to specify is in `THE_BASEMENT.md`.
