# Ableton preset format: how it actually works

A technical description of the `.adg` format as established by
differential diffing against **Ableton Live 12.4.3** on Windows.

This document is the consolidated model. `SCHEMA.md` is the lab notebook -
raw findings, one entry per spike, with the evidence. `SPIKES.md` is the
procedure that produces them. When the two disagree, `SCHEMA.md` wins,
because it cites files.

## Confidence markers

Every claim here is tagged. Nothing is included on the strength of
plausibility alone.

- **[V]** verified by diff or direct inspection of named files
- **[I]** inferred from consistent evidence, not yet isolated by a
  single-change diff
- **[?]** open question, listed at the end

---

## 1. Container

**[V]** An `.adg` is a single gzipped XML document. No archive, no
manifest, no binary blobs - everything is text.

**[V]** Live writes it with these conventions:

| | Live | notes |
|---|---|---|
| declaration | `<?xml version="1.0" encoding="UTF-8"?>` | double quotes, no `standalone` |
| line endings | CRLF | |
| indentation | tabs | |
| empty elements | `<X />` | space before slash |
| end of file | trailing newline | |

**[V]** **Live does not require any of them.** `patchbay`'s writer (lxml)
violates all five - single-quoted declaration with `standalone='no'`, LF,
`<X/>`, no trailing newline - and Live 12.4.3 opens the result correctly.
A 560 KB rack round-tripped through load-then-save differs by 20,252
bytes and zero facts.

Consequence: **never byte-diff two `.adg` files.** Two semantically
identical files differ by ~4%. Use `patchbay diff`, which compares the
parsed tree.

## 2. Root element and versioning

**[V]** The document root is `<Ableton>`, carrying the version stamp:

```xml
<Ableton MajorVersion="5"
         MinorVersion="12.0_12402"
         SchemaChangeCount="5"
         Creator="Ableton Live 12.4.3"
         Revision="e3d8be4d07c71dbd4de9e4183bf90652f680375b" />
```

Read the Live version from the file, not from the About box - any donor
or rack can be version-checked without opening Live.

`SchemaChangeCount` is the field to watch after a Live update. If it
moves, the findings in `SCHEMA.md` are suspect and the spikes should be
re-run.

## 3. Preset format vs Set format

**[V]** A rack preset's root child is `<GroupDevicePreset>`. This is the
*preset* representation, which is **not** the same shape a rack has
inside a Live Set (`.als`), where chains live under `DeviceChain`.

This distinction is the single most important structural fact in the
format, because it inverts the containment you would expect.

### The sibling duality

**[V]** A `GroupDevicePreset` has two sibling subtrees:

```xml
<GroupDevicePreset>
  <Device>
    <AudioEffectGroupDevice Id="0">   <!-- the rack ITSELF: macros, chain selector -->
      <MacroControls.0> ... </MacroControls.0>
      <NumVisibleMacroControls Value="8" />
      <ChainSelector> ... </ChainSelector>
    </AudioEffectGroupDevice>
  </Device>
  <BranchPresets>                      <!-- the rack's CHAINS and their devices -->
    <AudioEffectBranchPreset Id="0">
      <DevicePresets>
        <AbletonDevicePreset Id="0">
          <Device>
            <Saturator Id="0"> ... </Saturator>
          </Device>
        </AbletonDevicePreset>
      </DevicePresets>
    </AudioEffectBranchPreset>
  </BranchPresets>
  <PresetRef> ... </PresetRef>
</GroupDevicePreset>
```

`Device` holds what the rack *is*. `BranchPresets` holds what the rack
*contains*. They are siblings, so:

> **A parameter controlled by a rack's macro is never a descendant of the
> rack device node that owns that macro.**

Any code that resolves "which rack owns this macro" by walking up to the
nearest `*GroupDevice` ancestor is wrong. The correct walk is: up to the
nearest `BranchPresets`, then to its parent `GroupDevicePreset`, then
into that preset's `Device/*GroupDevice`. Implemented in
`patchbay/mappings.py:_owning_rack`.

### Rack device types

**[V]** Observed: `AudioEffectGroupDevice`, `InstrumentGroupDevice`,
`DrumGroupDevice`. **[I]** `MidiEffectGroupDevice` presumably exists by
symmetry; untested.

**[V]** Branch types pair with them: `AudioEffectBranchPreset`,
`InstrumentBranchPreset`, `DrumBranchPreset`.

### Nesting

**[V]** Racks nest by a chain's `DevicePresets` containing another
`GroupDevicePreset`. Three levels observed in `racks/s1_source.adg`:

```
GroupDevicePreset                        (DrumGroupDevice)
└─ BranchPresets/DrumBranchPreset
   └─ DevicePresets/GroupDevicePreset    (InstrumentGroupDevice)
      └─ BranchPresets/InstrumentBranchPreset
         └─ DevicePresets/GroupDevicePreset  (InstrumentGroupDevice)
```

