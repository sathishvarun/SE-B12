
import json
import torch

from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

V1_ADAPTER = "model/marketing-llm-finetuned"
V2_ADAPTER = "model/marketing-llm-finetuned-v2"

QUESTIONS_FILE = "evaluation_questions.json"
OUTPUT_FILE = "adapter_comparison_results.json"

MAX_NEW_TOKENS = 300

# --------------------------------------------------
# 2. Select device
# --------------------------------------------------

if torch.backends.mps.is_available():
    device = "mps"
elif torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

print("Using device:", device)

# --------------------------------------------------
# 3. Load tokenizer
# --------------------------------------------------

print("\nLoading tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# --------------------------------------------------
# 4. Load base model
# --------------------------------------------------

print("\nLoading base model...")

base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.float32
)

# Move base model to the selected device
base_model = base_model.to(device)

# --------------------------------------------------
# 5. Load both adapters
# --------------------------------------------------

print("\nLoading V1 adapter...")

model = PeftModel.from_pretrained(
    base_model,
    V1_ADAPTER,
    adapter_name="v1"
)

print("Loading V2 adapter...")

model.load_adapter(
    V2_ADAPTER,
    adapter_name="v2"
)

model = model.to(device)
model.eval()

print("Both adapters loaded successfully.")

# --------------------------------------------------
# 6. Load evaluation questions
# --------------------------------------------------

with open(QUESTIONS_FILE, "r", encoding="utf-8") as file:
    questions_data = json.load(file)

if not isinstance(questions_data, list) or not questions_data:
    raise ValueError("Evaluation questions must be a non-empty JSON array.")

questions = []

for index, item in enumerate(questions_data):
    if not isinstance(item, dict) or not isinstance(item.get("question"), str):
        raise ValueError(f"Invalid question at item {index}.")
    questions.append(item["question"].strip())

print("Total evaluation questions:", len(questions))

# --------------------------------------------------
# 7. Generate answer
# --------------------------------------------------

def generate_answer(question):

    messages = [
        {
            "role": "user",
            "content": question
        }
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt"
    )

    # Input and model must use the same device
    inputs = inputs.to(device)

    with torch.inference_mode():

        outputs = model.generate(
            input_ids=inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )

    generated_tokens = outputs[0][inputs.shape[-1]:]

    answer = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True
    )

    return answer.strip()

# --------------------------------------------------
# 8. Compare V1 and V2
# --------------------------------------------------

results = []

for index, item in enumerate(questions_data, start=1):

    question = item["question"].strip()
    category = item.get("category", "General")

    print(f"\nQuestion {index}/{len(questions_data)}")
    print("Category:", category)
    print("Question:", question)

    # Generate V1 answer
    model.set_adapter("v1")

    v1_answer = generate_answer(question)

    # Generate V2 answer
    model.set_adapter("v2")

    v2_answer = generate_answer(question)

    results.append({
        "category": category,
        "question": question,
        "v1_answer": v1_answer,
        "v2_answer": v2_answer
    })

    print("\nV1:", v1_answer[:200])
    print("\nV2:", v2_answer[:200])

# --------------------------------------------------
# 9. Save results
# --------------------------------------------------

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:

    json.dump(
        results,
        file,
        indent=4,
        ensure_ascii=False
    )

print("\n====================================")
print("V1 VS V2 COMPARISON COMPLETED")
print("====================================")

print("Results saved to:", OUTPUT_FILE)
