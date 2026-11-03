# Marketing AI Assistant

An AI-powered marketing knowledge assistant built around a fine-tuned
Qwen2.5 language model and Retrieval-Augmented Generation (RAG). The
project combines a Streamlit user interface, a FastAPI service, a
PEFT/LoRA adapter, semantic document retrieval, and evaluation
utilities.

> **Project status:** The FastAPI health check and generation endpoint
> were tested successfully. Both generation without RAG and generation
> with RAG returned HTTP 200 in local testing. The RAG test retrieved
> `eloqua/eloqua_basics.txt`. Full Streamlit end-to-end validation
> remains to be completed.

## 1. Project objectives

-   Answer marketing operations questions using a domain-adapted
    language model.
-   Ground answers in approved internal knowledge-base documents through
    RAG.
-   Expose model functionality through an API.
-   Provide a simple interactive interface for users.
-   Fine-tune and compare LoRA adapters using marketing-focused
    question-and-answer data.
-   Evaluate model responses with repeatable evaluation questions and
    reports.

## 2. High-level architecture

``` text
User
 |
 v
Streamlit UI (app.py)
 |
 | HTTP request + API key
 v
FastAPI service (main.py)
 |
 +--> Qwen2.5-0.5B-Instruct base model
 |       |
 |       +--> PEFT / LoRA marketing adapter (V2)
 |
 +--> RAG pipeline (rag_pipeline.py), when enabled
         |
         +--> Knowledge-base documents
         +--> Text chunking and metadata
         +--> Sentence Transformers embeddings
         +--> FAISS similarity search
 |
 v
Generated answer + retrieval/source metadata
```

## 3. Technology stack and concepts

  ------------------------------------------------------------------------------------------
  Area                    Technology / concept                       Purpose
  ----------------------- ------------------------------------------ -----------------------
  Programming language    Python                                     Application, model,
                                                                     data and automation
                                                                     code

  Base LLM                `Qwen/Qwen2.5-0.5B-Instruct`               Generates
                                                                     natural-language
                                                                     answers

  Model adaptation        Supervised fine-tuning (SFT)               Adapts the base model
                                                                     to marketing-domain
                                                                     examples

  Parameter-efficient     PEFT / LoRA                                Trains a smaller
  fine-tuning                                                        adapter instead of
                                                                     updating every
                                                                     base-model parameter

  ML framework            PyTorch                                    Model execution and
                                                                     training

  Model tooling           Hugging Face Transformers                  Tokenizer, model
                                                                     loading and text
                                                                     generation

  Adapter tooling         Hugging Face PEFT                          Loading and applying
                                                                     LoRA adapters

  Backend/API             FastAPI                                    Exposes health and
                                                                     answer-generation
                                                                     endpoints

  ASGI server             Uvicorn                                    Runs the FastAPI
                                                                     application

  Frontend                Streamlit                                  Provides the
                                                                     interactive web
                                                                     application

  RAG                     Retrieval-Augmented Generation             Retrieves relevant
                                                                     knowledge before answer
                                                                     generation

  Embeddings              `sentence-transformers/all-MiniLM-L6-v2`   Converts text into
                                                                     semantic vectors

  Vector search           FAISS                                      Finds semantically
                                                                     similar document chunks

  Configuration           `python-dotenv`                            Loads local environment
                                                                     variables

  Data formats            JSON, JSONL, TXT, Markdown                 Training, evaluation
                                                                     and knowledge-base
                                                                     content

  Version control         Git and GitHub                             Tracks and publishes
                                                                     project source code
  ------------------------------------------------------------------------------------------

### Technologies not established as part of this implementation

-   **React:** The current user interface is implemented with Streamlit.
    React is not part of the confirmed application stack.
-   **pytest:** The project includes model-evaluation scripts and API
    checks described in this README, but a pytest test suite has not
    been confirmed. Do not describe pytest as implemented unless test
    files and a successful pytest run are added.
-   **Docker / cloud deployment:** These are not confirmed as part of
    the current validated application workflow.

