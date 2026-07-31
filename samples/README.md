# Samples

Curation is manual, wiring is automatic. This folder is the interface
between the two: put a file in the right folder and the next build picks it
up. Nothing tells a spec what is here. It asks.

**Nothing in this folder is committed except this file.** Not audio, not a
licence, not a manifest listing filenames. Sample content is licensed and a
public repo is redistribution. `.gitignore` pins it with `samples/*` and
`!samples/README.md`; see `CLAUDE.md`.

So this file describes the tree in counts and folder names. It does not
enumerate it and it does not name its sources.

## The contract

**One folder per rack, named exactly as the rack is.** A rack that wants
samples looks in `samples/<RACK>/` and nowhere else. Two racks never
negotiate over a folder, and a folder no rack is named for is never read.

```
samples/
  all/        DROP ANYTHING HERE. Never read by a build
  DR1/        one subfolder per pad category
    kick/     rim/      snare/    clap/
    perc/     hat/      tom/      ohat/
  SR1/        flat, no categories
  cymbals/    unclaimed
  loops/      unclaimed, tempo locked
  manifests/  the move log, never read by a build
```

**A rack with categories has one subfolder per category. A flat rack has
none.** DR1 is a drum rack, so a category is a pad and a pad is a MIDI
note. SR1 walks one list, so its files sit directly in `SR1/`.

## What is fixed and what is not

| | fixed by | to change it |
|---|---|---|
| which racks have folders | the rack's name | add a folder named for the rack |
| DR1's eight categories | one MIDI note each, laid out on the Push grid | edit `PADS` in `examples/patchbayground.py` |
| how many files in a category | nothing | drop a file in, rebuild |

**Eight categories is the fixed part. What is inside one is not.** Adding a
file to `DR1/snare/` adds a chain to the snare pad on the next build, and
nothing has to be told. That is the drum rack's whole shape, and it is why
no sample count appears in the spec.

Renaming a category folder is one edit to `PADS`, because a pad note is a
musical decision rather than something to infer from a folder name.

## Naming

**Sorted by the whole filename, case insensitively.** Both of these order
the way they read, so either convention is fine:

    NNN_name.wav        numbered at the front
    name_NNN.wav        numbered at the back

Do not mix the two inside one folder.

**Number from the first free index and never renumber.** Chain order is
sort order, so inserting a file ahead of the others shifts every chain
after it, and one knob position then lands on different audio. Appending
never does that.

`.wav`, `.aif`, `.aiff` and `.flac` are discovered. Anything else in a
folder, `.asd` analysis files included, is ignored.

## Current counts

    DR1/      307 over eight categories
    SR1/        6
    cymbals/   47 over two, unclaimed
    loops/     40 over two, unclaimed

Counts change as the collection does. Ask the filesystem, not this file.

## How the tree is built

    python examples/reorg_samples.py            # say what would happen
    python examples/reorg_samples.py --apply    # do it

Drop a pack into `samples/all/` in whatever shape it arrived in. The script
COPIES each file into the folder its name says it belongs in, renamed
`<category>_NNN` continuing from the first free index. Nothing is moved and
nothing is deleted, so `all/` is still intact afterwards and a wrong
classification costs a re-run. Delete `all/` yourself when satisfied.

Sorting is by FILENAME TOKEN rather than by the folder a file arrived in,
so the classification is checkable rather than trusted. The rules are an
ordered list in the script and the first match wins:

- **a loop outranks everything**, so `kick_loop_120bpm` is a loop and not a
  kick. It is bar length and tempo locked, and a pad holding one is
  unplayable.
- **specific before general**: `ohat` before `hat`, `clap` and `rim` before
  `snare`, `crash` and `ride` before the `cy` abbreviation.
- **abbreviations match at word boundaries only**, so `bd` is a kick in
  `bd_04` and nothing in `abdomen`.

A file whose name says nothing is left in `all/` and counted as
UNCLASSIFIED. Rename it so the sound is in the name, or add a pattern.
Exact duplicates of audio already in the destination are skipped by content
hash; two takes that merely sound alike are not, and that is a listening
decision rather than a script's.

`manifests/` holds the move log as `from,to,date`. It is the only record of
the original names, it makes a reorganisation reversible, and it stays on
this machine.

Live's `.asd` analysis files are discarded on a reorganisation. They are a
cache keyed to a filename that no longer exists, and Live rebuilds them on
load.

Licence terms that arrive with a pack are kept in this folder, untracked,
because the directory they arrived in does not survive sorting.

## Unclaimed folders

`cymbals/` and `loops/` are raw material no rack reads. That is not an
oversight and nothing is broken: discovery only ever looks inside
`samples/<RACK>/`, so a folder no rack is named for costs nothing. Give one
to a rack by moving it under that rack's folder.
