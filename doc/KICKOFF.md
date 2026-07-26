# Kickoff

Paste this as your first message in Claude Code, or leave it in the repo
and say "read KICKOFF.md and start with Phase 0".

---

## The ask

Build a system that generates a complete Ableton Live 12 template for Push 3
from a declarative specification, with as little manual work in Live as
possible.

Read `PATCHBAYGROUND.md` first. It defines the target: eight tracks, the DR1
three level nesting pattern, the macro grammar, the sound family constraint,
and the PM1 pre master mechanism. That document is the requirement. This one
is the plan.

Read `CLAUDE.md` for the working method (differential diffing) and the known
landmines.

## Why file generation and not the Live API

Live's API cannot group devices into a rack, create a macro mapping, or set a
chain zone. Those operations are not exposed to remote scripts or Max for
Live. `.adg` and `.als` are gzipped XML, so everything happens at the file
level instead. This has already been established. Do not spend time
re-investigating it.

## Two layers, keep them separate

**`patchbay/` is generic.** It knows about gzipped XML, Ableton's node
structure, ids, macro mappings, chain zones, file references. It knows
nothing about kick drums or darkwave. Its API should read roughly as:
"load this preset, find that node, set this parameter, clone that chain,
write it back". Anyone building any Live template should be able to use it.

**The rest of the project is specific.** It encodes one opinionated template:
this eight track Push set. It expresses that template as data in `specs/`,
and uses `patchbay` to realise it.

If you find yourself putting the word "kick" or "drum" inside `patchbay/`,
that logic belongs in the specific layer.

## The donor pattern

Do not generate device XML from nothing. A Simpler node is large, and a
partially specified device will either fail to load or load with silent
wrong defaults.

Instead: harvest real device instances from Live. Save a rack containing a
correctly configured Simpler, Operator, Saturator etc, and store those `.adg`
files in `donors/`. The build composes new racks by copying donor subtrees
and overriding specific parameters.

This turns "reverse engineer the whole schema" into "reverse engineer the
handful of nodes I actually need to change", which is the difference between
a weekend and a month.

Corollary: `donors/` is a project asset, not a scratch folder. Document what
each donor contains and which Live version produced it.

---

## Phase 0: spikes

**Status: 5 of 13 done, both kill criteria passed.** Live progress table
is in `SPIKES.md`; the resulting model of the format is in
`ARCHITECTURE.md`. Struck-through items below are complete.

Do these before writing anything else. Each one is a question with a yes or
no answer, recorded in `SCHEMA.md`. Several are kill criteria.

~~**S1. Round trip fidelity.**~~ **DONE - PASSED.** Lossless over 18,148
facts; Live 12.4.3 opens the output. Live tolerates lxml's serialiser
conventions, so byte identity is not required.

~~**S2. Noise floor.**~~ **DONE - PASSED, floor is zero.** Real churn is
`RoundRobinRandomSeed` plus the preset self-identity paths, now filtered.
Ids were found **not** to churn, so the id filter was inverted: ids are
shown by default.

~~**S3. Macro mapping representation.**~~ **DONE - PASSED.** None of the
three guesses. A mapping is a `KeyMidi` element *inside* the target
parameter, encoding a virtual MIDI CC: channel 16, CC number = macro
index. The target is named by containment. `ARCHITECTURE.md` §5.

~~**S3b (new). Macro index confirmation.**~~ **DONE - CONFIRMED.**
`NoteOrController` is the zero-based macro index. Also established the
macro-to-parameter transfer function, which Phase 5 needs.

~~**S4. Macro to macro mapping.**~~ **DONE - no structural difference.**
An inner rack's macro is an ordinary parameter, so it takes a `KeyMidi`
like any other. Three working levels already exist in
`racks/s1_source.adg`. Depth is not encoded anywhere; it is structural.
`ChainSelector` is mappable identically.

**S5. Chain select zones.** Drag one chain zone. Diff. Record how zone start,
length and fade are stored. Do the same for key and velocity zones, since
they are probably siblings of the same structure.

