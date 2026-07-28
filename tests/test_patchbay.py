"""Tests against the real racks in racks/.

These do not prove Live will load anything - only dragging a file in does
that. What they do prove is that the library still agrees with every
finding recorded in SCHEMA.md. If Live changes its schema, these fail and
point at the spike that needs re-running.

Run with:  uv run pytest tests/ -q
       or:  uv run tests/test_patchbay.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from patchbay import io, find, params, clone, diff, mappings, ids, variations  # noqa: E402
from patchbay.dsl import Layout, Rack, RackKind, Variation   # noqa: E402

RACKS = Path(__file__).resolve().parent.parent / "racks"
GOLDEN = Path(__file__).resolve().parent / "golden.txt"


# --- S1: round trip -------------------------------------------------------

def test_roundtrip_is_lossless(tmp_path=None):
    src = RACKS / "s1_source.adg"
    out = Path(tmp_path or "/tmp") / "rt.adg" if tmp_path else Path("build/rt.adg")
    out.parent.mkdir(exist_ok=True)
    io.save(io.load(src), out)

    from patchbay.diff import compare
    changed, only_a, only_b = compare(src, out, show_all=True)
    assert not changed and not only_a and not only_b, "round trip lost facts"
    out.unlink(missing_ok=True)


# --- S3/S4: mappings are KeyMidi, addressed by containment ----------------

def test_mapping_structure():
    root = io.load(RACKS / "s3b.adg")
    found = mappings.find(root)
    assert len(found) == 2
    by_macro = {m["macro"]: m for m in found}
    assert by_macro[1]["target"] == "PreDrive"
    assert by_macro[2]["target"] == "PostDrive"
    for m in found:
        assert m["channel"] == "16", "macro bus is channel 16"
        assert m["is_note"] == "false"


def test_macro_index_is_zero_based():
    root = io.load(RACKS / "s3b.adg")
    sat = next(root.iter("Saturator"))
    assert params.mapped_macro(find.param(sat, "PostDrive")) == 2
    assert params.is_mapped(find.param(sat, "PreDrive"))


def test_macro_to_macro_nests_three_levels():
    root = io.load(RACKS / "s1_source.adg")
    found = mappings.find(root)
    assert len(found) == 3
    depths = sorted(m["depth"] for m in found)
    assert depths == [1, 2, 2], "the DR1 pattern: one at depth 1, two at depth 2"
    assert {m["target"] for m in found} == {"MacroControls.0", "ChainSelector"}


def test_map_and_unmap_roundtrip():
    root = io.load(RACKS / "s3a.adg") if (RACKS / "s3a.adg").exists() \
        else io.load(RACKS / "s3_a.adg")
    sat = next(root.iter("Saturator"))
    p = find.param(sat, "PreDrive")

    assert not params.is_mapped(p), "s3_a is the unmapped control"
    params.map_to_macro(p, 5)
    assert params.mapped_macro(p) == 5
    km = p.find("KeyMidi")
    assert km.find("Channel").get("Value") == "16"
    assert km.find("NoteOrController").get("Value") == "4"
    # Live writes KeyMidi between LomId and Manual; match that ordering.
    tags = [c.tag for c in p]
    assert tags.index("KeyMidi") == tags.index("LomId") + 1

    assert params.unmap(p) is True
    assert not params.is_mapped(p)


# --- S5: chain zones ------------------------------------------------------

def test_zone_invariant_holds_in_real_racks():
    root = io.load(RACKS / "s5_fade_bb.adg")
    preset = find.preset(root)
    for b in find.branches(preset):
        z = find.zone(b)
        v = {c.tag: float(c.get("Value")) for c in z}
        assert v["Min"] <= v["CrossfadeMin"] <= v["CrossfadeMax"] <= v["Max"], \
            "fades grow inward from the bounds"


# --- S3b/S10: the transfer function ---------------------------------------

def test_transfer_function_matches_live():
    # Live wrote Drive=3.11810875 for macro 69 over the range -36..36.
    got = params.macro_to_value(69, -36, 36)
    assert abs(got - 3.11810875) < 1e-5
    # and the inverse round-trips
    assert abs(params.value_to_macro(got, -36, 36) - 69) < 1e-5


def test_set_range_is_the_mapping_range():
    root = io.load(RACKS / "s3b.adg")
    sat = next(root.iter("Saturator"))
    p = find.param(sat, "PreDrive")
    assert params.range_of(p) == (-36.0, 36.0)
    params.set_range(p, -36, 12)
    assert params.range_of(p) == (-36.0, 12.0)
    # macro at full now lands on +12, which is what Live showed
    assert params.macro_to_value(127, *params.range_of(p)) == 12.0


# --- S6: ids --------------------------------------------------------------

def test_real_racks_have_no_sibling_collisions():
    for f in sorted(RACKS.glob("*.adg")):
        root = io.load(f)
        assert not ids.collisions(root), f"{f.name} would be refused by Live"


def test_collision_is_detected():
    root = io.load(RACKS / "s9_b.adg")
    pads = list(root.iter("DrumBranchPreset"))
    assert len(pads) >= 2
    for p in pads:
        p.set("Id", "0")
    bad = ids.collisions(root)
    assert bad, "duplicate sibling ids must be caught before writing"
    assert any(tag == "DrumBranchPreset" for _, tag, _, _ in bad)


# --- Phase 2: cloning -----------------------------------------------------

def test_clone_branch_gets_free_id_and_keeps_mappings():
    root = io.load(RACKS / "s3b.adg")
    preset = find.preset(root)
    before = find.branches(preset)
    assert len(before) == 1

    made = clone.clone_branch(before[0], count=3)
    after = find.branches(preset)

    assert len(after) == 4
    assert len({b.get("Id") for b in after}) == 4, "ids unique among siblings"
    assert not ids.collisions(root), "Live would accept this"

    # Every copy carries its own mappings, needing no remapping.
    assert len(mappings.find(root)) == 2 * 4
    for m in made:
        sat = next(m.iter("Saturator"))
        assert params.mapped_macro(find.param(sat, "PreDrive")) == 1
        assert params.mapped_macro(find.param(sat, "PostDrive")) == 2


def test_clone_pad_assigns_free_notes():
    root = io.load(RACKS / "s9_b.adg")
    preset = find.preset(root)
    pads = find.branches(preset)
    notes_before = {b.find("ZoneSettings").find("ReceivingNote").get("Value")
                    for b in pads}

    clone.clone_pad(preset, pads[0], count=2)
    pads_after = find.branches(preset)

    notes_after = [b.find("ZoneSettings").find("ReceivingNote").get("Value")
                   for b in pads_after]
    assert len(notes_after) == len(set(notes_after)), "each pad answers to one note"
    assert len(set(notes_after) - notes_before) == 2, "new pads got new notes"
    # SendingNote is untouched: pads play at root pitch wherever they sit.
    for b in pads_after:
        assert b.find("ZoneSettings").find("SendingNote").get("Value") == "60"
    assert not ids.collisions(root)


def test_assert_loadable_raises_on_collision():
    root = io.load(RACKS / "s9_b.adg")
    for p in root.iter("DrumBranchPreset"):
        p.set("Id", "0")
    try:
        clone.assert_loadable(root)
    except ValueError as e:
        assert "collision" in str(e)
    else:
        raise AssertionError("expected a loud failure, got silence")


def test_clone_ganged_vs_per_chain():
    """Cloned chains gang to the same macro unless told otherwise.

    Both behaviours are wanted: ganged for the sound family constraint,
    per-chain when each engine needs its own knob.
    """
    root = io.load(RACKS / "s3b.adg")
    preset = find.preset(root)
    clone.clone_branch(find.branches(preset)[0], count=3)
    ganged = sorted(m["macro"] for m in mappings.find(root))
    assert ganged == [1, 1, 1, 1, 2, 2, 2, 2], "every copy answers to the same macros"

    root = io.load(RACKS / "s3b.adg")
    preset = find.preset(root)
    clone.clone_branch_per_macro(find.branches(preset)[0], count=3, stride=2)
    spread = sorted(m["macro"] for m in mappings.find(root))
    assert spread == [1, 2, 3, 4, 5, 6, 7, 8], "each copy gets its own macro block"
    assert not ids.collisions(root)


def test_macro_overflow_is_reported_not_silent():
    root = io.load(RACKS / "s3b.adg")
    preset = find.preset(root)
    _, report = clone.clone_branch_per_macro(
        find.branches(preset)[0], count=8, stride=2)
    skipped = [s for _, _, sk in report for s in sk]
    assert skipped, "running past macro 16 must be visible"
    for tag, was, would_be in skipped:
        assert would_be > 16
    # and the mappings that could not move are left valid, not corrupted
    for m in mappings.find(root):
        assert 1 <= m["macro"] <= 16


# --- S8: macro variations -------------------------------------------------

def _rack_dev(name):
    return find.rack_device(find.preset(io.load(RACKS / name)))


def test_reads_the_variations_live_wrote():
    got = variations.read(_rack_dev("s8_c.adg"))
    assert [v["name"] for v in got] == ["Variation 1", "Variation 2"]
    # Absolute on the macro 0..127 scale, matching the file's live macros.
    assert got[0]["values"] == {1: 69.0, 2: 127.0}
    assert got[1]["values"] == {1: 16.0, 2: 39.0}
    # Sparseness is MacroHasValue, so unset slots are absent rather than -1.
    assert 3 not in got[0]["values"]
    assert variations.count(_rack_dev("s8_a.adg")) == 0, "s8_a is the control"


def test_rewriting_variations_matches_live_fact_for_fact():
    """The strongest check available without Live: clear what Live wrote,
    write it back from our own code, and diff. Any disagreement about
    element order, sentinel or scale shows up here.
    """
    from patchbay.diff import compare

    src = RACKS / "s8_c.adg"
    root = io.load(src)
    dev = find.rack_device(find.preset(root))
    variations.write(dev, [(v["name"], v["values"])
                           for v in variations.read(dev)])

    out = Path("build/s8_rewrite.adg")
    out.parent.mkdir(exist_ok=True)
    io.save(root, out)
    changed, only_a, only_b = compare(src, out, show_all=True)
    assert not changed and not only_a and not only_b, \
        "our MacroSnapshot differs from the one Live wrote"
    out.unlink(missing_ok=True)


def test_all_16_slots_are_written_with_the_sentinel():
    dev = _rack_dev("s8_a.adg")
    snap = variations.append(dev, "one", {4: 100})
    for i in range(variations.SLOTS):
        assert snap.find(f"MacroValues.{i}") is not None
        assert snap.find(f"MacroHasValue.{i}") is not None
    assert snap.find("MacroValues.3").get("Value") == "100"
    assert snap.find("MacroHasValue.3").get("Value") == "true"
    assert snap.find("MacroValues.0").get("Value") == variations.UNSET
    assert snap.find("MacroHasValue.0").get("Value") == "false"
    # Live's own element order, which we match rather than test in Live.
    tags = [c.tag for c in snap]
    assert tags[:2] == ["AutogeneratedNameIndex", "SnapshotName"]
    assert tags[2] == "MacroValues.0" and tags[18] == "MacroHasValue.0"


def test_variation_ids_are_positional():
    dev = _rack_dev("s8_a.adg")
    variations.write(dev, [(f"v{i}", {1: i}) for i in range(5)])
    snaps = variations.container(dev)
    assert [s.get("Id") for s in snaps] == ["0", "1", "2", "3", "4"]
    assert [s.find("AutogeneratedNameIndex").get("Value") for s in snaps] == \
        ["1", "2", "3", "4", "5"]
    assert variations.clear(dev) == 5


def test_out_of_range_position_is_refused():
    dev = _rack_dev("s8_a.adg")
    for bad in (-1, 128, 8000):
        try:
            variations.append(dev, "bad", {1: bad})
        except ValueError as e:
            assert "macro space" in str(e)
        else:
            raise AssertionError(f"{bad} is not a macro position; expected a raise")


# --- Phase 5: variations through the DSL ----------------------------------

def _pd1():
    g = Layout("Engine", "Cutoff", "Resonance", "Decay", "Drive")
    rack = Rack("PD1", g, kind=RackKind.INSTRUMENT)
    with rack.engine("FM", "Operator") as e:
        e.bind(cutoff=("Filter/Frequency", 200, 8000),
               decay="Filter/Envelope/DecayTime")
    with rack.engine("Sample", "OriginalSimpler") as e:
        e.bind(cutoff=("Filter/Slot/Value/SimplerFilter/Freq", 200, 8000),
               decay="Filter/Slot/Value/SimplerFilter/Envelope/DecayTime")
    return rack


def test_one_vector_renders_through_every_engine():
    """The sound family constraint, as a structural fact.

    A variation names layout slots, never a device parameter, so there is
    nothing per engine to keep aligned. Both engines bind cutoff, so one
    variation is one sound in each.
    """
    rack = _pd1()
    rack.variations(Variation("dark", cutoff=30, decay=110),
                    Variation("open", cutoff=120, decay=20))
    root = rack.build()
    dev = find.rack_device(find.preset(root))

    got = variations.read(dev)
    assert [v["name"] for v in got] == ["dark", "open"]
    cutoff = rack.layout.macro_of("cutoff")
    assert got[0]["values"][cutoff] == 30

    # One macro, one mapping per engine, which is what makes that work.
    per_macro = [m["macro"] for m in mappings.find(root)]
    assert per_macro.count(cutoff) == len(rack.engines)


def test_engine_choice_is_a_variation_slot():
    """A sound is a variation, not a chain, so it may pick its own engine."""
    rack = _pd1()
    fm, sample = rack.engine_macro("FM"), rack.engine_macro("Sample")
    assert fm < 64 <= sample, "each engine's zone centre falls in its own half"

    rack.variations(Variation("fm sound", engine=fm, cutoff=40),
                    Variation("sampled", engine=sample, cutoff=40))
    root = rack.build()
    preset = find.preset(root)
    dev = find.rack_device(preset)

    slot = rack.layout.macro_of("engine")
    got = variations.read(dev)
    assert got[0]["values"][slot] == fm and got[1]["values"][slot] == sample

    # The position has to fall inside the zone it claims to select.
    for i, branch in enumerate(find.branches(preset)):
        z = {c.tag: float(c.get("Value")) for c in find.zone(branch)}
        pos = rack.engine_macro(i)
        assert z["Min"] <= pos <= z["Max"]


def test_variation_on_an_undriven_slot_is_refused():
    """Fail loudly: a flagged macro with nothing mapped to it is SPIKES Q5,
    untested, so the DSL refuses rather than shipping a guess."""
    rack = _pd1()
    rack.variations(Variation("bad", drive=90))
    try:
        rack.build()
    except ValueError as e:
        assert "drive" in str(e) and "no engine binds" in str(e)
    else:
        raise AssertionError("expected a raise, got a rack with a dead knob")


def test_unknown_slot_fails_at_declaration_not_at_build():
    rack = _pd1()
    try:
        rack.variations(Variation("typo", cuttoff=40))
    except KeyError as e:
        assert "cuttoff" in str(e)
    else:
        raise AssertionError("a mistyped slot must not reach the file")


def test_a_built_rack_does_not_inherit_donor_variations():
    """Skeletons come from real racks, which may carry variations of their
    own. Those describe a different rack and must not survive."""
    rack = _pd1()
    root = rack.build()
    dev = find.rack_device(find.preset(root))
    assert variations.count(dev) == 0

    rack.variations(Variation("only one", cutoff=10))
    dev = find.rack_device(find.preset(rack.build()))
    assert variations.count(dev) == 1


def test_the_patchbayground_grid_builds():
    """The spec this project exists for, compiled end to end."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    rack = patchbayground.pd1()
    assert len(rack.variation_set) == 96, "2 engines x 4 x 4 x 3"
    dev = find.rack_device(find.preset(rack.build()))
    got = variations.read(dev)
    assert len(got) == 96
    assert len({v["name"] for v in got}) == 96, "names must be distinguishable"
    for v in got:
        assert set(v["values"]) == {rack.layout.macro_of(s)
                                    for s in ("instrument", "filter",
                                              "release", "character")}


