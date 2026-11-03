"""Quick smoke test for the saved adapter. Run from the project root."""
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
ADAPTER_DIR = "model/marketing-llm-finetuned"

tokenizer = AutoTokenizer.from_pretrained(ADAPTER_DIR)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

device = "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu"
dtype = torch.float32

base = AutoModelForCausalLM.from_pretrained(BASE_MODEL, torch_dtype=dtype)
base.to(device)
model = PeftModel.from_pretrained(base, ADAPTER_DIR)
model.eval()

questions = [
    "What is a Smart Campaign in Marketo?",
    "What does No Show mean in a webinar?",
    "What is Oracle Eloqua?",
]

for question in questions:
    messages = [{"role": "user", "content": question}]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    with torch.inference_mode():
        output = model.generate(
            **inputs, max_new_tokens=120, do_sample=False,
            pad_token_id=tokenizer.eos_token_id
        )
    answer = tokenizer.decode(
        output[0, inputs["input_ids"].shape[1]:],
        skip_special_tokens=True
    ).strip()
    print(f"\nQ: {question}\nA: {answer}\n" + "-" * 60)
