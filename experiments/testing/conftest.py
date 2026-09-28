"""Make the experiment modules importable for the experiment tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
