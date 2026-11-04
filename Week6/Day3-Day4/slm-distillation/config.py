"""
Central configuration for the Teacher -> Student distillation project.
Change models or training settings here, and every script picks them up.
"""
import torch

# ---------------------------------------------------------------------------
# Models (both from Hugging Face; both share the same tokenizer, which is
# required for logit-level distillation)
# ---------------------------------------------------------------------------
TEACHER_MODEL = "HuggingFaceTB/SmolLM2-360M-Instruct"   # ~720 MB  - the "teacher" / parent
STUDENT_MODEL = "HuggingFaceTB/SmolLM2-135M"            # ~270 MB  - the "student" / sub model

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROMPTS_FILE = "data/prompts.txt"              # questions the teacher will answer
DISTILL_FILE = "data/distill_dataset.jsonl"    # teacher answers (created in Step 1)
STUDENT_OUTPUT_DIR = "models/student-distilled"  # trained student (created in Step 2)

# ---------------------------------------------------------------------------
# Prompt format used for training AND inference (must be identical)
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE = "### Question:\n{prompt}\n\n### Answer:\n"

# ---------------------------------------------------------------------------
# Step 1 - teacher generation
# ---------------------------------------------------------------------------
TEACHER_MAX_NEW_TOKENS = 160

# ---------------------------------------------------------------------------
# Step 2 - distillation training
# ---------------------------------------------------------------------------
EPOCHS = 3
BATCH_SIZE = 4
LEARNING_RATE = 5e-5
MAX_SEQ_LEN = 256
TEMPERATURE = 2.0   # softens teacher probabilities so the student learns "dark knowledge"
ALPHA = 0.5         # 0.5 = half KL loss (imitate teacher), half CE loss (match teacher text)
SEED = 42


def get_device() -> str:
    """Apple Silicon GPU (mps) on Mac, CUDA on NVIDIA, otherwise CPU."""
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"