**S6. Id allocation and scope.** ~~The critical one.~~ **Downgraded by
S3** - macro mappings carry no ids, so this no longer decides whether
cloning is viable. Still needed before `clone.py` ships, for any other
cross-reference. Add a device, diff, and
work out how ids are assigned. What is the uniqueness scope: the file, the
rack, the chain? Which attributes participate (`Id`, `PointeeId`, `LomId`,
`LomIdView`, others)? What breaks if two nodes share an id?
*This determines whether cloning is viable. Spend real time here.*

**S7. FileRef anatomy.** Swap one sample in a Simpler. Diff. Record every
field that changes, not just the path. Expect relative path type, search
hints, and possibly size or hash fields. Then test the failure mode
deliberately: rewrite only the path and confirm what Live does (probably
shows the sample offline).

**S8. Macro variations.** Click New in the variations panel, then again with
different macro values. Diff. How is a variation stored? Are values absolute
or normalised? Where do names live?

**S9. Drum Rack specifics.** Diff a drum rack against an instrument rack.
Record: how a pad maps to its receiving note, how return chains inside the
drum rack are represented, and how per chain send levels are stored.

**S10. Macro metadata.** Rename a macro, change its custom min/max range,
toggle exclude from randomisation, change the visible macro count from 8 to
16. One diff each.

~~**S11. `.als` track structure.**~~ **DROPPED - see `MCP.md`.** Live's API
does expose track creation and output routing; the `ableton-mcp` submodule
just had not wired them up. Extending the remote script is smaller work
than generating `.als` and survives Live updates. Original text follows.

**S11.** Separate spike, do it after S1 to S10.
In a Live Set, record how track output routing (Audio To) is stored, how a
compressor's sidechain source references another track, and how return
tracks differ from regular tracks. This unlocks generating the whole set
rather than just the racks.

**S12. Minimal device viability.** Can a device node be written with only
some of its parameters present, or must the full blob exist? Test by deleting
parameter nodes from a donor and reloading. Determines how much the donor
pattern is load bearing.

---

## Build phases

Each phase ends with a manual gate: generate, drag into Live, confirm
behaviour. There is no automated test that proves Live will load a file.

~~**Phase 1. patchbay core.**~~ **DONE.** `find.py` locates nodes, `params.py`
reads and writes values, ranges and mappings.

**Phase 2. Clone with id remapping.**
Duplicate a chain or a whole device subtree, allocating fresh ids so mappings
survive. Depends on S3, S4, S6.
*Revised: mappings survive a verbatim copy - no id work needed for them.
Remaining id work is whatever S6 turns up for other references, so this
phase is cheaper than planned.*
*Gate: PASSED.* Cloning a mapped chain three times produced four chains
whose macros all drive correctly, with no cross-wiring, confirmed in Live.

Note what "independent" means here: the copies are separate objects, but
they answer to the *same* macro and therefore move together. That is the
default and it is what the sound family constraint wants. `--stride` gives
each copy its own macro block when independent knobs are needed instead.

**Phase 3. Sample retargeting.** NOT STARTED, and much smaller than
budgeted: S7 showed Live re-reads sample metadata on load, so only the two
path fields on each of a sample's two FileRefs are required.
Belongs in the DSL as a binding, not a separate module.
*Gate: eight pads with eight different samples, none offline.*

~~**Phase 4. Rack composition from spec.**~~ **DONE, gate passed.** This
is the DSL. A spec declares engines bound to a shared macro grammar; the
compiler assembles donor subtrees, distributes zones and writes mappings.
See `DSL.md`.

*Gate: PASSED.* `build/PD1.adg`, compiled from `examples/patchbayground.py`,
loads on a MIDI track. Macro 1 sweeps engines, Macro 2 drives Operator's
filter frequency and Simpler's cutoff over the same declared 200-8000 Hz
range. One grammar, two synthesis methods, verified by ear.

**Phase 5. Macro variations.** BUILT.
`patchbay/variations.py` writes the `MacroSnapshot` list; `Variation` in the
DSL expresses one sound as a vector over grammar slots.

