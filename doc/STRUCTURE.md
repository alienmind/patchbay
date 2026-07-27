# A mature Push template, reconstructed

Reference notes on how PLAYGRND lays out its controls, assembled from
publicly available material about the template. Treat every line as an
EDUCATED GUESS rather than documentation: nothing here comes from the
vendor, and nothing has been checked against a file.

It exists to inform the design decisions in `PATCHBAYGROUND.md`. What is
worth taking is the SHAPE: how deep the nesting goes, which slots change
meaning at which level, and where sends live.

## The two rows on Push

Push shows the device chain on the top line and the selected device's eight
macros beneath it. The two rows share columns but are independent, which is
the easiest thing to misread.

## Drum track: six levels

    MFX_DR  >  DR1  >  <PAD>  >  <PAD>n WRKS  >  <sound>  >  EQC_DR1

| Level | Holds |
|---|---|
| 1 | MIDI effect, kit wide |
| 2 | The drum rack itself |
| 3 | Pad rack, one per pad |
| 4 | A "workshop" rack inside the pad |
| 5 | The sound that actually plays |
| 6 | Channel EQ and compression |

Level 4 has no counterpart in our model. Every pad carries a rack named for
the pad plus `WRKS`, sitting between the pad and its sound.

### Pads, workshops and sounds

| Pad rack | Workshop | Sound |
|---|---|---|
| `Kick` | `KDR1 WRKS` | `Kick 1` |
| `Snare` | `SNR1 WRKS` | `Snares` |
| `Tom` | `TOM1 WRKS` | `Long Tom` |
| `Claps` | `CLP1 WRKS` | `Claps` |
| `HH Open` | `HHO1 WRKS` | `HH Open` |
| `HH Closed` | `HHC1 WRKS` | `HH Closed` |

Level 5 names a FAMILY MEMBER, not a file. Sweeping `SOUND` walks the
family.

**Open and closed hats are separate pads**, each with its own workshop and
its own `SOUND` knob. So `SOUND` walks a family of closed hats, or a family
of open hats, and does not morph one into the other. Worth stating because
the opposite is the natural assumption.

Pad racks appear colour coded on Push, which suggests colour is assigned
per pad rather than inherited from the kit.

### The same eight slots change meaning with depth

Slots 1-4, 7 and 8 hold at every level. Slots 5 and 6 are where the level
shows through.

| Slot | Workshop selected | Sound selected |
|---|---|---|
| 1 | `SOUND` | `SOUND` |
| 2 | `PITCH` | `PITCH` |
| 3 | `FILTER & ENV.` or `FILTER` | same |
| 4 | `DRIVE & SNAP` or `DRIVE` | same |
| 5 | `SEND A` | `FM Ø / TYPE` |
| 6 | `SEND B` | `FM AMOUNT` |
| 7 | `DECAY` | `DECAY` |
| 8 | `VOLUME` | `VOLUME` |

Sends are reachable at the workshop level; FM one level deeper. The same
pattern appears on the kick, tom, closed hat and claps.

**Slot names vary by pad.** The kick reads `FILTER & ENV.` and `DRIVE &
SNAP`; hats, snare and claps read plain `FILTER` and `DRIVE`. So the
grammar is positional and each pad labels its own slots for what they
actually drive. A kick gets snap; a hat does not.

### Units seen

`SOUND` reads as a small integer, `PITCH` in semitones, `VOLUME` in dB,
`DECAY` and the filter and drive slots as bare 0..127. `FM AMOUNT` reads in
dB and sits at negative infinity when off; `FM Ø / TYPE` is a bare integer.

## Returns

Four, named for character rather than device:

    A-Rvb:Short    B-Dly:Short    C-Rvb:Space    D-Dly:Shift

Two reverbs and two delays. Instrument tracks appear to reach only the
first two.

## Instrument racks

Eight macros each. Slots 1, 2, 7 and 8 are stable across racks; 3 to 6 are
where a rack spends its character.

| # | BS1 | PD1 | SR1 |
|---|---|---|---|
| 1 | `INST.` | `INST.` | `SAMPLE` |
| 2 | `SOUND` | `SOUND` | `START POINT` |
| 3 | `FILTER & RES.` | `FILTER & RES` | `FILTER` |
| 4 | `DRIVE & F.ENV.` | `DRIVE & F.ENV.` | `PITCH` |
| 5 | `LFO` | `LFO \| RAN.SND.` | `LOOP LENGTH` |
| 6 | `SATURATION` | `ATTACK` | `ATTACK` |
| 7 | `RELEASE` | `RELEASE` | `RELEASE` |
| 8 | `VOLUME` | `VOLUME` | `VOLUME` |

Three observations worth carrying into our own design.

**Slots 3 and 4 each drive two parameters.** `FILTER & RES.` and `DRIVE &
F.ENV.` are one knob apiece. That is how eight slots cover a synth with
more than eight things worth reaching, and it is the alternative to
spending a slot on resonance alone.

**PD1 spends slot 6 on `ATTACK`**, where BS1 spends it on `SATURATION`. A
pad needs an attack knob and a bass does not. This is the clearest evidence
that slot 6 is a genuine per-rack wildcard rather than a fixed control.

**PD1's slot 5 pairs an LFO with a random-sound function**, so one knob
both modulates and re-rolls the sound selector. That is the only slot that
appears to reach back into slot 2's territory.

**SR1 is the deliberate exception.** A sampler has no instrument axis, so
slots 1 and 2 become the sample and its start point, and 3 to 6 become
filter, pitch, loop length and attack. Same shape, different content.

Release displays in milliseconds below one second and in seconds above it,
so the unit switches with magnitude. Both are consistent with the stored
value being seconds. See Q13 in `SCHEMA.md`.

## ARP1

A device at the head of the channel strip, not a track.

| # | Name |
|---|---|
| 1 | `Ø /STYLE` |
| 2 | `MAIN RATE` |
| 3 | `RETRIGGER` |
| 4 | `RANDOM NOTES` |
| 5 | `JITTER RATE` |
| 6 | `TRANSP. STEPS` |
| 7 | `GATES` |
| 8 | `VEL. RANDOM` |

`Ø` prefixes slot 1 on every rack that has something to select between, so
it appears to mark the selector slot.

## The channel strip

    ARP1   MFX1   <instrument>   EQC_<track>   AFX1   AFX SEL1   Channel EQ   VOL1

The instrument sits third, after two MIDI effects. `Channel EQ` is Live's
stock device under its stock name; the rest are custom racks. Each strip
instance is named for its track, `EQC_BS1` on the bass and `EQC_PD1` on the
pads.

## What this suggests for us

Three things worth arguing about in `PATCHBAYGROUND.md`, none decided:

1. **A level between pad and sound.** Our DR1 sketch is pad rack, engine
   rack, devices. This is pad rack, workshop rack, sound. Whether the
   workshop earns its own level or is a naming convention on the engine
   rack we already have cannot be settled from the outside.
2. **Slots 5 and 6 change meaning with depth.** Sends at one level, FM one
   level deeper, same knobs. Our grammar fixes a slot's meaning across a
   whole rack. This does not.
3. **Two parameters per knob on slots 3 and 4.** We currently spend slot 3
   on cutoff alone and push resonance to the wildcard. Pairing them frees
   slot 6 for something a rack actually needs.

## Confidence

Everything above is reconstruction. It is consistent, it is detailed, and
it could still be wrong in specifics: names may be abbreviated by the
display, values are read at one instant, and nothing states what a control
is wired to underneath. Nothing here should be treated as verified, and
nothing in `patchbay` should depend on it without a diff of our own.
