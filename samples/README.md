# Samples

Manifests mapping sample files to pads and chains. Curation is manual,
wiring is automatic. This folder is the interface between the two.

**Nothing in this folder is committed except this file.** Not audio, not a
licence, not a manifest listing filenames. Sample content is licensed and a
public repo is redistribution. `.gitignore` pins it with `samples/*` and
`!samples/README.md`; see `CLAUDE.md`.

So this file describes the tree in counts and folder names. It does not
enumerate it and it does not name its sources.

## Layout

One folder per sound, named for the sound rather than for where it came
from. A spec addresses `samples/drums/kick/kick_004.wav` and never a
vendor's directory tree.

```
drums/    kick  snare  clap  hat  ohat  tom  perc  rim
cymbals/  crash  ride
loops/    kick  rumble          tempo locked, not pad material
fx/       vox  hit
```

Files are `<sound>_NNN.wav`, numbered from 1 in sorted order. Counts vary
as the collection changes; ask the filesystem, not this file.

## How the tree is built

Sources arrive in whatever shape they were packaged in, which is not
addressable from a spec. Sorting is by FILENAME TOKEN rather than by the
folder a file arrived in, so the classification is checkable rather than
trusted.

`manifests/` holds the move log as `from,to`. It is the only record of the
original names, it makes a reorganisation reversible, and it stays on this
machine.

Live's `.asd` analysis files are discarded on a reorganisation. They are a
cache keyed to a filename that no longer exists, and Live rebuilds them on
load.

Licence terms that arrive with a pack are kept in this folder, untracked,
because the directory they arrived in does not survive sorting.

## Adding to it

Drop files into the folder for their sound, then normalise the names:
sorted case insensitively, numbered from the first free index, and appended
to the move log. Existing numbers do not shift, so a path already written
into a spec keeps pointing at the same audio.

Every sound has enough files for a pad to select across. The one that did
not, `rim/`, has since been filled.
