# CLAUDE.md - working rules for agents in this repo

This repo builds Ableton Live racks from Python, and Live Sets through the
`ableton-mcp` submodule. Start with `README.md`, then `doc/ARCHITECTURE.md`
for how the file format works and `doc/SPIKES.md` for what is still open.
This file is only the house rules, the things not derivable from the code.

## The method

Nothing here is learned by reading Ableton's schema. It is learned by
changing ONE thing in Live and diffing:

1. Save a rack as `a.adg`
2. Change exactly one thing
3. Save as `b.adg`
4. `patchbay diff a.adg b.adg`
5. Write the finding in `doc/SCHEMA.md`, citing both files

The one-change rule applies to files you CONSTRUCT too. A test file with
two edits in it produced one wrong conclusion in this repo already.

Every feature is preceded by a diff that proves where the data lives. No
feature rests on a guess about the format.

## Asking for a test in Live

No unit test proves Live will load a file. A change lands as a file to be
dragged in by hand. Make that request SCHEMATIC:

1. Name the EXACT file - `build/PD1.adg`, not "the output".
2. A table and little else: check number, what to do, what should happen.
3. One line on what is expected to still be broken at this stop.
4. Ask for the result by check NUMBER.

Do NOT re-explain how racks work, or what a macro is. That is known.

> Load **`build/PD1.adg`**.
>
> | # | Do this | Should happen |
> |---|---------|---------------|
> | 1 | Turn Macro 1 full left, then full right | Engine sweeps FM to Sample |
> | 2 | Turn Macro 2 | Cutoff moves on whichever engine is selected |
>
> Expected still broken: macros 5-13 are unbound.

**DRAG IT IN. Never double-click an `.adg`.** Double-clicking starts a
SECOND Live instance, which hangs for a few seconds and loads nothing.
That is indistinguishable from Live rejecting the file, and it already
caused a retracted finding. When a load fails, check
`%APPDATA%/Ableton/Live <version>/Preferences/Log.txt` for `CommandLine`
and `Another instance` before concluding anything.

## Hard rules

1. **NEVER INVENT A PARAMETER NAME.** Ableton's element names are not the
   GUI labels and are not guessable. Saturator's Drive knob is `PreDrive`,
   its Output is `PostDrive`. Simpler's filter cutoff is
   `Filter/Slot/Value/SimplerFilter/Freq`. Operator has 217 parameters.
   Use `library.Device.search("filter", "freq")` and read what comes back.
   A wrong name does not error, it produces a rack with a missing mapping.
2. **An `Id` must be unique among its SIBLINGS.** Nothing else about it
   matters: not contiguity, not matching the index, not file-wide
   uniqueness. Give two sibling branches the same `Id` and Live refuses
   the ENTIRE preset. `clone.assert_loadable()` catches it before writing;
   do not route around it.
3. **Never byte-compare two `.adg` files.** Two semantically identical
   files differ by about 4 percent, because Live writes CRLF and `<X />`
   and lxml does not. Use `patchbay diff`, which compares the parsed tree.
4. **A rack's `Device` and its `BranchPresets` are SIBLINGS.** A parameter
   controlled by a macro is never a descendant of the rack node owning
   that macro. Walking up to the nearest `*GroupDevice` to find the owning
   rack is wrong and has already shipped as a bug once. Walk to the
   nearest `BranchPresets` and take its parent.
5. **Three scales, do not mix them.** Device parameters are in native
   units over their own range. Macros and variations are 0..127
   continuous. Sends are linear amplitude, 0.000316 to 1. The table is in
   `doc/ARCHITECTURE.md` section 12.
6. **No musical vocabulary inside `patchbay/`.** If you are writing the
   word "kick" or "darkwave" in the library, it belongs in `examples/`.
   The library knows XML, ids, macros, chains and FileRefs. It does not
   know what they are for.

## Facts that look like bugs

The terse rules are above. The spike that PROVED each one, with the files
it used, is `doc/SCHEMA.md`. The consolidated model is
`doc/ARCHITECTURE.md`. When one of these bites, read the evidence, do not
re-derive it.

- **A macro mapping carries no id.** It is a `KeyMidi` element INSIDE the
  target parameter, encoding a virtual MIDI CC on channel 16 where the CC
  number is the macro index. The target is named by containment. So a
  cloned chain keeps working with no remapping, and deleting a parameter
  deletes its mapping.
- **A device loads with every parameter removed.** Live fills defaults.
  Donors are for FIDELITY, not loadability: they carry configured values
  and tell you what a device can be asked to do.
- **Sample metadata is advisory.** Live re-reads the file on load, so
  retargeting a sample needs only the two path fields on each of its two
  FileRefs. `OriginalCrc` is never validated and never needs computing.
- **`MacroDefaults` lags one save**, as do `PresetRef` and `UserName`.
  Write `-1` and ignore it.
- **The UI says Variations, the XML says Snapshots.** Grepping the UI word
  finds nothing.

## Scratch work goes in `build/`

Anything exploratory - a probe file, an unpacked `.xml`, a deliberately
broken rack you are testing a failure mode with - goes in `build/`, which
is gitignored.

`racks/` is NOT scratch. Those files are the evidence behind every
verified claim in `doc/ARCHITECTURE.md`, and the tests read them. Deleting
one destroys a finding.

A probe that answered its question is deleted once the answer is written
down. The finding has value; the scaffolding that produced it is noise.

## Commit messages

**Commit messages are not for literature. For that we have the markdown.**

ONE LINE. `type: what changed`, stated plainly. No body.

    feat: compile specs into rack presets
    fix: index children of homogeneous plural containers
    docs: record the id uniqueness rule
    test: spike evidence for drum rack sends

The subject STATES, it does not argue. Everything you were about to put in
a body already has a home: the constraint goes in a comment at that line,
the evidence in `doc/SCHEMA.md`, the model in `doc/ARCHITECTURE.md`, the
remaining work in `doc/SPIKES.md`.

## Fail loudly

A corrupt `.adg` that Live silently half-loads is worse than one it
rejects. Where we can know in advance, we refuse to write the file.
`clone.assert_loadable()` is the pattern: raise with the offending
container named, do not warn and continue.
