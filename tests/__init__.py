"""Test package. Puts scripts/ on sys.path so tests import the gate modules directly."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
