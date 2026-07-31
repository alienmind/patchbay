# The Live API boundary

**Nothing in this toolchain drives a running Live.** No module under
`patchbay/` imports the `ableton-mcp` submodule, no build touches it, and
no test needs it. The plan that did is buried in `THE_BASEMENT.md`.

This file stays because the capability table below is EVIDENCE, and it is
the reason the project writes files at all: it is what established that
racks, macro mappings and chain zones are unreachable from the API. Read it
as a boundary, not as a division of labour.

Evidence is Live 12.4.3's own bundled scripts at
`Resources/MIDI Remote Scripts`, in particular `_MxDCore/LomTypes.pyc`,
which enumerates the Live Object Model. Symbol present in that table means
the API exposes it; absent means it does not exist, not that we failed to
find it.

## The premise holds: racks are not scriptable

`CLAUDE.md` and `KICKOFF.md` assert that Live's API cannot group devices
into a rack, create a macro mapping, or set a chain zone, and that file
generation is therefore the only route. **Confirmed.**

| operation | LOM | consequence |
|---|---|---|
| `map_parameter`, `macro_mapping`, `mapped_parameter`, `mappings` | **absent** | macro mappings cannot be created or read via the API |
| `add_chain`, `delete_chain` | **absent** | chains cannot be created or removed |
| `zone` | **absent** | chain/key/velocity zones are not reachable |
| `chains`, `return_chains`, `drum_pads`, `chain_selector` | present | existing structure is *readable*, not constructible |
| `add_macro`, `remove_macro` | present | changes the macro *count* only - `NumVisibleMacroControls` |
| `randomize_macros`, `selected_variation_index`, `store_variation` | present | variations can be stored and selected, but not named |

So `patchbay` has a real job that nothing else does: **rack structure, macro
mappings, chain zones and variations, at the file level.** That is the core
of Phases 1-5 and none of it is duplicated work.

## But Phase 6 largely is duplicated work

`KICKOFF.md` Phase 6 proposes emitting a whole `.als`: tracks, routing,
returns, sidechain, tempo, clips. Most of that **is** in the Live API:

| operation | LOM | in the submodule's remote script? |
|---|---|---|
| `create_midi_track` | present | **yes** |
| `create_audio_track` | present | no |
| `create_return_track` | present | no |
| `delete_track`, `duplicate_track` | present | no |
| `output_routing_type` / `_channel` | present | no |
| `input_routing_type`, `available_output_routing_types` | present | no |
| set tempo, name tracks | present | **yes** |
| create clips, add notes | present | **yes** |
| load a device or preset by browser URI | present | **yes** |

**The remote script is the limiting factor, not the Live API.** Everything
Phase 6 needs for tracks and routing exists in the LOM and is simply not
wired up in `AbletonMCP_Remote_Script/__init__.py` yet.

Adding `create_audio_track`, `create_return_track` and an output-routing
setter is a handful of command handlers in a file that already has twenty.
That is a much smaller and far less fragile job than generating `.als`
XML, which would mean reverse-engineering Set structure and re-doing it
after every Live update.

### The exception: sidechain

`sidechain` and `side_chain` are **absent** from the LOM. A compressor's
sidechain source cannot be set from the API.

`PATCHBAYGROUND.md` wants DR1 sidechaining into other tracks, so that stays
either manual - one afternoon, per `KICKOFF.md`'s own fallback - or is
done at the file level later if it proves worth it. It is one setting per
track, not a system.

## What the browser costs, and why the Set is a file after all

**A device can only be loaded onto a track BY BROWSER URI**, and Live's
browser index is a snapshot taken at startup. A rack written to the User
Library while Live is running is not in it, and neither is a file dropped
into a folder Live has already indexed - checked against a running 12.4.3
by polling for a file that never appeared, so it is the index rather than
the folder.

That is fatal for the one job this division of labour gave the API. A
toolchain that generates racks cannot ask a running Live to place them
without restarting the Live it is driving.

So `patchbay session` writes the `.als`: tracks, returns, tempo, and every
rack placed. Q30 has what Set form cost to write, and the templates for it
come from Live's own factory Sets rather than from this repo. What stays
manual is what no factory Set has an example of: routing a track into
another track, and the sidechain source.

## Division of labour

**`patchbay` - files.** Racks, macro mappings, chain zones, sample
retargeting, variations, AND the Set: tracks, returns, tempo, every rack
placed. Everything the API cannot express, which turned out to include
placing a generated rack at all.

**`ableton-mcp` - the live session.** Reading back what is actually on a
track, transport, tempo, clips and notes, creating tracks. What it cannot
do is load a rack this toolchain just wrote, for the browser reason above.

**Do not migrate MCP code into `patchbay`.** They have different runtime
models - one writes files offline, the other holds a socket to a running
Live. Merging them would put a network dependency inside a library whose
whole value is working without Live open.

## Verification harness

**The smoke test as designed does not run.** It was: generate a rack, have
MCP load it onto a track, read the device tree back with `get_track_info`.
Step two is the browser step, and the browser cannot see a file written
after Live started.

What remains usable: `get_track_info` against a Set opened by hand reads
back what Live made of a file, which is a real check and needs no dragging
once the Set is open. It still cannot confirm a macro mapping -
`mapped_parameter` does not exist in the LOM - so that stays ears and eyes,
exactly as `KICKOFF.md` said.

## Where this leaves the submodule

- **S11 and Phase 6 as written are dropped, and Set structure WAS mapped
  after all.** Q9 read it, Q30 and Q31 wrote it, `live_set.py` is the
  module, and the shapes are templates read from Live's factory content
  rather than reverse-engineered from nothing.
- **The remote script additions in `mcp/remote_script_additions.py` are no
  longer on the critical path.** `create_audio_track` and
  `create_return_track` were wanted so MCP could build the Set; the Set is
  a file now. They stay written down because reading a running Live is
  still worth having.
- **Sidechain and track-to-track routing stay manual** until a Set carrying
  one exists to diff. Neither is in the LOM, and neither appears in any of
  Live's 26 factory Sets.
- **Phase 5 stays file-level.** `store_variation` exists, but variations
  cannot be *named* through the API, and generated names encoding their own
  parameter values are what make culling informed rather than blind.
