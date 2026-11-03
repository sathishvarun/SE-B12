# Marketing AI Assistant

An AI-powered marketing knowledge assistant built with FastAPI,
Streamlit, Hugging Face Transformers, PEFT/LoRA, Sentence Transformers,
and FAISS.

## Project status

-   [x] Qwen2.5 base model and V2 LoRA adapter load successfully.
-   [x] FastAPI backend starts and exposes `/health`.
-   [x] API-key authentication is implemented.
-   [x] Text generation works with RAG disabled.
-   [x] RAG retrieval and generation work with RAG enabled.
-   [ ] Complete end-to-end validation through the Streamlit interface.
-   [ ] Expand the knowledge base with approved marketing documentation.

## Architecture

``` text
User
 |
 v
Streamlit UI (app.py)
 |
 | HTTP request + X-API-Key
 v
FastAPI backend (main.py)
 |
 +--> Qwen2.5 base model + V2 LoRA adapter
 |
 +--> MarketingRAG (when use_rag=true)
        |
        +--> Sentence Transformers embeddings
        +--> FAISS vector index
        +--> Knowledge-base chunks and metadata
 |
 v
Generated answer + source details
```

## Technology stack

  Component       Technology
  --------------- ------------------------------------------
  Base model      Qwen/Qwen2.5-0.5B-Instruct
  Fine-tuning     SFT with PEFT/LoRA
  Adapter         `model/marketing-llm-finetuned-v2`
  Backend         FastAPI, Uvicorn
  Frontend        Streamlit
  Embeddings      `sentence-transformers/all-MiniLM-L6-v2`
  Vector search   FAISS
  ML framework    PyTorch, Transformers

## Project structure

``` text
Marketing_AI_Assistant/
├── app.py
├── main.py
├── rag_pipeline.py
├── ingest_documents.py
├── build_vector_db.py
├── training_dataset.json
├── training_dataset_v2.json
├── evaluation_questions.json
├── compare_adapters.py
├── evaluate_comparison.py
├── knowledge_base/
│   ├── eloqua/
│   ├── marketo/
│   ├── webinar_operations/
│   ├── lead_nurturing/
│   └── crm_integration/
├── model/
├── vector_store/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Prerequisites

-   Python 3.12 recommended
-   Git
-   Internet access to download the Hugging Face model and dependencies
-   Adequate memory and disk space for model files

## Installation

Clone the repository and enter the project directory. Adjust the path if
your project is stored elsewhere:

``` bash
git clone https://github.com/sathishvarun/SE-B12.git
cd SE-B12/Week6/Day2/Marketing_AI_Assistant
```

Create and activate a virtual environment:

``` bash
python3.12 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

``` powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

``` bash
pip install --upgrade pip
pip install -r requirements.txt
```

If `requirements.txt` does not exist yet, create it from the working
environment and review the contents before committing:

``` bash
pip freeze > requirements.txt
```

## Environment configuration

Create `.env` from the example:

``` bash
cp .env.example .env
```

Set your own secret in `.env`:

``` env
MARKETING_API_KEY=replace_with_a_long_random_secret
```

Never commit `.env`, API keys, access tokens, or other credentials. Keep
`.env.example` placeholder-only.

## Prepare the RAG knowledge base

Add approved reference documents to the appropriate folders under
`knowledge_base/`, then run:

``` bash
python ingest_documents.py
python build_vector_db.py
```

The ingestion script is designed to process PDF, DOCX, and TXT
documents. Check the implementation for the exact supported formats and
extraction behaviour.

Only add documents you are authorised to use. Do not include
confidential customer information or personal data.

## Run the application

### 1. Start FastAPI

``` bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Health check:

``` bash
curl http://127.0.0.1:8000/health
```

### 2. Start Streamlit

Open a second terminal, activate the same virtual environment, and run:

``` bash
streamlit run app.py --server.port 8503
```

Open `http://localhost:8503` (or the URL printed by Streamlit). Keep the
FastAPI terminal running.

## API

### Health

``` http
GET /health
```

### Generate

``` http
POST /generate
X-API-Key: YOUR_MARKETING_API_KEY
Content-Type: application/json
```

Example request:

``` json
{
  "question": "What is Eloqua Campaign Canvas?",
  "max_new_tokens": 150,
  "use_rag": true
}
```

Example response shape:

``` json
{
  "answer": "Generated marketing answer...",
  "used_rag": true,
  "sources": [
    {
      "source": "eloqua/eloqua_basics.txt",
      "category": "eloqua",
      "similarity": 0.5698
    }
  ]
}
```

The answer and similarity value are illustrative; actual results depend
on the indexed documents and model output.

## Validation performed

Local backend tests confirmed:

  Test                                       Result
  ------------------------------------------ -------------------------------------
  `/health` endpoint                         Passed
  Generation with `use_rag=false`            HTTP 200
  Generation with `use_rag=true`             HTTP 200
  RAG source retrieval                       Returned `eloqua/eloqua_basics.txt`
  V2 LoRA adapter                            Loaded successfully
  Runtime device in the tested environment   Apple MPS

The test knowledge base contained one Eloqua text chunk. Add more
relevant documents and rebuild the vector index to improve topic
coverage. Streamlit end-to-end validation remains to be completed.

## GitHub upload and large files

Before pushing:

1.  Ensure `.env`, virtual environments, caches, and local secrets are
    excluded.
2.  Do not blindly commit model weights, large vector indexes, or
    private source documents.
3.  Use Git LFS or external model/artifact storage if model adapters or
    other large assets need version control.
4.  Commit source code, authorised datasets, dependency files,
    `.env.example`, and documentation.
5.  Test installation and startup from a clean clone.

Suggested `.gitignore`:

``` gitignore
.env
.env.*
!.env.example
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
.venv-*/
venv/
.DS_Store
.vscode/
*.log

# Generated RAG artifacts; track only if intentionally required
document_chunks.jsonl
vector_store/

# Model weights/adapters; use Git LFS or external artifact storage if required
model/
```

If you intentionally want to version the vector index or model adapters,
review and adjust the relevant ignore rules and use a suitable
large-file strategy. Do not upload secrets.

## Next improvements

-   Finish Streamlit end-to-end testing.
-   Add more reviewed Eloqua, Marketo, webinar, lead-nurturing, and CRM
    documents.
-   Add automated tests for authentication, generation, and retrieval.
-   Evaluate retrieval relevance and answer quality.
-   Add production logging, request limits, HTTPS, and secure secret
    management before public deployment.

## Disclaimer

This is a development project. AI-generated answers may be incomplete or
inaccurate. Verify important platform procedures against current
official documentation before using them operationally.
