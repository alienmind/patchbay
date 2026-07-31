"""Tests against the real racks in racks/.

These do not prove Live will load anything - only dragging a file in does
that. What they do prove is that the library still agrees with every
finding recorded in SCHEMA.md. If Live changes its schema, these fail and
point at the spike that needs re-running.

Run with:  uv run pytest tests/ -q
       or:  uv run tests/test_patchbay.py
"""

import atexit
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from patchbay import io, find, params, clone, diff, mappings, ids, variations  # noqa: E402
from patchbay import dsl   # noqa: E402
from patchbay.dsl import Engine, Layout, Rack, Range, Slot   # noqa: E402

RACKS = Path(__file__).resolve().parent.parent / "racks"
GOLDEN = Path(__file__).resolve().parent / "golden.txt"

#: Where tests write. NOT `build/`, which holds what `patchbay build`
#: produces and nothing else: a suite that leaves 190 round-trip files
#: beside 58 racks makes the output of a build unreadable, and the two are
#: indistinguishable by name. Removed at interpreter exit.
SCRATCH = Path(tempfile.mkdtemp(prefix="patchbay-tests-"))
atexit.register(shutil.rmtree, SCRATCH, True)


# --- S1: round trip -------------------------------------------------------

def test_roundtrip_is_lossless():
    src = RACKS / "s1_source.adg"
    out = SCRATCH / "rt.adg"
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

    out = SCRATCH / "s8_rewrite.adg"
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

PD1 = Layout(Slot("Engine", selects=True), Slot("Cutoff"), Slot("Resonance"),
             Slot("Decay"), Slot("Drive"))

CUTOFF = Range(200, 8000, "Hz")


def _pd1():
    return (Rack.instrument("PD1", PD1)
            .chain("FM", Engine("Operator")
                   .drives(PD1.cutoff, "Filter/Frequency", over=CUTOFF)
                   .drives(PD1.decay, "Filter/Envelope/DecayTime"))
            .chain("Sample", Engine("OriginalSimpler")
                   .drives(PD1.cutoff, "Filter/Slot/Value/SimplerFilter/Freq",
                           over=CUTOFF)
                   .drives(PD1.decay,
                           "Filter/Slot/Value/SimplerFilter/Envelope/DecayTime")))


def test_one_vector_renders_through_every_engine():
    """The sound family constraint, as a structural fact.

    A variation names layout slots, never a device parameter, so there is
    nothing per engine to keep aligned. Both engines bind cutoff, so one
    variation is one sound in each.
    """
    rack = _pd1().variations(PD1.variation("dark", cutoff=30, decay=110),
                             PD1.variation("open", cutoff=120, decay=20))
    root = rack.build()
    dev = find.rack_device(find.preset(root))

    got = variations.read(dev)
    assert [v["name"] for v in got] == ["dark", "open"]
    cutoff = PD1.cutoff.number
    assert got[0]["values"][cutoff] == 30

    # One macro, one mapping per engine, which is what makes that work.
    per_macro = [m["macro"] for m in mappings.find(root)]
    assert per_macro.count(cutoff) == len(rack.engines)


def test_engine_choice_is_a_variation_slot():
    """A sound is a variation, not a chain, so it may pick its own engine."""
    rack = _pd1()
    fm, sample = rack.engine_macro("FM"), rack.engine_macro("Sample")
    assert fm < 64 <= sample, "each engine's zone centre falls in its own half"

    rack = rack.variations(PD1.variation("fm sound", engine=fm, cutoff=40),
                           PD1.variation("sampled", engine=sample, cutoff=40))
    root = rack.build()
    preset = find.preset(root)
    dev = find.rack_device(preset)

    slot = PD1.engine.number
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
    rack = _pd1().variations(PD1.variation("bad", drive=90))
    try:
        rack.build()
    except ValueError as e:
        assert "Drive" in str(e) and "no chain drives" in str(e)
    else:
        raise AssertionError("expected a raise, got a rack with a dead knob")


def test_unknown_slot_fails_at_declaration_not_at_build():
    """And at the LAYOUT, which is one step earlier than it used to be."""
    try:
        PD1.variation("typo", cuttoff=40)
    except AttributeError as e:
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

    rack = rack.variations(PD1.variation("only one", cutoff=10))
    dev = find.rack_device(find.preset(rack.build()))
    assert variations.count(dev) == 1


