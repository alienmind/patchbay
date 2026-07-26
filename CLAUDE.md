# adgkit

Generate and manipulate Ableton Live rack presets (`.adg`) programmatically,
so that building a large hyper-mapped Push template does not require
thousands of manual macro mappings.

## Why this exists

Ableton's Live API (remote scripts, Max for Live) cannot group devices into
a rack, create a macro mapping, or set a chain zone. Those operations are
not exposed. So automation has to happen at the file level instead.

`.adg` files are gzipped XML. Everything we need is text in there.

## Scope

- **In scope:** `.adg` rack presets. Small, self contained, and dropping one
  into the User Library makes it appear in Live's browser immediately.
- **Out of scope:** `.als` Live Sets. Bigger, riskier, and unnecessary.
  Build racks, load them by hand or via AbletonMCP.

## Method: differential diffing, not schema reading

Do not try to understand the schema by reading it. The discovery loop is:

1. In Live, save a rack as `a.adg`
2. Change exactly ONE thing (move one macro, remap one parameter, shift one
   chain zone)
3. Save as `b.adg`
4. `adgkit diff a.adg b.adg`

The diff names the node. Record the finding in `SCHEMA.md`. Every feature
in this project should be preceded by a diff that proves where the data lives.

## Landmines

These will bite. In rough order of how much time they will cost:

1. ~~**Id collisions on clone.** Macro mappings are stored as ID references
   between a macro and its target parameter.~~ **DISPROVED by spike S3.**
   Macro mappings carry no ids at all: a mapping is a `KeyMidi` element
   *inside* the target parameter, and the target is named by containment.
   Copying a chain copies its mappings correctly, with no remapping.
   See `ARCHITECTURE.md` §5.

   Id hygiene may still matter for other cross-references — S6 is still
   open — but not for macros, which was the expensive case.

2. **FileRef is more than a path.** Sample references carry relative path
   type, search hints and other fields alongside the path. Rewrite only the
   path and samples come back offline. Diff a rack before and after swapping
   one sample to see the full set of fields that move.

3. **Round trip fidelity.** Before writing any generator, prove that
   `load` then `save` with zero changes produces a file Live still opens.
   If the no-op round trip breaks, nothing built on top will work.

## Where the knowledge lives

`ARCHITECTURE.md` is the consolidated model of how the format works, with
every claim marked verified or inferred. Read it before writing code that
touches XML. `SCHEMA.md` is the evidence behind it, `SPIKES.md` carries
the progress table and the procedure.

## Build order

1. ~~`io.py` + `diff.py` (done) and round-trip test~~ **done** — round trip
   verified lossless against a 560 KB rack, S1
2. `SCHEMA.md` populated by diffing: ~~macro mapping node~~ **done, S3**,
   chain zone node, FileRef node, macro variation node
3. `clone.py` — duplicate a chain N times with correct Id remapping
4. `samples.py` — retarget FileRef paths from a manifest
5. `variations.py` — generate Macro Variations by permuting macro values.
   This is the highest value module: it is what turns a few engines into
   hundreds of "sounds" and is completely impractical by hand.

## Testing

There is no unit test that proves Live will load a file. The only real test
is dragging it in. Keep a `racks/` folder of known-good inputs and after
every generator change, load the output in Live and confirm the macros
still move the right parameters.

Fail loudly. A corrupt `.adg` that Live silently half-loads is worse than
one it rejects.

## Musical context

See `TEMPLATE_SPEC.md` for what this tooling is actually building: the
eight track layout, the DR1 three level nesting pattern that `clone.py`
must replicate, the macro grammar, and the sound family constraint that
`variations.py` must respect.

## Session zero checklist

Before writing any generator, in this order:

1. Save the same rack from Live twice with no changes between saves.
   `adgkit diff a.adg b.adg`. This shows the noise floor and tells you
   whether the Id filter is catching everything it should.
2. Round trip a real rack: `io.load` then `io.save`, no changes, then drag
   the output into Live. If it does not open, stop and fix this first.
3. Change exactly one macro mapping in Live, save, diff, record the finding
   in `SCHEMA.md`.

Do not start `clone.py` until all three pass.
