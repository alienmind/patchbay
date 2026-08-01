# Research Catalogue

This document serves as a lookup index for the **Q** (Question) and **S** (Spike) numbers referenced
throughout the codebase and documentation. It clarifies that these are _research tickets and
experiments_ (not racks or components).

## Schema Findings (Q*)

Q numbers represent specific findings (Questions answered) about the XML schema of .adg and .als
files. Detailed evidence for each is recorded in doc/SCHEMA.md.

- **Q10. Meld filter resonance - ANSWERED**
- **Q11/Q12. Displayed units are not stored units - ANSWERED**
- **Q14. One slot, two unit systems - ANSWERED BY EAR**
- **Q15. A macro range follows the parameter's taper - ANSWERED**
- **Q16. Drift's modulation routing - ANSWERED**
- **Q9. Set form versus preset form - PARTLY ANSWERED, and it bit**
- **Q7. An inverted chain-select zone loads, and Live REPAIRS it - ANSWERED**
- **Q18. The sidechain source is not in preset form - ANSWERED**
- **Q22. A path written in two formats at once - ANSWERED**
- **Q23. A send IS mappable, and the first check was wrong - ANSWERED**
- **Q24. The arpeggiator ships FREE, so a synced rate reaches nothing - ANSWERED**
- **Q25. A macro at 0 puts a bipolar parameter at its minimum - ANSWERED**
- **Q21. The Eq8 band mode enum - PARTLY ANSWERED**
- **Q20. A named scale IS one parameter - ANSWERED**
- **Q17. Meld has no glide switch, so glide was never off - ANSWERED**
- **Q3. Key and velocity zones - ANSWERED**
- **Q5 tail. `MacroHasValue.N` survives with no mapping - ANSWERED**
- **Q19. The sidechain EQ mode enum, and a RENAME under it - ANSWERED**
- **Q26. An INVERTED mapping range - ANSWERED, and it works**
- **Q27. Live's own content is a path a donor must KEEP - ANSWERED**
- **Q28. What 50 stale donors actually cost - ANSWERED**
- **Q29. A send went into the nested rack, not the chain - ANSWERED**
- **Q8. The send slider loses 20 dB per halving - ANSWERED**
- **Q30. Writing a Set: what preset form costs to reverse - ANSWERED**
- **Q31. A zero pointee id is valid in a preset and refused in a Set**
- **Q32. `ReturnBranch` is the Set-form tag for a rack's return chain - ANSWERED**
- **Q33. A track routed into a track, and a sidechain source - ANSWERED**
- **Q34. A pointee is recognised by SHAPE, not by its tag - ANSWERED**
- **Q35. A preset-only child on a Set-form branch CRASHES Live - ANSWERED**
- **Q36. A track needs one clip slot per SCENE - ANSWERED**
- **Q37. A send on a RETURN track is disabled - ANSWERED**
- **Q38. `SendsPre` is one flag per RETURN, at Set level - ANSWERED**
- **Q39. Colour is one integer, everywhere it appears - ANSWERED**
- **Q40. A drum pad's note is `ZoneSettings` in a preset and `BranchInfo` in a Set - ANSWERED**
- **Q41. A chain per sample is a RAM budget - ANSWERED**
- **Q42. `ReceivingNote` counts DOWN from 128 - ANSWERED**
- **Q43. A macro on a BOOLEAN carries `MidiCCOnOffThresholds` - OPEN**

## Spikes (S*)

Spikes are targeted experiments performed in Ableton Live to reverse-engineer its file formats. The
procedures and results are detailed below.

How this project learns anything about the file format, and what is still unknown.

Findings go in `SCHEMA.md`. The consolidated model is `ARCHITECTURE.md`. This file is the procedure
and the open list.

### Phase 0 is closed

Thirteen spikes answered, one retired. Both kill criteria passed. Every verified claim in
`ARCHITECTURE.md` traces to a file in `racks/` or, for the constructed failure tests, in `build/`.

