# Spikes

How this project learns anything about the file format, and what is still
unknown.

Findings go in `SCHEMA.md`. The consolidated model is `ARCHITECTURE.md`.
This file is the procedure and the open list.

## Phase 0 is closed

Twelve spikes answered, one retired. Both kill criteria passed. Every
verified claim in `ARCHITECTURE.md` traces to a file in `racks/`.

| | spike | result |
|---|---|---|
| S1 | round trip fidelity | lossless; Live tolerates lxml's serialiser |
| S2 | noise floor | zero after filtering; ids do NOT churn |
| S3 | macro mapping | `KeyMidi` in the target, virtual MIDI CC channel 16 |
| S3b | macro index | CC number is the zero-based macro index |
| S4 | macro to macro | identical structure, three levels verified |
| S5 | chain zones | `BranchSelectorRange`, bounds, fades grow inward |
| S6 | id allocation | unique among SIBLINGS, nothing else matters |
| S7 | FileRef | two per sample; only the paths are required |
| S8 | macro variations | `MacroSnapshot` list, absolute 0..127 |
| S9 | drum racks | `ReceivingNote`, `ReturnBranchPresets`, `SendInfos` |
| S10 | macro metadata | one field per menu item; ranges are `MidiControllerRange` |
| S12 | minimal devices | load with ALL parameters deleted |
| S11 | `.als` structure | RETIRED. Live's API does tracks and routing, see `MCP.md` |

## Open questions

Ordered by what they block. None is a kill criterion; the project works
without any of them.

**Q1. Rack inside a chain.** DR1 needs three levels of nesting and the
structure is known, but the DSL cannot yet write a `GroupDevicePreset`
into another rack's `DevicePresets`. This is a build task with a spike
attached: confirm a generated nested rack loads and that macro-to-macro
mappings survive being written rather than saved by Live.
*Blocks: DR1, VA1, VA2.*

**Q1b. Why a nested rack cannot be lifted out.** A `GroupDevicePreset`
taken from inside another rack's chain, wrapped in a fresh `<Ableton>`
root and saved, produces a file Live REFUSES TO ACCEPT AS A DROP. It never
gets as far as loading.

Everything checkable looks correct: same top-level children as a working
rack, same `PresetRef` shape with the right `DeviceId`, no sibling id
collisions, no parent-referencing state in `LastPresetRef`,
`SourceContext`, `LockId` or `LockSeal`.

Evidence: `build/probe_a_extracted.adg` refuses to drag, while
`build/probe_b_audio.adg` built by the same code from a top-level skeleton
drags onto both track types.

This matters beyond skeletons: DR1 needs racks nested INTO chains, and if
Live is sensitive to something about a nested rack's serialisation then
writing one may hit the same wall. Diff a hand-built nested rack against a
Live-saved one to find it.

*Workaround in place:* the DSL now only accepts a top-level rack as a
skeleton and raises otherwise, rather than silently producing a file that
cannot be loaded.

**Q2. Aftertouch.** `TEMPLATE_SPEC.md` wants aftertouch mapped to filter
and pitch on every sound, excluding drum pads. Nothing is known about how
that is stored. It is probably a sibling of the `KeyMidi` mechanism, since
that already encodes MIDI, but that is a guess.
Diff a rack before and after mapping aftertouch to one parameter.
*Blocks: the macro grammar being complete.*

**Q3. Key and velocity zones.** S5 settled chain-select zones. Key and
velocity zones are Instrument Rack only and are PRESUMED siblings of
`BranchSelectorRange`. Do not assume it in code until diffed.
Save an instrument rack with two chains, drag a key zone, then a velocity
zone, one save each.
*Blocks: multi-sampled racks.*

**Q4. Variation limits and naming.** How many `MacroSnapshot` entries will
Live accept, and does it truncate or reject beyond that? ~692 sounds
across 18 engines means tens of variations per rack, and nothing yet says
where the ceiling is.
Generate 8, 64 and 256 variations and load each.
*Blocks: knowing whether the variation grid needs chunking.*

**Q5. Unmapped macros in a variation.** Can `MacroHasValue.N` be true for
a macro that has no mapping? Only mapped macros were flagged in the sample.
Minor, but it decides whether a generator writes participation per macro
or per binding.