The sound family constraint came out structural rather than enforced. A
variation names slots, never a device parameter, so there is nothing per
engine to keep aligned: index N is the same musical idea in every engine
because the grammar is what they share. Engine choice is itself a slot, so a
variation selects its own chain.

*Gate: PASSED.* `build/PD1.adg` carries 96 variations over engine, cutoff,
decay and resonance. All 96 recall, unbound macros stay put, and a variation
selects its own engine. Recalling a Sample variation then turning Engine
left gives the same idea through FM, which is the sound family constraint
holding without being enforced.

Two probes rode along and closed `SPIKES.md` Q4 and Q5: no snapshot ceiling
at 256, and flagging an unmapped macro is accepted but inert.

**Phase 6. Live Set assembly - REVISED, see `MCP.md`.**
~~Emit the whole `.als`.~~ Instead: extend the `ableton-mcp` remote script
with `create_audio_track`, `create_return_track` and an output-routing
setter, then drive it to build the eight tracks, returns, routing, tempo
and starter clips, loading each generated rack by browser URI.

All of that is already in the Live Object Model - verified against Live
12.4.3's `_MxDCore/LomTypes.pyc` - so no Set XML needs reverse
engineering. **Sidechain source is the exception**: absent from the LOM,
so it stays manual.

~~**Phase 7. Full build.**~~ **DONE in shape, thin in content.**
`patchbay build examples/patchbayground.py -o build/` compiles a spec into rack
presets. The spec declares one rack so far; the machinery is not the
missing part.

---

## What is automated and what stays manual

Be honest about this boundary in the design. Trying to automate the manual
column is how this project fails.

**Automated**

- Rack structure at every nesting level
- All macro mappings, including macro to macro chains
- Chain select zone layout and distribution
- Sample wiring, given a manifest that says which file goes on which pad
- Macro variation generation across the whole parameter grid
- Per pad send levels and drum rack return chain structure
- Channel strip placement on all eight tracks
- Track creation, naming, ordering, routing, sidechain sources
- Return track setup
- Starter MIDI clips
- The final `.als`

**Manual, permanently**

- Choosing which samples are good. A generator cannot judge whether a kick
  is the right kick.
- Sound design judgement. Phase 5 can emit 64 variations across a parameter
  grid, but deciding which 30 are keepers requires ears. Design the workflow
  around generate wide, then audition and cull, rather than trying to
  generate only good ones.
- Gain staging and mix balance between tracks.
- Anything involving listening.

**Semi automated, worth designing carefully**

- Sample assignment. Curation is manual, wiring is automatic. The interface
  between them is a manifest file (pad name to sample path). Make that
  manifest pleasant to write and easy to regenerate from a folder.
- Variation culling. Consider emitting variations with generated names that
  encode their parameter values, so culling is informed rather than blind.

---

## Verification harness

AbletonMCP cannot build any of this, but it is useful for checking the
output. It can load a preset onto a track by browser URI and report the
devices present. Consider a smoke check that generates a rack, loads it via
MCP, and confirms the expected device tree appeared. That catches gross
failures without a human dragging files.

It cannot verify that macros are mapped correctly. That still needs a person.

---

## Risks and fallbacks

- ~~**S3 or S6 fail.**~~ **Not triggered.** S3 passed; mappings are
  addressable and cheaply so. This fallback is retired.
- ~~**S11 turns out to be nasty.**~~ **Resolved better than the fallback.**
  Set structure never needs reverse engineering: tracks and routing are
  scriptable through the Live API. See `MCP.md`.
- **Live version drift.** The schema is version specific. Record the exact
  Live version in `SCHEMA.md` and in every donor's documentation. Expect to
  redo spikes after a major update.

## Definition of done

`python build.py` produces a `.als` that opens in Live 12, presents eight
correctly named and routed tracks, with racks whose macros are mapped
according to the grammar in `PATCHBAYGROUND.md`, playable from Push 3 without
touching a mouse.

## Start here

Run Phase 0 spikes S1, S2, S3 in that order. Report back with findings in
`SCHEMA.md` before writing any generator code. If S1 or S3 fail, stop and say
so rather than working around it.
