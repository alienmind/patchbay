# Schema findings

Every entry here must come from a diff, not a guess.
Format: what was changed in Live -> which node moved.

See `SPIKES.md` for the recipe that produces each entry.

## Environment

- Live version: **12.4.3**
- OS: Windows 11
- Findings below are valid only for that version.

Read straight from the `<Ableton>` root attributes rather than the About
box, so any donor or rack can be version-checked without opening Live:

```
MajorVersion="5" MinorVersion="12.0_12402" SchemaChangeCount="5"
Creator="Ableton Live 12.4.3"
Revision="e3d8be4d07c71dbd4de9e4183bf90652f680375b"
```

`SchemaChangeCount` is the one to watch after a Live update. If it moves,
re-run the spikes.

## S1. Round trip fidelity - PASSES

`racks/s1_source.adg`, an Instrument Rack, 559,674 bytes of XML,
18,148 facts.

`patchbay roundtrip` reports **structurally identical: YES** with ids
included - no fact lost, invented or renumbered. Output loads in Live 12.4.3
and presents identically.

Bytes differ by 20,252 (lxml serialiser vs Live's), from four cosmetic
causes, none semantic:

| | Live writes | lxml writes | cost |
|---|---|---|---|
| declaration | `<?xml version="1.0" encoding="UTF-8"?>` | `<?xml version='1.0' encoding='UTF-8' standalone='no'?>` | ~16 B |
| line endings | CRLF | LF | ~13,600 B |
| empty elements | `<X />` | `<X/>` | 6,656 B |
| end of file | trailing newline | none | 2 B |

**Live tolerates all four.** So `io.save` does not need to reproduce Live's
byte conventions, and no code should depend on byte identity.

Consequence for later spikes: never diff `.adg` files with a byte-level
tool, only with `patchbay diff`. A byte diff of two semantically identical
files reports ~20 KB of noise.

Open option, not currently needed: making `io.save` byte-exact (CRLF,
double-quoted declaration, `<X />`) would turn round trip into an exact
regression check. Deferred - it means post-processing serialised bytes,
which is its own risk, and S1 passing means nothing requires it.

## S2. Noise floor - PASSES, floor is zero

`racks/s2_a.adg` / `racks/s2_b.adg`, same Drum Rack saved twice with no
edit between saves. Eight facts moved, in two groups. Neither group is a
mystery, and after retuning the filter `patchbay diff` reports `identical`.

### Ids do NOT churn. This is the headline.

`--with-ids` produced **byte-for-byte the same report** as the filtered
run. Live preserved every `Id`, `PointeeId`, `LomId` and `LomIdView`
across the save.

Consequences:

- The original default of hiding ids was throwing away signal for no
  benefit. It would have hidden the answer to S3, where the mapping is
  likely *made of* ids.
- Ids are now **shown by default**; `--hide-ids` opts out.
- Early positive signal for S6 and therefore Phase 2: ids are stable
  identities, not per-save serial numbers. Still to be established is
  what happens when a device is *added* - stability across a no-op save
  does not prove stability across an edit.

### Genuine per-save churn: `RoundRobinRandomSeed`

Four occurrences, one per Simpler, new random value on every save:

```
.../OriginalSimpler/Player/MultiSampleMap/RoundRobinRandomSeed@Value
    940716808  ->  1038285703
```

Live reseeds sample round-robin on save. Added to `SAVE_NOISE` in
`diff.py`, hidden by default, visible with `--all`.

### Not noise: preset self-identity

Four facts changed because the two saves have different filenames:

```
GroupDevicePreset/PresetRef/FilePresetRef/FileRef/Path@Value
GroupDevicePreset/PresetRef/FilePresetRef/FileRef/RelativePath@Value
GroupDevicePreset/Device/DrumGroupDevice/LastPresetRef/Value/FilePresetRef/FileRef/Path@Value
GroupDevicePreset/Device/DrumGroupDevice/LastPresetRef/Value/FilePresetRef/FileRef/RelativePath@Value
```

A rack stores where it was last saved, in two places: `PresetRef` (the
preset's own identity) and the device's `LastPresetRef`. Both carry an
absolute `Path` and a User-Library-relative `RelativePath`.

This is a real Phase 4 finding, not churn - but it is unavoidable churn
in *every* spike pair, since a pair needs two filenames. Hidden by
default via `PRESET_REF_MARKERS`, visible with `--all`.

Note the shape: `FileRef` with parallel `Path` + `RelativePath` is the
same structure S7 will meet for samples. Landmine #2 in `CLAUDE.md`
applies here too - these travel in pairs and must stay consistent.

### Filter state after S2

| group | contents | default |
|---|---|---|
| `ID_FIELDS` | Id, PointeeId, LomId, LomIdView | **shown** |
| `SAVE_NOISE` | RoundRobinRandomSeed | hidden |
| `PRESET_REF_MARKERS` | `/PresetRef/`, `/LastPresetRef/` | hidden |

Verified: `patchbay diff racks/s2_a.adg racks/s2_b.adg` prints `identical`.

### Incidental

`s1_source` / `s2_*` is a Drum Rack nested
`DrumBranchPreset -> GroupDevicePreset -> InstrumentBranchPreset ->
GroupDevicePreset -> InstrumentBranchPreset`, i.e. already the DR1
three-level pattern from `PATCHBAYGROUND.md`. Good subject for S4 and S6.

## S3. Macro mapping - ANSWERED

**A macro mapping is a `KeyMidi` element on the target parameter.**
There is no id, no pointer and no path string. The target is named by
containment: the parameter that owns the `KeyMidi` is the mapped one.

```xml
<PreDrive>
  <LomId Value="0" />
  <KeyMidi>
    <PersistentKeyString Value="" />
    <IsNote Value="false" />
    <Channel Value="16" />
    <NoteOrController Value="0" />
    <LowerRangeNote Value="-1" />
    <UpperRangeNote Value="-1" />
    <ControllerMapMode Value="0" />
  </KeyMidi>
  <Manual Value="0" />
  <MidiControllerRange><Min Value="-36" /><Max Value="36" /></MidiControllerRange>
  <AutomationTarget Id="0"><LockEnvelope Value="0" /></AutomationTarget>
  <ModulationTarget Id="0"><LockEnvelope Value="0" /></ModulationTarget>
</PreDrive>
```

Live implements rack macros as MIDI CC on a virtual channel:

| field | meaning |
|---|---|
| `Channel` = 16 | the virtual macro bus, not a real MIDI channel |
| `NoteOrController` | **macro index, zero-based**. 0 = Macro 1 |
| `IsNote` = false | a controller, not a note |
| `ControllerMapMode` = 0 | absolute |
| `PersistentKeyString` = "" | empty for macro mappings (computer-key mapping field) |
| `LowerRangeNote` / `UpperRangeNote` = -1 | unused when `IsNote` is false |

Which rack owns the macro is **not** stored - it is resolved structurally.
The rule is *not* "nearest enclosing rack device": in preset format a
rack's `Device` and its `BranchPresets` are siblings, so a mapped
parameter is never a descendant of the rack node owning the macro. Walk up
to the nearest `BranchPresets`, then take its parent's
`Device/*GroupDevice`. See `ARCHITECTURE.md` §3 and S4 below.

Verified across four files:

| file | KeyMidi count | targets |
|---|---|---|
| `s3_a.adg` | 0 | unmapped control |
| `s3_b.adg` | 1 | `Saturator/PreDrive` |
| `s1_source.adg` / `s2_a.adg` | 3 | two `MacroControls.0`, one `ChainSelector` |

`ChainSelector` is mappable by exactly the same mechanism, which matters
for `PATCHBAYGROUND.md`'s chain-select layout.

### Implications

- **Addressing is by containment, so mappings survive a subtree copy
  unchanged.** Landmine #1 in `CLAUDE.md` (cloning cross-wires mappings via
  duplicated ids) **does not apply to macro mappings**. Phase 2 gets
  materially cheaper. S6 still governs whatever else uses ids.
- To map parameter P to macro N, insert a `KeyMidi` block as a child of P
  with `NoteOrController = N-1`. To unmap, delete the element.
- `KeyMidi` is written lazily: absent until the parameter is mapped.
  Its presence is therefore a reliable "is mapped" test.
- Element order within the parameter puts `KeyMidi` after `LomId` and
  before `Manual`. Whether Live cares about that order is untested.

### Still open

1. ~~`NoteOrController` = macro index is inferred.~~ **Closed by S3b** -
   confirmed with Macro 2 -> `CC=1`.
2. Live 12 supports a custom min/max range per mapping. Not present in
   any sample here; likely `MidiControllerRange` on the target parameter,
   which currently holds the parameter's full range (`-36..36` for Drive).
   Belongs with S10.

### Method note

The first pass at this spike wrongly concluded the mapping was absent,
by reading the `KeyMidi` block as empty MIDI-mapping defaults. It was the
finding. Two follow-on errors came from the same guess: treating
`racks/s2_a.adg` as an unmapped control because its macros had default
names and zero values - it has three mappings - and looking for an
id-based reference because that is what `CLAUDE.md` predicted.

Lesson, consistent with the project method: a diff of a single confirmed
change contains the answer somewhere. When it appears not to, the reading
is wrong, not the diff.

## S3 (superseded first pass) - why it looked inconclusive

`racks/s3_a.adg` / `racks/s3_b.adg`. Audio Effect Rack containing one
Saturator. Between saves, Drive was mapped to Macro 1 via right-click ->
Map to Macro 1. Nothing else touched.

**The mapping is not in the file.** Verified two ways, which agree:
`patchbay diff` and a raw `difflib` line diff of the unpacked XML (66 lines
total). This rules out a `flatten` blind spot.

The complete set of differences:

1. `AudioEffectGroupDevice/MacroControls.0/Manual` `0` -> `63.5`
2. A `KeyMidi` block appeared on `Saturator/PreDrive` (Saturator's Drive
   knob is `PreDrive` internally). All fields are empty defaults:
   `PersistentKeyString=""`, `IsNote=false`, `Channel=16`,
   `NoteOrController=0`, `LowerRangeNote=-1`, `UpperRangeNote=-1`,
   `ControllerMapMode=0`.
3. `PresetRef` changed from `AbletonDefaultPresetRef` to `FilePresetRef`
   - first save vs re-save, unrelated.

### The macro value proves Live made the mapping

Drive's `MidiControllerRange` is `-36..36`; its `Manual` is `0`, exactly
mid-range. `0..127` mid-range is `63.5`, the value written. Live derived
the macro position from the mapped parameter, so the link existed in the
session. It just did not reach the file.

### Where the mapping is NOT

Ruled out by inspection, worth recording so nobody re-checks:

- **On the macro.** `MacroControls.0` contains only `LomId`,
  `Manual`, `MidiControllerRange`, `AutomationTarget Id="0"`,
  `ModulationTarget Id="0"` - identical in shape to an unmapped rack.
- **On the target parameter.** `PreDrive` has the same five children plus
  the new empty `KeyMidi`. No pointer of any kind.
- **On the rack device.** `AudioEffectGroupDevice` has ~160 children:
  `MacroDisplayNames.0-15`, `MacroDefaults.0-15`, `MacroAnnotations.0-15`,
  `MacroColor.0-15`, `ForceDisplayGenericValue.0-15`,
  `ExcludeMacroFromRandomization.0-15`, `ExcludeMacroFromSnapshots.0-15`,
  `MacroVariations`, `MacroSnapshots`, `NumVisibleMacroControls`. None
  carries a target reference.
- **Ids.** Every `Pointee`, `AutomationTarget` and `ModulationTarget` in
  both files is `Id="0"`. Preset files appear to zero these; they are not
  the mapping mechanism here.
- **`ModConnections.N` / `Connection` / `Amount` / `Slot`.** These exist in
  quantity but belong to Simpler's internal modulation matrix, not macros.

### Resolution

`racks/s3_b.adg` reloads in Live with Macro 1 correctly driving Drive, so
the mapping was in the file all along - as the `KeyMidi` block. Kill
criterion **not triggered**; see the answered section above.

Retained as a caution: a macro whose display name is the default
`Macro N` and whose value is `0` may still be mapped. Neither field is
evidence either way. Count `KeyMidi` elements instead.

## S3b. Macro index confirmation - ANSWERED

`racks/s3_b.adg` -> `racks/s3b.adg`. Saturator's Output mapped to Macro 2,
on top of the existing Drive -> Macro 1. Both macros then moved.

**`NoteOrController` is the zero-based macro index. Confirmed.**

```
Saturator/PostDrive/KeyMidi/NoteOrController@Value = 1     (Macro 2)
Saturator/PostDrive/KeyMidi/Channel@Value          = 16
```

`Channel` stays 16 for the second macro, so the bus is fixed and only the
CC number varies. `patchbay mappings racks/s3b.adg` reports both correctly.

### Internal name: Output is `PostDrive`

Second confirmation that GUI labels are not element names. Saturator:
Drive = `PreDrive`, Output = `PostDrive`. Their ranges differ -
`-36..36` and `-36..0` - so ranges are per parameter, not per device.

### Macro to parameter transfer function

**Linear over the target's own `MidiControllerRange`:**

```
value = Min + (macro / 127) * (Max - Min)
```

Verified twice in this pair:

| macro | value | target range | computed | stored |
|---|---|---|---|---|
| `MacroControls.0` = 69 | Drive | `-36..36` | `3.11811024` | `3.11810875` |
| `MacroControls.1` = 127 | Output | `-36..0` | `0` | `0` |

The 1.5e-6 discrepancy on the first is float32 storage precision, not a
different formula.

This is the arithmetic Phase 5 needs: to place a parameter at a known
value, invert it as `macro = (value - Min) / (Max - Min) * 127`.

Note the consequence for the earlier S3 finding: Drive at `0` in a
`-36..36` range is mid-range, so mapping it produced macro `63.5`, i.e.
Live wrote the *fractional* macro position rather than rounding to an
integer CC value. Macro values are continuous, not 0-127 integers.

### Incidental: `MacroDefaults.N`

`-1` is the "unset" sentinel. All 16 were `-1` in `s3_b`. After this edit:

| slot | before | after |
|---|---|---|
| `MacroDefaults.0` | `-1` | `63.5` |
| `MacroDefaults.1` | `-1` | **`-1`, unchanged** |
| `MacroDefaults.2-15` | `-1` | `0` |

`MacroDefaults.0` captured `63.5`, which is exactly the value Macro 1 held
before it was moved to 69 - so a default appears to be recorded at some
point after mapping.

**[?] `MacroDefaults.1` staying `-1` while every other slot materialised
is unexplained.** Macro 2 was mapped and moved in this same step, so
whatever writes defaults did not fire for it. Do not model macro defaults
until S10 isolates the trigger with a single-change diff.

## S4. Macro to macro mapping - ANSWERED (no separate spike)

No structural difference from S3. An inner rack's macro is an ordinary
parameter node, so it takes a `KeyMidi` child like any other parameter.

Found already present in `racks/s1_source.adg` via `patchbay mappings`,
chaining three levels:

```
Macro 1  ->  MacroControls.0   [DrumGroupDevice,       depth 1]
Macro 1  ->  MacroControls.0   [InstrumentGroupDevice, depth 2]
Macro 1  ->  ChainSelector     [InstrumentGroupDevice, depth 2]
```

`Channel` is 16 at every depth, so **nesting depth is not encoded in the
mapping**. Which rack owns a macro is resolved structurally - see
`ARCHITECTURE.md` §3 for the walk, which is not the obvious one.

`ChainSelector` is an ordinary parameter and mappable identically. This is
the DR1 three-level pattern from `PATCHBAYGROUND.md`, confirmed working in
a real file rather than assumed.

## S5. Chain select zone - PARTIAL

`racks/s5_a.adg` / `racks/s5_b.adg`. Audio Effect Rack, two chains.
Chain 2's chain-select zone dragged from position 0 to 8.

**The zone lives on the chain, not on the rack device.** One node, four
fields, all absolute on the `ChainSelector`'s 0..127 scale:

```xml
<AudioEffectBranchPreset Id="1">
  <BranchSelectorRange>
    <Min Value="8" />
    <Max Value="8" />
    <CrossfadeMin Value="8" />
    <CrossfadeMax Value="8" />
  </BranchSelectorRange>
```

Diff was exactly four facts, all on `AudioEffectBranchPreset[1]`:

```
BranchSelectorRange/Min@Value           0 -> 8
BranchSelectorRange/Max@Value           0 -> 8
BranchSelectorRange/CrossfadeMin@Value  0 -> 8
BranchSelectorRange/CrossfadeMax@Value  0 -> 8
```

Established:

- Zones are stored as **bounds (`Min`/`Max`), not start+length**.
- Units are **raw positions on the chain selector's own scale**, whose
  `MidiControllerRange` is `0..127`. Not normalised.
- Fade is **two values**, not one, and they are absolute positions rather
  than widths - moving a zero-width zone moved all four together.
- Untouched chains are untouched: `AudioEffectBranchPreset[0]` kept
  `0/0/0/0`. Zones are per chain and independent.
- The rack's `ChainSelector` is an ordinary parameter (`Manual`,
  `MidiControllerRange` `0..127`) and is macro-mappable - see S3.