This is the DR1 pattern from `PATCHBAYGROUND.md`, confirmed to exist and
function in a real file. **[V]** `build/VA1.adg` is two levels of it
written from scratch by `patchbay`, and it loads.

### The one thing that changes with position

**[V] A top-level `GroupDevicePreset` carries no attributes. A nested one
carries an `Id`.** All 26 racks in `racks/` agree, and it is the only
structural difference between the same rack built on a top-level skeleton
and on a nested one.

**[V] A stray `Id` on the top-level preset makes Live refuse the file as a
drop**, without ever loading it - no dialog, because Live never parses the
preset. Proved by one change: `build/probe_b_toplevel.adg` loads,
`build/probe_c_id_added.adg` is the same file plus `Id="0"` and is
refused.

This is the boundary case of the sibling rule in §8. At the top level a
`GroupDevicePreset` has no siblings, so it must carry **no** `Id` rather
than a unique one.

Consequence for a generator: **moving a rack between the two positions
means adding or removing that attribute.** Lifting an inner rack out to
use standalone is otherwise correct, and lifting one out *without*
stripping the `Id` is what made this look like a deep serialisation
problem for a while. See `THE_BASEMENT.md`.

**[V]** Nothing else about a nested rack differs. `Channel` stays `16` at
every depth (§5), depth is not encoded anywhere, and a `GroupDevicePreset`
written into a chain's `DevicePresets` needs no other adjustment.

## 4. Parameter nodes

**[V]** Every automatable parameter is an element named after the
parameter, with a consistent set of children:

```xml
<PreDrive>
  <LomId Value="0" />
  <Manual Value="0" />
  <MidiControllerRange>
    <Min Value="-36" />
    <Max Value="36" />
  </MidiControllerRange>
  <AutomationTarget Id="0">
    <LockEnvelope Value="0" />
  </AutomationTarget>
  <ModulationTarget Id="0">
    <LockEnvelope Value="0" />
  </ModulationTarget>
</PreDrive>
```

| child | meaning |
|---|---|
| `Manual` | the parameter's value. **[V]** absolute, in the parameter's own units |
| `MidiControllerRange` | **[V]** the range a macro drives this parameter across - the **mapping range**, not merely a display bound. Saturator Drive defaults to `-36..36` dB |
| `AutomationTarget` / `ModulationTarget` | automation plumbing. **[V]** `Id="0"` throughout preset files - presets carry no automation, so these are inert here |
| `KeyMidi` | **[V]** present only when mapped. See §5 |

**[V]** Internal parameter names are not the GUI labels. In Saturator,
**Drive** is `PreDrive` and **Output** is `PostDrive`. Never guess a
parameter's element name - diff for it.

**[V]** Values are absolute and in native units, not normalised 0..1.

## 5. Macro mappings - the central mechanism

**[V]** **A macro mapping is a `KeyMidi` element inserted as a child of
the target parameter.** There is no id, no pointer, no path string, and
no mapping table anywhere in the file.

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
  ...
