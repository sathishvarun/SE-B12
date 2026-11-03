
"""
Marketing AI Assistant - Model Evaluation
Loads the Qwen base model and existing LoRA adapter.
Runs five marketing automation smoke tests.
"""

from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel


# --------------------------------------------------
# 1. PROJECT CONFIGURATION
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

ADAPTER_DIR = (
    PROJECT_DIR / "model" / "marketing-llm-finetuned"
)


# --------------------------------------------------
# 2. SELECT COMPUTE DEVICE
# --------------------------------------------------

if torch.backends.mps.is_available():
    device = "mps"
elif torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

print("=" * 60)
print("MARKETING AI ASSISTANT - MODEL EVALUATION")
print("=" * 60)

print(f"Device: {device}")
print(f"Base model: {BASE_MODEL}")
print(f"Adapter: {ADAPTER_DIR}")


# --------------------------------------------------
# 3. CHECK ADAPTER DIRECTORY
# --------------------------------------------------

if not ADAPTER_DIR.exists():
    raise FileNotFoundError(
        f"LoRA adapter not found: {ADAPTER_DIR}"
    )


# --------------------------------------------------
# 4. LOAD TOKENIZER
# --------------------------------------------------

print("\nLoading tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(
    BASE_MODEL
)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token


# --------------------------------------------------
# 5. LOAD BASE MODEL
# --------------------------------------------------

print("\nLoading Qwen base model...")

base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.float32
)

base_model.to(device)


# --------------------------------------------------
# 6. LOAD LORA ADAPTER
# --------------------------------------------------

print("\nLoading fine-tuned LoRA adapter...")

model = PeftModel.from_pretrained(
    base_model,
    str(ADAPTER_DIR)
)

model.eval()

print("Model loaded successfully!")


# --------------------------------------------------
# 7. EVALUATION QUESTIONS
# --------------------------------------------------

questions = [
    {
        "category": "Oracle Eloqua",
        "question": "Explain Oracle Eloqua and its main features."
    },
    {
        "category": "Marketo",
        "question": "How do Smart Campaigns work in Marketo?"
    },
    {
        "category": "Lead Nurturing",
        "question": "Explain a lead nurturing workflow."
    },
    {
        "category": "Webinar Operations",
        "question": "What follow-up process should be used for webinar no-shows?"
    },
    {
        "category": "CRM Integration",
        "question": "Explain Oracle Eloqua and Salesforce CRM integration."
    }
]


# --------------------------------------------------
# 8. GENERATE AND DISPLAY ANSWERS
# --------------------------------------------------

results = []

print("\nStarting model evaluation...\n")

for index, item in enumerate(questions, start=1):

    question = item["question"]

    print(f"\nTest {index}: {item['category']}")
    print(f"Question: {question}")

    messages = [
        {
            "role": "user",
            "content": question
        }
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    ).to(device)

    with torch.inference_mode():

        outputs = model.generate(
            **inputs,
            max_new_tokens=200,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id
        )

    new_tokens = outputs[
        0, inputs["input_ids"].shape[1]:
    ]

    answer = tokenizer.decode(
        new_tokens,
        skip_special_tokens=True
    ).strip()

    print(f"\nGenerated Answer:\n{answer}")
    print("-" * 60)

    results.append({
        "category": item["category"],
        "question": question,
        "answer": answer
    })


# --------------------------------------------------
# 9. SAVE EVALUATION RESULTS
# --------------------------------------------------

import json

output_file = PROJECT_DIR / "model_evaluation_results.json"

with open(output_file, "w", encoding="utf-8") as file:

    json.dump(
        results,
        file,
        indent=4,
        ensure_ascii=False
    )

print("\n" + "=" * 60)
print("MODEL EVALUATION COMPLETED")
print("=" * 60)

print(f"Total questions tested: {len(questions)}")
print(f"Results saved to: {output_file}")