### Width drag - `racks/s5_len_a.adg` / `racks/s5_len_b.adg`

Chain 2's zone right edge dragged from 16 to 40. Exactly two facts moved:

```
BranchSelectorRange/Max@Value           16 -> 40
BranchSelectorRange/CrossfadeMax@Value  16 -> 40
```

| file | chain | Min | Max | CrossfadeMin | CrossfadeMax |
|---|---|---|---|---|---|
| `s5_len_a` | 1 | 8 | 16 | 8 | 16 |
| `s5_len_b` | 1 | 8 | 40 | 8 | 40 |

**[V]** `CrossfadeMin` / `CrossfadeMax` are **absolute positions on the
same 0..127 scale**, not widths or offsets. Zero fade is encoded as
`Crossfade == bound`, and Live drags the crossfade bound along with the
zone bound to preserve it.

**[V]** `Min` was untouched, confirming the four fields are independently
addressable and an edge drag is a two-field edit.

**[?] Still open**, needs the fade pair:

1. Is `Max` inclusive or exclusive? A width drag alone cannot show this.
2. Which direction does a fade grow - does dragging the handle inward make
   `CrossfadeMin > Min`, or does the fade extend outward past the bound?
   `Crossfade == bound` means no fade, but the sign is unknown.

Key and velocity zones are untested. They are Instrument Rack only and
are presumably siblings of this structure; do not assume it.

