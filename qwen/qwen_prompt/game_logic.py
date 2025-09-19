#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Game logic for SCIP solver parameter tuning.
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Tuple

from .model_wrapper import QwenRunner, ModelConfig
from .prompts import SYSTEM_DECIDE, SYSTEM_SUMMARIZE
from .log_processor import process_log_for_conversation, write_transcript_line
from .utils import ensure_dir, extract_first_json, save_jsonl_line, now_ts, clamp_int


@dataclass
class Trial:
    """Represents a single trial run."""
    cfg: int
    minutes: int
    log_excerpt: str


def run_game(
    model_id: str,
    logs_dir: Path,
    history_dir: Path,
    ins: int,
    total_budget_min: int = 6
) -> Tuple[int, List[Trial]]:
    """
    Run the SCIP solver parameter tuning game.

    Args:
        model_id: Model identifier for Qwen
        logs_dir: Directory containing log files
        history_dir: Directory to save history files
        ins: Instance ID
        total_budget_min: Total budget in minutes

    Returns:
        Tuple of (final_cfg, trials_list)
    """
    ensure_dir(history_dir)
    ensure_dir(logs_dir)

    transcript_path = history_dir / f"transcript_ins{ins}.txt"
    history_jsonl = history_dir / f"history_ins{ins}.jsonl"

    # Reset transcript for this run
    if transcript_path.exists():
        transcript_path.unlink()

    # Initialize model
    runner = QwenRunner(ModelConfig(
        model_id=model_id,
        four_bit=True,
        temperature=0.0,
        max_new_tokens=384
    ))

    remaining = total_budget_min
    trials: List[Trial] = []

    # Conversation messages we keep appending to (like ChatGPT memory)
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_DECIDE},
        {"role": "user", "content": (
            f"Total budget: {total_budget_min} minutes.\n"
            f"Remaining minutes: {remaining}.\n"
            "Configs available: 1..6.\n"
            f"Instance id: {ins} (NOTE: do not mention instance id in your reasoning or outputs).\n"
            "Previous trials: none."
        )}
    ]

    write_transcript_line(transcript_path, "system", SYSTEM_DECIDE)
    write_transcript_line(transcript_path, "user", messages[-1]["content"])

    while remaining > 0:
        # Ask model for next decision
        model_out = runner.chat(messages)
        write_transcript_line(transcript_path, "assistant(raw)", model_out)
        save_jsonl_line(history_jsonl, {
            "ts": now_ts(),
            "type": "assistant_raw",
            "text": model_out
        })

        js = extract_first_json(model_out) or {}
        decision = js.get("decision", {})
        cfg = int(decision.get("cfg", 1))
        minutes = int(decision.get("minutes", 1))

        cfg = clamp_int(cfg, 1, 6)
        minutes = clamp_int(minutes, 1, 6)
        if minutes > remaining:
            minutes = remaining  # clamp to remaining

        # Read and process the corresponding log
        clean_log = process_log_for_conversation(logs_dir, cfg, minutes, ins)

        # Record this trial
        trials.append(Trial(cfg=cfg, minutes=minutes, log_excerpt=clean_log[:2000]))

        # Append tool log to conversation
        tool_msg = (
            f"TRIAL RESULT (cfg={cfg}, minutes={minutes}):\n"
            f"{clean_log if clean_log.strip() else '[empty log]'}"
        )
        messages.append({"role": "assistant", "content": json.dumps(js, ensure_ascii=False)})
        messages.append({"role": "user", "content": tool_msg})
        write_transcript_line(transcript_path, "tool(log)", tool_msg)
        save_jsonl_line(history_jsonl, {
            "ts": now_ts(),
            "type": "trial",
            "cfg": cfg,
            "minutes": minutes,
            "log_excerpt": clean_log[:1000]
        })

        remaining -= minutes

        # Prepare the next user instruction summarizing remaining budget and prior trials
        trials_brief = "; ".join([f"(cfg={t.cfg}, min={t.minutes})" for t in trials])
        next_user = (
            f"Remaining minutes: {remaining}. "
            f"Tried so far: {trials_brief if trials_brief else 'none'}. "
            f"Choose NEXT decision following the JSON schema."
        )
        messages.append({"role": "user", "content": next_user})
        write_transcript_line(transcript_path, "user", next_user)

    # Budget ended → Ask for final summary/decision
    messages_summary = [
        {"role": "system", "content": SYSTEM_SUMMARIZE},
        {"role": "user", "content": (
            f"Budget fully consumed (total {total_budget_min} minutes). "
            f"Trials: " + "; ".join([f"(cfg={t.cfg}, min={t.minutes})" for t in trials]) + ". "
            "Provide final decision JSON now."
        )}
    ]
    write_transcript_line(transcript_path, "system", SYSTEM_SUMMARIZE)
    write_transcript_line(transcript_path, "user", messages_summary[-1]["content"])

    final_out = runner.chat(messages_summary)
    write_transcript_line(transcript_path, "assistant(raw)", final_out)
    save_jsonl_line(history_jsonl, {
        "ts": now_ts(),
        "type": "assistant_final_raw",
        "text": final_out
    })

    final_js = extract_first_json(final_out) or {}
    final_cfg = int(final_js.get("final_cfg", 1))
    final_cfg = clamp_int(final_cfg, 1, 6)

    # Append final JSON to transcript
    write_transcript_line(transcript_path, "assistant(json)", json.dumps(final_js, ensure_ascii=False))

    return final_cfg, trials