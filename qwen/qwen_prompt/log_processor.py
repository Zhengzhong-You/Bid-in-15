#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log processing utilities for SCIP solver logs.
Handles sanitization and snippet extraction from long logs.
"""

import re
import time
from pathlib import Path
from typing import Optional


def sanitize_log(text: str) -> str:
    """Remove instance tags like '1ins', 'ins=123', 'instance 45' from logs."""
    if not text:
        return ""
    # Remove tokens like '123ins' or '1ins' or 'ins123'
    text = re.sub(r'\b\d+\s*ins\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\bins\s*\d+\b', '', text, flags=re.IGNORECASE)
    # Remove 'ins=123' variants
    text = re.sub(r'\bins\s*=\s*\d+\b', '', text, flags=re.IGNORECASE)
    # Remove 'instance XXX'
    text = re.sub(r'\binstance\s*[:=]?\s*\d+\b', '', text, flags=re.IGNORECASE)
    # Collapse multiple spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def extract_log_snippet(log_text: str, max_length: int = 2000) -> str:
    """Extract relevant snippet from log, prioritizing important sections."""
    if not log_text or len(log_text) <= max_length:
        return log_text

    # Try to find important sections (error messages, solver stats, etc.)
    important_patterns = [
        r'.*error.*',
        r'.*warning.*',
        r'.*solution.*',
        r'.*optimal.*',
        r'.*status.*',
        r'.*time.*',
        r'.*nodes.*',
        r'.*bound.*'
    ]

    lines = log_text.split('\n')
    important_lines = []

    for line in lines:
        for pattern in important_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                important_lines.append(line)
                break

    # If we have important lines, use those
    if important_lines:
        snippet = '\n'.join(important_lines)
        if len(snippet) <= max_length:
            return snippet
        # Truncate if still too long
        return snippet[:max_length] + "..."

    # Otherwise, just take the beginning and end
    if len(log_text) > max_length:
        half = max_length // 2 - 50
        return log_text[:half] + "\n...[truncated]...\n" + log_text[-half:]

    return log_text


def read_log_file(logs_dir: Path, cfg: int, minutes: int, ins: int) -> str:
    """Read log file and return its content."""
    fname = f"log_{cfg}cfg_{minutes}min_{ins}ins.txt"
    fpath = logs_dir / fname
    if not fpath.exists():
        # Create placeholder empty if missing
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()
    return fpath.read_text(encoding="utf-8", errors="ignore")


def process_log_for_conversation(logs_dir: Path, cfg: int, minutes: int, ins: int, max_length: int = 2000) -> str:
    """Read, sanitize, and extract snippet from log file for conversation."""
    raw_log = read_log_file(logs_dir, cfg, minutes, ins)
    clean_log = sanitize_log(raw_log)
    return extract_log_snippet(clean_log, max_length)


def write_transcript_line(transcript_path: Path, role: str, content: str) -> None:
    """Write a line to the transcript file with timestamp."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with transcript_path.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {role.upper()}: {content}\n\n")