## 4. Main project components

  -----------------------------------------------------------------------
  File / folder                       Responsibility
  ----------------------------------- -----------------------------------
  `app.py`                            Streamlit user interface

  `main.py`                           FastAPI application, model loading
                                      and generation endpoint

  `rag_pipeline.py`                   RAG retrieval and supporting
                                      pipeline logic

  `ingest_documents.py`               Processes knowledge-base source
                                      documents

  `build_vector_db.py`                Builds the vector index used for
                                      retrieval

  `train_model.py`                    Fine-tunes the model using the
                                      marketing training data

  `evaluate_model.py`                 Evaluates model output

  `compare_adapters.py`               Compares model adapters

  `evaluate_comparison.py`            Evaluates comparison results

  `run_evaluation.py`                 Runs the evaluation workflow

  `training_dataset.json`             Initial training examples

  `training_dataset_v2.json`          Updated training examples

  `evaluation_questions.json`         Questions used for evaluation

  `evaluation_results.json`           Saved evaluation output

  `adapter_comparison_results.json`   Adapter comparison output

  `adapter_evaluation_report.md`      Human-readable evaluation report

  `model_evaluation_results.json`     Model evaluation output

  `knowledge_base/`                   Source documents used by RAG

  `vector_store/`                     Generated vector index; rebuildable

  `model/`                            Local LoRA adapter/model artifacts
  -----------------------------------------------------------------------

## 5. AI and application concepts covered

1.  **Large Language Models (LLMs):** Using an instruction-tuned model
    to generate responses.
2.  **Prompt formatting and tokenization:** Preparing user questions in
    the format expected by the model.
3.  **Supervised fine-tuning:** Training with curated
    question-and-answer examples.
4.  **LoRA:** Efficiently adapting a pretrained model with a smaller set
    of trainable parameters.
5.  **Model and adapter loading:** Combining the base model with a
    selected marketing adapter.
6.  **Inference and generation:** Producing answers from input prompts
    with controlled generation settings.
7.  **Embeddings:** Representing documents and questions as numerical
    vectors.
8.  **Semantic search:** Finding relevant content by vector similarity
    rather than exact keyword matching.
9.  **RAG:** Supplying retrieved knowledge to the language model to
    improve grounding.
10. **Document ingestion and chunking:** Preparing source documents for
    retrieval.
11. **Metadata and source attribution:** Retaining document
    source/category details with retrieved chunks.
12. **REST API development:** Exposing model functions through HTTP
    endpoints.
13. **API-key authentication:** Protecting the generation endpoint with
    a configured key.
14. **Frontend/backend integration:** Calling the FastAPI service from
    Streamlit.
15. **Evaluation and comparison:** Running repeatable questions and
    comparing adapter/model outputs.
16. **Environment and dependency management:** Using a Python virtual
    environment and `requirements.txt`.
17. **Version control:** Committing selected project files and pushing
    them to GitHub.

## 6. Issues encountered and how they were addressed