</PreDrive>
```

Live implements rack macros as **MIDI CC on a virtual channel**. The same
structure serves computer-key mapping and real MIDI mapping; macros are
one case of it.

| field | value for a macro mapping | meaning |
|---|---|---|
| `Channel` | `16` | **[V]** the virtual macro bus, not a real MIDI channel. Fixed - does not vary with macro index or nesting depth |
| `NoteOrController` | `0`-`15` | **[V]** the macro index, zero-based. `0` = Macro 1, `1` = Macro 2 |
| `IsNote` | `false` | **[V]** a controller, not a note |
| `ControllerMapMode` | `0` | **[V]** absolute |
| `PersistentKeyString` | `""` | **[V]** empty; belongs to computer-key mapping |
| `LowerRangeNote` / `UpperRangeNote` | `-1` | **[V]** unused when `IsNote` is false |

### The three rules that follow

**1. Target is named by containment.** The mapped parameter is the one
that owns the `KeyMidi` block.

**2. Owning rack is implicit.** Which rack's Macro N is meant is not
stored. It is resolved structurally, per the walk in §3.

**3. Presence is the mapped/unmapped test.** **[V]** `KeyMidi` is written
lazily - absent until the parameter is mapped, appearing on the save
after. Counting `KeyMidi` elements counts mappings.

**[V]** Corollary, and a trap: a macro's display name and value say
nothing about whether it is mapped. `racks/s1_source.adg` has three live
mappings while every macro is named the default `Macro N` with value `0`.

### Macro to parameter transfer function

**[V]** A macro drives its target **linearly across the target's own
`MidiControllerRange`**, on a 0-127 scale:

```
value = Min + (macro / 127) * (Max - Min)
macro = (value - Min) / (Max - Min) * 127
```

Verified on two parameters with different ranges:

| macro | target | range | computed | stored |
|---|---|---|---|---|
| 69 | Saturator Drive | `-36..36` | `3.11811024` | `3.11810875` |
| 127 | Saturator Output | `-36..0` | `0` | `0` |

The 1.5e-6 gap is float32 storage precision.

**[V]** Macro values are **continuous, not integer CC steps.** Mapping a
parameter sitting at mid-range writes macro `63.5`, not `63` or `64`.

**[V] The mapping range is `MidiControllerRange` on the target.** Narrowing
it narrows what the macro reaches: setting Drive's `Max` to `12` makes
Macro 1 at full land on exactly +12 dB. Verified by writing the file and
loading it.

Worth noting for the macro grammar: **Live 12.4.3 exposes no range editor
in its UI** - not on the macro, the target, or in Map mode. Ranges are
writable only from the file, so a generator can express per-mapping scoping
that cannot be built by hand.

**[V]** Ranges are per parameter, not per device: within one Saturator,
Drive is `-36..36` while Output is `-36..0`.

This is the arithmetic Phase 5 needs. To place a parameter at a chosen
value across a variation grid, invert the formula using that parameter's
own `MidiControllerRange`.

**[V] The macro wins on load.** A mapped parameter still stores its own
`Manual`, and Live overwrites it from the macro the moment the preset
loads. So `MacroControls.N/Manual` is not cosmetic: it decides where every
parameter that macro drives starts.

Read that with the two facts above and the trap is exact. A macro nobody
has touched reads `0`; a macro at `0` puts its target at the BOTTOM of the
range; and nothing about the file is malformed when it happens. Gated in
Live 12.4.3: five racks whose Volume and Filter macros were left at `0`
loaded silent with the filter shut, and every diff, every id check and all
49 tests passed on them. Ears caught it.

A generator therefore has to place the knobs, not just wire them. The DSL
does it with grammar-level start positions, see `DSL.md`.

### Why this matters for cloning

**[V]** Because mappings are containment-addressed rather than
id-addressed, **a mapping survives a naive subtree copy**. Duplicating a
chain duplicates its `KeyMidi` blocks, and each copy correctly refers to
its own new parent's macros.

This contradicts landmine #1 in `CLAUDE.md`, which anticipated that
cloning would cross-wire mappings through duplicated ids. For **macro
mappings** that risk does not exist. Id hygiene may still matter for
other references - see §8 - but the highest-risk case is gone.

### Macro-to-macro is not a special case

**[V]** Mapping an outer rack's macro to an inner rack's macro uses the
identical structure: a `KeyMidi` on the inner rack's `MacroControls.N`,
which is itself an ordinary parameter node.

Verified in `racks/s1_source.adg`, which chains three levels:

```
Macro 1 -> MacroControls.0   [DrumGroupDevice,       depth 1]
Macro 1 -> MacroControls.0   [InstrumentGroupDevice, depth 2]
Macro 1 -> ChainSelector     [InstrumentGroupDevice, depth 2]
```

**[V]** `Channel` stays `16` at every depth, so nesting depth is not
encoded anywhere in the mapping. Depth is purely structural.

**[V]** `ChainSelector` is an ordinary parameter and takes a `KeyMidi`
like any other - chain selection is macro-mappable by the same mechanism.

## 6. The rack device node

**[V]** A rack device carries ~160 children. The macro-related ones are
fixed-width arrays of **16**, regardless of how many macros are visible:

| family | indices | holds | UI |
|---|---|---|---|
| `MacroControls.N` | 0-15 | the macro parameter itself (`Manual`, range, targets) | the knob |
| `MacroDisplayNames.N` | 0-15 | name; default `"Macro N"` (1-based in the string) | *Rename* |
| `MacroDefaults.N` | 0-15 | default value, `-1` unset | *Return to Default* |
| `MacroAnnotations.N` | 0-15 | info text | *Edit Info Text* |
| `MacroColor.N` | 0-15 | colour | colour palette |
| `ForceDisplayGenericValue.N` | 0-15 | show raw 0-127 instead of units | *Show Generic 0-127 Value* |
| `ExcludeMacroFromRandomization.N` | 0-15 | randomisation opt-out | *Exclude Macro from Randomization* |
| `ExcludeMacroFromSnapshots.N` | 0-15 | variation opt-out | *Exclude Macro **From Variations*** |

**[V]** Every one of those was confirmed by a single-change diff.

**[V]** Watch the vocabulary split on the last row: the UI says
**Variations**, the XML says **Snapshots**, exactly as with
`MacroVariations`/`MacroSnapshots` in §11. Grepping the UI word finds
nothing.

**[V]** `NumVisibleMacroControls` controls how many are shown (`8` by
default). Changing it from 8 to 16 alters **exactly that one fact and adds
no elements** - all 16 slots exist in every family regardless. A generator
always writes 16 and sets the count.

**[I]** `MacroDefaults.N` is unreliable bookkeeping. Two behaviours were
observed: it **lags one save** (a file's defaults equal the previous
save's macro values - the same lag as `PresetRef` in §9 and `UserName` in
§6), and **mapping a macro resets it to `-1`**. It drives only the *Return
to Default* menu item and affects nothing audible. **Write `-1` and do not
depend on it.**

Other notable children, **[V]** present but not yet characterised:
`MacroVariations`, `MacroSnapshots` (both empty in current samples),
`ChainSelector`, `ChainSelectorFilterMidiCtrl`, `Branches`,
`ReturnBranches`, `RangeTypeIndex`, `Annotation`.

**[V]** `UserName` holds the rack's display name. It is written **one save
behind** - a file records the name the device carried when that save
began, not the name it is being saved as. Same lag as `PresetRef` (§9).

**[V]** `Branches` on the device node is distinct from `BranchPresets` on
the preset node - see §3.

## 7. Chain select zones

**[V]** A chain's zone lives **on the chain**, not on the rack device:

```xml
<AudioEffectBranchPreset Id="1">
  <BranchSelectorRange>
    <Min Value="8" />
    <Max Value="8" />
    <CrossfadeMin Value="8" />
    <CrossfadeMax Value="8" />
  </BranchSelectorRange>
