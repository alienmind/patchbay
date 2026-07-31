# The basement

Where bad ideas are buried. Every entry is something this project tried,
planned or believed, and then stopped: an approach abandoned, a theory
disproved, a spike retired unrun.

It exists so nobody digs the same hole twice. An entry says what was
attempted, what killed it, and what replaced it. Nothing here is a live
question. Live questions are in `TODO.md`.

## Generating `.als` from scratch

**Planned as KICKOFF Phase 6, with spike S11 to reverse-engineer Set
structure.** Dropped before either started.

Live's API *does* expose `create_audio_track`, `create_return_track`,
`output_routing_type` and `output_routing_channel`, verified against Live
12.4.3's own `_MxDCore/LomTypes.pyc`. The `ableton-mcp` remote script had
simply not wired them up.

So Set structure never needed reverse engineering. Adding command handlers
to a remote script is smaller work and survives Live updates, which `.als`
generation would not. The `sets/` folder and its spike were deleted
unbuilt.

**Replaced by:** `live_set.py`, and the entry below on the whole MCP half.

**And then partly dug back up.** The reasoning above holds for what the API
CAN do, and it turned out not to cover the one thing the Set needed most:
placing a rack. That goes through the browser, and the browser is a startup
snapshot, so a rack generated after Live launched cannot be loaded into it.
`patchbay session` writes the Set instead - `live_set.py`, Q30 - and Set
structure did need mapping after all, though Q9 had already done most of it
for reading. `.als` generation from NOTHING is still not what happens: the
tracks, returns and branch shapes are templates read from Live's own
factory content at build time.

## The 13 slot macro layout

`PATCHBAYGROUND.md` specified thirteen named slots: Engine, Cutoff,
Resonance, Decay, Drive, Movement, Space, Character on page one, then
Glide, Detune, Delay, Width, Transient on page two. Slots 14 to 16 were
left deliberately unnamed.

Two things killed it.

**Page two is not reached during a jam.** Push shows eight macros at a
time. A page flip mid-performance costs more than the five extra knobs are
worth, so slots 9 to 13 were paid for and never spent.

**`Space` was on the wrong device.** A reverb send belongs on the channel
strip, not on the instrument rack, and putting it in the instrument
layout spent one of only eight useful knobs on something the strip
already carries.

**Replaced by** the eight slot layout in `PATCHBAYGROUND.md`, with slots
1, 2, 7 and 8 fixed across every rack (Instrument, Sound, Release, Volume)
and 3 to 6 as per rack character. Volume and Release are new; they were
absent from the thirteen and are the two most universally wanted knobs.

`examples/patchbayground.py` still declares the thirteen. Reconciling it is
open work, noted under Current state in `PATCHBAYGROUND.md`.

## "Grammar" as the name for the macro layout

**Tried:** calling the shared, ordered list of macro slots a Grammar. The
word entered as prose, a `## Macro grammar` heading in the first draft of
the target spec, and was promoted to a class 15 commits later without
anyone re-examining it.

**What killed it:** it describes something the object does not do. A
grammar has production rules, composition, recursion and a notion of
well-formedness. A layout has a fixed length, an order, and names. Nothing
is parsed and nothing is generated. The tell was in the documentation:
every place that had to be precise wrote "a Grammar is a contract, not a
template", which is a name doing negative work.

Worse in context. The project describes itself as a Python DSL, so a reader
meeting `Grammar` reasonably assumes it is the grammar of the language.

**Traced first, then renamed.** The suspicion was that the word came from
PLAYGRND. It did not: the only document assembled from PLAYGRND material,
since deleted, used "grammar" twice and both times in our own analytic
voice. What is observable there is slot LABELS in caps, `FILTER & RES.`,
`SOUND`, `VOLUME`, and no word at all for the system they belong to.

**Replaced by:** `Layout`. See `DSL.md` for the QWERTY argument. Also
considered and rejected: `Schema`, which collides with `SCHEMA.md` and with
Ableton's own XML schema; `Mapping`, which collides violently with macro
mappings, the `KeyMidi` mechanism; `Template`, which the docs had already
rejected in prose; and `Contract`, which is accurate and reads like a
compliance document.

## ableton-inspector as a dependency

Evaluated twice: once as a way to read Sets, and again as the reading half
of a rack extractor.

