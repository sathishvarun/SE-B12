
import os
import tempfile

import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate


# --------------------------------------------------
# 1. Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Multi-PDF RAG Assistant",
    page_icon="📚",
    layout="wide",
)

st.title("📚 Multi-PDF RAG Assistant")
st.write(
    "Upload multiple business PDFs, index them together, "
    "and ask questions with file and page citations."
)


# --------------------------------------------------
# 2. Initialize session state
# --------------------------------------------------

if "store" not in st.session_state:
    st.session_state.store = None

if "chunk_count" not in st.session_state:
    st.session_state.chunk_count = 0

if "indexed_files" not in st.session_state:
    st.session_state.indexed_files = []


# --------------------------------------------------
# 3. Read API key from environment
# --------------------------------------------------

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error(
        "OPENAI_API_KEY is missing. Set it in your "
        "terminal and restart Streamlit."
    )
    st.stop()


# --------------------------------------------------
# 4. Upload multiple PDFs
# --------------------------------------------------

uploaded_files = st.file_uploader(
    "Upload one or more PDF documents",
    type=["pdf"],
    accept_multiple_files=True,
)


# --------------------------------------------------
# 5. Index all PDFs into one FAISS database
# --------------------------------------------------

if st.button("Build / Rebuild Vector Database"):

    if not uploaded_files:
        st.warning("Please upload at least one PDF.")

    else:
        all_documents = []

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n\n", "\n", " ", ""],
        )

        with st.spinner("Reading and processing PDFs..."):

            try:
                for uploaded_file in uploaded_files:

                    # Save uploaded PDF temporarily
                    temp_path = None

                    try:
                        with tempfile.NamedTemporaryFile(
                            suffix=".pdf",
                            delete=False,
                        ) as temp_file:

                            temp_file.write(
                                uploaded_file.getvalue()
                            )

                            temp_path = temp_file.name

                        # Load each PDF page
                        loader = PyPDFLoader(temp_path)
                        pages = loader.load()

                        # Preserve the original filename.
                        # PyPDFLoader page numbers start at 0,
                        # so convert them to human-readable pages.
                        for page in pages:
                            page.metadata["source"] = (
                                uploaded_file.name
                            )

                            page.metadata["page"] = (
                                int(page.metadata.get("page", 0)) + 1
                            )

                        # Split each document into smaller chunks
                        chunks = splitter.split_documents(pages)

                        all_documents.extend(chunks)

                    finally:
                        if temp_path and os.path.exists(temp_path):
                            os.remove(temp_path)

                if not all_documents:
                    st.error(
                        "No readable text was found in the PDFs."
                    )
                    st.stop()

                # Create embeddings and ONE shared vector database
                embeddings = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    api_key=api_key,
                )

                new_store = FAISS.from_documents(
                    all_documents,
                    embeddings,
                )

                # Save the index in Streamlit session state
                st.session_state.store = new_store
                st.session_state.chunk_count = len(all_documents)
                st.session_state.indexed_files = [
                    f.name for f in uploaded_files
                ]

                st.success(
                    f"Successfully indexed "
                    f"{len(all_documents)} chunks."
                )

            except Exception as error:
                st.error(f"Indexing failed: {error}")


# --------------------------------------------------
# 6. Display index information
# --------------------------------------------------

if st.session_state.store is not None:

    st.subheader("Indexed Documents")

    st.write(
        "Files: "
        + ", ".join(st.session_state.indexed_files)
    )

    st.metric(
        "Total chunks indexed",
        st.session_state.chunk_count,
    )

    st.divider()


# --------------------------------------------------
# 7. Ask a question
# --------------------------------------------------

st.subheader("Ask a Question")

question = st.text_input(
    "Enter your question",
    placeholder=(
        "Example: How many annual leave days do new joiners get?"
    ),
)

if st.button("Get Answer"):

    if st.session_state.store is None:
        st.warning(
            "Please upload PDFs and build the vector database first."
        )

    elif not question.strip():
        st.warning("Please enter a question.")

    else:
        with st.spinner("Searching documents and generating answer..."):

            try:
                # Retrieve the most relevant chunks
                retriever = st.session_state.store.as_retriever(
                    search_kwargs={"k": 6}
                )

                retrieved_docs = retriever.invoke(question)

                if not retrieved_docs:
                    st.warning("No relevant document chunks were found.")
                    st.stop()

                # Include source metadata with each retrieved chunk
                context_parts = []

                for doc in retrieved_docs:
                    filename = doc.metadata.get(
                        "source", "Unknown file"
                    )
                    page_number = doc.metadata.get(
                        "page", "Unknown page"
                    )

                    context_parts.append(
                        f"[Source: {filename}, Page: {page_number}]\n"
                        f"{doc.page_content}"
                    )

                context = "\n\n".join(context_parts)

                # Tell the model how to handle conflicting information
                prompt = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            """
You are a document question-answering assistant.

Answer using only the supplied document excerpts.

Rules:
1. Do not invent facts that are not in the excerpts.
2. If the documents disagree, explicitly say that
   conflicting information was found.
3. Explain each conflicting value and identify the
   file and page where it appears.
4. If the answer is not supported by the excerpts,
   say that the available documents do not provide
   enough information.
5. Distinguish a document's stated policy from a
   verified or legally binding policy.
6. Do not claim that every uploaded document was checked
   unless the retrieved evidence supports that statement.
7. Keep the answer clear and concise.

The application will display the retrieved source list
separately below your answer.
                            """,
                        ),
                        (
                            "human",
                            """
Question:
{question}

Retrieved document excerpts:
{context}

Answer the question based on these excerpts.
                            """,
                        ),
                    ]
                )

                # Generate the answer using OpenAI
                llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0,
                    api_key=api_key,
                )

                chain = prompt | llm

                response = chain.invoke(
                    {
                        "question": question,
                        "context": context,
                    }
                )

                st.subheader("Answer")
                st.write(response.content)

                # Display unique source filename + page combinations
                st.subheader("Sources")

                unique_sources = {}

                for doc in retrieved_docs:
                    filename = doc.metadata.get(
                        "source", "Unknown file"
                    )
                    page_number = doc.metadata.get(
                        "page", "Unknown page"
                    )

                    unique_sources[(filename, page_number)] = True

                for filename, page_number in unique_sources:
                    st.caption(
                        f"📄 {filename} — Page {page_number}"
                    )

            except Exception as error:
                st.error(f"Question answering failed: {error}")
