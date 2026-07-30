# Donors

Real device instances, used as source material for composition. Never
generate device XML from scratch.

A donor is wanted for its parameter list and each parameter's native range,
not for anybody's settings. Paths, names and annotations are stripped on
harvest, so a donor names no file and shows no name of its own in Live.

## One file, one device, named after it

`AutoFilter.adg` carries `AutoFilter`. That is the whole convention, and it
is load bearing in two places:

- **`Library.harvest` breaks a TIE first in favour of `donors/`, then in
  favour of the file named after the device.** A one-change probe is the
  same device with the same parameter count as the donor it was cut from,
  so it ties every time. Without the rule the winner is filename order,
  which is case-insensitive on Windows and case-sensitive elsewhere: the
  same repo would build different racks on different machines. It has
  happened twice. Once giving every generated rack a Wavetable with
  `Resonance = 0.4` instead of `0`; once when `racks/q17_a.adg` arrived and
  took Operator from `racks/s1_source.adg` on nothing but the letter q,
  handing every rack in the build glide on and a filter at 30 Hz.

  A fuller copy still wins on parameter count, ahead of both tie-breaks.
  That is deliberate: `racks/q20_a.adg` holds a 12.4.3 `MidiScale` with
  `InternalScale` and `UseCurrentScale`, and the donor here was harvested
  before Scale Awareness existed.
- **`Rack._find_skeleton` prefers a file named after a device it indexes.**
  Otherwise the skeleton is whichever rack of the right kind sorts first,
  so adding a file with an unrelated name rebuilds every rack. Also
  observed, on a rename.

`skeleton_drum.adg` and `skeleton_return.adg` are here because that
preference does not reach them: no donor holds a drum rack or a return
chain, so both fell through to `racks/` and were decided by sort order.
`racks/q23_a.adg` then took both, giving all eight DR1 pads a reverb send
at 0.339 that no spec declared. A template lifted from anywhere now has its
sends put back on the floor and its mappings stripped, and these two files
pin the shape so the fallback scan is never reached.

Three files break the convention on purpose, and their names say why:

| File | Holds | The one change | Evidence for |
|---|---|---|---|
| `InstrumentMeld filter Q 8.adg` | `InstrumentMeld` | Engine A filter Q to `8.0` | Q10 |
| `InstrumentVector filter 1 resonance 40.adg` | `InstrumentVector` | Filter 1 Res to `40` | Q11 |
| `Drift filter resonance 1.01.adg` | `Drift` | Filter Res to `1.01` | Q12 |

Each is the second half of a one-change diff, kept beside the donor it was
cut from so the pair stays legible. They are evidence, not donors, and the
two rules above are what stop them being used as one.

`Operator.adg` and `OriginalSimpler.adg` were harvested out of
`racks/s1_source.adg` for exactly that reason: both had been coming from
`racks/`, where the next spike file to sort earlier takes them. Harvesting
also stripped what the spike copy dragged along, a sample named
`00_KIck 1` with a machine-specific path, out of every Simpler PD1, VA1 and
DR1 place.

`MidiPitcher` and `Saturator` still come from `racks/`. A file added here
shadows the spike copy, which is the fix if either moves.

**Live's own installed content keeps its path.** A `FileRef` with
`RelativePathType 7` is part of the DEVICE, not a file somebody dragged in:
Hybrid Reverb's impulse response is one. Scrubbing it shipped a donor that
loaded with "Media files are missing" in both DR1 returns. `scrub` skips
those two fields now. Q27.

**Most of these were saved by 12.0_12203 and the schema has moved since.**
Live 12.4.3 writes `SchemaChangeCount 5` and renamed Compressor's sidechain
EQ from five children of a `SideChainEq` element to five flat
`SideChainEq_X` parameters. EQC wrote three settings at the old paths for a
whole release, and nothing could catch it: the DSL refuses a path the DONOR
lacks, and the donor had them. Q19.

So a stale donor is not merely a stale VALUE, it is a stale vocabulary.

**Every donor has now been compared by parameter NAME against Live 12.4.3's
own factory library**, 73 files over 59 devices, no Live open. Three
renames in total - `Compressor2`, `Limiter`, `MultiSampler` - plus two new
parameters each on `Chorus2`, `LoungeLizard` and `MidiRandom`. Those five
were re-harvested and the other 53 left alone, because an addition breaks
nothing and re-harvesting a device moves every rack that uses it. Q28 has
the table and the reasoning.

Re-run that scan after a Live update. It answers the question a version
bump actually raises, which is not "did anything change" but "did anything
I BIND change".

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

A stock donor is enough to write and verify every binding, and not enough
to ship a rack anyone wants to play. Re-harvesting from configured devices
is worth doing before sound design starts, and costs nothing already spent:
replacing a file here changes no code.

## Adding more

```
patchbay harvest "path/to/a Project"
```

Reads `.adg`, `.adv` and `.als`, writes one file per device, and skips any
tag the library already indexes. That last part is not politeness: a fuller
copy of a device already here would win on parameter count and rebuild
racks that were gated in Live against the old one.

For a donor meant to carry SOUND rather than only paths and ranges, build
the device in Live inside a rack, save it, and harvest that file. Replacing
a donor changes no code.

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
  `donors/InstrumentMeld.adg` against
  `donors/InstrumentMeld filter Q 8.adg`. See Q10 in `SCHEMA.md`.
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

Operator and Simpler are the exception and store envelope times in
MILLISECONDS, 1..60000 against Wavetable's 0.0015..20. See
`ARCHITECTURE.md` section 4: the unit belongs to the parameter, and nothing
in the file marks it.

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
