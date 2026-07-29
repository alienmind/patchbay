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

**What is left of the original scope is the CHANNEL STRIP**, and it was
never on this list until now. `PATCHBAYGROUND.md` puts the same seven
devices on every track, five of them racks with their own layouts, and none
of them exist. That is a bigger gap than everything else here combined, and
it is the last part that is genuinely tedious by hand.

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

### C. The channel strip

`PATCHBAYGROUND.md` puts these on every one of the eight tracks, in order:

    ARP1   MFX1   <instrument>   EQC   AFX1   AFXS1   Channel EQ   VOL1

Build the racks once, paste the strip across eight tracks by hand. Copying
a device chain in Live is two minutes; building AFX1's eight effect chains
and their mappings by mouse is not.

**C1. AFX1.** Eight character effects behind ONE selector, so a knob swaps
the effect rather than layering it. The biggest remaining piece of real
tedium, and the DSL already does all of it: a selector slot, eight chains,
zones distributed, one macro each.

`PATCHBAYGROUND.md` asks for a spread across degradation, time and space
rather than eight flavours of one idea: glitch, tear, erode, grind, reduce,
soak, stretch, fade. Which device serves which is a taste call and yours.
*Donors: 9 of 11 candidates are indexed. Phaser and Resonators are not.*

**C2. ARP1 and MFX1.** Two small MIDI racks. MFX1's four devices are all
indexed already; ARP1 needs the donors in K2.
*Cheap once the donors land.*

**C3. EQC.** Five devices, and only partly automatable: the sidechain
inside it is absent from the file format AND from the Live Object Model, so
that part stays a manual step whatever else happens. See `THE_BASEMENT.md`.
*Donors: `ChannelEq` and `Utility` are missing.*

### K. Donors: three racks to save, one file to load

C1 to C3 are blocked on the saves. K3 is the one that can fail, and it is
worth doing before anything depends on a harvested donor.

Defaults are wanted, not settings: a donor is for the parameter list and
each parameter's native range.

| # | Do this | Save as |
|---|---|---|
| K1 | New Audio Effect Rack. One each of Channel EQ, Tuner, Spectrum, Auto Shift into ONE chain, all at defaults | `donors/AM_fx.adg` |
| K2 | New MIDI Effect Rack. One each of Arpeggiator, Note Length, all at defaults | `donors/AM_midi.adg` |
| K4 | New Audio Effect Rack. One each of Phaser-Flanger, Resonators, Utility, all at defaults | `donors/AM_fx2.adg` |

| # | Do this | Should happen |
|---|---|---|
| K3 | Drag in `build/K3_als_donor.adg`. Three chains: Auto Filter, EQ Eight, Echo | Loads, all three devices present and normal. Macro 1 sweeps the Auto Filter cutoff |

K3 is a real risk, not a formality. Every harvested donor was lifted out of
a `.als`, and whether a device node is serialised identically in Set form
and preset form is Q9, which is open. Id checks pass and say nothing about
it. If K3 refuses or half-loads, all 51 harvested donors are suspect and
the harvest has to go through preset form instead.

### F1. One deliberately broken zone

| # | File | Question | What to report |
|---|---|---|---|
| F1 | `build/Q7_bad_zone.adg` | Chain 2's zone is inverted: Min 120, Max 20, crossfades outside both | Does it load? Repaired, refused, or loaded broken? |

A refusal is a RESULT here, not a problem. It decides whether the DSL has
to guard the invariant or can leave it to Live.

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

**T8. DECIDE WHAT SLOTS 5 AND 6 MEAN INSIDE A DRUM PAD.** A design call,
not a task. Nobody else can make it and the code is sitting on a
placeholder.

`PATCHBAYGROUND.md`, "What a slot means may depend on depth", records it as
undecided and calls it the sharpest open question in the DR1 design. The
two answers:

- **One meaning per rack, whatever the depth.** What the code does today.
  Muscle memory is the product and a knob that changes meaning as you dive
  is the thing muscle memory cannot absorb.
- **Meaning per LEVEL.** Slots 5 and 6 become the two sends at kit level
  and the FM pair inside the sound. Buys four controls with no page flip,
  and spends the one property the layout exists to guarantee.

Three things now bear on it that did not when it was written. Slot 6 is
already a per-rack role rather than a fixed meaning, so meaning varies by
RACK and the question is only whether it may also vary by DEPTH. Labels are
local, so a pad can SAY what its slot 5 does. And round D showed the
conservative branch is not free: the first knob inside every pad is dead,
and the kit and pad rows are offset by one.

*Wants Q6 either way: the kit-level sends are FX selectors, not send
levels, and nothing wires them yet.*

