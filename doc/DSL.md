# The rack DSL

## Why a DSL rather than a config file

`PATCHBAYGROUND.md` line 60: *"This consistency is the actual product, more
than any individual rack."* The macro grammar is identical across every
instrument rack. Six racks sharing one grammar is a program, not a
document - in YAML you would copy the grammar six times and watch it
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
promise; expressed through a shared grammar it is structural.

## The shape

```python
PUSH = Grammar("Instrument", "Sound", "Filter", "Drive",
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
parameters to the standard grammar"**. Everything else follows:

- one engine is one chain
- chain-select zones are distributed evenly across 0..127
- the grammar's `selector` slot drives the chain selector
- the same grammar slot means the same macro in every engine, which *is*
  the sound family constraint

## The selector slot is named, not fixed

`Grammar(..., selector="Instrument")` says which slot drives the chain
selector. It defaults to `"engine"` and may be `None` for a grammar with
no selector at all, such as a drum kit whose macro 1 is Tune.

This was hardcoded to `"engine"` once. Renaming the slot then produced a
rack that compiled, passed every check the tooling has, loaded in Live,
and whose first macro moved nothing, because the code silently found no
slot to map. A grammar is a contract the caller writes; the library must
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
position. Every slot in this grammar is multiply mapped by design, one
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
the grammar has one Filter knob; an A knob and a B knob would be two slots
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
grammar's name onto every rack, so every rack sharing a grammar showed
identical words.

Two cases break that, and neither is cosmetic:

- **A paired slot under-describes itself.** Slot 3 drives cutoff and
  resonance. A knob labelled "Filter" that also moves resonance is lying
  by omission, on the one surface the player actually reads.
- **A selector steps where every other knob sweeps**, and nothing in the
  format marks it. That is a property of the rack, not of the parameter.

So labels are separate, declared on the grammar and overridable per rack,
exactly as start positions are:

```python
PATCHBAYGROUND = Grammar(..., labels={"Instrument": "> Instrument"})

Rack("KICK", PAD, labels={"Drive": "Drive + Snap"})
```

**Position stays the contract; the word is local.** A kick reading
"Drive + Snap" where a hat reads "Drive" is the same slot, the same
chaining and the same muscle memory. Nothing about what the knob DOES
changes, which is what makes this safe: a label cannot move a mapping, and
a label for a slot that is not in the grammar raises.

## A grammar says where the knobs open

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
PATCHBAYGROUND = Grammar(
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
That default is the whole argument for one grammar: when both racks share
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

A `Variation` is a vector over grammar slots, in macro space 0..127 - the
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
across the entire grammar. See `PATCHBAYGROUND.md`.

Instrument choice is itself a slot, because the grammar's selector slot
drives the chain selector and a selector is an ordinary parameter:

```python
Variation("sampled", instrument=rack.engine_macro("Sample"), filter=40)
```

`engine_macro` returns the centre of that engine's zone, from the same
arithmetic that distributes the zones. So a variation selects its own chain,
which is what makes a sound a variation rather than a chain.

Two refusals, both loud:

- a slot not in the grammar fails at declaration, so a typo never reaches a
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

That is the whole claim of this document demonstrated: one grammar, two
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
survives being nested, and a macro-to-macro mapping written by patchbay
drives exactly like one Live wrote.

One thing the exercise caught, and it took two passes. The DSL originally
lifted a rack out of another rack's chain to use as a skeleton, producing
a file that passed every check and that Live refused as a drop. The cause
turned out to be a single leftover attribute; the guard against nested
skeletons is gone and the attribute is handled. See `THE_BASEMENT.md` for
why it stayed hidden as long as it did.

## Deliberate limits

**Not a general graph DSL.** It expresses the racks in
`PATCHBAYGROUND.md`. Generality can come later, from real second cases.

**Racks only, not Sets.** Per `MCP.md`, Live's API *does* expose track
creation and routing, so Sets are built by driving `ableton-mcp`, not by
generating `.als`. A Set-level layer should emit MCP calls, not XML.

**Donors are the vocabulary.** A device the library has never seen cannot
be used, and the error says so and lists what is available. That is
correct: inventing device XML is how you get a file Live half-loads.
