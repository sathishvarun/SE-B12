
import os
import requests
import streamlit as st
from dotenv import load_dotenv

# Project configuration
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_DIR, ".env"))

API_URL = "http://127.0.0.1:8000/generate"
API_KEY = os.getenv("MARKETING_API_KEY")

st.set_page_config(
    page_title="Marketing AI Assistant",
    page_icon="🤖",
    layout="centered",
)

# Page heading
st.title("🤖 Marketing AI Assistant")
st.caption("Qwen 2.5 0.5B + Marketing Fine-Tuned LoRA V2")

st.write(
    "Ask questions about Oracle Eloqua, Marketo, marketing automation, "
    "webinar operations, lead nurturing and email campaigns."
)

# Sidebar
with st.sidebar:
    st.header("Model information")
    st.write("**Base model:** Qwen/Qwen2.5-0.5B-Instruct")
    st.write("**Adapter:** marketing-llm-finetuned-v2")
    st.write("**Backend:** FastAPI")
    st.write("**API endpoint:** Port 8000")

    if st.button("Check backend health"):
        try:
            health = requests.get(
                "http://127.0.0.1:8000/health",
                timeout=10,
            )
            if health.ok:
                st.success(f"Backend: {health.json()}")
            else:
                st.error(f"Backend returned HTTP {health.status_code}")
        except requests.RequestException as exc:
            st.error(f"Backend connection failed: {exc}")

    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

# Check API key
if not API_KEY:
    st.error(
        "MARKETING_API_KEY is missing. "
        "Please check your project .env file."
    )
    st.stop()

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])

# Chat input
question = st.chat_input("Ask your Marketing AI Assistant...")

if question:
    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Marketing AI is preparing your answer..."):
            try:
                response = requests.post(
                    API_URL,
                    headers={
                        "X-API-Key": API_KEY,
                        "Content-Type": "application/json",
                    },
                    json={
                        "question": question,
                        "max_new_tokens": 300,
                    },
                    timeout=180,
                )

                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("answer", "")

                    if answer:
                        st.markdown(answer)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": answer}
                        )
                    else:
                        st.warning("The backend returned an empty answer.")

                elif response.status_code == 401:
                    st.error(
                        "API authentication failed. "
                        "Check MARKETING_API_KEY in your .env file."
                    )
                else:
                    st.error(
                        f"API error: HTTP {response.status_code}\n\n"
                        f"{response.text}"
                    )

            except requests.exceptions.Timeout:
                st.error("The request timed out. Please try again.")

            except requests.exceptions.ConnectionError:
                st.error(
                    "Cannot connect to FastAPI. "
                    "Make sure the backend is running on port 8000."
                )

            except requests.RequestException as exc:
                st.error(f"Request failed: {exc}")
