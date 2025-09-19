#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model wrapper for Qwen SCIP solver parameter tuning.
"""

from dataclasses import dataclass
from typing import List, Dict

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig


@dataclass
class ModelConfig:
    """Configuration for the Qwen model."""
    model_id: str = "Qwen/Qwen2.5-7B-Instruct"
    four_bit: bool = True
    temperature: float = 0.0
    max_new_tokens: int = 384


class QwenRunner:
    """Wrapper for running Qwen model inference."""

    def __init__(self, cfg: ModelConfig):
        self.cfg = cfg
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                cfg.model_id, trust_remote_code=True, use_fast=True
            )
        except ValueError as e:
            if "Qwen2Tokenizer" in str(e):
                # Fallback for older transformers versions
                print("Warning: Using fallback tokenizer loading...")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    cfg.model_id, trust_remote_code=True, use_fast=False, revision="main"
                )
            else:
                raise e

        bnb_config = None
        torch_dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

        if cfg.four_bit:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch_dtype,
            )

        self.model = AutoModelForCausalLM.from_pretrained(
            cfg.model_id,
            device_map="auto",
            torch_dtype=torch_dtype,
            quantization_config=bnb_config,
            trust_remote_code=True,
        )

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Generate response from chat messages."""
        chat_text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(chat_text, return_tensors="pt").to(self.model.device)

        gen_kwargs = dict(
            max_new_tokens=self.cfg.max_new_tokens,
            temperature=self.cfg.temperature,
            do_sample=(self.cfg.temperature > 0.0),
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.eos_token_id,
        )

        with torch.inference_mode():
            out = self.model.generate(**inputs, **gen_kwargs)

        return self.tokenizer.decode(out[0], skip_special_tokens=True)