```

**[V]** Stored as **bounds, not start plus length**.

**[V]** Values are **absolute positions on the rack's `ChainSelector`
scale**, whose `MidiControllerRange` is `0..127`. Not normalised.

**[V]** Fade is **two independent values**, not one, and they are
**absolute positions on the same 0..127 scale** - not widths or offsets.

**[V]** Fades grow **inward** from the bounds:

```
Min=8      CrossfadeMin=20    CrossfadeMax=32     Max=40
 |------------->|==================|<--------------|
   fade in         full level          fade out
```

| field | meaning |
|---|---|
| `Min` | zone start |
| `CrossfadeMin` | position where fade-in completes |
| `CrossfadeMax` | position where fade-out begins |
| `Max` | zone end |

**[V] Invariant: `Min <= CrossfadeMin <= CrossfadeMax <= Max`.** No fade on
a side means that crossfade bound equals its zone bound. Resizing a zone
drags the matching crossfade bound along to preserve that equality.

**[V]** Zones are per chain and independent - editing one chain's zone
leaves every sibling untouched.

**[V]** The rack's `ChainSelector` is itself an ordinary parameter, so it
is macro-mappable exactly like any device parameter (§5). That is how the
chain-select layout in `PATCHBAYGROUND.md` gets driven from a macro.

**[?]** Whether `Max` is inclusive or exclusive is unsettled - it only
matters at the single-value boundary between touching zones, and probably
needs listening rather than a diff.

**[?]** Whether Live repairs or rejects a zone violating the ordering
invariant is untested.

**[?]** Key and velocity zones are untested. They exist on Instrument Rack
chains and are presumably siblings of this structure, but that is a guess
until diffed. `KeyRange` and `VelocityRange` elements were observed in
`racks/s1_source.adg`.

## 8. Ids

**[V]** Id-bearing fields seen: `Id` (an attribute), and elements
`PointeeId`, `LomId`, `LomIdView`.

**[V]** **The one rule: an `Id` must be unique among its siblings.**
Everything else about the value is free.

**[V]** With one boundary case: the document's top-level
`GroupDevicePreset` has no siblings, and must carry no `Id` at all. See
§3.

Established by deliberate-failure test. Two sibling `DrumBranchPreset`
elements sharing `Id="0"` makes Live reject the whole preset with *"the
preset cannot be loaded"*. Forcing every `AbletonDevicePreset` to `Id="7"`
- gapped, out of range, but unique among siblings - loads fine.

**[V]** Ids are **not file-unique**: `Id="0"` occurs 548 times in one real
rack. They are **not contiguous**: a rack with `Id="2"` at index 1, left by
a deleted device, opens fine. They are **not** required to equal the index,
though 2347 of 2359 observed do - the value is a sequence number assigned
on insert and never compacted.

**[V]** **Nothing references them.** No `PointeeId` in any preset points
anywhere. With S3's mappings also being containment-based, the preset
format uses no cross-references at all.

**[V]** **Ids are stable across saves.** Saving the same rack twice with
no edits renumbers nothing.

**[V]** In preset files most are `0`: every `AutomationTarget`,
`ModulationTarget` and `Pointee` observed carries `Id="0"`, and container
nodes like `AbletonDevicePreset Id="0"` repeat the value freely. Ids in
`.adg` are largely inert.

**[I]** This is consistent with ids mattering mainly inside `.als`, where
automation and routing need real cross-references.

**[V]** Adding a device introduced 76 new `Id` facts and changed zero
existing ones.

### Consequence for cloning

Landmine #1 in `CLAUDE.md` holds, but narrowly: duplicating a branch needs
exactly one fixup - **an `Id` unused by its new siblings**. There is no web
of references to remap, because there are no references.

`patchbay.ids.next_free_id(parent, tag)` allocates one, and `patchbay ids`
reports sibling collisions; its verdict matches Live's on every test file.

### Devices may be partial

**[V]** A device loads with **every one of its parameter nodes deleted** -
all 18 of a Saturator's. Live fills defaults for whatever is absent. There
is no required subset and no threshold.

So `donors/` is not needed for a file to *load*. It is needed for
**fidelity**: absent parameters return as defaults, and a donor is how a
device arrives configured. A generator may write **partial** device nodes,
overriding only what it cares about - a much smaller surface than emitting
a complete device.

**[V]** Deleting a parameter deletes any mapping to it, since the mapping
is a `KeyMidi` *inside* that parameter (§5). Mappings to *other* parameters
survive untouched and still work.

## 9. Save-time nondeterminism

**[V]** Two things change on every save regardless of edits. Both are
filtered by default in `patchbay diff`.

**`RoundRobinRandomSeed`** - one per Simpler, at
`OriginalSimpler/Player/MultiSampleMap/`. Live reseeds sample round-robin
selection on each save. Pure noise.

**Preset self-identity** - a preset records where it was last saved, in
two places:

```xml
<GroupDevicePreset>
  <PresetRef>
    <FilePresetRef Id="0">
      <FileRef>
        <RelativePathType Value="6" />
        <RelativePath Value="Presets/Audio Effects/Audio Effect Rack/My Rack.adg" />
        <Path Value="C:/.../User Library/Presets/Audio Effects/Audio Effect Rack/My Rack.adg" />
        <Type Value="1" />
        <LivePackName Value="" />
        <LivePackId Value="" />
        <OriginalFileSize Value="0" />
        <OriginalCrc Value="0" />
        <SourceHint Value="" />
      </FileRef>
    </FilePresetRef>
  </PresetRef>
