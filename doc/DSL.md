# The rack DSL

Embedded in Python. A spec is a module that imports from `patchbay.dsl` and
declares racks as values, so a loop or a comprehension describes them as
readily as a literal does.

## Why a DSL rather than a config file

`PATCHBAYGROUND.md` line 60: *"This consistency is the actual product, more
than any individual rack."* The macro layout is identical across every
instrument rack. Six racks sharing one layout is a program, not a
document - in YAML you would copy the layout six times and watch it
drift.

Three further pressures point the same way:

**Parameter names are not guessable.** Saturator's Drive knob is
`PreDrive`. Simpler's filter cutoff is
`Filter/Slot/Value/SimplerFilter/Freq`. Operator carries 217 parameters at
paths like `Operator.0/Envelope/DecayTime`. A binding written from
imagination is wrong; one written against the harvested device library is
checkable, and wrong paths fail with a suggestion.

**Variations are combinatorial.** ~692 sounds across 18 engines, generated
by permuting macro values. That is a loop, not a list.

**The sound family constraint is a function.** Variation index N must mean
the same musical idea across every engine. Expressed as data that is a
promise; expressed through a shared layout it is structural.

## The shape

```python
PUSH = Layout("Instrument", "Sound", "Filter", "Drive",
               "Movement", "Character", "Release", "Volume",
               selector="Instrument")

rack = Rack("PD1", PUSH, kind=RackKind.INSTRUMENT)

with rack.engine("FM", "Operator") as e:
    e.bind(filter=("Filter/Frequency", 30, 18500),
           character="Filter/Resonance",
           release=("Operator.0/Envelope/ReleaseTime", 10, 20000),
           volume=("Globals/Volume", 0.0003162277571, 1.0))

with rack.engine("Sample", "OriginalSimpler") as e:
    e.bind(filter=("Filter/Slot/Value/SimplerFilter/Freq", 30, 18500),
           character="Filter/Slot/Value/SimplerFilter/Res",
           release=("VolumeAndPan/Envelope/ReleaseTime", 10, 20000),
           volume=("VolumeAndPan/Volume", -36.0, 0.0))

rack.variations(Variation("dark", filter=30, release=110),
                Variation("open", filter=120, release=20))

rack.save("build/PD1.adg")
```

The declaration is not "build a rack". It is **"bind this engine's
parameters to the standard layout"**. Everything else follows:

- one engine is one chain
- chain-select zones are distributed evenly across 0..127
- the layout's `selector` slot drives the chain selector
- the same layout slot means the same macro in every engine, which *is*
  the sound family constraint

## Why it is called a Layout

The object is an ordered list of named slots, plus which one drives the
chain selector, plus where each knob rests. A rack takes one as an argument
and binds its own parameters to it.

QWERTY is the analogy and it is exact. A keyboard layout is shared across
many different physical keyboards precisely so the skill transfers, the
position carries the meaning, and the keycap is local paint. That is this
object, slot for slot, and it is what `PATCHBAYGROUND.md` has claimed from
its first draft: "identical across every instrument rack so muscle memory
transfers".

It was called a Grammar until it was not. A grammar has production rules,
composition and a notion of well-formedness, and this has none of the
three: nothing is parsed and nothing is generated. In a project that
describes itself as a Python DSL the word also reads as the grammar OF the
language, which it never was. See `THE_BASEMENT.md`.

## The selector slot is named, not fixed

`Layout(..., selector="Instrument")` says which slot drives the chain
selector. It defaults to `"engine"` and may be `None` for a layout with
no selector at all, such as a drum kit whose macro 1 is Tune.

This was hardcoded to `"engine"` once. Renaming the slot then produced a
rack that compiled, passed every check the tooling has, loaded in Live,
and whose first macro moved nothing, because the code silently found no
slot to map. A layout is a contract the caller writes; the library must
not also assume one of its words.

## A chain may name its own sample

```python
with rack.engine("Kick", "OriginalSimpler") as e:
    e.sample("samples/kicks/ebm_01.wav")
```