# --- nested racks ---------------------------------------------------------

def _nested_pair():
    """An outer rack with one chain holding an inner rack."""
    g = Layout("Engine", "Cutoff")
    inner = Rack("INNER", g, kind=RackKind.INSTRUMENT)
    with inner.engine("FM", "Operator") as e:
        e.bind(cutoff="Filter/Frequency")
    outer = Rack("OUTER", g, kind=RackKind.INSTRUMENT)
    outer.nest("SUB", inner)
    return outer


def test_only_the_top_level_preset_carries_no_id():
    """The one difference between the two positions a GroupDevicePreset can
    occupy, and the reason a lifted-out nested rack was refused as a drop."""
    outer = _nested_pair()
    racks = list(find.walk_racks(find.preset(outer.build())))
    assert len(racks) == 2
    assert racks[0].attrib == {}, "a top-level preset has no attributes"
    assert racks[1].get("Id") is not None, "a nested preset is a sibling, so it has one"


def test_live_saved_racks_agree_on_that():
    for f in sorted(RACKS.glob("*.adg")):
        assert find.preset(io.load(f)).attrib == {}, f.name


def test_a_nested_skeleton_loses_its_id():
    """s1_source's inner rack is usable as a skeleton once the Id is gone."""
    g = Layout("Engine", "Cutoff")
    rack = Rack("FROM_NESTED", g, kind=RackKind.INSTRUMENT,
                skeleton=RACKS / "s1_source.adg")
    with rack.engine("FM", "Operator") as e:
        e.bind(cutoff="Filter/Frequency")
    assert find.preset(rack.build()).attrib == {}