## S6. Id allocation and scope - ANSWERED

**An `Id` must be unique among its siblings. Nothing else about it
matters.**

### Static evidence

Across `s9_b`, `s1_source`, `s8_c` and `s7_b`: **2347 of 2359** elements
carrying an `Id` attribute have `Id` equal to their index among same-tag
siblings. `Id` is a sequence number assigned on insert.

The 12 exceptions are gaps, not errors - `s1_source.adg` has
`AbletonDevicePreset Id="2"` sitting at index 1, left behind when a device
was deleted. Live opens that file fine, so **ids are not compacted and
gaps are legal**.

`s9_b.adg` has 555 `Id` occurrences with **3 distinct values**; 548 of them
are `0`. Ids are emphatically **not** file-unique.

Adding a device (`s9_a` -> `s9_b`) introduced 76 new `Id` facts and changed
**zero** existing ones.

### Deliberate-failure test

Three files built and loaded in Live 12.4.3:

| file | change | result |
|---|---|---|
| `build/s6_collide.adg` | both pads `Id=0` **and** all devices `Id=7` | **"the preset cannot be loaded"** |
| `build/s6_dup_pads_only.adg` | both pads `Id=0`, devices untouched | **refuses to load** |
| `build/s6_high_id_only.adg` | all devices `Id=7`, no duplicates | **loads fine** |

