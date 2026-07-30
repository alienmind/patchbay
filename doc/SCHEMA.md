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
chain. `build/VA1.adg`, two levels deep and built entirely by PatchBay,
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

Re-checked on `build/PD1.adg`, Macro 3 (Resonance), Live 12.4.3: the menu
offers `Show Generic 0-127 Values` and no range editor, and the entry
carries the note

    This macro will continue to show generic 0-127 values because of its
    mappings

So Live declines to show a macro in a parameter's units at all once the
macro reaches more than one target, which every slot in `PATCHBAYGROUND.md`
does by design. A knob's meaning lives in its NAME here, not in a unit
Live will not print. The S10 tail is closed.

### Resolved by reverse test - ranges ARE `MidiControllerRange`

`build/s10_range_test.adg` is `s3b` with
`Saturator/PreDrive/MidiControllerRange/Max` changed from `36` to `12`.
Loaded in Live, **Macro 1 at full drives Drive to exactly +12 dB.**

**[V]** `MidiControllerRange` on the target parameter is the macro mapping
range. Narrowing it narrows what the macro can reach.

This is the useful direction: mapping ranges are **writable from XML with
no UI involved**, which matters because Live 12.4.3 exposes no range
editor at all. A generator has a capability the GUI does not.

For the macro layout in `PATCHBAYGROUND.md` this means a macro can be
scoped per mapping, per engine. What that scoping is FOR is settled by
Q15: not to concentrate a knob's travel, which the parameter's own taper
already handles, but to make one knob position mean the same thing on
engines whose native ranges differ.

### Incidental

The `s3b -> s10_c` diff carried extra drift - `IsExpanded`,
`DocumentColorIndex`, `PreDrive/Manual`, `MacroControls.0` - because that
step bundled a rename with the randomisation toggle and some knob
movement. The two fields of interest were still unambiguous, but it is a
reminder that the one-change discipline is what keeps these diffs to a
single line, as `s10_c` through `s10_f` each demonstrate.

## Q10. Meld filter resonance - ANSWERED

`donors/Meld Rack.adg` -> `donors/spikes/q10_a.adg`. One change: Engine A filter
**Q** set to `8.0` in the UI, nothing else touched.

The diff is one fact:

    .../Device/InstrumentMeld/MeldVoice_EngineA_Filter_Macro1/Manual@Value
    '0' -> '0.07999999821'

**[V]** Meld's filter resonance is `MeldVoice_EngineA_Filter_Macro1`.
`Macro2` is the L-B-H-N morph, by elimination.

### Why this needed a spike at all

Meld exposes its filter as `FilterType`, `Frequency`, `Macro1`, `Macro2`.
Nothing in the parameter list contains "res" or "q", so
`Device.search("filter", "res")` returns NOTHING and the tempting
conclusion is that Meld has no resonance. It has one. The GUI labels the
two knobs **Q** and **L-B-H-N**; the XML does not.

This is `CLAUDE.md` rule 1 in its least obvious form. The usual failure is
inventing a name that does not exist. Here the failure is concluding a
parameter does not exist because the name search missed it. A search
returning nothing is not evidence of absence, it is evidence that the GUI
word is not the element word.

**`Macro1` and `Macro2` are positional, not semantic.** They are whichever
two knobs the selected `FilterType` offers. The binding above is verified
for `FilterType = 0` (SVF 12dB) and is not guaranteed to hold for another
filter type. A rack that changes filter type may silently re-point its
resonance macro at something else.

`library.Device.range_of` puts `FilterType` at 0..16, so there are
**17 filter types** and 17 possible meanings for each of the two knobs.
Only type 0 has been measured. Binding resonance and then changing filter
type is a silent-wrong change, not an error: the mapping stays valid and
starts moving a different control.

### Scale

UI `8.0` stored as `0.07999999821`. See Q11/Q12 below for what that does
and does not generalise to.

## Q11/Q12. Displayed units are not stored units - ANSWERED

Two one-change diffs, run to find out whether Q10's normalised Q was a
Meld quirk or a general rule. It is neither, and the answer is more useful
than either.

| spike | files | change | stored |
|---|---|---|---|
| Q11 | `donors/Wavetable Rack.adg` -> `donors/spikes/q11_a.adg` | Filter 1 Res to UI `40` | `0.400000006` |
| Q12 | `donors/Drift Rack.adg` -> `donors/spikes/q12_a.adg` | Filter Res to UI `1.01` | `1.00999999` |

Both diffs are one real field plus the 16 `MacroDefaults` fields Live
rewrites on every save.

### The finding

| device | parameter | UI range | stored for UI value | relationship |
|---|---|---|---|---|
| Meld | `MeldVoice_EngineA_Filter_Macro1` | 0..100 | `0.08` for `8.0` | UI/100 |
| Wavetable | `Voice_Filter1_Resonance` | 0..100 | `0.4` for `40` | UI/100 |
| Drift | `Filter_Resonance` | 0..1.01 | `1.01` for `1.01` | 1:1 |

**[V]** Three resonance controls, two different relationships between what
the GUI shows and what the file stores. There is no rule that converts one
to the other.

Drift's UI range is 0..1.01, which is why typing `40` into it produces
`1.01`: the field clamps. That clamping is the tell. A parameter whose UI
maxes at a number unlike 100 is displaying something close to its stored
range; one showing 0..100 may well be displaying a percentage of a 0..1
stored range.

### What this corrects

Q10 above originally called Meld's normalised Q "a fourth scale" alongside
the three in `ARCHITECTURE.md` section 12. That was wrong, and the
correction matters more than the original claim.

Section 12 already says device parameters are in **native units over their
own range**. Nothing there promises native units equal displayed units.
Meld and Wavetable are not a new scale; they are devices whose native
range is 0..1 while their GUI presents 0..100. Drift is a device whose
native range is what the GUI shows. All three are section 12 behaving as
written.