**T10. DECIDE WHETHER TO PORT TO TYPESCRIPT.** A design call, not a task.
`TS-PORT.md` is the analysis: the XML layer round trips losslessly in
`@xmldom/xmldom` at 70 ms, the donors fit a browser at 300 KB, and three of
the arguments on both sides turned out to be void. What survives is that
the only reason to switch is a browser-hosted version, and the strongest
objection is samples, which a browser cannot stat.

*One cheap thing first: Pyodide ships lxml, so the existing compiler may
run in a browser unchanged. Twenty minutes to find out, and it would make
the whole question moot.*

*`TS-PORT.md` predates the DSL migration and quotes the old syntax. What it
measures is the XML layer, which did not move, so the analysis stands.*

**T1. Drum rack return chains.** The pad half is done: `Rack.pad` takes a
note and a content, zone distribution skips pads, and DR1 builds eight pads
each holding a rack of eight samples. What is left is the RETURN side,
which nothing in the DSL reaches: a drum rack's return chains, their
per-pad send levels, and a selector across several reverbs and delays.
*Wants Q6. Shares its mechanism with C1, so do C1 first and this gets
cheaper.*

**T6. Decompile a saved rack into DSL source.** `patchbay extract` emits
DSL for a `.adg` and round-trips all six racks exactly; see `DSL.md`. What
is left is finding racks inside a Set, and putting names on the slots.

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

## Open spikes

None is a kill criterion. The project works without any of them.

**Q6. Return selectors.** `PATCHBAYGROUND.md` wants each DR1 return chain
to hold a selector across several reverbs and delays, so a macro swaps the
EFFECT rather than the send level. The pieces are known separately, the
combination is untested. **C1 is the same mechanism one level up**, so
building AFX1 answers most of this for free.

**Q17. Meld's glide mode.** `MeldVoice_Engine{A,B}_GlideMode` reads 0 and
the enum is undiffed, so LD1's Macro 6 moves Meld's glide TIME and glides
nothing. The last of the mapped-but-switched-off family. Load
`build/LD1.adg`, turn glide on for engine A only, save `racks/q17_a.adg`
and the off twin as `racks/q17_b.adg`.

**Q2. Aftertouch.** `PATCHBAYGROUND.md` wants aftertouch on filter and
pitch for every sound, excluding drum pads. Nothing is known about how it
is stored. Probably a sibling of the `KeyMidi` mechanism, since that
already encodes MIDI, but that is a guess. Diff a rack before and after
mapping aftertouch to one parameter: `racks/q2_a.adg` / `_b.adg`.

**Q3. Key and velocity zones.** S5 settled chain-select zones. Key and
velocity zones are Instrument Rack only and are PRESUMED siblings of
`BranchSelectorRange`. Do not assume it in code until diffed. Save an
instrument rack with two chains, drag a key zone, then a velocity zone,
one save each: `racks/q3_key_a.adg` / `_b.adg`, `racks/q3_vel_a.adg` /
`_b.adg`.
*Blocks: multi-sampled racks, and SR1 with them.*

**Q7. Zone ordering violations.** `Min <= XfMin <= XfMax <= Max` is the
invariant. Untested whether Live repairs or rejects a file that breaks it.
F1 above is the check.

**Q8. Send taper.** Sends are linear amplitude from 0.000316 to 1, but
whether the knob is linear in amplitude or in dB is unknown. Only matters
if a spec ever states send levels as knob percentages.

**Q9. Set form versus preset form.** Whether a device node is serialised
identically in a `.als` and a `.adg`. K3 is the cheap probe; T6c needs the
full answer.

**S10 tail. Macro mapping range from the UI.** Live 12.4.3 has no macro
range editor, so the reverse test at `build/s10_range_test.adg` is prepared
and unrun: write a narrowed `MidiControllerRange`, load it, and see what
the UI shows. Load `build/PD1.adg`, right-click Macro 3, report what the
range UI offers.

**Q5 tail.** Whether Live keeps or strips `MacroHasValue.N` on an unmapped
macro. Save `build/probe_q5_unmapped.adg` back out of Live to
`racks/q5_b.adg` and diff. Cheap, and nothing depends on it.

## Standing manual work

Not backlog. These do not get automated, and trying is how the project
fails. **A check that asks whether something SOUNDS right belongs here, not
in the backlog above.** Several did, for a while, and reading them as tasks
is what made the project feel bigger than it is.

- Choosing which samples are good. A generator cannot judge a kick.
- Sound design judgement. Generate wide, audition, cull.
- Gain staging and mix balance. The `PEAK_DB` table is worth about 3 dB and
  will not get better without a repeatable signal instead of a played note.
- Whether one knob feels comparable across engines. The RANGES that make it
  so are declared and tested; whether the result is musical is ears.
- Assembling the Set: eight tracks, naming, routing, returns, tempo. Half
  an hour, once. See `THE_BASEMENT.md` for why this is not automated.
- Sidechain source. Absent from the LOM and not found in the file format.
  One setting per track, not a system.
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
