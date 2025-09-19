#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCIP Solver Parameter Tuning Package

A modular system for tuning SCIP solver parameters using Qwen LLM.
"""

from .model_wrapper import QwenRunner, ModelConfig
from .game_logic import run_game, Trial
from .log_processor import sanitize_log, process_log_for_conversation
from .prompts import SYSTEM_DECIDE, SYSTEM_SUMMARIZE
from .utils import ensure_dir, extract_first_json, save_jsonl_line, now_ts, clamp_int

__version__ = "1.0.0"
__all__ = [
    "QwenRunner",
    "ModelConfig",
    "run_game",
    "Trial",
    "sanitize_log",
    "process_log_for_conversation",
    "SYSTEM_DECIDE",
    "SYSTEM_SUMMARIZE",
    "ensure_dir",
    "extract_first_json",
    "save_jsonl_line",
    "now_ts",
    "clamp_int",
]