def test_the_patchbayground_grid_builds():
    """The spec this project exists for, compiled end to end."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    rack = patchbayground.PD1
    assert len(rack.variation_set) == 96, "2 engines x 4 x 4 x 3"
    dev = find.rack_device(find.preset(rack.build()))
    got = variations.read(dev)
    assert len(got) == 96
    assert len({v["name"] for v in got}) == 96, "names must be distinguishable"
    for v in got:
        assert set(v["values"]) == {patchbayground.PB[s].number
                                    for s in ("Instrument", "Filter",
                                              "Release", "Character")}


# --- nested racks ---------------------------------------------------------

NEST = Layout(Slot("Engine", selects=True), Slot("Cutoff"))


def _nested_pair(*chained):
    """An outer rack with one chain holding an inner rack.

    No `chained` slots keeps the identity default, which is what one shared
    layout is for.
    """
    inner = Rack.instrument("INNER", NEST).chain(
        "FM", Engine("Operator").drives(NEST.cutoff, "Filter/Frequency"))
    return Rack.instrument("OUTER", NEST).chain("SUB", inner.chaining(*chained))


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
    rack = (Rack.instrument("FROM_NESTED", NEST,
                            skeleton=RACKS / "s1_source.adg")
            .chain("FM", Engine("Operator").drives(NEST.cutoff, "Filter/Frequency")))
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


def test_chaining_defaults_to_identity_over_the_shared_layout():
    assert _nested_pair()._resolve()[0].chained == {1: 1, 2: 2}


def test_naming_the_slots_replaces_the_identity_default():
    """A partial chaining means only what is named is driven."""
    assert _nested_pair(NEST.cutoff)._resolve()[0].chained == {2: 2}


def test_an_outer_slot_may_drive_a_differently_named_inner_one():
    assert _nested_pair(NEST.engine.to(NEST.cutoff))._resolve()[0].chained == {1: 2}


def test_a_nested_slot_counts_as_driven():
    """A variation may name a slot only something answers to, and a chained
    macro answers just as much as a bound parameter does."""
    outer = _nested_pair().variations(NEST.variation("v", cutoff=40))
    dev = find.rack_device(find.preset(outer.build()))
    assert variations.count(dev) == 1


def test_an_instrument_rack_is_refused_in_an_audio_effect_chain():
    g = Layout(Slot("Cutoff"))
    inner = Rack.instrument("I", g)
    outer = Rack.audio_effect("A", g)
    try:
        outer.chain("SUB", inner)
    except ValueError as e:
        assert "audio effect chain" in str(e)
    else:
        raise AssertionError("Live refuses this preset; so must we")


def test_va1_builds_two_levels():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    root = patchbayground.VA1.build()
    racks = list(find.walk_racks(find.preset(root)))
    assert len(racks) == 3, "the outer rack and its two sub-racks"
    chained = [m for m in mappings.find(root)
               if m["target"].startswith("MacroControls.")]
    assert len(chained) == 12, "6 slots chained into each of 2 sub-racks"
    assert all(m["channel"] == "16" for m in chained), "depth is not encoded"


# --- drum pads ------------------------------------------------------------

def _kit():
    inner = Rack.instrument("KICK", NEST).chain(
        "S1", Engine("OriginalSimpler").drives(
            NEST.cutoff, "Filter/Slot/Value/SimplerFilter/Freq"))
    return (Rack.drum("DR1", Layout(Slot("Tune"), Slot("Decay")))
            .pad("KICK", 36, inner)
            .pad("RIM", 37, Engine("OriginalSimpler")))


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
    rack = (Rack.instrument("PD1", Layout(Slot("Cutoff")))
            .chain("A", Engine("OriginalSimpler").zone(0, 99))
            .chain("B", Engine("OriginalSimpler").zone(100, 127)))

    got = [{c.tag: c.get("Value") for c in find.zone(b)}
           for b in find.branches(find.preset(rack.build()))]
    assert [(z["Min"], z["Max"]) for z in got] == [("0", "99"), ("100", "127")]
    assert [(z["CrossfadeMin"], z["CrossfadeMax"]) for z in got] == [
        ("0", "99"), ("100", "127")]


def test_a_half_declared_zone_set_is_refused():
    """The other chain would take an even share of a scale it does not own."""
    rack = (Rack.instrument("PD1", Layout(Slot("Cutoff")))
            .chain("A", Engine("OriginalSimpler").zone(0, 99))
            .chain("B", Engine("OriginalSimpler")))
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
    kit = Rack.drum("DR1", Layout(Slot("Tune"))).pad(
        "KICK", 36, Engine("OriginalSimpler"))
    try:
        kit.pad("SNARE", 36, Engine("OriginalSimpler"))
    except ValueError as e:
        assert "already triggers" in str(e)
    else:
        raise AssertionError("two pads on one note must not reach a file")


def test_pads_need_a_drum_rack():
    rack = Rack.instrument("PD1", Layout(Slot("Cutoff")))
    try:
        rack.pad("KICK", 36, Engine("OriginalSimpler"))
    except ValueError as e:
        assert "drum rack" in str(e)
    else:
        raise AssertionError("an instrument rack has no pads")


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


def test_sample_retargets_both_filerefs():
    from patchbay import samples
    wav = _a_wav(SCRATCH)

    rack = Rack.instrument("SR", Layout(Slot("Instrument"), Slot("Filter"))).chain(
        "S", Engine("OriginalSimpler").sample(wav))

    device = find.devices(next(find.preset(rack.build()).iter("BranchPresets"))[0])[0]
    got = samples.targets(device)

    # S7: TWO FileRefs per sample, and in the donor they point at different
    # files. Both must move, or the provenance ref still names the old one.
    assert len(got) == 2, "the live ref and the provenance ref"
    assert set(got) == {wav.resolve().as_posix()}, "both, to the same file"
    assert all("/" in p and "\\" not in p for p in got), "Live writes posix"


def test_sample_refuses_a_missing_file():
    try:
        Engine("OriginalSimpler").sample("no/such/file.wav")
    except FileNotFoundError:
        return
    raise AssertionError("a missing sample loads offline, so it must refuse")


def test_sample_refuses_a_device_with_no_sampleref():
    wav = _a_wav(SCRATCH)

    rack = Rack.instrument("X", Layout(Slot("Instrument"))).chain(
        "FM", Engine("Operator").sample(wav))
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

    kit = patchbayground.DR1
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
    slot = patchbayground.PB.character.number

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

    slot = patchbayground.PB.filter.number
    for rack in patchbayground.RACKS:
        if rack.layout is not patchbayground.PB:
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

    slot = patchbayground.PB.release.number
    found = set()
    for rack in patchbayground.RACKS:
        if rack.layout is not patchbayground.PB:
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

    A digest rather than the facts themselves: DR1 alone is 178,960 facts,
    and a hash per rack fits in a file whose git diff is readable. When one
    fails, build the rack before and after and run `patchbay diff` for the
    detail.

    This also catches a hazard nothing else does. Skeleton and donor
    selection reads `donors/` and `racks/` by name, so adding a file can
    silently rebuild every rack. That shows up here as six failures.

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

    # The per-track strip instances are the same six racks under 46 names,
    # so digesting them costs half the suite's runtime and proves nothing a
    # digest of EQC does not already prove.
    instances = {r.name for r in patchbayground.STRIP_INSTANCES}
    built = {rack.name: digest(rack) for rack in patchbayground.RACKS
             if rack.name not in instances}

    if os.environ.get("PATCHBAY_REGOLD"):
        GOLDEN.write_text(
            "".join(f"{n} {built[n]}\n" for n in sorted(built)), newline="\n")
        return

    golden = dict(line.split() for line in
                  GOLDEN.read_text().splitlines() if line.strip())

    for name, want in sorted(golden.items()):
        # DR1 needs samples/, which is never committed, so it is absent on a
        # machine that has the repo and not the audio. The other five are not.
        if name == "DR1" and name not in built:
            continue
        assert name in built, f"{name} did not build"
        assert built[name] == want, (
            f"{name} changed. If that was intended, rebuild the goldens; "
            f"if not, `patchbay diff` it against a build from before.")


def test_a_device_node_carries_its_own_id():
    """Q9's second id rule, and it cost a Live check to find.

    A device inside `AbletonDevicePreset/Device` is a list member, and Live
    refuses the WHOLE document if one lacks an Id:

        Exception: Not all list members have Ids.
        The document "..." is corrupt and cannot be loaded.

    48 of 56 donors carried no Id, every one of them harvested out of a
    `.als`, where the device is a member of the track's `Devices` instead.
    Nothing caught it: ids were unique, every mapping resolved, and
    `patchbay check` passed.
    """
    g = Layout(Slot("Effect", selects=True), Slot("Cutoff"))
    rack = (Rack.audio_effect("K3", g)
            .chain("AutoFilter", Engine("AutoFilter").drives(g.cutoff, "Cutoff"))
            .chain("Echo", Engine("Echo")))
    for branch in find.branches(find.preset(rack.build())):
        for dev in find.devices(branch):
            assert dev.get("Id") is not None, f"<{dev.tag}> has no Id"


def test_a_device_with_no_id_is_refused_before_it_is_written():
    """Fail loudly. This one reached a file and a person before it was caught."""
    g = Layout(Slot("Effect", selects=True))
    root = Rack.audio_effect("X", g).chain("A", Engine("Echo")).build()
    dev = find.devices(find.branches(find.preset(root))[0])[0]
    del dev.attrib["Id"]
    try:
        clone.assert_loadable(root)
    except ValueError as e:
        assert "Not all list members have Ids" in str(e)
    else:
        raise AssertionError("a document Live refuses must not pass the guard")


def test_a_bipolar_binding_opens_off_centre_or_not_at_all():
    """A macro at 0 drives its target to the BOTTOM of the range.

    Harmless where the bottom is the neutral value - off, dry, silent - and
    not harmless where the parameter is bipolar. MFX1 shipped with
    MidiPitcher over its native -128..128 and macro 2 at 0, so every note
    arrived 128 semitones down and the rack made no sound at all (S2a).

    So: a mapping whose range crosses zero must have its macro placed. What
    the right position IS cannot be checked here - that is the spec's call -
    but zero on a bipolar parameter is never it.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    bad = []
    for rack in patchbayground.RACKS:
        root = rack.build()
        for m in mappings.find(root):
            if not m["macro"]:
                continue
            param = m["element"].getparent()
            rng = param.find("MidiControllerRange")
            if rng is None:
                continue
            lo = float(rng.find("Min").get("Value"))
            hi = float(rng.find("Max").get("Value"))
            if not (lo < 0.0 < hi):
                continue
            owner = mappings._owning_rack(param)
            macro = find.macro(owner, m["macro"])
            at = float(macro.find("Manual").get("Value"))
            if at == 0.0:
                bad.append(f"{rack.name} macro {m['macro']} -> {m['target']} "
                           f"({lo:g}..{hi:g}) opens at {lo:g}")
    assert not bad, (
        "a bipolar parameter driven from a macro at 0 sits at its minimum: "
        + "; ".join(bad))


