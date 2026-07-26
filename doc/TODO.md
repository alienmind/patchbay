# TODO - the live backlog

The only place that says what is in flight. Everything else in `doc/` is
settled knowledge.

Work happens HERE: pick a task, move it to In progress, update its status
as you go. When it is done, it leaves this file. It does not stay as a
completed entry. See "The routine" at the bottom.

Live version for every finding below: **12.4.3**.

## Status

Phase 0 discovery is closed: 12 spikes answered, 1 retired, both kill
criteria passed. What the format does is in `ARCHITECTURE.md`, each claim
marked verified, inferred or open and traced to a file in `racks/`.

The end-to-end chain has passed its gate in Live: a rack declared in
`examples/patchbayground.py`, compiled with `patchbay build`, dropped on a
MIDI track, one grammar driving two synthesis engines, 96 variations
recalling.

## In progress

Nothing. Pick from Next.

## Next

**T1. Nested racks.** The DSL cannot write a `GroupDevicePreset` into
another rack's `DevicePresets`. DR1 needs three levels. The structure is
known from S4; what is unknown is whether a rack Live never saved itself
survives being nested. Build it, then gate it in Live, and confirm
macro-to-macro mappings still drive.
*Blocks: DR1, VA1, VA2.*

**T2. Why a nested rack cannot be lifted out** (`SPIKES.md` Q1b). A
`GroupDevicePreset` taken from inside another rack's chain, wrapped in a
fresh `<Ableton>` root and saved, produces a file Live refuses as a drop.
It never gets as far as loading. Everything checkable looks correct: same
top-level children as a working rack, same `PresetRef` shape with the
right `DeviceId`, no sibling id collisions, no parent-referencing state in
`LastPresetRef`, `SourceContext`, `LockId` or `LockSeal`.

Evidence: `build/probe_a_extracted.adg` refuses to drag,
`build/probe_b_audio.adg` from the same code on a top-level skeleton drags
onto both track types.

Workaround in place: the DSL accepts only a top-level rack as a skeleton
and raises otherwise. Diff a hand-built nested rack against a Live-saved
one to find the difference.
*Coupled to T1: the same sensitivity may block writing racks INTO chains.*

**T3. Sample retargeting** (KICKOFF Phase 3). Much smaller than budgeted:
S7 showed Live re-reads sample metadata on load, so only the two path
fields on each of a sample's two FileRefs are required. Belongs in the DSL
as a binding, not a separate module.
*Gate: eight pads, eight samples, none offline.*

**T4. Extend the `ableton-mcp` remote script** (KICKOFF Phase 6, revised).
`create_audio_track`, `create_return_track` and an output-routing setter
are all in the LOM and simply not wired up. A handful of command handlers
in a file that already has twenty. Then drive it to build the eight
tracks, returns, routing, tempo and starter clips, loading each generated
rack by browser URI. See `MCP.md`.

**T5. MCP smoke test.** `patchbay` generates a rack, MCP loads it onto a
track, `get_track_info` confirms the expected device tree appeared. Catches
gross failures without a human dragging files. It cannot confirm macros are
mapped correctly, `mapped_parameter` does not exist, so that check stays
manual.

## Open spikes

None is a kill criterion. The project works without any of them.

**Q2. Aftertouch.** `PATCHBAYGROUND.md` wants aftertouch on filter and
pitch for every sound, excluding drum pads. Nothing is known about how it
is stored. Probably a sibling of the `KeyMidi` mechanism, since that
already encodes MIDI, but that is a guess. Diff a rack before and after
mapping aftertouch to one parameter.
*Blocks: the macro grammar being complete.*

**Q3. Key and velocity zones.** S5 settled chain-select zones. Key and
velocity zones are Instrument Rack only and are PRESUMED siblings of
`BranchSelectorRange`. Do not assume it in code until diffed. Save an
instrument rack with two chains, drag a key zone, then a velocity zone,
one save each: `s5_key_a`/`s5_key_b`, `s5_vel_a`/`s5_vel_b`.
*Blocks: multi-sampled racks.*

**Q6. Drum rack return selectors.** `PATCHBAYGROUND.md` wants each DR1
return chain to hold a selector across several reverbs and delays, so a
macro swaps the EFFECT rather than the send level. The pieces are known
separately, the combination is untested.

**Q7. Zone ordering violations.** `Min <= XfMin <= XfMax <= Max` is the
invariant. Untested whether Live repairs or rejects a file that breaks it.
Worth knowing before a generator produces one by arithmetic error.

**Q8. Send taper.** Sends are linear amplitude from 0.000316 to 1, but
whether the knob is linear in amplitude or in dB is unknown. Only matters
if a spec ever states send levels as knob percentages.

**S10 tail. Macro mapping range from the UI.** Live 12.4.3 has no macro
range editor, so the reverse test at `build/s10_range_test.adg` is prepared
and unrun: write a narrowed `MidiControllerRange`, load it, and see what
the UI shows.

**Q5 tail.** Whether Live keeps or strips `MacroHasValue.N` on an unmapped
macro. Save `build/probe_q5_unmapped.adg` back out of Live and diff. Cheap,
and nothing depends on it.

## Standing manual work

Not backlog. These do not get automated, and trying is how the project
fails.

- Choosing which samples are good. A generator cannot judge a kick.
- Sound design judgement. Generate wide, audition, cull.
- Gain staging and mix balance.
- Sidechain source. Absent from the LOM and not found in the file format.
  One setting per track, not a system. See `THE_BASEMENT.md`.
- Confirming macros are mapped correctly. No API reads mappings.

Semi-automated, worth designing well: sample assignment (curation manual,
wiring automatic, a pad-to-path manifest between them) and variation
culling (generated names encoding parameter values make culling informed).

## Definition of done

`patchbay build` plus a driven `ableton-mcp` session produces a Set that
opens in Live 12, with eight correctly named and routed tracks, racks whose
macros follow the grammar in `PATCHBAYGROUND.md`, playable from Push 3
without touching a mouse.

## The routine

1. Work a task from this file. Keep its status current here while it moves.
2. When it lands, DELETE it from this file and put what was learned in its
   permanent home:
   - a capability a user would want to know about: `README.md`
   - how the format works: `ARCHITECTURE.md`, with the evidence in
     `SCHEMA.md`
   - a shape decision about the DSL: `DSL.md`
   - an idea that did not work, an approach abandoned, a theory disproved:
     `THE_BASEMENT.md`
3. A task leaves this file exactly once, in exactly one direction. Nothing
   is archived in place, and no completed entries accumulate here.
