# TODO - the live backlog

The only place that says what is unfinished. Everything else in `doc/` is
settled knowledge. Live version for every item below: **12.4.3**.

## The backlog

In order. Nothing here blocks anything else, so the order is by what it
costs against what it decides.

| # | What | Who | Cost | Decides |
|---|---|---|---|---|
| 1 | Drag `build/PATCHBAYGROUND.als` into Live, attempt 5 | you | 1 drag | Whether the written Set loads: 8 tracks, 6 returns, 52 racks placed, all routing written |
| 2 | Re-save the Q33 reference Set with no sampled rack in it | you | 2 minutes | Whether Q33's evidence can live in `racks/` |
| 3 | Write a `.alp` as well as a `.als` | me | unknown, format undocumented | Whether a build ships as one installable file instead of a folder |
| 4 | Re-run the donor name scan after a Live update | me | minutes | Nothing today. It is the check that catches a rename before a spec does |

## 1. The Set

    patchbay session examples/patchbayground_set.py -o build/PATCHBAYGROUND.als

Written, and verified as far as a file can be without Live: every one of
the 52 placed racks was lifted back out with `extract.preset_from_set` and
compared to the `.adg` it came from. 51 match exactly and DR1 differs in 18
facts of provenance metadata on its two return branches. No value moved.

| | |
|---|---|
| tracks | DR1, BS1, PD1, LD1, SR1, VA1, VA2 as MIDI; PM1 as audio |
| returns | A-Rvb:Short, B-Rvb:Long, C-Dly:Short, D-Dly:Long, E-Spc:Wide, F-Drv:Grit |
| strip | ARP1, MFX1, instrument, EQC, AFX1, AFXS1, Channel EQ, VOL1, each named for its track |
| routing | every track but PM1 feeds PM1; every EQC but DR1's sidechains from DR1 |
| tempo | 120 |
| SR1 | strip only. Its rack is blocked on samples, so the track says so by being empty |

**Open it and report what Live says.** A Set is a construct nothing here
has written before, so this is a class 3 check: it either loads or it does
not, and so far each attempt has found exactly one more thing:

| attempt | Live said | what it was |
|---|---|---|
| 1 | `Invalid Pointee Id.` | preset form writes `Id="0"` on every pointee; a Set refuses zero. Q31 |
| 2 | `Illegal class of list member (AudioEffectBranch)` | a rack's return chain is `ReturnBranch` in Set form. Q32 |
| 3 | `PointeeId 341 is used 8 times.` x131 | `ControllerTargets.N` is a pointee and Q31's rule named tags, not the shape. Q34 |
| 4 | nothing. `EXCEPTION_ACCESS_VIOLATION`, Live gone | 221 branches carried `DocumentColorIndex`, and every drum branch a `ZoneSettings`. Both are preset-only. Q35 |
| 5 | unrun | |

**A crash is a worse answer than a refusal.** Attempt 4 parsed clean and
took Live down 177 ms later, so the log says only the version and the
exception. Where a refusal names the element, a crash names nothing, and
the finding came from diffing against the Q33 reference Set instead.

**Do not accept Live's repair offer.** Attempt 3 repaired, reported
success, and then crashed Live with `EXCEPTION_ACCESS_VIOLATION` on
reload. A repaired Set answers nothing and costs a restart.

The pattern is worth naming: each failure is one field or tag whose value
is REQUIRED to differ between the two forms, and neither Q9 nor the factory
templates announce which. Expect more, and read the message literally - it
has named the exact element every time.

## 2. The Q33 reference Set

The hand-built Set that answered track-to-track routing and the sidechain
source is `build/q32_set Project/q32_set.als`, and it **cannot be
committed**: DR1 sits on T2, so the file enumerates sample filenames.

Q33 records the two nodes, which is the whole finding, but the tests assert
against what `live_set` writes rather than against a Live-saved file, which
is weaker than every other finding here.

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
