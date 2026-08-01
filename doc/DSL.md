# The rack DSL

Embedded in Python. A spec is a module that imports from `patchbay.dsl` and
declares racks as values, so a loop or a comprehension describes them as
readily as a literal does.

## Why a DSL rather than a config file

Becasue code can be reused: macro layout is identical across every
instrument rack. Six racks sharing one layout is a program, not a
document. But moreover:

**Parameter names are not guessable.** Saturator's Drive knob is
`PreDrive`. Simpler's filter cutoff is
`Filter/Slot/Value/SimplerFilter/Freq`. Operator carries 217 parameters at
paths like `Operator.0/Envelope/DecayTime`. A binding written from
imagination is wrong; one written against the harvested device library is
checkable, and wrong paths fail with a suggestion.

And this is code that can be unit tested.

**Variations are combinatorial.** ~692 sounds across 18 engines, generated
by permuting macro values. That is a loop, not a list.

**The sound family constraint is a function.** Variation index N must mean
the same musical idea across every engine. Expressed as data that is a
promise; expressed through a shared layout it is structural.

## The shape

```python
PB = Layout(
    Slot("Instrument", selects=True),
    Slot("Sound"),
    Slot("Filter", start=127),
    Slot("Release", start=30),
    Slot("Volume", start=127),
)

CUTOFF = Range(30.0, 18500.0, "Hz")
RELEASE = Range(0.01, 20.0, "s")

FM = (Engine("Operator")
      .drives(PB.filter, "Filter/Frequency", over=CUTOFF)
      .drives(PB.release, "Operator.0/Envelope/ReleaseTime",
              over=RELEASE.scaled(1000.0))
      .offers("attack", "Operator.0/Envelope/AttackTime")
      .offers("glide", "Globals/PortamentoTime"))

SAMPLER = (Engine("OriginalSimpler")
           .drives(PB.filter, "Filter/Slot/Value/SimplerFilter/Freq",
                   over=CUTOFF)
           .drives(PB.release, "VolumeAndPan/Envelope/ReleaseTime",
                   over=RELEASE.scaled(1000.0))
           .offers("attack", "VolumeAndPan/Envelope/AttackTime"))

PD1 = (Rack.instrument("PD1", PB)
       .chain("FM", FM)
       .chain("Sample", SAMPLER)
       .variations(PB.variation("dark", filter=30, release=110)))

PD1.save("build/PD1.adg")
```

The declaration is not "build a rack". It is **"bind this engine's
parameters to the standard layout"**. Everything else follows:

- one chain is one engine, or one nested rack
- chain-select zones are distributed evenly across 0..127
- the layout's selector slot drives the chain selector
- the same layout slot means the same macro in every engine, which *is*
  the sound family constraint

Two properties hold throughout, and most of the shape above is downstream
of them.

**One verb per relation.** `drives` binds a slot to a device parameter,
`offers` says what an engine could serve, `spends` picks which of those a
rack wants, `chain` and `pad` add chains, `chaining` puts a rack inside
one. Nesting cannot be misread as parameter binding, because they are not
the same call.

**Values, not mutation.** Every builder returns a new object, so a layout,
an engine profile or a sub-rack can sit in two racks without one build
reaching the other. `PD1.variations(...)` is a new rack; `PD1` is not
touched.

An earlier surface had neither, and what that cost is in `THE_BASEMENT.md`.

## A slot carries everything about itself

`Slot` is one macro: its name, where it opens, what the hardware calls it,
and whether it drives the chain selector. Stated once, in one place.

`PB.filter` is the slot itself, not the string `"Filter"`, so a typo
raises at the layout rather than at the binding that uses it. `Send A`
answers to `send_a`: the word on the hardware and the Python name are
already two things, and this finishes the split.

**The selector is named, not fixed.** `selects=True` says which slot
drives the chain selector, and a layout where no slot claims it gets no
selector mapping at all. That is not a corner case: a drum rack's macro 1
is Tune, and a pad is chosen by its `ReceivingNote`. Two slots claiming it
raises, because a rack has one chain selector.

**A slot says where its knob opens.** Binding a slot is half the job. The
other half is where the knob sits when the rack is dropped, and the
default answer is the worst one available: an untouched macro reads 0, a
macro at 0 drives its target to the bottom of that target's range, so a
rack that binds Volume and does not place it loads silent.
`ARCHITECTURE.md` has the mechanism and what it cost.

