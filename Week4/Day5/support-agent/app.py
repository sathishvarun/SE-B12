"""
Customer Support Agent — web app on localhost (Streamlit)

Run:   streamlit run app.py
Open:  http://localhost:8501

Pages
  💬 Customer Chat   – customer asks; Step 1 RAG → Step 2 Web → Step 3 manual form
  🎫 Tickets         – see every manual entry, answer it (answer is added to RAG)
  📚 Knowledge Base  – upload your PDFs / docs and re-index them
"""
from pathlib import Path

import pandas as pd
import streamlit as st

import support_flow
from tools.rag_tool import KNOWLEDGE_DIR, MissingKeyError, add_text, ingest_folder, kb_count
from tools.ticket_store import list_tickets, update_ticket

st.set_page_config(page_title="Customer Support Agent", page_icon="🤖", layout="wide")

BADGES = {
    "Knowledge Base (RAG)": "📗 Answered from your content (Step 1 · RAG)",
    "Web Search": "🌐 Answered from the web (Step 2)",
    "Manual Entry → Escalation Agent": "📝 Ticket created (Step 3 · Manual entry)",
}

if "messages" not in st.session_state:
    st.session_state.messages = []          # chat history
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None  # question waiting for the Step 3 form

# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("🤖 Support Agent")
    page = st.radio("Go to", ["💬 Customer Chat", "🎫 Tickets", "📚 Knowledge Base"])
    st.divider()
    st.caption("How answers are found")
    st.markdown("1. **Your content** (RAG)\n2. **Web search**\n3. **Manual entry** → saved as ticket")
    open_count = len(list_tickets("OPEN"))
    st.metric("Open tickets", open_count)
    if page == "💬 Customer Chat" and st.button("🧹 Clear chat"):
        st.session_state.messages = []
        st.session_state.pending_question = None
        st.rerun()


def show_message(msg: dict):
    with st.chat_message(msg["role"]):
        if msg.get("badge"):
            st.caption(msg["badge"])
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.caption("Sources: " + ", ".join(msg["sources"]))
        if msg.get("steps"):
            with st.expander("How the agents handled this"):
                for s in msg["steps"]:
                    st.write(s)


# ----------------------------------------------------------- page: chat
def chat_page():
    st.header("💬 Customer Support Chat")
    st.caption("Ask anything. The agents check your content first, then the web, "
               "and if neither has the answer they collect your details for the team.")

    for msg in st.session_state.messages:
        show_message(msg)

    # ---- STEP 3 form (shown only when steps 1 and 2 found nothing)
    if st.session_state.pending_question:
        with st.form("manual_entry", clear_on_submit=True):
            st.subheader("📝 Share your details")
            st.write(f"**Your question:** {st.session_state.pending_question}")
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Name *")
            email = c2.text_input("Email *")
            phone = c3.text_input("Phone")
            details = st.text_area("More details about your request")
            submitted = st.form_submit_button("Submit request", type="primary")

        if submitted:
            if not name.strip() or "@" not in email:
                st.error("Please enter your name and a valid email.")
            else:
                with st.spinner("Saving your request and creating a ticket..."):
                    ticket_id, message = support_flow.create_ticket(
                        st.session_state.pending_question, name.strip(), email.strip(),
                        phone.strip(), details.strip())
                st.session_state.messages.append({
                    "role": "assistant", "content": message,
                    "badge": f"{BADGES['Manual Entry → Escalation Agent']} · Ticket #{ticket_id}",
                })
                st.session_state.pending_question = None
                st.rerun()

    # ---- chat input
    question = st.chat_input("Type your question...",
                             disabled=bool(st.session_state.pending_question))
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    show_message(st.session_state.messages[-1])

    with st.chat_message("assistant"):
        with st.status("Agents are working on it...", expanded=False) as status:
            try:
                state = support_flow.run_support(question)
            except MissingKeyError as e:
                status.update(label="Setup needed", state="error")
                st.error(str(e))
                return
            except Exception as e:  # show any API / network error in the page
                status.update(label="Something went wrong", state="error")
                st.exception(e)
                return
            for s in state.steps:
                st.write(s)
            status.update(label="Done", state="complete")

    if state.needs_manual_entry:
        st.session_state.messages.append({
            "role": "assistant", "steps": state.steps,
            "badge": "🔎 Not found in your content or on the web",
            "content": "I couldn't find an answer to this. Please share your details "
                       "below and our team will get back to you.",
        })
        st.session_state.pending_question = question
    else:
        st.session_state.messages.append({
            "role": "assistant", "content": state.answer, "sources": state.sources,
            "badge": BADGES.get(state.answered_by, state.answered_by), "steps": state.steps,
        })
    st.rerun()


