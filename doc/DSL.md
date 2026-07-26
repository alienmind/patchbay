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
PUSH = Grammar("Engine", "Cutoff", "Resonance", "Decay",
               "Drive", "Movement", "Space", "Character")

rack = Rack("PD1", PUSH, kind=RackKind.INSTRUMENT)

with rack.engine("FM", "Operator") as e:
    e.bind(cutoff=("Filter/Frequency", 200, 8000),
           resonance="Filter/Resonance",
           decay="Filter/Envelope/DecayTime")

with rack.engine("Sample", "OriginalSimpler") as e:
    e.bind(cutoff=("Filter/Slot/Value/SimplerFilter/Freq", 200, 8000),
           resonance="Filter/Slot/Value/SimplerFilter/Res",
           decay="Filter/Slot/Value/SimplerFilter/Envelope/DecayTime")

rack.variations(Variation("dark", cutoff=30, decay=110),
                Variation("open", cutoff=120, decay=20))

rack.save("build/PD1.adg")
```

The declaration is not "build a rack". It is **"bind this engine's
parameters to the standard grammar"**. Everything else follows:

- one engine is one chain
- chain-select zones are distributed evenly across 0..127
- macro 1 drives the chain selector, so the Engine knob sweeps engines
- the same grammar slot means the same macro in every engine, which *is*
  the sound family constraint

## A sound is a variation

`PATCHBAYGROUND.md` puts ~692 sounds across 18 engines. As chains that is
impossible; as variations it is a loop.

A `Variation` is a vector over grammar slots, in macro space 0..127 - the
only scale a variation has, since Live applies each target's own
`MidiControllerRange` at recall. It names slots, never device parameters:

```python
Variation("dark plucks", cutoff=30, decay=110, resonance=90)
```

**That is why the sound family constraint needs no enforcing.** Both engines
bind `cutoff` to their own parameter, so one vector is one sound in each,
and index alignment across engines is structural rather than a rule someone
has to remember. Nothing in the variation code knows how many engines there
are.

Engine choice is itself a slot, because macro 1 drives the chain selector
and a selector is an ordinary parameter:

```python
Variation("sampled", engine=rack.engine_macro("Sample"), cutoff=40)
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
| writes variations in macro space, all 16 slots, `MacroHasValue.N` for participation | S8: that is the `MacroSnapshot` shape, and rewriting Live's own diffs at zero facts |

## Verified, not merely designed

`build/PD1.adg`, compiled from `examples/patchbayground.py`, loads on a MIDI
track in Live 12.4.3. Macro 1 sweeps engines across the distributed zones.
Macro 2 drives Operator's `Filter/Frequency` and Simpler's
`Filter/Slot/Value/SimplerFilter/Freq`, both scoped to the declared
200-8000 Hz range.

That is the whole claim of this document demonstrated: one grammar, two
synthesis methods, the same knob meaning the same thing in both.

Variations passed the same way. `build/PD1.adg` carries 96, all named and all
recalling; unbound macros stay where they are, and a variation selects its
own engine through the chain selector. The sound family claim was checked by
ear: recall a Sample variation, turn Engine full left, and the same musical
idea arrives through FM with nothing re-set. Live accepts more variations
than the template needs - 256 loaded without truncation.

One thing the exercise caught. The DSL originally scanned `racks/` for a
skeleton and would lift a rack out of another rack's chain, producing a
file that passed every check and that Live refused to accept as a drop.
Skeletons are now top-level only, and the underlying question is open as
Q1b in `SPIKES.md`. It matters because DR1 needs racks nested INTO chains.

## Deliberate limits

**Not a general graph DSL.** It expresses the racks in
`PATCHBAYGROUND.md`. Generality can come later, from real second cases.

**Racks only, not Sets.** Per `MCP.md`, Live's API *does* expose track
creation and routing, so Sets are built by driving `ableton-mcp`, not by
generating `.als`. A Set-level layer should emit MCP calls, not XML.

**Donors are the vocabulary.** A device the library has never seen cannot
be used, and the error says so and lists what is available. That is
correct: inventing device XML is how you get a file Live half-loads.
