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

The eight slot grammar in `PATCHBAYGROUND.md` is what the code declares
and is gated in Live 12.4.3 on both racks, ranges included. Donors for
Wavetable, Drift and Meld are harvested and their bindings measured, so
BS1, LD1 and PD1 proper are blocked on being written, not on evidence.

## In progress

**Awaiting a human in Live.** Everything below was written in one headless
session on branch `headless/overnight`. It compiles, 49 tests pass, and
NONE of it has been loaded into Live. Tooling verification proves a file is
well formed; it has never once proved a rack sounds right, and this session
produced two silent-wrong bugs that only ears caught.

Work the checks in the order given: the loads come first, because if a file
is refused nothing after it matters.

### A. Do the new racks load and play

| # | File | Do this | Should happen |
|---|---|---|---|
| A1 | `build/PD1W.adg` | Drag onto a MIDI track, play | Wavetable pad sounds |
| A2 | `build/PD1W.adg` | Macro 1 full left, full right | Sweeps Wave to Drift |
| A3 | `build/BS1.adg` | Drag on, sweep Macro 1 | Three engines: Wave, Drift, Meld |
| A4 | `build/LD1.adg` | Drag on, sweep Macro 1 | Two engines: FM, Meld |
| A5 | `build/DR1.adg` | Drag onto a MIDI track | 8 pads, none red or offline |
| A6 | `build/DR1.adg` | Play pads 36,37,38,39,41,42,43,46 | Kick, rim, snare, clap, tom, hat, perc, ohat |

### B. Does the grammar hold on the new racks

Same knob, same meaning, on every engine. Q14 is what it looks like when
this fails: a slot bound correctly everywhere that still did two different
things.

| # | Rack | Do this | Should happen |
|---|---|---|---|
| B1 | BS1 | Macro 3 across all three engines | Cutoff moves, comparable range |
| B2 | BS1 | Macro 7 across all three engines | Release length comparable |
| B3 | BS1 | Macro 8 full left, then right, each engine | Silent at 0, unity at 127, no clipping |
| B4 | BS1 | Macro 4 on Drift | NOTHING. Drift exposes no drive |
| B5 | BS1 | Macro 5 on Wave, then Meld | NOTHING on either. Only Drift has LFO depth |
| B6 | BS1/LD1 | Macro 6 on Meld | Filter Q moves |

### C. Two guesses I could not check without you

Both are inferences, marked as such in the source. Either could be wrong.

| # | Check | How | If wrong |
|---|---|---|---|
| C1 | Drift's amp envelope is `Envelope1` | BS1, select Drift, hold a note, turn Macro 7. Does the TAIL change? | It is `Envelope2`; say so and I will swap it |
| C2 | Meld Engine A only | BS1, select Meld, turn Macro 3. Does the whole sound filter, or half? | Needs both A and B bound to one macro |

### D. DR1 in depth

| # | Do this | Should happen |
|---|---------|---------------|
| D1 | Kit Macro 1 (Sound), slowly, while playing a pad | Sample changes on EVERY pad at once |
| D2 | Dive into KICK on Push, turn its Sound knob | Only the kick's sample changes |
| D3 | Kit Macro 3 (Filter) | Cutoff on all pads |
| D4 | Kit Macros 5, 6, 7 (Send A, Send B, Send Vol) | NOTHING. Sends are not wired: needs Q6 |

### E. Spikes, each a one change diff

Save as the exact filename. One change only, nothing else touched.

| # | Spike | Do this | Save as |
|---|---|---|---|
| E1 | Q2 aftertouch | Any rack, map aftertouch to ONE parameter | `racks/q2_a.adg`, and the same rack unmapped as `racks/q2_b.adg` |
| E2 | Q3 key zone | Instrument rack, 2 chains, drag a KEY zone | `racks/q3_key_a.adg` / `_b.adg` |
| E3 | Q3 velocity zone | Same rack, drag a VELOCITY zone | `racks/q3_vel_a.adg` / `_b.adg` |
| E4 | Q5 tail | Load `build/probe_q5_unmapped.adg`, save it straight back out | `racks/q5_b.adg` |
| E5 | S10 tail | Load `build/PD1.adg`, right-click Macro 3, read what the range UI offers | just tell me what you see |

### F. Failure modes, where the answer may be "Live refused it"

A refusal is a RESULT here, not a problem. Note exactly what Live does.

| # | File | Question | What to report |
|---|---|---|---|
| F1 | `build/Q7_bad_zone.adg` | Chain 2's zone is inverted: Min 120, Max 20, crossfades outside both | Does it load? Repaired, refused, or loaded broken? |

### G. Unverified code, needs Live to test at all

| # | What | Why it is unverified |
|---|---|---|
| G1 | `mcp/remote_script_additions.py` | Four handlers for audio tracks, return tracks and output routing. Written from the Object Model names in `MCP.md`, never executed. Routing matches by display name, which is the fragile part |

Applying G1 is by hand: the file says where each block goes. It is
deliberately NOT an edit to the `ableton-mcp` submodule, because that would
move the parent's pointer to a commit no remote has.

## Next

**T1. Drum rack pads in the DSL.** What DR1 still needs now that nesting
is done. `clone.py` already sets `ReceivingNote` and allocates free notes,
and `Rack.nest` already puts a rack inside a chain; nothing joins them up.
A drum rack declares pads by note rather than chains by zone, so
`RackKind.DRUM` needs a pad-shaped entry point rather than `engine`, and
zone distribution does not apply to a pad.
*Blocks: DR1. Wants Q6 for the return selectors; samples are done.*

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
`find.py` already walks a preset tree. What is missing is an emitter - he DSL is ours.

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