The position belongs to the slot, for the same reason the name does. If
Volume means one thing on every rack, then where Volume opens is also one
thing on every rack, and a per-rack answer is a chance to get it wrong per
rack. Full right is the NEUTRAL position for Filter and Volume here, not a
loud one, because every volume binding is capped at unity and every filter
binding tops out above the audible band. Drive and Movement carry no start
because their neutral is off, which is what 0 already means.

`rack.start(PB.volume, 100)` overrides one slot for one rack. Positions
are 0..127 like everything else in macro space, and out of range raises
rather than clamps: Live clamps silently, so a 200 would load as a rack
that looks correct and is not what was written.

**A start is written only for a slot the rack actually drives.** Layouts
declare positions for all their slots and no rack binds all of them.
Wavetable leaves Movement unbound; parking that knob at a meaningful
number would show a control that moves nothing, which reads exactly like a
mapping that broke.

**The label is what the knob SAYS, which is not what the slot IS.** Two
cases force the split, and neither is cosmetic:

- **A paired slot under-describes itself.** Slot 3 drives cutoff and
  resonance. A knob labelled "Filter" that also moves resonance is lying
  by omission, on the one surface the player actually reads.
- **A rack renames a slot for what IT does with it.** Slot 6 is a wildcard
  called Character in the layout, and reads Attack, Glide or Morph
  depending on which role the rack spent it on.

So a label sits on the slot and a rack may override it:

```python
Rack.instrument("KICK", PAD).label(PAD.drive, "Drive + Snap")
```

**Position stays the contract; the word is local.** A kick reading
"Drive + Snap" where a hat reads "Drive" is the same slot, the same
chaining and the same muscle memory. A label cannot move a mapping.

## Deriving a layout moves what changed and keeps the rest

```python
PAD = PB.deriving(selects=PB.sound)
```

Inside a drum pad the axis is WHICH SAMPLE, so the selector is Sound
rather than Instrument. `relabel` moves a word at the same time, and a
relabel of `None` clears one.

Everything not named survives, which is the point. Rebuilding the slot
list by hand to move the selector drops the starts and the labels with it,
and the result is a rack that loads silent with its filter shut. That
happened once, while testing something else, and it is the reason this is
a method rather than a splat.

## An engine profile is a value

`Engine` is how one device answers a layout. It is the thing this project
is about, so it is a thing: declared once, extended by returning a new
one, and used by every rack that wants that engine.

```python
DRIFT = (Engine("Drift")
         .drives(PB.filter, "Filter_Frequency", over=CUTOFF)
         .drives(PB.filter, "Filter_Resonance", over=RESONANCE)
         .drives(PB.release, "Envelope1_Release", over=RELEASE)
         .offers("attack", "Envelope1_Attack")
         .offers("glide", "Global_Glide"))
```

**`drives` on the same slot accumulates.** A per-slot call reads as a
second mapping, and behaves as one.

## Some controls can only be set, never driven

A device holds two kinds of thing, and only one of them is a parameter:

| kind | shape | takes a `KeyMidi` |
|---|---|---|
| parameter | `<Filter_Frequency><Manual Value="18500"/>...</Filter_Frequency>` | yes |
| setting | `<ModulationMatrix_Target1 Value="6" />` | no |

A setting carries its value on itself and has no `Manual` for a mapping to
sit in. `find.params` does not return one and `library.Device.search`
cannot find one, so it is invisible to everything a binding is written
against. Drift keeps its whole modulation ROUTING this way, which is how
Macro 5 came to be bound to `Lfo_Amount`, resolve, write a valid mapping
and move nothing: the LFO was not routed anywhere, and the element that
would have routed it is not a parameter. Q16 in `SCHEMA.md`.

So a third verb:

```python
DRIFT = (Engine("Drift")
         .sets("ModulationMatrix_Source1", 2)     # the LFO
         .sets("ModulationMatrix_Target1", 6)     # LP Frequency
         .sets("ModulationMatrix_Amount1", 1.0)
         .drives(PB.movement, "Lfo_Amount"))
```

`sets` takes a parameter too, for the value a rack wants that the donor
does not happen to carry. That is not a convenience. **A donor is for the
parameter list and each parameter's native range, not for anybody's
settings**, and a value inherited by accident is still a value nobody
wrote: every Drift this project built carried the donor's own modulation
row, `Source1=5, Target1=8`, quietly modulating the high-pass at 80%,
until `sets` existed to overwrite it.

Setting the same control twice REPLACES, where `drives` accumulates. Two
values for one control is an edit; two mappings on one slot is the Meld
case.