**Q6. Drum rack return selectors.** `TEMPLATE_SPEC.md` wants each DR1
return chain to hold a selector across several reverbs and delays, so a
macro swaps the EFFECT rather than the send level. The pieces are known
separately; the combination is untested.

**Q7. Zone ordering violations.** `Min <= XfMin <= XfMax <= Max` is the
invariant. Untested whether Live repairs or rejects a file that breaks it.
Worth knowing before a generator can produce one by arithmetic error.

**Q8. Send taper.** Sends are linear amplitude from 0.000316 to 1, but
whether the knob is linear in amplitude or in dB is unknown. Only matters
if a spec ever states send levels as knob percentages.

## Retired

**Sidechain source.** Absent from the Live Object Model AND not yet found
in the file format. `TEMPLATE_SPEC.md` needs it for DR1. It stays manual,
which `KICKOFF.md` prices at one afternoon. Revisit only if that proves
annoying in practice.

**`OriginalCrc` algorithm.** 16-bit, and zlib plus ten CRC-16 variants
over four chunk choices all missed. Closed as irrelevant: nothing reads it
on load.

## Ground rules

- **Load-test by dragging the file into a running Live instance.**
  Double-clicking an `.adg` starts a *second* Live, which hangs for a few
  seconds and loads nothing - indistinguishable from Live rejecting the
  file, and it has already produced one wrong conclusion. Live's log at
  `%APPDATA%/Ableton/Live <version>/Preferences/Log.txt` settles which
  happened: grep for `CommandLine` and `Another instance`.
- Every spike is: save `a`, change **exactly one thing**, save `b`, diff.
  Two changes in one diff wastes the spike, because you cannot tell which
  node belongs to which change.
- Save every pair into `racks/`, named `s3_a.adg` / `s3_b.adg` etc, so the
  evidence survives. `racks/` is an asset, not scratch.
- Record the exact Live version once, at the top of `SCHEMA.md`.
  (Live > About Live.) The schema is version specific.
- If a diff comes back with dozens of changes, you changed more than one
  thing, or the noise floor (S2) is worse than assumed. Do S2 first.

## Order

Original plan: S1, S2, S3 first (kill criteria), then S6 to decide whether
cloning is viable, then the rest, S11 last.

**Revised after S3.** Mappings turned out to be containment-addressed, not
id-addressed, so cloning does not depend on id hygiene for macros and S6
stopped being a gate. Remaining order:

1. **S3b** - confirm the macro index encoding. One diff, and everything in
   Phase 2 rests on it.
2. **S5, S7, S10** - feed Phases 3 and 4.
3. **S8** - feeds Phase 5, the highest-value module.
4. **S9, S12** - fill in the drum rack and donor details.
5. **S6** - still worth doing before `clone.py` ships, for non-macro
   references.
6. **S11** - last, and skippable per KICKOFF's fallback.

---

## ~~S1. Round trip fidelity~~ - DONE, PASSED (kill criterion)

**Live:** save any real rack (the more complex the better) as
`racks/s1_source.adg`.

**Run:**
```
patchbay roundtrip racks/s1_source.adg
```

**Then:** drag `racks/s1_source.roundtrip.adg` into Live.

Pass = it opens and behaves identically. `structurally identical: YES`
with differing bytes is expected (lxml's serialiser is not Live's) and is
fine *provided Live opens it*. Only Live's opinion counts.

If it fails: stop. Do not proceed. The likely culprits are the XML
declaration, encoding, or self-closing tag style in `io.save`.

## ~~S2. Noise floor~~ - DONE, PASSED

**Live:** open a rack, save as `racks/s2_a.adg`. Change nothing at all.
Save again as `racks/s2_b.adg`.

**Run:**
```
patchbay diff racks/s2_a.adg racks/s2_b.adg
patchbay diff racks/s2_a.adg racks/s2_b.adg --all
```

**Record:** anything the first command shows is noise the filter does not
yet catch; add its field name to `SAVE_NOISE` in `patchbay/diff.py` and note
why in `SCHEMA.md`. The second shows what is already filtered.

Ideal result: first command prints `identical`.

**Done for Live 12.4.3 - see SCHEMA.md.** Floor is zero after adding
`RoundRobinRandomSeed` and the `PresetRef` paths to the filter. Ids were
found *not* to churn, so they are now shown by default. Re-run this spike
after any Live update.

