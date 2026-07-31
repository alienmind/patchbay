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
    kick/     tom/      snare/    hat/
    rim/      misc/     clap/     ohat/
  SR1/        flat, no categories
  manifests/  the move log, never read by a build
```

**There are no other folders, and that is the rule.** A build reads
`samples/<RACK>/` and nothing else, so a folder no rack is named for is a
folder nothing opens. `cymbals/` and `loops/` used to exist and were
exactly that: write-only. Cymbals now go to the `misc` pad, which is the
pad that plays one, and loops go nowhere at all.

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
    all/     1419 waiting to be sorted

Counts change as the collection does. Ask the filesystem, not this file.

## How the tree is built

    python examples/patchbaygrnd_fetch_samples.py            # say what would happen
    python examples/patchbaygrnd_fetch_samples.py --explain  # and why, per file
    python examples/patchbaygrnd_fetch_samples.py --apply    # do it

Drop a pack into `samples/all/` in whatever shape it arrived in. The script
COPIES each file into the folder its name says it belongs in, renamed
`<category>_NNN` continuing from the first free index. Nothing is moved and
nothing is deleted, so `all/` is still intact afterwards and a wrong
classification costs a re-run. Delete `all/` yourself when satisfied.

Classification is a pipeline of STAGES, tried in order, first verdict
wins. `--explain` prints which stage decided each file and on what, so
every placement is answerable:

1. **a folder that says LOOP**, before anything about what the sound is.
   `loops/kick/kick_001.wav` is a bar of kick, and reading the filename
   first would put it on the kick pad where it is unplayable.
2. **the filename**, which is what survives a pack being copied around.
3. **the enclosing folders**, as a fallback for packs that number their
   files and put the sound in the folder.

Why two folder stages rather than one: FORM outranks sound, but only the
unambiguous tokens are safe to read off a folder. A kit folder called
`Kit 01 G# 126 BPM` holds one-shots, so a tempo in a FOLDER name describes
the kit and not the file, and the `bpm` pattern is filename-only.

Within a stage the rules are one ordered list and the first match wins:

- **a loop outranks everything**, so `kick_loop_120bpm` is a loop and not a
  kick. It is bar length and tempo locked, and a pad holding one is
  unplayable.
- **specific before general**: `ohat` before `hat`, `clap` and `rim` before
  `snare`, `crash` and `ride` before the `cy` abbreviation.
- **an unknown hat is a CLOSED hat.** `ohat` needs `open hat`, `oh hat` or
  `ohh` spelled out. Bare `oh` is not a rule: it matched one file in 1332
  and that file was a vocal.
- **abbreviations match at word boundaries only**, so `bd` is a kick in
  `bd_04` and nothing in `abdomen`.

The rules were derived from 1332 files across ten commercial packs, by
token frequency and then by checking what each rule caught. They place
1331 of them.

**A loop is recognised and then left alone.** No rack plays one: a pad is a
one-shot and SR1 walks one-shots too. Recognising them is what keeps 311
bar-length files out of the pads; giving them a folder would only be a
folder nothing reads.

A file whose name and folder both say nothing is left in `all/` and counted
as UNCLASSIFIED. Rename it so the sound is in the name, or add a pattern.
Exact duplicates of audio already in the destination are skipped by content
hash; two takes that merely sound alike are not, and that is a listening
decision rather than a script's. `doc/TODO.md` has the design for a third
stage that would hear the difference.

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