`patchbay extract` emits a `sets` line for every direct-child value that
differs from the donor the rebuild would use. Anything equal to the donor
is already there and emitting it would be noise; what differs is either
something a spec set or something Live wrote, and both have to be said or
the rebuild is a different device.

## A slot may drive more than one parameter

```python
MELD = Engine("InstrumentMeld").drives(
    PB.filter, "MeldVoice_EngineA_Filter_Frequency",
    "MeldVoice_EngineB_Filter_Frequency", over=CUTOFF)
```

Meld is two synthesis engines behind one device, and every A-side path has
a B twin. Binding only A produced a rack in which Macro 3 filtered half
the sound and left the other half wide open. Every id was unique, every
mapping resolved, every range was right, and the whole thing was audibly
broken.

What this is not is a second axis. Both Meld engines move together because
the layout has one Filter knob; an A knob and a B knob would be two slots
out of eight, and a Push page has no room for that.

## A rack spends its wildcard slot on a role

One slot per rack is deliberately not fixed. `offers` is what an engine
CAN serve; `spends` is what this rack asks the whole family for:

```python
LD1 = (Rack.instrument("LD1", PB)
       .spends(PB.character, "glide")
       .chain("FM", FM)
       .chain("Meld", MELD))
```

An engine that does not offer the role leaves the slot EMPTY rather than
substituting something else, which is what makes the wildcard a decision
instead of a leftover. BS1 asks for `morph` and only Meld has one, so on
BS1 that knob moves Meld and nothing else. The alternative is binding
three different ideas to one knob and calling it consistency.

The role is stated once, on the rack, because it is a rack decision. The
knob takes the role's name unless a label says otherwise.

## A slot is only as consistent as its ranges

Two engines binding the same slot to their own equivalent parameter
satisfies the sound family constraint and is still not enough.

PD1's Volume slot bound `Globals/Volume` on Operator and
`VolumeAndPan/Volume` on Simpler. Both correct, both the right parameter.
One is linear amplitude bottoming at -70 dB, the other decibels bottoming
at -36. Macro 8 at zero silenced one engine and left the other playing.
See Q14 in `SCHEMA.md`.

So `Range` is not decoration for taste. **Where engines disagree about
units, `MidiControllerRange` is the only place the agreement can live**,
and Live 12.4.3 has no UI for it at all.
`library.Device.range_of(path)` reports a parameter's native range without
opening Live, which is how the divergence above was measured after ears
found it.

A range states its unit and does its own arithmetic:

```python
RELEASE = Range(0.01, 20.0, "s")
RELEASE_MS = RELEASE.scaled(1000.0)
TRIMMED = VOLUME.capped(0.631)
```

Nothing reads `unit`, because nothing can: the format records none, and
the same slot is Hz on one engine and dB on the next. It is there so the
constant says which it is, which is the fact Q14 cost a rack to find.

Rule of thumb: bind bare when engines agree about units, bind with a range
when they do not, and assume they do not until checked.

**A shared slot reads 0..127, never Hz.** A macro driving more than one
parameter has no single unit to show, so Live displays the raw macro
position. Every slot in this layout is multiply mapped by design, one
target per engine, so no instrument knob will ever show a unit. That is
the cost of one knob reaching every engine, and it is not
`ForceDisplayGenericValue` (S10), which forces the same display on a
SINGLY mapped macro and cannot undo this.

## A range equalises settings, not loudness

The intersection above gets every engine to the same gain SETTING at the
same knob position. It does not get them to the same loudness, and the
difference is not small: at what each engine's own volume parameter calls
unity, these four span about 12 dB. What an engine puts out before its
volume stage is a property of the engine.

**The DSL does not correct for that, deliberately.** Every volume binding
is capped at its engine's unity and stops there. A per-engine loudness trim
was built, measured in Live and then removed: it is a number taken by ear,
in one Set, on one set of patches, and no test can check it. The
measurements are in `THE_BASEMENT.md` for whoever wants them. Gain staging
is mixer work.

One part of it is not taste and is worth keeping in mind when binding a
volume slot. Wavetable's `Volume` and Drift's `Global_Volume` both max out
at 1.0 amplitude natively, so a range cannot push either above its own
unity whatever it says; only Meld and Operator reach 1.995.

## A chain may name its own sample

