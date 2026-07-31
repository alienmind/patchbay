# TODO - the live backlog

The only place that says what is unfinished. Everything else in `doc/` is
settled knowledge. Live version for every item below: **12.4.3**.

## The backlog

In order. Nothing here blocks anything else, so the order is by what it
costs against what it decides.

| # | What | Who | Cost | Decides |
|---|---|---|---|---|
| 1 | Colour tracks, chains and clips from the DSL | me | small, the format is already read off | Whether a Set arrives looking like a Set someone laid out |
| 2 | Re-save the Q33 reference Set with no sampled rack in it | you | 2 minutes | Whether Q33 and Q37's evidence can live in `racks/` |
| 3 | Write a `.alp` as well as a `.als` | me | unknown, format undocumented | Whether a build ships as one installable file instead of a folder |
| 4 | Re-run the donor name scan after a Live update | me | minutes | Nothing today. It is the check that catches a rename before a spec does |

## 1. Colour

**The research is done and no spike is left.** Read off `q32_set.als`, the
26 factory Sets, and the templates `live_set` already uses.

**One element, one integer, everywhere it appears:**

    <Color Value="19" />

| carried by | scope |
|---|---|
| `MidiTrack`, `AudioTrack`, `ReturnTrack`, `MainTrack` | the track |
| `MidiClip`, `AudioClip` | one clip |
| every `*Branch` in Set form | one chain inside a rack |
| `Scene` | one scene |
| `PreHearTrack` | always `-1` |

**The value is an index into Live's palette, 0 to 69.** Established across
the 26 factory Sets: minimum 0, maximum 69, 39 distinct values in use, and
70 is the size of the swatch grid Live shows. **`-1` means no colour**, and
`Scene` and `PreHearTrack` carry it.

Two counters sit at Set level and drive Live's own auto-colouring:
`AutoColorPickerForPlayerAndGroupTracks/NextColorIndex` and
`AutoColorPickerForReturnAndMainTracks/NextColorIndex`. A Set that sets
every colour explicitly does not need them, and what they do when a colour
is written by hand is unchecked.

A branch also carries `AutoColored` and `AutoColorScheme`, which a track
does not. Whether writing `Color` on a branch while `AutoColored` is true
survives a save is the one thing worth a diff before this ships.

### What it needs

`live_set.Track` already accepts `color` and does nothing with it, which is
the worst of both. Wire that, and add the same on the return list and on a
rack's chains in the DSL. A palette index is a number a person should not
have to memorise, so the DSL surface is the open question rather than the
format: an integer is honest and unreadable, a name is readable and is
sixty-nine names to invent and defend.

**Class 2 at most.** `Color` is a value inside a construct every shipped
Set already carries, so the file loads either way. A human eye confirms the
colour is the one asked for.

## 2. The Q33 reference Set

The hand-built Set that answered track-to-track routing and the sidechain
source is `build/q32_set Project/q32_set.als`, and it **cannot be
committed**: DR1 sits on T2, so the file enumerates sample filenames.

That one file also settled Q35, Q37 and Q38, which is four findings resting
on a donor the repo does not hold. The tests assert against what `live_set`
writes rather than against a Live-saved file, which is weaker than every
other finding here.

To close it: open that Set, delete DR1 from T2, drop any stock device on T2
in its place so the sidechain still has a source, and save as
`q33_set.als`. Then it goes in `racks/` and the tests read it.

## 3. A `.alp` as a second output

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

## 4. The donor name scan

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