Read only, `.als` only, and its schema coverage stops well short of devices
and racks. The second look was the decisive one: extracting racks needs
exactly the part it does not cover, and the part it DOES cover is
`gzip.open` plus `etree.fromstring`, which is 17 lines in `io.py` and
already accepts `.als`.

A dependency that reads the easy half and not the hard half is a
dependency that costs more than it returns.

**Replaced by:** `io.py`, and `TODO.md` T6 for the emitter, which no
external library could supply because the DSL is ours.

## Sidechain source, at any level - WRONG, and dug back up

**The claim was:** absent from the Live Object Model, and not found in the
file format either, so it stays manual at one setting per track. It carried
its own revisit condition: *"Revisit only if that proves annoying in
practice."*

**The LOM half stands. The file format half was wrong.** Reading the
indexed `Compressor2` donor rather than searching for the word
"sidechain" turns up the whole mechanism:

    SideChain/OnOff                                    parameter, false
    SideChain/DryWet                                   parameter, 1
    SideChain/RoutedInput/Volume                       parameter, 1
    SideChainEq/On /Mode /Freq /Q /Gain                parameters
    SideChain/RoutedInput/Routable/Target              AudioIn/None
    SideChain/RoutedInput/Routable/UpperDisplayString  No Output

Everything but the source is an ordinary parameter, settable today. The
SOURCE is a plain `Target` string, which is the same shape as Drift's
routing: a value with no `Manual`, invisible to `find.params` and to
`library.Device.search`.

**Why it was missed:** the search was for a device or a parameter named
after the feature. The routing lives under `RoutedInput/Routable`, which
names the mechanism rather than the feature, and the enable is three levels
down a path. The same mistake as Q16, made twice: a control that is not a
parameter does not answer a parameter search.

**Where it went:** `Q18` in `TODO.md`. What remains genuinely unknown is
what `Target` holds when it points at a real track, and whether that
reference survives dragging the rack into a different Set. One diff answers
the first; a load answers the second.

## The `OriginalCrc` algorithm

16 bit. zlib plus ten CRC-16 variants over four chunk choices all missed.

Closed as irrelevant rather than solved: S7 showed nothing reads it on
load. Live re-reads the sample file and recomputes its metadata, so a
path-only rewrite works and the CRC never needs computing.

## Id reallocation on clone

Budgeted as the expensive part of Phase 2, gated on spike S6, with a
fallback plan in case cloning turned out unviable.

Both premises were wrong. S3 showed macro mappings carry no ids at all,
they are addressed by containment, so a cloned chain keeps working with a
verbatim copy. S6 then showed the only id rule is uniqueness among
SIBLINGS. Nothing references ids.

`clone.py` copies subtrees and checks sibling uniqueness. There is no
remapping pass, and there never needs to be.

## "A nested rack cannot be lifted out"

The DSL originally scanned `racks/` for a skeleton and would take a
`GroupDevicePreset` from inside another rack's chain. That produced a file
which passed every check the tooling has and which Live refused to accept
as a drop, without ever loading it.

Stated as a structural claim - that Live serialises a nested rack
differently, or records its parent somewhere - it was wrong. The nested
subtree is byte for byte usable. It keeps the `Id` it carried among its
`DevicePresets` siblings, and a top-level `GroupDevicePreset` must have no
attributes at all. One attribute, and the drop is refused.

The guard that accepted only top-level skeletons is gone, replaced by
stripping the `Id`. See S13 in `SCHEMA.md`, and `ARCHITECTURE.md` §3.

**What made it hard to see:** the comparison was between a broken file and
a working one that also differed in what it contained, so the one fact was
buried in hundreds. Building the *same rack twice* and changing only the
skeleton's position reduced it to three facts, two of them cosmetic. When
a diff is too big to read, the fix is a better pair of files, not a
closer reading.

## `PresetRef` as the reason a lifted-out rack was refused

The standing suspect while the above was open. A nested rack's
`AbletonDefaultPresetRef` has `RelativePathType=0` and empty `Path` and
`RelativePath`, while `racks/s1_source.adg`'s top-level drum rack points
at the factory device with `RelativePathType=7`. A tidy theory followed:
Live resolves which device to instantiate from that path when accepting a
drop, and an empty one cannot be resolved.