The first test changed two things at once and had to be re-run split -
the one-change rule applies to constructed files as much as to Live saves.

**Conclusions:**

- **Duplicate `Id` among siblings -> Live rejects the entire preset**, with
  a dialog. Loud failure, not silent corruption. This is the good outcome:
  `CLAUDE.md`'s "Live will either silently cross-wire the mappings or
  refuse to load" resolves to *refuse*.
- **Value is arbitrary otherwise.** Not contiguous, not matching index, not
  file-unique. `Id="7"` on every device loads happily.
- **Nothing references these ids.** No `PointeeId` in any preset carries a
  non-zero value pointing anywhere. Combined with S3, the format uses
  containment rather than reference throughout.

### Consequence for Phase 2

Landmine #1 in `CLAUDE.md` survives, but in a far narrower and cheaper form
than written. Cloning a branch does **not** require remapping a web of
cross-references - macro mappings carry no ids at all (S3). It requires
exactly one thing: **give the new branch an `Id` unused by its siblings.**

`patchbay.ids.next_free_id(parent, tag)` does that. `patchbay ids` now reports
sibling collisions directly and its verdict matches Live's behaviour on all
three test files.

## S13. Where a GroupDevicePreset sits, and its `Id` - ANSWERED

**A top-level `GroupDevicePreset` carries no attributes. A nested one
carries an `Id`. Getting that backwards is what made Live refuse a lifted
out nested rack as a drop, without ever loading it.**

This answers Q1b, which had been open with everything checkable looking
correct.

### Isolating it

The earlier investigation compared a broken file against a working one and
found nothing, because the two files also differed in what they contained.
The experiment that worked builds the **same rack twice**, changing only
which `GroupDevicePreset` is harvested as the skeleton - top level from
`racks/s7_a.adg`, nested from `racks/s1_source.adg` at depth 2. Everything
else is identical by construction.

Three facts came back:

```
CHANGED (2)
  .../InstrumentBranchPreset[0]/DocumentColorIndex@Value   26  ->  1
  .../InstrumentGroupDevice/AreMacroControlsVisible@Value  true  ->  false

REMOVED (1)
  GroupDevicePreset@Id = 0
```

Two are cosmetic. The third is the finding.

### Static evidence

All **26** `.adg` files in `racks/`, every one saved by Live, have a
top-level `GroupDevicePreset` whose attribute dict is **empty**. Both
nested racks in `racks/s1_source.adg` carry an `Id`, `0` and `1`.

Asserted by `test_live_saved_racks_agree_on_that`.

### Deliberate-failure test

Two files, one change apart, both dragged into Live 12.4.3:

| file | change | result |
|---|---|---|
| `build/probe_b_toplevel.adg` | none, the control | **loads** |
| `build/probe_c_id_added.adg` | `Id="0"` on the top-level preset | **refused as a drop** |

The refusal happens at the drop, not at load: there is no dialog, because
Live never gets as far as parsing the preset.

### What it is not

`PresetRef` was the standing suspect and is **dead**. A never-saved rack
carries an `AbletonDefaultPresetRef` with `RelativePathType=0` and empty
`Path` and `RelativePath`, and both `racks/s7_a.adg` and `build/PD1.adg`
are that shape and load. The `DeviceId` child was already known to be
correct in the refused files.

### Consequence

The `Id` rule from S6 is unchanged - unique among siblings - and this is
its boundary case. At the top level a `GroupDevicePreset` has no siblings
at all, so it must carry no `Id` rather than a unique one.

`Rack._load_skeleton` strips the `Id` when a nested rack is used as a
skeleton, and `Rack._nested_preset` sets one when a rack is written into a
chain. `build/VA1.adg`, two levels deep and built entirely by patchbay,
loads and its macro-to-macro mappings drive.

## S12. Minimal device viability - ANSWERED