```

and the device's `LastPresetRef` mirrors it.

**[V]** A never-saved rack has `<AbletonDefaultPresetRef>` with an empty
`FileRef` plus a `<DeviceId Name="AudioEffectGroupDevice" />` child. On
first save to the User Library this is *replaced* by `<FilePresetRef>`,
and the `DeviceId` child disappears.

**[V]** This is real state, not churn - but it changes whenever a spike
pair is saved under two names, so it is filtered during discovery.

### FileRef shape

**[V]** `FileRef` carries far more than a path, exactly as landmine #2 in
`CLAUDE.md` warns: `RelativePathType`, `RelativePath`, `Path`, `Type`,
`LivePackName`, `LivePackId`, `OriginalFileSize`, `OriginalCrc`,
`SourceHint`. `RelativePathType="6"` appears to denote User Library.

**[V]** `Path` and `RelativePath` travel as a consistent pair.

**[?]** Whether sample `FileRef`s carry the same field set, and which
fields must be rewritten together to avoid an offline sample, is S7.
The `PresetRef` case above is a strong hint at the shape but is not a
substitute for the spike.

---

## 10. Sample references

**[V]** A Simpler's sample lives under
`OriginalSimpler/Player/MultiSampleMap/SampleParts/MultiSamplePart`, and
carries **two** `FileRef`s, not one:

```
MultiSamplePart/SampleRef/FileRef                     <- the live reference
MultiSamplePart/SampleRef/SourceContext/SourceContext/
                          OriginalFileRef/FileRef     <- where it was imported from
