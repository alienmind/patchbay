# The Live API boundary, and what AbletonMCP is for

`ableton-mcp` is a submodule: a Live remote script plus an MCP server that
drives Live over a socket. This document records what Live's API can and
cannot do, so the two layers stay in their lanes and we do not rebuild
something that already works.

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
retargeting, variations. Everything the API cannot express. Produces
`.adg` files dropped into the User Library.

**`ableton-mcp` - the live session.** Tracks, naming, routing, tempo,
clips, loading presets by URI, reading back what is actually there.
Everything the API can express.

They meet at the User Library: `patchbay` writes a rack, `ableton-mcp` loads
it onto a track by browser URI.

**Do not migrate MCP code into `patchbay`.** They have different runtime
models - one writes files offline, the other holds a socket to a running
Live. Merging them would put a network dependency inside a library whose
whole value is working without Live open. Keep the submodule, extend its
remote script.

## Verification harness

`KICKOFF.md` anticipated this and it is now concrete. `get_track_info`
returns the devices present on a track, and `load_instrument_or_effect`
loads a preset by browser URI. Together they give a smoke test:

1. `patchbay` generates a rack
2. MCP loads it onto a track
3. `get_track_info` confirms the expected device tree appeared

That catches gross failures without a human dragging files. It **cannot**
confirm macros are mapped correctly - `mapped_parameter` does not exist -
so that check stays manual, exactly as `KICKOFF.md` says.

## Revised plan

- **S11 and Phase 6 as written are dropped.** Do not reverse-engineer
  `.als` structure. The `sets/` folder and its spike are unnecessary.
- **New Phase 6:** extend the remote script with audio/return track
  creation and output routing. Smaller, and immune to schema drift.
- **Sidechain stays manual** until proven annoying.
- **Phase 5 stays file-level.** `store_variation` exists, but variations
  cannot be *named* through the API, and generated names encoding their own
  parameter values are what make culling informed rather than blind.