The trap is not a missing scale. It is assuming DISPLAY equals NATIVE.

### Q13. Envelope times

Read off the three donors with no save, since the default values differ
enough to be diagnostic on their own.

| device | parameter | stored | displayed |
|---|---|---|---|
| Wavetable | `Voice_Modulators_AmpEnvelope_Times_Decay` | `0.5999999642` | `600 ms` |
| Wavetable | `Voice_Modulators_AmpEnvelope_Times_Attack` | `0.001000000164` | `1.00 ms` |
| Drift | `Envelope1_Decay` | `0.6000000238` | `600 ms` |
| Meld | `MeldVoice_EngineA_AmpEnvelope_Times_Decay` | `0.6000000238` | `600 ms` |

**[V]** Envelope times are stored in SECONDS and displayed in
MILLISECONDS. A third relationship: not 1:1, not a normalisation, a unit
prefix. Transcribing the displayed `600` into a binding is wrong by 1000.

### The general rule

Four parameter families, three relationships:

| family | displayed | stored | relationship |
|---|---|---|---|
| Cutoff, all three devices | Hz | Hz | 1:1 |
| Resonance, Wavetable and Meld | 0..100 | 0..1 | UI/100 |
| Resonance, Drift | 0..1.01 | 0..1.01 | 1:1 |
| Envelope times, all three | ms | s | UI/1000 |

**Meld is the important row.** Its Q is normalised and its envelope is
unit-converted, in the same device. So the relationship is a property of
the PARAMETER, not of the device, and knowing how one parameter behaves
predicts nothing about its neighbour.

**[V]** There is no conversion rule and no per-device rule. A displayed
number is never evidence of a stored one.

### Consequence for bindings

`e.bind(filter=("path", lo, hi))` ranges are in STORED units, because that
is what gets written to `MidiControllerRange`. So a range cannot be
transcribed from a Live GUI. It is measured:

1. set the parameter to its minimum in Live, save, read the stored value
2. set it to its maximum, save, read the stored value

Two saves per parameter whose range a rack means to narrow. Cheaper first
step: set the parameter to a value that cannot be confused, `40` where the
maximum might be 100, and see what lands. Q11 and Q12 were each settled by
one such save.

Cutoff is the only family so far that needs no measurement, because
`20479.998` for 20.5 kHz is self-evidently Hz. A displayed unit that is
real (Hz, dB, %) is a hint that storage is native; a bare number, or a
prefixed unit like ms, is not.

## Q14. One slot, two unit systems - ANSWERED BY EAR

Found by playing `build/PD1.adg`, not by reading XML. Macro 8 (Volume) at
full left silenced the Operator engine and left the Simpler engine clearly
audible. Full right clipped.

`Device.range_of()` says why:

| engine | parameter | native range | unit |
|---|---|---|---|
| Operator | `Globals/Volume` | `0.0003162277571` .. `1.99526238` | linear amplitude |
| Simpler | `VolumeAndPan/Volume` | `-36.0` .. `36.0` | decibels |

**[V]** Two parameters serving the same musical idea, in two different
unit systems, on two engines of the same rack.

Operator's floor `0.000316` is the same number `ARCHITECTURE.md` section
12 gives as the send floor, and it is -70 dB, which reads as silence.
Simpler's floor is -36 dB, which does not. Neither device is wrong; they
simply do not agree, and an unscoped binding hands the macro whatever each
one offers.

The ceilings diverge too. Operator reaches 1.995, about +6 dB; Simpler
reaches +36 dB. That is the clipping.

### Why the layout did not catch it

The sound family constraint in `PATCHBAYGROUND.md` says one knob should
move the same musical idea through different synthesis. Both engines bound
slot 8 to their own volume, so the binding was correct by that rule and
still wrong in the room.

**A slot is only as consistent as its RANGES.** Binding the right
parameter on every engine is necessary and not sufficient. Where engines
disagree about units, the ranges are what make one knob feel like one
knob, and `MidiControllerRange` is the only place that agreement can live.

### The fix

Scope both to silence-to-unity in their own units:

```python
volume=("Globals/Volume", 0.0003162277571, 1.0)        # amplitude
volume=("VolumeAndPan/Volume", -36.0, 0.0)             # dB
```

Verified in `build/PD1.adg`: `Min=0.0003162277571 Max=1` and `Min=-36
Max=0`. Full right is now unity on both, so neither clips.

Full left still differs, -70 dB against -36 dB, because -36 is Simpler's
floor. That is a device limit, not a choice, and it is the residue this
fix cannot remove.

### Generalisation

This is the audible case of Q11 through Q13. Those found displayed units
differing from stored units within one parameter. This finds two
parameters, bound to one slot, whose stored units differ from each other.

The rule that covers both: **a range is measured, per parameter, and a
layout slot needs its ranges reconciled across every engine that binds
it.** `Device.range_of()` answers the first part without touching Live.
Only ears answer the second.

## Q15. A macro range follows the parameter's taper - ANSWERED

`build/PD1.adg`, FM engine, macro 3 bound to `Filter/Frequency` over
`200..8000` Hz. Macro set to 64, the centre. Live displayed **1.28 kHz**.

| hypothesis | predicted at macro 64 | matches |
|---|---|---|
| linear in Hz | 4100 Hz | no |
| logarithmic, geometric mean | 1265 Hz | **yes** |

**[V]** `MidiControllerRange` is interpolated along the PARAMETER'S OWN
taper, not linearly in stored units. For a filter frequency that taper is
logarithmic, so knob travel is spread by octave rather than by hertz.

### Consequence: a wide range costs nothing

The reason to narrow a range would be to stop a knob spending most of its
travel somewhere useless. With a logarithmic taper that does not happen:
30..18500 Hz is about 9.3 octaves spread evenly across 128 steps, roughly
14 steps per octave, playable everywhere.

