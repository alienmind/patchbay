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

`examples/patchbayground.py` is the end-to-end test: one example large
enough that a regression shows up there first. Six racks compile from it. Five have been loaded
into Live 12.4.3, played, and corrected on what playing them found: PD1,
PD1W, BS1, LD1 and DR1, with VA1 exercising nesting. Three levels of
nesting, macros chaining into whichever sub-rack is selected, 96 variations
recalling, and eight drum pads on their own notes each holding a rack of
eight samples.

The eight slot layout in `PATCHBAYGROUND.md` is what the code declares.
The cutoff and volume ranges, level trims and pad layout are gated. Slot
3's pairing, slot 6's per rack role, the local labels and the release range
on Operator and Simpler are NOT: they are the current round.

## In progress

**Awaiting a human in Live.** Tooling proves a file is well formed and, as
of `tests/golden.txt`, that a change moved nothing. It has never once
proved a rack sounds right.

Everything below has been triaged per `CLAUDE.md`. Six checks came off the
list because they asserted facts about the file rather than facts about the
sound, and are now tests: slot 3 driving a pair on every chain, slot 6
reaching only the engines that offer it, and slot 7 being one interval in
two units. What is left is perception, plus the spikes, which need Live to
PRODUCE a file rather than to judge one.

Rounds A, B and C are spent: every rack loads and plays, macros open where
they should, DR1's pads follow the 808 Core Kit grid, Drift's `Envelope1`
is confirmed as its amp envelope, and Meld's B side is bound alongside its
A side. `Q16` is what is left of them.

**`patchbayground.py` has changed shape since, and every check below is
against the new build.** Three changes, from the reconstruction in
`PATCHBAYGROUND.md`, plus a fourth from measuring release ranges:

| | old | new |
|---|---|---|
| slot 3 | cutoff | cutoff AND resonance, one knob |
| slot 6 | resonance on every rack | per rack: attack, glide or morph |
| labels | layout name on every rack | local per rack |
| slot 7 | unranged on Operator and Simpler | the shared range, in ms |

BS1's slot 6 moving on Meld ALONE is the rule working: only Meld can serve
morph, so Wavetable and Drift leave it empty rather than binding three
different ideas to one knob.

Rebuild before anything below: `patchbay build examples/patchbayground.py`

### The order to do it in

Ordered by what unblocks the most. Report by check number.

| Round | What | Why here |
|---|---|---|
| **Q16** | One diff, Drift's LFO routing | Unblocks Macro 5 on every rack. Nothing else does |
| **K** | Two donor racks, one load check | Widens the vocabulary and gates 54 donors nothing has loaded yet |
| **H** | The new slots 3 and 6 | The reshape has never been HEARD. Its structure is now a test |
| **I** | Labels on Push | Eyes only. Nothing about a display is in the file |
| **J** | Release, one check left | Whether 20 s is the right ceiling |
| **D** | DR1 in depth | Unaffected by the reshape except D3 |
| **E** | Five one-change spikes | Each unblocks a separate feature. No hurry, no order |
| **F1** | One deliberately broken zone | A refusal is a result |
| **G1** | The MCP handlers | Blocks the whole Set-building half |

### K. Donors: two racks to save, one file to load

`patchbay harvest` took the library from 8 devices to 56 out of files you
already had. What is missing is missing everywhere, and K3 is the one that
can fail.

Defaults are wanted in K1 and K2, not settings: a donor is for the
parameter list and each parameter's native range.

| # | Do this | Save as |
|---|---|---|
| K1 | New Audio Effect Rack. One each of Channel EQ, Tuner, Spectrum, Auto Shift into ONE chain, all at defaults | `donors/AM_fx.adg` |
| K2 | New MIDI Effect Rack. One each of Arpeggiator, Note Length, all at defaults | `donors/AM_midi.adg` |

| # | Do this | Should happen |
|---|---|---|
| K3 | Drag in `build/K3_als_donor.adg`. Three chains: Auto Filter, EQ Eight, Echo | Loads, all three devices present and normal. Macro 1 sweeps the Auto Filter cutoff |

