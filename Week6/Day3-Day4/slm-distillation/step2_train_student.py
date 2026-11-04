"""
STEP 2 - Knowledge distillation: the STUDENT learns from the TEACHER.

Loss = ALPHA * KL(teacher_probs || student_probs)   <- imitate how the teacher "thinks"
     + (1 - ALPHA) * CrossEntropy(teacher_answer)   <- reproduce the teacher's answer

Run:  python step2_train_student.py
"""
import json
import math
import os
import random
import time

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer

from config import (ALPHA, BATCH_SIZE, DISTILL_FILE, EPOCHS, LEARNING_RATE,
                    MAX_SEQ_LEN, PROMPT_TEMPLATE, SEED, STUDENT_MODEL,
                    STUDENT_OUTPUT_DIR, TEACHER_MODEL, TEMPERATURE, get_device)


class DistillDataset(Dataset):
    """Each item = prompt + teacher answer. Loss is only computed on the answer part."""

    def __init__(self, path, tokenizer):
        self.items = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                prompt_ids = tokenizer(PROMPT_TEMPLATE.format(prompt=row["prompt"]),
                                       add_special_tokens=False)["input_ids"]
                answer_ids = tokenizer(row["response"], add_special_tokens=False)["input_ids"]
                answer_ids = answer_ids + [tokenizer.eos_token_id]

                input_ids = (prompt_ids + answer_ids)[:MAX_SEQ_LEN]
                labels = ([-100] * len(prompt_ids) + answer_ids)[:MAX_SEQ_LEN]
                self.items.append((input_ids, labels))

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        return self.items[idx]


def make_collate(pad_id):
    def collate(batch):
        max_len = max(len(ids) for ids, _ in batch)
        input_ids, labels, attention = [], [], []
        for ids, lab in batch:
            pad = max_len - len(ids)
            input_ids.append(ids + [pad_id] * pad)
            labels.append(lab + [-100] * pad)
            attention.append([1] * len(ids) + [0] * pad)
        return {
            "input_ids": torch.tensor(input_ids),
            "labels": torch.tensor(labels),
            "attention_mask": torch.tensor(attention),
        }
    return collate


def distillation_loss(student_logits, teacher_logits, labels):
    # Shift so position t predicts token t+1
    s = student_logits[:, :-1, :]
    t = teacher_logits[:, :-1, :]
    y = labels[:, 1:]

    vocab = min(s.size(-1), t.size(-1))
    s, t = s[..., :vocab], t[..., :vocab]
    mask = (y != -100)

    # Hard loss: match teacher's generated text
    ce = F.cross_entropy(s.reshape(-1, vocab), y.reshape(-1), ignore_index=-100)

    # Soft loss: match teacher's probability distribution
    s_log_probs = F.log_softmax(s / TEMPERATURE, dim=-1)
    t_log_probs = F.log_softmax(t / TEMPERATURE, dim=-1)
    kl_per_token = (t_log_probs.exp() * (t_log_probs - s_log_probs)).sum(-1)
    kl = (kl_per_token * mask).sum() / mask.sum().clamp(min=1) * (TEMPERATURE ** 2)

    return ALPHA * kl + (1 - ALPHA) * ce, kl.item(), ce.item()


def main():
    random.seed(SEED)
    torch.manual_seed(SEED)
    device = get_device()

    print("=" * 60)
    print("STEP 2: Distill teacher -> student")
    print(f"Teacher : {TEACHER_MODEL}")
    print(f"Student : {STUDENT_MODEL}")
    print(f"Device  : {device}")
    print("=" * 60)

    if not os.path.exists(DISTILL_FILE):
        raise SystemExit(f"{DISTILL_FILE} not found. Run step1_generate_data.py first.")

    print("\n[1/4] Loading tokenizer + models...")
    tokenizer = AutoTokenizer.from_pretrained(STUDENT_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    teacher = AutoModelForCausalLM.from_pretrained(TEACHER_MODEL, torch_dtype=torch.float32).to(device).eval()
    for p in teacher.parameters():
        p.requires_grad = False
    student = AutoModelForCausalLM.from_pretrained(STUDENT_MODEL, torch_dtype=torch.float32).to(device)
    student.train()

    t_params = sum(p.numel() for p in teacher.parameters()) / 1e6
    s_params = sum(p.numel() for p in student.parameters()) / 1e6
    print(f"      Teacher params: {t_params:.0f}M | Student params: {s_params:.0f}M "
          f"({t_params / s_params:.1f}x smaller)")

    print("[2/4] Building dataset...")
    dataset = DistillDataset(DISTILL_FILE, tokenizer)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True,
                        collate_fn=make_collate(tokenizer.pad_token_id))
    print(f"      {len(dataset)} examples, {len(loader)} batches/epoch")

    optimizer = torch.optim.AdamW(student.parameters(), lr=LEARNING_RATE)

    print(f"[3/4] Training for {EPOCHS} epochs...\n")
    start = time.time()
    for epoch in range(1, EPOCHS + 1):
        total, steps = 0.0, 0
        for step, batch in enumerate(loader, 1):
            batch = {k: v.to(device) for k, v in batch.items()}

            with torch.no_grad():
                teacher_logits = teacher(input_ids=batch["input_ids"],
                                         attention_mask=batch["attention_mask"]).logits
            student_logits = student(input_ids=batch["input_ids"],
                                     attention_mask=batch["attention_mask"]).logits

            loss, kl, ce = distillation_loss(student_logits, teacher_logits, batch["labels"])

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(student.parameters(), 1.0)
            optimizer.step()

            total += loss.item()
            steps += 1
            if step % 5 == 0 or step == len(loader):
                print(f"  epoch {epoch}/{EPOCHS} | step {step:>3}/{len(loader)} | "
                      f"loss {loss.item():.3f} (kl {kl:.3f}, ce {ce:.3f})")
        avg = total / steps
        print(f"  >> epoch {epoch} avg loss {avg:.3f} | perplexity~{math.exp(min(avg, 20)):.1f}\n")

    print(f"[4/4] Saving student -> {STUDENT_OUTPUT_DIR}")
    os.makedirs(STUDENT_OUTPUT_DIR, exist_ok=True)
    student.save_pretrained(STUDENT_OUTPUT_DIR)
    tokenizer.save_pretrained(STUDENT_OUTPUT_DIR)
    print(f"\nTraining done in {time.time() - start:.0f}s.")
    print("Next: python step3_chat.py   (or start the API with uvicorn)")


if __name__ == "__main__":
    main()
