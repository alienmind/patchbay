# The basement

Where bad ideas are buried. Every entry is something this project tried,
planned or believed, and then stopped: an approach abandoned, a theory
disproved, a spike retired unrun.

It exists so nobody digs the same hole twice. An entry says what was
attempted, what killed it, and what replaced it. Nothing here is a live
question. Live questions are in `TODO.md`.

## Generating `.als` from scratch

**Planned as KICKOFF Phase 6, with spike S11 to reverse-engineer Set
structure.** Dropped before either started.

Live's API *does* expose `create_audio_track`, `create_return_track`,
`output_routing_type` and `output_routing_channel`, verified against Live
12.4.3's own `_MxDCore/LomTypes.pyc`. The `ableton-mcp` remote script had
simply not wired them up.

So Set structure never needed reverse engineering. Adding command handlers
to a remote script is smaller work and survives Live updates, which `.als`
generation would not. The `sets/` folder and its spike were deleted
unbuilt.

**Replaced by:** `TODO.md` T4, `MCP.md`.

## Sidechain source, at any level

Absent from the Live Object Model, and not found in the file format
either. `PATCHBAYGROUND.md` needs it for DR1.

It stays manual. It is one setting per track, priced at one afternoon.
Revisit only if that proves annoying in practice.

## The `OriginalCrc` algorithm

16 bit. zlib plus ten CRC-16 variants over four chunk choices all missed.

Closed as irrelevant rather than solved: S7 showed nothing reads it on
load. Live re-reads the sample file and recomputes its metadata, so a
path-only rewrite works and the CRC never needs computing.

## Id reallocation on clone

Budgeted as the expensive part of Phase 2, gated on spike S6, with a
fallback plan in case cloning turned out unviable.

Both premises were wrong. S3 showed macro mappings carry no ids at all,
they are addressed by containment, so a cloned chain keeps working with a
verbatim copy. S6 then showed the only id rule is uniqueness among
SIBLINGS. Nothing references ids.

`clone.py` copies subtrees and checks sibling uniqueness. There is no
remapping pass, and there never needs to be.

## "A nested rack cannot be lifted out"

The DSL originally scanned `racks/` for a skeleton and would take a
`GroupDevicePreset` from inside another rack's chain. That produced a file
which passed every check the tooling has and which Live refused to accept
as a drop, without ever loading it.

Stated as a structural claim - that Live serialises a nested rack
differently, or records its parent somewhere - it was wrong. The nested
subtree is byte for byte usable. It keeps the `Id` it carried among its
`DevicePresets` siblings, and a top-level `GroupDevicePreset` must have no
attributes at all. One attribute, and the drop is refused.

The guard that accepted only top-level skeletons is gone, replaced by
stripping the `Id`. See S13 in `SCHEMA.md`, and `ARCHITECTURE.md` §3.

**What made it hard to see:** the comparison was between a broken file and
a working one that also differed in what it contained, so the one fact was
buried in hundreds. Building the *same rack twice* and changing only the
skeleton's position reduced it to three facts, two of them cosmetic. When
a diff is too big to read, the fix is a better pair of files, not a
closer reading.

## `PresetRef` as the reason a lifted-out rack was refused

The standing suspect while the above was open. A nested rack's
`AbletonDefaultPresetRef` has `RelativePathType=0` and empty `Path` and
`RelativePath`, while `racks/s1_source.adg`'s top-level drum rack points
at the factory device with `RelativePathType=7`. A tidy theory followed:
Live resolves which device to instantiate from that path when accepting a
drop, and an empty one cannot be resolved.

Dead on inspection. `racks/s3_a.adg` and `racks/s7_a.adg` are top-level
racks Live saved with exactly the empty shape, and `build/PD1.adg` has it
too and was already gated in Live. A never-saved rack simply has nothing
to point at. The `RelativePathType=7` case is a rack still carrying its
factory default, not a requirement.

## The sample cache-key theory

S7 produced an intermediate variant that appeared to fail, which fit a
tidy theory: Live keys its sample cache on size or CRC, so an inconsistent
FileRef would be rejected.

The file had been double-clicked instead of dragged. A second Live
instance hangs for a few seconds and loads nothing, which looks exactly
like rejection. The theory was retracted and the ground rule written down:
drag into a running Live, and check `Log.txt` for `CommandLine` and
`Another instance` before concluding anything.

## Byte comparison of two `.adg` files

Used once as a fidelity check for the round trip. Two semantically
identical files differ by about 4 percent, because Live writes CRLF and
`<X />` and lxml does not.

S1 established that Live tolerates lxml's serialiser conventions, so byte
identity was never the requirement. `patchbay diff` compares the parsed
tree instead, and the noise floor after filtering is zero.

## "A partial device will not load"

The donor pattern was adopted on the assumption that a device node missing
parameters would either fail or load with silent wrong defaults, making
donors mandatory.

S12: a device loads with ALL 18 of its parameters deleted. Live fills in
whatever is absent.

Donors survive for a different reason than the one they were adopted for.
They carry configured values and tell you what a device can be asked to
do, so they are about fidelity, not loadability. Generators may write
partial device nodes.