def _kit_with_return(**kw):
    g = Layout(Slot("Tune"), Slot("Verb"))
    return g, (Rack.drum("K", g)
               .pad("KICK", 36, Engine("DrumCell"), sends={"verb": 0.35})
               .pad("SNARE", 38, Engine("DrumCell"))
               .ret("verb", Engine("Reverb")))


def test_a_return_chain_is_an_audio_effect_branch_whatever_the_parent():
    """S9: `ReturnBranchPresets` is a sibling of `BranchPresets`, and its
    members are `AudioEffectBranchPreset` even inside a drum rack."""
    _, kit = _kit_with_return()
    preset = find.preset(kit.build())
    rets = find.return_branches(preset)
    assert [b.tag for b in rets] == ["AudioEffectBranchPreset"]
    assert [b.get("Id") for b in rets] == ["0"]
    assert [d.tag for d in find.devices(rets[0])] == ["Reverb"]


def test_every_chain_gets_a_send_per_return():
    """Live seeds a send on every chain the moment a return appears, at the
    silent floor, and `Index` is positional. A chain that names no level
    still carries the entry (S9)."""
    _, kit = _kit_with_return()
    preset = find.preset(kit.build())
    levels = {}
    for branch in find.branches(preset) + find.return_branches(preset):
        infos = list(next(branch.iter("SendInfos")))
        assert [i.find("Index").get("Value") for i in infos] == ["0"]
        levels[branch.find("Name").get("Value")] = (
            infos[0].find("Send/Manual").get("Value"))
    assert levels["KICK"] == "0.35"
    assert levels["SNARE"] == str(dsl.SEND_FLOOR)
    assert levels["verb"] == str(dsl.SEND_FLOOR)


def test_a_send_to_a_return_that_does_not_exist_is_refused():
    g = Layout(Slot("Tune"), Slot("Verb"))
    kit = (Rack.drum("K", g)
           .pad("KICK", 36, Engine("DrumCell"), sends={"nope": 0.5})
           .ret("verb", Engine("Reverb")))
    try:
        kit.build()
    except ValueError as e:
        assert "not a return" in str(e)
    else:
        raise AssertionError("a send naming no return must be refused")


def test_a_send_carries_a_value_and_no_mapping():
    """Q23: Live ignores a macro written onto a send.

    The element is shaped exactly like a mappable parameter, the mapping
    resolves, and turning the knob in Live 12.4.3 left the send at -inf. So
    the DSL writes levels and refuses to pretend a knob can sweep them.
    """
    _, kit = _kit_with_return()
    preset = find.preset(kit.build())
    for branch in find.branches(preset):
        for info in branch.iter("AudioBranchSendInfo"):
            assert info.find("Send/KeyMidi") is None, (
                "a mapping on a send resolves and moves nothing; see Q23")
    dev = find.rack_device(preset)
    assert dev.find("AreSendsVisible").get("Value") == "true", (
        "the send column is where a player sets these by hand")


def test_a_nested_rack_may_be_driven_by_nothing():
    """`chaining()` is the identity default; `unchained()` is not the same thing.

    A return's effects answer their own macros. Chaining them to the outer
    rack by default would write a mapping nobody asked for, which is what
    extraction used to emit for every return.
    """
    inner_layout = Layout(Slot("Tune"))
    inner = Rack.audio_effect("FX", inner_layout).chain(
        "verb", Engine("Reverb").drives(inner_layout.tune, "DecayTime"))

    g = Layout(Slot("Tune"))
    kit = Rack.drum("K", g).pad("KICK", 36, Engine("DrumCell")).ret(
        "verb", inner.unchained())
    branch = find.return_branches(find.preset(kit.build()))[0]
    outer_driven = [m for m in mappings.find(branch)
                    if m["target"].startswith("MacroControls.")]
    assert outer_driven == []


def test_a_chain_may_hold_several_devices_in_series():
    """The channel strip shape: one chain, several devices, one macro set.

    Every device is a member of `DevicePresets` and numbers with the signal
    chain, while each device is still member 0 of its own holder. Both Ids
    are the Q9 rule one level apart.
    """
    g = Layout(Slot("Lo"), Slot("Gain"))
    rack = Rack.audio_effect("EQC", g).chain(
        "strip",
        Engine("ChannelEq").drives(g.lo, "LowShelfGain")
        .then(Engine("StereoGain").drives(g.gain, "Gain")))
    root = rack.build()
    branch = find.branches(find.preset(root))[0]

    assert [d.tag for d in find.devices(branch)] == ["ChannelEq", "StereoGain"]
    assert [w.get("Id") for w in branch.find("DevicePresets")] == ["0", "1"]
    assert all(d.get("Id") == "0" for d in find.devices(branch))

    got = {(m["macro"], m["target"]) for m in mappings.find(branch)}
    assert got == {(1, "LowShelfGain"), (2, "Gain")}


def test_a_zone_inside_a_series_is_refused():
    """A chain has one position on the selector, however many devices it holds."""
    g = Layout(Slot("Lo"))
    try:
        Engine("ChannelEq").zone(0, 63).then(Engine("StereoGain"))
    except ValueError as e:
        assert "one zone" in str(e)
    else:
        raise AssertionError("a per-device zone in a series must be refused")


def test_a_placed_device_does_not_inherit_the_donor_rack_mappings():
    """A donor is a device cut out of somebody's rack, mappings included.

    `Compressor2.adg` carried five, on Threshold, Ratio, Gain, DryWet and
    On, all pointing at macro 4 of a rack that no longer exists. Placed
    unchanged, one knob of the new rack moved all five. Same shape as the
    donor's Drift modulation row: a donor is for the parameter list, never
    for anybody's decisions.

    `AutoFilter` carries the two this test rides on now. The Compressor2
    donor was re-harvested for Q19 and its mappings went with the rename.
    """
    from patchbay.library import Library

    donor = Library.default().device("AutoFilter")
    assert mappings.find(donor.instance()), (
        "this test is pointless if the donor carries no mappings")

    g = Layout(Slot("Cutoff"))
    rack = Rack.audio_effect("C", g).chain(
        "strip", Engine("AutoFilter").drives(g.cutoff, "Cutoff"))
    branch = find.branches(find.preset(rack.build()))[0]
    assert {(m["macro"], m["target"]) for m in mappings.find(branch)} == {
        (1, "Cutoff")}


def test_a_midi_effect_rack_builds_with_its_own_branch_tag():
    """MidiEffectGroupDevice holds MidiEffectBranchPreset, per donors/AM_midi.adg."""
    g = Layout(Slot("Rate"))
    rack = Rack.midi_effect("ARP", g).chain(
        "strip", Engine("MidiArpeggiator").drives(g.rate, "SyncedRate"))
    preset = find.preset(rack.build())
    assert find.rack_device(preset).tag == "MidiEffectGroupDevice"
    assert [b.tag for b in find.branches(preset)] == ["MidiEffectBranchPreset"]


def test_an_instrument_rack_is_refused_in_a_midi_effect_chain():
    g = Layout(Slot("Cutoff"))
    try:
        Rack.midi_effect("M", g).chain("SUB", Rack.instrument("I", g))
    except ValueError as e:
        assert "midi effect chain" in str(e)
    else:
        raise AssertionError("Live refuses this preset; so must we")


