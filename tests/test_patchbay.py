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

from patchbay import io, find, params, clone, mappings, ids, variations  # noqa: E402
from patchbay.dsl import Grammar, Rack, RackKind, Variation   # noqa: E402

RACKS = Path(__file__).resolve().parent.parent / "racks"


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
    g = Grammar("Engine", "Cutoff", "Resonance", "Decay", "Drive")
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

    A variation names grammar slots, never a device parameter, so there is
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
    cutoff = rack.grammar.macro_of("cutoff")
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

    slot = rack.grammar.macro_of("engine")
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
        assert set(v["values"]) == {rack.grammar.macro_of(s)
                                    for s in ("engine", "cutoff",
                                              "decay", "resonance")}


# --- nested racks ---------------------------------------------------------

def _nested_pair():
    """An outer rack with one chain holding an inner rack."""
    g = Grammar("Engine", "Cutoff")
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
    g = Grammar("Engine", "Cutoff")
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


def test_nest_defaults_to_identity_over_the_shared_grammar():
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
    g = Grammar("Cutoff")
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
    assert len(chained) == 6, "3 slots chained into each of 2 sub-racks"
    assert all(m["channel"] == "16" for m in chained), "depth is not encoded"


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
