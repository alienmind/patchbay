# PATCHBAYGROUND

The musical target that `patchbay` exists to serve, and the spec
`examples/patchbayground.py` compiles. Read this alongside `CLAUDE.md`,
which covers the tooling.

## Inspired by PLAYGRND

The idea came from **PLAYGRND**, an Ableton Live Set by **Andri Soren**:
https://www.youtube.com/watch?v=plQ9F-0RmDw

What that Set demonstrates is an architecture: one macro grammar across every
rack, engines as chains, sounds as macro variations, three levels of nesting
inside a drum rack. This document reconstructs that shape to our own taste,
and the numbers it reasons from - 18 engines, ~692 sounds - are the publicly
stated ones.

Assembling a template of that kind by hand is thousands of macro mappings and
tens of thousands of variation values, entered one at a time by mouse. **That
tedium is what `patchbay` exists to remove.**

## Goal

A hyper-mapped Ableton Live template for Push 3, run tethered to a
computer (so VSTs are available, no standalone restrictions). Darkwave and
minimal techno. The design goal is that the mouse is never needed during a
jam: every meaningful control sits on a macro, reachable from Push encoders.

## The eight tracks

| Track | Type | Role |
|---|---|---|
| DR1 | MIDI | Super Drum Rack, RYTM inspired, per pad sends and FM |
| BS1 | MIDI | Multi engine bass |
| PD1 | MIDI | Polyphonic pads, Wavetable based |
| LD1 | MIDI | Leads, FM based, mono with glide |
| SR1 | MIDI | Sampler, built in sounds plus a hot swap slot |
| VA1 | MIDI | Various, nests all five instruments above |
| VA2 | MIDI | Various, second instance |
| PM1 | **Audio** | Pre master |

Tempo 128. Eight return tracks.

## The architectural insight

18 engines and ~692 sounds is ~38 sounds per engine, which means a "sound" is
NOT a chain. Chains are engines. Sounds are **Macro Variations**.

Arithmetic, and the most useful thing to know before writing any code.

This matters enormously for `patchbay`: the expensive, repetitive, worth
automating artifact is the macro variation set, not the chain structure.
Generating variations by permuting macro values is the highest value module
in the project.

CPU works out because instrument chains receiving no MIDI idle at near
nothing. Many instrument chains are cheap. Many parallel audio effect
chains are not, which is why effect racks use selectors instead of stacks.

## Sound families

Variations are built in parallel across engines, not independently.
Engine 0 variation 73 and engine 1 variation 73 are deliberately the same
musical idea rendered through different synthesis, with the last engine
usually being the FM treatment.

Consequence: the Engine knob becomes a *variation* control rather than a
jump into unrelated territory. Any generator must produce variation sets
index-aligned across engines, not independently randomised per engine.

## Macro grammar

Identical across every instrument rack so muscle memory transfers. This
consistency is the actual product, more than any individual rack.

Declared once, in `examples/patchbayground.py`, and passed to every rack:

```python
PATCHBAYGROUND = Grammar(
    "Engine",      # 1  chain selector
    "Cutoff",      # 2
    "Resonance",   # 3
    "Decay",       # 4  decay or release, whichever the engine has
    "Drive",       # 5
    "Movement",    # 6  LFO or mod depth
    "Space",       # 7  reverb send
    "Character",   # 8  per rack wildcard
    "Glide",       # 9  page two
    "Detune",      # 10
    "Delay",       # 11 delay feedback
    "Width",       # 12
    "Transient",   # 13
)
```

Racks support 16 macros. Push shows 8 per page, so slots 1-8 are page one
and 9-13 page two. Slots 14-16 are deliberately unassigned: this document
does not name them, and inventing slots would be inventing intent.

The grammar is a CONTRACT, not a template. A rack does not "have" these
macros, it BINDS its own parameters to these slots:

```python
with rack.engine("FM", "Operator") as e:
    e.bind(cutoff=("Filter/Frequency", 200, 8000),
           decay="Filter/Envelope/DecayTime")
```

Every engine binding the same slot to its own parameter is what makes the
sound family constraint below structural rather than a matter of
discipline. Ranges are optional and scope what the macro reaches; Live
12.4.3 has no UI for them, so they exist only in code.

Every sound also maps aftertouch to filter and pitch. Exception: drum rack
pads, since Push does not send per pad aftertouch there.

## DR1 structure

Three levels of nesting per pad. This is the pattern `clone.py` must
replicate across 8 pads:

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

Drum Rack top level macros are reserved for kit wide moves (global tune,
decay, drive, send A select, send B select) because 8 pads times 8
parameters cannot fit 8 knobs. Pad level controls are reached by diving
into the pad on Push, which is free.

DR1 return chains live inside the Drum Rack via Show Return Chains, and each
contains a selector across several reverbs and delays, so a macro swaps the
*effect*, not just the send level.

## Sidechain

No ghost track. The channel strip compressor sidechains from DR1 with the
sidechain EQ set to a low band only, so it tracks the kick and ignores hats.
Reverb returns are sidechained too, not just instrument channels.

## PM1

The Master track has no Session clip slots, so master bus moves cannot be
automated in Session view. PM1 solves this: an audio track that all seven
other tracks route into, carrying the master chain, with silent dummy clips
holding automation envelopes. Requires Session Automation Recording enabled
in Record/Warp/Launch preferences.

## Current state

**In Live, by hand:**

- 8 tracks created and named, PM1 recreated as audio
- One DR1 pad built and mapped end to end, three levels deep, verified
  working through all three macro hops. That rack is `racks/s1_source.adg`
  and it is the evidence for the whole nesting model.

**In code, `examples/patchbayground.py`:**

- The grammar above, complete
- PD1 as a two engine slice, Operator and Simpler. Compiles, loads on a
  MIDI track, and both engines answer the same macros. Verified in Live
  12.4.3, not merely generated.
- 96 variations on PD1, over engine, cutoff, decay and resonance. All 96
  recall in Live, and a variation selects its own engine.

**Not yet declarable, and why:**

| rack | blocked on |
|---|---|
| DR1 | rack-inside-chain nesting in the DSL, and per-pad sends |
| BS1, PD1 proper, LD1 | donors for Wavetable, Drift, Meld |
| SR1 | sample retargeting bound into the DSL |
| VA1, VA2 | rack-in-rack composition |
| PM1 | not a rack; built through `ableton-mcp` |

Variations were the largest gap and are now built, which this document
argued for: they are the highest value artifact in the project. They arrive
on any rack whose slots are bound, so each row above gains its variation
grid the moment the rack itself is declarable.

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