K3 is a real risk, not a formality. Every harvested donor was lifted out of
a `.als`, and whether a device node is serialised identically in Set form
and preset form is Q9, which is open. Id checks pass and say nothing about
it. If K3 refuses or half-loads, all 51 harvested donors are suspect and
the harvest has to go through preset form instead. Nothing depends on them
yet, which is why this is cheap now and expensive later.

### H. The new slot 3, and the new slot 6

Everything round B proved about slots 3 and 6 is void; those two knobs
drive different parameters now. Slots 1, 2, 4 and 8 are unchanged and are
not re-checked. Slot 7 is round J.

**The structural half is now a test and is not asked for here.** That slot
3 drives a pair on every chain, that slot 6 reaches Meld and neither
Wavetable nor Drift on BS1, and that it reaches both chains on PD1W and
LD1, are all asserted in `tests/test_patchbay.py`. What is left is whether
those mappings SOUND like what they are called, which nothing but ears
answers.

| # | Rack | Do this | Should happen |
|---|---|---|---|
| H1 | BS1 | Macro 3 across all three engines | The sweep is comparable on all three. Report an engine that is obviously wider or narrower than the others |
| H2 | BS1 | Macro 3 at 127 | Playable, not a scream. If it screams, slot 3's resonance half wants a narrower range |
| H3 | PD1W, LD1 | Macro 6 on each chain | Attack softens on PD1W, glide on LD1. This is whether the role is the RIGHT parameter, not whether it is mapped |
| H6 | LD1 | Macro 5 on FM | `Lfo/LfoAmount` is bound on Operator and its routing is Q16's question one device over. Anything at all, or nothing? |

H6 is not covered by the test above and is the one that surprised: LD1's
macro 5 IS mapped, on Operator, so "nothing until Q16" was only ever true
of Wavetable and Meld.

### I. Do the labels read right on the hardware

The first check of this whole mechanism, and it is a Push check rather
than a Live one.

| # | Do this | Report |
|---|---|---|
| I1 | BS1 on Push, look at the macro row | Do you see `> Instrument`, `Filter + Res`, `Morph`? Or truncated versions, and truncated to what? |
| I2 | Same in Live's rack panel | Same question. Live's macro name field is narrower than Push's |
| I3 | DR1, dive into KICK, then into HAT | KICK slot 4 reads `Drive + Snap`, HAT reads `Drive`, same position |
| I4 | Any rack | Does `>` read as "this one steps"? If it is noise on the display, say so and it goes |

I1 and I2 decide whether labels can carry a phrase at all. If Push shows
eight characters, `Filter + Res` is not the answer and the pairing needs a
different word rather than a longer one.

### J. Release, now that Operator and Simpler are ranged

**That the two spellings are one interval is a test, not a check.** Exactly
two device ranges carry slot 7 across the five racks, `0.01..20` and
`10..20000`, one being the other times 1000, and
`tests/test_patchbay.py` fails if that stops being true. J1 and J2 as
written asked a person to confirm arithmetic.

What a test cannot say is whether 20 s is the right ceiling.

| # | Rack | Do this | Should happen |
|---|---|---|---|
| J3 | LD1 | Macro 7 at its 30 default, then full right | Playable at 30, and the long end is long enough to be worth having. Report if either end is useless |

Expected still broken: Macro 5 on Wavetable and Meld, until Q16.

### Q16. Drift's LFO reaches nothing

Held over from round B. `Lfo_Amount` is the right parameter and moves.
What is missing is the routing, and it is NOT in the parameter list: Drift
keeps it in plain `Value` elements next to the parameters, as
`Filter_ModSource1`, `ModulationMatrix_Source1` / `_Target1` / `_Amount1`
and their numbered siblings. The donor has `ModulationMatrix_Source1=5,
Target1=8, Amount1=0.8` and `Lfo_ModSource=5`, so the enums are guessable
and therefore exactly what must not be guessed.

One change diff, and it answers the whole thing at once:

| # | Do this | Save as |
|---|---|---|
| Q16 | Load `build/BS1.adg`, select Drift, set ONE modulation matrix row to LFO -> Filter Frequency, nothing else | `racks/q16_a.adg`, and the same rack with that row cleared as `racks/q16_b.adg` |

Until it lands, Macro 5 does nothing audible on any engine: Wavetable's
LFO depth is not in the parameter list at all, and Meld has no equivalent.

### D. DR1 in depth