Dead on inspection. `racks/s3_a.adg` and `racks/s7_a.adg` are top-level
racks Live saved with exactly the empty shape, and `build/PD1.adg` has it
too and was already gated in Live. A never-saved rack simply has nothing
to point at. The `RelativePathType=7` case is a rack still carrying its
factory default, not a requirement.

## The sample cache-key theory

S7 produced an intermediate variant that appeared to fail, which fit a
tidy theory: Live keys its sample cache on size or CRC, so an inconsistent
FileRef would be rejected.

The file had been double-clicked instead of dragged. A second Live
instance hangs for a few seconds and loads nothing, which looks exactly
like rejection. The theory was retracted and the ground rule written down:
drag into a running Live, and check `Log.txt` for `CommandLine` and
`Another instance` before concluding anything.

## Byte comparison of two `.adg` files

Used once as a fidelity check for the round trip. Two semantically
identical files differ by about 4 percent, because Live writes CRLF and
`<X />` and lxml does not.

S1 established that Live tolerates lxml's serialiser conventions, so byte
identity was never the requirement. `patchbay diff` compares the parsed
tree instead, and the noise floor after filtering is zero.

## "A partial device will not load"

The donor pattern was adopted on the assumption that a device node missing
parameters would either fail or load with silent wrong defaults, making
donors mandatory.

S12: a device loads with ALL 18 of its parameters deleted. Live fills in
whatever is absent.

Donors survive for a different reason than the one they were adopted for.
They carry configured values and tell you what a device can be asked to
do, so they are about fidelity, not loadability. Generators may write
partial device nodes.

## The mutating DSL: `bind`, `nest`, engine functions and slot strings

**Tried:** the first rack DSL. A rack was mutated in place, a chain came
from `rack.engine(name, tag)` inside a `with` block, and every relation
went through one verb:

```python
PATCHBAYGROUND = Layout("Instrument", "Sound", "Filter", ...,
                        selector="Instrument",
                        start={"Filter": 127, "Volume": 127},
                        labels={"Instrument": "> Instrument"})

rack = Rack("PD1", PATCHBAYGROUND, kind=RackKind.INSTRUMENT,
            labels=paired("attack"))
with rack.engine("FM", "Operator") as e:
    e.bind(filter=[("Filter/Frequency", *CUTOFF),
                   ("Filter/Resonance", *RESONANCE)],
           release=("Operator.0/Envelope/ReleaseTime", *RELEASE_MS))
rack.nest("PADS", pd1()).bind(filter="filter")
```

It built all six racks of `examples/patchbayground.py` correctly for the
whole of Phase 0 to 5. It was replaced because of what it cost to READ and
to EXTEND, not because anything it wrote was wrong.

**What killed it**, in the order the costs showed up:

- **`bind` was four relations under one name.** `e.bind(filter="...")`
  mapped a slot to a device parameter; `n.bind(filter="filter")` mapped an
  outer slot to an inner one. The value was `str`, or `(path, lo, hi)`, or
  a list of either. All four were the same shape at the call site, and
  which one a line meant depended on whether its receiver came from
  `engine()` or from `nest()`.
- **A slot name was a string in four places.** `selector=`, `start={}`,
  `labels={}` and every `bind` keyword each named the slot again, and each
  did its own typo check. A layout declaring `start={"Filter": 127}` said
  "Filter" twice within three lines. Slots that are not Python identifiers
  were worse off: `KIT` declares `Send A`, `Send B` and `Send Vol`, and
  none could be written as a keyword.
- **There was no value for "how a device answers to the layout."** That is
  the thing this project is about, and the spec had to express it as five
  functions that take a rack, mutate it and return it.
  `meld(drift(wavetable(rack)))` is a rack read inside out, and the profile
  could not be shared, extended or inspected.
- **The wildcard role was threaded by hand.** Five engine functions carried
  a `character: str | None` parameter, a module-level `WILDCARD` table
  mapped role to path per device, and a `_bind` helper filtered the misses.
  The role was then stated two to four times per rack.
- **Ranges were anonymous tuples doing arithmetic.** `("Filter/Frequency",
  *CUTOFF)` splatted a pair into a triple, `RELEASE_MS = tuple(v * 1000.0
  for v in RELEASE)` rebuilt one by comprehension, and a trim helper
  returned another to be splatted again. Nothing said which was Hz and
  which was dB, which is exactly what Q14 cost a rack to find out.
