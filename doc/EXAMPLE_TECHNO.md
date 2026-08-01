# EXAMPLE_TECHNO

`donors/Techno/Techno.als` is a Live 11.0.11 Set at 135 BPM containing a drum rack and seven synth tracks. The `examples/techno.py` script rebuilds its drum rack as a PatchBay declaration.

This document compares `techno.py` against `playgrnd.py` to identify which design choices are structural and which are subjective taste. Since `techno.py` is much simpler, it serves as a baseline for understanding how PatchBay structures racks.

## What was rebuilt

| | Racks | Mappings verified against the donor |
|---|---|---|
| Select racks | 8 | 10 each, exact |
| FX racks | 5 | 10, 15, 16, 4, 9 - exact |
| the kit | 1 | 0, it has none |

Every mapping matches the donor on macro index, device position, device tag, parameter path, and range. Pad notes match exactly (92 down to 85).

Not rebuilt: Amb 1, Perc 1, and the five tracks carrying loose devices. The open work for these is tracked in `doc/TODO.md`.

## Structural Agreements (Where both examples align)

**Unified Layout:** The eight Select racks use identical layouts, carrying the same ten bindings over the same ranges. They only differ in knob start positions and sample loaded. This confirms that repeated layouts are a natural Live design pattern, not an artifact of the DSL.

**Standard Drum Range:** The kit is mapped to notes 36..43, perfectly aligning with the bottom two rows of a Push grid.

**Deliberate Start Positions:** Bipolar knobs are parked at their center (e.g., PAN at 63.5, PITCH at 0 semitones). Low-pass filters start fully open at 127. 

**Aggressively Narrowed Ranges:** Effects are tightly constrained (e.g., Overdrive 0..50, Reverb 0..0.5). Narrow ranges ensure a knob's full sweep is musically useful without ruining the sound.

**Shared Knobs:** Multiple parameters are grouped under single ideas. One knob drives both decay and release. Another tilts EQ bands together for a consistent perceived loudness. 

**Dummy Macros:** Macros can be mapped to parameters that have no effect depending on the loaded sample (e.g., sample selector on a chain with only one sample). This allows uniform mapping without breaking the structure.

## Structural Differences (Where the examples diverge)

### Series vs. Selector (FX Routing)

`playgrnd` uses a chain selector for FX: 8 parallel effect chains where only one is active at a time to save CPU.

`techno` uses series processing: 8 to 10 effects run sequentially in a single chain. Knobs control "how much" of an effect is applied, rather than "which" effect is used, acting like a mixing desk over a fixed path.

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
### Returns inside the rack, not on the Set

This Set has **no return tracks at all**. Instead, four returns live INSIDE the drum rack. This makes the drum kit a completely self-contained instrument that travels with its own effects, whereas `playgrnd` relies heavily on global Set-level return tracks.

Naming diverges as well. `playgrnd` names returns for their character (e.g., `A-Rvb:Short`), which survives reuse. `techno` names them for what feeds them (e.g., `b Delay C/S` for claps and snares), which documents intent.

### Drum kit macros

**The drum rack has no macros at all.** All 16 macros are left unnamed and unbound. Every control lives one level down, inside individual pads. Because each pad is tuned independently, a kit-wide knob would blindly move all eight pads off their carefully dialed settings together.

Both Sets agree on one structural point: drum rack slots do not use chain selectors because pads are triggered by MIDI notes, not macro zones.

### Layout naming

| `playgrnd` Layout (`PB`) | `techno` Layout |
|---|---|
| Instrument, Sound, Filter, Drive, Movement, Character, Release, Volume | SAMPLE SELECTR, PITCH, DECAY, SAMPLE START, HPF, LPF, PAN, VOLUME |

The `PB` layout is abstract because it has to work across Operator, Simpler, Wavetable, Drift, and Meld. The `techno` layout only drives Samplers, so its slots are named exactly for what they control. A layout should only be as abstract as necessary.

### Racks as parallel mixers

The `RIDE DELAY` rack uses two chains: `Wet` and `Dry`, both set to zone `0/0/0/0`. This means both sound simultaneously, acting as a parallel mixer where the `Dry` chain is just a bypass path. `playgrnd` uses zones distributed across 0..127 to create selectors, not mixers.

### Filters built out of EQs

Every pad's high-pass and low-pass filters are built using Eq8 bands parked at the ends of their ranges (10 Hz and 22 kHz). Both bands are active but inaudible until moved by a macro. This provides a playable filter pair without needing an actual Auto Filter device, saving CPU compared to `playgrnd`'s approach.

## Toolchain Findings and Limitations

Rebuilding this Set uncovered a few limitations in PatchBay's DSL and extraction logic:

1. **Drum Pad Note Extraction:** `extract.preset_from_set` originally lost MIDI note assignments because a drum branch stores them differently than a standard chain. This was fixed.
2. **Missing Devices:** `FrequencyShifter` was missing from the PatchBay library entirely. Running `patchbay harvest` indexed it automatically.
3. **Chaining Limitations:** A chain cannot currently hold a rack followed by loose devices. `techno`'s chains look like `[Select rack] -> [FX rack] -> Eq8 -> StereoGain`, but the DSL's `then()` method only chains Engines, and `Nested()` only wraps a single rack. As a workaround, the racks were built separately.
4. **Silent Drops:** `patchbay extract` silently drops trailing devices in unsupported chains. This is a known issue tracked in `TODO.md`.

## Manual Verification Required

One detail cannot be automatically verified from the file: `MidiCCOnOffThresholds`. When macros toggle a device's `On` state, the XML stores a threshold, but the DSL does not explicitly manage this yet. 

To verify:
1. Load `build/bt/PERC_FX.adg` onto an audio track.
2. Leave all macros at 0 (All devices should be BYPASSED).
3. Turn up Macro 5 (SATURATION) (Saturator should switch ON).
4. Turn Macro 5 back to 0 (Saturator should switch OFF).