Four copies of the `s3b` Saturator rack with parameter nodes deleted, all
loaded in Live 12.4.3:

| file | parameters dropped | result |
|---|---|---|
| `build/s12_one.adg` | 1 of 18 | loads, sounds correct |
| `build/s12_five.adg` | 5 of 18 | loads, sounds correct |
| `build/s12_half.adg` | 9 of 18 | loads, sounds correct |
| `build/s12_all.adg` | **18 of 18** | loads, sounds correct |

**[V] A device loads with every one of its parameter nodes removed.** Live
fills defaults for whatever is absent. There is no threshold and no
required subset.

### What this changes, and what it does not

The donor pattern is **not** required for loadability. It is still required
for **fidelity**: absent parameters come back as defaults, so a donor is
how a device arrives with the right values. That is the whole point of
`donors/` - carrying a *configured* device, not a loadable one.

So the KICKOFF rationale stands, with the reason corrected: donors save us
from having to know every parameter's default and name, not from producing
unloadable files.

Practical upshot for Phase 4: a generator may write **partial** device
nodes, overriding only the parameters it cares about and letting Live
default the rest. That is a much smaller surface than emitting a complete
Saturator.

### Deleting a parameter deletes its mapping

**[V]** Every variant dropped `PreDrive` (first parameter in document
order), which was Macro 1's target. All four loaded with **Macro 1
unmapped** - because a mapping *is* a `KeyMidi` element inside the target
parameter (S3). Remove the parameter, remove the mapping.

**[V]** Macro 2 -> `PostDrive` survived in `s12_one` and `s12_five`, and
**still drives Output correctly** after its sibling parameters were
deleted. Mappings are robust to structural edits around them.

This is a clean confirmation of the containment model from an angle S3
could not reach, and it is reassuring for Phase 2: editing a chain cannot
corrupt a mapping it does not touch.

## S7. FileRef / sample reference - PARTIAL, failure test outstanding

`racks/s7_a.adg` / `racks/s7_b.adg`. Instrument Rack + Simpler, one sample
swapped for another. **16 facts moved and 4 were removed.** Rewriting the
path alone touches 2 of 20.

### There are TWO FileRefs per sample

```
MultiSamplePart/SampleRef/FileRef                        <- the live reference
MultiSamplePart/SampleRef/SourceContext/SourceContext/
                          OriginalFileRef/FileRef        <- provenance
```

Both moved. The second records where the sample *came from* - in `s7_a` it
still pointed at `C:/Music/AlienMindLibrary/CIRCUIT TRACKS/BACKUP/...`,
the pre-import location, while the live ref already pointed into the User
Library.

**[V]** `RelativePathType` differs per ref and per location: `6` for a file
inside the User Library, `1` for the imported-from original, whose
`RelativePath` was `../../../../../CIRCUIT TRACKS/BACKUP/07_EBM/PCM/...` -
i.e. type 1 permits escaping upward with `..`.

**[V]** `FileRef@Id` changed `1 -> 0` on the OriginalFileRef. First
non-zero id observed anywhere in a preset. Relevant to S6.

### Fields that move inside FileRef

| field | example | derivation |
|---|---|---|
| `Path` | absolute path, forward slashes even on Windows | the file |
| `RelativePath` | `Samples/Imported/00_TECH KICK 1.wav` | relative to User Library |
| `RelativePathType` | `6` User Library, `1` escaping relative | the location |
| `OriginalFileSize` | `24044` | **[V]** exact on-disk byte count |
| `OriginalCrc` | `63283` | **[?]** 16-bit checksum, algorithm unidentified |

### Fields that move OUTSIDE FileRef

This is the part that makes path-only rewriting insufficient:

| node | s7_a | s7_b | derivation |
|---|---|---|---|
| `MultiSamplePart/Name` | `00_EBM Kick1` | `00_TECH KICK 1` | filename without extension |
| `SampleRef/DefaultDuration` | `13432` | `12000` | **[V]** frame count |
| `MultiSamplePart/SampleEnd` | `13431` | `11999` | **[V]** frames - 1 |
| `SustainLoop/End` | `13431` | `11999` | frames - 1 |
| `ReleaseLoop/End` | `13431` | `11999` | frames - 1 |
| `SourceContext/BrowserContentPath` | `query:Everything#FileId_202149` | `query:UserLibrary#Samples:Imported:00_TECH%20KICK%201.wav` | browser URI, URL-encoded |
| `InitialSlicePointsFromOnsets/SlicePoint` | present | **removed** | transient analysis |

### Derived values verified against the files on disk

Both samples are 48 kHz, 1 channel, 16-bit WAV:

| | on-disk bytes | `OriginalFileSize` | frames | `DefaultDuration` |
|---|---|---|---|---|
| `00_EBM Kick1.wav` | 26908 | 26908 | 13432 | 13432 |
| `00_TECH KICK 1.wav` | 24044 | 24044 | 12000 | 12000 |

`frames = (filesize - 44) / (channels * bits/8)`, i.e. a plain WAV header
plus PCM. So `OriginalFileSize`, `DefaultDuration` and `SampleEnd` are all
computable by `patchbay` from the target file without Live.

### `OriginalCrc` - not yet reproducible

**[?]** 16-bit (both values < 65536). Ruled out by brute force: zlib
`crc32` and `adler32` masked to 16 bits, and CRC-16 CCITT-FALSE, XMODEM,
KERMIT, MODBUS, ARC/IBM, MAXIM, USB, DNP, GENIBUS, MCRF4XX - each over the
whole file, the PCM body, the first 1 KB and the first 16 KB. No match.

Whether this blocks Phase 3 depends entirely on whether Live *checks* it.
That is what the failure test below is for.

### Failure test - DONE. All six combinations load

Six variants built from `racks/s7_b.adg`, each retargeting to
`00_EBM Kick1.wav`, isolating one field group. All loaded in Live 12.4.3:

| file | paths | size + crc | duration + ends | result |
|---|---|---|---|---|
| `s7_test_A` | correct | stale | stale | **works** |
| `s7_test_B` | correct | **correct** | **stale** | **FAILS** |
| `s7_test_C` | correct | correct | correct | works |
| `s7_test_D` | correct | zeroed | stale | works |
| `s7_test_E` | correct | stale | correct | works |
| `s7_test_F` | correct | zeroed | correct | works |

**Every combination works, including B on re-test.**

B initially appeared to fail. Live's log showed exactly one
`AApplication: CommandLine` entry for the whole day, and it was B:

```
2026-07-26T11:32:09: info: AApplication: CommandLine : "...\build\s7_test_B.adg"
2026-07-26T11:32:28: info: Message Box: Another instance of the same Live
                            version is running.
```

B had been **double-clicked**, which launches a second Live instance rather
than loading into the running one. The symptom - several seconds of
unresponsive UI, then nothing loaded, no error dialog - was an instance
collision. The other five were dragged in. No sample-loading error, and no
`missing`, `offline` or `could not` line, appears anywhere in the log.

Dragged into the running instance, **B loads correctly**.

### Conclusion: the derived metadata is advisory

**[V]** There is no failing combination. Live **re-reads the sample file**
and recomputes `DefaultDuration`, `SampleEnd` and the loop ends regardless
of what the preset claims. `OriginalFileSize` and `OriginalCrc` are not
validated on load.

**[V]** So a path-only rewrite is sufficient to retarget a sample. The 18
other facts a real swap moves are Live keeping its own bookkeeping tidy,
not requirements.

**Retracted:** an earlier revision of this document read B's apparent
failure as proof that `OriginalFileSize` + `OriginalCrc` form a
cache-validity key, with B breaking because a *correct* key made Live trust
*stale* derived values. The model was elegant, fit all six data points, and
was wrong - it rested entirely on the one contaminated point. Recorded here
rather than deleted, because the failure mode is instructive: a single
surprising result that confirms a tidy theory deserves more suspicion than
a boring one.

### The CRC is irrelevant

`samples.py` never needs to compute the CRC, because nothing reads it on
load. Write `0`, or leave the donor's value stale - both work.

Recommended write strategy, matching `s7_test_F`:

| step | field | required? |
|---|---|---|
| 1 | `Path`, `RelativePath` on **both** FileRefs | **yes** |
| 2 | `RelativePathType` -> `6` inside the User Library | **yes** |
| 3 | `MultiSamplePart/Name` -> filename without extension | cosmetic |
| 4 | `DefaultDuration` = frames, `SampleEnd` and loop `End`s = frames - 1 | no |
| 5 | `OriginalFileSize`, `OriginalCrc` -> `0` | no |

Only steps 1 and 2 are load-bearing. Steps 3 to 5 are hygiene: they keep a
generated preset indistinguishable from one Live saved, which keeps future
diffs clean. Since the frame arithmetic is verified and cheap, do them -
but a bug there cannot break a preset.

### Method note, learned the hard way

Load tests must **drag the file into the running Live instance**.
Double-clicking an `.adg` launches a second Live and produces a hang that
looks exactly like a rejected file. Live's log at
`%APPDATA%/Ableton/Live <version>/Preferences/Log.txt` distinguishes the
two: grep for `CommandLine` and `Another instance`.

**[?]** Whether Live rewrites the zeroed key on its next save is untested.
Expected yes, since it re-reads the file. Harmless either way.

## S8. Macro variations - ANSWERED

`racks/s8_a.adg` (no variations) -> `s8_b` (one) -> `s8_c` (two).
Audio Effect Rack, Saturator, macros 1 and 2 mapped.

A variation is a `MacroSnapshot` in a positional list on the rack device:

```xml
<MacroVariations>
  <MacroSnapshots>
    <MacroSnapshot Id="0">
      <AutogeneratedNameIndex Value="1" />
      <SnapshotName Value="Variation 1" />
      <MacroValues.0 Value="69" />       <!-- x16, then -->
      <MacroValues.1 Value="127" />
      <MacroValues.2 Value="-1" />
      <MacroHasValue.0 Value="true" />   <!-- x16 -->
      <MacroHasValue.1 Value="true" />
      <MacroHasValue.2 Value="false" />
    </MacroSnapshot>
  </MacroSnapshots>
</MacroVariations>
```

### Values are absolute, on the macro 0..127 scale

**[V]** Proven without needing chosen values: `s8_b`'s Variation 1 holds
`69, 127`, which is exactly that same file's live
`MacroControls.0/Manual` and `MacroControls.1/Manual`. Identical units,
identical scale - **not normalised 0..1**.

So a variation stores macro positions, and §5's transfer function converts
them to parameter values. Phase 5 works entirely in macro space.

### Sparse in meaning, dense in XML

**[V]** All 16 slots are always written, in both families. Participation is
carried by `MacroHasValue.N`:

| macro | mapped? | `MacroHasValue.N` | `MacroValues.N` |
|---|---|---|---|
| 0, 1 | yes | `true` | `69`, `127` |
| 2-15 | no | `false` | `-1` |

`-1` is the unset sentinel again, as with `MacroDefaults.N` in S3b.

**[V]** Only *mapped* macros were flagged `true`. Whether an unmapped
macro can be included is untested, but the flag exists to express exactly
that, so a generator should set both fields rather than relying on `-1`
alone.

### Naming and ordering

**[V]** Two fields, both written:

- `SnapshotName` - the display name, defaulting to `"Variation N"`
- `AutogeneratedNameIndex` - the `N` used to build that default, `1` then `2`

`Id` runs `0`, `1`, matching list position. Order is positional.

**[V]** Element order inside a `MacroSnapshot` is `AutogeneratedNameIndex`,
`SnapshotName`, all 16 `MacroValues.N`, then all 16 `MacroHasValue.N`. The
two families are not interleaved, and the name index precedes the name. An
earlier version of this entry had both pairs the other way round, from
reading rather than dumping the element; `racks/s8_c.adg` is the authority.
Whether Live cares about the order is untested, so `variations.py` matches
it.

