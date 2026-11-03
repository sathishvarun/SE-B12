# Marketing AI Assistant

## Qwen2.5-0.5B-Instruct + Fine-Tuned LoRA Adapter

A local, browser-based Marketing AI Assistant built with **Python,
Hugging Face Transformers, PEFT/LoRA, PyTorch and Streamlit**.

The application loads the original Qwen instruction model and attaches
the saved marketing-domain LoRA adapter. It provides a chat interface
for asking questions about marketing automation, Marketo, Oracle Eloqua,
webinar operations, lead nurturing and email campaigns.

> **Project status:** The Streamlit application and adapter-loading
> workflow have been assembled. The tokenizer-loading issue described
> below was corrected in `app.py` by loading the tokenizer from the
> original Qwen base model. Model quality still needs to be evaluated
> with a broader test set before production use.

------------------------------------------------------------------------

## 1. Project objective

The objective was to take a small general-purpose instruction model,
fine-tune it for marketing-automation question-and-answer examples, save
the trained adapter, and run it locally through a simple web interface.

### What we built

-   **Base model:** `Qwen/Qwen2.5-0.5B-Instruct`
-   **Fine-tuning approach:** Supervised fine-tuning (SFT) using a
    PEFT/LoRA adapter
-   **Adapter folder:** `model/marketing-llm-finetuned/`
-   **Application:** Streamlit chat interface
-   **Inference:** Transformers + PyTorch + PEFT
-   **Local address:** http://localhost:8501

### Important distinction: base model versus fine-tuned model

The original Qwen model is the **base model**. It provides the general
language understanding and text-generation capability.

The saved `marketing-llm-finetuned` folder contains the **LoRA
adapter**, which stores learned parameter updates from the fine-tuning
exercise. It is not a complete standalone model.

At runtime, the application loads the base model first and then attaches
the LoRA adapter. Together, they are used as the fine-tuned Marketing AI
Assistant.

------------------------------------------------------------------------

## 2. End-to-end project flow

``` text
Marketing question-and-answer examples
                |
                v
       Prepare training dataset
                |
                v
       Load Qwen base model
                |
                v
   Supervised fine-tuning (SFT)
        with PEFT / LoRA
                |
                v
     Save trained LoRA adapter
                |
                v
 Download / place adapter ZIP locally
                |
                v
   Marketing_AI_Assistant project
                |
                +---- app.py
                |
                +---- requirements.txt
                |
                +---- model/
                |       |
                |       +---- marketing-llm-finetuned/
                |
                v
       Create Python environment
                |
                v
       Install dependencies
                |
                v
   Load Qwen base model + adapter
                |
                v
       Streamlit chat interface
                |
                v
       http://localhost:8501
                |
                v
       User asks a question
                |
                v
       Model generates an answer
```

------------------------------------------------------------------------

## 3. Project folder structure

The main project directory is `Marketing_AI_Assistant`.

``` text
Marketing_AI_Assistant/
│
├── app.py
│   └── Streamlit application, model loading and chat generation
│
├── requirements.txt
│   └── Python packages required by the application
│
├── README.md
│   └── Project documentation and setup instructions
│
├── run_mac.sh
│   └── Optional Mac setup and launch script
│
├── evaluate_model.py
│   └── Command-line sample evaluation script
│
├── training_dataset.json
│   └── Small set of marketing question-and-answer examples
│
├── .gitignore
│   └── Files and folders excluded from Git
│
├── .venv/
│   └── Local Python virtual environment (created during setup)
│
└── model/
    └── marketing-llm-finetuned/
        │
        ├── adapter_config.json
        │   └── LoRA configuration and base-model reference
        │
        ├── adapter_model.safetensors
        │   └── Trained LoRA adapter weights
        │
        ├── tokenizer_config.json
        │   └── Tokenizer configuration saved with the adapter
        │
        ├── tokenizer.json
        │   └── Tokenizer vocabulary and processing information
        │
        ├── chat_template.jinja
        │   └── Chat formatting template
        │
        ├── training_args.bin
        │   └── Saved training arguments
        │
        └── README.md
            └── Adapter model card / metadata
```

The `.venv` folder is generated on the user's computer and is not
required to be copied between machines. The adapter folder must retain
`adapter_config.json` and `adapter_model.safetensors`.

------------------------------------------------------------------------

## 4. Base model: what we started with

We used the Hugging Face model:

**`Qwen/Qwen2.5-0.5B-Instruct`**

The base model is a general-purpose instruction-following language
model. Before domain fine-tuning, it has general language capabilities,
but it is not specifically trained for our small set of
marketing-automation examples.

The base model is downloaded from Hugging Face the first time the
application runs. An internet connection is therefore required for the
first model load. Subsequent runs can use the locally cached base model.

Model page: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct

------------------------------------------------------------------------

## 5. Fine-tuning approach: what we created

We used **Supervised Fine-Tuning (SFT)** with **Parameter-Efficient
Fine-Tuning (PEFT)** and **Low-Rank Adaptation (LoRA)**.

### What is LoRA?

