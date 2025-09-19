#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions for the SCIP solver tuning system.
"""

import json
import re
import time
from pathlib import Path
from typing import Any, Optional, Dict


def ensure_dir(p: Path) -> None:
    """Ensure directory exists."""
    p.mkdir(parents=True, exist_ok=True)


def extract_first_json(text: str) -> Optional[Any]:
    """Extract first JSON object/array from text."""
    m = re.search(r'(\{.*\}|\[.*\])', text, flags=re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def save_jsonl_line(path: Path, obj: Dict[str, Any]) -> None:
    """Save a single object as a line in JSONL file."""
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def now_ts() -> str:
    """Get current timestamp string."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def clamp_int(x: int, lo: int, hi: int) -> int:
    """Clamp integer to range [lo, hi]."""
    return max(lo, min(hi, x))