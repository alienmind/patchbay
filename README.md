# adgkit

Generate and manipulate Ableton Live rack presets (`.adg`) programmatically.

`.adg` files are gzipped XML. Live's API cannot group devices into a rack,
create a macro mapping, or set a chain zone, so this works at the file level
instead.

## Current state

**Phase 0, spikes 5 of 13 done, S5 partial. Both kill criteria passed — the project is
viable.** Next action is Phase 1–2: `adgkit` core and `clone.py`.

**Phases 1 and 2 are done and gated in Live**: node navigation, parameter
and mapping read/write, and chain cloning. `python tests/test_adgkit.py`
runs 16 tests asserting the library still agrees with every recorded
finding.

The headline finding so far: **macro mappings are not id-based.** A
mapping is a `KeyMidi` element inside the target parameter, encoding a
virtual MIDI CC on channel 16 where the CC number is the macro index.
Targets are named by containment, so mappings survive a subtree copy —
which removes the risk that was expected to dominate Phase 2.

The macro-to-parameter transfer function is also known: linear over the
target parameter's own range. That is what Phase 5 needs to generate
variation grids.

Sample retargeting turned out cheap too — Live re-reads a sample's
metadata on load, so rewriting two path fields per sample is enough.

## Documents, in reading order

| file | what it is | read it when |
|---|---|---|
| **`README.md`** | this file: state, commands, workflow | first |
| **`ARCHITECTURE.md`** | how the `.adg` format works — the consolidated technical model, with confidence markers | before writing any code that touches XML |
| **`SPIKES.md`** | Phase 0 procedure and **progress table**, one section per spike | before running a spike |
| **`SCHEMA.md`** | lab notebook: raw findings per spike, citing files | when you doubt a claim in ARCHITECTURE |
| `CLAUDE.md` | working method and landmines | for the discovery discipline |
| `TEMPLATE_SPEC.md` | the musical target this tooling builds | for the specific layer |
| **`MCP.md`** | what Live's API can and cannot do, and how `adgkit` and `ableton-mcp` divide the work | before building anything that touches a running Live |
| `KICKOFF.md` | the plan, phases and fallbacks | for sequencing |

`ARCHITECTURE.md` is the model, `SCHEMA.md` is the evidence. If they
disagree, `SCHEMA.md` wins, because it cites files in `racks/`.

### Resuming this work

Read `SPIKES.md`'s progress table, then `ARCHITECTURE.md`. Between them
they carry the full state — nothing important lives only in a chat
transcript. Every **[V]** claim in `ARCHITECTURE.md` is reproducible from
the files in `racks/` with the commands listed in its §15.

## Requirements

- Python 3.10+
- Ableton Live 12 (for producing and verifying files — there is no
  automated test that proves Live will load a file)

## Install

```
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -e .
```

`-e` matters: the spikes involve editing `diff.py` (extending the id noise
filter), and an editable install picks that up without reinstalling.

That puts an `adgkit` command on PATH. Without installing, every command
below also works as `python -m adgkit.cli ...` from the repo root.

Verify:

```
adgkit --help
```

## Commands

### `adgkit roundtrip SRC [-o OUT]`

Spike S1. Loads a file and saves it back with zero changes, then reports
whether the result is byte identical and whether it is structurally
identical (every element, attribute and text node, ids included).

```
adgkit roundtrip racks/s1_source.adg
```