LoRA fine-tunes selected model layers by learning a smaller set of
additional parameters rather than updating and saving every parameter in
the original base model.

This makes the fine-tuning output smaller and easier to store and reuse.

### Adapter configuration

The supplied `adapter_config.json` identifies these settings:

  Setting                 Saved value
  ----------------------- ------------------------------
  Base model              `Qwen/Qwen2.5-0.5B-Instruct`
  PEFT type               LoRA
  Task type               Causal language modelling
  LoRA rank (`r`)         8
  LoRA alpha              16
  LoRA dropout            0.05
  PEFT version recorded   0.21.2

The adapter targets attention and feed-forward projection modules,
including `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`
and `down_proj`.

**Note:** These values are read from the saved adapter configuration.
They describe the adapter that was supplied to this application.

------------------------------------------------------------------------

## 6. Training input: what information we gave the model

The example training data is stored in `training_dataset.json`.

It contains question-and-answer pairs. Each item has: - `question`: the
example question - `answer`: the expected answer

### Training examples included in the project

  ------------------------------------------------------------------------
                           No. Training question     Topic
  ---------------------------- --------------------- ---------------------
                             1 What is a Smart       Marketo
                               Campaign in Marketo?  

                             2 What does No Show     Webinar operations
                               mean in a webinar?    

                             3 What is Oracle        Eloqua
                               Eloqua?               

                             4 What is lead          Lead management
                               nurturing?            

                             5 What is CRM           CRM integration
                               integration?          

                             6 What is email         Email automation
                               automation?           

                             7 What is a hard        Email deliverability
                               bounce?               

                             8 What is a webinar     Webinar operations
                               registration          
                               confirmation?         
  ------------------------------------------------------------------------

These are short instructional examples, not a large enterprise knowledge
base.

### Example training record

``` json
{
  "question": "What is lead nurturing?",
  "answer": "Lead nurturing is building relationships with potential customers through relevant and personalized communications."
}
```

The training process teaches the model the response patterns represented
by these examples. The training dataset is not automatically a live
database, and the model does not automatically know private company
processes or current campaign data.

------------------------------------------------------------------------

## 7. What questions can we ask the running model?

After launching the application, users can enter questions in the
Streamlit chat box.

Examples for testing:

### Marketo

-   What is a Smart Campaign in Marketo?
-   How do triggers, filters and flow steps work in a Smart Campaign?

### Oracle Eloqua

-   What is Oracle Eloqua?
-   What is a typical Eloqua email campaign workflow?
-   What is lead nurturing?

### Webinar operations

-   What does No Show mean in a webinar?
-   What is a webinar registration confirmation?
-   What is the difference between a registrant and an attendee?

### Email marketing

-   What is a hard bounce?
-   What is email automation?
-   Why should invalid email addresses be excluded from a campaign?

### CRM and marketing operations

-   What is CRM integration?
-   Why is CRM data synchronization important for marketing automation?

Some questions above are additional **inference test prompts**. They are
not all included in the eight-example training dataset.

------------------------------------------------------------------------

## 8. How the application works

The main application is `app.py`.

### Application sequence

1.  Streamlit creates the browser-based chat page.
2.  The application checks that the adapter configuration and weights
    exist.
3.  The tokenizer is loaded from the original Qwen base model.
4.  The application detects the available compute device:
    -   CUDA when an NVIDIA GPU is available
    -   Apple MPS when supported on the Mac
    -   CPU otherwise
5.  The Qwen base model is loaded.
6.  PEFT attaches the saved LoRA adapter from
    `model/marketing-llm-finetuned/`.
7.  The model is placed in evaluation mode.
8.  A user's question is formatted using the Qwen chat template.
9.  The model generates a response.
10. Streamlit displays the response in the chat interface.

The application uses Streamlit session state to retain the conversation
while the current app session is running. The **Clear conversation**
button clears that chat history.

------------------------------------------------------------------------

## 9. Issues faced and how we fixed them

### Issue 1: Tokenizer loading error

**Error displayed:**

``` text
AttributeError: 'list' object has no attribute 'keys'
```

**Where it occurred:**

The error occurred while calling:

``` python
AutoTokenizer.from_pretrained(tokenizer_path)
```

The traceback showed that Transformers was processing
`extra_special_tokens` and attempted to call `.keys()` on a value that
was a list.

**Why it happened:**

The adapter ZIP included its own tokenizer configuration. The installed
Transformers tokenizer code expected a different data structure for the
`extra_special_tokens` value in that configuration.

**Correction made in `app.py`:**

Instead of loading the tokenizer from the adapter directory, the
application now loads it from the original base model:

``` python
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
```

The adapter remains loaded separately using PEFT:

``` python
model = PeftModel.from_pretrained(base, ADAPTER_DIR)
```

**Why this correction is appropriate:**

The adapter was fine-tuned from the same Qwen base model. Therefore, the
base model's tokenizer can be used to tokenize the user's questions and
decode generated answers, while the LoRA adapter supplies the fine-tuned
weights.

### Issue 2: Understanding the adapter versus the full model

