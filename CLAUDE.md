# CLAUDE.md - working rules for agents in this repo

This repo is a Python DSL and toolchain for AUTHORING Ableton Live racks
and Sets in code: racks by writing the `.adg` XML directly, Sets by driving
the `ableton-mcp` submodule. A spec is an ordinary Python module importing
from `patchbay.dsl`. Offline authoring, not live coding - nothing here
makes a sound, it produces the instrument.

`examples/patchbayground.py` is ONE example and the end-to-end test. It is
not what the library is for, and per rule 6 the library knows nothing about
it.

Start with `doc/TODO.md` for what to work on, then `doc/ARCHITECTURE.md`
for how the file format works. This file is only the house rules, the
things not derivable from the code.

## The backlog is `doc/TODO.md`

It is the ONLY file that says what is unfinished. Work it, do not work
around it.

1. **Start there.** Take a task, move it to In progress, and keep its
   status current in that file as it moves. A finding that arrives
   mid-task is written down when it arrives, not at the end.
2. **When it lands, DELETE it from `TODO.md`** and materialise what was
   learned in its permanent home:
   - a capability a user would want: `README.md`
   - how the format works: `doc/ARCHITECTURE.md`, evidence in
     `doc/SCHEMA.md`
   - a shape decision about the DSL: `doc/DSL.md`
   - an idea that did not work, an approach abandoned, a theory
     disproved: `doc/THE_BASEMENT.md`
3. **Nothing is archived in place.** No completed entries accumulate in
   `TODO.md`, no struck-through text, no "DONE" markers. A task leaves
   once, in one direction. `KICKOFF.md` is what that looks like when it is
   not done, and it is not a model to copy.

Bury generously. An approach that failed is worth more written down than
deleted, because the next reader will otherwise find it attractive again.
`THE_BASEMENT.md` entries say what was tried, what killed it, and what
replaced it.

`README.md` is for a person deciding whether to use this. Working
procedure, backlog and status are NOT in it.

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

## NEVER COMMIT SAMPLES

Nothing under `samples/` is staged, committed or pushed, except
`samples/README.md`. Not audio. Not a licence file. Not a manifest, a CSV
or an index that merely LISTS the filenames.

Sample content is licensed and a public repo is redistribution. This is not
a tidiness rule.

`.gitignore` pins it with `samples/*` plus `!samples/README.md`, so
`git add -A` cannot sweep them in. Do not add an exception to that pair,
and do not `git add -f` a path under `samples/`.

The same care applies to what tracked files SAY. `samples/README.md`
describes the tree in counts and folder names; it does not enumerate files
and it does not name a source or a vendor. A filename list and a pack name
are both content that folder exists to keep out of the repo.

Before staging anything from a folder that arrived from outside this
project, check what is in it. `git add -A` over a vendor directory is how
a licence file or a file listing gets published, and it is far cheaper to
notice first than to rewrite pushed history after.

## Scratch work goes in `build/`

Anything exploratory - a probe file, an unpacked `.xml`, a deliberately
broken rack you are testing a failure mode with - goes in `build/`, which
is gitignored.

`racks/` is NOT scratch. Those files are the evidence behind every
verified claim in `doc/ARCHITECTURE.md`, and the tests read them. Deleting
one destroys a finding.

A probe that answered its question is deleted once the answer is written
down. The finding has value; the scaffolding that produced it is noise.

## This is an LF repo

Every tracked text file ends its lines with `\n`, on Windows too.
`.gitattributes` pins it and `tests/test_patchbay.py` fails on a stray
`\r`, so do not "fix" a file by letting an editor write CRLF back.

Do not confuse this with the format finding: **Live** writes CRLF inside an
`.adg`, and that stays true. Ableton's files are gzip, marked `binary`, and
git never touches them. A checked-in unpacked `.xml` is marked `-text` for
the same reason - it must stay byte for byte as Live wrote it, or diffing
it against a Live-saved file stops meaning anything.

## Prose

Applies to every markdown file, docstring and comment in this repo.

1. **NO EM-DASHES.** Neither U+2014 nor U+2013. Use a plain hyphen, a
   comma, or a full stop. `tests/test_patchbay.py` fails if either appears
   in a tracked `.md` or `.py` file, so this is enforced, not requested.
2. **State, do not argue.** "Ids must be unique among siblings", not "it
   turns out that, interestingly, ids need to be unique among siblings".
3. **No filler.** Cut "essentially", "basically", "it's worth noting
   that", "in order to", "leverage", "robust", "seamless".
4. **No restating what the code says.** A docstring explains WHY, or the
   constraint that is not visible at the call site. If it paraphrases the
   function name, delete it.
5. **Numbers and file names, not adjectives.** "560 KB, 18,148 facts" is
   worth writing. "A large complex rack" is not.

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