```python
.chain("Kick", Engine("OriginalSimpler").sample("samples/drums/kick/kick_001.wav"))
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
.chain("Wave", Engine("InstrumentVector").zone(0, 63))
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

## A chain may hold several devices in series

```python
EQC = Rack.audio_effect("EQC", EQ).chain(
    "strip",
    Engine("ChannelEq").drives(EQ.lo, "LowShelfGain")
    .then(Engine("Compressor2").drives(EQ.comp, "DryWet"))
    .then(Engine("StereoGain").drives(EQ.gain, "Gain")))
```

`then` puts the next device AFTER this one in the same chain. A chain is a
signal path, and the channel strip is the shape that needs saying: EQC is
an EQ into a compressor into a gain, all reached by one set of macros.

This is the opposite of what an instrument rack's chains mean. There, each
chain is an ALTERNATIVE and the selector picks one. Here the devices are
stages and all of them are in circuit, which is why they are one chain
rather than eight.

The zone belongs to the chain, so it is declared on the series and an
engine that already carries one is refused. A chain has one position on the
selector however many devices sit in it.

Each device keeps its own bindings, its own `sets`, its own sample. What is
shared is the layout: `EQ.gain` is macro 6 whichever device answers it.

## A rack has four kinds, and a MIDI rack is one of them

`Rack.instrument`, `Rack.audio_effect`, `Rack.midi_effect`, `Rack.drum`.
The kind picks the rack device tag and the branch tag - a
`MidiEffectGroupDevice` holds `MidiEffectBranchPreset`, read off
`donors/AnotherExample_midi.adg` rather than guessed - and it decides what may nest
inside. An effect rack takes only its own kind, because Live refuses the
preset otherwise, and the refusal happens at `chain()` rather than on the
drop.

## A chain may be another rack

DR1 is three levels deep and VA1 nests a rack per chain, so a chain has to
be able to hold a rack as easily as a device:

```python
VA1 = (Rack.instrument("VA1", PB)
       .chain("PADS", PADS.chaining(PB.filter, PB.release, PB.volume))
       .chain("KEYS", KEYS.chaining(PB.character.to(INNER.movement))))

DR1 = (Rack.drum("DR1", KIT)
       .pad("KICK", 36, KICK.chaining(KIT.sound, KIT.filter)))
```

`chain` takes an engine profile or a rack, because the outer rack does not
care which. Both get a zone, both take part in `engine_macro`, and a slot
a nested rack answers to counts as driven for variations exactly as a
bound parameter does. So a variation reaches into a sub-rack without
saying so.

**Chaining is outer slot to inner slot, and no slots at all means
identity.** That default is the whole argument for one layout: when both
racks share it, `chaining()` drives every slot the inner rack drives from
the matching outer knob. Naming slots drives only those, as VA1 does by
leaving out the selector so the outer knob picks a sub-rack rather than
doing two jobs. `Slot.to` names an inner slot with a different name.

A pad is a chain with one thing swapped: it is selected by `ReceivingNote`
rather than by a zone, Live leaves its zone at 0/0/0/0, and it is exempt
from zone distribution. Nothing else changes.

Nothing in the mapping code knows how deep it is. A macro-to-macro mapping
is a `KeyMidi` on the inner rack's `MacroControls.N`, which is an ordinary
parameter node, and `Channel` stays 16 at every depth. So the same code
writes depth 1 and depth 3.

The one thing that *does* change with depth is an attribute: a nested
`GroupDevicePreset` carries an `Id`, and the document's top-level one must
carry none. That is handled in `_nested_preset` and `_load_skeleton` and
is invisible from the spec. It is also the whole of what once made nested
racks look intractable - see `THE_BASEMENT.md`.

## A rack may have RETURN chains, and chains may send to them

```python
kit = (Rack.drum("DR1", KIT)
       .ret("A-Rvb:Short", SHORT_FX.unchained())
       .ret("A-Dly:Long", LONG_FX.unchained())
       .pad("KICK", 36, KICK.chaining(KIT.sound), sends={"A-Rvb:Short": 0.35}))