def test_nesting_chains_macro_to_macro():
    """Outer macro N drives the inner rack's MacroControls, Channel 16 and
    no depth encoded anywhere - so the mapping is the same at any depth."""
    root = _nested_pair().build()
    inner = find.walk_racks(find.preset(root))
    inner = list(inner)[1]
    dev = find.rack_device(inner)
    target = find.macro(dev, 2)                 # inner Cutoff
    assert params.mapped_macro(target) == 2     # driven by outer Cutoff
    assert target.find("KeyMidi/Channel").get("Value") == "16"


def test_nest_defaults_to_identity_over_the_shared_layout():
    outer = _nested_pair()
    assert outer.engines[0].resolved() == {"Engine": "Engine", "Cutoff": "Cutoff"}


def test_an_explicit_bind_replaces_the_default():
    outer = _nested_pair()
    outer.engines[0].bind(cutoff="cutoff")
    assert outer.engines[0].resolved() == {"cutoff": "cutoff"}


def test_a_nested_slot_counts_as_driven():
    """A variation may name a slot only something answers to, and a chained
    macro answers just as much as a bound parameter does."""
    outer = _nested_pair()
    outer.variations(Variation("v", cutoff=40))
    dev = find.rack_device(find.preset(outer.build()))
    assert variations.count(dev) == 1