So the `200..8000` this project used everywhere was giving up the top of
every filter for nothing:

| engine | native cutoff | reachable under 200..8000 |
|---|---|---|
| Operator | 30 .. 18500 | 43% |
| Simpler | 30 .. 22000 | 36% |
| Wavetable | 20 .. 20480 | 39% |
| Drift | 20 .. 20000 | 39% |

The filter could never fully open. No macro position meant "filter off",
and every generated sound was permanently darkened.

### Where the number came from

Nowhere. `200..8000` first appears in `KICKOFF.md` as an illustrative
range in a spike, and was then copied into `DSL.md`, this file,
`PATCHBAYGROUND.md` and `examples/patchbayground.py`. No document argued
for it. It survived because a specific-looking constant reads as
deliberate.

Worth generalising: **a number repeated in five files with no derivation
recorded anywhere is a guess wearing a uniform.** The one-change diff
habit catches wrong facts about the format; it does not catch a plausible
constant nobody ever measured.

### Replaced by

`CUTOFF = (30.0, 18500.0)` in `examples/patchbayground.py`, the
INTERSECTION of what the four engines offer. The intersection rather than
each engine's own maximum, because one knob position should mean one
frequency on every engine, which is the sound family constraint. Nothing
audible is lost: 18.5 kHz is already above where a sweep reads as pitch.

## Q16. Drift's modulation routing - ANSWERED

**Files:** `racks/q16_a.adg` (LFO -> LP Frequency at 80%),
`racks/q16_b.adg` (same rack, that row set to Env 1 / None / 0%). Both are
BS1 saved out of Live 12.4.3, so the Drift under test is the one PatchBay
built.

`patchbay diff` moved three facts and one rename:

| element | a | b |
|---|---|---|
| `Drift/ModulationMatrix_Source1@Value` | 2 | 0 |
| `Drift/ModulationMatrix_Target1@Value` | 6 | 0 |
| `Drift/ModulationMatrix_Amount1/Manual@Value` | 0.8000000119 | 0 |

So a modulation row is three sibling elements with a shared index, and the
routing is NOT in the parameter list. `find.params` does not return
`Source1` or `Target1`, and `library.Device.search` cannot find them,
which is why a macro bound to `Lfo_Amount` resolved, wrote a valid
`KeyMidi`, and moved nothing audible.

**Two classes of element, and only one is mappable.**

| kind | elements | children | takes a KeyMidi |
|---|---|---|---|
| routing | `ModulationMatrix_Source{1,2,3}`, `_Target{1,2,3}`, `Filter_ModSource{1,2}`, `Lfo_ModSource` | none. The value is the element's own attribute | no |
| depth | `ModulationMatrix_Amount{1,2,3}`, `Filter_ModAmount{1,2}`, `Lfo_Amount` | `LomId`, `Manual`, `MidiControllerRange`, `AutomationTarget`, `ModulationTarget` | yes |

A routing selector is a bare `<ModulationMatrix_Target1 Value="6" />` with
no `Manual`, so nothing can drive it and it can only be SET. That is a
capability the DSL did not have: every write it makes is either a mapping
or a value on a parameter.

**Two enums, indexed from 0, and the target list is Drift's own dropdown
order:** `None, Osc 1 Gain, Osc 1 Shape, Osc 2 Gain, Osc 2 Detune, Noise
Gain, LP Frequency, LP Resonance, HP Frequency, LFO Rate, Cyc Env Rate,
Main Volume`. Target 6 is LP Frequency, read off the file rather than
counted off the dropdown. The SOURCE enum is a different list and only two
of its members are pinned by this diff: 2 is LFO, 0 is Env 1.

**The donor carries a live row of its own**, and every Drift PatchBay
builds has inherited it: `Source1=5, Target1=8, Amount1=0.8`. Target 8 is
HP Frequency. So BS1 and PD1W ship with something modulating the high-pass
at 80% because a donor happened to, which is the fidelity-not-loadability
argument arriving as a defect. A rack that means to modulate nothing has
to say so.

**`Lfo_Amount` IS the depth**, confirmed by ear in Live 12.4.3 with the row
written and `Amount1` at full: Macro 5 wobbles the cutoff and the wobble
deepens with the knob. So the LFO tab's Amount gates the matrix row rather
than being independent of it, and the macro stays where it was. The row was
what was missing, not the binding.

**The same defect exists on Operator and takes the same fix**, found by
round H. `Lfo/LfoOn` and `Filter/LfoOn` both default false, so Macro 5
drove the amount of a switched-off LFO into a filter it was not connected
to; `Globals/PortamentoOn` defaults false, so the glide slot moved a time
that gated nothing. All three are plain booleans, all three confirmed by
ear once set. The general rule this leaves:

**A mapped modulator is not a working modulator.** Live writes a valid
`KeyMidi`, the knob moves the target, and whether anything is HEARD depends
on switches and routing the parameter list does not mention.
`test_a_bound_modulator_is_switched_on` asserts the pairing for both
devices, so this fails in pytest rather than in a room.

## Q9. Set form versus preset form - PARTLY ANSWERED, and it bit

**Evidence:** `build/K3_als_donor.adg`, a three chain audio effect rack
built entirely from donors harvested out of a `.als`. Live 12.4.3 refused
it, on an audio track and on a MIDI track alike:

    Exception: Not all list members have Ids.
    Exception: The document "build/K3_als_donor.adg" is corrupt and
    cannot be loaded. (Not all list members have Ids. (at line 450,
    column 19))

Line 450 is the `<AutoFilter>` element itself, sitting inside
`AbletonDevicePreset/Device`, and it carried no `Id` attribute.

**So there is a SECOND id rule.** The first is S6: an `Id` must be unique
among its siblings. The second is that a list member must HAVE one at all.
A device node inside a preset holder is a list member.

