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

Nesting has passed the same gate. `build/VA1.adg` is two levels written
from scratch, with macros chaining into whichever sub-rack is selected.
DR1's remaining blockers are the pad side, not the nesting.

## In progress

Nothing. Pick from Next.

## Next

**T1. Drum rack pads in the DSL.** What DR1 still needs now that nesting
is done. `clone.py` already sets `ReceivingNote` and allocates free notes,
and `Rack.nest` already puts a rack inside a chain; nothing joins them up.
A drum rack declares pads by note rather than chains by zone, so
`RackKind.DRUM` needs a pad-shaped entry point rather than `engine`, and
zone distribution does not apply to a pad.
*Blocks: DR1. Wants T3 for the samples and Q6 for the return selectors.*

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

**T6. Decompile a saved rack into DSL source.** Turn racks built by hand
in Live into `Rack(...)` declarations, so a library of real racks becomes
declarable input instead of something to retype. This is `patchbay build`
run backwards.

*Not blocked on any external library.* `io.load` already opens `.adg`,
`.adv` and `.als`, because all three are gzipped XML and that is 17 lines.
`find.py` already walks a preset tree. What is missing is an emitter, and
no third party has one, because the DSL is ours. See `THE_BASEMENT.md` for
why ableton-inspector does not help here.

Four steps, each with its own gate. Do them in order; the first is the
whole value and the last is optional.

**T6a. Emit DSL from a `.adg`.** New module `patchbay/extract.py`, new CLI
verb `patchbay extract <file.adg>`, printing Python to stdout. Walk the
preset tree with `find.py` and emit, per rack:

- `Rack(name, grammar, kind=...)` from the rack tag, mapping
  `InstrumentGroupDevice` to `RackKind.INSTRUMENT` and so on
- one `rack.engine(chain_name, device_type)` per chain, in `BranchPresets`
  order, with the device type read off the wrapped device node
- `e.bind(slot=path)` per macro mapping, using `mappings.py`, which already
  finds `KeyMidi` targets and knows the CC number IS the macro index
- `e.zone(min, max)` where a chain's zone is not the full range
- `rack.variations(...)` from the snapshot data `variations.py` reads
- `rack.nest(...)` where a chain contains a rack rather than a device,
  recursing

*Gate, and it is a strong one:* extract `racks/s1_source.adg`, run the
emitted source through `patchbay build`, then `patchbay diff` the result
against the original. Three levels of nesting and real macro chaining make
it the hardest rack we have. Differences are allowed only in the fields
`ARCHITECTURE.md` already lists as per-save churn.

**T6b. Name the slots.** A decompiler recovers STRUCTURE, not INTENT. It
can see that macro 2 drives `Filter/Frequency` on three chains; it cannot
know that we call slot 2 `Cutoff`. Two halves:

- emit a positional grammar by default, `Grammar("Macro 1", "Macro 2", ...)`,
  which is honest and immediately compiles
- offer `--grammar patchbayground` to match extracted mappings against an
  existing grammar's bindings and use its names where a parameter path
  agrees, leaving the rest positional

Renaming stays a human edit. Do not guess a slot name from a parameter
path; that is inventing intent, and `CLAUDE.md` rule 1 applies.

**T6c. Locate racks inside a `.als`.** Only now, because it is the part
that needs a spike first and T6a is useful without it.

*Q9, and it must come first.* A `.adg` stores a rack in PRESET form:
`GroupDevicePreset` with `Device` and `BranchPresets` as siblings. A `.als`
stores the same rack in LIVE form, inside
`LiveSet/Tracks/*/DeviceChain/DeviceChain/Devices`. Whether chains are
serialised identically in both is UNKNOWN and must not be assumed. Method:
build one two-chain rack, save it as `racks/q9_a.adg` by dragging to the
browser, save the Set containing that same rack as `racks/q9_b.als`,
unpack both and diff by hand. Write the mapping in `SCHEMA.md`.

Then `patchbay extract <file.als>` walks tracks, finds rack nodes in each
device chain, lifts each into preset form, and reuses all of T6a. Note
S13: a lifted subtree must have its `Id` stripped, and a top-level
`GroupDevicePreset` must carry no attributes at all.

*Gate:* extract every rack from a Set, rebuild each, diff each.

**T6d. Batch it.** `patchbay extract --out lib/ <file.als>` writing one
module per rack plus an index. Trivial once T6c works, and worth nothing
until then.

**Cheaper path that needs none of T6c.** Dragging a rack from a Live Set
into the browser saves a `.adg`. If the library is tens of racks rather
than hundreds, hand-dragging plus T6a gets there without the spike.

**What this will not recover:** slot names, why a range was chosen, which
sample a `FileRef` was meant to point at once it moves, and anything Live
regenerates per save. Extraction gives a skeleton that compiles and
matches. It does not give a spec someone would have written by hand.

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