def test_an_instrument_rack_is_refused_in_an_audio_effect_chain():
    g = Layout("Cutoff")
    inner = Rack("I", g, kind=RackKind.INSTRUMENT)
    outer = Rack("A", g, kind=RackKind.AUDIO_EFFECT)
    try:
        outer.nest("SUB", inner)
    except ValueError as e:
        assert "audio effect chain" in str(e)
    else:
        raise AssertionError("Live refuses this preset; so must we")


def test_va1_builds_two_levels():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    root = patchbayground.va1().build()
    racks = list(find.walk_racks(find.preset(root)))
    assert len(racks) == 3, "the outer rack and its two sub-racks"
    chained = [m for m in mappings.find(root)
               if m["target"].startswith("MacroControls.")]
    assert len(chained) == 12, "6 slots chained into each of 2 sub-racks"
    assert all(m["channel"] == "16" for m in chained), "depth is not encoded"


# --- drum pads ------------------------------------------------------------

def _kit():
    inner = Rack("KICK", Layout("Engine", "Cutoff"))
    inner.engine("S1", "OriginalSimpler").bind(
        cutoff="Filter/Slot/Value/SimplerFilter/Freq")
    kit = Rack("DR1", Layout("Tune", "Decay"), kind=RackKind.DRUM)
    kit.pad("KICK", 36, rack=inner)
    kit.pad("RIM", 37, device="OriginalSimpler")
    return kit


def test_a_pad_is_addressed_by_note():
    branches = find.branches(find.preset(_kit().build()))
    notes = [b.find("ZoneSettings/ReceivingNote").get("Value") for b in branches]
    assert notes == ["36", "37"]
    for b in branches:
        assert b.find("ZoneSettings/SendingNote").get("Value") == "60", (
            "a pad's sampler plays at root pitch wherever the pad sits")


def test_pads_are_exempt_from_zone_distribution():
    """Live leaves every pad's zone at 0/0/0/0; the note is the selector."""
    for b in find.branches(find.preset(_kit().build())):
        assert {c.tag: c.get("Value") for c in find.zone(b)} == {
            "Min": "0", "Max": "0", "CrossfadeMin": "0", "CrossfadeMax": "0"}