| source | `<Device>` child | loads |
|---|---|---|
| every rack Live saved here | `Id="0"` | yes |
| donor harvested from a `.adg` | `Id="0"` | yes |
| donor harvested from a `.als` | no `Id` | **refused** |

The holder holds exactly one device, so the member is number 0 and every
Live-written file says `Id="0"`. In Set form the same device is a member of
the track's `Devices` list and carries its position there instead; lifting
it out dropped the attribute and put nothing back.

**48 of 56 indexed donors were affected**, which is every device the
harvest took out of a Set. Nothing caught it. Ids were unique, every
mapping resolved, `patchbay check` passed, and `clone.assert_loadable`
only ever looked for collisions.

**Fixed** by writing `Id="0"` on the device as it is placed in a chain,
which is where the rack already writes the wrapper's own `Id="0"`: the same
rule one level apart. `clone.missing_device_ids` now refuses a tree that
lacks one, so this class fails before a file is written rather than in
Live.

**The Id was NOT the only difference.** The rebuilt file was refused again,
by a different parser error and 30 lines further on:

    Exception: Unexpected value for int64 node:
    Exception: The document "C:\Users\jaime\src\patchbay\build\
    K3_als_donor.adg" is corrupt and cannot be loaded.
    (Unexpected value for int64 node:  (at line 480, column 46))

Line 480 is `<OriginalFileSize Value=""/>`, inside
`AutoFilter/LastPresetRef/Value/AbletonDefaultPresetRef/FileRef`. Its
sibling `OriginalCrc` is blank the same way. Blank is not absent: the node
is there, and Live's `.adg` parser reads it as an int64 and gives up.

| source | `OriginalFileSize` / `OriginalCrc` |
|---|---|
| the 28 racks Live saved here, preset refs | `0` / `0`, 307 of them |
| the same files, sample refs | the real size and CRC, 44 of them |
| donor harvested from a `.als` | blank, in 42 of 54 donors |

Never blank in anything Live wrote, at either kind of ref.

**42 of 54 donors carry it**, the same population as the missing Id: what
came out of a Set. Both are fixed at the same line of `_make_chains`,
`clone.fill_empty_int64_fields` next to the `Id="0"`, and
`clone.empty_int64_fields` refuses a tree that still has one.

**Why the one-change method never caught this.** `diff.PRESET_REF_MARKERS`
hides `/PresetRef/` and `/LastPresetRef/` by default, because saving one
rack under two names moves them and they bury real findings. The field that
refuses the document lives inside exactly that subtree, so no spike pair
ever printed it. `patchbay diff --all` does.

**K3b then loaded**, on an audio track, in Live 12.4.3: three chains, Auto
Filter, EQ Eight and Echo, all present. Both fixes were needed and together
they are enough for a rack built entirely from `.als`-harvested donors. The
48 donors are usable.

### The full mapping, from `racks/q9_a.adg` beside `racks/q9_b.als`

Both files were written by Live 12.4.3 and hold the same two-chain rack, one
dragged to the browser and one saved as a Set, so the only difference
between them is the container.

| preset form | Set form |
|---|---|
| `GroupDevicePreset` (no attributes at top level) | no wrapper; the rack device sits in the track |
| `Device/<X>GroupDevice` | `LiveSet/Tracks/<Track>/DeviceChain/DeviceChain/Devices/<X>GroupDevice` |
| `BranchPresets/<X>BranchPreset` | the rack device's `Branches/<X>Branch` |
| `DevicePresets/AbletonDevicePreset/Device/<dev>` | `DeviceChain/<A>To<B>DeviceChain/Devices/<dev>` |
| `MixerPreset/AbletonDevicePreset/Device/...` | the branch's `MixerDevice` |
| `<Name Value="erode" />` | `Name` with `EffectiveName`, `UserName`, `Annotation`, `MemorizedFirstClipName` |

The rack device's own `Branches` is EMPTY in preset form, which is Â§3's rule
holding on both sides of the lift.

**The device node itself is the same node**, and this is the finding T6c
needed. Erosion came back 159 facts against 159, identical but for ids;
Overdrive matched on every parameter it has.

What differs is bookkeeping, in three kinds:

| difference | preset | Set |
|---|---|---|
| `AutomationTarget@Id`, `ModulationTarget@Id`, `Pointee@Id` | `0` | live session ids, `22315` and up |
| `LastPresetRef/.../AbletonDefaultPresetRef@Id` | `0` | `1` |
| `SourceContext/Value/BranchSourceContext` | absent | present on a device dragged in from the browser, 53 facts of provenance |

**So harvesting a donor out of a Set brings session ids with it**, and every
rack this project shipped carried some: 48 of 56 donors came out of `.als`
files. Live loads them - EQC was played with `52306` on its compressor - but
a preset Live writes never has them, so `clone.zero_session_ids` clears them
as a device is placed. That is the fourth donor repair, beside the missing
`Id`, the blank int64 fields and the legacy path elements.

One value differed that is NOT a form difference: `Drive` read 0 in the
`.adg` and 50 in the `.als`, because the two files were saved a minute apart
with a knob moved between them. Worth stating because it is exactly the kind
of difference a spike pair is supposed to exclude, and this one did not.

## Q7. An inverted chain-select zone loads, and Live REPAIRS it - ANSWERED

**Evidence:** `build/Q7_bad_zone.adg`, an instrument rack whose chain 2
carries `Min 120, Max 20` with the crossfades outside both, breaking the
`Min <= XfMin <= XfMax <= Max` invariant. Live 12.4.3 loaded it on a MIDI
track.

**So Live does not refuse an inverted zone**, and a DSL guard that raises
on one would be stricter than the format.

