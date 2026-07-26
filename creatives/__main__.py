"""Allow `python -m creatives` as an alias for the root CLI."""

from __future__ import annotations

import runpy
from pathlib import Path


def _run() -> None:
    root_cli = Path(__file__).resolve().parent.parent / "generate_creatives.py"
    runpy.run_path(str(root_cli), run_name="__main__")


if __name__ == "__main__":
    _run()