# --------------------------------------------------------- page: tickets
def tickets_page():
    st.header("🎫 Tickets (manual entries)")
    status = st.segmented_control("Show", ["All", "OPEN", "RESOLVED"], default="All")
    rows = list_tickets(None if status in (None, "All") else status)
    if not rows:
        st.info("No tickets yet. They appear here when a question goes to Step 3.")
        return

    df = pd.DataFrame(rows)[["id", "created_at", "status", "priority", "name",
                             "email", "phone", "question", "details", "summary", "answer"]]
    st.dataframe(df, hide_index=True, width="stretch")

    open_rows = [r for r in rows if r["status"] == "OPEN"]
    if not open_rows:
        return
    st.subheader("Answer a ticket")
    st.caption("Your answer is saved on the ticket AND added to the knowledge base, "
               "so the next customer gets it instantly in Step 1.")
    choice = st.selectbox("Open ticket", open_rows,
                          format_func=lambda r: f"#{r['id']} – {r['name']}: {r['question'][:70]}")
    with st.form("answer_ticket", clear_on_submit=True):
        st.write(f"**Question:** {choice['question']}")
        if choice.get("details"):
            st.write(f"**Details:** {choice['details']}")
        answer = st.text_area("Your answer *")
        if st.form_submit_button("Resolve & add to knowledge base", type="primary"):
            if not answer.strip():
                st.error("Please write an answer.")
            else:
                update_ticket(choice["id"], answer=answer.strip(), status="RESOLVED")
                add_text(f"ticket-{choice['id']}",
                         f"Q: {choice['question']}\nA: {answer.strip()}", f"ticket #{choice['id']}")
                st.success(f"Ticket #{choice['id']} resolved and added to the knowledge base.")
                st.rerun()


# --------------------------------------------------- page: knowledge base
def knowledge_page():
    st.header("📚 Knowledge Base (your content)")
    st.caption("Step 1 answers come only from these files. Supported: PDF, TXT, MD.")

    files = sorted(p for p in KNOWLEDGE_DIR.glob("**/*") if p.suffix.lower() in {".pdf", ".txt", ".md"})
    c1, c2 = st.columns(2)
    c1.metric("Files", len(files))
    try:
        c2.metric("Indexed chunks", kb_count())
    except MissingKeyError as e:
        st.error(str(e))
        return

    for p in files:
        st.write(f"📄 {p.name}  ·  {p.stat().st_size / 1024:.1f} KB")

    uploads = st.file_uploader("Add files", type=["pdf", "txt", "md"], accept_multiple_files=True)
    if uploads and st.button("Save & index uploaded files", type="primary"):
        for f in uploads:
            (KNOWLEDGE_DIR / Path(f.name).name).write_bytes(f.getbuffer())
        with st.spinner("Indexing..."):
            n = ingest_folder()
        st.success(f"Saved {len(uploads)} file(s). {n} chunks indexed.")
        st.rerun()

    if st.button("🔄 Re-index all files"):
        with st.spinner("Indexing..."):
            n = ingest_folder()
        st.success(f"{n} chunks indexed.")


{"💬 Customer Chat": chat_page, "🎫 Tickets": tickets_page,
 "📚 Knowledge Base": knowledge_page}[page]()