**[V]** Confirmed by rewriting: clearing every `MacroSnapshot` in
`racks/s8_c.adg` and writing them back through `variations.write` produces a
file that diffs against the original at **zero facts**, with `--all`. Our
writer and Live's agree on order, sentinel and scale. Asserted in
`test_rewriting_variations_matches_live_fact_for_fact`.

Since `SnapshotName` is free text, Phase 5 can encode a variation's
parameter values into its name, which is what makes culling informed
rather than blind - see the workflow note in `KICKOFF.md`.

### A snapshot captures macro state at the click, then drifts

**[V]** In `s8_c`, Variation 2 holds `16, 39` while the file's live macros
are `94, 2`. The user clicked New, then moved the macros again before
saving. A snapshot is a copy taken at the instant New is pressed; it does
not track the live macros afterwards.

Harmless for generation - `variations.py` writes snapshots directly - but
it means a rack's current macro values tell you nothing about its
variations.

### Consequence for Phase 5

Writing a variation set is: append N `MacroSnapshot` elements, each with 16
`MacroHasValue` and 16 `MacroValues`, sequential `Id`, a name. No ids to
reconcile, no references to fix, no interaction with mappings.

### The two tails, closed in Live

Both were dragged into Live 12.4.3, from `build/probe_variations.py`.

**No ceiling at 256.** `build/probe_q4_256.adg` holds 256 snapshots and
differs from `build/PD1.adg` only in count. Live loads it and lists all 256.
Nothing truncated, nothing refused. The template wants ~38 per rack, so the
grid needs no chunking and the exact limit is not worth measuring.

**An unmapped macro may be flagged, and it does nothing.**
`build/probe_q5_unmapped.adg` is PD1's 96 plus one entry flagging macro 6,
which nothing is mapped to. Live loads the file and the entry appears in the
panel, so `MacroHasValue.N = true` on an unmapped macro is not a load error.
Recalling it leaves macro 6 where it was.

Accepted and inert, which is the worse of the two answers to design for: the
entry reads as live and is not. `Rack._write_variations` therefore refuses to
write one, and the reason in the message is now this finding rather than
"untested".

Untested tail, cheap if wanted: whether Live *keeps* the flag or strips it on
load. Save the probe back out of Live and diff `MacroHasValue.5`.

### Phase 5 gate: PASSED

`build/PD1.adg`, 96 variations over engine, cutoff, decay and resonance,
compiled from `examples/patchbayground.py`. All 96 appear, named. Recalling one
moves the four bound macros and leaves macros 5-13 alone. Recalling entry
`000` selects FM and `095` selects Sample, so a variation drives the chain
selector like any other parameter.

The sound family claim was checked by hand: recall a Sample-engine variation,
then turn Engine full left, and the same musical idea arrives through FM with
no knob re-set. That is the constraint holding structurally, since the
variation names slots and each engine binds its own parameters to them.

The sound-family constraint from `PATCHBAYGROUND.md` - variation index N
means the same musical idea across every engine - is satisfiable because
snapshots are positional and per rack: emit the same index across each
rack's list, with values chosen per engine.

## S9. Drum rack specifics

## S9. Drum rack specifics - ANSWERED

`racks/s9_a.adg` (2 pads) -> `s9_b` (return chain added) -> `s9_c` (one
send raised) -> `s9_d` (one pad moved to another slot).

### Pad to note

`DrumBranchPreset/ZoneSettings`:

```xml
<ZoneSettings>
  <ReceivingNote Value="92" />
  <SendingNote Value="60" />
  <ChokeGroup Value="0" />
</ZoneSettings>
```

**[V]** Moving a pad to a different grid slot changes **exactly one fact**,
`ReceivingNote` (`91 -> 90`). `SendingNote` stayed at `60`.

- `ReceivingNote` - the MIDI note that triggers this pad. This is the pad's
  grid position.
- `SendingNote` - the note handed to the chain's instrument, `60` (C3) on
  every pad. That is why each pad's sampler plays at its root pitch
  wherever it sits.
- `ChokeGroup` - `0` for none.

### Return chains live in a sibling of BranchPresets

**[V]** The preset-format container is `ReturnBranchPresets`, a direct
child of `GroupDevicePreset`:

```
GroupDevicePreset
├─ Device/DrumGroupDevice          the rack itself
├─ BranchPresets/DrumBranchPreset[i]        the pads
└─ ReturnBranchPresets/AudioEffectBranchPreset[i]   the returns
```

**[V]** A return branch is an **`AudioEffectBranchPreset`** - the same tag
an audio effect rack uses for its chains - regardless of the parent being a
drum rack. It has the same children as any branch: `Name`, `DevicePresets`,
`MixerPreset`, `BranchSelectorRange`, colours.

**[V]** Do not confuse this with `ReturnBranches` on the *device* node,
which is empty in presets exactly like `Branches`. Same trap as §3.

### Sends

**[V]** Each chain's mixer carries a `SendInfos` list, one entry per return:

```xml
<SendInfos>
  <AudioBranchSendInfo Id="0">
    <Send>
      <Manual Value="0.3388441503" />
      <MidiControllerRange>
        <Min Value="0.0003162277571" />
        <Max Value="1" />
      </MidiControllerRange>
    </Send>
    <EnabledByUser Value="true" />
    <Index Value="0" />
  </AudioBranchSendInfo>
</SendInfos>
```

At `MixerPreset/AbletonDevicePreset/Device/AudioBranchMixerDevice/SendInfos`.

**[V]** `Index` selects the return **positionally** - `0` is the first
entry in `ReturnBranchPresets`. No id reference.

**[V]** Adding a return chain seeds an `AudioBranchSendInfo` on **every**
existing chain at once, all at the floor value. So send count per chain
tracks return count, and a generator adding a return must add the matching
send entry to every chain.

**[V]** Send level is **linear amplitude**, not dB and not 0..127 - a third
scale, distinct from macros (§5) and zones (§7):