Unaffected by the reshape except D3, which now moves a pair.

D4 is a pure absence claim and D1 to D3 each have a structural half, so all
four are largely answerable by the mapping matrix test. They are not yet,
because DR1 needs `samples/` and this machine's checkout has none, so the
test would be asserting nothing. **Extend
`test_the_wildcard_slot_reaches_only_the_engines_that_offer_it` to DR1 on
a machine that has the audio, and D4 goes away entirely.**

What stays is whether the chaining does what its name says three levels
down, which is the part the matrix cannot reach.

| # | Do this | Should happen |
|---------|---------|---------------|
| D1 | Kit Macro 1 (Sound), slowly, while playing a pad | Sample changes on EVERY pad at once, and lands on a sample rather than between two |
| D2 | Dive into KICK on Push, turn its Sound knob | Only the kick's sample changes |
| D3 | Kit Macro 3 (Filter + Res) | Cutoff and resonance on all pads, comparable across pads |

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

**T8. DECIDE WHAT SLOTS 5 AND 6 MEAN INSIDE A DRUM PAD.** A design call,
not a task. Nobody else can make it and the code is currently sitting on a
placeholder.

`PATCHBAYGROUND.md`, "What a slot means may depend on depth", records it as
undecided and calls it the sharpest open question in the DR1 design. The
two answers:

- **One meaning per rack, whatever the depth.** What the code does today.
  Slots 5 and 6 mean modulation depth and the wildcard at every level.
  Muscle memory is the product and a knob that changes meaning as you dive
  is the thing muscle memory cannot absorb.
- **Meaning per LEVEL.** Slots 5 and 6 become the two sends at kit level
  and the FM pair inside the sound. Buys four controls with no page flip,
  and spends the one property the layout exists to guarantee.

The conservative reading is in the code because it is reversible; the other
is not, once anything is played on it. Nothing is blocked on this and the
cost of deciding late is that DR1 gets rebuilt.

Two things now bear on it that did not when it was written. Slot 6 is a
per rack role rather than a fixed meaning, so meaning already varies by
RACK and the question is only whether it may also vary by DEPTH. And
labels are local, so a pad can SAY what its slot 5 does, which removes the
"you cannot tell what the knob is" half of the argument but not the muscle
memory half.

*Wants Q6 either way: the kit-level sends are FX selectors, not send
levels, and nothing wires them yet.*

**T10. DECIDE WHETHER TO PORT TO TYPESCRIPT.** A design call, not a task.
`TS-PORT.md` is the analysis: the XML layer round trips losslessly in
`@xmldom/xmldom` at 70 ms, the donors fit a browser at 300 KB, and three of
the arguments on both sides turned out to be void. What survives is that
the only reason to switch is a browser-hosted version, and the strongest
objection to it is samples, which a browser cannot stat.

Nothing is blocked on this. It is here so it does not get decided by
drift.

*One cheap thing first: Pyodide ships lxml, so the existing compiler may
run in a browser unchanged. Twenty minutes to find out, and it would make
the whole question moot.*

**T9. Migrate to the proposed DSL surface.** The shape, the argument for
it and what was verified are the last section of `DSL.md`. Slots become
values carrying their own start, label and selector flag; an engine profile
becomes a value with `drives` and `offers`; `bind` splits into one verb per
relation; ranges become a `Range` with a unit and methods.

**Class 1 throughout: NO LIVE CHECK, at any step.** Not a format change. A
prototype front end, `patchbay/experimental/dsl2.py` driven by
`examples/experimental/patchbayground2.py`, declared PD1, PD1W, BS1, LD1
and VA1, plus a drum rack
holding a nested pad, and every one diffed identical against what the
current syntax builds. `tests/golden.txt` holds the digests, so every step
below proves itself by `uv run pytest`. If a step needs the goldens
regenerated, that step has moved the output and is wrong.

Order matters, because the round trip test is what holds the rest honest.

**T9a. The types, beside the current ones.** `Slot`, `Range`, `Layout`,
`Engine`, `Rack` in `patchbay/dsl.py`, with the current classes still
exported and still passing their tests. Nothing else moves yet.
*Gate: the prototype's five racks, declared in the new types, digest equal
to `tests/golden.txt`.*