The following table records the issues observed during development and
GitHub publishing. It distinguishes resolved issues from items that
still require validation.

  ------------------------------------------------------------------------------------------------------------------
                     \# Issue                Cause / symptom             Resolution or current status
  --------------------- -------------------- --------------------------- -------------------------------------------
                      1 Python environment   Multiple local virtual      Kept dependencies in `requirements.txt`;
                        and dependency setup environments and            used a project virtual environment. The
                                             Python/package              environments themselves are excluded from
                                             compatibility               Git.
                                             considerations              

                      2 Model loading and    The project had more than   Selected the V2 marketing adapter for the
                        adapter selection    one LoRA adapter/version    validated local API run.

                      3 Incorrect tensor     `torch.ones_like()` was     Updated generation to pass the tokenizer
                        handling during      applied to a                result as a batch using
                        generation           `BatchEncoding` object      `model.generate(**inputs, ...)` and obtain
                                             instead of a tensor         input length from `inputs["input_ids"]`.

                      4 Old API process      A new Uvicorn process       Identified the need to check the listening
                        still using port     reported                    process before restarting the backend. Use
                        8000                 `Address already in use`;   `lsof -nP -iTCP:8000 -sTCP:LISTEN` and stop
                                             an older process could      only the confirmed stale process.
                                             still serve stale code      

                      5 Streamlit port       Port 8503 was already       Check the process listening on that port or
                        conflict             occupied                    use another available port. Full UI
                                                                         end-to-end validation remains pending.

                      6 RAG retrieval and    Needed to confirm that      Tested generation with RAG disabled and
                        source verification  retrieval was actually used enabled. The RAG-enabled test returned HTTP
                                             rather than only model      200 and a source from
                                             generation                  `eloqua/eloqua_basics.txt`.

                      7 Large local files    Virtual environments were   Added ignore rules for virtual environments
                                             approximately 1.5 GB and    and model weights. Model artifacts should
                                             1.3 GB; local model         be distributed separately or managed with
                                             directory was approximately Git LFS if required.
                                             202 MB                      

                      8 Generated files in   Logs, cache files, chunks   Added `.gitignore` rules for logs, Python
                        the repository       and vector indexes are      cache, `document_chunks.jsonl`,
                                             generated locally           `vector_store/` and model weights.

                      9 Secrets risk         `.env` contains local       Excluded `.env` and `.env.*`; use a
                                             configuration/secrets       placeholder-only `.env.example` for
                                                                         sharing. Never commit credentials.

                     10 Git push rejected    GitHub `main` contained     Fetched `origin`; confirmed the remote had
                        (non-fast-forward)   commits not present in the  newer commits. A rebase attempt aborted
                                             original local checkout     with `could not detach HEAD`.

                     11 Untracked files      The original repository     Avoided staging the entire repository.
                        blocked a rebase     folder contained many       Created a separate fresh clone named
                                             unrelated untracked Week    `SE-B12-GitHub-Sync` to isolate the update.
                                             1--Week 5 and other project 
                                             files                       

                     12 Existing GitHub      The target folder already   Copied the latest project source into the
                        project already      contained an initial        existing target folder, while excluding
                        present              project version and a model local secrets, virtual environments,
                                             adapter                     generated files and the local model
                                                                         directory.

                     13 Verifying the copied Needed to ensure new files  Used `git status --short`; Git showed
                        project              were staged without adding  modified (`M`) and added (`A`) files under
                                             unrelated repository        only
                                             content                     `Week6/Day1-Day2/Marketing_AI_Assistant`.

                     14 Final GitHub         The latest files were       Commit and push from `SE-B12-GitHub-Sync`
                        publication          staged in the fresh clone   are the final publishing steps; verify the
                                                                         remote folder and clean Git status after
                                                                         pushing.
  ------------------------------------------------------------------------------------------------------------------

### Important Git lesson

Do not run `git add .` from the repository root when unrelated untracked
projects are present. Stage only the intended project path:

``` bash
git add Week6/Day1-Day2/Marketing_AI_Assistant
```

The original local repository and the fresh sync clone are separate
working copies. Continue the final publishing workflow from
`~/Downloads/SE-B12-GitHub-Sync`.

## 7. Local setup

### Prerequisites

-   Python 3.12 recommended for a compatible ML dependency environment.
-   Git.
-   Internet access for downloading dependencies and the base model on
    first run.
-   Adequate memory and disk space for model inference.
-   macOS or another supported Python environment; hardware acceleration
    depends on the installed PyTorch build.

### Clone and enter the project

``` bash
git clone https://github.com/sathishvarun/SE-B12.git
cd SE-B12/Week6/Day1-Day2/Marketing_AI_Assistant
```

### Create and activate a virtual environment

``` bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

``` bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 8. Environment configuration

Create a local `.env` file:

``` bash
cp .env.example .env
```

Example placeholder:

``` env
MARKETING_API_KEY=replace_with_a_long_random_secret
```

The exact environment-variable names must match the configuration read
by `main.py` and `app.py`. Keep real secrets in `.env` only. Commit
`.env.example` with placeholders, never real keys.

