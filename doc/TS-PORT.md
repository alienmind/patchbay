# Porting PatchBay to TypeScript

Whether to rewrite this project in TypeScript, following the `defineXXX()`
pattern of `m4l-jweb`, in order to make it more accessible and open the
door to a browser-hosted version.

Not decided. This file is the analysis, with what was measured and what
three separate arguments turned out to be worth. Nothing here is a plan.

## What the pattern looks like

`m4l-jweb`'s `packages/surface/src/index.ts` declares a device's Live
parameters as one object:

```ts
export default defineSurface({
  params: {
    rate: menu({ options: RATES, default: "off", short: "Rate" }),
    density: dial({ range: [0, 100], unit: "%", default: 50, short: "Dens" }),
  },
  banks: [{ name: "Perform", params: ["rate", "density"] }],
});
```

`banks` may only name parameters that exist, enforced by
`const P extends Record<string, ParamSpec>` and `Extract<keyof P, string>`,
so a renamed parameter breaks the build at the typo. What types cannot
reach, bank size and default-in-range, is checked at call time and throws.
The build imports the module, so a violation fails the build either way.

That maps onto this project cleanly. A layout is a set of named slots, an
engine is a set of paths bound to them, and both are exactly the shape
`defineSurface` handles.

## What was measured

### The XML layer is not a blocker

The concern was lxml. PatchBay needs parent pointers (`mappings.py` walks
up to the nearest `BranchPresets`), deep copies of donor subtrees, tree
surgery, and a serialisation that preserves the tree exactly.

`@xmldom/xmldom` does all four, in pure JS, so it runs in a browser.
Measured on real files:

| file | facts | parse | clone + surgery | serialise | round trip |
|---|---|---|---|---|---|
| `build/VA1.adg` | 15,006 | 70 ms | 7.9 ms | 15 ms | lossless |
| `build/PD1.adg` | 14,823 | 51 ms | 2.5 ms | 33 ms | lossless |
| `racks/s1_source.adg` | 18,148 | 51 ms | 3.6 ms | 50 ms | lossless |
| `donors/InstrumentMeld.adg` | 5,256 | | | | lossless |

Round trip means parse, serialise, reparse, and compare every element,
attribute and path. Nothing was lost on any of the four.

The fact counts are the same numbers `patchbay.diff.flatten` produces:
18,148 for `s1_source.adg` is the figure `CLAUDE.md` already quotes. A
flattener written independently in JS agreeing to the fact with the Python
one is the cross-check that says the port is possible at all.

Ableton's files are gzip, which browsers do natively.

### The donor payload fits a browser

`donors/` is 1.4 MB, and 1.1 MB of that is `Looper.adg` alone. The rest is
about 300 KB for 56 devices, which is a bundled asset rather than a
download. A browser version needs no server: it reads bundled donors,
writes an `.adg`, and hands it over as a file to drag into Live.

## Three arguments that did not survive

Each of these was offered as a reason to switch or not to. All three were
weaker than they looked.

### There is no coupling to the MCP half

The claim was that a port splits the project, because Live's Remote Script
is embedded Python and the Set half must stay there.

`patchbay/*.py` references `ableton-mcp` once, in a docstring.
`mcp/remote_script_additions.py` imports nothing from PatchBay. The wire
format is JSON over a socket: `params.get("track_index")` in, `{"index":
..., "name": ...}` out. What crosses the boundary is a file path and a rack
name.

`MCP.md` already settled this as architecture: the two have different
runtime models, they meet at the User Library, and MCP code is not to be
migrated into `patchbay`. So the Python remote script is a constant in
every scenario, not a cost of switching. **The argument is void.**

### Build-time type checking is not TypeScript's alone

The claim was that TypeScript could make hard rule 1 a compiler error and
Python could not.

Python can. A `Literal` union of Operator's 217 parameter paths, generated
from the donor library, plus a class-based `Layout` whose slots are
attributes, gives pyright everything it needs:

```
line 24: Cannot access attribute "filtr" for class "type[PATCHBAYGROUND]"
line 25: Argument of type "Literal['Filter/Freqency']" cannot be assigned
         to parameter "path" of type "OperatorParam"
line 26: Argument of type "Literal['Globals/PortamentoTim']" cannot be
         assigned to parameter "path" of type "OperatorParam"
--- 3 errors
```

A mistyped slot and two mistyped parameter paths, one of them a near miss
against a real path on another device, all caught before anything runs.

What TypeScript still does better is infer slot keys from a call-site
object literal through const generics, where Python needs the keys written
once as a class or a `TypedDict`. That is ergonomics, not capability.
**The strongest argument for switching was wrong.**

### The test suite is not 1,112 lines of translation

Of 63 tests:

| shape | count |
|---|---|
| load a checked-in `.adg` and assert facts about it | 19 |
| build a rack through the DSL | 20 |
| go through `examples/patchbayground.py` | 9 |

The 19 are not Python. "`s1_source.adg` has these mappings at this depth"
is a claim about a file, and it is also where the twelve spikes are
encoded. Extract them into a fixture both suites read and they become
language-neutral permanently, the same trick `tests/golden.txt` already
plays.

The 9 are covered by the golden digests, which are SHA values and belong to
no language. A port must reproduce the same five hashes, so the port has a
gate before it starts.

That leaves about 20 tests genuinely needing translation, and T9 rewrites
those anyway because it changes that exact API.

Deterministic transpilers are not the route: they would need lxml in JS.

## What is left

**For.** A browser-hosted version, which nothing else delivers, and which
measures cheap: 300 KB of donors, a lossless round trip at 70 ms, gzip in
the platform. Plus one toolchain across both projects.

**Against.** Samples. `Engine.sample` refuses a path that is not a file,
because a missing sample loads as an offline rack that passes every check
here and makes no sound. A browser cannot stat
`C:/Music/.../kick_001.wav`. DR1 is eight pads of eight samples, so the
browser build authors instrument racks and not the drum rack.

Partial mitigations: the File System Access API grants a real directory
handle on Chromium, or DR1 stays on a CLI build.

The shape of that is worth stating plainly. **The only surviving reason to
switch is the web app, and the strongest remaining objection is aimed at
the web app.** The other reasons cancelled out.

## The recommendation

Do T9 in Python. It is class 1 throughout, gated by `tests/golden.txt`,
and it costs no human checks. Add the pyright stubs on top and the
compile-time checking that looked TypeScript-only comes with it.

Then decide the browser version on its own merits rather than as a
side effect of a language preference.

## Open: Pyodide

Before pricing a port, price not porting. Pyodide ships lxml, so the
existing compiler might run in a browser unchanged, at the cost of a heavy
first load. Unverified, and about twenty minutes to find out. If it works,
the web app costs no rewrite and this document is moot.