def test_the_sidechain_is_configured_but_never_sourced():
    """C4: everything but the source, which no device preset carries (Q18).

    The enable is asserted next to the band, for the Q16 reason: a
    sidechain EQ that is set and switched off is a knob that moves nothing.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    comp = next(patchbayground.EQC.build().iter("Compressor2"))
    assert find.param(comp, "SideChain/OnOff").find("Manual").get("Value") == "true"
    # Flat, not nested: Live renamed these between 12.2 and 12.4.3, and the
    # first donor predated the rename. Q19.
    assert find.param(comp, "SideChainEq_On").find("Manual").get("Value") == "true"
    assert find.param(comp, "SideChainEq_Freq").find("Manual").get("Value") == "100"
    assert find.param(comp, "SideChainEq_Mode").find("Manual").get("Value") == "5", (
        "5 is the low-pass sidechain band, Q19")

    target = find.setting(comp, "SideChain/RoutedInput/Routable/Target")
    assert target.get("Value") == "AudioIn/None", (
        "a source in a .adg would contradict Q18; if this moved, re-read it")


def test_a_placed_device_carries_no_blank_int64_field():
    """The second Set-form difference, and it hid behind the first.

    A device lifted out of a `.als` brings a LastPresetRef whose FileRef
    has `OriginalFileSize` and `OriginalCrc` blank. A `.als` accepts that
    and a `.adg` does not:

        Exception: Unexpected value for int64 node:
        The document "..." is corrupt and cannot be loaded.

    42 of 54 donors carry it. It survived the Id fix because our own diff
    hides `/LastPresetRef/` by default, so no spike pair ever showed it.
    """
    g = Layout(Slot("Effect", selects=True), Slot("Cutoff"))
    rack = (Rack.audio_effect("K3", g)
            .chain("AutoFilter", Engine("AutoFilter").drives(g.cutoff, "Cutoff"))
            .chain("Eq8", Engine("Eq8"))
            .chain("Echo", Engine("Echo")))
    assert clone.empty_int64_fields(rack.build()) == []


def test_a_blank_int64_field_is_refused_before_it_is_written():
    """Fail loudly, same as the missing Id. This one reached a person too."""
    g = Layout(Slot("Effect", selects=True))
    root = Rack.audio_effect("X", g).chain("A", Engine("Echo")).build()
    ref = next(root.iter("FileRef"))
    ref.find("OriginalFileSize").set("Value", "")
    try:
        clone.assert_loadable(root)
    except ValueError as e:
        assert "Unexpected value for int64 node" in str(e)
    else:
        raise AssertionError("a document Live refuses must not pass the guard")


def test_a_bound_modulator_is_switched_on():
    """H6 and Q16 are one defect: a mapping that resolves and reaches nothing.

    Operator ships with `Lfo/LfoOn` false and `Filter/LfoOn` false, Drift
    with a modulation row pointed somewhere else. In every case the macro
    moved, the KeyMidi was valid, and only ears found it. So the enable is
    asserted next to the binding that needs it.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    for rack in patchbayground.RACKS:
        root = rack.build()
        for op in root.iter("Operator"):
            if find.param(op, "Lfo/LfoAmount") is None:
                continue
            if not params.is_mapped(find.param(op, "Lfo/LfoAmount")):
                continue
            for gate in ("Lfo/LfoOn", "Filter/LfoOn"):
                assert params.raw_value(find.param(op, gate)) == "true", (
                    f"{rack.name}: Lfo/LfoAmount is mapped with {gate} off, "
                    f"so the knob moves and nothing does")
        for drift in root.iter("Drift"):
            if not params.is_mapped(find.param(drift, "Lfo_Amount")):
                continue
            assert drift.find("ModulationMatrix_Target1").get("Value") == "6", (
                f"{rack.name}: Drift's LFO is bound but routed nowhere useful")
        # Q20. Scale Awareness makes the Set's scale win over the device's,
        # so a bound InternalScale under it selects a scale nothing uses.
        for scale in root.iter("MidiScale"):
            if not params.is_mapped(find.param(scale, "InternalScale")):
                continue
            got = params.raw_value(find.param(scale, "UseCurrentScale"))
            assert got == "false", (
                f"{rack.name}: InternalScale is mapped with Scale Awareness "
                f"on, so the Set's scale wins and the knob selects nothing")


