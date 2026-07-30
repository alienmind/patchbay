# TODO - the live backlog

The only place that says what is in flight. Everything else in `doc/` is
settled knowledge.

Work happens HERE: pick a task, move it to In progress, update its status
as you go. When it is done, it leaves this file. It does not stay as a
completed entry. See "The routine" at the bottom.

Live version for every finding below: **12.4.3**.

## What is left, at a glance

**Nothing is in flight.** Every task that was on this table has landed and
left it: the channel strip, the drum rack returns, both design calls, and
reading racks out of a Set. What each one became is in `README.md`,
`ARCHITECTURE.md`, `SCHEMA.md`, `DSL.md` or `THE_BASEMENT.md`, per the
routine at the bottom.

What is left is optional, and none of it blocks anything: **Q8** (send
taper) and **Q6** (return selectors, mostly answered by AFX1).

**One thing is worth deciding, not answering.** Q19 found that 50 of the 59
donors were saved by Live 12.0_12203 and that the schema has renamed at
least one parameter family since. Re-harvesting every donor from 12.4.3 is
one pass over a Live library and would move every golden; comparing
parameter NAMES against the 12.4.3 files already in `racks/` costs nothing
and covers only the devices those files happen to hold. The second is done
and found one rename. The first is a call.

Donors for the whole channel strip are in: `ChannelEq`, `Tuner`,
`SpectrumAnalyzer`, `AutoShift`, `MidiArpeggiator`, `MidiNoteLength`,
`PhaserNew`, `Resonator`, `StereoGain`. Two tags are not the GUI name:
Spectrum is `SpectrumAnalyzer`, Resonators is `Resonator`.

## Status

Phase 0 discovery is closed: 12 spikes answered, 1 retired, both kill
criteria passed. What the format does is in `ARCHITECTURE.md`, each claim
marked verified, inferred or open and traced to a file in `racks/`.

**The instrument half of PATCHBAYGROUND is built.** Six racks compile from
`examples/patchbayground.py`. PD1, PD1W, BS1, LD1 and DR1 have been loaded
into Live 12.4.3, played, and corrected on what playing them found; VA1
exercises nesting. DR1 is 178,960 facts, eight pads on their own notes each
holding a rack of eight samples, three levels deep, from about thirty lines
of declaration. That is the tedium the project exists to remove, and it is
removed.

`tests/golden.txt` holds a digest per rack, so a change that is not
supposed to move the output proves it by `uv run pytest` rather than by a
human dragging files into Live.

**The whole channel strip now builds too**: ARP1, MFX1, EQC, AFX1, AFXS1
and VOL1, from about a hundred lines of declaration. AFX1 alone is eight
effects, 24 bindings and a selector. That took three capabilities the
instrument racks never needed - several devices in ONE chain, MIDI effect
racks, and return chains with sends - and all three are in `DSL.md`. All six
have been loaded into Live 12.4.3 and played, and four defects came out of
that: Q22 refused three of them outright, Q23 buried a knob that could not
exist, Q24 found the arpeggiator bound to a parameter its own mode switch
had out of the path, and Q25 found a bipolar knob sitting at its minimum.

**DR1 has returns.** Two of them, each holding a rack of two effects behind
a selector. That closes Q6 structurally: a return chain holds a rack
exactly as any chain does. The per-pad send LEVELS are declarable; the kit
knobs that would sweep them are not, because a send takes a value and not a
macro (Q23).

## Scope, deliberately narrowed

Two things came off the plan rather than being finished, and both are in
`THE_BASEMENT.md` with the reasoning: **building the Set through
`ableton-mcp`**, and the old definition of done that rested on it.

The short version: assembling eight tracks, routing and returns is a
half-hour job by hand, done once, and already done once. Automating it
would spend the most fragile component in the project, a third-party
submodule tied to Live's remote-script API, on the least repetitive work
there is. Generating a rack is worth automating because it is 178,960
facts. Creating a track is not, because it is one click.

**What done means now:** every rack in `PATCHBAYGROUND.md` is generated
from a declaration, dragged into a Set assembled by hand, and plays from
Push 3 without a mouse. The tool authors instruments; the person assembles
the Set and chooses the sounds.

## In progress

### Racks read out of Sets

`patchbay extract file.als` walks every track, lifts each rack into preset
form, and emits DSL. `--out DIR` writes a module per rack plus an index.

Gated by `test_a_rack_lifted_out_of_a_set_matches_its_preset_twin`: the
lifted rack rebuilds to the same chains, mappings, macro positions and
labels as the same rack dragged to the browser by Live.

The lift also found the fourth donor repair. A device harvested from a
`.als` carries the session ids the Set was using for automation, and every
rack here shipped with some, because 48 of 56 donors came out of Sets. Live
loads them and a preset Live writes never has them, so they are cleared as a
device is placed. Six racks moved in the goldens for that, all of them
`AutomationTarget@Id`, `ModulationTarget@Id` and `Pointee@Id` going to 0.

### The strip is built and played

Ten racks compile, all ten have been loaded into Live 12.4.3, and the six
strip racks have been played: ARP1, MFX1, EQC, AFX1, AFXS1, VOL1. What the
three rounds of checks found is in `SCHEMA.md` under Q22 to Q25, and every
one of them is fixed rather than noted.

What is left of the strip is not structural. `PATCHBAYGROUND.md` names each
instance for its track, `EQC_BS1` on BS1, which is a loop over a name and
worth writing when the strip gets pasted across eight tracks. Channel EQ
stays stock, per the spec.