- **Deriving a layout copied dicts by hand.** `PAD = Layout(*PB.slots,
  selector="Sound", start=dict(PB.start), labels=...)`. A derivation that
  forgets `start=` produces a rack that loads silent, and nothing says so.
  It happened, by accident, while testing something else.

**One rule reversed on the way.** A second `bind` of a slot REPLACED the
first, because a bulk keyword call reads as an edit. `.drives` on the same
slot ACCUMULATES, because a per-slot call reads as a second mapping, which
is what the Meld case wants. Neither rule is more correct; each matches
how its own call site reads.

**Replaced by:** `Slot`, `Range`, `Layout`, `Engine`, `Rack` as they are in
`DSL.md`. The migration was gated on output identity rather than on
judgement: all six racks, DR1's 178,960 facts included, digest identical
before and after, so not one Live check was asked for at any step.

**Two shapes went with it and are not coming back.** `pad(name, note,
device=...)` versus `pad(name, note, rack=...)` became one positional
argument, because the outer rack does not care which it got and the two
keyword form could be given both or neither. And the `with rack.engine(...)
as e:` block bought scoping for an object that was already mutable and
already appended to the rack, so it read as a transaction and was not one.

## `>` as the mark for a stepping macro

**Tried:** prefixing the chain-selector slot's label with `>`, so
`Instrument` read `> Instrument` and a drum pad's `Sound` read `> Sound`.
Slot 1 STEPS between chains where every other knob SWEEPS, nothing in the
file format distinguishes the two on a display, and a player wants to know
which is which before touching it.

**What killed it:** round I in Live 12.4.3 and on Push 3, three results at
once.

- On Push the whole label rendered, `> Instrument` and all eight others,
  no truncation. The mechanism worked.
- In Live's rack panel the field is narrower and it came back
  `> Instrum`. The mark cost two characters on the one field that
  truncates, so it bought a display problem rather than solving one.
- Asked directly whether `>` reads as "this one steps", the answer was
  that it does not stand out at all.

So it was paid for and not delivering. Dropping it puts `Instrument` back
inside the field, or near enough that Live clips it to `Instrumen`, which
is readable in a way `> Instrum` is not.

**What survives:** the LABEL mechanism itself, which is worth more than the
mark ever was. It carries `Filter + Res` on the paired slot, and the
wildcard's actual role per rack, `Attack` on PD1 and `Morph` on BS1 in the
same position. Both rendered whole on Push and both are things a player
cannot get from the knob's position.

**Not tried, and still open:** a shorter name for slot 1. `Engine` fits
Live's field whole and is what the slot selects, but the eight slot names
are gated and renaming one reopens `PATCHBAYGROUND.md`, `DSL.md` and
`README.md` with it.

## `ableton-mcp`, the Live API, and the whole MCP half

**Dropped, routed around, and now removed.** The submodule is gone,
`mcp/remote_script_additions.py` is gone, and `doc/MCP.md` is gone: this
entry is all that is left, because everything that file established still
matters and nothing it proposed survived.

### The capability table, which is why this project exists

Read off Live 12.4.3's own bundled scripts at
`Resources/MIDI Remote Scripts`, in particular `_MxDCore/LomTypes.pyc`,
which enumerates the Live Object Model. A symbol present in that table
means the API exposes it; absent means it does not exist, not that we
failed to find it.

| operation | LOM | consequence |
|---|---|---|
| `map_parameter`, `macro_mapping`, `mapped_parameter`, `mappings` | **absent** | macro mappings cannot be created or read via the API |
| `add_chain`, `delete_chain` | **absent** | chains cannot be created or removed |
| `zone` | **absent** | chain, key and velocity zones are not reachable |
| `chains`, `return_chains`, `drum_pads`, `chain_selector` | present | existing structure is READABLE, not constructible |
| `add_macro`, `remove_macro` | present | changes the macro COUNT only, `NumVisibleMacroControls` |
| `randomize_macros`, `selected_variation_index`, `store_variation` | present | variations can be stored and selected, but not named |

**That table is the premise of the whole project.** Rack structure, macro
mappings, chain zones and variations are unreachable from the API, so
writing the file is not a workaround, it is the only route. The plan was to
drive a running Live over the remote script's socket: create the tracks,
name them, load each rack onto the right one, set the tempo.