|     | spike               | result                                                                    |
| --- | ------------------- | ------------------------------------------------------------------------- |
| S1  | round trip fidelity | lossless; Live tolerates lxml's serialiser                                |
| S2  | noise floor         | zero after filtering; ids do NOT churn                                    |
| S3  | macro mapping       | `KeyMidi` in the target, virtual MIDI CC channel 16                       |
| S3b | macro index         | CC number is the zero-based macro index                                   |
| S4  | macro to macro      | identical structure, three levels verified                                |
| S5  | chain zones         | `BranchSelectorRange`, bounds, fades grow inward                          |
| S6  | id allocation       | unique among SIBLINGS, nothing else matters                               |
| S7  | FileRef             | two per sample; only the paths are required                               |
| S8  | macro variations    | `MacroSnapshot` list, absolute 0..127                                     |
| S9  | drum racks          | `ReceivingNote`, `ReturnBranchPresets`, `SendInfos`                       |
| S10 | macro metadata      | one field per menu item; ranges are `MidiControllerRange`                 |
| S12 | minimal devices     | load with ALL parameters deleted                                          |
| S13 | nested racks        | a top-level `GroupDevicePreset` must carry no `Id`                        |
| S11 | `.als` structure    | ANSWERED after being retired once. Q9 read Set form, Q30 and Q31 wrote it |

### Open questions

Ordered by what they block. None is a kill criterion; the project works without any of them.

**~~Q1. Rack inside a chain.~~ ANSWERED: it writes, and it drives.** `build/VA1.adg` is two levels
built by `patchbay` from `examples/playgrnd.py`. It loads, Macro 1 swaps sub-rack, Macros 2 to 4
chain macro-to-macro into whichever is selected, and variations recall through that chain. So a rack
Live never saved survives being nested, and a mapping written rather than saved drives identically.

**~~Q1b. Why a nested rack cannot be lifted out.~~ ANSWERED: a leftover `Id`.** See S13 below. A
top-level `GroupDevicePreset` carries no attributes and a nested one carries an `Id`; that one
attribute decides whether Live accepts the drop. The guard restricting skeletons to top-level racks
is gone.

**Q2. Aftertouch.** `EXAMPLE_PLAYGRND.md` wants aftertouch mapped to filter and pitch on every
sound, excluding drum pads. Nothing is known about how that is stored. It is probably a sibling of
the `KeyMidi` mechanism, since that already encodes MIDI, but that is a guess. Diff a rack before
and after mapping aftertouch to one parameter. _Blocks: the macro layout being complete._

**Q3. Key and velocity zones.** S5 settled chain-select zones. Key and velocity zones are Instrument
Rack only and are PRESUMED siblings of `BranchSelectorRange`. Do not assume it in code until diffed.
Save an instrument rack with two chains, drag a key zone, then a velocity zone, one save each.
_Blocks: multi-sampled racks._

**~~Q4. Variation limits.~~ ANSWERED: no ceiling at 256.** Live 12.4.3 loads
`build/probe_q4_256.adg` and shows all 256 entries. Nothing is truncated and nothing is refused.
`build/PD1.adg`'s 96 load likewise.

~692 sounds across 18 engines is ~38 per rack, so the ceiling is far above what the template needs
and **the variation grid does not need chunking**. The exact limit is unmeasured and now
uninteresting.

**~~Q5. Unmapped macros in a variation.~~ ANSWERED: accepted, and inert.**
`build/probe_q5_unmapped.adg` flags macro 6 with nothing mapped to it. Live loads the file and the
entry appears in the panel, so `MacroHasValue.N` on an unmapped macro is **not** a load error.
Recalling it does not move macro 6.

So the failure mode is silence, not rejection: the entry looks like it does something and does
nothing. The guard in `Rack._write_variations` stays, now because a no-op variation is worse than an
error rather than because the answer was unknown.

_Untested tail, cheap if ever wanted:_ whether Live keeps the flag or strips it. Save the probe back
out of Live and diff `MacroHasValue.5`.

**Q6. Drum rack return selectors.** `EXAMPLE_PLAYGRND.md` wants each DR1 return chain to hold a
selector across several reverbs and delays, so a macro swaps the EFFECT rather than the send level.
The pieces are known separately; the combination is untested.

**Q7. Zone ordering violations.** `Min <= XfMin <= XfMax <= Max` is the invariant. Untested whether
Live repairs or rejects a file that breaks it. Worth knowing before a generator can produce one by
arithmetic error.

**Q8. Send taper.** Sends are linear amplitude from 0.000316 to 1, but whether the knob is linear in
amplitude or in dB is unknown. Only matters if a spec ever states send levels as knob percentages.

### Retired

**Sidechain source.** Absent from the Live Object Model AND not yet found in the file format.
`EXAMPLE_PLAYGRND.md` needs it for DR1. It stays manual, priced at one afternoon. Revisit only if
that proves annoying in practice.

