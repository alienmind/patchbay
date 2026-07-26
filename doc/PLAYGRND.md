# PLAYGRND, read off the videos

What Andri Soren's Live Set actually does, transcribed from two YouTube
videos: "The Push PLAYGRND Story" (kpgGy1axuaU) and "Push PLAYGRND: Music
Making Session" (n-I8hn9B6nw).

The Set is a paid product and we do not have the file. Everything here is
OBSERVED on screen or STATED on the recording. Nothing is derived from the
`.als`. `doc/PATCHBAYGROUND.md` is our own reconstruction of the same
architecture; this file is the evidence it was reconstructed from, kept
separate so the two never blur.

Marked **[obs]** for shown or said, **[inf]** for our reading of it.

## Track names

Confirmed by ear or on screen in the session video:

| Name | Role |
|---|---|
| DR1 | Drum rack |
| BS1 | Bass |
| LD1 | Lead, played with polyphonic aftertouch |
| ARP1 | Arpeggiated line |
| VA1 | "VA for various" **[obs]**, said explicitly at 24:25 |
| AFX1, AFX S1 | Audio effect returns |

Pads are addressed as "pad one" rather than PD1 in the video. **[inf]** the
same two letter plus digit scheme.

Our eight track table in `PATCHBAYGROUND.md` matches this on DR1, BS1, LD1
and VA1, and was written before the transcript. ARP1 and the AFX prefix are
new information.

## The controls, one at a time

### Sound select is one continuous index

**[obs]** Sounds are chosen by NUMBER while the clip keeps playing, without
opening the browser: "I usually have to go into browse and swap out things,
but here we can just use the macros to browse a whole bunch of sounds."
Numbers seen: 24, 124, 126, 128, 488.

**[obs]** Sweeping that one knob crosses categories in place: percussive
sounds, then "bass sounds, not so useful", then "lead sounds". Contiguous
regions of a single index, not separate selectors.

**[inf]** This is the Engine plus Variation split we already argue for. One
index over hundreds of entries, ordered so neighbours are related and
regions are categories. 488 exists, so the space is at least ~500 wide on
DR1's host rack alone.

**[obs]** Swapping the sound leaves the clip, the notes and the effect
sends untouched. Playing the same MIDI through index 124, 126, 128 and 488
back to back is the whole demonstrated workflow.

### Filter, twice over

**[obs]** The drum rack has a global filter macro AND every pad has its own
filter: "the drum rack itself has got a filter, every single pad within it
also has filters, so we'll just take the global one for now."

**[inf]** Confirms macro to macro chaining down the nest rather than one
filter per level competing.

### Filter position is physical

**[obs]** "The way Push works is that it will always want to default back
to the position you moved it physically." He exploits this: park the knob
low at the start of a clip and the drop is free, no automation recorded.

**[inf]** Macro defaults matter for performance, not just for recall. Ties
to the `MacroDefaults` lag noted in `CLAUDE.md`.

### Drive

**[obs]** Present on the instrument channels ("some drive there as well",
"the drive is still up here") and separately reachable on AFX1 as extra
saturation ("can also use afx1 to see if I can pull out some extra
saturation"). Applied to bass, pads and lead in the same session.

### Channel EQ

**[obs]** A Channel EQ on the bass, low end already boosted at the cost of
the highs, adjusted live. Stock Channel EQ, not EQ Eight. **[inf]** part of
a standard channel strip on every track.

### Velocity range

**[obs]** "I have a bit too much velocity range for this bass line, I'm
just going to pull that down", because the third note was too quiet.
A knob, adjusted while playing, not a clip edit.

**[inf]** Velocity to volume depth is a macro on the instrument rack.
Nothing in our grammar covers it.

### Aftertouch

**[obs]** "You have aftertouch in all of the instruments in PLAYGRND", and
on LD1 it moves pitch and filter together.

Matches the aftertouch line already in `PATCHBAYGROUND.md`. Still blocked
for us on SPIKES Q2.

### Sends: reverb and delay, several of each

**[obs]** At least three distinct return destinations, picked by knob:
a long reverb, a shorter reverb "with a bit more wet mix", and a delay.
He hits the wrong one by accident at 18:32: "now we're on a delay, I've
accidentally instead chosen a delay instead of a reverb, it works better I
think."

**[inf]** Reverb and delay sends sit adjacent on the same Push page. Our
grammar has Space at slot 7 and Delay at slot 11, on different pages. The
accident is only possible if they are neighbours.

**[obs]** Send amount is a knob he rides during the take, and overshoots
twice ("well that's too much, that's too much, just pull that back").

### Release

**[obs]** Pads have a long release: "with a long enough release value this
will just work." Held notes forgive sloppy timing, which he relies on
instead of quantizing.

## Sound qualities

**[obs]** All electronic. Stated outright: no sampled string instruments,
no acoustic sounds, "it's very much an electronic selection of sounds."
Claimed range is techno, house, dance, ambient and cinematic.

**[obs]** PD1 sounds ride on Wavetable: "so Wavetable's time is quite
quite glassy, quite FM", and he can "make it blocky if I want" with one
knob.

**[obs]** DR1 pads are pitched playable instruments, not just kit slots.
He plays a Tom chromatically AS the bassline, tuning it against the other
parts: "checking I've got my tuning right." **[inf]** each pad chain has a
tune macro reaching a pitcher, which is the `MidiPitcher` in our DR1 sketch.

**[obs]** The kick is selected by sound index, not swapped by file: "I
think it should be a nasty nasty kick", then knob.

**[obs]** Sounds are the compositional unit. The entire second video builds
a track without opening the browser once.

## What the videos do NOT show

- No macro NAMES on screen. The eight labels per page are never read out.
- No count of engines per rack, and no rack ever opened in Live's device
  view.
- No return track contents beyond "reverb" and "delay".
- No tempo. He checks it against the metronome rather than knowing it.
- Nothing about how sounds are stored: variations, chains and presets are
  indistinguishable from the outside at this resolution.

The claim in `PATCHBAYGROUND.md` that a sound is a Macro Variation rather
than a chain is therefore still OUR arithmetic from the published 18
engines and ~692 sounds, not something these videos confirm.

## Stated compatibility

Live 10.1.43 Standard and up, Live 11, Live 12, Push 3 standalone. **[obs]**
from the product page, not the videos.

**[inf]** Standalone compatible means no VSTs and stock devices only. Our
target runs tethered, so this constraint is not ours, but it explains why
everything seen is a stock Live device.

## Not about racks

The bulk of the second video is arrangement workflow: capture, loop point
zoom, Session to Arrangement recording with shift plus record, brutal
quantize, clip colouring. None of it touches the Set's structure. Recorded
here only so nobody watches 51 minutes again looking for format evidence.