Path only. S7 established that Live re-reads the file on load and
recomputes duration, sample end and the loop ends, so the other 18 facts a
real swap moves in Live are its own bookkeeping. Nothing computes a CRC.

Two refusals, both because the alternative is silent:

- **A path that is not a file raises at declaration.** Live loads a
  missing sample as an offline rack, which passes every check this tooling
  has and makes no sound.
- **A device with no `SampleRef` raises at build.** Pointing a sample at
  Operator is a mistake, not a no-op.

Both FileRefs move together, the live reference and the provenance one
under `SourceContext`. In a donor they routinely point at DIFFERENT files,
so writing only the first leaves the second naming a sample this rack no
longer plays.

Naming the sample a chain ALREADY plays writes nothing at all. Flattening
a donor's own pair to say the same thing in our form would discard the
provenance ref for no gain, and it showed up as a difference the moment
`patchbay extract` started round-tripping racks.

## A chain may state where on the selector it answers

```python
with rack.engine("Wave", "InstrumentVector") as e:
    e.zone(0, 63)
```

The default is an even share of 0..127 among the chains that are not pads,
which is what a generated rack wants and what every rack in
`examples/patchbayground.py` uses. This is for the rack that was not
generated: a hand built one whose chains overlap, or divide unevenly, or
leave a dead band. It is also what makes such a rack survive `patchbay
extract`.

Declaring it on ONE chain makes the whole rack explicit, and a chain left
out then raises. The alternative is a rack that mixes a stated bound with
an even share computed from a different chain count, which puts a chain
somewhere nobody wrote.

## A slot is only as consistent as its ranges

Two engines binding the same slot to their own equivalent parameter
satisfies the sound family constraint and is still not enough.

PD1's Volume slot bound `Globals/Volume` on Operator and
`VolumeAndPan/Volume` on Simpler. Both correct, both the right parameter.
One is linear amplitude bottoming at -70 dB, the other decibels bottoming
at -36. Macro 8 at zero silenced one engine and left the other playing.
See Q14 in `SCHEMA.md`.

So the range argument is not decoration for taste. **Where engines
disagree about units, `MidiControllerRange` is the only place the
agreement can live.** `library.Device.range_of(path)` reports a
parameter's native range without opening Live, which is how the divergence
above was measured after ears found it.

Rule of thumb: bind bare when engines agree about units, bind with a range
when they do not, and assume they do not until checked.

**A shared slot reads 0..127, never Hz.** A macro driving more than one
parameter has no single unit to show, so Live displays the raw macro
position. Every slot in this layout is multiply mapped by design, one
target per engine, so no instrument knob will ever show a unit. That is
the cost of one knob reaching every engine, and it is not
`ForceDisplayGenericValue` (S10), which forces the same display on a
SINGLY mapped macro and cannot undo this.

## A slot may drive more than one parameter

```python
e.bind(filter=[("MeldVoice_EngineA_Filter_Frequency", *CUTOFF),
               ("MeldVoice_EngineB_Filter_Frequency", *CUTOFF)])
```

Meld is two synthesis engines behind one device, and every A-side path has
a B twin. Binding only A produced a rack in which Macro 3 filtered half
the sound and left the other half wide open. Every id was unique, every
mapping resolved, every range was right, and the whole thing was audibly
broken.

So a slot maps to a LIST of parameters, and a single path is the one-item
case. Binding a slot twice replaces rather than accumulates, so a repeated
`bind` call reads as the edit it looks like.

What this is not is a second axis. Both Meld engines move together because
the layout has one Filter knob; an A knob and a B knob would be two slots
out of eight, and a Push page has no room for that.

## A range equalises settings, not loudness

The intersection above gets every engine to the same gain SETTING at the
same knob position. It does not get them to the same loudness, and the
difference is not small: on LD1 with Macro 8 full right, Operator peaks
+6 dB and clips while Meld sits below zero, both at what their own volume
parameter calls unity. What an engine puts out before its volume stage is
a property of the engine.

So a second number per engine. `examples/patchbayground.py` stores the
MEASUREMENT, `PEAK_DB`, and derives the correction from it against one
`TARGET_PEAK_DB`. Measured peaks at Macro 8 full right, Live 12.4.3:

| engine | peak | correction | range top |
|---|---|---|---|
| Operator | +4.4 dB | -12.4 dB | 0.240 |
| Meld | -6.8 dB | -1.3 dB | 0.866 |
| Drift | -5.8 dB | -2.2 dB | 0.776 |
| Wavetable | -4.0 dB | -4.0 dB | 0.631 |

Storing the measurement rather than the correction is what makes the table
re-derivable: change the target and every number follows, and an engine
that gets re-measured is one edit rather than an arithmetic problem. That
paid immediately. Correcting from these figures and measuring again put
Operator, Wavetable and Meld on -8 to within the meter's resolution and
Drift 2.2 dB loud, so Drift's first reading was wrong; the fix was one
number, and every other engine was unaffected.

**There is a ceiling on the target, and it is not taste.** Wavetable's
`Volume` and Drift's `Global_Volume` both max out at 1.0 amplitude
natively, so neither can be driven above its own unity from a range,
whatever a range says. Only Meld and Operator reach 1.995. So the target
can never exceed the quietest engine that cannot be boosted. -8 sits below
that with margin, every correction is a cut, and no correction can
introduce clipping.

Two things this is NOT. It is not a utility device after the rack, which
would cost a device per chain and hide the correction from the declaration
that caused it. And it does not apply to a range expressed in dB, like
Simpler's `-36..0`, where a correction is a subtraction and not a ratio;
that engine also plays whatever sample it is handed, so one measurement
would only ever hold for one sample.

One measurement here was derived rather than read: Operator clips at unity
and a pinned meter reports nothing, so it was measured through a known
-6 dB trim and the trim added back. That is worth knowing before trusting
any figure in a table like this one.

**These figures are worth about 3 dB, and the table does not say what they
were measured under.** Three passes over the same three engines gave
`-4 / -8 / -6.75`, `-8 / -5.78 / -8` and `-7.34 / -8.75 / -12`, on files
that had only the correction between them. A peak read off a played note
depends on the note, the velocity and where the Filter macro sits, because
cutoff is a gain stage; none of that was held fixed. The table did its job,
which was killing a 12 dB spread that clipped, and it will not get past a
few dB without a repeatable signal instead of a played note.

## The slot name and the knob label are two different things

A slot name is doing two jobs that pull apart: it is the KEY a rack binds
against, and it is the WORD on the hardware. `_name_macros` wrote the
layout's name onto every rack, so every rack sharing a layout showed
identical words.

Two cases break that, and neither is cosmetic:

- **A paired slot under-describes itself.** Slot 3 drives cutoff and
  resonance. A knob labelled "Filter" that also moves resonance is lying
  by omission, on the one surface the player actually reads.
- **A selector steps where every other knob sweeps**, and nothing in the
  format marks it. That is a property of the rack, not of the parameter.

So labels are separate, declared on the layout and overridable per rack,
exactly as start positions are:

```python
PATCHBAYGROUND = Layout(..., labels={"Instrument": "> Instrument"})

Rack("KICK", PAD, labels={"Drive": "Drive + Snap"})
```

**Position stays the contract; the word is local.** A kick reading
"Drive + Snap" where a hat reads "Drive" is the same slot, the same
chaining and the same muscle memory. Nothing about what the knob DOES
changes, which is what makes this safe: a label cannot move a mapping, and
a label for a slot that is not in the layout raises.

## A layout says where the knobs open

Binding a slot is half the job. The other half is where the knob sits when
the rack is dropped, and the default answer is the worst one available: an
untouched macro reads 0, a macro at 0 drives its target to the bottom of
that target's range, so a rack that binds Volume and does not place it
loads silent. `ARCHITECTURE.md` has the mechanism and what it cost.

The position belongs to the GRAMMAR, for the same reason the slot names
do. If Volume means one thing on every rack, then where Volume opens is
also one thing on every rack, and a per-rack answer is a chance to get it
wrong per rack:

```python
PATCHBAYGROUND = Layout(
    "Instrument", "Sound", "Filter", "Drive",
    "Movement", "Character", "Release", "Volume",
    selector="Instrument",
    start={"Filter": 127, "Release": 30, "Volume": 127},
)
```

