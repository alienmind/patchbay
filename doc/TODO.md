# TODO - the live backlog

The only place that says what is unfinished. Everything else in `doc/` is
settled knowledge. Live version for every item below: **12.4.3**.

## The backlog

In order. Nothing here blocks anything else, so the order is by what it
costs against what it decides.

| # | What | Who | Cost | Decides |
|---|---|---|---|---|
| 1 | Colour a rack's CHAINS and a clip | me | small, one diff first | Whether colour reaches inside a rack, not just the track list |
| 2 | Write a `.alp` as well as a `.als` | me | unknown, format undocumented | Whether a build ships as one installable file instead of a folder |
| 3 | Re-run the donor name scan after a Live update | me | minutes | Nothing today. It is the check that catches a rename before a spec does |

## 1. Colour inside a rack

**Tracks and returns are done**, Q39: `<Color Value="N" />`, 0 to 69, `-1`
for none, written by `live_set._color_track` and spread evenly across the
palette by `examples/patchbayground.py`.

What is left is the same element one level in. A Set-form `*Branch` carries
`Color`, so a rack's chains can be coloured, and so can a clip. **One diff
first**, because a branch also carries `AutoColored` and `AutoColorScheme`
and a track does not: save a rack with a hand-coloured chain, and see
whether `Color` survives with `AutoColored` still true, or whether Live
flips it. That is a five minute spike and it decides whether the DSL sets
one field or two.

The open shape question is the DSL surface, not the format. A palette index
is honest and unreadable; sixty-nine names are readable and are sixty-nine
names to invent and defend.

## 2. A `.alp` as a second output

`patchbay session` writes a `.als`, which is one file that refers to
samples wherever they happen to sit. A **Live Pack** is the packed form of
a whole Project: Live builds one with File > Manage Files > Manage Project
> Packing > Create Pack, and installs one by dragging the `.alp` in or via
File > Install Pack. So a Pack is what a build should ship as, and a `.als`
plus a folder is what it ships as now.

Not started, and the cost is unknown, because the container is
undocumented and nothing in `SCHEMA.md` touches it. The first spike is
whether it is an ordinary archive: unpack a Pack Live made, look at what
came out, and see whether the tree is a Project folder verbatim. If it is,
this is a writer over a known layout. If it is not, it is a format to
reverse and the answer may be no.

Note what it does NOT fix. Absolute paths were never a problem here:
routing is by track id (Q33), and sample retargeting needs the two path
fields on each FileRef (Q10). The paths in a Live-saved file are Live's own
bookkeeping.

**A Pack of PATCHBAYGROUND would carry the samples**, which is the same
licence question as `samples/`. A Pack is a distribution format, so this
task decides how a build is shipped, not just how it is written.

## 3. The donor name scan

Every donor has been compared by parameter NAME against Live 12.4.3's own
factory library, 73 files over 59 devices, no Live open. Three renames
found and fixed, three harmless additions, 53 unchanged. Q28 has the table.

Worth re-running after a Live update, because a rename is the one change
that breaks a spec silently: the DSL validates a binding against the donor,
so a stale donor is a stale vocabulary and the check passes on a fiction.

## Standing manual work

**Not backlog.** These do not get automated, and trying is how the project
fails. A check that asks whether something SOUNDS right belongs here.

- Choosing which samples are good, and culling generated variations.
- Sound design judgement, gain staging, mix balance. A number taken by ear
  is not structure and no test can check one.
- Whether one knob feels comparable across engines. The ranges that make it
  so are declared and tested; whether the result is musical is ears.
- Which track a sidechain listens to, and which track feeds which. Both are
  written by `patchbay session` now (Q33); which ones to pick is a mix
  decision.
- Confirming a mapped macro DOES something. Which mappings exist is not
  manual: `patchbay mappings` reads them out of the file and the tests
  assert the matrix, including the switch behind each modulator.

## The routine

1. Work a task from this file. Keep its status current here while it moves.
2. When it lands, DELETE it from this file and put what was learned in its
   permanent home:
   - a capability a user would want to know about: `README.md`
   - how the format works: `ARCHITECTURE.md`, with the evidence in
     `SCHEMA.md`
   - a shape decision about the DSL: `DSL.md`
   - an idea that did not work, an approach abandoned, a theory disproved:
     `THE_BASEMENT.md`
3. A task leaves this file exactly once, in exactly one direction. Nothing
   is archived in place, and no completed entries accumulate here.
