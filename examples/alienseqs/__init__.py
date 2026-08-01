import importlib
from pathlib import Path

RACKS = []
_dir = Path(__file__).parent
for _file in sorted(_dir.glob("*.py")):
    if _file.name == "__init__.py":
        continue
    mod_name = _file.stem
    mod = importlib.import_module(f".{mod_name}", package=__name__)
    RACKS.extend(mod.RACKS)