```

**[V]** Both move when a sample is swapped. The second can point somewhere
entirely different - a sample imported into the User Library keeps its
pre-import path here indefinitely.

### FileRef fields

| field | example | notes |
|---|---|---|
| `Path` | `C:/Music/.../Samples/Imported/kick.wav` | **[V]** absolute, forward slashes even on Windows |
| `RelativePath` | `Samples/Imported/kick.wav` | **[V]** relative to the User Library |
| `RelativePathType` | `6` | **[V]** `6` = inside User Library, `1` = escaping relative (`../../..`) |
| `OriginalFileSize` | `24044` | **[V]** exact on-disk byte count |
| `OriginalCrc` | `63283` | **[V]** 16-bit checksum. **[?]** algorithm unidentified |
| `Type`, `LivePackName`, `LivePackId`, `SourceHint` | | present, unchanged by a swap |

### Derived metadata outside FileRef

**[V]** Swapping one sample moves 20 facts. Rewriting the path touches 2 of
them. The rest:

| node | derivation |
|---|---|
| `MultiSamplePart/Name` | filename without extension |
| `SampleRef/DefaultDuration` | frame count |
| `MultiSamplePart/SampleEnd` | frames - 1 |
| `SustainLoop/End`, `ReleaseLoop/End` | frames - 1 |
| `SourceContext/BrowserContentPath` | browser URI, URL-encoded |
| `InitialSlicePointsFromOnsets/SlicePoint` | transient analysis; may be added or removed |

**[V]** For plain PCM WAV, `frames = (filesize - 44) / (channels * bits/8)`
- verified exactly against two files. So everything except the CRC is
computable from the target file without Live.

### What is actually required

**[V]** The derived metadata is **advisory**. Live re-reads the sample file
on load and recomputes it. Six deliberately inconsistent variants were
built and dragged into Live:

| paths | size + crc | duration | result |
|---|---|---|---|
| correct | stale | stale | works |
| correct | correct | stale | works |
| correct | correct | correct | works |
| correct | zeroed | stale | works |
| correct | stale | correct | works |
| correct | zeroed | correct | works |

**[V] All six load.** `OriginalFileSize` and `OriginalCrc` are not
validated on load, and stale `DefaultDuration` / `SampleEnd` / loop ends do
no harm.

**[V]** **A path-only rewrite is sufficient to retarget a sample.** The
other 18 facts a real swap moves are Live keeping its own bookkeeping
tidy. Write them for hygiene - a generated preset that diffs cleanly
against a Live-saved one is worth having - but nothing depends on them.

**[V]** Nothing needs the CRC. See §11 rule 10.

An earlier reading of this table had one variant failing and inferred a
cache-key mechanism; that variant had been double-clicked rather than
dragged, which starts a second Live instance and hangs. See §11 rule 11 and
`SCHEMA.md` S7.

## 11. Macro variations

**[V]** A variation is a `MacroSnapshot` in a positional list on the rack
device. Live's UI calls them Variations; the XML calls them Snapshots.

```xml
<MacroVariations>
  <MacroSnapshots>
    <MacroSnapshot Id="0">
      <AutogeneratedNameIndex Value="1" />
      <SnapshotName Value="Variation 1" />
      <MacroValues.0 Value="69" />        <!-- 16 of these, then -->
      <MacroHasValue.0 Value="true" />    <!-- 16 of these -->
      ...
    </MacroSnapshot>
  </MacroSnapshots>
</MacroVariations>
```

| field | meaning |
|---|---|
| `Id` | position, `0`-based, matches list order |
| `SnapshotName` | display name, free text, defaults to `"Variation N"` |
| `AutogeneratedNameIndex` | the `N` behind that default name |
| `MacroHasValue.0-15` | whether this variation drives that macro |
| `MacroValues.0-15` | the macro position, or `-1` when unset |

**[V]** **Values are absolute on the macro 0..127 scale**, the same units
as `MacroControls.N/Manual` - not normalised. Verified by a snapshot
holding `69, 127` in a file whose live macros were `69, 127`.

Combined with the transfer function in §5, this means variation generation
happens entirely in macro space, and each engine's parameter ranges are
applied by Live rather than by the generator.

**[V]** All 16 slots are always written. Sparseness is expressed by
`MacroHasValue.N`, with `-1` as the unset value - the same sentinel as
`MacroDefaults.N`.

**[V]** A snapshot is captured when the user presses New and does not track
the macros afterwards: a rack's live macro values say nothing about its
variations.

**[V]** Writing a variation set requires no id reconciliation and no
interaction with mappings - append elements with sequential `Id`s.

**[V]** Element order is `AutogeneratedNameIndex`, `SnapshotName`, the 16
`MacroValues.N`, then the 16 `MacroHasValue.N`. The families are not
interleaved. Clearing `racks/s8_c.adg`'s snapshots and rewriting them
through `variations.write` diffs at zero facts against the original, so the
writer agrees with Live on order, sentinel and scale.

**[V]** A variation may drive the rack's `ChainSelector`, since that is an
ordinary parameter and macro-mappable like any other (§5). So a variation
can select its own chain, which is what makes a sound a variation rather
than a chain.

**[V]** An *unmapped* macro may carry `MacroHasValue = true`. The file loads
and the entry appears in the panel, but recalling it moves nothing, since
there is no mapping for the position to travel down. Accepted and inert, so
`patchbay` refuses to write one: a variation that looks live and does
nothing is worse than an error. Verified with
`build/probe_q5_unmapped.adg`.

**[V]** No snapshot ceiling at 256. Live loads and lists all 256 in
`build/probe_q4_256.adg`, with no truncation. The template needs ~38 per
rack, so variation grids do not need chunking.

## 12. Drum racks, returns and sends

### Pads map to notes

**[V]** `DrumBranchPreset/ZoneSettings`:

| field | meaning |
|---|---|
| `ReceivingNote` | the MIDI note that triggers this pad - its grid position |
| `SendingNote` | the note handed to the chain's instrument, `60` (C3) on every pad |
| `ChokeGroup` | `0` for none |

Moving a pad in the grid changes `ReceivingNote` and nothing else.
`SendingNote` staying at 60 is why a pad's sampler plays at root pitch
wherever the pad sits.

### Return chains

**[V]** Returns live in `ReturnBranchPresets`, a sibling of `BranchPresets`
under `GroupDevicePreset`:

```
GroupDevicePreset
├─ Device/DrumGroupDevice                            the rack itself
├─ BranchPresets/DrumBranchPreset[i]                 the pads
└─ ReturnBranchPresets/AudioEffectBranchPreset[i]    the returns
```

**[V]** A return branch is an `AudioEffectBranchPreset` whatever the parent
rack type - it is an audio chain by nature.

**[V]** As in §3, the device node's `ReturnBranches` is empty in presets,
just like `Branches`. The `Presets`-suffixed containers are the real ones.

### Sends

**[V]** Every chain's mixer holds a `SendInfos` list with one
`AudioBranchSendInfo` per return, at
`MixerPreset/AbletonDevicePreset/Device/AudioBranchMixerDevice/SendInfos`:

```xml
<AudioBranchSendInfo Id="0">
  <Send>
    <Manual Value="0.3388441503" />
    <MidiControllerRange><Min Value="0.0003162277571" /><Max Value="1" /></MidiControllerRange>
  </Send>
  <EnabledByUser Value="true" />
  <Index Value="0" />