Full right is the NEUTRAL position here, not a loud one, because every
volume binding is capped at unity and every filter binding tops out above
the audible band. Drive and Movement are absent from the mapping because
their neutral is off, which is what 0 already means.

`rack.start(volume=100)` overrides one slot for one rack. Positions are
0..127 like everything else in macro space, and out of range raises rather
than clamps: Live clamps silently, so a 200 would load as a rack that
looks correct and is not what was written.

**A start is written only for a slot the rack actually drives.** Grammars
declare positions for all their slots and no rack binds all of them.
Wavetable leaves Movement unbound; parking that knob at a meaningful
number would show a control that moves nothing, which reads exactly like a
mapping that broke.

## A chain may be another rack

DR1 is three levels deep and VA1 nests a rack per chain, so a chain has to
be able to hold a rack as easily as a device:

```python
rack.nest("PADS", pd1())
rack.nest("KEYS", ld1()).bind(filter="filter", release="release")
```

`nest` is `engine`'s sibling, not a separate construct. Both add one
chain, both get a zone, both take part in `engine_macro`, and a slot a
nested rack answers to counts as driven for variations exactly as a bound
parameter does. So the outer rack does not know or care which kind of
chain it has, and a variation reaches into a sub-rack without saying so.

**Bindings are outer slot to inner slot, and the default is identity.**
That default is the whole argument for one layout: when both racks share
it, `outer.nest(name, inner)` with no arguments chains every slot the
inner rack drives into the matching outer knob. Naming the exceptions is
the only work, as VA1 does by binding around `engine` so the outer knob
picks a sub-rack rather than doing two jobs.

Nothing in the mapping code knows how deep it is. A macro-to-macro mapping
is a `KeyMidi` on the inner rack's `MacroControls.N`, which is an ordinary
parameter node, and `Channel` stays 16 at every depth. So the same code
writes depth 1 and depth 3.

The one thing that *does* change with depth is an attribute: a nested
`GroupDevicePreset` carries an `Id`, and the document's top-level one must
carry none. That is handled in `_nested_preset` and `_load_skeleton` and
is invisible from the spec. It is also the whole of what once made nested
racks look intractable - see `THE_BASEMENT.md`.

## A variation is a vector, not a sound

A `Variation` is a vector over layout slots, in macro space 0..127 - the
only scale a variation has, since Live applies each target's own
`MidiControllerRange` at recall. It names slots, never device parameters:

```python
Variation("dark plucks", filter=30, release=110, character=90)
```

**That is why the sound family constraint needs no enforcing.** Both engines
bind `filter` to their own parameter, so one vector is one sound in each,
and index alignment across engines is structural rather than a rule someone
has to remember. Nothing in the variation code knows how many engines there
are.

A variation is NOT how PATCHBAYGROUND addresses a sound. Nothing maps a
knob to a variation, so a variation cannot be dialled in while a clip
plays; a sound is `(instrument, sound)`, two macros driving two chain
selectors. What a variation carries that a selector position cannot is the
WHOLE vector at once, which makes it the right mechanism for a preset
across the entire layout. See `PATCHBAYGROUND.md`.

Instrument choice is itself a slot, because the layout's selector slot
drives the chain selector and a selector is an ordinary parameter:

```python
Variation("sampled", instrument=rack.engine_macro("Sample"), filter=40)
```

`engine_macro` returns the centre of that engine's zone, from the same
arithmetic that distributes the zones. So a variation selects its own chain,
which is what makes a sound a variation rather than a chain.

Two refusals, both loud:

- a slot not in the layout fails at declaration, so a typo never reaches a
  file
- a slot **no engine binds** fails at build, and the message lists the slots
  that are driven. Live accepts such an entry and moves nothing on recall
  (`SPIKES.md` Q5), so it would read as live and be dead

A built rack always replaces the skeleton's variation set rather than
appending to it. Donors are real racks and may carry variations describing a
different rack entirely.

## What it rests on

Each capability traces to a spike, not an assumption:

| DSL does | because |
|---|---|
| writes mappings as `KeyMidi` in the target | S3: mappings are containment-addressed |
| copies chains without touching ids | S6: only sibling uniqueness matters |
| refuses to write colliding ids | S6: Live rejects the whole preset |
| narrows macro ranges | S10: `MidiControllerRange` is the mapping range, and Live's UI cannot set it |
| distributes zones as bounds with collapsed fades | S5: `Min <= XfMin <= XfMax <= Max` |
| copies devices from donors | S12: partial devices load, but donors carry the configured values |
| strips a skeleton's own macro mappings | those describe how its *parent* drove it |
| writes an `Id` on a nested rack and none on the top-level one | S13: that one attribute decides whether Live accepts the drop |
| chains macros without regard to depth | S4: `Channel` is 16 at every level, depth is not encoded |
| writes variations in macro space, all 16 slots, `MacroHasValue.N` for participation | S8: that is the `MacroSnapshot` shape, and rewriting Live's own diffs at zero facts |

## Verified, not merely designed

`build/PD1.adg`, compiled from `examples/patchbayground.py`, loads on a MIDI
track in Live 12.4.3. Macro 1 sweeps engines across the distributed zones.
Macro 3 drives Operator's `Filter/Frequency` and Simpler's
`Filter/Slot/Value/SimplerFilter/Freq`, both scoped to the declared
30-18500 Hz range.

That is the whole claim of this document demonstrated: one layout, two
synthesis methods, the same knob meaning the same thing in both.

Variations passed the same way. `build/PD1.adg` carries 96, all named and all
recalling; unbound macros stay where they are, and a variation selects its
own engine through the chain selector. The sound family claim was checked by
ear: recall a Sample variation, turn Engine full left, and the same musical
idea arrives through FM with nothing re-set. Live accepts more variations
than the template needs - 256 loaded without truncation.

Nesting passed too. `build/VA1.adg` is two levels written from scratch:
Macro 1 swaps sub-rack, Macros 2 to 4 chain into whichever is selected,
and its variations recall through that chain. So a rack Live never saved
survives being nested, and a macro-to-macro mapping written by PatchBay
drives exactly like one Live wrote.

One thing the exercise caught, and it took two passes. The DSL originally
lifted a rack out of another rack's chain to use as a skeleton, producing
a file that passed every check and that Live refused as a drop. The cause
turned out to be a single leftover attribute; the guard against nested
skeletons is gone and the attribute is handled. See `THE_BASEMENT.md` for
why it stayed hidden as long as it did.

## The compiler runs backwards

`patchbay extract file.adg` prints DSL source for a saved rack. It recovers
what is in the file: chains and their device types, every macro mapping
with its range, chain zones, samples, macro resting positions, macro
labels, variations, and nesting to any depth with the macro-to-macro
chaining intact.

For a rack PatchBay built, extracting and rebuilding is EXACT. All six
racks in `examples/patchbayground.py`, including DR1 at three levels with
64 sample chains, diff clean against the original, and a test holds them
there. That gate is what found the gaps: ranges were not being emitted at
all, variations came out as a comment, and unnamed chains were given
invented names.

For a rack LIVE built it recovers a skeleton, and the shortfall is
structural rather than a missing feature. A declaration names a device by
tag and the compiler fills it from a donor, so:

- **parameter values do not survive.** The rebuilt device holds the donor's
  settings, not the original's. On `racks/s1_source.adg` that is about
  15,000 facts.
- **only the first device on a chain survives.** A chain holding Simpler
  plus a Pitch device comes back as Simpler.
- **only the first sample of a multi-sampled device survives.** Q3.
- **per-rack cosmetics do not survive**, `DocumentColorIndex` and
  `AreMacroVariationsControlsVisible` among them.

Closing that gap means a DSL that can carry an arbitrary parameter dump,
which is a different tool: at that point the declaration is the rack rather
than a description of one, and the donor stops being the vocabulary.

**Slot names never survive, from either source.** The emitted layout is
positional, `Macro_1` through `Macro_N`. That a macro drives
`Filter/Frequency` on every chain is in the file; that its author called
the slot `Filter` is not, and guessing it is inventing intent. Renaming is
a human edit, and every binding follows the rename.

