# TODO - the live backlog

The only place that says what is unfinished. Everything else in `doc/` is
settled knowledge. Live version for every item below: **12.4.3**.

## The backlog

In order. Nothing here blocks anything else, so the order is by what it
costs against what it decides.

| # | What | Who | Cost | Decides |
|---|---|---|---|---|
| 1 | Turn Macro 5 in `racks/q23_b.adg` | you | 1 knob | Whether a macro can sweep a send, and whether `Rack.sending` comes back |
| 2 | Open Hybrid Reverb in either DR1 return | you | 1 drag | Whether a harvested donor's blank IR slot is a missing file or a fallback |
| 3 | Name each strip instance for its track, `EQC_BS1` on BS1 | me | small | Nothing. It is a loop over a name, wanted when the strip is pasted across eight tracks |
| 4 | Decide whether to re-harvest 50 donors from 12.4.3 | you | a call | Whether every golden moves once now, or a rename bites later |
| 5 | `patchbay extract --layout patchbayground` | me | small | Whether extracted slots come out named or positional |
| 6 | Q8, the send taper | you | 2 saves | Only matters if a spec ever states send levels as percentages |

Items 1 and 2 are checks in Live. Nothing is waiting on them, but they are
the two cheapest facts left to buy.

## 1. Does a mapped send move

`Rack.sending` is buried in `THE_BASEMENT.md` on one check: the mapping
resolved and every send stayed at -inf. Q23 in `SCHEMA.md` now shows Live
writing the identical mapping by hand, reproduced byte for byte, so the
structural half of that conclusion is dead.

**Load `racks/q23_b.adg`, turn Macro 5, watch pad 1's Send A.** Moves means
the mechanism works and DR1's failure was ours to find. Does not move means
Live writes a mapping it ignores, which is a stronger claim than the one the
feature was buried on.

Until then DR1's kit slots 5 and 6 stay named and unbound.

## 2. The blank impulse response in DR1's returns

Harvesting strips paths, so the Hybrid Reverb in both DR1 return chains
carries an IR slot naming no file. A Simpler sample part in that state is
removed at build time; an IR slot cannot be, because the device needs one.

**Drag `build/DR1.adg` in and open either return's Hybrid Reverb.** Either
Live falls back to a built-in response, and nothing needs doing, or it
reports a missing file, and the donor needs re-harvesting with its IR.

## 4. The 50 donors that predate 12.4.3

Q19 found Live renaming a parameter family between 12.0_12203 and
12.0_12402: Compressor's sidechain EQ went from five children of a
`SideChainEq` element to five flat `SideChainEq_X` parameters. EQC wrote
three settings at the old paths for a release, and no test could see it,
because the DSL validates against the donor and the donor had them.

50 of the 59 donors were saved by 12.0_12203. Two ways out:

- **Re-harvest the lot from a 12.4.3 library.** One pass, and every golden
  moves at once, on purpose, with the checks that implies.
- **Leave them and compare names** against whatever 12.4.3 files land in
  `racks/`. Free, already done once, and covers only the devices those
  files happen to hold. It found the one rename above.

The second is in place. The first is a call about how much a silent wrong
path is worth avoiding.

## Standing manual work

**Not backlog.** These do not get automated, and trying is how the project
fails. A check that asks whether something SOUNDS right belongs here.

- Choosing which samples are good, and culling generated variations.
- Sound design judgement, gain staging, mix balance. A number taken by ear
  is not structure and no test can check one.
- Whether one knob feels comparable across engines. The ranges that make it
  so are declared and tested; whether the result is musical is ears.
- Assembling the Set: eight tracks, naming, routing, returns, tempo. Half an
  hour, once. `THE_BASEMENT.md` says why it is not automated.
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