def test_glide_is_only_enabled_where_a_rack_spends_it():
    """The role owns the enable, not the engine profile.

    PD1 and VA1 hold the same Operator profile and spend slot 6 on attack.
    Portamento on there would smear every pad they play.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    on = {}
    for rack in patchbayground.RACKS:
        for op in rack.build().iter("Operator"):
            got = params.raw_value(find.param(op, "Globals/PortamentoOn"))
            on.setdefault(rack.name, set()).add(got)
    assert on.get("LD1") == {"true"}, "LD1 spends glide"
    for name in ("PD1", "VA1"):
        assert on.get(name) == {"false"}, f"{name} does not spend glide"


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
            got = params.value(find.macro(dev, rack.layout[slot].number))
            assert got, f"{rack.name}: {slot} opens at {got}"


def test_one_slot_can_drive_several_parameters():
    """Meld is two engines behind one device; binding A alone filters half.

    Gated in Live 12.4.3 as C2: Macro 3 moved the A side and left B wide
    open, audibly, on a rack where every id, every mapping and every range
    checked out.
    """
    g = Layout(Slot("Engine", selects=True), Slot("Filter"))
    rack = Rack.instrument("X", g).chain("M", Engine("InstrumentMeld").drives(
        g.filter, "MeldVoice_EngineA_Filter_Frequency",
        "MeldVoice_EngineB_Filter_Frequency", over=Range(30.0, 18500.0, "Hz")))
    root = rack.build()
    on_two = sorted(m["target"] for m in mappings.find(root) if m["macro"] == 2)
    assert on_two == ["MeldVoice_EngineA_Filter_Frequency",
                      "MeldVoice_EngineB_Filter_Frequency"]


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
    g = Layout(Slot("Engine", label="> Engine", selects=True), Slot("Filter"))
    rack = (Rack.instrument("X", g)
            .label(g.filter, "Filter + Res")
            .chain("A", Engine("Operator").drives(g.filter, "Filter/Frequency")))
    assert _labels(rack) == ["> Engine", "Filter + Res"]
    # The slot did not move: it is still the second macro, and still `filter`.
    assert g.filter.number == 2


def test_two_racks_on_one_layout_may_label_differently():
    g = Layout(Slot("Engine", selects=True), Slot("Drive"))
    voice = Engine("OriginalSimpler").drives(
        g.drive, "Filter/Slot/Value/SimplerFilter/Drive")
    a = Rack.instrument("KICK", g).label(g.drive, "Drive + Snap").chain("S", voice)
    b = Rack.instrument("HAT", g).chain("S", voice)
    assert _labels(a) == ["Engine", "Drive + Snap"]
    assert _labels(b) == ["Engine", "Drive"]


def test_a_slot_that_does_not_exist_is_refused_at_the_layout():
    """One step earlier than it used to be: a slot is a value, not a string."""
    g = Layout(Slot("Engine", selects=True), Slot("Filter"))
    try:
        g.cutoff
    except AttributeError as e:
        assert "cutoff" in str(e) and "filter" in str(e)
    else:
        raise AssertionError("a slot this layout does not have must not resolve")


def test_a_position_off_the_macro_scale_is_refused():
    g = Layout(Slot("Engine", selects=True), Slot("Volume"))
    rack = Rack.instrument("X", g)
    for bad in (-1, 128, 200):
        try:
            rack.start(g.volume, bad)
        except ValueError:
            pass
        else:
            assert False, f"{bad} accepted as a macro position"
        try:
            Layout(Slot("Volume", start=bad))
        except ValueError:
            continue
        assert False, f"{bad} accepted as an opening position"


def test_start_is_not_written_for_a_slot_nothing_drives():
    """A knob parked somewhere meaningful that moves nothing reads as a bug."""
    g = Layout(Slot("Engine", selects=True), Slot("Filter", start=127),
               Slot("Volume", start=127))
    rack = Rack.instrument("X", g).chain(
        "A", Engine("Operator").drives(g.volume, "Globals/Volume"))
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


def test_a_rack_lifted_out_of_a_set_matches_its_preset_twin():
    """T6c, gated on the Q9 pair.

    `racks/q9_b.als` is a Set holding one rack; `racks/q9_a.adg` is that
    same rack dragged out to the browser, so both were written by Live and
    the only difference between them is the container. Lifting the Set form
    and rebuilding it has to land on the preset form's structure.

    Not fact-exact, and cannot be: the two files were saved a minute apart
    and a knob moved between them, which is a value rather than a shape.
    """
    from patchbay import extract

    lifted = extract.racks_in_set(io.load(RACKS / "q9_b.als"))
    assert [name for name, _ in lifted] == ["1-Audio"]

    ns = {}
    exec(compile(extract.source(RACKS / "q9_b.als"), "q9_b.als", "exec"), ns)
    rebuilt = ns["RACKS"][0].build()

    want = _structure(io.load(RACKS / "q9_a.adg"))
    got = _structure(rebuilt)
    assert want[0] == got[0], "chains differ"
    assert want[1] == got[1], "mappings differ"
    assert want[2] == got[2], "macro positions differ"
    assert want[3] == got[3], "macro labels differ"

    # And the lifted tree is loadable in its own right, which is the whole
    # point of preset form: the three donor repairs apply to a Set exactly
    # as they do to a donor.
    clone.assert_loadable(rebuilt)


def test_extract_round_trips_structure():
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

    # Same reason as the goldens: a strip instance is EQC under another
    # name, and round tripping 46 of them is half this suite's runtime.
    instances = {r.name for r in patchbayground.STRIP_INSTANCES}
    for rack in patchbayground.RACKS:
        if rack.name in instances:
            continue
        original = rack.build()
        out = SCRATCH / f"{rack.name}.extract.adg"
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


# --- the surface itself ---------------------------------------------------

def test_a_slot_driven_twice_accumulates():
    """A per-slot call reads as a second mapping, and behaves as one.

    Which is what the Meld case wants: two synthesis engines behind one
    device, every A path with a B twin, one knob.
    """
    g = Layout(Slot("Engine", selects=True), Slot("Filter"))
    meld = (Engine("InstrumentMeld")
            .drives(g.filter, "MeldVoice_EngineA_Filter_Frequency")
            .drives(g.filter, "MeldVoice_EngineB_Filter_Frequency"))
    rack = Rack.instrument("X", g).chain("M", meld)

    on_two = [m["target"] for m in mappings.find(rack.build()) if m["macro"] == 2]
    assert on_two == ["MeldVoice_EngineA_Filter_Frequency",
                      "MeldVoice_EngineB_Filter_Frequency"]


def test_a_range_states_its_unit_and_does_its_own_arithmetic():
    """Release is one interval in two spellings, seconds and milliseconds."""
    release = Range(0.01, 20.0, "s")
    assert release.scaled(1000.0) == Range(10.0, 20000.0, "s")
    assert release.capped(5.0).as_tuple() == (0.01, 5.0)


def test_deriving_a_layout_carries_what_was_not_named():
    """The failure this exists to stop: a start silently dropped.

    Rebuilding the slot list by hand to move the selector loses the starts
    and the labels with it, which loads as a rack whose filter is shut and
    whose volume is down. It happened once, while testing something else.
    """
    pb = Layout(Slot("Instrument", label="Engine", selects=True),
                Slot("Sound"),
                Slot("Filter", start=127))
    pad = pb.deriving(selects=pb.sound,
                      relabel={pb.sound: "Sample", pb.instrument: None})

    assert pad.selector.display == "Sound"
    assert pad.sound.label == "Sample"
    assert pad.filter.start == 127, "the start survived a derivation"
    assert pad.instrument.label is None, "a relabel of None clears one"
    assert [s.display for s in pad] == [s.display for s in pb]
    assert pb.selector.display == "Instrument", "the original did not move"


def test_a_layout_refuses_two_slots_that_mean_one_python_name():
    """`Send A` answers to `send_a`, so `Send-A` beside it is unreachable."""
    try:
        Layout(Slot("Send A"), Slot("Send-A"))
    except ValueError as e:
        assert "send_a" in str(e)
    else:
        raise AssertionError("two slots collided on one key and were accepted")


def test_a_layout_has_one_chain_selector():
    try:
        Layout(Slot("A", selects=True), Slot("B", selects=True))
    except ValueError as e:
        assert "chain selector" in str(e)
    else:
        raise AssertionError("two slots claimed the selector and were accepted")


def test_an_engine_profile_is_a_value_and_does_not_mutate():
    """Two racks may hold one profile; extending it in one cannot reach the other."""
    g = Layout(Slot("Engine", selects=True), Slot("Filter"))
    base = Engine("OriginalSimpler").drives(
        g.filter, "Filter/Slot/Value/SimplerFilter/Freq")
    wider = base.drives(g.filter, "Filter/Slot/Value/SimplerFilter/Res")

    assert len(base._drives) == 1 and len(wider._drives) == 2
    assert Rack.instrument("A", g).chain("S", base)._chains[0].content is base


def test_a_rack_builder_returns_a_new_rack():
    """Same reason: a sub-rack in two racks, and neither build reaching the other."""
    g = Layout(Slot("Engine", selects=True), Slot("Filter"))
    empty = Rack.instrument("X", g)
    one = empty.chain("A", Engine("Operator").drives(g.filter, "Filter/Frequency"))
    assert len(empty.engines) == 0 and len(one.engines) == 1


def test_a_wildcard_slot_reaches_only_the_engines_that_offer_the_role():
    """`spends` states the role once; an engine without it leaves the slot empty."""
    g = Layout(Slot("Engine", selects=True), Slot("Character"))
    offering = Engine("OriginalSimpler").offers(
        "attack", "VolumeAndPan/Envelope/AttackTime")
    silent = Engine("OriginalSimpler").offers("glide", "Globals/PortamentoTime")
    rack = (Rack.instrument("X", g)
            .spends(g.character, "attack")
            .chain("A", offering)
            .chain("B", silent))

    on_two = [m["target"] for m in mappings.find(rack.build()) if m["macro"] == 2]
    assert on_two == ["AttackTime"], "the leaf, as mappings.find reports it"


DRIFT_ROW = (("ModulationMatrix_Source1", 2),      # the LFO
             ("ModulationMatrix_Target1", 6),      # LP Frequency
             ("ModulationMatrix_Amount1", 1.0))


def _drift_rack():
    g = Layout(Slot("Engine", selects=True), Slot("Movement"))
    d = Engine("Drift").drives(g.movement, "Lfo_Amount")
    for path, val in DRIFT_ROW:
        d = d.sets(path, val)
    return Rack.instrument("X", g).chain("D", d)


def test_a_setting_is_written_where_no_mapping_can_reach():
    """Q16. Drift's routing has no `Manual`, so nothing can drive it.

    `ModulationMatrix_Target1` is a bare `<Tag Value="6" />`. A macro bound
    to `Lfo_Amount` resolved, wrote a valid KeyMidi and moved nothing,
    because no row routed the LFO anywhere.
    """
    device = next(_drift_rack().build().iter("Drift"))
    assert device.find("ModulationMatrix_Source1").get("Value") == "2"
    assert device.find("ModulationMatrix_Target1").get("Value") == "6"
    assert find.param(device, "ModulationMatrix_Target1") is None, (
        "a routing selector is not a parameter and must not look like one")
    assert "ModulationMatrix_Target1" in find.settings(device)


def test_sets_reaches_a_parameter_as_well_as_a_setting():
    """One verb: the caller says what the control is worth, not where it lives."""
    device = next(_drift_rack().build().iter("Drift"))
    assert params.value(find.param(device, "ModulationMatrix_Amount1")) == 1.0


def test_a_written_row_replaces_the_donors_own():
    """The donor routes something to the HIGH-PASS at 80%, and nobody asked.

    Donors are for the parameter list and its native ranges. A value
    inherited by accident is still a value nobody wrote.
    """
    from patchbay.library import Library
    donor = Library.default().instance("Drift")
    assert donor.find("ModulationMatrix_Target1").get("Value") == "8"
    device = next(_drift_rack().build().iter("Drift"))
    assert device.find("ModulationMatrix_Target1").get("Value") == "6"


def test_setting_one_control_twice_replaces():
    """Unlike `drives`. Two values for one control is an edit, not a second one."""
    e = Engine("Drift").sets("ModulationMatrix_Target1", 8).sets(
        "ModulationMatrix_Target1", 6)
    assert e._sets == (("ModulationMatrix_Target1", 6),)


def test_an_unknown_control_is_refused_with_a_suggestion():
    g = Layout(Slot("Engine", selects=True))
    rack = Rack.instrument("X", g).chain(
        "D", Engine("Drift").sets("ModulationMatrix_Targt1", 6))
    try:
        rack.build()
    except KeyError as e:
        assert "ModulationMatrix_Target1" in str(e), "the near miss is offered"
    else:
        raise AssertionError("a mistyped control must not reach a file")


def test_spending_a_role_names_the_knob_after_it():
    g = Layout(Slot("Engine", selects=True), Slot("Character"))
    voice = Engine("OriginalSimpler").offers(
        "attack", "VolumeAndPan/Envelope/AttackTime")
    rack = Rack.instrument("X", g).spends(g.character, "attack").chain("A", voice)
    assert _labels(rack) == ["Engine", "Attack"]


def test_an_earlier_harvest_path_wins_a_tie():
    """`racks/` is evidence, and a probe ties the donor it was cut from.

    Decided by filename order instead, `racks/q17_a.adg` took Operator from
    `racks/s1_source.adg` because q sorts first, and every rack in the build
    arrived with glide on and its filter at 30 Hz. donors/ now breaks the
    tie, and a fuller copy still wins - which is how a 12.4.3 MidiScale out
    of `racks/` replaces a donor harvested before Scale Awareness existed.
    """
    from patchbay.library import Library
    lib = Library.default()
    assert lib.get("Operator").source == "Operator.adg"
    assert lib.get("MidiScale").source.startswith("q20_"), (
        "a fuller copy still wins on parameter count")
    assert "InternalScale" in lib.get("MidiScale").params


def test_a_sampler_with_no_sample_declared_carries_no_sample_part():
    """A donor names no file, and Live reads the leftover part as MISSING.

    Checked in Live 12.4.3: PD1's Sample chain, built from a harvested
    OriginalSimpler, loaded with a missing-sample warning rather than as an
    empty sampler. `Engine.sample` refuses a path that is not a file, so a
    blank path in the output means nobody ever named one.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    for rack in patchbayground.RACKS:
        for part in rack.build().iter("MultiSamplePart"):
            ref = part.find("SampleRef/FileRef/Path")
            assert ref is not None and ref.get("Value"), (
                f"{rack.name}: a sample part with no path is a missing "
                f"sample in Live, not an empty sampler")