def test_declared_zones_override_the_even_share():
    """A hand built rack divides its selector however it likes."""
    rack = Rack("PD1", Layout("Cutoff"), kind=RackKind.INSTRUMENT)
    with rack.engine("A", "OriginalSimpler") as e:
        e.zone(0, 99)
    with rack.engine("B", "OriginalSimpler") as e:
        e.zone(100, 127)

    got = [{c.tag: c.get("Value") for c in find.zone(b)}
           for b in find.branches(find.preset(rack.build()))]
    assert [(z["Min"], z["Max"]) for z in got] == [("0", "99"), ("100", "127")]
    assert [(z["CrossfadeMin"], z["CrossfadeMax"]) for z in got] == [
        ("0", "99"), ("100", "127")]


def test_a_half_declared_zone_set_is_refused():
    """The other chain would take an even share of a scale it does not own."""
    rack = Rack("PD1", Layout("Cutoff"), kind=RackKind.INSTRUMENT)
    with rack.engine("A", "OriginalSimpler") as e:
        e.zone(0, 99)
    rack.engine("B", "OriginalSimpler")
    try:
        rack.build()
    except ValueError as e:
        assert "has no zone" in str(e)
    else:
        raise AssertionError("a partly zoned rack must not reach a file")


def test_a_pad_may_hold_a_device_or_a_whole_rack():
    branches = find.branches(find.preset(_kit().build()))
    assert [d.tag for d in find.devices(branches[0])] == ["GroupDevicePreset"]
    assert [d.tag for d in find.devices(branches[1])] == ["OriginalSimpler"]


def test_two_pads_on_one_note_is_refused():
    """Legal and loadable, and almost never what anyone means: they fire
    together."""
    kit = Rack("DR1", Layout("Tune"), kind=RackKind.DRUM)
    kit.pad("KICK", 36, device="OriginalSimpler")
    try:
        kit.pad("SNARE", 36, device="OriginalSimpler")
    except ValueError as e:
        assert "already triggers" in str(e)
    else:
        raise AssertionError("two pads on one note must not reach a file")


def test_pads_need_a_drum_rack():
    rack = Rack("PD1", Layout("Cutoff"), kind=RackKind.INSTRUMENT)
    try:
        rack.pad("KICK", 36, device="OriginalSimpler")
    except ValueError as e:
        assert "drum rack" in str(e)
    else:
        raise AssertionError("an instrument rack has no pads")


def test_a_pad_holds_exactly_one_thing():
    kit = Rack("DR1", Layout("Tune"), kind=RackKind.DRUM)
    for kwargs in ({}, {"device": "OriginalSimpler", "rack": Rack("X", Layout("A"))}):
        try:
            kit.pad("KICK", 36, **kwargs)
        except ValueError as e:
            assert "exactly one" in str(e)
        else:
            raise AssertionError(f"pad({kwargs}) should not build")


# --- S12: devices may be partial ------------------------------------------

def test_params_survives_a_gutted_device():
    root = io.load(RACKS / "s3b.adg")
    sat = next(root.iter("Saturator"))
    ps = find.params(sat)
    # 19, not the 18 quoted in SCHEMA.md S12: the ad-hoc script used there
    # excluded `On`, the device enable. `On` has a Manual and is macro
    # mappable like any other parameter, so it counts.
    assert len(ps) == 19
    assert ps[0].tag == "On"
    for p in list(ps):
        sat.remove(p)
    assert find.params(sat) == []
    assert find.param(sat, "PreDrive") is None, "absent is not an error"


# --- T3/S7: sample retargeting --------------------------------------------

def _a_wav(dirpath):
    """A real, minimal 48 kHz mono 16-bit WAV. 10 frames of silence.

    Written rather than borrowed: nothing under `samples/` may be read by a
    test, and `sample()` refuses a path that is not a file.
    """
    import struct
    frames = 10
    data = b"\x00\x00" * frames
    hdr = (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt "
           + struct.pack("<IHHIIHH", 16, 1, 1, 48000, 96000, 2, 16)
           + b"data" + struct.pack("<I", len(data)))
    p = Path(dirpath) / "probe.wav"
    p.write_bytes(hdr + data)
    return p


def test_sample_retargets_both_filerefs(tmp_path=None):
    from patchbay import samples
    out = Path(tmp_path) if tmp_path else Path("build")
    out.mkdir(exist_ok=True)
    wav = _a_wav(out)

    rack = Rack("SR", Layout("Instrument", "Filter"), kind=RackKind.INSTRUMENT)
    with rack.engine("S", "OriginalSimpler") as e:
        e.sample(wav)

    device = find.devices(next(find.preset(rack.build()).iter("BranchPresets"))[0])[0]
    got = samples.targets(device)

    # S7: TWO FileRefs per sample, and in the donor they point at different
    # files. Both must move, or the provenance ref still names the old one.
    assert len(got) == 2, "the live ref and the provenance ref"
    assert set(got) == {wav.resolve().as_posix()}, "both, to the same file"
    assert all("/" in p and "\\" not in p for p in got), "Live writes posix"


def test_sample_refuses_a_missing_file():
    rack = Rack("SR", Layout("Instrument"), kind=RackKind.INSTRUMENT)
    with rack.engine("S", "OriginalSimpler") as e:
        try:
            e.sample("no/such/file.wav")
        except FileNotFoundError:
            return
    raise AssertionError("a missing sample loads offline, so it must refuse")


