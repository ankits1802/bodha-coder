from __future__ import annotations

import sys
from pathlib import Path

GOLD_SET = Path(__file__).resolve().parents[3] / "tools" / "gold_set"
if str(GOLD_SET) not in sys.path:
    sys.path.insert(0, str(GOLD_SET))