**What killed it, first time:** the trade. Assembling eight tracks by hand
is half an hour, once, and automating it would have spent the most fragile
component in the project - a third-party submodule tied to Live's remote
script API - on the least repetitive work there is.

**What killed it a second time, when it was tried anyway:** Live's browser
is a snapshot taken at startup. `load_browser_item` is the only way the
remote script can put a device on a track, it takes a browser URI, and a
rack written to the User Library after Live started is not in the browser.
Neither is a file dropped into a folder Live has already indexed, so it is
the index rather than the folder. Verified against a running Live 12.4.3
by polling for a file that never appeared. A toolchain whose whole job is
generating racks cannot load the racks it just generated without restarting
the thing it is driving.

**What replaced it:** `patchbay session`, which writes the `.als`. Q30 has
what that cost - one tag rename, a send seeded per return on every track -
and `live_set.py` is the module. Q9 had already mapped Set form to preset
form for reading, so writing was the same map backwards.

**The verification harness went with it.** The smoke test was: generate a
rack, have MCP load it onto a track, read the device tree back with
`get_track_info`. Step two is the browser step, so it never ran. What was
usable, reading back a Set opened by hand, is not worth a submodule and a
socket, and it could never confirm a macro mapping anyway because
`mapped_parameter` is not in the LOM.

**`create_audio_track` and `create_return_track`** were written into
`mcp/remote_script_additions.py` so MCP could build the Set. The Set is a
file now, and both are deleted rather than kept warm.

**The part of the original reasoning that did NOT survive:** output
routing into PM1 and the sidechain source per track were called permanent
dropdowns here, on the grounds that both are absent from the LOM and from
every factory Set. The second half was true and the conclusion was not. One
Set saved by hand with a track routed into another and a compressor
sidechained said what both are, and `patchbay session` writes them: Q33.

**So the whole entry now reads as one lesson.** Twice this concluded that
something was not writable, and twice the evidence was one file away.
Absence from the LOM says nothing about the FILE, and absence from Ableton's
own content says only that Ableton never shipped an example.


## The per-engine loudness trim, `PEAK_DB`

**Built, gated in Live, and removed anyway.** The spec file carried a table
of measured output peaks, one per engine, and derived a correction against
one target so that Macro 8 full right meant the same LOUDNESS on every
engine rather than the same gain SETTING.

Measured at Macro 8 full right, Live 12.4.3, on LD1 and BS1. Kept here
because they were expensive to take and they are real:

| engine | peak at unity | correction to -8 dBFS | range top |
|---|---|---|---|
| Operator | +4.4 dB | -12.4 dB | 0.240 |
| Wavetable | -4.0 dB | -4.0 dB | 0.631 |
| Meld | -6.8 dB | -1.3 dB | 0.866 |
| Drift | -5.8 dB | -2.2 dB | 0.776 |

Operator's figure is derived rather than read: at unity it clips and a
pinned meter reports nothing, so it was measured at -1.62 through a -6 dB
trim. Meld was measured twice on two racks, -6.74 and -6.75, which is what
says these are engine properties rather than patch properties.

**What killed it.** It is a measurement by ear, in one Set, on one set of
patches, and the DSL declares STRUCTURE. Nothing in the spec can state it,
no test can check it, and a Simpler figure would only hold for the sample
it was measured with. The table also read as settled fact in a file whose
other numbers are all derived from parameter ranges, which is the wrong
company for a number somebody heard once.

**Replaced by:** volume ranges capped at each engine's own unity, and
nothing else. Gain staging is mixer work and is listed under standing
manual work in `TODO.md`, beside sample choice and sound design judgement.

**What survives:** the reasoning about a CEILING, which is not taste.
Wavetable's `Volume` and Drift's `Global_Volume` both max at 1.0 amplitude
natively, so neither can be pushed above its own unity by a range whatever
the range says. Any future target above -4 dBFS is unreachable for two of
the four engines.

## Porting to TypeScript

**Analysed, measured, and decided against.** `TS-PORT.md` is the analysis
and it stands: the XML layer round trips losslessly in `@xmldom/xmldom` at
about 70 ms, the donor library fits a browser at 300 KB, and three of the
arguments on each side turned out to be void once measured rather than
asserted.

