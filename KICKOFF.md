# Kickoff

Paste this as your first message in Claude Code, or leave it in the repo
and say "read KICKOFF.md and start with Phase 0".

---

## The ask

Build a system that generates a complete Ableton Live 12 template for Push 3
from a declarative specification, with as little manual work in Live as
possible.

Read `TEMPLATE_SPEC.md` first. It defines the target: eight tracks, the DR1
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

**`adgkit/` is generic.** It knows about gzipped XML, Ableton's node
structure, ids, macro mappings, chain zones, file references. It knows
nothing about kick drums or darkwave. Its API should read roughly as:
"load this preset, find that node, set this parameter, clone that chain,
write it back". Anyone building any Live template should be able to use it.

**The rest of the project is specific.** It encodes one opinionated template:
this eight track Push set. It expresses that template as data in `specs/`,
and uses `adgkit` to realise it.

If you find yourself putting the word "kick" or "drum" inside `adgkit/`,
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

~~**S1. Round trip fidelity.**~~ **DONE — PASSED.** Lossless over 18,148
facts; Live 12.4.3 opens the output. Live tolerates lxml's serialiser
conventions, so byte identity is not required.

~~**S2. Noise floor.**~~ **DONE — PASSED, floor is zero.** Real churn is
`RoundRobinRandomSeed` plus the preset self-identity paths, now filtered.
Ids were found **not** to churn, so the id filter was inverted: ids are
shown by default.

~~**S3. Macro mapping representation.**~~ **DONE — PASSED.** None of the
three guesses. A mapping is a `KeyMidi` element *inside* the target
parameter, encoding a virtual MIDI CC: channel 16, CC number = macro
index. The target is named by containment. `ARCHITECTURE.md` §5.

~~**S3b (new). Macro index confirmation.**~~ **DONE — CONFIRMED.**
`NoteOrController` is the zero-based macro index. Also established the
macro-to-parameter transfer function, which Phase 5 needs.

~~**S4. Macro to macro mapping.**~~ **DONE — no structural difference.**
An inner rack's macro is an ordinary parameter, so it takes a `KeyMidi`
like any other. Three working levels already exist in
`racks/s1_source.adg`. Depth is not encoded anywhere; it is structural.
`ChainSelector` is mappable identically.

**S5. Chain select zones.** Drag one chain zone. Diff. Record how zone start,
length and fade are stored. Do the same for key and velocity zones, since
they are probably siblings of the same structure.

**S6. Id allocation and scope.** ~~The critical one.~~ **Downgraded by
S3** — macro mappings carry no ids, so this no longer decides whether
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

**S11. `.als` track structure.** Separate spike, do it after S1 to S10.
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

**Phase 1. adgkit core.**
Read, write, round trip. Node location helpers. Get and set parameter values.
Depends on S1, S2.

**Phase 2. Clone with id remapping.**
Duplicate a chain or a whole device subtree, allocating fresh ids so mappings
survive. Depends on S3, S4, S6.
*Revised: mappings survive a verbatim copy — no id work needed for them.
Remaining id work is whatever S6 turns up for other references, so this
phase is cheaper than planned.*
*Gate: clone one mapped pad, load it, confirm all three macro hops still
drive the right parameters and that the two pads are independent.*

**Phase 3. Sample retargeting.**
Rewrite `FileRef` nodes from a manifest. Depends on S7.
*Gate: eight pads with eight different samples, none offline.*

**Phase 4. Rack composition from spec.**
Build a rack by assembling donor subtrees according to a declarative spec.
Depends on S5, S12.

**Phase 5. Macro variations.**
Generate variation sets. Must respect the sound family constraint from
`TEMPLATE_SPEC.md`: variation index N means the same musical idea across
every engine in the rack, not independent randomisation per engine. Depends
on S8, S10.

**Phase 6. Live Set generation.**
Emit the whole `.als`: eight tracks with correct names and types, PM1 as an
audio track receiving the other seven, eight return tracks, sidechain
routing from DR1, tempo, and the racks placed on their tracks. Depends on S11.

**Phase 7. Full build.**
`build.py` produces a loadable template from `specs/` plus `donors/` plus
`samples/` in one command.

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
- **S11 turns out to be nasty.** Skip Phase 6. Generate racks only, assemble
  the set by hand once, save it as the default Live Set. This costs one
  afternoon, not a project.
- **Live version drift.** The schema is version specific. Record the exact
  Live version in `SCHEMA.md` and in every donor's documentation. Expect to
  redo spikes after a major update.

## Definition of done

`python build.py` produces a `.als` that opens in Live 12, presents eight
correctly named and routed tracks, with racks whose macros are mapped
according to the grammar in `TEMPLATE_SPEC.md`, playable from Push 3 without
touching a mouse.

## Start here

Run Phase 0 spikes S1, S2, S3 in that order. Report back with findings in
`SCHEMA.md` before writing any generator code. If S1 or S3 fail, stop and say
so rather than working around it.
