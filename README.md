# patchbay

Build Ableton Live racks and Sets from code.

## Why this project?

Live already exposes a programming interface. The Live Object Model
drives a session that is **open and running**: create a track, name it,
set its routing, fire a clip, move a parameter. Anything you can script
against a live Set, script through the LOM.

The LOM stops short in two ways. Parts of it are undocumented, and parts
of what the Set contains simply has no API at all. Grouping devices into
a rack, creating a macro mapping, setting a chain zone: none of these are
in the Object Model. Verified against Live's own model, not assumed, see
`doc/MCP.md`.

patchbay covers the other half by writing the **files**. An `.adg` is a
gzipped XML document, so is an `.als`, so is an `.adv`. What the API will
not build, the file format will, and patchbay writes and reads that XML
directly.

That changes what maintenance costs. A rack or a project kept current by
hand is hands on work: every mapping clicked, every variation dialled,
every fix repeated in each copy that inherited it, and all of it held
together by the author's discipline. Nothing records what changed or why,
and nothing carries a correction forward.

Declared as code, a rack gets the tools ordinary software already has. It
lives in version control, it diffs, it reviews, it rebuilds. A new Live
version, a renamed parameter, or a change of taste by whoever authored
the racks is an edit to a spec and one `patchbay build`, not an afternoon
of mousing. The source of truth is the spec, and the `.adg` is output.

A patchbay routes signals between things. This one routes macros to
parameters, chains to zones, and racks onto tracks - so that building a
large hyper-mapped Push template does not mean thousands of manual macro
mappings.

```python
PATCHBAYGROUND = Grammar("Instrument", "Sound", "Filter", "Drive",
                         "Movement", "Character", "Release", "Volume",
                         selector="Instrument")

rack = Rack("PD1", PATCHBAYGROUND, kind=RackKind.INSTRUMENT)

with rack.engine("FM", "Operator") as e:
    e.bind(filter="Filter/Frequency",
           release="Operator.0/Envelope/ReleaseTime")

with rack.engine("Sample", "OriginalSimpler") as e:
    e.bind(filter="Filter/Slot/Value/SimplerFilter/Freq",
           release="VolumeAndPan/Envelope/ReleaseTime")
```

```
patchbay build examples/patchbayground.py -o build/
```

Both engines bind the same grammar slots to their own parameters, so one
knob moves the same musical idea through different synthesis. That is the
sound family constraint from [`doc/PATCHBAYGROUND.md`](doc/PATCHBAYGROUND.md),
structural rather than a matter of discipline.

## Inspired by PLAYGRND

The idea came from **PLAYGRND**, an Ableton Live Set by **Andri Soren**:
https://www.youtube.com/watch?v=plQ9F-0RmDw

What that Set demonstrates is an architecture worth taking: one macro
grammar repeated across every rack, engines as chains, a sound addressed by
TWO knobs rather than one, a fixed channel strip on every track, and racks
nested inside racks so one instrument reaches all the others.

A sound is `(instrument, sound)`: one macro picks the engine, a second
steps a chain selector within it. Both are macros, so both are playable
while a clip runs. Variations then carry a whole vector of macro values at
once, which makes them right for presets and wrong for a sound browser.

Assembling that by hand is thousands of macro mappings and tens of thousands
of variation values, all clicked in one at a time. patchbay generates it from
a declaration instead. Same architecture, our own taste, in a spec that
diffs.

The target is spelled out in [`doc/PATCHBAYGROUND.md`](doc/PATCHBAYGROUND.md)
and declared in code in
[`examples/patchbayground.py`](examples/patchbayground.py).

## Two halves, because Live splits this way

The split above is not a design choice, it is where Live's API ends.
Fighting it wastes effort, so the tool follows it.

**Racks are built as files.** Racks, macro mappings and chain zones are
outside the Object Model, so patchbay writes the gzipped XML of the
`.adg` itself.

**Sets are built through the API.** Track creation, naming, routing and
clips *are* scriptable, so those go through the LOM via the `ableton-mcp`
submodule rather than generating `.als`. Sidechain source is missing from
both, and stays manual.

`ableton-mcp` is vendored for inspiration, not as a dependency to build
on. It is one worked example of driving the LOM, and it inherits every
limit the LOM has. What patchbay learns about the file format could make
a better MCP server possible, one that reaches past the Object Model.
Whether that is what this becomes, time will tell.

Its standing role here is the test harness. A file that passes
`patchbay check` is still only a file, and no unit test proves Live will
load it. MCP is how a build gets tested **live**: drive a running Live,
put the device we just wrote onto a track, read back what Live made of
it, and do that programmatically rather than by hand. That makes
integration tests possible against the real application, and it is the
only way patchbay ever confirms a device actually deploys.

## What it does

Everything here is built, and every item was gated by loading the output
in Live 12.4.3.

- read, write, lossless round trip
- structural diff - the discovery engine
- node navigation and parameter addressing, including nested paths
- macro mapping read and write, including ranges Live's own UI cannot set
- chain and drum-pad cloning
- the declarative DSL, and a compiler for specs
- macro variations
- nested racks, at any depth, with macros chaining into them
- sample retargeting, so a chain plays a file you name rather than
  whichever one the donor happened to carry
- extraction: read a saved `.adg` back out as DSL source
- donor harvesting from any saved file, Live Sets included

A variation is a vector over grammar slots in macro space, so it renders
through every engine without being written per engine, and it may select
its own engine:

```python
rack.variations(Variation("dark", instrument=rack.engine_macro("FM"),
                          filter=30, release=110))
```

A chain may hold another rack instead of a device, which is how the drum
rack in `PATCHBAYGROUND.md` gets its three levels:

```python
rack.nest("PADS", pd1())
rack.nest("KEYS", ld1()).bind(filter="filter", release="release")
```

Bindings are outer slot to inner slot, and default to identity when both
racks share a grammar. So one knob reaches through however many levels are
between it and the parameter, and the spec says only where it should not.

`patchbay extract` runs the compiler backwards, printing a `Rack(...)`
declaration for a saved rack: chains, device types, macro mappings with
their ranges, chain zones, samples, macro positions, labels, variations and
nesting to any depth.

```
patchbay extract build/DR1.adg > dr1.py
patchbay build dr1.py -o build/rt/
patchbay diff build/DR1.adg build/rt/DR1.adg      # identical
```

That round trip is exact for a rack patchbay built, and a test holds it
there. For a rack Live built it recovers the skeleton and not the sound:
the emitted source fills each device from a donor, so parameter values, a
chain's second and third device, and per-rack cosmetics do not survive.
Slot names never survive either - they are intent, and the emitted grammar
is positional, `Macro_1` through `Macro_N`, for you to rename.

A device can only be used if the library has a donor for it, and donors
come from files you already own:

```
patchbay harvest "path/to/Project" -o donors_local/
```

Indexing a device never looks at preset structure, so a `.als` donates its
devices exactly as a rack does and one Set is usually worth dozens of
hand-saved racks. Paths and names are stripped on the way out, and a tag
the library already indexes is left alone so a fuller copy of a device
cannot silently rebuild racks that were gated against the old one.

`uv run pytest tests/ -q` runs 59 tests asserting the library still
agrees with every recorded finding. One of them clears the variations Live
wrote in `racks/s8_c.adg`, writes them back through `patchbay`, and requires
the diff to be empty.

What is in flight and what is next lives in
[`doc/TODO.md`](doc/TODO.md), the live backlog.

## Install

Managed with [uv](https://docs.astral.sh/uv/).

```
uv sync                         # creates .venv, installs patchbay editable
git submodule update --init     # ableton-mcp
```

Editable matters, and `uv sync` does it by default: specs and findings are
both still moving.

Then either activate the environment, or prefix commands with `uv run`:

```
uv run patchbay build examples/patchbayground.py -o build/
uv run pytest tests/ -q
```

`uv run` works from any directory with `--project`, which matters for the
probe scripts in `build/`. Nothing needs a global install, and there is no
`pip install -e .` step to get stale - the failure mode that prompted this
was an editable install still pointing at the folder's old name.

## Commands

| command | does |
|---|---|
| `patchbay build SPEC -o DIR` | compile a spec into rack presets |
| `patchbay diff A B` | structural diff - the discovery engine |
| `patchbay mappings SRC` | list macro mappings |
| `patchbay variations SRC` | list macro variations |
| `patchbay clone SRC DEST -n N` | duplicate a chain |
| `patchbay extract SRC` | emit DSL source for a saved rack |
| `patchbay harvest SRC -o DIR` | lift donors out of files or Live Sets |
| `patchbay check SRC` | would Live accept this file? |
| `patchbay roundtrip SRC` | prove load-then-save is lossless |
| `patchbay ids SRC` | id census and collision report |
| `patchbay unpack` / `repack` | gzip in and out, for eyeballing XML |

`patchbay <command> --help` for options. Two worth knowing: `diff -n N`
caps output per section, because adding one device drags its whole
parameter blob in - a Reverb is some 800 facts. And `clone --stride N`
gives each copy its own macro block rather than ganging them together.

## Layout

```
patchbay/    the library. Knows XML, ids, macros, chains, FileRefs.
             Knows nothing about kick drums. Keep it that way.
examples/    specs. patchbayground.py is the template this project exists for.
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
| **`doc/TODO.md`** | the live backlog: in flight, next, open spikes | before starting anything |
| **`doc/ARCHITECTURE.md`** | how the `.adg` format works - the consolidated model | before writing code that touches XML |
| **`doc/DSL.md`** | why the DSL is shaped as it is | before extending the DSL |
| **`doc/SPIKES.md`** | discovery procedure and the spikes that answered it | before investigating anything |
| **`doc/SCHEMA.md`** | lab notebook: raw findings, citing files | when you doubt a claim in ARCHITECTURE |
| **`doc/PATCHBAYGROUND.md`** | the musical target, the grammar, and what inspired it | for what any of this is for |
| `doc/MCP.md` | what Live's API can and cannot do | before touching a running Live |
| `doc/THE_BASEMENT.md` | ideas that failed, and what killed them | before reviving a good-sounding plan |
| `doc/KICKOFF.md` | the original plan, and how it changed | for sequencing |
| `CLAUDE.md` | working method and landmines | first, if you are an agent |

`doc/ARCHITECTURE.md` is the model, `doc/SCHEMA.md` is the evidence. If
they disagree, SCHEMA wins, because it cites files.

`doc/TODO.md` is the only file that says what is unfinished. When a task
lands it leaves that file, into README, ARCHITECTURE or THE_BASEMENT.

## Live version

The file format is version specific. Everything here was established
against Live **12.4.3**, and a major Live update may need the findings
rechecked. How that checking is done is `CLAUDE.md` and `doc/SPIKES.md`,
which are written for whoever, or whatever, does the work.