**It does not keep it either.** Dragged straight back out to the browser as
`racks/q7_c.adg`, chain 2's zone reads:

    BranchSelectorRange/Min           120  ->  20
    BranchSelectorRange/CrossfadeMin   10  ->  20
    BranchSelectorRange/CrossfadeMax    5  ->  20

`Max` was 20 and stayed 20, so Live collapsed the zone to `Min = XfMin =
XfMax = Max = 20`: it clamps every bound down to `Max` rather than swapping
Min and Max. An inverted zone is therefore silently a ONE-value zone, not
the range that was written, which is the worst of both answers for a
generator - no error, and not what the file said.

**So the DSL should refuse an inverted zone after all**, not because Live
rejects the file but because Live rewrites the intent. Nothing states a zone
directly yet; the guard belongs with the first caller that does.

The rest of that diff is drift from the same session, not part of the
finding: `Operator/Filter/Frequency` 12000 -> 30 on both chains, and
`LastPresetRef` filled in with a Drift path, which `patchbay diff` hides
without `--all`.

## Q18. The sidechain source is not in preset form - ANSWERED

**Evidence:** `racks/q18_a.adg` and `racks/q18_b.adg`, one Compressor on a
track in a Set that has a DR1 track, dragged to the browser twice: first
with the sidechain off, then with it on and its source set to DR1.

`patchbay diff --all` over the pair reports ONE changed fact:

    Compressor2/SideChain/OnOff/Manual@Value   false -> true

`SideChain/RoutedInput/Routable/Target` reads `AudioIn/None` in BOTH files,
beside `UpperDisplayString = No Output`, with the source selected in Live
at the moment of the drag. The rest of the diff is `PresetRef` churn from
saving under a second name.

**So a device preset does not carry its sidechain source.** The routing
belongs to the Set, and dragging a device chain to the browser leaves it
behind. Q18c is the same answer from the other direction: dropped into a
Set with no DR1 track, the enable came back ON and the source read
`No input`.

**What this settles for C4.** Every part of the sidechain except the source
is an ordinary parameter on `Compressor2` and `sets` writes it:

    SideChain/OnOff                       the External toggle
    SideChainEq/On /Mode /Freq /Q /Gain   the band that ignores hats
    SideChain/DryWet                      how much of the duck lands
    SideChain/RoutedInput/Volume          input trim
    SideListen                            audition the sidechain input

Picking the source stays one dropdown per track, by hand, and it is on the
Standing manual work list rather than the backlog. Nothing here can be
automated by trying harder: the fact is not in the file format we author.

**The External toggle is `SideChain/OnOff`.** The sidechain does nothing
until it is true, whatever the source says, which is the same shape as
Q16: a routing behind a switch.

## S11. .als track structure

TBD - routing and return tracks. The sidechain source is answered above:
it is not in a `.adg`. Whether an `.als` stores it by track name or by id
is still unknown, and only matters if PatchBay ever writes a Set.



## Q22. A path written in two formats at once - ANSWERED