**Since answered:** Q33. Both the routing target and the sidechain source are in the file, and
`patchbay session` writes them.

**`OriginalCrc` algorithm.** 16-bit, and zlib plus ten CRC-16 variants over four chunk choices all
missed. Closed as irrelevant: nothing reads it on load.

### Ground rules

- **Load-test by dragging the file into a running Live instance.** Double-clicking an `.adg` starts
  a _second_ Live, which hangs for a few seconds and loads nothing - indistinguishable from Live
  rejecting the file, and it has already produced one wrong conclusion. Live's log at
  `%APPDATA%/Ableton/Live <version>/Preferences/Log.txt` settles which happened: grep for
  `CommandLine` and `Another instance`.
- Every spike is: save `a`, change **exactly one thing**, save `b`, diff. Two changes in one diff
  wastes the spike, because you cannot tell which node belongs to which change.
- Save every pair into `racks/`, named `s3_a.adg` / `s3_b.adg` etc, so the evidence survives.
  `racks/` is an asset, not scratch.
- Record the exact Live version once, at the top of `SCHEMA.md`. (Live > About Live.) The schema is
  version specific.
- If a diff comes back with dozens of changes, you changed more than one thing, or the noise floor
  (S2) is worse than assumed. Do S2 first.

### Order

Original plan: S1, S2, S3 first (kill criteria), then S6 to decide whether cloning is viable, then
the rest, S11 last.

**Revised after S3.** Mappings turned out to be containment-addressed, not id-addressed, so cloning
does not depend on id hygiene for macros and S6 stopped being a gate. Remaining order:

1. **S3b** - confirm the macro index encoding. One diff, and everything in Phase 2 rests on it.
2. **S5, S7, S10** - feed Phases 3 and 4.
3. **S8** - feeds Phase 5, the highest-value module.
4. **S9, S12** - fill in the drum rack and donor details.
5. **S6** - still worth doing before `clone.py` ships, for non-macro references.
6. **S11** - last, and skippable if it proved too costly.

---

### ~~S1. Round trip fidelity~~ - DONE, PASSED (kill criterion)

**Live:** save any real rack (the more complex the better) as `racks/s1_source.adg`.

**Run:**

```
patchbay roundtrip racks/s1_source.adg
```

**Then:** drag `racks/s1_source.roundtrip.adg` into Live.

Pass = it opens and behaves identically. `structurally identical: YES` with differing bytes is
expected (lxml's serialiser is not Live's) and is fine _provided Live opens it_. Only Live's opinion
counts.

If it fails: stop. Do not proceed. The likely culprits are the XML declaration, encoding, or
self-closing tag style in `io.save`.

### ~~S2. Noise floor~~ - DONE, PASSED

**Live:** open a rack, save as `racks/s2_a.adg`. Change nothing at all. Save again as
`racks/s2_b.adg`.

**Run:**

```
patchbay diff racks/s2_a.adg racks/s2_b.adg
patchbay diff racks/s2_a.adg racks/s2_b.adg --all
```

**Record:** anything the first command shows is noise the filter does not yet catch; add its field
name to `SAVE_NOISE` in `patchbay/diff.py` and note why in `SCHEMA.md`. The second shows what is
already filtered.

Ideal result: first command prints `identical`.

**Done for Live 12.4.3 - see SCHEMA.md.** Floor is zero after adding `RoundRobinRandomSeed` and the
`PresetRef` paths to the filter. Ids were found _not_ to churn, so they are now shown by default.
Re-run this spike after any Live update.

### ~~S3. Macro mapping~~ - DONE, PASSED (kill criterion)

**Live:** rack with one device, no macro mapped. Save `racks/s3_a.adg`. Map Macro 1 to one device
parameter. Change nothing else - not the macro value, not the name. Save `racks/s3_b.adg`.

**Run:**

```
patchbay diff racks/s3_a.adg racks/s3_b.adg
```

**Record in SCHEMA.md:** the node that appeared, and critically _how it names its target_ - by id,
by path, or by index. Quote the actual XML of the added subtree (`patchbay unpack` then find it).

If the target is addressed by an id, S6 becomes load bearing. If it is addressed positionally,
cloning gets easier and remapping gets harder.