## 9. Prepare the RAG knowledge base

1.  Add approved reference documents under `knowledge_base/`.
2.  Run the ingestion process.
3.  Build or refresh the vector index.

``` bash
python ingest_documents.py
python build_vector_db.py
```

The current sample knowledge base includes an Eloqua basics document.
Expand it with approved, accurate marketing documentation. Avoid
confidential customer information and personal data.

## 10. Run the application

### Start FastAPI

From the project directory with the virtual environment activated:

``` bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Health check:

``` bash
curl http://127.0.0.1:8000/health
```

### Start Streamlit

Open a second terminal, activate the same environment, enter the project
directory, and run:

``` bash
streamlit run app.py --server.port 8503
```

Open the local URL printed by Streamlit. If the port is occupied, select
another free port and ensure the frontend is configured to call the
correct backend URL.

## 11. API usage

### Health endpoint

``` http
GET /health
```

The local test returned a healthy status with the model and RAG pipeline
loaded.

### Generation endpoint

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

The response includes the generated answer and, when RAG is enabled,
retrieval/source information. Use the exact request schema implemented
in `main.py` if it changes.

## 12. Testing and evaluation

The project currently contains standalone evaluation scripts and saved
result files:

``` bash
python evaluate_model.py
python compare_adapters.py
python evaluate_comparison.py
python run_evaluation.py
```

Run the scripts according to their command-line arguments and local
model/data availability.

### Validation completed

-   FastAPI health endpoint returned a running status.
-   Model loading was confirmed.
-   RAG loading was confirmed.
-   Generation without RAG returned HTTP 200.
-   Generation with RAG returned HTTP 200.
-   The RAG-enabled response identified `eloqua/eloqua_basics.txt` as a
    source.

### Validation still recommended

-   Complete a full browser-based Streamlit-to-FastAPI test.
-   Test missing/invalid API keys and malformed requests.
-   Add automated unit and API tests.
-   If adopting `pytest`, create a `tests/` suite and add `pytest` to
    development dependencies; do not treat it as already implemented.
-   Test multiple knowledge-base documents and verify retrieval quality.
-   Record reproducible evaluation metrics for V1 and V2 adapters.

## 13. Git ignore and large-file policy

The project `.gitignore` should exclude at least:

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
*.log
document_chunks.jsonl
vector_store/
model/
```

The model directory was approximately 202 MB locally, and the two
virtual environments were approximately 1.5 GB and 1.3 GB. Do not commit
virtual environments. Keep model weights outside normal Git commits, or
use Git LFS / an approved model-artifact store if repository
distribution is required.

## 14. Repository location

GitHub repository:

<https://github.com/sathishvarun/SE-B12>

Project folder:

<https://github.com/sathishvarun/SE-B12/tree/main/Week6/Day1-Day2/Marketing_AI_Assistant>

## 15. Future improvements

-   Expand and curate the marketing knowledge base.
-   Improve document parsing, chunking and metadata filtering.
-   Add source citations and relevance thresholds to generated answers.
-   Add robust error handling, request validation, logging and rate
    limiting.
-   Add a dedicated automated test suite (for example, pytest).
-   Complete Streamlit end-to-end and user-acceptance testing.
-   Add monitoring for latency, memory use and retrieval quality.
-   Document model licensing, data provenance and safe deployment
    requirements.
-   Consider a React frontend only if a separate custom web UI is a
    future requirement; the current frontend is Streamlit.

## 16. Summary

Marketing AI Assistant demonstrates an end-to-end applied AI workflow:
domain-specific dataset preparation, LoRA fine-tuning, LLM inference,
semantic embeddings, FAISS-based retrieval, RAG, API development, a
Streamlit interface, and model evaluation.

The development process also covered practical engineering skills:
debugging Python model inputs, managing local server ports, protecting
credentials, excluding large generated artifacts, understanding Git
history, resolving remote/local divergence safely, and publishing a
focused project folder without staging unrelated repository files.
