# TODO - the live backlog

The only place that says what is unfinished. Everything else in `doc/` is
settled knowledge. Live version for every item below: **12.4.3**.

## The backlog

In order. Nothing here blocks anything else, so the order is by what it
costs against what it decides.

| # | What | Who | Cost | Decides |
|---|---|---|---|---|
| 1 | Load `build/DR1.adg`, turn kit Macros 5 and 6 | you | 1 drag | Whether the restored send knobs sweep every pad, and whether the returns are now audible |
| 2 | Check the Hybrid Reverb in either DR1 return names an impulse response | you | same drag | Whether Q27's fix landed: the donor keeps Live's own IR path now |
| 3 | Q8, the send taper | you | 2 saves | Only matters if a spec ever states send levels as percentages |
| 4 | Re-run the donor name scan after a Live update | me | minutes | Nothing today. It is the check that catches a rename before a spec does |

Items 1 and 2 are the same drag. Everything else that was on this table has
landed: `sending` restored, per-track strip instances, `extract --layout`,
the five stale donors re-harvested.

## 1 and 2. One drag answers both

`build/DR1.adg` was rebuilt after both changes, so it carries them.

| # | Do this | Should happen |
|---|---|---|
| 1 | Turn kit Macro 5 (Send A) up | Every pad's Send A rises together, reverb comes in |
| 2 | Turn kit Macro 6 (Send B) up | Same for the delay return |
| 3 | Click the Hybrid Reverb inside the `A-Rvb:Short` return | It names an impulse response instead of reporting missing media |

Expected still open: per-pad send levels all start at the floor, so the
knobs are the only thing moving them.

## 3. Q8, the send taper

Sends are linear amplitude from `0.000316` to `1`. Whether the KNOB between
those is linear in amplitude or in dB is unknown, and it only matters if a
spec ever wants to say "this pad sends 30 percent".

Two saves settle it: a rack with one return, its send dragged to exactly
halfway on the slider, saved as `racks/q8_half.adg`, and the same at a
quarter as `racks/q8_quarter.adg`. If half reads `0.5`, the knob is linear
in amplitude; if it reads about `0.018`, it is linear in dB.

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