def test_sample_refuses_a_device_with_no_sampleref(tmp_path=None):
    out = Path(tmp_path) if tmp_path else Path("build")
    out.mkdir(exist_ok=True)
    wav = _a_wav(out)

    rack = Rack("X", Layout("Instrument"), kind=RackKind.INSTRUMENT)
    with rack.engine("FM", "Operator") as e:
        e.sample(wav)
    try:
        rack.build()
    except ValueError as err:
        assert "SampleRef" in str(err)
        return
    raise AssertionError("Operator holds no sample; pointing one at it is a bug")


def test_dr1_is_three_levels_with_one_sample_per_chain():
    """Skips where `samples/` is absent: the audio is never committed."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground
    from patchbay import samples as S

    kit = patchbayground.dr1()
    if kit is None:
        return  # no samples on this machine

    root = kit.build()
    pre = find.preset(root)

    notes = sorted(int(el.get("Value")) for el in root.iter("ReceivingNote"))
    assert notes == sorted(n for _, n, _ in patchbayground.PADS)
    assert len(notes) == len(set(notes)), "two pads on one note fire together"

    # kit + one rack per pad
    assert len(list(find.walk_racks(pre))) == len(notes) + 1

    paths = set()
    for dev in root.iter("OriginalSimpler"):
        paths.update(S.targets(dev))
    assert paths, "every pad chain carries a sample"
    assert all(Path(p).is_file() for p in paths), "no chain points at nothing"


def _mapping_matrix(rack):
    """{chain name: {macro: [target tags]}} for one built rack."""
    out = {}
    for branch in find.branches(find.preset(rack.build())):
        name = branch.find("Name").get("Value")
        per_macro = {}
        for km in branch.iter("KeyMidi"):
            cc = int(km.find("NoteOrController").get("Value")) + 1
            per_macro.setdefault(cc, []).append(km.getparent().tag)
        out[name] = {k: sorted(v) for k, v in per_macro.items()}
    return out


def test_the_wildcard_slot_reaches_only_the_engines_that_offer_it():
    """Slot 6 is a per rack role, and an engine without it stays empty.

    An ABSENCE is what a file can prove. That a knob is mapped says nothing
    about whether it is audible, which is the whole of Q16: Drift's
    `Lfo_Amount` is bound, resolves, and reaches nothing, because the
    routing is not a parameter. So this asserts which mappings exist and
    stops there.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    by_name = {r.name: r for r in patchbayground.RACKS}
    slot = patchbayground.PATCHBAYGROUND.macro_of("Character")

    # BS1 asks for morph and only Meld has one.
    bs1 = _mapping_matrix(by_name["BS1"])
    assert slot in bs1["Meld"]
    for chain in ("Wave", "Drift"):
        assert slot not in bs1[chain], (
            f"BS1 {chain} answers slot 6, which no Wavetable or Drift "
            f"parameter can serve; it should be left empty")

    # Where every engine offers the role, every chain answers.
    for name, chains in (("PD1W", ("Wave", "Drift")), ("LD1", ("FM", "Meld"))):
        matrix = _mapping_matrix(by_name[name])
        for chain in chains:
            assert slot in matrix[chain], f"{name} {chain} does not answer slot 6"


def test_the_filter_slot_drives_a_pair_on_every_engine():
    """Slot 3 is cutoff AND resonance, which is what frees slot 6."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    slot = patchbayground.PATCHBAYGROUND.macro_of("Filter")
    for rack in patchbayground.RACKS:
        if rack.layout is not patchbayground.PATCHBAYGROUND:
            continue
        for chain, per_macro in _mapping_matrix(rack).items():
            targets = per_macro.get(slot, [])
            assert len(targets) >= 2, (
                f"{rack.name} {chain}: slot 3 drives {targets}, not a pair")


def test_release_is_one_interval_however_an_engine_spells_it():
    """Operator and Simpler keep envelope times in ms, the others in seconds.

    So one knob position means one length only if the two ranges are the
    same interval scaled by 1000. That is arithmetic, and it used to be
    three people-minutes of holding notes and comparing tails.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    slot = patchbayground.PATCHBAYGROUND.macro_of("Release")
    found = set()
    for rack in patchbayground.RACKS:
        if rack.layout is not patchbayground.PATCHBAYGROUND:
            continue
        for branch in find.branches(find.preset(rack.build())):
            for km in branch.iter("KeyMidi"):
                if int(km.find("NoteOrController").get("Value")) + 1 != slot:
                    continue
                target = km.getparent()
                # Macro-to-macro chaining is 0..127 and not a device range.
                if target.tag.startswith("MacroControls"):
                    continue
                found.add(params.range_of(target))

    assert len(found) == 2, f"expected seconds and milliseconds, got {found}"
    lo, hi = sorted(found, key=lambda r: r[1])
    assert hi == (lo[0] * 1000.0, lo[1] * 1000.0), (
        f"{hi} is not {lo} in milliseconds, so slot 7 means two different "
        f"lengths depending on the engine")