| | value | meaning |
|---|---|---|
| `Min` | `0.0003162277571` | `10^(-70/20)`, i.e. -70 dB, Live's silent floor |
| `Max` | `1` | 0 dB |
| observed | `0.3388441503` | about -9.4 dB |

**[?]** The knob taper is not pinned down: the observed value came from an
arbitrary knob position, so whether the control is linear in amplitude or
in dB is unknown. Only matters if a spec ever states send levels as
percentages of knob travel rather than as dB or amplitude.

### Incidental

**[V]** `AreSendsVisible` on the rack device gates the send column in the
chain list. It is `false` by default, which makes per-pad sends invisible
in the UI until toggled - this cost real time during the spike.

**[V]** Adding a return flipped pad 0's mixer
`RoutingHelper/Routable/UpperDisplayString` from `No Output` to
`Sends Only`. Recorded as an observation; routing is S11's subject.

## S10. Macro metadata - ANSWERED except mapping range

Chain of saves from `racks/s3b.adg`, one change each:
`s10_c` -> `s10_d` -> `s10_e` -> `s10_f` -> `s10_g`.

(`s10_a.adv` / `s10_b.adv` are Saturator *device* presets, saved from the
device's own save button rather than the rack's, so they carry no macro
data. `s3b.adg` served as the pre-rename baseline instead.)

### One field per menu item

Live's right-click menu on a macro knob maps cleanly onto the `.N` families:

| menu item | field | diff |
|---|---|---|
| *Rename* | `MacroDisplayNames.0` | `"Macro 1"` -> `"Grit"` |
| *Exclude Macro from Randomization* | `ExcludeMacroFromRandomization.0` | `false` -> `true` |
| *Exclude Macro From Variations* | `ExcludeMacroFromSnapshots.0` | `false` -> `true` |
| *Show Generic 0-127 Value* | `ForceDisplayGenericValue.0` | `false` -> `true` |
| *Return to Default* | `MacroDefaults.0` | see below |
| - (macro panel control) | `NumVisibleMacroControls` | `8` -> `16` |

**[V]** Note the vocabulary split: the UI says **Variations**, the XML says
**Snapshots** (`ExcludeMacroFromSnapshots`), matching
`MacroVariations`/`MacroSnapshots` from S8. Grepping for the UI word finds
nothing.

**[V]** Changing the visible macro count from 8 to 16 changed **exactly one
fact** and added no elements. All 16 slots exist in every family
regardless. A generator always writes 16 and sets the count.

**[V]** The menu offers no macro range item, and mapping ranges were not
reachable from the macro knob, the target parameter, or the Map button.
See the open question below.

### Mapping macro 3 confirmed the index rule a third time

`s10_g` mapped Macro 3 to Saturator's Dry/Wet:

```
Saturator/DryWet/KeyMidi/NoteOrController@Value = 2
Saturator/DryWet/KeyMidi/Channel@Value          = 16
```

Zero-based macro index, fixed channel. Consistent with S3 and S3b.

### `MacroDefaults.N` - the S3b anomaly, mostly resolved

**[V]** Observed across the chain:

```
s3b:     MacroControls.0=69   .1=127        MacroDefaults.0=63.5  .1=-1
s10_c:   MacroControls.0=57                 MacroDefaults.0=69    .1=127
s10_f:   MacroControls.2=0                  MacroDefaults.2=0
s10_g:   MacroControls.2=127  (just mapped) MacroDefaults.2=-1
```

**[I]** Two behaviours, together explaining S3b:

1. **`MacroDefaults` lags one save.** `s10_c`'s defaults are exactly
   `s3b`'s *macro values*. This is the third field with a one-save lag,
   after `PresetRef` (S3) and `UserName` (S5) - evidently Live serialises
   some bookkeeping from the pre-save state.
2. **Mapping a macro resets its default to `-1`.** `s10_g` shows
   `MacroDefaults.2` going `0 -> -1` at the moment Macro 3 was mapped,
   rather than trailing the previous value. This is why S3b saw
   `MacroDefaults.1` stay at `-1` while its siblings materialised.

**Actionable rule regardless of which behaviour dominates: write `-1`
(unset) and do not depend on this field.** It drives the *Return to
Default* menu item only, has no effect on sound, and Live rewrites it on
the next save anyway.

### Mapping ranges

**Answered - see below.** Live 12.4.3's macro right-click menu contains no
range editor, and none was found on the target parameter or via Map mode.
The full menu is:
Show Automation, Show Automation In New Lane, Show Modulation Source,
Return to Default, Edit MIDI Map, Edit Key Map, Copy Max for Live Path,
Copy Parameter Name, Remove Mapping, Show Generic 0-127 Value, Rename,
Edit Info Text, Exclude Macro from Randomization, Exclude Macro From
Variations, colour palette.

### Resolved by reverse test - ranges ARE `MidiControllerRange`

`build/s10_range_test.adg` is `s3b` with
`Saturator/PreDrive/MidiControllerRange/Max` changed from `36` to `12`.
Loaded in Live, **Macro 1 at full drives Drive to exactly +12 dB.**

**[V]** `MidiControllerRange` on the target parameter is the macro mapping
range. Narrowing it narrows what the macro can reach.

This is the useful direction: mapping ranges are **writable from XML with
no UI involved**, which matters because Live 12.4.3 exposes no range
editor at all. A generator has a capability the GUI does not.

For the macro grammar in `PATCHBAYGROUND.md` this means a macro can be
scoped to a musically sensible slice of a parameter - e.g. filter cutoff
over 200 Hz..8 kHz rather than the full sweep - per mapping, per engine.

### Incidental

The `s3b -> s10_c` diff carried extra drift - `IsExpanded`,
`DocumentColorIndex`, `PreDrive/Manual`, `MacroControls.0` - because that
step bundled a rename with the randomisation toggle and some knob
movement. The two fields of interest were still unambiguous, but it is a
reminder that the one-change discipline is what keeps these diffs to a
single line, as `s10_c` through `s10_f` each demonstrate.

## S11. .als track structure

TBD - routing, sidechain source, return tracks.