**Issue:** The downloaded ZIP was initially easy to mistake for a
complete standalone model.

**Clarification:** The ZIP contains the LoRA adapter and related files,
not all the weights of the original Qwen base model.

**Resolution:** The application loads the base model from Hugging Face
and attaches the adapter from the local `model/marketing-llm-finetuned/`
folder.

### Issue 3: First launch requires a model download

**Issue:** The adapter is present locally, but the base model is not
bundled into the project ZIP.

**Resolution:** Keep an internet connection during the first launch so
Transformers can download the Qwen base model. It is normally cached
locally for later use.

------------------------------------------------------------------------

## 10. Environment setup on macOS

Open the `Marketing_AI_Assistant` folder in VS Code and select
**Terminal → New Terminal**.

### Step 1: Check Python

``` bash
python3 --version
```

Python 3.11 or 3.12 is recommended for this project.

### Step 2: Create a virtual environment

For Python 3.12:

``` bash
python3.12 -m venv .venv
```

If using Python 3.11:

``` bash
python3.11 -m venv .venv
```

### Step 3: Activate the environment

``` bash
source .venv/bin/activate
```

When activated, the terminal prompt should show:

``` text
(.venv)
```

### Step 4: Upgrade pip

``` bash
python -m pip install --upgrade pip
```

### Step 5: Install dependencies

``` bash
python -m pip install -r requirements.txt
```

### Step 6: Run the Streamlit application

``` bash
python -m streamlit run app.py
```

### Step 7: Open the local application

Open this address in your browser:

**http://localhost:8501**

To stop the running application, return to the terminal and press
`Control + C`.

To deactivate the virtual environment:

``` bash
deactivate
```

When opening a new terminal later, activate the existing environment
again. Do not recreate it every time.

------------------------------------------------------------------------

## 11. Dependencies

The project's `requirements.txt` specifies:

  Package          Purpose
  ---------------- ------------------------------------
  `torch`          Model computation and inference
  `transformers`   Loads the Qwen model and tokenizer
  `peft`           Loads the LoRA adapter
  `accelerate`     Model execution support
  `safetensors`    Reads adapter weights
  `streamlit`      Browser-based user interface

Install them with:

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

## 12. Localhost application

Once Streamlit starts successfully, the terminal displays a local URL.

**Application URL: http://localhost:8501**

This is a local development address. It is accessible from the same
computer while the Streamlit process is running. It is not a public
internet URL.

------------------------------------------------------------------------

## 13. Current limitations and next improvements

-   The training dataset contains only eight short examples. It is
    suitable for a learning demonstration, not a comprehensive marketing
    knowledge assistant.
-   Fine-tuning does not guarantee that every answer will be correct.
    Validate responses against trusted documentation.
-   The model does not automatically access Eloqua, Marketo, Salesforce,
    CRM records, campaign reports or live webinar platforms.
-   The model may produce incomplete or incorrect answers, especially
    for detailed platform-specific procedures.
-   CPU inference may be slower than GPU or supported Apple Silicon
    acceleration.
-   The current application is a local demo. Authentication, access
    control, monitoring, data protection and production deployment would
    be needed before wider use.
-   The base model is downloaded from Hugging Face on first launch; the
    adapter is stored in the project folder.

### Suggested future improvements

1.  Expand the training dataset with reviewed Marketo, Eloqua, webinar
    and campaign-operation examples.
2.  Create a separate validation/test dataset and measure answer
    quality.
3.  Add retrieval-augmented generation (RAG) to answer from approved
    product documentation and internal process guides.
4.  Add integrations with CRM and marketing automation platforms only
    through approved, secure APIs.
5.  Add user authentication and deployment controls if the application
    is shared with a team.

------------------------------------------------------------------------

## 14. Conclusion

In this project, we started with the general-purpose
`Qwen/Qwen2.5-0.5B-Instruct` model and used a saved PEFT/LoRA adapter
fine-tuned on a small set of marketing automation question-and-answer
examples.

We then built a local Streamlit application that loads the base model,
attaches the adapter, accepts questions from the user and displays
generated answers in a browser.

During setup, we encountered a tokenizer configuration error because the
adapter's saved tokenizer configuration was incompatible with the
installed Transformers tokenizer code. We corrected the application to
load the tokenizer from the original Qwen base model while continuing to
load the LoRA adapter from the local project folder.

The result is a working application structure for experimenting with a
domain-adapted Marketing AI Assistant. The next important step is to
test answer quality and expand the reviewed training data before
treating it as a reliable business assistant.

------------------------------------------------------------------------

## 15. Key project details

  Item                         Value
  ---------------------------- ----------------------------------
  Project name                 Marketing AI Assistant
  Base model                   `Qwen/Qwen2.5-0.5B-Instruct`
  Fine-tuning method           SFT with PEFT/LoRA
  Adapter location             `model/marketing-llm-finetuned/`
  Training examples included   8
  Application framework        Streamlit
  Main application file        `app.py`
  Local environment            `.venv`
  Local application URL        http://localhost:8501
  Primary language             Python