def test_the_example_racks_still_build_the_same_bytes():
    """The output-identity gate. A refactor that moves no output proves it here.

    Live tells you a file loads; it never tells you a file is UNCHANGED, and
    a human dragging in a rack cannot see that 14,823 facts are the same
    14,823 facts. So a change that is not supposed to move the output says so
    against this, and nobody opens Live for it.

    A digest rather than the facts themselves: the five racks flatten to
    9.5 MB, and a hash per rack fits in a file whose git diff is readable.
    When one fails, build the rack before and after and run `patchbay diff`
    for the detail.

    This also catches a hazard nothing else does. Skeleton and donor
    selection reads `donors/` and `racks/` by name, so adding a file can
    silently rebuild every rack. That shows up here as five failures.

    Regenerate deliberately, never to make a red test green:
        PATCHBAY_REGOLD=1 uv run pytest tests/ -k same_bytes
    """
    import hashlib
    import os

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    def digest(rack):
        facts = diff.flatten(rack.build())
        text = "\n".join(f"{k}={v}" for k, v in sorted(facts.items()))
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    built = {rack.name: digest(rack) for rack in patchbayground.RACKS}

    if os.environ.get("PATCHBAY_REGOLD"):
        GOLDEN.write_text(
            "".join(f"{n} {built[n]}\n" for n in sorted(built)), newline="\n")
        return

    golden = dict(line.split() for line in
                  GOLDEN.read_text().splitlines() if line.strip())

    # DR1 needs samples/, which is never committed, so it is absent on a
    # machine that has the repo and not the audio. The other five are not.
    for name in ("PD1", "PD1W", "BS1", "LD1", "VA1"):
        assert name in built, f"{name} did not build"
        assert built[name] == golden[name], (
            f"{name} changed. If that was intended, rebuild the goldens; "
            f"if not, `patchbay diff` it against a build from before.")