`structurally identical: NO` means the round trip is lossy — stop, nothing
built on top will work. `YES` with differing bytes is normal (lxml's
serialiser is not Live's) and is only a pass once Live opens the output.

Exits non-zero on structural failure, so it is usable as a check.

### `adgkit diff A B [--hide-ids] [--all] [--grep TEXT]`

The discovery engine. Structural diff between two files.

```
adgkit diff racks/s3_a.adg racks/s3_b.adg
adgkit diff racks/s7_a.adg racks/s7_b.adg --grep FileRef
```

By default it hides only what S2 proved churns on every save
(`RoundRobinRandomSeed`, and the `PresetRef` / `LastPresetRef` paths that
change whenever a spike pair is saved under two names). On a clean pair
this means an unedited save diffs as `identical`.

**Ids are shown by default.** S2 established that Live preserves
`Id` / `PointeeId` / `LomId` / `LomIdView` across saves, so they are signal
— usually *the* signal, since mappings appear to be built from them.

- `--hide-ids` drops them, for when a structural edit renumbers enough to
  drown the diff
- `--all` hides nothing, including per-save churn
- `--grep TEXT` keeps only facts whose path contains TEXT
- `-n N` / `--limit N` caps lines per section; counts stay exact. Adding one
  device drags its whole parameter blob in — a Reverb is ~800 facts

Output has three sections: `CHANGED` (a fact whose value moved), `REMOVED`
(present in A only), `ADDED` (present in B only). A node appearing with no
value still shows up, so structural additions are visible.

### `adgkit ids SRC [--fields A,B,C]`

Spike S6. Census of id-bearing fields. Per field: occurrence count, value
range, and whether values are unique across the file (file-scoped — a clone
must reallocate them) or duplicated (narrower scope — a clone must **not**
reallocate them, or mappings break).

```
adgkit ids racks/s6_a.adg
adgkit ids racks/s6_a.adg --fields Id,PointeeId,ReceivingNote
```

### `adgkit mappings SRC`

Lists every macro mapping in a preset: which macro drives which parameter,
in which rack, at which nesting depth.

```
adgkit mappings racks/s1_source.adg
```

```
3 macro mapping(s) in racks/s1_source.adg

  Macro 1  ->  MacroControls.0   [DrumGroupDevice, depth 1]
  Macro 1  ->  MacroControls.0   [InstrumentGroupDevice, depth 2]
  Macro 1  ->  ChainSelector     [InstrumentGroupDevice, depth 2]
```

Works by finding `KeyMidi` elements (see `ARCHITECTURE.md` §5). Flags any
mapping whose channel is not the macro bus, or whose mode is not absolute.

This is the check to run after every clone in Phase 2: the mapping list
before and after must match, with the right multiplicity.

### `adgkit clone SRC DEST [-c N] [-n N] [--pad] [--stride N]`

Duplicate a chain. `-c` picks which chain (default 0), `-n` how many
copies.

```
adgkit clone racks/s3b.adg build/out.adg -n 3
adgkit clone racks/s9_b.adg build/out.adg -n 3 --pad
adgkit clone racks/s3b.adg build/out.adg -n 3 --stride 2
```

**Ganged by default.** Copies keep the original's macro indices, so every
copy answers to the same macro and they move together. That is what the
sound family constraint in `TEMPLATE_SPEC.md` wants.

`--stride N` instead gives each copy its own block of N macros — chain 0
on macros 1..N, the first copy on N+1..2N, and so on — for when each
engine needs its own knob. Mappings that would pass macro 16 are left
where they are and reported, so running out is visible.

`--pad` assigns each copy the next free `ReceivingNote`, for drum racks.
Without it every copy answers to the original's note and they all trigger
together.

Refuses to write a file with sibling id collisions, which is the one thing
Live rejects outright.

### `adgkit check SRC`

Would Live accept this file? Reports sibling id collisions and exits
non-zero if any exist. Verified against Live's actual behaviour on three
deliberately broken files.

### `adgkit unpack SRC [-o OUT]` / `adgkit repack SRC DEST`

Gunzip to readable XML and back. Use for eyeballing a node a diff pointed
at, and for the deliberate-failure tests in S6, S7 and S12 (hand-edit the
XML, repack, see what Live does).

```
adgkit unpack racks/s1_source.adg          # -> racks/s1_source.adg.xml
adgkit repack racks/s1_source.adg.xml build/patched.adg
```

## Layout

```
adgkit/     generic library. Knows XML, ids, macros, chains, FileRefs.
            Knows nothing about kick drums. Keep it that way.
specs/      declarative description of the specific template
donors/     real device instances harvested from Live, to copy from
racks/      known-good inputs and spike evidence pairs
samples/    audio
build/      generated output, gitignored
```

## Workflow

Discovery is differential, never schema reading:

1. In Live, save a rack as `a.adg`
2. Change exactly **one** thing
3. Save as `b.adg`
4. `adgkit diff a.adg b.adg`
5. Record the finding in `SCHEMA.md`

Start with `SPIKES.md`, in the order it gives. S1 and S3 are kill criteria.

The schema is Live-version specific. Record the exact version in
`SCHEMA.md` and expect to redo spikes after a major Live update.
