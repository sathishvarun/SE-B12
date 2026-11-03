"""
Marketing AI Assistant - LoRA Fine-Tuning
Base Model: Qwen/Qwen2.5-0.5B-Instruct
Dataset: training_dataset_v2.json
Output: model/marketing-llm-finetuned-v2/
"""

import json
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    default_data_collator,
)

# ============================================================
# 1. CONFIGURATION
# ============================================================

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

DATASET_PATH = Path("training_dataset_v2.json")

OUTPUT_DIR = Path("model/marketing-llm-finetuned-v2")

MAX_LENGTH = 512
NUM_EPOCHS = 3
LEARNING_RATE = 1e-4
BATCH_SIZE = 1
GRADIENT_ACCUMULATION_STEPS = 4
RANDOM_SEED = 42


# ============================================================
# 2. VALIDATE DATASET
# ============================================================

if not DATASET_PATH.is_file():
    raise FileNotFoundError(
        f"Dataset not found: {DATASET_PATH}"
    )

with DATASET_PATH.open("r", encoding="utf-8") as file:
    data = json.load(file)

if not isinstance(data, list):
    raise ValueError("Dataset must be a JSON array.")

if len(data) != 50:
    raise ValueError(
        f"Expected 50 examples, found {len(data)}"
    )

for index, item in enumerate(data):

    if not isinstance(item, dict):
        raise ValueError(
            f"Dataset item {index} is not a JSON object."
        )

    question = item.get("question")
    answer = item.get("answer")

    if not isinstance(question, str) or not question.strip():
        raise ValueError(
            f"Empty or invalid question at item {index}"
        )

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(
            f"Empty or invalid answer at item {index}"
        )

questions = [
    item["question"].strip().casefold()
    for item in data
]

if len(questions) != len(set(questions)):
    raise ValueError("Duplicate questions found.")

# Never overwrite an existing training run.
if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
    raise FileExistsError(
        f"{OUTPUT_DIR} already exists and is not empty. "
        "Choose a new output directory before training."
    )

print(f"Dataset validated: {len(data)} unique examples")


# ============================================================
# 3. SELECT DEVICE
# ============================================================

if torch.backends.mps.is_available():
    device_name = "Apple Silicon MPS"

elif torch.cuda.is_available():
    device_name = "CUDA"

else:
    device_name = "CPU"

print(f"Training device: {device_name}")


# ============================================================
# 4. LOAD TOKENIZER
# ============================================================

print("Loading tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

tokenizer.padding_side = "right"


# ============================================================
# 5. LOAD BASE MODEL
# ============================================================

print("Loading base model...")

model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.float32,
)

model.config.pad_token_id = tokenizer.pad_token_id
model.config.use_cache = False


# ============================================================
# 6. CONFIGURE LORA
# ============================================================

print("Configuring LoRA...")

lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
)

model = get_peft_model(model, lora_config)

model.print_trainable_parameters()


# ============================================================
# 7. TOKENIZE DATASET
# ============================================================

def tokenize_example(example):

    prompt_messages = [
        {
            "role": "user",
            "content": example["question"].strip(),
        }
    ]

    full_messages = [
        {
            "role": "user",
            "content": example["question"].strip(),
        },
        {
            "role": "assistant",
            "content": example["answer"].strip(),
        },
    ]

    prompt_ids = tokenizer.apply_chat_template(
        prompt_messages,
        tokenize=True,
        add_generation_prompt=True,
    )

    full_ids = tokenizer.apply_chat_template(
        full_messages,
        tokenize=True,
        add_generation_prompt=False,
    )

    # Verify that the prompt is the exact prefix
    # of the complete conversation.

    if full_ids[:len(prompt_ids)] != prompt_ids:
        raise ValueError(
            "Chat template token mismatch. "
            "Training stopped before starting."
        )

    if len(prompt_ids) >= MAX_LENGTH:
        raise ValueError(
            "Question exceeds the available token limit. "
            "Increase MAX_LENGTH after reviewing the dataset."
        )

    input_ids = full_ids[:MAX_LENGTH]

    labels = input_ids.copy()

    # Ignore the question during loss calculation.
    prompt_length = len(prompt_ids)

    labels[:prompt_length] = (
        [-100] * prompt_length
    )

    # Padding
    attention_mask = [1] * len(input_ids)

    padding_length = MAX_LENGTH - len(input_ids)

    input_ids += (
        [tokenizer.pad_token_id] * padding_length
    )

    attention_mask += (
        [0] * padding_length
    )

    labels += (
        [-100] * padding_length
    )

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
    }


print("Tokenizing dataset...")

tokenized_examples = [
    tokenize_example(item)
    for item in data
]

for index, item in enumerate(tokenized_examples):

    if not any(label != -100 for label in item["labels"]):
        raise ValueError(
            f"No answer tokens available in example {index}"
        )

train_dataset = Dataset.from_list(
    tokenized_examples
)

print(
    f"Tokenization completed: {len(train_dataset)} examples"
)


# ============================================================
# 8. TRAINING CONFIGURATION
# ============================================================

training_args = TrainingArguments(

    output_dir=str(OUTPUT_DIR),

    num_train_epochs=NUM_EPOCHS,

    per_device_train_batch_size=BATCH_SIZE,

    gradient_accumulation_steps=(
        GRADIENT_ACCUMULATION_STEPS
    ),

    learning_rate=LEARNING_RATE,

    weight_decay=0.01,

    logging_steps=1,

    save_strategy="epoch",

    save_total_limit=2,

    report_to="none",

    use_cpu=(device_name == "CPU"),

    fp16=False,

    bf16=False,

    dataloader_pin_memory=False,

    optim="adamw_torch",

    seed=RANDOM_SEED,
)


# ============================================================
# 9. INITIALIZE TRAINER
# ============================================================

trainer = Trainer(

    model=model,

    args=training_args,

    train_dataset=train_dataset,

    data_collator=default_data_collator,

    processing_class=tokenizer,
)


# ============================================================
# 10. START TRAINING
# ============================================================

print("\nStarting Marketing AI fine-tuning...")

print(f"Device: {device_name}")
print(f"Dataset size: {len(train_dataset)}")
print(f"Epochs: {NUM_EPOCHS}")
print(f"Learning rate: {LEARNING_RATE}")
print(f"Batch size: {BATCH_SIZE}")

trainer.train()


# ============================================================
# 11. SAVE NEW LORA ADAPTER
# ============================================================

print("\nSaving the new adapter...")

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

trainer.model.save_pretrained(
    OUTPUT_DIR
)

tokenizer.save_pretrained(
    OUTPUT_DIR
)

print("\n====================================")
print("FINE-TUNING COMPLETED SUCCESSFULLY")
print("====================================")

print(f"New adapter saved at: {OUTPUT_DIR}")

print("Original adapter remains unchanged.")