</AudioBranchSendInfo>
```

**[V]** `Index` names the return **positionally**, matching order in
`ReturnBranchPresets`. No ids involved - consistent with §5.

**[V]** Adding a return seeds a send entry on **every** existing chain at
once. A generator adding a return must add the matching `AudioBranchSendInfo`
to every chain, or the rack will be inconsistent.

**[V]** Send level is **linear amplitude**: `Min` is `0.0003162277571`
(10^(-70/20), -70 dB, the silent floor) and `Max` is `1` (0 dB).

This is a **third scale** in the format. Keep them straight:

| thing | scale |
|---|---|
| macros and variations | `0..127`, continuous (§5, §11) |
| chain zones | `0..127` integer positions (§7) |
| device parameters | native units, per-parameter range (§4) |
| sends | linear amplitude `0.000316..1` (§12) |

**[?]** Whether the send knob is linear in amplitude or in dB is untested.

### View state worth knowing

**[V]** `AreSendsVisible` on the rack device gates the send column in the
chain list, and defaults to `false`. Per-pad sends are invisible in Live
until it is on, which is a UI trap rather than a format one.

## 13. Practical rules for generators

Derived from the above; these are the invariants `patchbay` must respect.

1. **Never byte-compare.** §1.
2. **Never guess a parameter's element name.** Diff for it. Drive is
   `PreDrive`. §4.
3. **To map parameter P to macro N:** insert a `KeyMidi` child with
   `Channel=16`, `IsNote=false`, `NoteOrController=N-1`,
   `ControllerMapMode=0`, empty `PersistentKeyString`, both range notes
   `-1`. To unmap: delete the element. §5.
4. **P must live in the `BranchPresets` subtree of the rack whose macro N
   is.** There is nothing else to set - no table to register with. §5.
5. **Cloning a chain may copy `KeyMidi` blocks verbatim.** They rebind
   structurally. §5.
6. **Write all 16 macro slots**, and set `NumVisibleMacroControls` to
   control visibility. §6.
7. **Values are absolute in native units.** Do not normalise. §4.
8. **Rewrite `Path` and `RelativePath` together**, never one alone. §9.
9. **Chain zones are bounds on a 0..127 scale, stored per chain.** §7.
10. **To retarget a sample:** rewriting `Path` + `RelativePath` on **both**
    FileRefs is sufficient. Set `Name`, the frame-derived values and zero
    the size/crc for hygiene, but none of that is load-bearing and the CRC
    never needs computing. §10.
11. **Load-test by dragging into a running Live**, never by double-clicking
    the file - that starts a second instance and hangs, which is
    indistinguishable from a rejected file. §10.
12. **Variations are written in macro space, 0..127**, with all 16 slots
    present and `MacroHasValue.N` carrying participation. §11.
13. **A pad's grid position is `ReceivingNote`**; leave `SendingNote` at 60. §12.
15. **When cloning a branch, give it an `Id` free among its siblings.** That
    is the only id work required, and getting it wrong makes Live reject
    the whole preset. §8.
17. **A rack written into a chain's `DevicePresets` needs an `Id`; the
    document's top-level rack must have none.** Moving a rack between
    those two positions means adding or removing that one attribute, and
    nothing else. §3.
16. **Device nodes may be partial** - override the parameters you care
    about and let Live default the rest. §8.
14. **Adding a return chain means adding an `AudioBranchSendInfo` to every
    chain**, and send levels are linear amplitude, not dB. §12.

## 14. Open questions

Ordered by how much they gate the build.

| | question | spike | gates |
|---|---|---|---|
| **[?]** | Chain zone: is `Max` inclusive? Does Live repair a violated zone ordering? | S5 tail | Phase 4, low stakes |
| **[?]** | Key and velocity zone encoding - assumed sibling of `BranchSelectorRange`, unverified. | S5 rest | Phase 4 |
| **[?]** | `OriginalCrc` algorithm. 16-bit; zlib and 10 CRC-16 variants ruled out over 4 chunk choices. **Closed as irrelevant** - nothing reads it on load. | - | nothing |
| **[V]** | Can an *unmapped* macro carry `MacroHasValue = true`? **Yes, and it does nothing.** Closed, see §11 | S8 tail | nothing |
| **[V]** | Snapshot ceiling. **None at 256**, no truncation. Closed, see §11 | S8 tail | nothing |
| **[?]** | Drum rack pad-to-note (`ReceivingNote`, `SendingNote` seen but uncharacterised), internal returns, per-chain sends. | S9 | Phase 4 |
| **[?]** | `.als` track routing, sidechain source, return tracks. | S11 | Phase 6 |
| **[?]** | Does element order within a parameter matter? `KeyMidi` is written between `LomId` and `Manual`. | - | writer safety |

## 15. Evidence

Every **[V]** claim above traces to these files, all in `racks/`.

| file | what it is | establishes |
|---|---|---|
| `s1_source.adg` | AlienMind Drum Rack, 560 KB, 18,148 facts, 3 nesting levels, 3 mappings | round trip, DR1 nesting, macro-to-macro, ChainSelector mapping |
| `s2_a.adg` / `s2_b.adg` | same rack saved twice, no edits | noise floor, id stability, `RoundRobinRandomSeed`, `PresetRef` |
| `s3_a.adg` / `s3_b.adg` | Audio Effect Rack + Saturator, before/after mapping Drive to Macro 1 | the entire `KeyMidi` mechanism |
| `s3b.adg` | same rack, Output additionally mapped to Macro 2, both macros moved | `NoteOrController` = macro index; the transfer function; `MacroDefaults` sentinel |
| `s5_a.adg` / `s5_b.adg` | two-chain Audio Effect Rack, one chain's zone dragged 0 -> 8 | `BranchSelectorRange` |
| `s5_len_a.adg` / `s5_len_b.adg` | same rack, zone right edge 16 -> 40 | `Crossfade*` are absolute positions |
| `s5_fade_aa.adg` / `s5_fade_bb.adg` | same rack, left fade handle dragged inward | fades grow inward; the ordering invariant |
| `s7_a.adg` / `s7_b.adg` | Instrument Rack + Simpler, one sample swapped | the 20 facts a swap moves; two FileRefs |
| `s8_a/b/c.adg` | same rack with 0, 1 and 2 macro variations | the `MacroSnapshot` structure |
| `s9_a/b/c/d.adg` | drum rack: 2 pads, then a return, then a send raised, then a pad moved | `ZoneSettings`, `ReturnBranchPresets`, `SendInfos` |
| `s10_c..g.adg` | one macro-metadata change per save | each `.N` family, `NumVisibleMacroControls` |
| `build/s10_range_test.adg` | Drive's `MidiControllerRange/Max` set to 12 | mapping ranges are `MidiControllerRange` |
| `build/s6_*.adg` | duplicate vs merely-gapped ids | siblings must be unique; value is free |
| `build/s12_*.adg` | 1, 5, 9 and all 18 parameters deleted | devices may be partial |
| `build/s7_test_A..F.adg` | six deliberately inconsistent retargets, all loaded in Live | the cache-key model |
| `build/PD1.adg` | 96 variations over four slots, one being the engine | variations load and recall; a variation may drive `ChainSelector` |
| `build/probe_q4_256.adg` | 256 variations, count the only difference from PD1 | no snapshot ceiling at 256 |
| `build/probe_q5_unmapped.adg` | one variation flagging an unmapped macro | accepted on load, inert on recall |
| `build/probe_b_toplevel.adg` / `probe_c_id_added.adg` | one rack, differing only by `Id` on the top-level preset | a top-level `GroupDevicePreset` must carry no `Id` |
| `build/VA1.adg` | two levels of nesting, written from scratch | a rack Live never saved survives being nested; macro-to-macro drives |

Reproduce with:

```
patchbay roundtrip racks/s1_source.adg
patchbay diff racks/s2_a.adg racks/s2_b.adg
patchbay diff racks/s3_a.adg racks/s3_b.adg
patchbay mappings racks/s1_source.adg
patchbay diff racks/s3_b.adg racks/s3b.adg
patchbay diff racks/s5_a.adg racks/s5_b.adg
patchbay diff racks/s5_fade_aa.adg racks/s5_fade_bb.adg
patchbay diff racks/s8_b.adg racks/s8_c.adg
patchbay diff racks/s9_c.adg racks/s9_d.adg
patchbay diff racks/s10_c.adg racks/s10_d.adg
patchbay ids racks/s1_source.adg
```
