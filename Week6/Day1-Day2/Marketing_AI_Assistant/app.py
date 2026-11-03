import os
import torch
import streamlit as st
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ADAPTER_DIR = os.path.join(PROJECT_DIR, "model", "marketing-llm-finetuned")

st.set_page_config(
    page_title="Marketing AI Assistant",
    page_icon="🤖",
    layout="centered",
)

@st.cache_resource(show_spinner="Loading the base model and your fine-tuned adapter...")
def load_assistant():
    required = ["adapter_config.json", "adapter_model.safetensors"]
    missing = [f for f in required if not os.path.isfile(os.path.join(ADAPTER_DIR, f))]
    if missing:
        raise FileNotFoundError(
            "Missing adapter file(s): " + ", ".join(missing) +
            f"\nExpected folder: {ADAPTER_DIR}"
        )

    # Load the tokenizer from the original Qwen base model.
    # The adapter folder contains LoRA weights; its tokenizer_config.json
    # may have an incompatible extra_special_tokens format.
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if torch.cuda.is_available():
        device = "cuda"
        dtype = torch.float16
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        # float32 is selected for broad MPS compatibility on Apple Silicon.
        device = "mps"
        dtype = torch.float32
    else:
        device = "cpu"
        dtype = torch.float32

    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=dtype,
    )
    base.to(device)

    model = PeftModel.from_pretrained(base, ADAPTER_DIR)
    model.eval()
    return tokenizer, model, device

def answer_question(question, tokenizer, model, device, max_new_tokens=180):
    messages = [{"role": "user", "content": question}]
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    new_tokens = output[0, inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

st.title("🤖 Marketing AI Assistant")
st.caption("Qwen 2.5 0.5B + your saved LoRA adapter")
st.write(
    "Ask questions about Marketo, Eloqua, marketing automation, "
    "webinar operations, lead nurturing and email campaigns."
)

with st.sidebar:
    st.header("Model information")
    st.write(f"**Base model:** `{BASE_MODEL}`")
    st.write("**Adapter:** `model/marketing-llm-finetuned`")
    st.info("The first launch downloads the base model from Hugging Face. "
            "Keep an internet connection during the first load.")
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

try:
    tokenizer, model, device = load_assistant()
    st.sidebar.success(f"Model loaded · {device.upper()}")
except Exception as exc:
    st.error("The model could not be loaded.")
    st.exception(exc)
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])

question = st.chat_input("Ask your Marketing AI Assistant...")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Generating answer..."):
            try:
                response = answer_question(question, tokenizer, model, device)
                st.markdown(response or "_The model returned an empty response._")
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )
            except Exception as exc:
                st.error(f"Answer generation failed: {exc}")