```

`ret` adds a return: an effect, or a whole rack when the return is a
selector across several of them. A return branch is an
`AudioEffectBranchPreset` whatever the parent rack is, and it lives in
`ReturnBranchPresets`, a sibling of `BranchPresets` (S9).

`sends` is return NAME to level, in linear amplitude - a third scale, not
macros and not zones. The file names a return POSITIONALLY, by `Index`, so
the spec names it and the build resolves the position. A send to a return
the rack does not have raises.

**Adding a return writes a send on every chain**, including the other
returns, at the silent floor. That is what Live does, and a rack missing
one is inconsistent rather than merely sparse.

**A macro may sweep every chain's send to one return:**

```python
kit = kit.sending(KIT.send_a, "A-Rvb:Short")
```

One mapping per chain, written into that chain's own `SendInfos` entry,
because a send belongs to a chain and not to the rack. So the kit knob is
how much of the WHOLE rack reaches that return, and a per-chain `sends`
level still sets where each chain starts.

This was deleted for a release on a check that found the knob moving
nothing, and restored when Live wrote the identical mapping by hand. Q23
has both halves; `THE_BASEMENT.md` has what the wrong conclusion cost.
Writing sends flips `AreSendsVisible`, because Live ships it false and
sends nobody can see look exactly like sends that failed to write.

**`unchained()` is not `chaining()`.** With no arguments `chaining` means
the IDENTITY default, every slot the inner rack drives from the matching
outer knob. A return's effects answer their own knobs and no outer knob at
all, so they take `unchained()`. The two are one call apart and read
differently on purpose; extraction emits whichever the file actually shows.

## One declaration, one instance per track

```python
STRIP_INSTANCES = [rack.named(f"{rack.name}_{track}")
                   for track in TRACKS for rack in STRIP]
