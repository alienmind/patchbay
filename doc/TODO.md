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

Six racks compile from `examples/patchbayground.py`. Five have been loaded
into Live 12.4.3, played, and corrected on what playing them found: PD1,
PD1W, BS1, LD1 and DR1, with VA1 exercising nesting. Three levels of
nesting, macros chaining into whichever sub-rack is selected, 96 variations
recalling, and eight drum pads on their own notes each holding a rack of
eight samples.

The eight slot grammar in `PATCHBAYGROUND.md` is what the code declares.
The cutoff and volume ranges, level trims and pad layout are gated. Slot
3's pairing, slot 6's per rack role, the local labels and the release range
on Operator and Simpler are NOT: they are the current round.

## In progress

**Awaiting a human in Live.** Tooling verification proves a file is well
formed; it has never once proved a rack sounds right.

The first three rounds are spent. A, B and C all ran: every rack loads and
plays, macros open where they should, DR1's pads follow the 808 Core Kit
grid, Drift's `Envelope1` is confirmed as its amp envelope, and Meld's B
side is bound alongside its A side after Macro 3 was heard filtering half
the sound. What is left of those rounds is `Q16` below.

**`patchbayground.py` has since changed shape, and every check below is
against the new build.** Three changes, all from the reconstruction in
`PATCHBAYGROUND.md`:

| | old | new |
|---|---|---|
| slot 3 | cutoff | cutoff AND resonance, one knob |
| slot 6 | resonance on every rack | per rack: attack, glide or morph |
| labels | grammar name on every rack | local per rack |

BS1's slot 6 moving on Meld ALONE is the rule working: only Meld can serve
morph, so Wavetable and Drift leave it empty rather than binding three
different ideas to one knob.

Rebuild before anything below: `patchbay build examples/patchbayground.py`

### H. The new slot 3, and the new slot 6

Everything the old B round proved about slots 3 and 6 is void; those two
knobs drive different parameters now. Slots 1, 2, 4, 7 and 8 are unchanged
and are not re-checked.

| # | Rack | Do this | Should happen |
|---|---|---|---|
| H1 | BS1 | Macro 3 across all three engines | Cutoff AND resonance move together, comparable on all three |
| H2 | BS1 | Macro 3 at 127 | Fully open with resonance at maximum. Confirm this is playable, not a scream. If it is, slot 3's resonance half wants a narrower range |
| H3 | PD1W | Macro 6 | Attack softens on Wave and Drift both |
| H4 | LD1 | Macro 6 | Glide on FM and Meld both |
| H5 | BS1 | Macro 6 on Meld, then Wave, then Drift | Filter morphs on Meld. NOTHING on the other two, by design |
| H6 | LD1 | Macro 5 | NOTHING, until Q16 |

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

Macro 7 bound through the full 1 ms..60 s on Operator and Simpler and
through 0.01..20 s everywhere else. Both now go through the same
intersection, expressed twice because the two devices keep envelope times
in milliseconds and the other three in seconds. Nothing about this is
audible from the file; it is one knob position meaning one length, or not.

| # | Rack | Do this | Should happen |
|---|---|---|---|
| J1 | PD1 | Macro 7 full right, hold a note on FM, then on Sample | Tail sounds the same length on both, about 20 s |
| J2 | PD1W | Same, Wave then Drift | Same length again, and the same as J1 |
| J3 | LD1 | Macro 7 at its 30 default, FM then Meld | Short and comparable. Report if either is too short to play |

Expected still broken: Macro 5 on every rack, until Q16.

### K. The donors we still lack are all stock devices

`patchbay harvest` took the tracked library from 8 devices to 32, out of
the AM_RADIAN template. What is still missing is missing everywhere, or is
only available in projects that are not ours to redistribute, so it stays
in the gitignored `donors_local/` and a clone cannot build with it.

One rack, one save, and the tracked library covers the whole
`PATCHBAYGROUND.md` device chain. Defaults are wanted here, not settings:
a donor is for the parameter list and each parameter's native range.

| # | Do this | Save as |
|---|---|---|
| K1 | New Audio Effect Rack. Drop one each of Channel EQ, Roar, Redux, Overdrive, Corpus, Gate, Auto Shift, Utility into ONE chain, all at defaults | `donors/AM_FX_donors.adg` |
| K2 | New MIDI Effect Rack. One each of Arpeggiator, Velocity, Note Length, Chord, all at defaults | `donors/AM_MIDI_donors.adg` |

K3 is the one that can fail. Every donor above came out of a `.als`, and
whether a device node is serialised identically in Set form and preset form
is Q9, which is open. Id checks pass and say nothing about it.

| # | Do this | Should happen |
|---|---|---|
| K3 | Drag in `build/K3_als_donor.adg`. Three chains: Auto Filter, EQ Eight, Echo, all built from Set-harvested donors | Loads, all three devices present and normal. Macro 1 sweeps the Auto Filter cutoff |

If K3 refuses or half-loads, every `donors/h_*.adg` is suspect and the
harvest needs to go through preset form instead. Nothing else depends on
them yet.

Expected still broken: nothing. This only widens the vocabulary.

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

| # | Do this | Should happen |
|---------|---------|---------------|
| D1 | Kit Macro 1 (Sound), slowly, while playing a pad | Sample changes on EVERY pad at once |
| D2 | Dive into KICK on Push, turn its Sound knob | Only the kick's sample changes |
| D3 | Kit Macro 3 (Filter + Res) | Cutoff and resonance on all pads |
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
  and spends the one property the grammar exists to guarantee.

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
DSL for a `.adg` and round-trips patchbay's own racks exactly; see `DSL.md`.
What is left is finding racks inside a Set, and putting names on the slots.

**T6b tail. Match extracted mappings against a known grammar.**
`--grammar patchbayground` would use that grammar's slot names wherever an
extracted parameter path agrees with one of its bindings, leaving the rest
positional. The positional half is done. Do not guess a slot name from a
parameter path with no grammar to check it against; that is inventing
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
