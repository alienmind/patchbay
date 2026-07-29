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
| **Q16b** | One knob, Drift's LFO depth | The diff landed. This decides which parameter Macro 5 binds |
| **K** | Two donor racks, one load check | Widens the vocabulary and gates 54 donors nothing has loaded yet |
| **H3b/H6b** | Two knobs on LD1 and PD1 | The switches are on now. Confirm the knobs finally do something |
| **I** | Labels on Push | Eyes only. Nothing about a display is in the file |

| **D2b** | One knob inside a pad | Sound is the second macro, not the first |
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

### H. The new slot 3, and the new slot 6 - MOSTLY ANSWERED

H1, H2 passed in Live 12.4.3: BS1's Macro 3 sweeps comparably on all three
engines and is playable at 127, so slot 3's pairing and its resonance range
both stand.

H3 and H6 found the same defect Q16 found, twice more. A macro was mapped,
resolved, moved its target, and reached nothing because a SWITCH was off:

| rack | knob | what was off | fixed by |
|---|---|---|---|
| LD1 | Macro 6, glide | Operator `Globals/PortamentoOn` = false | `sets` on LD1's FM chain only |
| PD1, LD1, VA1 | Macro 5, movement | Operator `Lfo/LfoOn` AND `Filter/LfoOn` = false | `sets` on the FM profile |

Both are plain booleans read off the donor, so neither is a guessed enum.
`test_a_bound_modulator_is_switched_on` now asserts that a mapped
`Lfo/LfoAmount` implies both switches, and a mapped Drift `Lfo_Amount`
implies a routed row, so this class of defect fails a test rather than
waiting for ears. Goldens moved for PD1, LD1 and VA1.

The glide enable sits on the RACK, not on the FM profile: PD1 and VA1 hold
the same profile and spend slot 6 on attack, and portamento there would
smear every pad they play.

| # | Rack | Do this | Should happen |
|---|---|---|---|
| H3b | LD1 | Macro 6 on the FM chain, playing a legato line | Notes now GLIDE. Report if the 50 ms donor default is too short to hear |
| H6b | LD1, PD1 | Macro 5 on the FM chain | Filter wobbles, deepening with the knob |

Meld's half of glide is NOT fixed and is E6 below: its
`MeldVoice_Engine{A,B}_GlideMode` is 0, an enum nobody has diffed, and a
mode that is probably off is exactly what rule 1 says not to guess.

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

J3 passed: 30 is playable and neither end is useless. The 0.01..20 s
ceiling stands and round J is closed.

### Q16. Drift's LFO routing - DIFFED, one question left

The file half is ANSWERED and written up in `SCHEMA.md` against
`racks/q16_a.adg` and `racks/q16_b.adg`. A modulation row is three sibling
elements sharing an index. `ModulationMatrix_Source1=2` is the LFO,
`_Target1=6` is LP Frequency, `_Amount1` is an ordinary mappable
parameter, and the two selectors are bare `Value` elements with no
`Manual`, so they can only be SET and never driven.

Both consequences are BUILT. `Engine.sets` writes a control that no
mapping can reach, `patchbay extract` recovers it, and DRIFT in
`examples/patchbayground.py` now states its own row, which also stamps out
the donor's `Source1=5, Target1=8` that had every Drift here modulating
the high-pass at 80% unasked. `tests/golden.txt` was regolded for BS1 and
PD1W, deliberately: those are the two racks with a Drift in them.

What is left is which knob is the DEPTH, and only ears answer it.
`Lfo_Amount` and `ModulationMatrix_Amount1` are both mappable and the file
does not say whether the first gates the second. Macro 5 is on
`Lfo_Amount`, and the row it feeds is now open at full.

| # | Do this | Should happen |
|---|---|---|
| Q16b | Load `build/BS1.adg`, Macro 1 to the middle for the Drift chain, hold a note and turn Macro 5 through its travel | The cutoff wobbles, and the wobble deepens as the knob rises |

If NOTHING moves, `Lfo_Amount` is not the depth: Macro 5 moves to
`ModulationMatrix_Amount1` and `Lfo_Amount` becomes a `sets` at full. One
line either way.

Wavetable's LFO depth is still not in the parameter list at all and Meld
has no equivalent, so Macro 5 stays empty on those two regardless.

### D. DR1 in depth - ANSWERED, with one thing to re-check

D1 and D3 passed: the kit's Sound walks every pad's sample at once and
lands on a sample rather than between two, and Kit Macro 3 moves cutoff and
resonance comparably across pads.

D2 reported that diving into KICK and turning Sound moved every pad. The
file says that cannot be what happened: each pad's chain selector is driven
by that pad's OWN macro 2, and the kit reaches pads only through macros 1,
3, 4 and 8, which is asserted by the mapping matrix test. The likely cause
is which knob was turned. **Inside a pad, Sound is the SECOND macro**,
because PAD keeps Instrument in slot 1 and leaves it unbound, so the first
encoder does nothing and the second one steps.

| # | Do this | Should happen |
|---|---|---|
| D2b | Dive into KICK, turn the SECOND macro | Only the kick's sample changes |

**That the first knob inside a pad is dead is a finding, not a slip.** It is
T8 arriving in practice: one meaning per rack whatever the depth costs a
knob at every level below the top. Worth weighing when T8 is decided.

### E. Spikes, each a one change diff

Save as the exact filename. One change only, nothing else touched.

| # | Spike | Do this | Save as |
|---|---|---|---|
| E1 | Q2 aftertouch | Any rack, map aftertouch to ONE parameter | `racks/q2_a.adg`, and the same rack unmapped as `racks/q2_b.adg` |
| E2 | Q3 key zone | Instrument rack, 2 chains, drag a KEY zone | `racks/q3_key_a.adg` / `_b.adg` |
| E3 | Q3 velocity zone | Same rack, drag a VELOCITY zone | `racks/q3_vel_a.adg` / `_b.adg` |
| E4 | Q5 tail | Load `build/probe_q5_unmapped.adg`, save it straight back out | `racks/q5_b.adg` |
| E5 | S10 tail | Load `build/PD1.adg`, right-click Macro 3, read what the range UI offers | just tell me what you see |
| E6 | Meld glide | Load `build/LD1.adg`, select Meld, turn glide ON for engine A only, nothing else | `racks/q17_a.adg`, and the same rack with it off as `racks/q17_b.adg` |

E6 is the last of the mapped-but-switched-off family. Meld's
`MeldVoice_EngineA_GlideMode` reads 0 and the enum is undiffed, so LD1's
Macro 6 moves Meld's glide TIME and glides nothing. One diff closes it.

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

*`TS-PORT.md` predates the DSL migration and quotes the old syntax. What
it measures is the XML layer, which did not move, so the analysis stands.*

**T1. Drum rack return chains.** The pad half is done: `Rack.pad` takes a
note and a content, zone distribution skips pads, and DR1 builds eight pads
each holding a rack of eight samples, three levels deep. What is left is
the RETURN side, which nothing in the DSL reaches: a drum rack's return
chains, their per-pad send levels, and a selector across several reverbs
and delays so a macro swaps the effect rather than its level.
*Wants Q6, which is where that combination is untested.*

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
