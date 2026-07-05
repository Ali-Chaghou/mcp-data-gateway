"""Shared test setup.

Puts the repository's ``scripts/`` directory on ``sys.path`` so the loader
script can be imported and unit-tested like a module.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