def test_an_inverted_range_stays_inverted():
    """Q26, and it looks like a typo, which is why it is asserted here.

    EQC's Duck rises as the compressor's threshold falls. Live 12.4.3
    honours `Min > Max` - checked on `build/EQC.adg` - and its own UI cannot
    write one, so nothing outside this repo will ever produce the shape.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    comp = next(patchbayground.EQC.build().iter("Compressor2"))
    r = find.param(comp, "Threshold").find("MidiControllerRange")
    lo = float(r.find("Min").get("Value"))
    hi = float(r.find("Max").get("Value"))
    assert lo > hi, "Duck drives the threshold DOWNWARD as the knob rises"


def test_the_skeletons_come_from_donors_and_not_from_evidence():
    """Adding a file to `racks/` must not rebuild every rack.

    It did, twice in one session. `racks/q23_a.adg` became the drum skeleton
    on nothing but sorting first, and gave all eight DR1 pads a send at
    0.339 that no spec declared; it also became the return template, which
    moved a colour. Both are pinned in `donors/` now, and the fallback scan
    stays for a machine that has neither.
    """
    from patchbay.dsl import Rack

    g = Layout(Slot("A"))
    assert Rack.drum("X", g)._find_skeleton().parent.name == "donors"
    rack = Rack.drum("X", g)
    rack._load_return_templates()
    send = rack._send_skeleton().find("Send")
    assert float(send.find("Manual").get("Value")) == dsl.SEND_FLOOR, (
        "a lifted template carries shape, never the value it was saved at")
    assert send.find("KeyMidi") is None, "nor anybody else's mapping"


def test_one_strip_instance_per_track_named_for_it():
    """PATCHBAYGROUND.md's naming rule, as a loop rather than six copies.

    PM1 is an audio track, so it takes the audio half of the strip and
    neither MIDI rack: 6 racks over 7 MIDI tracks plus 4 over PM1.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground
    from patchbay.dsl import RackKind

    names = [r.name for r in patchbayground.STRIP_INSTANCES]
    assert len(names) == 46 == len(set(names))
    assert "EQC_BS1" in names and "VOL1_PM1" in names
    assert not [n for n in names if n.startswith(("ARP1_PM1", "MFX1_PM1"))], (
        "a MIDI effect rack cannot go on an audio track")
    for inst in patchbayground.STRIP_INSTANCES:
        if inst.kind is RackKind.MIDI_EFFECT:
            continue
        assert inst.name.split("_")[1] in patchbayground.TRACKS


def test_a_named_layout_recovers_slot_names():
    """T6's tail: a spec the caller NAMES is not a guess.

    Extraction is positional by default because reading intent off a
    parameter path invents it. Passing a spec makes the name a second file's
    claim rather than the extractor's, and the rack still rebuilds fact for
    fact.
    """
    from patchbay import extract
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    root = Path(__file__).resolve().parent.parent
    spec = root / "examples" / "patchbayground.py"
    bs1 = next(r for r in patchbayground.RACKS if r.name == "BS1")
    out = SCRATCH / "BS1.named.adg"
    io.save(bs1.build(), out)

    positional = extract.source(out)
    assert "Slot('Macro 3'" in positional, "the default names nothing"

    named = extract.source(out, layout=spec)
    assert "Slot('Filter + Res'" in named
    assert ".drives(bs1_layout.filter_res," in named, (
        "the reference must be the identifier Layout will build")

    ns: dict = {}
    exec(compile(named, "<named>", "exec"), ns)
    rebuilt = SCRATCH / "BS1.named.rebuilt.adg"
    io.save(ns["RACKS"][0].build(), rebuilt)
    changed, lost, invented = diff.compare(out, rebuilt, show_all=True)
    assert not (changed or lost or invented), "naming a slot moved a fact"


def test_a_donor_keeps_lives_own_installed_paths():
    """Q27. Harvest scrubs a user's kick and must not scrub a device's IR.

    `RelativePathType 7` is Live's installed content. Scrubbing it shipped
    a Hybrid Reverb that loaded with "Media files are missing" in both DR1
    returns, and nothing in the file said so.
    """
    from patchbay.library import Library

    hybrid = Library.default().instance("Hybrid")
    refs = [r for r in hybrid.iter("FileRef")
            if (r.find("RelativePathType") is not None
                and r.find("RelativePathType").get("Value") == "7")]
    assert refs, "the Hybrid donor carries no installed-content reference"
    for ref in refs:
        assert ref.find("RelativePath").get("Value"), (
            "the relative path is the one Live resolves for type 7; the "
            "absolute one is the macOS path Ableton ships to both platforms")


