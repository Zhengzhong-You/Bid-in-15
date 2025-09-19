#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Controller for SCIP solver parameter tuning using Qwen.

Features:
- Smoke test (load model and answer a simple prompt)
- Prepare placeholder empty logs: log_{cfg}cfg_{min}min_{ins}ins.txt
- Run the game loop for a given instance id, total 6 minutes budget.
- Conversation memory (history.jsonl) and long transcript saving.
- Sanitization that removes instance tags from logs before feeding to the model.

Dependencies:
  pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio
  pip install transformers accelerate peft bitsandbytes sentencepiece

Usage examples:
  # 1) Smoke test the model
  python qwen_controller.py smoke-test --model Qwen/Qwen2.5-7B-Instruct

  # 2) Prepare empty log files. This may take a while on some filesystems.
  python qwen_controller.py prepare-logs --logs-dir ./logs

  # 3) Run the game for instance 1 with 6-minute budget
  python qwen_controller.py run-game --ins 1 --logs-dir ./logs --history-dir ./history --model Qwen/Qwen2.5-7B-Instruct
"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from qwen_prompt.model_wrapper import QwenRunner, ModelConfig
from qwen_prompt.game_logic import run_game
from qwen_prompt.utils import ensure_dir

# --------------------------- Commands ---------------------------

def cmd_smoke_test(args: argparse.Namespace) -> None:
    """Run smoke test to verify model loading and basic functionality."""
    runner = QwenRunner(ModelConfig(
        model_id=args.model,
        four_bit=not args.no_4bit,
        temperature=0.0
    ))
    msgs = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Qwen smoke test OK' in one short sentence."}
    ]
    out = runner.chat(msgs)
    print(out)


def cmd_prepare_logs(args: argparse.Namespace) -> None:
    """Prepare empty log files for the specified instance."""
    logs_dir = Path(args.logs_dir)
    ensure_dir(logs_dir)
    total = 0
    # Only create files for instance 1 to reduce file count
    ins = 1
    for cfg in range(1, 7):
        for minute in range(1, 7):
            fname = logs_dir / f"log_{cfg}cfg_{minute}min_{ins}ins.txt"
            if not fname.exists():
                fname.touch()
            total += 1
    print(f"Prepared {total} empty log files under {logs_dir} (instance {ins} only)")


def cmd_run_game(args: argparse.Namespace) -> None:
    """Run the SCIP solver parameter tuning game."""
    model_id = args.model
    logs_dir = Path(args.logs_dir)
    history_dir = Path(args.history_dir)
    final_cfg, trials = run_game(
        model_id, logs_dir, history_dir,
        ins=args.ins, total_budget_min=args.budget
    )
    print(json.dumps({
        "instance": args.ins,
        "final_cfg": final_cfg,
        "trials": [asdict(t) for t in trials],
        "history_files": {
            "transcript": str(history_dir / f"transcript_ins{args.ins}.txt"),
            "jsonl": str(history_dir / f"history_ins{args.ins}.jsonl"),
        }
    }, indent=2, ensure_ascii=False))


def build_argparser() -> argparse.ArgumentParser:
    """Build command line argument parser."""
    p = argparse.ArgumentParser(description="Qwen controller: smoke test, prepare logs, and run game.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("smoke-test")
    sp.add_argument("--model", type=str, default="Qwen/Qwen2.5-7B-Instruct")
    sp.add_argument("--no_4bit", action="store_true")
    sp.set_defaults(func=cmd_smoke_test)

    sp = sub.add_parser("prepare-logs")
    sp.add_argument("--logs-dir", type=str, default="./logs")
    sp.set_defaults(func=cmd_prepare_logs)

    sp = sub.add_parser("run-game")
    sp.add_argument("--model", type=str, default="Qwen/Qwen2.5-7B-Instruct")
    sp.add_argument("--logs-dir", type=str, default="./logs")
    sp.add_argument("--history-dir", type=str, default="./history")
    sp.add_argument("--ins", type=int, required=True, help="instance id [1..390]")
    sp.add_argument("--budget", type=int, default=6, help="total minutes budget (default 6)")
    sp.set_defaults(func=cmd_run_game)

    return p


def main():
    """Main entry point."""
    parser = build_argparser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()