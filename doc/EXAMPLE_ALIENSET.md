# EXAMPLE_ALIENSET

A template live set for electronica and experimental techno. `examples/alienset.py` is the spec that compiles this set.

## Goal

Create a lean, CPU-efficient live set that borrows the best ideas from other examples in this repo:
1. The **consistency** of `EXAMPLE_PLAYGRND` (the `PB` layout for instruments, nested racks, sound families).
2. The **simplicity and efficiency** of `EXAMPLE_TECHNO` (series FX racks that use no CPU when turned down, and self-contained drum kits).

This avoids the "heavy beast" problem of having a massive 7-device channel strip on every track, keeping the set agile and focused on the sound engines.

## The Eight Tracks

| Track | Type | Role |
|---|---|---|
| DR | MIDI | Drum rack with self-contained internal return chains |
| BS | MIDI | Multi engine bass (FM, Wavetable, Meld) |
| PD | MIDI | Polyphonic pads, evolving textures (Wavetable, Drift) |
| LD | MIDI | Leads (FM, Meld) with glide |
| ARP | MIDI | Standalone Arpeggiator feeding a Lead instrument |
| SR | MIDI | Sampler track for glitch/granular textures |
| VA1 | MIDI | Various, nests PADS and KEYS |
| PM | Audio | Pre-master bus / Master FX track |

Every track from 2 to 7 routes its output into `PM`, and sidechains from `DR`. 

## The FX Strategy: ALIEN_FX

Instead of a heavy selector where every chain calculates audio constantly, `EXAMPLE_ALIENSET` uses a single `ALIEN_FX` series rack on every synth track. 

This rack chains devices in series:
`Erosion -> BeatRepeat -> Roar -> Echo -> ChannelEq -> Saturator`

Each device's `DryWet` or `Amount` is bound to a macro, but **crucially, so is its `On` switch**. When the macro is at 0, the device is bypassed and consumes 0 CPU. As you turn up the knob, the device switches on and blends into the signal path. This allows every track to have an elaborate effects strip without crippling your processor before you even play a note.

## Instrument Layout (PB)

We preserve the 8-slot `PB` layout from `playgrnd` because muscle memory is the product:

| # | Slot | Notes |
|---|---|---|
| 1 | Instrument | Which engine |
| 2 | Sound | Which sound within that engine |
| 3 | Filter | Cutoff, paired with resonance |
| 4 | Drive | Filter drive |
| 5 | Movement | LFO or modulation depth |
| 6 | Character | Per-rack wildcard (e.g. Attack, Glide, Morph) |
| 7 | Release | Release or decay |
| 8 | Volume | Always |

## Drum Rack (DR)

The Drum Rack uses 8 pads spread across the bottom two rows of Push. 
It diverges from `playgrnd` by keeping all its **Returns internal**. The `A` and `B` sends at the pad level feed directly into a Reverb and a Delay rack hidden inside `DR` itself. This makes the drum kit completely self-contained and ready to be dragged into any other set without needing external return tracks.