def test_a_send_is_written_on_the_chain_that_owns_the_return():
    """Rule 4 again, in a place the rule did not name.

    `branch.iter("SendInfos")` is a descendant search, and a chain holding a
    nested rack lists `DevicePresets` before `MixerPreset`, so the first hit
    belongs to the INNER rack's first chain. Every DR1 send landed there:
    the pads showed no send column, and `sending` mapped macro 5 of a rack
    no kit knob reaches. Checked in Live 12.4.3 by a knob that moved
    nothing.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    import patchbayground

    if patchbayground.DR1 is None:
        return  # samples/ is absent, as on any machine without the audio

    root = patchbayground.DR1.build()
    preset = find.preset(root)
    pads = find.branches(preset)
    assert len(pads) == 8
    for pad in pads:
        own = pad.find("MixerPreset")
        infos = list(next(own.iter("SendInfos")))
        assert len(infos) == 2, "one send per return, on the PAD's own mixer"
        ccs = [i.find("Send/KeyMidi/NoteOrController").get("Value")
               for i in infos]
        assert ccs == ["4", "5"], "kit macros 5 and 6, in return order"

    # The inner rack has no returns of its own, so it has no sends at all.
    inner = next(pads[0].iter("GroupDevicePreset"))
    for branch in find.branches(inner):
        mixer = branch.find("MixerPreset")
        assert not list(next(mixer.iter("SendInfos"))), (
            "a rack with no returns writes no sends")

    # A return's send to the other return is Live's own seeding and belongs
    # to nobody: sweeping it would feed the delay into the reverb.
    for ret in find.return_branches(preset):
        mixer = ret.find("MixerPreset")
        for info in next(mixer.iter("SendInfos")):
            assert info.find("Send/KeyMidi") is None


def test_build_writes_one_file_per_rack_and_nothing_else():
    """`build/` holds what a build produced, or it holds nothing useful.

    The suite used to write round-trip output there - 190 files named
    `X.extract.adg` and `X.extract.rebuilt.adg` beside 58 racks - and
    nothing told the two apart by name. Tests write to SCRATCH now, and
    `--clean` removes a rack that a rename left behind.
    """
    from patchbay import compile as compile_spec

    spec = Path(__file__).resolve().parent.parent / "examples" / "patchbayground.py"
    out = SCRATCH / "built"
    built = compile_spec.compile_spec(spec, out)
    assert sorted(p.name for p in out.iterdir()) == sorted(
        b.path.name for b in built), "a build writes racks and no scratch"

    stale = out / "RENAMED_AWAY.adg"
    stale.write_bytes(b"")
    compile_spec.compile_spec(spec, out, clean=True)
    assert not stale.exists(), "--clean drops what this build did not write"

    try:
        compile_spec.compile_spec(spec, out, only=["DR1"], clean=True)
    except compile_spec.SpecError:
        pass
    else:
        raise AssertionError("--clean beside --only would delete the rest")


def test_the_send_slider_loses_20_db_per_halving():
    """Q8, measured: `racks/q8_half.adg` and `racks/q8_quarter.adg`.

    Neither guess was right. Half the travel is not 0.5 (linear in
    amplitude) and it is not -35 dB (linear in dB over -70..0). It is
    -20 dB, and a quarter is -40 dB, so the stored value is the slider
    position raised to log2(10).
    """
    half = diff.flatten(io.load(RACKS / "q8_half.adg"))
    quarter = diff.flatten(io.load(RACKS / "q8_quarter.adg"))

    def first_send(facts):
        return float(next(v for k, v in facts.items()
                          if k.endswith("Send/Manual@Value")))

    assert abs(first_send(half) - 0.1) < 1e-6
    assert abs(first_send(quarter) - 0.01) < 1e-6
    assert abs(params.send_amplitude(0.5) - 0.1) < 1e-9
    assert abs(params.send_amplitude(0.25) - 0.01) < 1e-9
    assert abs(params.send_knob(0.1) - 0.5) < 1e-9
    assert params.send_amplitude(0.0) == params.SEND_FLOOR


def test_a_rack_placed_in_a_set_lifts_back_out_unchanged():
    """`live_set` and `extract` are one mapping read in both directions.

    Q9 gave preset form against Set form; this is the gate that keeps the
    two halves agreeing. It caught the branch mixer, whose TAG is the whole
    difference between the forms - `MixerDevice` in a Set,
    `AudioBranchMixerDevice` in a preset, and `MidiBranchMixerDevice` when
    the branch is a MIDI effect one.

    Skipped where Live is not installed: the Set-form templates come from
    Live's own factory content rather than from this repo.
    """
    from lxml import etree
    from patchbay import extract, live_set

    try:
        live_set.live_resources()
    except FileNotFoundError:
        return

    for name in ("EQC", "ARP1", "VA1"):
        src = Path(__file__).resolve().parent.parent / "build" / f"{name}.adg"
        if not src.exists():
            continue
        preset = io.load(src).find("GroupDevicePreset")
        placed = live_set.set_from_preset(preset, 0)
        wrap = etree.Element("Ableton")
        wrap.append(extract.preset_from_set(placed))
        a, b = diff.flatten(io.load(src)), diff.flatten(wrap)
        # `PresetRef` is where a preset records its own file identity, and
        # the wrapper a lift builds takes it from a donor. `patchbay diff`
        # hides it for the same reason.
        changed = {k: (a[k], b[k]) for k in set(a) & set(b)
                   if a[k] != b[k]
                   and not any(m in k for m in diff.PRESET_REF_MARKERS)}
        assert not changed, f"{name}: {list(changed)[:3]}"


def test_a_written_set_carries_a_send_per_return_on_every_track():
    """S9's rule one level up: a Set where the counts disagree is broken."""
    from patchbay import live_set

    try:
        live_set.live_resources()
    except FileNotFoundError:
        return

    src = Path(__file__).resolve().parent.parent / "build" / "EQC.adg"
    if not src.exists():
        return
    preset = io.load(src).find("GroupDevicePreset")
    root = live_set.build(
        [live_set.Track("T1", "midi", [preset]),
         live_set.Track("T2", "audio", [])],
        returns=["A", "B", "C"], tempo=132.0)

    tracks = list(root.find("LiveSet/Tracks"))
    assert [t.tag for t in tracks] == ["MidiTrack", "AudioTrack"] +         ["ReturnTrack"] * 3
    for track in tracks:
        sends = track.find("DeviceChain/Mixer/Sends")
        assert len(sends) == 3, "one send per return, on every track"
        ids = [s.get("Id") for s in sends]
        assert len(set(ids)) == len(ids), "sibling ids collide"
    assert next(root.iter("Tempo")).find("Manual").get("Value") == "132.0"


def test_a_set_hands_out_a_unique_pointee_id():
    """Live refuses a Set with a zero pointee id: "Invalid Pointee Id."

    A preset writes `Id="0"` on every `AutomationTarget`,
    `ModulationTarget` and `Pointee` - 28,214 of them in PATCHBAYGROUND -
    and that is correct for a `.adg` and invalid in a `.als`. Read off
    `racks/q9_b.als`, a Set Live saved: 267 pointees, none zero, no
    duplicates, `NextPointeeId` one above the highest.
    """
    from patchbay import live_set

    try:
        live_set.live_resources()
    except FileNotFoundError:
        return

    src = Path(__file__).resolve().parent.parent / "build" / "EQC.adg"
    if not src.exists():
        return
    preset = io.load(src).find("GroupDevicePreset")
    root = live_set.build([live_set.Track("T1", "midi", [preset])],
                          returns=["A"])

    seen = []
    for el in root.iter():
        if isinstance(el.tag, str) and live_set._is_pointee(el):
            seen.append(el.get("Id"))
    assert seen, "the Set carries no pointees at all"
    assert "0" not in seen, "a zero pointee id is what Live refuses"
    assert len(set(seen)) == len(seen), "pointee ids are unique document-wide"
    nxt = int(root.find("LiveSet/NextPointeeId").get("Value"))
    assert nxt > max(int(v) for v in seen), "NextPointeeId is the next FREE id"


