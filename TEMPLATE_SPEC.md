# Template spec

The musical target that `adgkit` exists to serve. Read this alongside
`CLAUDE.md`, which covers the tooling.

## Goal

A hyper-mapped Ableton Live template for Push 3, run tethered to a
computer (so VSTs are available, no standalone restrictions). Darkwave and
minimal techno. The design goal is that the mouse is never needed during a
jam: every meaningful control sits on a macro, reachable from Push encoders.

Modelled on a commercial template called PLAYGRND. We are not copying its
files, we are rebuilding the same architecture to taste.

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

The template advertises 18 engines and ~692 sounds. That is ~38 sounds per
engine, which means a "sound" is NOT a chain. Chains are engines. Sounds are
**Macro Variations**.

This matters enormously for `adgkit`: the expensive, repetitive, worth
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

1. Engine select (chain selector)
2. Cutoff
3. Resonance
4. Decay / release
5. Drive
6. Movement (LFO or mod depth)
7. Space (reverb send)
8. Character (per rack wildcard)

Racks support up to 16 macros. Push shows 8 per page. Page 2 holds glide,
detune, delay feedback, width, transient.

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

## Current state in Live

- 8 tracks created and named, PM1 recreated as audio
- One DR1 pad built and mapped end to end, three levels deep, verified
  working through all three macro hops
- Nothing else built

## What was tried and rejected

- **AbletonMCP for the build.** Can create tracks, load presets, write
  notes, set names and tempo. Cannot group devices, map macros, or set
  chain zones, because the Live API does not expose those. Still useful for
  loading finished `.adg` presets onto tracks and writing starter clips.
- **Building on ableton-inspector.** Read only, `.als` only, and its schema
  coverage stops well short of devices and racks. Useful only as
  confirmation that these files are gzipped XML and that samples live in
  `FileRef` elements.