**T9b. Move `examples/patchbayground.py`.** Six racks including DR1 at
three levels, which is where `spends`, `pad` and `deriving` are actually
exercised. Deletes `_bind`, the `character=` parameter on five engine
functions, and the `fm(sampler(rack))` nesting.
*Gate: `tests/golden.txt` unchanged. DR1 is not in it and needs a machine
with `samples/`; add its digest there while you are on one.*

**T9c. Move `patchbay/extract.py`.** The emitter writes DSL source, so it
writes the new syntax or the round trip breaks. This is the step that
proves the new surface expresses everything the old one did, because the
extractor is a complete enumeration of it.
*Gate: `test_extract_round_trips_structure` passes unchanged in what it
asserts.*

**T9d. Delete the old surface.** Tests, then `DSL.md`'s code blocks, then
the classes. The proposal section at the end of that file folds into the
body once it is no longer a proposal.

One rule reverses on the way: `.drives` on the same slot twice accumulates,
where a second `bind` of a slot replaces.  `DSL.md` says why.
`test_binding_a_slot_twice_replaces_rather_than_accumulates` asserts the
old behaviour and is the one test that must change rather than pass; no
other caller relies on it.

*Wants nothing. Blocks nothing. It is worth doing before T1 and T6c add
callers to a surface that is going to move.*

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

**T6. Decompile a saved rack into DSL source.** `patchbay extract` emits
DSL for a `.adg` and round-trips PatchBay's own racks exactly; see `DSL.md`.
What is left is finding racks inside a Set, and putting names on the slots.

**T6b tail. Match extracted mappings against a known layout.**
`--layout patchbayground` would use that layout's slot names wherever an
extracted parameter path agrees with one of its bindings, leaving the rest
positional. The positional half is done. Do not guess a slot name from a
parameter path with no layout to check it against; that is inventing
intent, and `CLAUDE.md` rule 1 applies.

**T6c. Locate racks inside a `.als`.**

*Q9, and it must come first.* A `.adg` stores a rack in PRESET form:
`GroupDevicePreset` with `Device` and `BranchPresets` as siblings. A `.als`
stores the same rack in LIVE form, inside
`LiveSet/Tracks/*/DeviceChain/DeviceChain/Devices`. Whether chains are
serialised identically in both is UNKNOWN and must not be assumed. Method:
build one two-chain rack, save it as `racks/q9_a.adg` by dragging to the
browser, save the Set containing that same rack as `racks/q9_b.als`,
unpack both and diff by hand. Write the mapping in `SCHEMA.md`.

Then `patchbay extract <file.als>` walks tracks, finds rack nodes in each
device chain, lifts each into preset form, and reuses the emitter. Note
S13: a lifted subtree must have its `Id` stripped, and a top-level
`GroupDevicePreset` must carry no attributes at all.

*Gate:* extract every rack from a Set, rebuild each, diff each.

**T6d. Batch it.** `patchbay extract --out lib/ <file.als>` writing one
module per rack plus an index. Trivial once T6c works, and worth nothing
until then.

**Cheaper path that needs none of T6c.** Dragging a rack from a Live Set
into the browser saves a `.adg`, which extracts today. For tens of racks
rather than hundreds, hand-dragging is the whole answer.

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
*Blocks: the macro layout being complete.*

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
- Confirming a mapped macro DOES something. WHICH mappings exist is not
  manual: `patchbay mappings` reads them out of the file and the matrix is
  asserted in tests. Whether one reaches anything is Q16's lesson, and
  Live's API exposes no `mapped_parameter` either, so ears are the only
  instrument for it.

Semi-automated, worth designing well: sample assignment (curation manual,
wiring automatic, a pad-to-path manifest between them) and variation
culling (generated names encoding parameter values make culling informed).

## Definition of done

`patchbay build` plus a driven `ableton-mcp` session produces a Set that
opens in Live 12, with eight correctly named and routed tracks, racks whose
macros follow the layout in `PATCHBAYGROUND.md`, playable from Push 3
without touching a mouse.

That is the END-TO-END TEST passing, not the point of the project. What it
proves is that the DSL reaches far enough to author a whole Set of this
size in code. `PATCHBAYGROUND.md` is our reconstruction of PLAYGRND from
what is publicly visible of it, and the library stays ignorant of it
throughout: rule 6.

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
