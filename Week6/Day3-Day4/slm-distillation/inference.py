"""
Shared inference code - used by both the terminal chat and the API server.
"""
import os

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from config import PROMPT_TEMPLATE, STUDENT_MODEL, STUDENT_OUTPUT_DIR, get_device


class StudentModel:
    def __init__(self, model_path: str = STUDENT_OUTPUT_DIR):
        if model_path == STUDENT_OUTPUT_DIR and not os.path.isdir(model_path):
            raise RuntimeError(
                f"Trained student not found at '{model_path}'. "
                "Run step1_generate_data.py and step2_train_student.py first."
            )
        self.device = get_device()
        self.model_path = model_path
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.float32)
        self.model.to(self.device).eval()

    def generate(self, prompt: str, max_new_tokens: int = 150, temperature: float = 0.7) -> str:
        text = PROMPT_TEMPLATE.format(prompt=prompt)
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)

        gen_kwargs = dict(
            max_new_tokens=max_new_tokens,
            repetition_penalty=1.2,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )
        if temperature > 0:
            gen_kwargs.update(do_sample=True, temperature=temperature, top_p=0.9)
        else:
            gen_kwargs.update(do_sample=False)

        with torch.no_grad():
            output = self.model.generate(**inputs, **gen_kwargs)
        new_tokens = output[0][inputs["input_ids"].shape[1]:]
        answer = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        # Stop if the model starts inventing a new question
        return answer.split("### Question")[0].strip()


def load_untrained_student() -> StudentModel:
    """The original student before distillation - handy for before/after comparison."""
    return StudentModel(model_path=STUDENT_MODEL)
