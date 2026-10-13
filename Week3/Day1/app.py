import os

# 1. Silence telemetry and telemetry-related DNS warnings completely
os.environ["GUARDRAILS_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

import openai
from guardrails import Guard
from guardrails_ai.toxic_language import ToxicLanguage
from guardrails_ai.provenance_embeddings import ProvenanceEmbeddings

# 2. Configure the Guard using .use() chaining
guard = (
    Guard()
    .use(ToxicLanguage(threshold=0.5, on_fail="filter"))
    .use(ProvenanceEmbeddings(threshold=0.75, on_fail="reask"))
)


def evaluate_static_text():
    """Evaluate pre-generated outputs against reference context."""
    print("--- 1. Evaluating Pre-generated Text ---")

    # Pass as multiple distinct strings to prevent numpy AxisError (1D array)
    reference_sources = [
        "All subscription plans come with a 30-day money-back guarantee.",
        "Support is available 24/7 via live chat and email."
    ]

    sample_llm_output = (
        "You can request a full refund within 30 days of subscribing. "
        "Customer support is active around the clock."
    )

    # Run validation (use 'sources' key for ProvenanceEmbeddings)
    result = guard.validate(
        sample_llm_output,
        metadata={"sources": reference_sources}
    )

    print(f"Validation Passed : {result.validation_passed}")
    print(f"Validated Output  : {result.validated_output}\n")


def evaluate_live_llm_call():
    """Wrap an active OpenAI completion call with real-time validation."""
    print("--- 2. Evaluating Live LLM Generation ---")

    # Reference sources chunked into multiple strings
    reference_sources = [
        "Project Apollo launched on July 16, 1969.",
        "It carried three astronauts to the Moon."
    ]

    try:
        # Guard wraps the standard openai call directly
        response = guard(
            openai.chat.completions.create,
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Answer the user question factually using only the provided context."
                },
                {
                    "role": "user",
                    "content": "When did Project Apollo launch and how many astronauts were on board?"
                }
            ],
            metadata={"sources": reference_sources}
        )

        print(f"Validated Output  : {response.validated_output}")
        print(f"Raw Output        : {response.raw_llm_output}\n")
    except Exception as e:
        print(f"LLM validation error: {e}\n")


if __name__ == "__main__":
    # Test 1: Static validation (no OpenAI API key required)
    evaluate_static_text()

    # Test 2: Live validation (requires valid OPENAI_API_KEY environment variable)
    if os.getenv("OPENAI_API_KEY"):
        evaluate_live_llm_call()
    else:
        print("Note: Set OPENAI_API_KEY to test evaluate_live_llm_call().")