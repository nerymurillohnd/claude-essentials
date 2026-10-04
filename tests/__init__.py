"""Test package. Puts scripts/ on sys.path so tests import the gate modules directly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
