# patchbay

Build Ableton Live racks and Sets from code.

A patchbay routes signals between things. This one routes macros to
parameters, chains to zones, and racks onto tracks — so that building a
large hyper-mapped Push template does not mean thousands of manual macro
mappings.

```python
PLAYGRND = Grammar("Engine", "Cutoff", "Resonance", "Decay",
                   "Drive", "Movement", "Space", "Character")

rack = Rack("PD1", PLAYGRND, kind=RackKind.INSTRUMENT)

with rack.engine("FM", "Operator") as e:
    e.bind(cutoff=("Filter/Frequency", 200, 8000),
           decay="Filter/Envelope/DecayTime")

with rack.engine("Sample", "OriginalSimpler") as e:
    e.bind(cutoff=("Filter/Slot/Value/SimplerFilter/Freq", 200, 8000),
           decay="Filter/Slot/Value/SimplerFilter/Envelope/DecayTime")
```

```
patchbay build examples/playgrnd.py -o build/
```

Both engines bind the same grammar slots to their own parameters, so one
knob moves the same musical idea through different synthesis. That is the
sound family constraint from `doc/TEMPLATE_SPEC.md`, structural rather
than a matter of discipline.

## Two halves, because Live splits this way

Fighting that split wastes effort, so the tool follows it.

**Racks are built as files.** Live's API cannot group devices into a rack,
create a macro mapping, or set a chain zone. Verified against Live's own
Object Model, not assumed — see `doc/MCP.md`. `.adg` files are gzipped
XML, so patchbay writes them directly.

**Sets are built through the API.** Track creation, naming, routing and
clips *are* scriptable, so those go through the `ableton-mcp` submodule
rather than generating `.als`. Sidechain source is missing from both, and
stays manual.

## Current state

Phase 0 discovery is **complete**: 12 spikes answered, 1 retired as
unnecessary, both kill criteria passed. What the format does is recorded
in `doc/ARCHITECTURE.md`, each claim marked verified, inferred or open and
traced to a file in `racks/`.

Built, and gated by loading in Live:

- read, write, lossless round trip
- structural diff — the discovery engine
- node navigation and parameter addressing, including nested paths
- macro mapping read and write, including ranges Live's own UI cannot set
- chain and drum-pad cloning
- the declarative DSL, and a compiler for specs

**Not built: macro variations**, which `doc/TEMPLATE_SPEC.md` argues is
the highest-value module here — ~692 sounds across 18 engines are
variations, not chains. That is the next thing.

`python tests/test_patchbay.py` runs 16 tests asserting the library still
agrees with every recorded finding.

## Install

```
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -e .
git submodule update --init     # ableton-mcp
```

`-e` matters: specs and findings are both still moving.

## Commands

| command | does |
|---|---|
| `patchbay build SPEC -o DIR` | compile a spec into rack presets |
| `patchbay diff A B` | structural diff — the discovery engine |
| `patchbay mappings SRC` | list macro mappings |
| `patchbay clone SRC DEST -n N` | duplicate a chain |
| `patchbay check SRC` | would Live accept this file? |
| `patchbay roundtrip SRC` | prove load-then-save is lossless |
| `patchbay ids SRC` | id census and collision report |
| `patchbay unpack` / `repack` | gzip in and out, for eyeballing XML |

`patchbay <command> --help` for options. Two worth knowing: `diff -n N`
caps output per section, because adding one device drags its whole
parameter blob in — a Reverb is some 800 facts. And `clone --stride N`
gives each copy its own macro block rather than ganging them together.

## Layout

```
patchbay/    the library. Knows XML, ids, macros, chains, FileRefs.
             Knows nothing about kick drums. Keep it that way.
examples/    specs. playgrnd.py is the template this project exists for.
doc/         how the format works, and how we found out.
donors/      real device instances harvested from Live, to copy from.
racks/       spike evidence. Every verified claim traces to one of these.
samples/     audio.
build/       generated output, gitignored.
tests/       assertions against the recorded findings.
ableton-mcp/ submodule: the Live-side half.
```

## Documentation

| file | what it is | read it when |
|---|---|---|
| **`doc/ARCHITECTURE.md`** | how the `.adg` format works — the consolidated model | before writing code that touches XML |
| **`doc/DSL.md`** | why the DSL is shaped as it is | before extending the DSL |
| **`doc/SPIKES.md`** | discovery procedure, progress, open questions | before investigating anything |
| **`doc/SCHEMA.md`** | lab notebook: raw findings, citing files | when you doubt a claim in ARCHITECTURE |
| **`doc/TEMPLATE_SPEC.md`** | the musical target, and the grammar | for what any of this is for |
| `doc/MCP.md` | what Live's API can and cannot do | before touching a running Live |
| `doc/KICKOFF.md` | the original plan, and how it changed | for sequencing |
| `CLAUDE.md` | working method and landmines | first, if you are an agent |

`doc/ARCHITECTURE.md` is the model, `doc/SCHEMA.md` is the evidence. If
they disagree, SCHEMA wins, because it cites files.

## Method

Discovery is differential, never schema reading:

1. In Live, save a rack as `a.adg`
2. Change exactly **one** thing
3. Save as `b.adg`
4. `patchbay diff a.adg b.adg`
5. Record the finding in `doc/SCHEMA.md`

Two rules learned the hard way, both in `doc/SPIKES.md`. Load-test by
**dragging into a running Live**, never by double-clicking — a second
instance hangs in a way indistinguishable from a rejected file, and that
cost one wrong conclusion. And the one-change rule applies to constructed
test files as much as to saves from Live.

The schema is version specific. Findings here are Live **12.4.3**; watch
`SchemaChangeCount` on the root element after an update.