## Deliberate limits

**Not a general graph DSL.** Every shape here was pulled out by building
`examples/patchbayground.py`, which is one big example and the end-to-end
test rather than the point of the library. Generality comes from real
second cases, not from anticipating them.

**Racks only, not Sets.** Per `MCP.md`, Live's API *does* expose track
creation and routing, so Sets are built by driving `ableton-mcp`, not by
generating `.als`. A Set-level layer should emit MCP calls, not XML.

**Donors are the vocabulary.** A device the library has never seen cannot
be used, and the error says so and lists what is available. That is
correct: inventing device XML is how you get a file Live half-loads.

The vocabulary is cheap to widen. `patchbay harvest` reads `.als` as
readily as `.adg`, because indexing a device never looks at preset
structure, so one Live Set donates whatever it happens to contain. What a
donor is wanted for is the parameter list and each parameter's native
range, not anybody's settings, so paths and names are stripped on the way
out. 56 devices are indexed today, from 8 before it existed.

## The surface this should grow into

Not built. This section is the shape the next version of the syntax takes,
and `T9` in `TODO.md` is the migration. What is written here compiles: the
five sample-free racks of `examples/patchbayground.py`, plus a drum rack
with a nested pad, were declared through
`patchbay/experimental/dsl2.py` and diff clean against the racks the
current syntax builds.

### What the current surface costs

**`bind` is four relations under one name.** `e.bind(filter="Filter/Frequency")`
maps a slot to a device parameter. `n.bind(filter="filter")` maps an outer
slot to an inner one. The value is `str`, or `(path, lo, hi)`, or a list of
either. All four are the same shape at the call site, and which one a line
means depends on whether its receiver came from `engine()` or `nest()`.

**A slot name is a string in four places.** `selector=`, `start={}`,
`labels={}` and every `bind` keyword each name the slot again, and each
does its own `macro_of` typo check. A layout that declares
`start={"Filter": 127}` states "Filter" twice within three lines. Slots
that are not Python identifiers are worse off: `KIT` declares `Send A`,
`Send B` and `Send Vol`, and none can be written as a keyword. Nothing has
bound them yet, so it has not bitten.

**There is no value for "how a device answers to the layout."** That is the
thing this project is about, and `examples/patchbayground.py` has to
express it as five functions that take a rack, mutate it and return it.
`meld(drift(wavetable(rack)))` is a rack read inside out, and the profile
cannot be shared, extended or inspected.

**The wildcard role is threaded by hand.** Five engine functions carry a
`character: str | None` parameter, a module-level `WILDCARD` table maps
role to path per device, and `_bind` filters the misses. The role is then
stated two to four times per rack: once in `labels=paired("attack")` and
once per engine call. `pd1()` says "attack" three times.

**Ranges are anonymous tuples doing arithmetic.** `("Filter/Frequency",
*CUTOFF)` splats a pair into a triple, `RELEASE_MS = tuple(v * 1000.0 for v
in RELEASE)` rebuilds one by comprehension, and `trimmed()` returns another
to be splatted again.

**Deriving a layout copies dicts by hand.** `PAD = Layout(*PATCHBAYGROUND.slots,
selector="Sound", start=dict(PATCHBAYGROUND.start), labels=...)`. A
derivation that forgets `start=` produces a rack that loads silent, and
nothing says so.

### The shape

A slot carries everything about itself, so it is named once:

```python
PATCHBAYGROUND = Layout(
    Slot("Instrument", label="> Instrument", selects=True),
    Slot("Sound"),
    Slot("Filter", start=127),
    Slot("Drive"),
    Slot("Movement"),
    Slot("Character"),
    Slot("Release", start=30),
    Slot("Volume", start=127),
)
```

`PATCHBAYGROUND.filter` is that slot. `Send A` answers to `send_a`, because
the word on the hardware and the Python name are already two things and
this only finishes the split. A typo raises at the layout, listing the
slots.

An engine profile is a value:

