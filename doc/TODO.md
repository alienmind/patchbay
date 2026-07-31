# TODO - the live backlog

The only place that says what is unfinished. Everything else in `doc/` is
settled knowledge. Live version for every item below: **12.4.3**.

## The backlog

In order. Nothing here blocks anything else, so the order is by what it
costs against what it decides.

| # | What | Who | Cost | Decides |
|---|---|---|---|---|
| 1 | Classify samples by what they SOUND like, not what they are called | me | a dependency and a spike | Whether curation stops being manual |
| 2 | Duck from DR1's KICK CHAIN, not the whole track | you, one save | one Set saved by hand | Whether a sidechain can name a chain inside a rack |
| 3 | Colour a rack's CHAINS and a clip | me | small, one diff first | Whether colour reaches inside a rack, not just the track list |
| 4 | Write a `.alp` as well as a `.als` | me | unknown, format undocumented | Whether a build ships as one installable file instead of a folder |
| 5 | Re-run the donor name scan after a Live update | me | minutes | Nothing today. It is the check that catches a rename before a spec does |

## 1. Classifying by sound

We currently have a basic classification algorithm for samples based on file names `examples/patchbaygrnd_fetch_samples.py`,
which sorts a drop folder. But this is not enough to properly cluster the samples as we want them to be:

### Enhancements

Based on some of the exmaples used:

| case | example in the drop | what would settle it |
|---|---|---|
| one-shot or bar | `WHAEVER_KIT_5_BASS_126_Gm_7`, a tempo and a key and no `loop` | LENGTH against the tempo |
| near duplicates | five packs each ship a 909 clap | spectral distance, not a content hash |
| is it usable | anything | nothing automatic. Ears |

The content hash in place today catches a pack copied in twice. It does not
catch the same 909 clap sampled by two vendors, which is the duplicate that
actually fills a pad with eight versions of one sound.

### The shape it plugs into

The classifier is already a PIPELINE of stages, tried in order, first
verdict wins. Two exist, `NameStage` and `FolderStage`, and each returns a
`Verdict` carrying which stage decided and on what evidence. **A third
stage is an append to `PIPELINE` and changes nothing above it.** That is
why the refactor happened before the feature.

    PIPELINE = (NameStage(RULES), FolderStage(RULES), AudioStage(...))

`AudioStage` runs last on purpose. It is the only stage that must open the
file, so it costs a decode per sample where the others cost a regex, and it
should only ever see what the cheap stages could not answer.

### The features worth having, cheapest first

| feature | says | rough cost |
|---|---|---|
| duration | one-shot or bar. Against a tempo in the name, how many bars | header only, no decode |
| peak and RMS | how hard it hits, and gain staging across a pad | one pass |
| attack time | transient. Separates a kick from a sub, a rim from a snare | one pass |
| spectral centroid | dark or bright. Orders a pad's chains by tone | FFT |
| fundamental pitch | tuned or not. A kick's note, a tom's | FFT plus autocorrelation |
| MFCC distance | near duplicates, and clustering a pack into families | FFT plus a library |

**Duration alone settles the biggest open case** and needs no decode: a
`.wav` header carries sample rate and frame count. Do that one first and
alone, because it turns `BASS_126_Gm` from a guess into an answer, and
because it can ship with no new dependency.

### The dependency question, which is the real decision

Everything past duration wants FFT. `numpy` alone does the first four.
`librosa` does all of them and drags in `scipy`, `numba` and a compile
step.

This project currently depends on `lxml` and nothing else, which is why a
clone builds in seconds. **Adding `numpy` for duration and attack is a
different decision from adding `librosa` for MFCCs**, and they should not
be made together. Ship duration on the standard library, then decide.

### What it must not become

Sorting into folders is reversible and the log makes it so. **Anything that
DISCARDS a sample on a machine's judgement is not.** So a near-duplicate
finding reports and never deletes, and "is it good" stays under Standing
manual work where it already is. The tool narrows what a person listens to;
it does not decide.

## 2. Ducking from the kick chain

Every EQC but DR1's sidechains from **the whole DR1 track**, which triggers
on hats and claps as much as on kicks. Musically that is wrong: only the
low kick should duck a bass.

**Half of this is already solved and shipped.** `EQC` sets
`SideChainEq_On`, mode 5, at `SIDECHAIN_HZ = 100.0`, so the trigger is a
low band of DR1 rather than all of DR1. Live's own manual prescribes
exactly that for this case: "even if you only have a mixed drum track to
work with... enable the sidechain EQ and select the low-pass filter... you
should be able to isolate the kick drum from the rest of the drum mix."

**What is NOT known is whether a routing target can name a CHAIN.** The
manual says the chooser offers "any of Live's internal routing points", and
a Drum Rack's pads are routing points in the UI. Q33 established the shape
for a track, `AudioIn/Track.<id>/PostFxOut`, and says nothing about a chain
inside one. Writing a guess is rule 1.

**One save answers it.** In any Set, put a Compressor on one track, turn its
sidechain on, and set the source to a single PAD of a Drum Rack on another
track. Save it as `racks/q41_chain_source.als`. The diff against Q33's
target is the whole finding, and if a chain can be named then `sidechain=`
takes a chain as readily as a track.

**Until then the low band stands**, and it is not a placeholder: it is the
technique the manual recommends and it is already in every EQC.

## 3. Colour inside a rack

**Tracks and returns are done**, Q39: `<Color Value="N" />`, 0 to 69, `-1`
for none, written by `live_set._color_track` and spread evenly across the
palette by `examples/patchbayground.py`.

What is left is the same element one level in. A Set-form `*Branch` carries
`Color`, so a rack's chains can be coloured, and so can a clip. **One diff
first**, because a branch also carries `AutoColored` and `AutoColorScheme`
and a track does not: save a rack with a hand-coloured chain, and see
whether `Color` survives with `AutoColored` still true, or whether Live
flips it. That is a five minute spike and it decides whether the DSL sets
one field or two.

The open shape question is the DSL surface, not the format. A palette index
is honest and unreadable; sixty-nine names are readable and are sixty-nine
names to invent and defend.

## 4. A `.alp` as a second output

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
Samples used for this experiment cannot be redistributed, but at least we should
provide a way to build a pack for any user willing to build it from their
sample collection.

## 5. The donor name scan

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
