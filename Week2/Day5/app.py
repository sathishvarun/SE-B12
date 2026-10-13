# app.py
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnablePassthrough
from rag_store import init_vector_store

load_dotenv()

st.set_page_config(page_title="SK Mini Mart AI Shopping Assistant", page_icon="🌾", layout="centered")

# Initialize RAG vectorstore
@st.cache_resource
def get_retriever():
    return init_vector_store()

retriever = get_retriever()

# Sidebar: Kept minimal only for store info and clearing conversation
with st.sidebar:
    st.header("🌾 SK Mini Mart")
    st.markdown("**Location:** Tamil Nadu, India")
    st.markdown("**Timings:** 7:00 AM - 9:30 PM (All Days)")
    st.markdown("**Payment:** Cash & UPI (GPay/PhonePe) at store")
    st.divider()
    if st.button("Start New Shopping Session"):
        st.session_state.messages = []
        st.rerun()

# Welcome message
if "messages" not in st.session_state:
    st.session_state.messages = [
        AIMessage(content=(
            "Hello! Welcome to SK Mini Mart.\n\n"
            "Tell me what items you want to buy (for example: *'I want 1kg Udhayam urad dal and 1L Idhayam gingelly oil'*), "
            "and I will calculate your itemized bill and running total right here in the chat!"
        ))
    ]

st.title("🌾 SK Mini Mart AI")
st.caption("Tell the assistant what you need—it will track your shopping list and calculate your total amount live.")

# Render chat history
for msg in st.session_state.messages:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(msg.content)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# Conversational Shopping Prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an intelligent billing and shopping assistant for SK Mini Mart in Tamil Nadu.
Your job is to answer grocery questions AND maintain a live shopping list with total bill calculations inside the conversation.

Rules:
1. CURRENCY: Always show prices in Indian Rupees (₹ or Rs.).
2. SHOPPING LIST & TOTAL BILL:
   - When a user indicates they are buying, selecting, or adding items (e.g., "Add 1kg Udhayam urad dal", "I am buying 2 packs of Aachi chilli powder"), remember all selected items across previous conversation turns.
   - Present the current shopping summary in a neat Markdown table or bullet points:
       * Item & Brand
       * Unit Price
       * Quantity
       * Line Total
   - Always conclude with the clear **Final Total Amount: ₹XX.XX**.
3. QUERIES & PRICE CHECKS:
   - If the user is just asking questions (e.g., "What brands of rice do you have?"), provide the brand comparisons and prices normally without forcing a total unless they confirm they want to buy.
4. OUT OF STOCK / MISSING ITEMS:
   - If an item requested is not in the store catalog, notify them politely and do not add it to the bill.
5. LOCAL TERMINOLOGY:
   - Understand local names: Malli thool (Coriander powder), Milagai thool (Chilli powder), Nallennai (Gingelly oil), Ulundhu (Urad dal), Thuvaram paruppu (Toor dal).

Retrieved Store Inventory:
{context}"""),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

# RAG execution chain
rag_chain = (
    RunnablePassthrough.assign(
        context=lambda x: format_docs(retriever.invoke(x["input"]))
    )
    | prompt
    | llm
)

# Chat input
user_input = st.chat_input("E.g., 'I want 1 pack of Aachi Sambar powder and 1L Gold Winner oil. What is my total?'")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Calculating bill and checking inventory..."):
            response = rag_chain.invoke({
                "history": st.session_state.messages,
                "input": user_input
            })
            st.markdown(response.content)

    st.session_state.messages.append(HumanMessage(content=user_input))
    st.session_state.messages.append(AIMessage(content=response.content))