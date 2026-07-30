# TODO - the live backlog

The only place that says what is unfinished. Everything else in `doc/` is
settled knowledge. Live version for every item below: **12.4.3**.

## The backlog

In order. Nothing here blocks anything else, so the order is by what it
costs against what it decides.

| # | What | Who | Cost | Decides |
|---|---|---|---|---|
| 1 | Open `build/PATCHBAYGROUND.als` in Live | you | 1 double click | Whether the written Set loads: 8 tracks, 6 returns, 52 racks placed |
| 2 | Route the seven MIDI tracks into PM1, pick each EQC's sidechain source | you | 15 dropdowns | Nothing structural. Neither is writable, see below |
| 3 | Re-run the donor name scan after a Live update | me | minutes | Nothing today. It is the check that catches a rename before a spec does |

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
| tempo | 120 |
| SR1 | strip only. Its rack is blocked on samples, so the track says so by being empty |

**Open it and report what Live says.** A Set is a construct nothing here
has written before, so this is a class 3 check: it either loads or it does
not.

## 2. What the file cannot say

**Routing seven tracks into PM1.** Live writes `AudioOut/Main` or, inside
a group, `AudioOut/GroupTrack`. A track feeding another TRACK appears in
none of the 26 factory Sets, so the target's shape is unknown and writing
a guess is rule 1. Seven dropdowns.

**The sidechain source on each EQC.** Not in a device preset (Q18), not in
the LOM, and no factory example. Eight dropdowns.

Both become writable the moment a Set that contains one exists: save a Set
with one track routed into another and one compressor sidechained, and the
diff says what they are.

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
- Assembling the Set: eight tracks, naming, routing, returns, tempo. The
  strip is generated per track now, `EQC_BS1` on BS1, so this is dragging
  and naming rather than rebuilding. `THE_BASEMENT.md` says why it is not
  automated.
- Picking the sidechain source, one dropdown per track. A device preset does
  not carry one at all (Q18). Everything around it is declared.
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
