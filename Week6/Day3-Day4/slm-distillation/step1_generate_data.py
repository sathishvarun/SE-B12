"""
STEP 1 - The TEACHER answers every question in data/prompts.txt.
Its answers become the training data for the student.

Run:  python step1_generate_data.py
"""
import json
import os
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from config import (DISTILL_FILE, PROMPTS_FILE, TEACHER_MAX_NEW_TOKENS,
                    TEACHER_MODEL, get_device)


def main():
    device = get_device()
    print("=" * 60)
    print("STEP 1: Teacher generates answers")
    print(f"Teacher model : {TEACHER_MODEL}")
    print(f"Device        : {device}")
    print("=" * 60)

    print("\n[1/3] Loading teacher (first run downloads ~720 MB)...")
    tokenizer = AutoTokenizer.from_pretrained(TEACHER_MODEL)
    model = AutoModelForCausalLM.from_pretrained(TEACHER_MODEL, torch_dtype=torch.float32)
    model.to(device).eval()

    with open(PROMPTS_FILE, encoding="utf-8") as f:
        prompts = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    print(f"[2/3] Loaded {len(prompts)} prompts from {PROMPTS_FILE}")

    os.makedirs(os.path.dirname(DISTILL_FILE), exist_ok=True)
    print("[3/3] Generating teacher answers...\n")
    start = time.time()

    with open(DISTILL_FILE, "w", encoding="utf-8") as out_file:
        for i, prompt in enumerate(prompts, 1):
            messages = [{"role": "user", "content": prompt}]
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(text, return_tensors="pt").to(device)

            with torch.no_grad():
                output = model.generate(
                    **inputs,
                    max_new_tokens=TEACHER_MAX_NEW_TOKENS,
                    do_sample=False,
                    pad_token_id=tokenizer.eos_token_id,
                )
            new_tokens = output[0][inputs["input_ids"].shape[1]:]
            answer = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

            out_file.write(json.dumps({"prompt": prompt, "response": answer}, ensure_ascii=False) + "\n")
            print(f"  [{i:>3}/{len(prompts)}] {prompt[:55]}")

    print(f"\nDone in {time.time() - start:.0f}s. Saved -> {DISTILL_FILE}")
    print("Next: python step2_train_student.py")


if __name__ == "__main__":
    main()
