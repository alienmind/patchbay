"""Command handlers the vendored remote script is missing.

`doc/MCP.md` establishes that `create_audio_track`, `create_return_track`
and output routing are all in the Live Object Model and simply not wired up
in `ableton-mcp/AbletonMCP_Remote_Script/__init__.py`. This file is those
handlers, written to be pasted in.

## Why this is not an edit to the submodule

`ableton-mcp` is a vendored third party repo pinned at a commit. Editing it
in place moves the parent's submodule pointer to a commit that exists on
nobody's remote, which breaks a fresh `git submodule update --init` for
everyone including future us. So the additions live here, reviewable and
reversible, and are applied by hand.

## Applying

1. Open `ableton-mcp/AbletonMCP_Remote_Script/__init__.py`
2. Paste the four `_`-prefixed methods below into the `AbletonMCP` class,
   next to `_create_midi_track`
3. Paste the DISPATCH block into `main_thread_task`, next to the existing
   `elif command_type == "create_midi_track":`
4. Copy the folder into Live's Remote Scripts directory and restart Live

## Status

**UNVERIFIED.** None of this has run against Live. It is written from the
Object Model names recorded in `doc/MCP.md`, which were read from Live's
own `_MxDCore/LomTypes.pyc` rather than guessed, but reading a name is not
the same as calling it. The routing setters are the least certain part:
`output_routing_type` takes a routing OBJECT chosen from
`available_output_routing_types`, not a string, and the matching below is
by display name, which is the kind of thing that works until a localised
Live says otherwise.
"""

# ---------------------------------------------------------------------------
# Methods for the AbletonMCP class
# ---------------------------------------------------------------------------

METHODS = '''
    def _create_audio_track(self, index):
        """Create an audio track. PM1 needs one; the LOM has always had it."""
        try:
            self._song.create_audio_track(index)
            new_index = len(self._song.tracks) - 1 if index == -1 else index
            track = self._song.tracks[new_index]
            return {"index": new_index, "name": track.name}
        except Exception as e:
            self.log_message("Error creating audio track: " + str(e))
            raise

    def _create_return_track(self):
        """Create a return track. Takes no index: Live appends returns."""
        try:
            self._song.create_return_track()
            new_index = len(self._song.return_tracks) - 1
            track = self._song.return_tracks[new_index]
            return {"index": new_index, "name": track.name}
        except Exception as e:
            self.log_message("Error creating return track: " + str(e))
            raise

    def _list_output_routings(self, track_index):
        """The routing objects this track will accept, by display name.

        Exposed because the setter below has to be given one of THESE, not
        a string of our choosing. Anything that wants to route should list
        first and match against what comes back.
        """
        try:
            track = self._song.tracks[track_index]
            return {
                "types": [t.display_name
                          for t in track.available_output_routing_types],
                "channels": [c.display_name
                             for c in track.available_output_routing_channels],
                "current_type": track.output_routing_type.display_name,
            }
        except Exception as e:
            self.log_message("Error listing output routings: " + str(e))
            raise

    def _set_output_routing(self, track_index, type_name, channel_name=None):
        """Route a track's output. Matching is by display name.

        `output_routing_type` wants a routing OBJECT out of the track's own
        `available_output_routing_types`, so this looks the name up rather
        than assigning a string. Raises when no match is found instead of
        silently leaving the routing alone, because a track that quietly
        kept its old output is the failure that is hardest to notice.
        """
        try:
            track = self._song.tracks[track_index]

            match = None
            for t in track.available_output_routing_types:
                if t.display_name == type_name:
                    match = t
                    break
            if match is None:
                available = [t.display_name
                             for t in track.available_output_routing_types]
                raise RuntimeError(
                    "no output routing type named " + repr(type_name) +
                    "; available: " + repr(available))
            track.output_routing_type = match

            if channel_name is not None:
                chan = None
                for c in track.available_output_routing_channels:
                    if c.display_name == channel_name:
                        chan = c
                        break
                if chan is None:
                    available = [c.display_name
                                 for c in track.available_output_routing_channels]
                    raise RuntimeError(
                        "no output routing channel named " +
                        repr(channel_name) + "; available: " + repr(available))
                track.output_routing_channel = chan

            return {
                "index": track_index,
                "type": track.output_routing_type.display_name,
                "channel": track.output_routing_channel.display_name,
            }
        except Exception as e:
            self.log_message("Error setting output routing: " + str(e))
            raise
'''

# ---------------------------------------------------------------------------
# Dispatch, for main_thread_task
# ---------------------------------------------------------------------------

DISPATCH = '''
                        elif command_type == "create_audio_track":
                            index = params.get("index", -1)
                            result = self._create_audio_track(index)
                        elif command_type == "create_return_track":
                            result = self._create_return_track()
                        elif command_type == "list_output_routings":
                            track_index = params.get("track_index", 0)
                            result = self._list_output_routings(track_index)
                        elif command_type == "set_output_routing":
                            track_index = params.get("track_index", 0)
                            type_name = params.get("type_name")
                            channel_name = params.get("channel_name")
                            result = self._set_output_routing(
                                track_index, type_name, channel_name)
'''


if __name__ == "__main__":
    print(__doc__)
    print("=" * 70)
    print("METHODS - paste into the AbletonMCP class")
    print("=" * 70)
    print(METHODS)
    print("=" * 70)
    print("DISPATCH - paste into main_thread_task")
    print("=" * 70)
    print(DISPATCH)
