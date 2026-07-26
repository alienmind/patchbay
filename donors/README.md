# Donors

Real device instances harvested from Live, used as source material for
composition. Never generate device XML from scratch.

Each donor needs a line here recording what it contains and which Live
version produced it, because the schema is version specific.

| File | Contains | Params | Configured | Live version |
|---|---|---|---|---|
| `Wavetable Rack.adg` | `InstrumentVector` | 93 | no, stock | 12.4.3 |
| `Drift Rack.adg` | `Drift` | 66 | no, stock | 12.4.3 |
| `Meld Rack.adg` | `InstrumentMeld` | 129 | no, stock | 12.4.3 |

`Operator`, `OriginalSimpler`, `MidiPitcher`, `Reverb` and `Saturator` are
not here. They are harvested from `racks/`, which is spike evidence that
happens to contain them. `Library.default()` reads `donors/` first and
`racks/` second, so a donor added here shadows the spike copy.

## `spikes/` is not harvested, on purpose

| File | Derived from | One change | Evidence for |
|---|---|---|---|
| `spikes/q10_a.adg` | `Meld Rack.adg` | Engine A filter Q to `8.0` | Q10 |
| `spikes/q11_a.adg` | `Wavetable Rack.adg` | Filter 1 Res to `40` | Q11 |
| `spikes/q12_a.adg` | `Drift Rack.adg` | Filter Res to `1.01` | Q12 |

These are the second half of a one change diff, kept next to the donor
each was cut from so the pair stays legible. They are NOT donors, and the
subfolder is what stops them being treated as such.

`Library.default()` globs `donors/*.adg` without recursing, so anything in
`spikes/` is invisible to it. That is load bearing, not tidiness:

**A tie is broken by filename order, and filename order is
case-insensitive on Windows.** `harvest()` keeps whichever instance has
MORE parameters and, on a tie, whichever it saw first. A probe file is the
same device with the same parameter count as the donor it came from, so it
ties every time. Sitting alongside, `q11_a.adg` sorted before
`Wavetable Rack.adg` (lowercased `q` before `w`, not ASCII `W` before `q`)
and won. Every generated rack would have carried a Wavetable with
`Resonance = 0.4` instead of `0`, with nothing reporting it.

So: probe files never share a directory with the donor they were cut from.

## Configured or not

The **Configured** column is not bookkeeping. `THE_BASEMENT.md` records
that a device loads with every parameter deleted, because Live fills in
whatever is absent. So a donor is never needed for a file to LOAD. It is
needed for two other things, and they come apart:

- **Parameter paths.** Complete in a stock donor. The whole point of rule 1
  in `CLAUDE.md` is that `PreDrive` and
  `Filter/Slot/Value/SimplerFilter/Freq` are not guessable, and a stock
  device names every parameter it has. Bindings can be written against a
  stock donor with no loss.
- **Sound.** Absent in a stock donor. A rack built from one arrives at
  Live's defaults and sounds like the device's init patch.

The three above are stock. That is enough to write and verify every
binding, and not enough to ship a rack anyone wants to play. Re-harvesting
with configured devices is worth doing before sound design starts, and
costs nothing already spent: replacing a file here changes no code.

## How to harvest

1. Build the device in Live, inside a rack. Configure it to sound like
   something you want if the donor is meant to carry sound.
2. Save the rack to User Library
3. Copy the .adg here and document it above, including whether it is
   configured

## Verified parameter paths

Found with `library.Device.search()`, not written from memory. Recorded
because these are the paths the instrument racks bind against.

| Device | Cutoff | Resonance | Decay |
|---|---|---|---|
| `InstrumentVector` | `Voice_Filter1_Frequency` | `Voice_Filter1_Resonance` | `Voice_Modulators_AmpEnvelope_Times_Decay` |
| `Drift` | `Filter_Frequency` | `Filter_Resonance` | `Envelope1_Decay` |
| `InstrumentMeld` | `MeldVoice_EngineA_Filter_Frequency` | `MeldVoice_EngineA_Filter_Macro1` | `MeldVoice_EngineA_AmpEnvelope_Times_Decay` |

Notes worth having before writing bindings:

- **Wavetable and Meld are two engine devices.** Each has a `Filter1`/
  `Filter2` or `EngineA`/`EngineB` pair. Binding one macro to one side
  only moves half the sound. Which side, or both, is a decision per rack.
- **Meld's filter names its knobs `Macro1` and `Macro2`.** The GUI calls
  them **Q** and **L-B-H-N**. Nothing matching "res" or "q" exists in the
  parameter list, so a search for resonance returns nothing and the wrong
  conclusion is that Meld has none. It has one. The whole filter is
  `FilterType`, `Frequency`, `Macro1`, `Macro2`.
- **`Macro1` is Q, `Macro2` is L-B-H-N.** Verified by one change diff,
  `donors/Meld Rack.adg` against `donors/spikes/q10_a.adg`. See Q10 in
  `SCHEMA.md`.
- **Displayed units are not stored units, and there is no conversion
  rule.** See the measured ranges below.
- **`Macro1`/`Macro2` change meaning with `FilterType`.** They are the two
  knobs the filter type happens to offer, not fixed roles. A binding is
  only correct for the filter type the donor was saved with, here
  `FilterType = 0`, SVF 12dB.
- **L-B-H-N is a morph**, lowpass through bandpass, highpass, notch, on one
  continuous control. That is a strong candidate for a `Character` slot: a
  single knob that changes filter behaviour rather than degree.
- **Wavetable and Meld envelopes split `Times` from `Slopes`.**
  `..._Times_Decay` is the duration; `..._Slopes_Decay` is the curve.
  Binding the wrong one produces a macro that changes the shape of a decay
  without changing its length.

## Stored ranges, measured

**Bind against these, not against what Live displays.** Verified by one
change diff: Q10, Q11 and Q12 in `SCHEMA.md`.

| Device | Parameter | UI shows | Stored | Relationship |
|---|---|---|---|---|
| all three | Cutoff | Hz | Hz | 1:1 |
| `InstrumentVector` | Filter 1 Res | 0..100 | 0..1 | UI/100 |
| `InstrumentMeld` | Filter Q | 0..100 | 0..1 | UI/100 |
| `Drift` | Filter Res | 0..1.01 | 0..1.01 | 1:1 |
| all three | Envelope times | ms | s | UI/1000 |

Four families, three relationships, and no rule that converts one to
another. A range is measured or it is wrong.

**The relationship belongs to the PARAMETER, not the device.** Meld proves
it: its Q is normalised and its envelope is unit-converted, in the same
device. Knowing how one parameter stores tells you nothing about the one
next to it.

Two tells worth knowing:

- Drift clamping a typed `40` down to `1.01` says its display is near its
  stored range. A control whose maximum is not 100 is usually honest.
- A real displayed unit (Hz, dB) suggests native storage. A bare number,
  or a prefixed unit like ms, does not: envelope times display in ms and
  store in seconds, so the displayed `600` is `0.6` on disk.

Measuring a range is two saves: set the parameter to its minimum, save,
read the stored value; set it to its maximum, save, read again. Only
needed for parameters a rack means to narrow with `bind(path, lo, hi)`.
A cheaper first move is one save at a value that cannot be confused, `40`
where the maximum might be 100, which is how Q11 and Q12 were settled.
