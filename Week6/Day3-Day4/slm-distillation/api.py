"""
STEP 4 - Serve the distilled student as a REST API (FastAPI + uvicorn).

Run:   uvicorn api:app --reload
Open:  http://127.0.0.1:8000/docs   (interactive Swagger UI to test it)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import STUDENT_MODEL, TEACHER_MODEL
from inference import StudentModel

state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading distilled student model...")
    state["model"] = StudentModel()
    print(f"Model ready on {state['model'].device}")
    yield
    state.clear()


app = FastAPI(
    title="SLM Distillation API",
    description="A small student model distilled from a larger teacher LLM.",
    version="1.0.0",
    lifespan=lifespan,
)


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, examples=["What is machine learning?"])
    max_new_tokens: int = Field(150, ge=1, le=512)
    temperature: float = Field(0.7, ge=0.0, le=2.0)


class GenerateResponse(BaseModel):
    prompt: str
    response: str


@app.get("/")
def health():
    return {
        "status": "ok",
        "teacher": TEACHER_MODEL,
        "student_base": STUDENT_MODEL,
        "device": state["model"].device if "model" in state else None,
    }


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    try:
        text = state["model"].generate(req.prompt, req.max_new_tokens, req.temperature)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return GenerateResponse(prompt=req.prompt, response=text)
