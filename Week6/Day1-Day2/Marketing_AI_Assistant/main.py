
import os
import secrets
import traceback
from pathlib import Path
from contextlib import asynccontextmanager

import torch
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

from rag_pipeline import MarketingRAG


# ==================================================
# 1. PROJECT CONFIGURATION
# ==================================================

PROJECT_DIR = Path(__file__).resolve().parent

load_dotenv(PROJECT_DIR / ".env")

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

ADAPTER_DIR = (
    PROJECT_DIR
    / "model"
    / "marketing-llm-finetuned-v2"
)

API_KEY = os.getenv("MARKETING_API_KEY")

if torch.backends.mps.is_available():
    DEVICE = "mps"
elif torch.cuda.is_available():
    DEVICE = "cuda"
else:
    DEVICE = "cpu"

tokenizer = None
model = None
rag = None


# ==================================================
# 2. LOAD MODEL AND RAG DURING STARTUP
# ==================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    global tokenizer, model, rag

    if not API_KEY:
        raise RuntimeError(
            "MARKETING_API_KEY is missing from .env"
        )

    if not ADAPTER_DIR.exists():
        raise FileNotFoundError(
            f"V2 adapter folder not found: {ADAPTER_DIR}"
        )

    print("Loading tokenizer...")

    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = (
        torch.float16
        if DEVICE == "cuda"
        else torch.float32
    )

    print("Loading base model...")

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        dtype=dtype
    )

    base_model.to(DEVICE)

    print("Loading V2 LoRA adapter...")

    model = PeftModel.from_pretrained(
        base_model,
        str(ADAPTER_DIR)
    )

    model.eval()

    print("Loading RAG knowledge base...")

    rag = MarketingRAG()

    print("======================================")
    print("Marketing AI Assistant is ready.")
    print(f"Device: {DEVICE}")
    print("Adapter: marketing-llm-finetuned-v2")
    print("RAG: Loaded")
    print("======================================")

    yield

    model = None
    tokenizer = None
    rag = None


# ==================================================
# 3. FASTAPI APPLICATION
# ==================================================

app = FastAPI(
    title="Marketing AI Assistant API",
    description="Marketing AI Assistant with Qwen, LoRA V2 and RAG",
    version="2.1",
    lifespan=lifespan
)


# ==================================================
# 4. REQUEST MODEL
# ==================================================

class ChatRequest(BaseModel):

    question: str = Field(
        min_length=1,
        max_length=5000
    )

    max_new_tokens: int = Field(
        default=300,
        ge=1,
        le=500
    )

    use_rag: bool = True


# ==================================================
# 5. API AUTHENTICATION
# ==================================================

def verify_api_key(x_api_key: str):

    if not API_KEY or not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )

    if not secrets.compare_digest(
        x_api_key,
        API_KEY
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )


# ==================================================
# 6. ROOT ENDPOINT
# ==================================================

@app.get("/")
def root():

    return {
        "message": "Marketing AI Assistant API is running",
        "version": "2.1"
    }


# ==================================================
# 7. HEALTH CHECK ENDPOINT
# ==================================================

@app.get("/health")
def health():

    return {
        "status": "running",
        "model_loaded": model is not None,
        "rag_loaded": rag is not None,
        "adapter": "marketing-llm-finetuned-v2",
        "device": DEVICE
    }


# ==================================================
# 8. GENERATE ANSWER ENDPOINT
# ==================================================

@app.post("/generate")
def generate(
    request: ChatRequest,
    x_api_key: str = Header(default=None)
):

    try:

        # Verify API authentication
        verify_api_key(x_api_key)

        # Check model availability
        if model is None or tokenizer is None:
            raise HTTPException(
                status_code=503,
                detail="Model is not loaded"
            )

        retrieved = []

        # --------------------------------------------------
        # RAG RETRIEVAL
        # --------------------------------------------------

        if request.use_rag:

            if rag is None:
                raise HTTPException(
                    status_code=503,
                    detail="RAG system is not loaded"
                )

            retrieved = rag.search(
                request.question,
                top_k=3
            )

        # --------------------------------------------------
        # BUILD REFERENCE CONTEXT
        # --------------------------------------------------

        if retrieved:

            context = "\n\n".join(
                (
                    f"Source: {item['source']}\n"
                    f"Category: {item['category']}\n"
                    f"Content: {item['text']}"
                )
                for item in retrieved
            )

        else:

            context = (
                "No reference documents were retrieved. "
                "Answer using your existing knowledge, "
                "and do not invent unsupported facts."
            )

        # --------------------------------------------------
        # BUILD PROMPT
        # --------------------------------------------------

        prompt = f"""You are a Marketing AI Assistant.

Answer the user's question accurately and clearly.

Instructions:
- Use the reference context when relevant.
- Do not invent facts, product features or procedures.
- If the reference context does not contain the answer,
  clearly acknowledge that limitation.
- Explain technical concepts in simple professional English.
- Provide practical examples when supported by the context.

Reference context:

{context}

User question:

{request.question}
"""

        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]

        # --------------------------------------------------
        # TOKENIZATION
        # --------------------------------------------------

        inputs = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt"
        )

        # Move BatchEncoding tensors to the selected device.
        inputs = inputs.to(DEVICE)

        # --------------------------------------------------
        # MODEL GENERATION
        # --------------------------------------------------

        with torch.inference_mode():

            output = model.generate(
                **inputs,
                max_new_tokens=request.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )

        # --------------------------------------------------
        # DECODE ANSWER
        # --------------------------------------------------

        input_length = inputs["input_ids"].shape[1]

        generated_tokens = output[
            0,
            input_length:
        ]

        answer = tokenizer.decode(
            generated_tokens,
            skip_special_tokens=True
        ).strip()

        # --------------------------------------------------
        # API RESPONSE
        # --------------------------------------------------

        return {
            "answer": answer,
            "used_rag": bool(retrieved),
            "sources": [
                {
                    "source": item["source"],
                    "category": item["category"],
                    "similarity": round(
                        item["score"],
                        4
                    )
                }
                for item in retrieved
            ]
        }

    except HTTPException:

        raise

    except Exception as exc:

        print("\n========== GENERATION ERROR ==========")

        traceback.print_exc()

        print("======================================\n")

        raise HTTPException(
            status_code=500,
            detail=(
                f"Generation failed: "
                f"{type(exc).__name__}: {exc}"
            )
        )


# ==================================================
# END OF MAIN.PY
# ==================================================
