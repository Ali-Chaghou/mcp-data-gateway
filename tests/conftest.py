"""Shared test setup.

Puts the repository's ``scripts/`` directory and this ``tests/`` directory on
``sys.path`` so the loader script and shared test helpers can be imported as
modules.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent / "scripts"))
sys.path.insert(0, str(_here))