## ~~S3. Macro mapping~~ - DONE, PASSED (kill criterion)

**Live:** rack with one device, no macro mapped. Save `racks/s3_a.adg`.
Map Macro 1 to one device parameter. Change nothing else - not the macro
value, not the name. Save `racks/s3_b.adg`.

**Run:**
```
patchbay diff racks/s3_a.adg racks/s3_b.adg
```

**Record in SCHEMA.md:** the node that appeared, and critically *how it
names its target* - by id, by path, or by index. Quote the actual XML of
the added subtree (`patchbay unpack` then find it).

If the target is addressed by an id, S6 becomes load bearing.
If it is addressed positionally, cloning gets easier and remapping gets
harder.

**Result: neither.** The target is addressed by **containment** - the
mapping is a `KeyMidi` element inside the target parameter, encoding a
virtual MIDI CC. No id, no path, no index into a table. See
`ARCHITECTURE.md` §5 for the full mechanism and `SCHEMA.md` for evidence.

Consequence: S6 is **not** load bearing for macro mappings, and cloning
may copy `KeyMidi` blocks verbatim.

Caution for whoever repeats this: the first read of this diff wrongly
concluded no mapping was present, because `KeyMidi` looks like inert MIDI
defaults. It is the finding.

## ~~S3b. Macro index confirmation~~ - DONE, CONFIRMED

Small but load bearing. Every mapping observed so far targets Macro 1
(`NoteOrController = 0`), so "CC number = zero-based macro index" is
inference, not fact.

**Live:** take `racks/s3_b.adg` (Saturator, Drive mapped to Macro 1).
Map a *second* parameter - Saturator's **Output** - to **Macro 2**.
Save as `racks/s3b.adg`.

**Run:**
```
patchbay diff racks/s3_b.adg racks/s3b.adg
patchbay mappings racks/s3b.adg
```

**Expected:** a second `KeyMidi`, on the Output parameter, with
`NoteOrController = 1` and `Channel = 16`. `patchbay mappings` should then
report `Macro 1 -> PreDrive` and `Macro 2 -> <output param>`.

**If instead** `NoteOrController` is 2, or the channel changes, or the
index turns out to be 1-based, fix the mapping model in
`ARCHITECTURE.md` §5 and the `macro` calculation in
`patchbay/mappings.py` before any generator is written.