def test_every_track_carries_one_clip_slot_per_scene():
    """Q36. Scene count comes from the skeleton, slot count from the track.

    The Set skeleton is the 8-Track Template, 8 scenes. The track templates
    are the Creating Tracks defaults, 1 slot each. Live reads slot i of
    every track without checking, so the mismatch is an access violation
    rather than a refusal, and four attempts crashed on it.

    A return track has an empty FreezeSequencer list and no MainSequencer
    one. That is what Live writes and it stays empty.
    """
    from patchbay import live_set

    try:
        live_set.live_resources()
    except FileNotFoundError:
        return

    root = live_set.build([live_set.Track("T1", "midi"),
                           live_set.Track("T2", "audio")],
                          returns=["A", "B"])
    scenes = len(root.find("LiveSet/Scenes"))
    assert scenes > 1, "the skeleton has to have scenes for this to bite"

    for track in root.find("LiveSet/Tracks"):
        name = track.find("Name/EffectiveName").get("Value")
        for holder in track.iter("ClipSlotList"):
            if track.tag == "ReturnTrack":
                assert len(holder) == 0, f"{name}: a return holds no clips"
                continue
            assert len(holder) == scenes, (
                f"{name}: {len(holder)} slots against {scenes} scenes")
            ids = [s.get("Id") for s in holder]
            assert len(set(ids)) == len(ids), f"{name}: sibling slot ids collide"


def test_a_set_form_branch_carries_nothing_the_template_lacks():
    """Q35. Preset-only children on a Set-form branch CRASH Live.

    `DocumentColorIndex` is preset form's name for what a Set calls
    `Color`, and `ZoneSettings` belongs on a MIDI effect and an instrument
    branch but not on a drum branch, whose note is in `BranchInfo`. Both
    were copied across because `_branch_from_preset` appended a tag the
    template lacked. Live did not refuse the file, it took an access
    violation while installing the document.
    """
    from patchbay import live_set

    try:
        live_set.live_resources()
    except FileNotFoundError:
        return

    root = Path(__file__).resolve().parent.parent
    for name in ("DR1", "PD1W", "EQC", "ARP1"):
        src = root / "build" / f"{name}.adg"
        if not src.exists():
            continue
        made = live_set.set_from_preset(
            io.load(src).find("GroupDevicePreset"), 0)
        branches = [el for el in made.iter()
                    if isinstance(el.tag, str) and el.tag.endswith("Branch")
                    and el.find("DeviceChain") is not None]
        assert branches, f"{name} converted to no branches at all"
        for branch in branches:
            kids = {k.tag for k in branch if isinstance(k.tag, str)}
            assert "DocumentColorIndex" not in kids, (
                f"{name}: a Set-form {branch.tag} has no DocumentColorIndex")
            if branch.tag == "DrumBranch":
                assert "ZoneSettings" not in kids, (
                    f"{name}: a Set-form DrumBranch has no ZoneSettings")
                assert "BranchInfo" in kids, (
                    f"{name}: a DrumBranch keeps BranchInfo, the pad's note")


def test_a_pointee_is_found_by_shape_not_by_a_list_of_tags():
    """Q34. `ControllerTargets.N` is a pointee and its NAME says nothing.

    Every MIDI track template carries 131 of them, so two tracks share 131
    ids and Live refuses the Set with `PointeeId 341 is used 8 times`. The
    tag matches no pointee naming convention, which is why Q31's rule let
    them through and why the rule is now the shape: an `Id` plus a lone
    `LockEnvelope` child.
    """
    from patchbay import live_set

    try:
        live_set.live_resources()
    except FileNotFoundError:
        return

    root = live_set.build([live_set.Track("T1", "midi"),
                           live_set.Track("T2", "midi")])

    seen = [el.get("Id") for el in root.iter()
            if isinstance(el.tag, str)
            and el.tag.startswith("ControllerTargets.")]
    assert len(seen) >= 262, f"a MIDI track carries 131 of these, got {len(seen)}"
    assert len(set(seen)) == len(seen), "two tracks share a controller target id"
    assert all(live_set._is_pointee(el) for el in root.iter()
               if isinstance(el.tag, str)
               and el.tag.startswith("ControllerTargets.")), (
        "the shape rule does not recognise ControllerTargets")


def test_a_track_routes_into_another_track_by_id():
    """Q33. `AudioOut/Track.<id>/TrackIn`, and the id is the ATTRIBUTE.

    Read off a Set saved by Live with T1 routed into PM1: PM1 sits third in
    `Tracks` and carries `Id="8"`, and the target names 8. So resolving a
    name to a POSITION would be right by accident here and wrong in
    general.
    """
    from patchbay import live_set

    try:
        live_set.live_resources()
    except FileNotFoundError:
        return

    root = live_set.build(
        [live_set.Track("T1", "midi", out="PM1"),
         live_set.Track("T2", "midi"),
         live_set.Track("PM1", "audio")],
        returns=["A"])

    tracks = {t.find("Name/EffectiveName").get("Value"): t
              for t in root.find("LiveSet/Tracks")}
    target = tracks["PM1"].get("Id")
    got = tracks["T1"].find("DeviceChain/AudioOutputRouting")
    assert got.find("Target").get("Value") == f"AudioOut/Track.{target}/TrackIn"
    assert got.find("UpperDisplayString").get("Value") == "PM1"
    assert got.find("LowerDisplayString").get("Value") == "Track In"
    for name in ("T2", "PM1"):
        other = tracks[name].find("DeviceChain/AudioOutputRouting/Target")
        assert other.get("Value") == "AudioOut/Main", f"{name} was rerouted"


def test_a_sidechain_source_is_filled_into_the_node_the_preset_carries():
    """Q33 and Q18 together: the `Routable` ships, the TARGET cannot.

    A preset carries the whole node pointing at `AudioIn/None`, so naming a
    source adds no element. It also must not switch the sidechain on: which
    is a different field and a different decision.
    """
    from patchbay import live_set

    try:
        live_set.live_resources()
    except FileNotFoundError:
        return

    src = Path(__file__).resolve().parent.parent / "build" / "EQC.adg"
    if not src.exists():
        return
    preset = io.load(src).find("GroupDevicePreset")
    before = [r.find("Target").get("Value")
              for r in preset.iter("Routable")
              if r.getparent().tag == "RoutedInput"]
    assert before == ["AudioIn/None"], "EQC's sidechain node moved"

    root = live_set.build(
        [live_set.Track("T1", "midi", [preset], sidechain="DR1"),
         live_set.Track("DR1", "midi")])

    tracks = {t.find("Name/EffectiveName").get("Value"): t
              for t in root.find("LiveSet/Tracks")}
    source = tracks["DR1"].get("Id")
    found = 0
    for chain in tracks["T1"].iter("SideChain"):
        node = chain.find("RoutedInput/Routable")
        if node is None:
            continue
        assert node.find("Target").get("Value") == (
            f"AudioIn/Track.{source}/PostFxOut")
        assert node.find("UpperDisplayString").get("Value") == "DR1"
        assert node.find("LowerDisplayString").get("Value") == "Post FX"
        found += 1
    assert found == 1, f"EQC holds one sidechain, found {found}"
    for chain in tracks["DR1"].iter("SideChain"):
        node = chain.find("RoutedInput/Routable")
        assert node is None or node.find("Target").get("Value") == "AudioIn/None"


def test_a_routing_target_that_is_not_a_track_is_refused():
    """Fail loudly: a typo would otherwise write a Set routed nowhere."""
    from patchbay import live_set

    try:
        live_set.live_resources()
    except FileNotFoundError:
        return

    for kwargs in ({"out": "PM2"}, {"sidechain": "PM2"}):
        try:
            live_set.build([live_set.Track("T1", "midi", **kwargs),
                            live_set.Track("PM1", "audio")])
        except ValueError as e:
            assert "PM2" in str(e)
        else:
            raise AssertionError(f"{kwargs} named a track that is not there")


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