**Evidence:** `build/ARP1.adg`, `build/MFX1.adg` and `build/AFX1.adg`, all
refused by Live 12.4.3 on the correct track type:

    Exception: Base types can't have children
    Exception: The document "...\build\ARP1.adg" is corrupt and cannot be
    loaded.  (Base types can't have children (at line 951, column 57))

Line 951 is a `RelativePath` carrying a `Value` AND child elements:

```xml
<RelativePath Value="">
  <RelativePathElement Id="24" Dir="Devices" />
  <RelativePathElement Id="25" Dir="Midi Effects" />
  <RelativePathElement Id="26" Dir="Velocity" />
</RelativePath>
```

Two eras of the same field. Older Live wrote the path as a LIST of
directory elements; 12.4.3 writes it as a string on the node. A node that
has both is a base type with children, and Live gives up on the document.

| source | `RelativePath` |
|---|---|
| the 28 racks Live 12.4.3 saved here | a Value, no children, 366 of them |
| 6 of 54 donors | a Value AND children |

The six: `CrossDelay`, `Gate`, `MidiNoteLength`, `MidiVelocity`,
`Overdrive`, `Redux`. Nothing about those devices is wrong; they came out
of files an older Live wrote.

**Fixed** by `clone.strip_legacy_path_elements`, which drops the child form
and keeps the Value, next to the other two donor repairs in
`_make_chains`. `clone.legacy_path_elements` refuses a tree that still has
one.

**This is the third defect of one shape**, and the shape is worth naming: a
donor carries whatever the file it was cut from happened to contain, and
some of that is not merely unwanted but invalid HERE. The other two are the
missing `Id` and the blank int64 fields, both under Q9.

## Q23. A send IS mappable, and the first check was wrong - ANSWERED

**Evidence:** `build/DR1.adg` in Live 12.4.3, kit macros 5 and 6 mapped to
every pad's send with `Rack.sending`, checks S1g and S1h.

The mapping is written exactly as every other one: a `KeyMidi` inside the
`Send` element, which carries `LomId`, `Manual`, `MidiControllerRange`,
`AutomationTarget` and `ModulationTarget` - the same shape as any
macro-driven parameter - and is addressed by containment like the rest.

**The send column was visible and every send stayed at -inf whatever the
knob did**, and that was read as Live ignoring the mapping. It was not.
See below: Live writes the identical mapping and it works. What was wrong
with `build/DR1.adg` at that moment is not recorded, the file is gone, and
the reading was the error rather than the observation.

**What this means for a spec.** Both work. A send LEVEL is
`sends={"A-Rvb:Short": 0.35}` on a chain, and a knob that sweeps every
chain's send to one return is `sending(slot, "A-Rvb:Short")` on the rack.
DR1 carries both.

**The Q16 rule still holds** - structure cannot tell you a knob works -
but this entry is the other half of it, and the more expensive half: a knob
that does not work tells you nothing about the FILE either. Verified in
Live 12.4.3: Macro 5 of `racks/q23_b.adg` sweeps pad 1's Send A.

### Live writes the SAME mapping, so "not mappable" is wrong

**Evidence:** `racks/q23_a.adg` and `racks/q23_b.adg`, `racks/s9_c.adg`
saved back out of Live and then saved again with macro 5 mapped to pad 1's
Send A **in Live's own UI**. The diff is 15 facts added and 3 changed:

    DrumBranchPreset[0]/.../SendInfos/AudioBranchSendInfo[0]/Send/KeyMidi
        Channel 16, NoteOrController 4, IsNote false, ControllerMapMode 0
    DrumGroupDevice/MacroControls.4/Manual      0 -> 97.1476822
    DrumGroupDevice/MacroDefaults.4             0 -> -1
    DrumGroupDevice/AreMacroControlsVisible     false -> true

A `KeyMidi` inside the `Send` element, addressed by containment, on channel
16 with the macro index as the CC. That is exactly what `Rack.sending`
wrote, and writing it again with `params.map_to_macro` reproduces
`q23_b.adg` with **`patchbay diff` reporting `identical`**.

So the structural half of Q23 is dead: a send is not a parameter Live
refuses to map. The behaviour observed on `build/DR1.adg` stands unexplained
and the ranges rule it out - every send in that build carried the full
`0.000316..1`, the same as this one.

**Checked:** the knob sweeps the send. `Rack.sending` is restored, DR1's
kit slots 5 and 6 drive the two returns again, and what the wrong
conclusion cost is in `THE_BASEMENT.md`.

## Q24. The arpeggiator ships FREE, so a synced rate reaches nothing - ANSWERED

**Evidence:** `build/ARP1.adg` in Live 12.4.3, check S2a. Rate is bound to
`SyncedRate`. The knob did nothing until the device's own toggle was moved
from `ms` to the metronome by hand, after which it worked as declared.

`MidiArpeggiator/SyncState` is a boolean and ships `false`, which is FREE
mode, where the rate comes from `FreeRate` in milliseconds and `SyncedRate`
is not in the signal path at all. Two states, and the other one is synced.

**This is the Q16 family again**, with a fourth device and a new twist: the
switch does not gate the parameter, it selects between TWO parameters, and
the one a spec binds is the one that is off. The others were
`Lfo/LfoOn`, `Filter/LfoOn` and `Globals/PortamentoOn` on Operator, Drift's
modulation row, and Echo's `Filter_On`.

**Fixed** by `sets("SyncState", True)` beside the binding. The general form
is worth stating: where a device offers the same control in two units,
binding one of them is half the declaration and the mode is the other half.

## Q25. A macro at 0 puts a bipolar parameter at its minimum - ANSWERED

**Evidence:** `build/MFX1.adg` in Live 12.4.3, check S2a. MidiPitcher was
bound over its native range and the rack made no sound: `Pitch` is
`-128..128` semitones, macro 3 opened at 0, and 0 through that binding is
-128 semitones. MidiScale's `Transpose` is `-36..36` and sat at -35 for the
same reason.

The mechanism is not new - a macro at 0 drives its target to the bottom of
the mapping range, which is why every layout slot carries a `start`. What is
new is that the bottom of a BIPOLAR range is not a neutral value but an
extreme, so the usual reasoning about neutral positions inverts.

**Fixed** with a range and a placed knob: `over=Range(-24, 24)` and
`start=63.5`, which is exactly 0 semitones because 63.5 of 127 is half.
Macro positions are floats, so the centre of an odd-numbered scale is
reachable.

**Guarded** by `test_a_bipolar_binding_opens_off_centre_or_not_at_all`,
which fails on any mapping whose range crosses zero while its macro sits at
0. It cannot check that a start is the RIGHT position; it can check that a
bipolar parameter is not left at its extreme.

## Q21. The Eq8 band mode enum - PARTLY ANSWERED

**Evidence:** `racks/q21_hp.adg` and `racks/q21_bell.adg`, one Eq8 in an
audio effect rack, band 1 saved as a high-pass and then as a bell.

    Eq8/Bands.0/ParameterA/Mode/Manual@Value    1  ->  3
    Eq8/Bands.0/ParameterA/Gain/Manual@Value    0  ->  15
    Eq8/Bands.0/ParameterA/Freq/Manual@Value   30  ->  30.3010044

**`Mode` is an int enum on the BAND, not on the device**, one per
`Bands.N/ParameterA`, so eight bands carry eight independent modes.
**Mode 1 is a high-pass and mode 3 is a bell.** The pair says nothing about
the other six entries, and bell is the shipped default, which is why
`q21_bell` also carries the +15 dB and the 0.3 Hz of knob drift that made
the change visible.

`Gain` reaching 15 also shows the library's harvested range for that
parameter, `-9..9`, is the DONOR's `MidiControllerRange` and not the
parameter's own limit. A range read out of a donor is a mapping range, not a
validation bound.

**Bands.0/ParameterA/Freq is `10..22000`**, which is what makes VOL1's Sub
Cut a swept frequency: set `Mode` to 1 once and bind `Freq`.

## Q20. A named scale IS one parameter - ANSWERED

**Evidence:** four saves of one MIDI rack holding `MidiScale`,
`racks/q20_a.adg` through `_d.adg`. Diffs, in order:

    a -> b   Base            0 -> 7
    a -> c   Base            0 -> 7      UseCurrentScale  false -> true
    c -> d   Base            7 -> 10     InternalScale        0 -> 2
                             UseCurrentScale  true -> false

Three parameters, and the twelve `Mapping.N` never moved:

    Base              root, 0..11 semitones, 0 = C, 7 = G, 10 = A#
    InternalScale     the scale BY NAME, 0..35, 0 = User, 2 = Minor
    UseCurrentScale   the Scale Awareness toggle - follow the Set's scale

`d` is A# Minor and reads `Base 10, InternalScale 2`, which fixes both
enum entries at once. The library reports `InternalScale` as `0..35` and
Live 12.4.3's menu lists exactly 36 entries in this order, so the index is
the menu position: User, Major, Minor, Dorian, Mixolydian, Lydian,
Phrygian, Locrian, Whole Tone, Half-whole Dim., Whole-half Dim., Minor
Blues, Minor Pentatonic, Major Pentatonic, Harmonic Minor, Harmonic Major,
Dorian #4, Phrygian Dominant, Melodic Minor, Lydian Augmented, Lydian
Dominant, Super Locrian, 8-Tone Spanish, Bhairav, Hungarian Minor,
Hirajoshi, In-Sen, Iwato, Kumoi, Pelog Selisir, Pelog Tembung, Messiaen 3
to Messiaen 7. Only 0 and 2 are diffed; the rest is the list read in order.

**What this corrects.** The earlier reading, that a scale is twelve
`Mapping.N` parameters and nothing selects one by name, was wrong: the
twelve mappings are the USER scale, reachable only at `InternalScale 0`.
So MFX1 gets its Scale Selector, one knob over one enum, and it must also
write `UseCurrentScale false` or the Set's own scale wins and the knob
moves nothing - the Q16 family, a switch in front of a binding.

## Q17. Meld has no glide switch, so glide was never off - ANSWERED

**Evidence:** `build/LD1.adg` beside `racks/q17_a.adg`, the same rack with
engine A's glide set to Gliss and its glide time driven to full.

    InstrumentMeld/MeldVoice_EngineA_GlideMode/Manual@Value   0  ->  1
    InstrumentMeld/MeldVoice_EngineA_GlideTime/Manual@Value   0  ->  2

**`GlideMode` is `Porta | Gliss`, not on and off.** Meld exposes exactly
two glide parameters per engine, `MeldVoice_Engine{A,B}_GlideMode` and
`_GlideTime`, and no enable of any kind. Mode 0 is Portamento, the shipped
default, and mode 1 is Glissando.

**So the mapped-but-switched-off diagnosis of LD1's Character knob is
wrong.** There was no switch to find. The knob moves `GlideTime` and
`GlideTime` is the whole feature, so whatever glide does or does not do
under it is a question about Meld's voicing, not about a binding, and the
Q16 family is closed at five members rather than six.

## Q3. Key and velocity zones - ANSWERED

**Evidence:** `racks/q3_a.adg` and `racks/q3_b.adg`, one instrument rack of
two chains, split first across the keyboard and then across the velocity
lane.

    [0]/ZoneSettings/KeyRange/Max              61  ->  127
    [0]/ZoneSettings/KeyRange/CrossfadeMax     61  ->  127
    [0]/ZoneSettings/VelocityRange/Max        127  ->   56
    [0]/ZoneSettings/VelocityRange/CrossfadeMax 127 ->  56
    [1]/ZoneSettings/KeyRange/Min              62  ->    0
    [1]/ZoneSettings/KeyRange/CrossfadeMin     62  ->    0
    [1]/ZoneSettings/VelocityRange/Min          1  ->   57
    [1]/ZoneSettings/VelocityRange/CrossfadeMin  1 ->   57

**A chain's three zones are three siblings of the same shape**, each with
`Min`, `Max`, `CrossfadeMin`, `CrossfadeMax`:

    <chain>/ZoneSettings/KeyRange           0..127, MIDI note
    <chain>/ZoneSettings/VelocityRange      1..127, velocity - note the 1
    <chain>/BranchSelectorRange             0..127, chain select

`ZoneSettings` holds the key and velocity zones and NOT the chain selector,
which sits one level up as a sibling of `ZoneSettings` itself. Both files
were saved with zones already present on every chain, so `ZoneSettings` is
not created by dragging a zone: Live writes all three ranges for every
chain, full-open, and a zone is a narrowing of what is already there.

The crossfade bounds move WITH the hard bounds when no crossfade is drawn,
which is how a zero-width fade is stored - not by absence, but by
`CrossfadeMin == Min` and `CrossfadeMax == Max`. Velocity starts at 1 and
not 0, because velocity 0 is a note-off.

*Unblocks: multi-sampled racks, and SR1 with them.*

## Q5 tail. `MacroHasValue.N` survives with no mapping - ANSWERED

**Evidence:** `build/probe_q5_unmapped.adg`, written with
`MacroHasValue.5 = true` on macro 6, which `patchbay mappings` confirms
reaches nothing, loaded in Live 12.4.3 and dragged back out as
`racks/q5_b.adg`.

`MacroHasValue.5` is still `true`, and the other fifteen are still `false`.
**Live neither strips the field nor validates it against the mapping
list.** The diff is knob movement from the session plus the usual
`MacroDefaults.N` catch-up from `-1` to `0`.

So the field is not a mapping cache and cannot be used as one. Nothing
depends on it.

## Q19. The sidechain EQ mode enum, and a RENAME under it - ANSWERED

**Evidence:** `racks/q19_lp.adg`, `_bp.adg` and `_hp.adg`, one Compressor
saved three times with the sidechain EQ in each of its three modes. Each
diff is one line:

    Compressor2/SideChainEq_Mode/Manual@Value    5  ->  4  ->  3

| value | band |
|---|---|
| 5 | low-pass |
| 4 | band-pass |
| 3 | high-pass |

**This is NOT the Eq8 enum.** Q21 read 1 as a high-pass and 3 as a bell on
`Eq8/Bands.N/ParameterA/Mode`. Here 3 is a high-pass. Two devices, two
lists, and reading one off the other would have put EQC's sidechain on the
wrong band.

5 is also the value the old donor carried, so EQC's band was already the
one `PATCHBAYGROUND.md` asks for. It is written explicitly now.

### The parameters are FLAT in 12.4.3, and were NESTED in 12.2

The path is `SideChainEq_Mode`, not `SideChainEq/Mode`. Live 12.4.3 writes
five flat parameters where `donors/Compressor2.adg`, saved by 12.0_12203,
has a `SideChainEq` element with five children:

    12.0_12203, SchemaChangeCount 3    SideChainEq/On  /Mode  /Freq  /Q  /Gain
    12.0_12402, SchemaChangeCount 5    SideChainEq_On SideChainEq_Mode ...

So EQC had been writing `SideChainEq/On` and `SideChainEq/Freq` into a
container 12.4.3 does not have. The DSL cannot catch that: it refuses a
path the DONOR lacks, and the donor had those paths. **A parameter path is
only as current as the donor it was checked against.**

**Fixed** by re-harvesting `donors/Compressor2.adg` out of
`racks/q19_lp.adg` and writing the flat names. EQC's golden moved.

**Scanned for more of it.** Every donor holding a device that also appears
in a 12.4.3 file under `racks/`, compared by parameter NAME:

| device | difference | kind |
|---|---|---|
| `Compressor2` | five `SideChainEq/X` became `SideChainEq_X` | RENAME, silent breakage |
| `MidiScale` | gained `InternalScale`, `UseCurrentScale` | addition |
| `Delay` | gained six `Modulation_*` | addition |

Only the rename can break a spec quietly; an addition is a parameter
nothing has bound yet. 50 of the 59 donors were saved by 12.0_12203, and
the ones no 12.4.3 file covers are unscanned.

## Q26. An INVERTED mapping range - ANSWERED, and it works

**Where it came from:** EQC's Duck knob drove `SideChain/DryWet`, the
sidechain MIX, and checked in Live 12.4.3 it never made a track duck
however far it was turned. Mix blends the external signal against the
track's own; the control that decides how much a kick flattens this track
is `Threshold`, and it moves the wrong way round - the knob must rise as
the threshold FALLS.

Nothing in the format says a range must ascend, so the binding writes:

    Compressor2/Threshold/MidiControllerRange/Min    1
    Compressor2/Threshold/MidiControllerRange/Max    0.0003162277571

**[V] Live honours `Min > Max`.** Checked in Live 12.4.3 on
`build/EQC.adg`: Duck full left leaves the threshold at 0 dB, Duck full
right puts it on the floor, and the track ducks as declared. The knob runs
backwards because the range does.

There can be no Live-SAVED evidence for this, and there never will be:
12.4.3 has no macro range editor at all (S10), so no file Live wrote has
ever carried an inverted range. This is the second capability the format
has and the GUI does not, after the range itself.

Q7 was the reason to doubt it - Live accepts an inverted chain ZONE and
silently clamps it - so the two constructs do not behave alike. A zone is
repaired, a mapping range is obeyed.

`Threshold` is stored as **linear amplitude**, not dB: `1.0` is 0 dB,
`0.000316` is -70 dB, the same scale as a send (Â§12). So the knob is linear
in amplitude and its middle sits near -6 dB.

## Q27. Live's own content is a path a donor must KEEP - ANSWERED

**Evidence:** `C:/Music/Ableton/Resources/Core Library/Defaults/Audio
Effects/Hybrid Reverb.adv`, Live 12.4.3's own default preset. Its impulse
response reads:

    ImpulseResponseHandler/SampleSlot/Value/SampleRef/FileRef
        RelativePathType   7
        RelativePath       Samples/Hybrid/ImpulseResponses/Hybrid_Early_...aif
        Path               /Applications/Live_main_2026-03-05_....app/...

**`RelativePathType 7` is Live's installed content**, the same value
`AbletonDefaultPresetRef` carries on every device this repo has looked at.
Two things follow.

**The absolute `Path` is a macOS path, in a preset running on Windows.**
Ableton ships one preset for both platforms, so for type 7 the RELATIVE
path is the real one and the absolute is decoration. That inverts the rule
for a user sample, where S7 established the absolute path is authoritative.

**A donor must keep it.** `patchbay harvest` scrubs paths so a donor names
no file, which is right for a kick somebody dragged in and wrong for an
impulse response that is part of the device: the scrubbed `Hybrid` donor
shipped in both DR1 returns and Live reported "Media files are missing".
`harvest.scrub` now skips `Path` and `RelativePath` under a type 7 ref, and
`extract` skips them too, because emitting `.sample()` for one produces
source that refuses to build on the machine that extracted it.

## Q28. What 50 stale donors actually cost - ANSWERED

**Evidence:** every donor in `donors/` compared BY PARAMETER NAME against
the same device harvested from Live 12.4.3's factory library, 73 files
covering 59 devices.

| donor | difference | kind |
|---|---|---|
| `Compressor2` | `SideChainEq/X` became `SideChainEq_X` | rename, Q19 |
| `Limiter` | `LinkChannels` became `LinkAmount`, plus `Maximize` | rename |
| `MultiSampler` | `AuxLfos.0/Slot/...` became `Lfo/Slot/...` | rename |
| `Chorus2`, `LoungeLizard`, `MidiRandom` | 1 to 2 new parameters | addition |
| the other 53 | none | - |

**So the answer to "re-harvest everything" is no.** Three renames in 59
devices, and a rename is the only kind that breaks a spec silently: a spec
binds a path the donor has, and if the donor is the only thing that says
the path exists, the binding is checked against a fiction. An ADDITION
cannot break anything, it is a parameter nothing has bound yet.

Re-harvesting only the five that differ moved five racks in the goldens and
left the other seven untouched. Re-harvesting all 59 would have moved every
rack for the sake of three.

**The scan is the durable part**, not the fix. It is one pass over
`Resources/Core Library`, it needs no Live open, and it answers the question
a version bump raises: not "did anything change" but "did anything I BIND
change".