```python
PB = PATCHBAYGROUND

FM = (Engine("Operator")
      .drives(PB.filter, "Filter/Frequency", over=CUTOFF)
      .drives(PB.filter, "Filter/Resonance", over=RESONANCE)
      .drives(PB.release, "Operator.0/Envelope/ReleaseTime", over=RELEASE_MS)
      .drives(PB.volume, "Globals/Volume", over=trimmed("Operator", UNITY))
      .offers("attack", "Operator.0/Envelope/AttackTime")
      .offers("glide", "Globals/PortamentoTime")
      .offers("saturation", "Shaper/Drive"))
```

`offers` is what this engine can serve when a rack spends its wildcard slot
on a role. The `WILDCARD` table, the `character=` parameter on five
functions and `_bind` all collapse into it.

A rack states the role once and lists its chains:

```python
LD1 = (Rack.instrument("LD1", PB)
       .spends(PB.character, "glide")
       .label(PB.filter, "Filter + Res")
       .chain("FM", FM)
       .chain("Meld", MELD))
```

Engines that do not offer `glide` leave the slot empty, which is the
current rule with nothing to thread it through.

One verb per relation. Nesting cannot be misread as parameter binding, and
`chain` takes a device profile or a rack, because the outer rack does not
care which:

```python
VA1 = (Rack.instrument("VA1", PB)
       .chain("PADS", PADS.chaining(PB.filter, PB.release, PB.volume))
       .chain("KEYS", KEYS.chaining(PB.character.to(INNER.movement))))

DR1 = (Rack.drum("DR1", KIT)
       .pad("KICK", 36, KICK.chaining(KIT.sound, KIT.filter)))
```

A bare slot chains to the inner slot of the same name, `Slot.to` names one
that differs, and no arguments keeps the identity default.

A range is a value, so the unit is stated and the arithmetic is a method:

```python
CUTOFF = Range(30.0, 18500.0, "Hz")
RELEASE = Range(0.01, 20.0, "s")
RELEASE_MS = RELEASE.scaled(1000.0)
```

Nothing reads `unit`, because nothing can: the format records none, and the
same slot is Hz on one engine and dB on the next. It is there so the
constant says which it is, which is the fact Q14 cost a rack to find.

Deriving a layout moves what changed and keeps the rest:

```python
PAD = PATCHBAYGROUND.deriving(selects=PATCHBAYGROUND.sound,
                              relabel={PATCHBAYGROUND.sound: "> Sound"})
```

Builders return new objects. A profile or a sub-rack can sit in two racks
without one build reaching the other.

### One rule reverses

`.drives` on the same slot twice ACCUMULATES. Today a second `bind` of a
slot replaces the first, and that rule exists because `bind` is a bulk
keyword call where a second call reads as an edit. A per-slot fluent call
reads as a second mapping, which is what the Meld case wants, so the
reading and the behaviour agree instead of the docstring having to say
which won.

### What was verified

`patchbay/experimental/dsl2.py` is a front end over the current
`patchbay.dsl`, and `examples/experimental/patchbayground2.py` declares
PD1, PD1W, BS1, LD1 and VA1 through it. Every one diffs identical against
the rack the current syntax builds, and a drum rack holding a nested pad
rack was checked the same way. So this is a surface change and not a format
change, which is what makes the migration mechanical.

Rebuild both sides and compare:

    uv run patchbay build examples/patchbayground.py -o build/old
    uv run python examples/experimental/patchbayground2.py build/new
    patchbay diff build/old/PD1.adg build/new/PD1.adg

One near-miss is worth keeping. The drum rack diff did not come out clean
first time, because the hand written `Layout(*KIT.slots, selector="Sound")`
dropped the kit's starts and labels while `deriving` carried them. That is
the failure mode the derivation argument above predicts, produced by
accident while testing something else.

### What it costs

`patchbay extract` emits DSL source and a test rebuilds six racks from it
and diffs them, so the emitter moves with the syntax or the round trip
breaks. That gate is also the reason the migration is safe to attempt: it
is a complete enumeration of what the syntax has to express.

`examples/patchbayground.py`, `tests/test_patchbay.py` and every code block
in this document move too. `compile.py` picks racks out of a spec by
`isinstance`, so it takes the new type.