### Rounds A to J are closed

Every macro check against the instrument racks has been run in Live 12.4.3.
What they found, and where it went:

- **Three mapped macros reached nothing**, because a switch or a routing
  was off and neither is in the parameter list: Drift's modulation matrix
  (Q16), Operator's `Lfo/LfoOn` and `Filter/LfoOn`, and Operator's
  `Globals/PortamentoOn`. All three are fixed, and
  `test_a_bound_modulator_is_switched_on` means the class fails in pytest
  now rather than in a room. `SCHEMA.md` has the evidence.
- **The `>` selector mark is gone.** Push rendered it, Live truncated it,
  and it read as nothing. `THE_BASEMENT.md`.
- **Glide is ranged**, `0.01..2 s`, because Operator's native
  `0.1..10000 ms` through a logarithmic taper put half the knob under
  32 ms.
- Slot 3's pairing, slot 6's per-rack role, slot 7's release ceiling and
  DR1's pad grid all stand as declared.

Two things came out of round D that are not defects and are not tasks.

**The kit and pad layouts are offset by one.** Sound is knob 1 at kit level
and knob 2 inside a pad, and a pad's knob 1, `Instrument`, is bound to
nothing at all. It is the cost of one meaning per rack whatever the depth,
and it is evidence for T8 below.

**All eight pads move in lockstep.** With the kit's Sound chained into
every pad, kick sample 3 with snare sample 5 is unreachable, because a
macro mapped to an outer macro cannot be turned independently. That is
Live, not the file. `PATCHBAYGROUND.md` already lists per-pad unlinking as
deferred, and `chaining()` supports it today by omitting a slot for one
pad.

## Next

**T6 is done.** `patchbay extract` reads a `.adg` or a `.als` and emits DSL
that rebuilds it; `--out DIR` writes one module per rack plus an index, so a
Set becomes a spec directory. What it recovers and what it cannot is in
`DSL.md`.

The one tail left is naming: slots come out positional, `Macro 1`, because
guessing a slot name from a parameter path is inventing intent. A
`--layout patchbayground` flag would use a known layout's names wherever an
extracted parameter path agrees with one of its bindings, and leave the rest
positional. Nothing needs it.

## Open spikes

None is a kill criterion. The project works without any of them.

**Q6. Return selectors.** `PATCHBAYGROUND.md` wants each DR1 return chain
to hold a selector across several reverbs and delays, so a macro swaps the
EFFECT rather than the send level. The pieces are known separately, the
combination is untested. **C1 is the same mechanism one level up**, so
building AFX1 answers most of this for free.

**Q23 is worth re-opening if a hand-mapped send exists.** `Rack.sending` is
buried on the strength of one check: the mapping resolved and the send did
not move. A send column mapped to a macro BY LIVE, saved as a pair, would
say whether the mechanism is impossible or whether we wrote it in the wrong
place. Nothing depends on it; DR1's kit slots 5 and 6 stay named and
unbound until then.

The pair arrived, and it says Live writes the mapping exactly as we did -
byte for byte, reproduced with `params.map_to_macro`. See Q23 in
`SCHEMA.md`. What is left is one knob turn: **load `racks/q23_b.adg` and
turn Macro 5.** If pad 1's Send A moves, the mechanism works and DR1's
failure was ours; if it does not, Live writes a mapping it ignores.

**Hybrid Reverb's impulse response slot is blank** in both DR1 returns,
because the donor was harvested and harvesting strips paths. Unlike a
Simpler sample part, an IR slot cannot simply be removed, and whether Live
falls back to a built-in response or reports a missing file is unchecked.
One drag answers it.

**Q8. Send taper.** Sends are linear amplitude from 0.000316 to 1, but
whether the knob is linear in amplitude or in dB is unknown. Only matters
if a spec ever states send levels as knob percentages.

**Q9 is closed.** The full mapping between Set form and preset form is in
`SCHEMA.md`, read off `racks/q9_a.adg` beside `racks/q9_b.als`. Four donor
repairs came out of it and `patchbay extract` reads a Set because of it.

## Standing manual work

Not backlog. These do not get automated, and trying is how the project
fails. **A check that asks whether something SOUNDS right belongs here, not
in the backlog above.** Several did, for a while, and reading them as tasks
is what made the project feel bigger than it is.

- Choosing which samples are good. A generator cannot judge a kick.
- Sound design judgement. Generate wide, audition, cull.
- Gain staging and mix balance. A per-engine loudness trim lived in the
  spec for a while and is buried in `THE_BASEMENT.md` with its
  measurements: a number taken by ear is not structure, and no test can
  check one. Volume ranges stop at each engine's own unity; trim on the
  mixer.
- Whether one knob feels comparable across engines. The RANGES that make it
  so are declared and tested; whether the result is musical is ears.
- Assembling the Set: eight tracks, naming, routing, returns, tempo. Half
  an hour, once. See `THE_BASEMENT.md` for why this is not automated.
- Picking the sidechain SOURCE, one dropdown per track. Q18 showed a device
  preset does not carry it at all. The configuration around it is not
  manual: see C4.
- Confirming a mapped macro DOES something. WHICH mappings exist is not
  manual: `patchbay mappings` reads them out of the file, the matrix is
  asserted in tests, and as of round H so is the switch behind each
  modulator. Whether one is audible is still ears.

Semi-automated, worth designing well: sample assignment (curation manual,
wiring automatic, a pad-to-path manifest between them) and variation
culling (generated names encoding parameter values make culling informed).

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
