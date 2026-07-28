# patchbay

Author Ableton Live racks and Sets in code instead of by clicking.

## What this is

A DSL and a toolchain for writing Live racks as source. You declare what a
rack is - engines, macro grammar, bindings, ranges, zones, variations,
nesting - and `patchbay build` produces the `.adg` Live opens. It also runs
backwards: `patchbay extract` reads a saved rack and prints the declaration
that rebuilds it.

Inspired in ideas from [strudel.cc](https://strudel.cc) and TidalCycles,
but instead of targetting live coding of music, patchbay is about
**offline authoring**. Nothing here makes a sound. It produces the
assets you will load in your DAW.

## Motivation

Instead of spending an afternoon dragging, dropping, patching
and connecting macros, you just do an edit and a rebuild from well-known
patterns.

That changes what maintenance costs. A rack kept current by hand is hands
on work: every mapping clicked, every variation dialled, every fix repeated
in each copy that inherited it, held together by the author's discipline.
Nothing records what changed or why, and nothing carries a correction
forward.

Declared as code, a rack gets the tools ordinary software already has. It
lives in version control, it diffs, it reviews, it rebuilds. A new Live
version, a renamed parameter, or a change of taste is an edit to a spec and
one `patchbay build`.

## Why files rather than the API

Live already exposes a programming interface. The Live Object Model drives
a session that is **open and running**: create a track, name it, set its
routing, fire a clip, move a parameter. Anything you can script against a
live Set, script through the LOM.

The LOM stops short in two ways. Parts of it are undocumented, and parts of
what a Set contains have no API at all. Grouping devices into a rack,
creating a macro mapping, setting a chain zone: none of these are in the
Object Model. Or at least that I've been slowly digging while looking into
other examples, like ableton-mcp (see [`doc/MCP.md`](doc/MCP.md)).

patchbay covers the other half by writing the **files**. An `.adg` is a
gzipped XML document, so is an `.als`, so is an `.adv`. What the API will
not build, the file format will.

## Basic Concepts

Similar to a real patchbay in a music studio - routing signals between things.
This tool routes macros to parameters, chains to zones, and racks onto tracks.

```python
PATCHBAYGROUND = Grammar("Instrument", "Sound", "Filter", "Drive",
                         "Movement", "Character", "Release", "Volume",
                         selector="Instrument")

rack = Rack("PD1", PATCHBAYGROUND, kind=RackKind.INSTRUMENT)

with rack.engine("FM", "Operator") as e:
    e.bind(filter="Filter/Frequency",
           release=("Operator.0/Envelope/ReleaseTime", 10, 20000))

with rack.engine("Sample", "OriginalSimpler") as e:
    e.bind(filter="Filter/Slot/Value/SimplerFilter/Freq",
           release=("VolumeAndPan/Envelope/ReleaseTime", 10, 20000))
```

Both engines bind the same grammar slots to their own parameters, so one
knob moves the same musical idea through different synthesis.

Most of the vocabulary is Live's. A few terms are this project's own, and
those are the ones worth pinning down, because they are what the DSL is
made of.

| term | from | what it means |
|---|---|---|
| **rack** | Live | a container of parallel chains, with 16 macro knobs on its front |
| **chain** | Live | one signal path inside a rack, holding devices |
| **device** | Live | an instrument or effect: Operator, Saturator, Auto Filter |
| **macro** | Live | one of the rack's 16 knobs. Its position is 0..127 and nothing else |
| **chain selector** | Live | the control that decides which chain is live |
| **zone** | Live | the span of 0..127 over which one chain answers the selector |
| **pad** | Live | a drum rack chain, chosen by a MIDI note instead of a zone |
| **variation** | Live | a stored position for every macro, recalled as one. Live's UI says Variations, the XML says Snapshots |
| **engine** | patchbay | one chain and the device in it, treated as one way of making the sound |
| **slot** | patchbay | one position in the grammar. Slot N is macro N |
| **grammar** | patchbay | the ordered list of slot NAMES, shared by every rack that uses it |
| **binding** | patchbay | one slot pointed at one parameter of one device |
| **range** | patchbay | the span of that parameter the macro drives, in the parameter's own units |
| **label** | patchbay | what a knob is CALLED on this rack, which is not what it is keyed by |
| **donor** | patchbay | a real device instance to copy a device from |
| **spec** | patchbay | a Python module declaring racks, the input to `patchbay build` |

**A grammar is a contract, not a template.** It says slot 3 is `Filter` and
that slot 3 is macro 3, everywhere. A rack does not *have* those macros, it
BINDS its own parameters to them. Reuse the grammar across racks and one
knob means one musical idea on every one of them, structurally rather than
by discipline.

**A binding names a parameter, and parameter names are not the GUI
labels.** `Filter/Slot/Value/SimplerFilter/Freq` is Simpler's cutoff. This
is why `donors/` exists and why a binding is written against one, never
from memory: see [Everything here is guessed from empirical evidence](#everything-here-is-guessed-from-empirical-evidence).

**A range is what makes a slot mean the same thing twice.** Two engines can
bind the same slot to the right parameter each and still disagree, because
one is decibels and the other linear amplitude, or one is seconds and the
other milliseconds. Where engines disagree about units, the range is the
only place the agreement can live. Live 12.4.3 has no UI for it at all.

**A variation is a vector over slots, in macro space.** So it renders
through every engine without being written per engine, and it can select
its own engine on the way:

```python
rack.variations(Variation("dark", instrument=rack.engine_macro("FM"),
                          filter=30, release=110))
```

**A chain may hold a rack instead of a device.** Bindings are then outer
slot to inner slot, defaulting to identity where both racks share a
grammar, so one knob reaches through however many levels lie between it and
the parameter:

```python
rack.nest("PADS", pd1())
rack.nest("KEYS", ld1()).bind(filter="filter", release="release")
```

## Everything here is guessed from empirical evidence

Ableton publishes no schema, and its element names are not the GUI labels:
Saturator's Drive knob is `PreDrive`, Simpler's cutoff is
`Filter/Slot/Value/SimplerFilter/Freq`.

So I've had to guess some stuff, but following a strict methodology:
Change ONE thing in Live, save, diff the two files, write down what moved.

The findings are in [`doc/ARCHITECTURE.md`](doc/ARCHITECTURE.md), each marked verified or
inferred, with the evidence in [`doc/SCHEMA.md`](doc/SCHEMA.md).

`donors/` contains real device instances,
harvested from racks and Sets hand crafted, and they are what the DSL is
learned FROM: a device's parameter list, the path to each parameter, and
the native range each one spans. A binding is written against a donor and
checked. `patchbay harvest` adds more from any
file you already own.

## PATCHBAYGRND - The ultimate end-to-end test

The idea and inspiration of this project came from the amazing **PLAYGRND**, an Ableton Live Set
by **Andri Soren**: https://www.youtube.com/watch?v=plQ9F-0RmDw

Based on the information publicly made available from the author, what that Set demonstrates
is worth taking: one macro grammar repeated across every rack, engines as chains,
using knobs to quickly switch between instruments, a semi fixed channel strip on every track,
and racks nested inside racks so one instrument reaches all the others.

[`examples/patchbayground.py`](examples/patchbayground.py) is this
project's attempt at rebuilding that, from what is publicly visible of it
plus everything harvesting the devices has taught us. It serves as **one big
example, and the end-to-end test**. Six racks, three levels of nesting, 96
variations, eight drum pads - if a change breaks something real, it breaks
there first. The musical target is spelled out in
[`doc/PATCHBAYGROUND.md`](doc/PATCHBAYGROUND.md).

## Potential way forward - authoring of Ableton assets via MCP

`ableton-mcp` is vendored within this project as well and a potential
future scope.

It is one worked example of driving the LOM, and it inherits every
limit the LOM has.

This project aims to complement where Live's API falls short.

**Racks are built as files.** Racks, macro mappings and chain zones are
outside the Object Model, so patchbay writes the gzipped XML of the
`.adg` itself.

**Sets can still be built through the API.** Track creation, naming, routing and
clips *are* scriptable, so those go through the LOM via the `ableton-mcp`
submodule rather than generating `.als`. Sidechain source is missing from
both, and stays manual.

For now, ableton-mcp is the test harness. A file that passes
`patchbay check` is still only a file, and no unit test proves Live will
load it. MCP is how a build gets tested **live**: drive a running Live,
put the device we just wrote onto a track, read back what Live made of
it, and do that programmatically rather than by hand. That makes
integration tests possible against the real application, and it is the
only way patchbay ever confirms a device actually deploys.

## What works today

Every item below was gated by loading the output in Live 12.4.3.

- read, write, lossless round trip
- structural diff, which is the discovery engine
- node navigation and parameter addressing, including nested paths
- macro mappings read and written, including ranges Live's own UI cannot set
- chain and pad cloning
- the DSL and its compiler: engines, bindings, ranges, zones, labels, start
  positions, variations, nesting to any depth
- sample retargeting, so a chain plays a file you name rather than whichever
  one the donor happened to carry
- extraction, the compiler backwards
- donor harvesting from any saved file, Live Sets included

`patchbay extract` prints the declaration for a saved rack: chains, device
types, bindings with their ranges, zones, samples, macro positions, labels,
variations and nesting.

```
patchbay extract build/DR1.adg > dr1.py
patchbay build dr1.py -o build/rt/
patchbay diff build/DR1.adg build/rt/DR1.adg      # identical
```

That round trip is exact for a rack patchbay built, and a test holds it
there. For a rack Live built it recovers the skeleton and not the sound:
each device is refilled from a donor, so parameter values, a chain's second
and third device, and per-rack cosmetics do not survive. Slot names never
survive either. They are intent, not structure, so the emitted grammar is
positional, `Macro_1` through `Macro_N`, for you to rename.

`patchbay harvest` is how the donor library grows, from files you already
own:

```
patchbay harvest "path/to/Project"
```

Indexing a device never looks at preset structure, so a `.als` donates its
devices exactly as a rack does and one Set is usually worth dozens of
hand-saved racks. Paths and names are stripped on the way out, and a device
the library already holds is left alone: a fuller copy would win on
parameter count and silently rebuild racks that were gated against the old
one.

`uv run pytest tests/ -q` runs 59 tests asserting the library still agrees
with every recorded finding. One of them clears the variations Live wrote
in `racks/s8_c.adg`, writes them back through `patchbay`, and requires the
diff to be empty.

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
examples/    specs. patchbayground.py is the big one, and the end-to-end test.
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