**Result: neither.** The target is addressed by **containment** - the mapping is a `KeyMidi` element
inside the target parameter, encoding a virtual MIDI CC. No id, no path, no index into a table. See
`ARCHITECTURE.md` §5 for the full mechanism and `SCHEMA.md` for evidence.

Consequence: S6 is **not** load bearing for macro mappings, and cloning may copy `KeyMidi` blocks
verbatim.

Caution for whoever repeats this: the first read of this diff wrongly concluded no mapping was
present, because `KeyMidi` looks like inert MIDI defaults. It is the finding.

### ~~S3b. Macro index confirmation~~ - DONE, CONFIRMED

Small but load bearing. Every mapping observed so far targets Macro 1 (`NoteOrController = 0`), so
"CC number = zero-based macro index" is inference, not fact.

**Live:** take `racks/s3_b.adg` (Saturator, Drive mapped to Macro 1). Map a _second_ parameter -
Saturator's **Output** - to **Macro 2**. Save as `racks/s3b.adg`.

**Run:**

```
patchbay diff racks/s3_b.adg racks/s3b.adg
patchbay mappings racks/s3b.adg
```

**Expected:** a second `KeyMidi`, on the Output parameter, with `NoteOrController = 1` and
`Channel = 16`. `patchbay mappings` should then report `Macro 1 -> PreDrive` and
`Macro 2 -> <output param>`.

**If instead** `NoteOrController` is 2, or the channel changes, or the index turns out to be
1-based, fix the mapping model in `ARCHITECTURE.md` §5 and the `macro` calculation in
`patchbay/mappings.py` before any generator is written.

