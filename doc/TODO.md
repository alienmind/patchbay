# TODO - the live backlog

The only place that says what is in flight. Everything else in `doc/` is
settled knowledge.

Work happens HERE: pick a task, move it to In progress, update its status
as you go. When it is done, it leaves this file. It does not stay as a
completed entry. See "The routine" at the bottom.

Live version for every finding below: **12.4.3**.

## What is left, at a glance

Everything below this table is detail. **You** means a human in Live;
nothing in that column can be done from code.

| # | Who | Task | Unblocks |
|---|---|---|---|
| **K3b** | you | Drag `build/K3_als_donor.adg` onto an AUDIO track. Loads clean? | 48 donors, and with them C1 to C4 |
| **F1** | you | Drag `build/Q7_bad_zone.adg` onto a MIDI track. Repaired, refused, or broken? | Whether the DSL guards the zone invariant |
| **C1** | code | AFX1: eight effects behind one selector | The last big tedium. Answers Q6 on the way |
| **C2** | code | ARP1 and MFX1 | Channel strip |
| **C3** | code | EQC | Channel strip |
| **C4** | code | Sidechain config on every track and return | The tedium this was reopened for |
| **T8** | you | DECIDE: do slots 5 and 6 change meaning inside a drum pad | DR1's final shape |
| **T10** | you | DECIDE: TypeScript port, or not | Nothing. Here so it is not decided by drift |
| **T1** | code | Drum rack return chains | DR1's sends. Cheaper after C1 |
| **T6c** | code | Read racks out of a `.als`. Needs Q9 finished first | Turning Sets you own into specs |

Optional spikes, none blocking: **Q17** (Meld glide mode), **Q2**
(aftertouch), **Q3** (key and velocity zones, needed only for SR1), **Q8**
(send taper), the **S10** and **Q5** tails.

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
*Donors: all 11 candidates are indexed.*

**C2. ARP1 and MFX1.** Two small MIDI racks, every device indexed.

**C3. EQC.** Five devices, carrying Lo-Hi EQ, EQ dry/wet, compressor
dry/wet, gain, and the sidechain. Every device indexed; Utility is
`StereoGain`.

**C4. The sidechain, on every track.** This is the tedious one, and it was
wrongly written off as manual. `PATCHBAYGROUND.md` sidechains EQC's
compressor from DR1 with the sidechain EQ on a low band, so it tracks the
kick and ignores hats, and it does the same on the reverb returns. Eight
tracks plus returns, each with an enable, an EQ mode, a frequency, a Q, a
dry/wet and a source: that is the shape of thing this project exists to
stop doing by hand.

**Everything but the source is reachable today**, as ordinary parameters
that `sets` writes:

    SideChain/OnOff                       the External toggle
    SideChainEq/On /Mode /Freq /Q /Gain   the low band that ignores hats
    SideChain/DryWet                      how much of the duck lands
    SideChain/RoutedInput/Volume          input trim
    SideListen                            audition the sidechain input

**The source is not automatable, and Q18 settled why.** A device preset
does not carry it: `Target` reads `AudioIn/None` in a file saved with the
source pointed at DR1, and a rack dropped into another Set comes back with
the enable ON and the source at `No input`. Picking it is one dropdown per
track, by hand, and it is on the Standing manual work list. See Q18 in
`SCHEMA.md`.
*Ready to build. Nothing blocks it.*

### K3b. One file to load

| # | Do this | Should happen |
|---|---|---|
| K3b | Drag `build/K3_als_donor.adg` onto an AUDIO track. Three chains: Auto Filter, EQ Eight, Echo | Loads, all three devices present and normal. Macro 1 sweeps the Auto Filter cutoff |

Live refuses a drop of the wrong kind before it reads the file, so a
refusal on the wrong track type says nothing about the file. This one is an
`AudioEffectGroupDevice` and wants an audio track.

**K3 has fired twice and caught a different defect each time.** Both are
Set form leaving something behind, both are fixed in `_make_chains`, and
both are guarded by `clone.assert_loadable`. Evidence is under Q9 in
`SCHEMA.md`.

| refusal | what was wrong | affected |
|---|---|---|
| *Not all list members have Ids* | the device node carried no `Id` | 48 of 56 donors |
| *Unexpected value for int64 node* | `OriginalFileSize` and `OriginalCrc` blank on the device's `LastPresetRef` | 42 of 54 donors |

The second hid behind the first, and behind our own tool: `patchbay diff`
hides `/LastPresetRef/` by default, so no spike pair ever printed the field
that refuses the document.

**K3b is the retest, against a file rebuilt after both fixes.** It does not
prove the two forms are otherwise identical - two differences have now been
found by loading one file, and a third is not ruled out. If it loads, the
donors are usable and the channel strip is unblocked. If it refuses again,
the log names the next one.

### F1. One deliberately broken zone

| # | File | Question | What to report |
|---|---|---|---|
| F1 | `build/Q7_bad_zone.adg`, onto a MIDI track | Chain 2's zone is inverted: Min 120, Max 20, crossfades outside both | Does it load? Repaired, refused, or loaded broken? |

A refusal is a RESULT here, not a problem. It decides whether the DSL has
to guard the invariant or can leave it to Live.

**The file is an `InstrumentGroupDevice` and needs a MIDI track.** Dropped
on an audio track Live answers *"Only audio effects can be loaded on an
audio track"* without reading it, which is a fact about track types and not
about the zone.

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