**Result: confirmed.** `PostDrive` (Saturator's Output) got
`NoteOrController=1`, `Channel=16`. The mapping model in
`ARCHITECTURE.md` §5 stands as written.

Two extras came free: the **macro to parameter transfer function** (linear
over the target's `MidiControllerRange`, see ARCHITECTURE §5), and
`MacroDefaults.N` using `-1` as an unset sentinel - with an anomaly now
tracked under S10.

## ~~S4. Macro to macro~~ - DONE, answered by S3 evidence

**Live:** rack containing a rack. Save `racks/s4_a.adg`. Map the outer
rack's Macro 1 to the inner rack's Macro 1. Save `racks/s4_b.adg`.

**Run:** same two commands.

**Record:** whether the added node is the same shape as S3's or a
different type. DR1 needs three levels of this, so also note whether the
depth appears anywhere in the encoding.

**Result: no separate spike needed.** `racks/s1_source.adg` already
contains three levels of macro-to-macro chaining, found by
`patchbay mappings`. The structure is **identical** to S3 - a `KeyMidi` on
the inner rack's `MacroControls.N`, which is just another parameter node.
`Channel` stays 16 at every depth, so nesting is not encoded in the
mapping at all; it is purely structural.

`ChainSelector` is mappable the same way.

Re-run this spike properly only if a case appears where the implicit
owning-rack resolution is ambiguous.

## ~~S5. Chain select zones~~ - DONE for chain zones; key/vel outstanding

**Live:** rack with two chains. Save `racks/s5_a.adg`. Drag one chain's
chain-select zone. Save `racks/s5_b.adg`. Repeat as `s5_key_*` for a key
zone and `s5_vel_*` for a velocity zone.

**Done so far:** zone position. It is `BranchSelectorRange` on the chain,
holding `Min`, `Max`, `CrossfadeMin`, `CrossfadeMax` - absolute values on
the chain selector's 0..127 scale, stored as bounds rather than
start+length. See `SCHEMA.md`.

**Chain zones are fully characterised** across three pairs - position
(`s5_a`/`s5_b`), width (`s5_len_a`/`s5_len_b`) and fade
(`s5_fade_aa`/`s5_fade_bb`). Model and invariant in `ARCHITECTURE.md` §7.

**Still outstanding:** key and velocity zones, which are Instrument Rack
only. Save `s5_key_a`/`s5_key_b` and `s5_vel_a`/`s5_vel_b` from an
Instrument Rack with two chains, one drag each. They are *presumed*
siblings of `BranchSelectorRange`; do not assume it in code until diffed.

UI note, since this cost time: fade handles are the small triangles at the
zone rectangle's **top corners**, and they do not render on a zero-width
zone. Widen the zone first.

**Record:** how start, length and the two fade values are stored, and
whether key/velocity/chain zones are siblings of one structure. Note the
units - raw semitones vs normalised.

## ~~S6. Id allocation and scope~~ - DONE

**Live:** rack with two chains. Save `racks/s6_a.adg`. Add one device to
one chain. Save `racks/s6_b.adg`.

**Run:**
```
patchbay ids racks/s6_a.adg
patchbay diff racks/s6_a.adg racks/s6_b.adg
```

**Downgraded, not cancelled.** S3 showed macro mappings carry no ids, so
this no longer gates Phase 2. It still governs any *other* cross-reference
in the format, so do it before `clone.py` ships.

Note also that S2 already established ids do **not** churn across saves,
and that preset files carry `Id="0"` almost everywhere. The open part is
what happens when a device is *added*.

`ids` tells you, per field, whether values are unique across the whole
file (file-scoped, must reallocate on clone) or repeat (narrower scope,
must NOT reallocate). Getting this backwards is landmine #1 in CLAUDE.md.

**Record:** for each of `Id`, `PointeeId`, `LomId`, `LomIdView` and
anything else the census surfaces - its scope, whether it is a definition
or a reference, and what the new device's id was relative to the existing
maximum (sequential? max+1? reuses gaps?).

Then the destructive test: hand-edit an unpacked file to give two nodes
the same id, repack, load in Live. Record what Live actually does -
refuses, silently cross-wires, or repairs. That failure mode determines
how loud `clone.py` has to be.

**Result: it refuses**, with a dialog. The rule is simply that an `Id` must
be unique among its siblings; gaps, out-of-range values and file-wide
repetition are all fine, and nothing references ids at all. See
`ARCHITECTURE.md` §8.

Method note: the first collision file changed two things at once and had to
be rebuilt split. The one-change rule applies to constructed test files
just as much as to saves from Live.

## ~~S7. FileRef anatomy~~ - DONE

**Live:** Simpler with a sample. Save `racks/s7_a.adg`. Swap the sample
for a different one. Save `racks/s7_b.adg`.

**Run:**
```
patchbay diff racks/s7_a.adg racks/s7_b.adg --grep FileRef
patchbay diff racks/s7_a.adg racks/s7_b.adg
```

The second command matters as much as the first: sample data outside
FileRef (length, warp markers, default slice points) also moves.

**Record:** every field, not only Path. Then the deliberate failure -
rewrite *only* the path in an unpacked file, repack, load. Confirm what
Live does. Expect offline.

**Result - and the expectation was wrong.** A path-only rewrite *works*.

20 facts move on a real swap, across **two** FileRefs plus frame-derived
values outside them, but six deliberately inconsistent variants all load:
Live re-reads the sample file and recomputes its metadata. Nothing
validates `OriginalFileSize` or `OriginalCrc`. See `ARCHITECTURE.md` §10.

Practical upshot: `samples.py` rewrites two paths per sample. Everything
else is optional hygiene, and the CRC never needs computing.

One false start worth remembering: an intermediate variant appeared to
fail, which fit a tidy cache-key theory. It had been double-clicked instead
of dragged. See the ground rule at the top of this file.

## ~~S8. Macro variations~~ - DONE

**Live:** rack with a few macros. Save `racks/s8_a.adg`. Click New in the
variations panel. Save `racks/s8_b.adg`. Change macro values, click New
again. Save `racks/s8_c.adg`.

**Record:** where variations live, whether stored values are absolute or
normalised 0..1, where names live, and whether variation order is
positional.

**Result:** `MacroVariations/MacroSnapshots/MacroSnapshot[N]` on the rack
device. Values are **absolute on the macro 0..127 scale**, all 16 slots
always written, participation carried by `MacroHasValue.N` with `-1` as
the unset value. Names in `SnapshotName`, order positional. See
`ARCHITECTURE.md` §11.

Note: the macro values chosen when clicking New do not need to be
memorable. A snapshot can be checked against the same file's live
`MacroControls.N/Manual`, which is what proved the scale.

## ~~S9. Drum rack specifics~~ - DONE

**Live:** save a drum rack as `racks/s9_drum.adg` and an instrument rack
as `racks/s9_instrument.adg`.

**Run:** `patchbay diff racks/s9_instrument.adg racks/s9_drum.adg` - a big
diff, read it for structure not detail.

**Record:** how a pad maps to its receiving note, how return chains inside
the drum rack are represented, how per-chain send levels are stored.

**Done differently, and better:** rather than one huge drum-vs-instrument
diff, this was four saves with one change each - 2 pads, add a return, raise
a send, move a pad. See `ARCHITECTURE.md` §12.

Two UI traps that cost time, worth knowing before repeating this:

- **`AreSendsVisible` defaults to `false`.** Per-pad send knobs are simply
  not in the chain list until that column is toggled on. There is nothing
  to drag until then.
- **"Create Chain" is not "Create Return Chain".** The former adds another
  pad. The return pane has to be visible
  (`IsReturnBranchesListVisible`), and the right-click must happen inside
  *that* pane.

Adding a device brings its whole parameter blob into the diff - the Reverb
on the return chain was ~800 facts. Use `-n` to cap it.

## ~~S10. Macro metadata~~ - DONE, except mapping range

Four separate one-change diffs from a common `racks/s10_a.adg`:
rename a macro, set a custom min/max range, toggle exclude from
randomisation, change visible macro count 8 -> 16.

**Record:** one line each. The macro count one is the interesting one -
note whether unused macros are present-but-hidden or absent.

**Result:** present, not absent - all 16 slots exist in every family, and
changing the count alters exactly one fact. Each menu item maps to one
field; see `ARCHITECTURE.md` §6 for the table.

Two things worth knowing before repeating this:

- Save from the **rack's** save button, not the device's. Two saves here
  came out as `.adv` device presets with no macro data in them.
- Live 12.4.3 has **no macro range editor** - not on the macro knob, not
  on the target parameter, not in Map mode. That part of the spike is
  still open, with a reverse test prepared at `build/s10_range_test.adg`.

## S11. .als track structure

Do after S1-S10. Live Set, not rack. Three separate diffs:
change one track's Audio To; point a compressor's sidechain at another
track; compare a return track against a regular track.

**Record:** how routing targets are named - by id, by name, by index.
This decides whether Phase 6 is viable or gets skipped per KICKOFF's
fallback.

**Dropped, and the reason is better than the fallback.** Live's API *does*
expose `create_audio_track`, `create_return_track`, `output_routing_type`
and `output_routing_channel` - verified against Live 12.4.3's own
`_MxDCore/LomTypes.pyc`. The `ableton-mcp` submodule simply has not wired
them up.

So there is no reason to reverse-engineer Set structure: adding a few
command handlers to the remote script is smaller work and survives Live
updates, which `.als` generation would not. See `MCP.md`.

Sidechain source is the one exception - absent from the LOM - and stays
manual.

Both kill criteria passed, and all remaining spikes are answered or
retired. **Phase 0 is complete.**

## ~~S12. Minimal device viability~~ - DONE

**Live:** save any donor device.

**Then:** unpack, delete a handful of parameter nodes, repack, load.
Binary search until you know whether Live tolerates partial devices.

**Record:** the answer decides how load bearing the donor pattern is. If
Live demands the full blob, donors are mandatory and generating device
XML is off the table permanently.

**Result: a device loads with all 18 of its parameters deleted.** Live
defaults whatever is absent. Donors are therefore about *fidelity*, not
loadability - they carry a configured device, saving us from knowing every
parameter name and default. Generators may write partial device nodes.