def test_bound_macros_do_not_open_at_zero():
    """Every rack in the example places the slots it binds.

    A macro Live has never been told about reads 0, and 0 through a binding
    is the BOTTOM of the parameter's range. That shipped once: PD1W, BS1,
    LD1, DR1 and PD1 all loaded in Live 12.4.3 silent, with the filter shut,
    and every one of them had to be turned up by hand before it made a
    sound. Nothing in the file was malformed, so only ears caught it.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    for rack in patchbayground.RACKS:
        dev = find.rack_device(find.preset(rack.build()))
        for slot in ("Filter", "Volume"):
            if slot.lower() not in rack.driven_slots():
                continue
            got = params.value(find.macro(dev, rack.layout.macro_of(slot)))
            assert got, f"{rack.name}: {slot} opens at {got}"


def test_one_slot_can_drive_several_parameters():
    """Meld is two engines behind one device; binding A alone filters half.

    Gated in Live 12.4.3 as C2: Macro 3 moved the A side and left B wide
    open, audibly, on a rack where every id, every mapping and every range
    checked out.
    """
    g = Layout("Engine", "Filter", selector="Engine")
    rack = Rack("X", g)
    with rack.engine("M", "InstrumentMeld") as e:
        e.bind(filter=[("MeldVoice_EngineA_Filter_Frequency", 30.0, 18500.0),
                       ("MeldVoice_EngineB_Filter_Frequency", 30.0, 18500.0)])
    root = rack.build()
    on_two = sorted(m["target"] for m in mappings.find(root) if m["macro"] == 2)
    assert on_two == ["MeldVoice_EngineA_Filter_Frequency",
                      "MeldVoice_EngineB_Filter_Frequency"]


def test_binding_a_slot_twice_replaces_rather_than_accumulates():
    g = Layout("Engine", "Filter", selector="Engine")
    rack = Rack("X", g)
    with rack.engine("M", "InstrumentMeld") as e:
        e.bind(filter="MeldVoice_EngineA_Filter_Frequency")
        e.bind(filter="MeldVoice_EngineB_Filter_Frequency")
    on_two = [m["target"] for m in mappings.find(rack.build()) if m["macro"] == 2]
    assert on_two == ["MeldVoice_EngineB_Filter_Frequency"]


def _labels(rack):
    dev = find.rack_device(find.preset(rack.build()))
    return [dev.find(f"MacroDisplayNames.{i}").get("Value")
            for i in range(len(rack.layout))]


def test_a_label_overrides_the_slot_name_without_moving_the_slot():
    """Position is the contract, the word is local.

    A slot that drives a PAIR ships a knob whose name under-describes it,
    and nothing in the format marks a selector as stepping rather than
    sweeping. Both are display problems with no other place to live.
    """
    g = Layout("Engine", "Filter", selector="Engine",
                labels={"Engine": "> Engine"})
    rack = Rack("X", g, labels={"Filter": "Filter + Res"})
    with rack.engine("A", "Operator") as e:
        e.bind(filter="Filter/Frequency")
    assert _labels(rack) == ["> Engine", "Filter + Res"]
    # The key did not move: bind() and macro_of() still take the slot name.
    assert g.macro_of("filter") == 2


def test_two_racks_on_one_layout_may_label_differently():
    g = Layout("Engine", "Drive", selector="Engine")
    a = Rack("KICK", g, labels={"Drive": "Drive + Snap"})
    b = Rack("HAT", g)
    for r in (a, b):
        with r.engine("S", "OriginalSimpler") as e:
            e.bind(drive="Filter/Slot/Value/SimplerFilter/Drive")
    assert _labels(a) == ["Engine", "Drive + Snap"]
    assert _labels(b) == ["Engine", "Drive"]


def test_a_label_for_a_slot_that_does_not_exist_is_refused():
    g = Layout("Engine", "Filter", selector="Engine")
    for bad in ({"Cutoff": "x"},):
        try:
            Rack("X", g, labels=bad)
        except KeyError:
            continue
        assert False, f"{bad} accepted as a label"


def test_start_refuses_a_position_off_the_macro_scale():
    g = Layout("Engine", "Volume", selector="Engine")
    rack = Rack("X", g)
    for bad in (-1, 128, 200):
        try:
            rack.start(volume=bad)
        except ValueError:
            continue
        assert False, f"{bad} accepted as a macro position"


def test_start_is_not_written_for_a_slot_nothing_drives():
    """A knob parked somewhere meaningful that moves nothing reads as a bug."""
    g = Layout("Engine", "Filter", "Volume", selector="Engine",
                start={"Filter": 127, "Volume": 127})
    rack = Rack("X", g)
    with rack.engine("A", "Operator") as e:
        e.bind(volume="Globals/Volume")
    dev = find.rack_device(find.preset(rack.build()))
    assert params.value(find.macro(dev, 3)) == 127     # Volume, bound
    assert params.value(find.macro(dev, 2)) == 0       # Filter, bound by nothing


# --- T6a: extraction ------------------------------------------------------

def _structure(root):
    """Chains, macro mappings and macro positions: what a spec determines.

    Positions are in here because dropping them is not a cosmetic loss: a
    Volume macro rebuilt at 0 is a rack that loads silent.
    """
    pre = find.preset(root)
    dev = find.rack_device(pre)
    chains = [((b.find("Name").get("Value") if b.find("Name") is not None else ""),
               find.devices(b)[0].tag if find.devices(b) else None)
              for b in find.branches(pre)]
    maps = sorted((m["macro"], m["target"])
                  for m in mappings.find(root) if m["macro"])
    pos = [params.raw_value(find.macro(dev, i + 1)) for i in range(8)]
    names = [dev.find(f"MacroDisplayNames.{i}").get("Value") for i in range(8)]
    return chains, maps, pos, names


def test_extract_round_trips_structure(tmp_path=None):
    """Extract a rack, rebuild from the emitted source, compare.

    Exact, over every fact `flatten` can see, not merely structural. A rack
    that patchbay built is rebuilt from the same donors, so anything left
    over is the extractor failing to say something the rack contains. This
    caught missing ranges, missing variations and invented chain names.

    A rack Live built is a different question and does not pass this: its
    devices carry values no DSL declaration holds. See DSL.md.
    """
    from patchbay import extract
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    for rack in patchbayground.RACKS:
        original = rack.build()
        out = Path(tmp_path or "build") / f"{rack.name}.extract.adg"
        out.parent.mkdir(exist_ok=True)
        io.save(original, out)

        ns = {}
        exec(compile(extract.source(out), str(out), "exec"), ns)
        rebuilt = ns["RACKS"][0].build()

        a, b = _structure(io.load(out)), _structure(rebuilt)
        assert a[0] == b[0], f"{rack.name}: chains differ"
        assert a[1] == b[1], f"{rack.name}: mappings differ"
        assert a[2] == b[2], f"{rack.name}: macro positions differ"
        assert a[3] == b[3], f"{rack.name}: macro labels differ"

        back = out.with_suffix(".rebuilt.adg")
        io.save(rebuilt, back)
        changed, lost, invented = diff.compare(out, back, show_all=True)
        assert not (changed or lost or invented), (
            f"{rack.name}: {len(changed)} changed, {len(lost)} lost, "
            f"{len(invented)} invented. First: "
            f"{sorted(changed or lost or invented)[:3]}")


# --- house style ----------------------------------------------------------

EM_DASH = chr(0x2014)   # named by codepoint so this file does not trip its own check
EN_DASH = chr(0x2013)


def test_no_em_dashes():
    """CLAUDE.md forbids em-dashes. Enforce it rather than asking.

    A rule nobody checks is a rule that decays. This one decayed within a
    session of being written, which is why it is a test.
    """
    root = Path(__file__).resolve().parent.parent
    skip = {".git", "ableton-mcp", "build", ".venv", "__pycache__",
            "patchbay.egg-info"}
    offenders = []
    for pattern in ("*.md", "*.py"):
        for f in root.rglob(pattern):
            if skip & set(f.parts):
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(text.splitlines(), 1):
                if EM_DASH in line or EN_DASH in line:
                    offenders.append(f"{f.relative_to(root)}:{i}")
    assert not offenders, (
        f"em-dash or en-dash in {len(offenders)} place(s): "
        f"{offenders[:5]}. Use a plain hyphen.")


def test_no_carriage_returns_in_tracked_text():
    """LF only. A rule nobody checks is a rule that decays, same as above.

    Ableton's own files are exempt and must stay exempt: an `.adg` is gzip,
    and `.xml` is Live's own CRLF output kept byte for byte so a diff
    against a Live-saved file still means something. `.gitattributes`
    encodes the same split for git.
    """
    import subprocess

    root = Path(__file__).resolve().parent.parent
    binary = (".adg", ".adv", ".als", ".alp", ".wav", ".aif", ".aiff",
              ".flac", ".xml")
    listed = subprocess.run(["git", "ls-files"], cwd=root,
                            capture_output=True, text=True)
    if listed.returncode != 0:
        return                                  # not a checkout, nothing to check

    offenders = []
    for name in listed.stdout.split():
        if name.endswith(binary):
            continue
        f = root / name
        if not f.is_file():
            continue
        data = f.read_bytes()
        if b"\x00" in data[:8000]:              # a binary we have not listed
            continue
        if b"\r" in data:
            offenders.append(name)
    assert not offenders, (
        f"carriage returns in {len(offenders)} tracked text file(s): "
        f"{offenders[:5]}. This is an LF repo; see .gitattributes.")


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  pass  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