What the analysis left was one reason to switch and one objection. The
reason was a browser-hosted version, which nothing on the backlog asks for.
The objection was samples: a browser cannot stat a file, and
`Engine.sample` refuses a path that is not a file precisely because Live
loads a missing sample as an offline rack that passes every check and makes
no sound. DR1 is 64 sample bindings.

**Decided: no.** The port buys a capability nobody has asked for and
spends a working, gated toolchain to get it.

**What survives:** `TS-PORT.md` stays as the measurement. If a
browser-hosted version is ever wanted, Pyodide ships lxml and running the
existing compiler unchanged is the cheap thing to try first.

## `Rack.sending`, buried on a false negative and dug back up

**Built, shipped in DR1, buried by one knob turn, and restored by another.**
A `Send` is shaped exactly like a mappable parameter - `LomId`, `Manual`,
`MidiControllerRange`, `AutomationTarget`, `ModulationTarget` - and
mappings are addressed by containment, so writing a `KeyMidi` into one
should give a kit-level knob for how much of the whole rack reaches a
return.

The first check said no: the file was valid, the mapping resolved,
`patchbay mappings` listed it, Live loaded it, and every send stayed at
-inf. That was written up as Q23 and the verb was deleted.

**What killed the burial:** Live writing the same mapping by hand.
`racks/q23_a.adg` against `racks/q23_b.adg` is one macro mapped to one
chain's Send A in Live's own UI, and it is a `KeyMidi` inside the `Send`
element, channel 16, macro index as the CC. Reproducing it with
`params.map_to_macro` gives a file `patchbay diff` calls identical to the
one Live saved, and the knob sweeps the send.

**What it cost:** a release with the feature deleted, a rewritten `DSL.md`
section, a README line that told users a send takes no macro, and a spec
comment explaining a limit that did not exist. All of it from one check that
was read as proof of impossibility rather than as one file failing.

**What it bought, and this is the part worth keeping:** the rule that a
check which finds nothing has TWO readings. Live ignoring what we wrote is
one. Us writing it somewhere Live does not look is the other, and the second
is not visible from the file. A negative result closes a question only when
something known-good produces the same file - which for a Live construct
means Live making it, and diffing.

## Aftertouch as something a rack file carries

**Never built, and the spike was called off rather than run.** Q2 asked for
a diff of a rack before and after mapping aftertouch to a parameter, on the
theory that it would be a sibling of the `KeyMidi` mechanism, which already
encodes a virtual MIDI CC.

**What killed it:** there is nothing to diff. In Live 12.4.3 aftertouch
reaches a rack macro one of two ways, and neither is a field in the preset:

- **MPE Control**, a MIDI effect placed BEFORE the rack, whose Pressure
  output is mapped to a macro. The routing belongs to that device and to
  the track it sits on.
- **MIDI Map mode**, Ctrl+M, macro clicked, key pressed hard. That is a
  MIDI mapping in the SET, the same class of fact as the sidechain source
  in Q18: not in the `.adg`, so not authorable here.

So `PATCHBAYGROUND.md` asking for aftertouch on filter and pitch for every
sound is asking for a DEVICE in the strip plus a mapping per Set, not for a
parameter on the instrument racks. Adding MPE Control to ARP1 or MFX1 is an
ordinary declaration and needs a donor harvested for it; the mapping stays
manual, beside picking the sidechain source.

**What it cost:** nothing. Two saves not spent.

## Meld's glide as another switched-off modulator

**A theory, held for three rounds, and wrong.** LD1's Character knob moves
`MeldVoice_EngineA_GlideTime` and glide was not heard, which matched the
Q16 family exactly: Operator's `Lfo/LfoOn`, `Filter/LfoOn` and
`Globals/PortamentoOn` are all switches that must be written beside the
binding. Q17 was raised to find Meld's.

**What killed it:** Meld has no glide switch. The device carries exactly
two glide parameters per engine, `_GlideMode` and `_GlideTime`, and
`GlideMode` is `Porta | Gliss` - two behaviours, no off. `racks/q17_a.adg`
against `build/LD1.adg` is the one-line diff.

**What replaced it:** nothing to fix in the binding. The knob reaches the
parameter that owns the feature. Why the result was inaudible is a question
about Meld's voicing, and it is ears, not structure.

**What it cost:** two saves, and it closed the mapped-but-switched-off
family at five members instead of leaving a sixth open forever.
