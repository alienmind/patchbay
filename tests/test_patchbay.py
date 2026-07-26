"""Tests against the real racks in racks/.

These do not prove Live will load anything - only dragging a file in does
that. What they do prove is that the library still agrees with every
finding recorded in SCHEMA.md. If Live changes its schema, these fail and
point at the spike that needs re-running.

Run with:  python -m pytest tests/ -q
       or:  python tests/test_patchbay.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from patchbay import io, find, params, clone, mappings, ids   # noqa: E402

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