```

`named` returns the same rack under another name and moves nothing else.
`PATCHBAYGROUND.md` names each strip instance for the track it sits on,
`EQC_BS1` on BS1, so that eight tracks do not end up staring at `EQC_LD1`
on a pad track. 46 files out of six declarations, and they are built but
not golden-gated: what a digest proves about EQC it proves about EQC_BS1.

## A variation is a vector, not a sound

A `Variation` is a vector over layout slots, in macro space 0..127 - the
only scale a variation has, since Live applies each target's own
`MidiControllerRange` at recall. It names slots, never device parameters:

```python
PB.variation("dark plucks", filter=30, release=110, character=90)
```

It is built from the layout, which is what checks the slots belong to it.
`_at` takes slot objects instead of keys, for values computed in a loop.

**That is why the sound family constraint needs no enforcing.** Both
engines bind `filter` to their own parameter, so one vector is one sound
in each, and index alignment across engines is structural rather than a
rule someone has to remember. Nothing in the variation code knows how many
engines there are.

A variation is NOT how PATCHBAYGROUND addresses a sound. Nothing maps a
knob to a variation, so a variation cannot be dialled in while a clip
plays; a sound is `(instrument, sound)`, two macros driving two chain
selectors. What a variation carries that a selector position cannot is the
WHOLE vector at once, which makes it the right mechanism for a preset
across the entire layout. See `PATCHBAYGROUND.md`.

Instrument choice is itself a slot, because the layout's selector slot
drives the chain selector and a selector is an ordinary parameter:

```python
PB.variation("sampled", instrument=PD1.engine_macro("Sample"), filter=40)
```

`engine_macro` returns the centre of that engine's zone, from the same
arithmetic that distributes the zones. So a variation selects its own
chain, which is what makes a sound a variation rather than a chain.

Two refusals, both loud:

- a slot not in the layout fails at declaration, so a typo never reaches a
  file
- a slot **nothing in the rack drives** fails at build, and the message
  lists the slots that are driven. Live accepts such an entry and moves
  nothing on recall (`SPIKES.md` Q5), so it would read as live and be dead

A built rack always replaces the skeleton's variation set rather than
appending to it. Donors are real racks and may carry variations describing
a different rack entirely.

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

`build/PD1.adg`, compiled from `examples/patchbayground.py`, loads on a
MIDI track in Live 12.4.3. Macro 1 sweeps engines across the distributed
zones. Macro 3 drives Operator's `Filter/Frequency` and Simpler's
`Filter/Slot/Value/SimplerFilter/Freq`, both scoped to the declared
30-18500 Hz range.

That is the whole claim of this document demonstrated: one layout, two
synthesis methods, the same knob meaning the same thing in both.

Variations passed the same way. `build/PD1.adg` carries 96, all named and
all recalling; unbound macros stay where they are, and a variation selects
its own engine through the chain selector. The sound family claim was
checked by ear: recall a Sample variation, turn Engine full left, and the
same musical idea arrives through FM with nothing re-set. Live accepts
more variations than the template needs - 256 loaded without truncation.

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

**Output identity is a test, not a claim.** `tests/golden.txt` holds a
digest per rack over every fact `diff.flatten` can see, DR1's 178,960
included. A change that is not supposed to move the output proves it by
`uv run pytest`, and nobody opens Live for it. Live tells you a file
loads; it never tells you a file is UNCHANGED.

## Reading racks out of a Set

```
patchbay extract mysong.als                 # DSL for every rack on every track
patchbay extract mysong.als --out lib/      # one module per rack, plus an index
```

A `.als` stores a rack in Set form and a `.adg` stores it in preset form.
The mapping between them is Q9 in `SCHEMA.md`, and `extract.preset_from_set`
applies it, so everything downstream is the same emitter a `.adg` uses.

What that mapping cost is worth knowing before trusting a harvested donor:
the DEVICE node is identical in both forms, and everything around it is
renamed and re-nested. What a Set adds is bookkeeping - session ids for
automation, a provenance subtree on anything dragged from the browser - and
a device placed by this DSL has all of it cleared.

## The compiler runs backwards

`patchbay extract file.adg` prints DSL source for a saved rack. It
recovers what is in the file: chains and their device types, every macro
mapping with its range, chain zones, samples, macro resting positions,
macro labels, variations, and nesting to any depth with the macro-to-macro
chaining intact.

For a rack PatchBay built, extracting and rebuilding is EXACT. Every
canonical rack in `examples/patchbayground.py`, including DR1 at three
levels with 64 sample chains, diffs clean against the original, and a test
holds them there. That gate is what found the gaps: ranges were not being emitted at
all, variations came out as a comment, and unnamed chains were given
invented names.

It is also what proves a change to the syntax is complete, because the
emitter is an exhaustive enumeration of what the syntax has to express.

For a rack LIVE built it recovers a skeleton, and the shortfall is
structural rather than a missing feature. A declaration names a device by
tag and the compiler fills it from a donor, so:

- **parameter values do not survive.** The rebuilt device holds the
  donor's settings, not the original's. On `racks/s1_source.adg` that is
  about 15,000 facts.
- **only the first device on a chain survives.** A chain holding Simpler
  plus a Pitch device comes back as Simpler.
- **only the first sample of a multi-sampled device survives.** Q3.
- **per-rack cosmetics do not survive**, `DocumentColorIndex` and
  `AreMacroVariationsControlsVisible` among them.

Closing that gap means a DSL that can carry an arbitrary parameter dump,
which is a different tool: at that point the declaration is the rack
rather than a description of one, and the donor stops being the
vocabulary.

**Slot names do not survive, unless a spec is named.** By default the
emitted layout is positional, `Slot("Macro 1")` through `Slot("Macro N")`,
answering to `macro_1` in Python. That a macro drives `Filter/Frequency` on
every chain is in the file; that its author called the slot `Filter` is not,
and guessing it is inventing intent.

```
patchbay extract build/BS1.adg --layout examples/patchbayground.py
```

`--layout` reads a spec's own bindings and reuses ITS name wherever an
extracted binding agrees, positional everywhere else. That is not a guess:
it is a second file claiming that whatever drives
`Voice_Filter1_Frequency` is called Filter. A macro is renamed only when
every path it drives that the spec knows about agrees on one slot; one
disagreement and it stays `Macro N`, because half a name is worse than
none. The rebuild is fact for fact identical either way.

## Deliberate limits

**Not a general graph DSL.** Every shape here was pulled out by building
`examples/patchbayground.py`, which is one big example and the end-to-end
test rather than the point of the library. Generality comes from real
second cases, not from anticipating them.

**Sets are a second, thinner surface.** `live_set.Track` and
`live_set.Session` say which racks sit on which track, in what order, and
what the returns are called. That is all a Set declaration is here: no
clips, no automation, no envelopes, and nothing that belongs to a
performance rather than to an instrument. The DSL proper is still about
racks - a Session names them and places them.

The two routings a Set adds are `Track(out=)` and `Track(sidechain=)`, and
both take a track NAME. Live stores a track ID (Q33), and a name is the
only thing a spec has: ids are assigned at build time and a spec that
wrote one would be guessing at the order. So the resolution happens in
`live_set.build`, after every track has an id, and a name that is not a
track in the Set raises rather than writing a route to nowhere.

**Donors are the vocabulary.** A device the library has never seen cannot
be used, and the error says so and lists what is available. That is
correct: inventing device XML is how you get a file Live half-loads.

The vocabulary is cheap to widen. `patchbay harvest` reads `.als` as
readily as `.adg`, because indexing a device never looks at preset
structure, so one Live Set donates whatever it happens to contain. What a
donor is wanted for is the parameter list and each parameter's native
range, not anybody's settings, so paths and names are stripped on the way
out. 56 devices are indexed today, from 8 before it existed.
