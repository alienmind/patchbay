"""Compile a spec into targets.

A spec is an ordinary Python file using the DSL. No custom syntax,
deliberately: a parser would have to be written, tested and kept in step
with the DSL, whereas a Python file type-checks, autocompletes, imports
helpers, and can express the loops that variations need.

A spec declares racks and lets the compiler realise them. Either export a
module-level `RACKS`, or define `build()` returning them:

    RACKS = [pd1, bs1]

    # or
    def build() -> list[Rack]:
        return [make_pad_rack(), make_bass_rack()]

Any module-level `Rack` is picked up if neither is present, so the
smallest useful spec is a few `Rack(...)` assignments.

Targets today are `.adg` rack presets. Sets are not compiled to `.als` -
Live's API cannot build those either. `MCP.md` has the capability table
that established it.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Sequence

from .dsl import Rack


class SpecError(Exception):
    """A spec that cannot be loaded or contains nothing to build."""


@dataclass(slots=True)
class Built:
    """One realised target."""

    rack: Rack
    path: Path

    @property
    def name(self) -> str:
        return self.rack.name


def load_spec(path: Path | str) -> ModuleType:
    """Import a spec file as a module.

    The spec's own directory goes on `sys.path` first, so a spec can import
    helpers sitting beside it.
    """
    p = Path(path).resolve()
    if not p.exists():
        raise SpecError(f"no such spec: {p}")

    parent = str(p.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    spec = importlib.util.spec_from_file_location(p.stem, p)
    if spec is None or spec.loader is None:
        raise SpecError(f"cannot load {p} as a Python module")

    module = importlib.util.module_from_spec(spec)
    sys.modules[p.stem] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:                       # the spec's own error
        raise SpecError(f"{p.name} failed to load: {type(e).__name__}: {e}") from e
    return module


def racks_in(module: ModuleType) -> list[Rack]:
    """The racks a spec declares, by whichever convention it used."""
    racks = getattr(module, "RACKS", None)
    if racks is None and callable(getattr(module, "build", None)):
        racks = module.build()
    if racks is None:
        racks = [v for v in vars(module).values() if isinstance(v, Rack)]

    if isinstance(racks, Rack):
        racks = [racks]
    racks = list(racks or [])

    bad = [r for r in racks if not isinstance(r, Rack)]
    if bad:
        raise SpecError(f"RACKS contains non-Rack values: {bad[:3]}")
    return racks


def slugify(name: str) -> str:
    keep = [c if c.isalnum() or c in "-_" else "_" for c in name.strip()]
    return "".join(keep).strip("_") or "rack"


def compile_spec(
    path: Path | str,
    out_dir: Path | str = "build",
    only: Sequence[str] | None = None,
    clean: bool = False,
) -> list[Built]:
    """Load a spec and write every rack it declares.

    `only` filters by rack name. Each rack is checked for sibling id
    collisions before writing, so a file Live would refuse never reaches
    disk.

    `clean` removes `.adg` files in `out_dir` this build did not write, so
    a renamed rack does not leave its old name behind for somebody to drag
    into Live. It removes nothing else, does not recurse, and is refused
    beside `only`, where every rack not asked for would look stale.
    """
    module = load_spec(path)
    racks = racks_in(module)
    if not racks:
        raise SpecError(
            f"{Path(path).name} declares no racks. Export RACKS, define "
            f"build(), or assign a Rack at module level.")

    if only:
        wanted = {n.lower() for n in only}
        racks = [r for r in racks if r.name.lower() in wanted]
        if not racks:
            raise SpecError(f"no rack matching {', '.join(only)}")

    if clean and only:
        raise SpecError(
            "--clean with --only would delete every rack not asked for")

    out = Path(out_dir)
    built: list[Built] = []
    for rack in racks:
        target = out / f"{slugify(rack.name)}.adg"
        rack.save(target)
        built.append(Built(rack, target))

    if clean:
        keep = {b.path.resolve() for b in built}
        for stale in sorted(out.glob("*.adg")):
            if stale.resolve() not in keep:
                stale.unlink()
                print(f"  removed {stale}")
    return built


def report(path: Path | str, out_dir: Path | str = "build",
           only: Sequence[str] | None = None,
           clean: bool = False) -> list[Built]:
    built = compile_spec(path, out_dir, only, clean)
    print(f"{Path(path).name} -> {len(built)} rack(s)\n")
    for b in built:
        engines = ", ".join(e.name for e in b.rack.engines)
        print(f"  {b.rack.name}")
        print(f"    {b.rack.kind.name.lower()}, {len(b.rack.engines)} engines: {engines}")
        print(f"    {b.path}")
    return built