**Result: confirmed.** `PostDrive` (Saturator's Output) got `NoteOrController=1`, `Channel=16`. The
mapping model in `ARCHITECTURE.md` §5 stands as written.

Two extras came free: the **macro to parameter transfer function** (linear over the target's
`MidiControllerRange`, see ARCHITECTURE §5), and `MacroDefaults.N` using `-1` as an unset sentinel -
with an anomaly now tracked under S10.

### ~~S4. Macro to macro~~ - DONE, answered by S3 evidence

**Live:** rack containing a rack. Save `racks/s4_a.adg`. Map the outer rack's Macro 1 to the inner
rack's Macro 1. Save `racks/s4_b.adg`.

**Run:** same two commands.

**Record:** whether the added node is the same shape as S3's or a different type. DR1 needs three
levels of this, so also note whether the depth appears anywhere in the encoding.

**Result: no separate spike needed.** `racks/s1_source.adg` already contains three levels of
macro-to-macro chaining, found by `patchbay mappings`. The structure is **identical** to S3 - a
`KeyMidi` on the inner rack's `MacroControls.N`, which is just another parameter node. `Channel`
stays 16 at every depth, so nesting is not encoded in the mapping at all; it is purely structural.

`ChainSelector` is mappable the same way.

Re-run this spike properly only if a case appears where the implicit owning-rack resolution is
ambiguous.

### ~~S5. Chain select zones~~ - DONE for chain zones; key/vel outstanding

**Live:** rack with two chains. Save `racks/s5_a.adg`. Drag one chain's chain-select zone. Save
`racks/s5_b.adg`. Repeat as `s5_key_*` for a key zone and `s5_vel_*` for a velocity zone.

**Done so far:** zone position. It is `BranchSelectorRange` on the chain, holding `Min`, `Max`,
`CrossfadeMin`, `CrossfadeMax` - absolute values on the chain selector's 0..127 scale, stored as
bounds rather than start+length. See `SCHEMA.md`.

**Chain zones are fully characterised** across three pairs - position (`s5_a`/`s5_b`), width
(`s5_len_a`/`s5_len_b`) and fade (`s5_fade_aa`/`s5_fade_bb`). Model and invariant in
`ARCHITECTURE.md` §7.

**Still outstanding:** key and velocity zones, which are Instrument Rack only. Save
`s5_key_a`/`s5_key_b` and `s5_vel_a`/`s5_vel_b` from an Instrument Rack with two chains, one drag
each. They are _presumed_ siblings of `BranchSelectorRange`; do not assume it in code until diffed.

UI note, since this cost time: fade handles are the small triangles at the zone rectangle's **top
corners**, and they do not render on a zero-width zone. Widen the zone first.

**Record:** how start, length and the two fade values are stored, and whether key/velocity/chain
zones are siblings of one structure. Note the units - raw semitones vs normalised.

### ~~S6. Id allocation and scope~~ - DONE

**Live:** rack with two chains. Save `racks/s6_a.adg`. Add one device to one chain. Save
`racks/s6_b.adg`.

**Run:**

```
patchbay ids racks/s6_a.adg
patchbay diff racks/s6_a.adg racks/s6_b.adg
```

**Downgraded, not cancelled.** S3 showed macro mappings carry no ids, so this no longer gates
Phase 2. It still governs any _other_ cross-reference in the format, so do it before `clone.py`
ships.

Note also that S2 already established ids do **not** churn across saves, and that preset files carry
`Id="0"` almost everywhere. The open part is what happens when a device is _added_.

`ids` tells you, per field, whether values are unique across the whole file (file-scoped, must
reallocate on clone) or repeat (narrower scope, must NOT reallocate). Getting this backwards is
landmine #1 in CLAUDE.md.

**Record:** for each of `Id`, `PointeeId`, `LomId`, `LomIdView` and anything else the census
surfaces - its scope, whether it is a definition or a reference, and what the new device's id was
relative to the existing maximum (sequential? max+1? reuses gaps?).

Then the destructive test: hand-edit an unpacked file to give two nodes the same id, repack, load in
Live. Record what Live actually does - refuses, silently cross-wires, or repairs. That failure mode
determines how loud `clone.py` has to be.

**Result: it refuses**, with a dialog. The rule is simply that an `Id` must be unique among its
siblings; gaps, out-of-range values and file-wide repetition are all fine, and nothing references
ids at all. See `ARCHITECTURE.md` §8.

Method note: the first collision file changed two things at once and had to be rebuilt split. The
one-change rule applies to constructed test files just as much as to saves from Live.

### ~~S7. FileRef anatomy~~ - DONE

**Live:** Simpler with a sample. Save `racks/s7_a.adg`. Swap the sample for a different one. Save
`racks/s7_b.adg`.

**Run:**

```
patchbay diff racks/s7_a.adg racks/s7_b.adg --grep FileRef
patchbay diff racks/s7_a.adg racks/s7_b.adg
```

The second command matters as much as the first: sample data outside FileRef (length, warp markers,
default slice points) also moves.

**Record:** every field, not only Path. Then the deliberate failure - rewrite _only_ the path in an
unpacked file, repack, load. Confirm what Live does. Expect offline.

**Result - and the expectation was wrong.** A path-only rewrite _works_.

20 facts move on a real swap, across **two** FileRefs plus frame-derived values outside them, but
six deliberately inconsistent variants all load: Live re-reads the sample file and recomputes its
metadata. Nothing validates `OriginalFileSize` or `OriginalCrc`. See `ARCHITECTURE.md` §10.

Practical upshot: `samples.py` rewrites two paths per sample. Everything else is optional hygiene,
and the CRC never needs computing.

One false start worth remembering: an intermediate variant appeared to fail, which fit a tidy
cache-key theory. It had been double-clicked instead of dragged. See the ground rule at the top of
this file.

### ~~S8. Macro variations~~ - DONE

**Live:** rack with a few macros. Save `racks/s8_a.adg`. Click New in the variations panel. Save
`racks/s8_b.adg`. Change macro values, click New again. Save `racks/s8_c.adg`.

**Record:** where variations live, whether stored values are absolute or normalised 0..1, where
names live, and whether variation order is positional.

**Result:** `MacroVariations/MacroSnapshots/MacroSnapshot[N]` on the rack device. Values are
**absolute on the macro 0..127 scale**, all 16 slots always written, participation carried by
`MacroHasValue.N` with `-1` as the unset value. Names in `SnapshotName`, order positional. See
`ARCHITECTURE.md` §11.

Note: the macro values chosen when clicking New do not need to be memorable. A snapshot can be
checked against the same file's live `MacroControls.N/Manual`, which is what proved the scale.

### ~~S9. Drum rack specifics~~ - DONE

**Live:** save a drum rack as `racks/s9_drum.adg` and an instrument rack as
`racks/s9_instrument.adg`.

**Run:** `patchbay diff racks/s9_instrument.adg racks/s9_drum.adg` - a big diff, read it for
structure not detail.

**Record:** how a pad maps to its receiving note, how return chains inside the drum rack are
represented, how per-chain send levels are stored.

**Done differently, and better:** rather than one huge drum-vs-instrument diff, this was four saves
with one change each - 2 pads, add a return, raise a send, move a pad. See `ARCHITECTURE.md` §12.

Two UI traps that cost time, worth knowing before repeating this:

- **`AreSendsVisible` defaults to `false`.** Per-pad send knobs are simply not in the chain list
  until that column is toggled on. There is nothing to drag until then.
- **"Create Chain" is not "Create Return Chain".** The former adds another pad. The return pane has
  to be visible (`IsReturnBranchesListVisible`), and the right-click must happen inside _that_ pane.

Adding a device brings its whole parameter blob into the diff - the Reverb on the return chain was
~800 facts. Use `-n` to cap it.

### ~~S10. Macro metadata~~ - DONE, except mapping range

Four separate one-change diffs from a common `racks/s10_a.adg`: rename a macro, set a custom min/max
range, toggle exclude from randomisation, change visible macro count 8 -> 16.

**Record:** one line each. The macro count one is the interesting one - note whether unused macros
are present-but-hidden or absent.

**Result:** present, not absent - all 16 slots exist in every family, and changing the count alters
exactly one fact. Each menu item maps to one field; see `ARCHITECTURE.md` §6 for the table.

Two things worth knowing before repeating this:

- Save from the **rack's** save button, not the device's. Two saves here came out as `.adv` device
  presets with no macro data in them.
- Live 12.4.3 has **no macro range editor** - not on the macro knob, not on the target parameter,
  not in Map mode. That part of the spike is still open, with a reverse test prepared at
  `build/s10_range_test.adg`.

### S11. .als track structure

Do after S1-S10. Live Set, not rack. Three separate diffs: change one track's Audio To; point a
compressor's sidechain at another track; compare a return track against a regular track.

**Record:** how routing targets are named - by id, by name, by index. This decides whether writing
the Set is viable or gets skipped.

**Dropped once, then run.** The reason for dropping it was that Live's API exposes
`create_audio_track`, `create_return_track`, `output_routing_type` and `output_routing_channel`,
verified against Live 12.4.3's own `_MxDCore/LomTypes.pyc`, so extending the remote script looked
smaller than reverse-engineering Set structure.

**What that missed:** a device reaches a track only through the browser, and the browser index is a
snapshot taken at startup, so a running Live cannot load a rack written after it launched. The API
could build the tracks and not fill them.

**Answered instead by Q9, Q30 and Q31.** Q9 mapped Set form to preset form for reading;
`live_set.py` runs the same map backwards, and the tracks, returns and branch shapes are templates
read from Live's own factory content rather than synthesised. `patchbay session` writes the Set.

Two things stay manual, and neither is a ratio argument: routing a track into another track has no
example in any of the 26 factory Sets, and a sidechain source is absent from the LOM and from preset
form both.

Both kill criteria passed, and all remaining spikes are answered or retired. **Phase 0 is
complete.**

### ~~S12. Minimal device viability~~ - DONE

**Live:** save any donor device.

**Then:** unpack, delete a handful of parameter nodes, repack, load. Binary search until you know
whether Live tolerates partial devices.

**Record:** the answer decides how load bearing the donor pattern is. If Live demands the full blob,
donors are mandatory and generating device XML is off the table permanently.

**Result: a device loads with all 18 of its parameters deleted.** Live defaults whatever is absent.
Donors are therefore about _fidelity_, not loadability - they carry a configured device, saving us
from knowing every parameter name and default. Generators may write partial device nodes.

### ~~S13. Nested racks~~ - DONE

Not planned. It came out of Q1b, which had been open with everything checkable looking correct.

**Method, and it is the point of this entry:** build the SAME rack twice, changing only which
`GroupDevicePreset` is harvested as the skeleton - top level from `racks/s7_a.adg`, nested from
`racks/s1_source.adg`. Then diff. Three facts came back where the earlier comparison had produced
hundreds.

**Result:** a top-level `GroupDevicePreset` carries no attributes and a nested one carries an `Id`.
Confirmed by one change in Live: `build/probe_b_toplevel.adg` loads, the same file plus `Id="0"` is
refused as a drop. Evidence in `SCHEMA.md` S13, model in `ARCHITECTURE.md` §3.

The one-change rule applies to which FILES you compare, not only to what you change inside one. A
diff too big to read is a badly chosen pair.


## Evidence Files (s*, q*)


Every **[V]** claim above traces to these files, all in `racks/`.

| file                                                  | what it is                                                                                                                     | establishes                                                                       |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| `s1_source.adg`                                       | AlienMind Drum Rack, 560 KB, 18,148 facts, 3 nesting levels, 3 mappings                                                        | round trip, DR1 nesting, macro-to-macro, ChainSelector mapping                    |
| `q32_set.als`                                         | a Set Live saved: 2 MIDI tracks, 1 audio, 2 returns, 3 of our racks placed, one track routed into another, one sidechain wired | Q33, Q35, Q36, Q37, Q38, Q39 - every Set-form finding the log could not name      |
| `s2_a.adg` / `s2_b.adg`                               | same rack saved twice, no edits                                                                                                | noise floor, id stability, `RoundRobinRandomSeed`, `PresetRef`                    |
| `s3_a.adg` / `s3_b.adg`                               | Audio Effect Rack + Saturator, before/after mapping Drive to Macro 1                                                           | the entire `KeyMidi` mechanism                                                    |
| `s3b.adg`                                             | same rack, Output additionally mapped to Macro 2, both macros moved                                                            | `NoteOrController` = macro index; the transfer function; `MacroDefaults` sentinel |
| `s5_a.adg` / `s5_b.adg`                               | two-chain Audio Effect Rack, one chain's zone dragged 0 -> 8                                                                   | `BranchSelectorRange`                                                             |
| `s5_len_a.adg` / `s5_len_b.adg`                       | same rack, zone right edge 16 -> 40                                                                                            | `Crossfade*` are absolute positions                                               |
| `s5_fade_aa.adg` / `s5_fade_bb.adg`                   | same rack, left fade handle dragged inward                                                                                     | fades grow inward; the ordering invariant                                         |
| `s7_a.adg` / `s7_b.adg`                               | Instrument Rack + Simpler, one sample swapped                                                                                  | the 20 facts a swap moves; two FileRefs                                           |
| `s8_a/b/c.adg`                                        | same rack with 0, 1 and 2 macro variations                                                                                     | the `MacroSnapshot` structure                                                     |
| `s9_a/b/c/d.adg`                                      | drum rack: 2 pads, then a return, then a send raised, then a pad moved                                                         | `ZoneSettings`, `ReturnBranchPresets`, `SendInfos`                                |
| `s10_c..g.adg`                                        | one macro-metadata change per save                                                                                             | each `.N` family, `NumVisibleMacroControls`                                       |
| `q3_a.adg` / `q3_b.adg`                               | two-chain Instrument Rack, split first by key then by velocity                                                                 | `ZoneSettings/KeyRange`, `/VelocityRange`                                         |
| `q7_c.adg`                                            | `build/Q7_bad_zone.adg` dragged back out of Live                                                                               | an inverted zone is repaired by clamping                                          |
| `q20_a..d.adg`                                        | one `MidiScale` saved at four scale settings                                                                                   | `Base`, `InternalScale`, `UseCurrentScale`                                        |
| `q21_hp.adg` / `q21_bell.adg`                         | one `Eq8`, band 1 high-pass then bell                                                                                          | the band `Mode` enum, per band                                                    |
| `build/s10_range_test.adg`                            | Drive's `MidiControllerRange/Max` set to 12                                                                                    | mapping ranges are `MidiControllerRange`                                          |
| `build/s6_*.adg`                                      | duplicate vs merely-gapped ids                                                                                                 | siblings must be unique; value is free                                            |
| `build/s12_*.adg`                                     | 1, 5, 9 and all 18 parameters deleted                                                                                          | devices may be partial                                                            |
| `build/s7_test_A..F.adg`                              | six deliberately inconsistent retargets, all loaded in Live                                                                    | the cache-key model                                                               |
| `build/PD1.adg`                                       | 96 variations over four slots, one being the engine                                                                            | variations load and recall; a variation may drive `ChainSelector`                 |
| `build/probe_q4_256.adg`                              | 256 variations, count the only difference from PD1                                                                             | no snapshot ceiling at 256                                                        |
| `build/probe_q5_unmapped.adg`                         | one variation flagging an unmapped macro                                                                                       | accepted on load, inert on recall                                                 |
| `build/probe_b_toplevel.adg` / `probe_c_id_added.adg` | one rack, differing only by `Id` on the top-level preset                                                                       | a top-level `GroupDevicePreset` must carry no `Id`                                |
| `build/VA1.adg`                                       | two levels of nesting, written from scratch                                                                                    | a rack Live never saved survives being nested; macro-to-macro drives              |

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
