# SLM Distillation: Teacher → Student

Train a **small language model (student)** to imitate a **bigger LLM (teacher)** using knowledge distillation, then serve it as a REST API with **FastAPI + uvicorn**. Runs fully on a Mac (Apple Silicon GPU via `mps`).

| Role | Model | Size |
|---|---|---|
| Teacher (parent) | `HuggingFaceTB/SmolLM2-360M-Instruct` | ~720 MB |
| Student (sub model) | `HuggingFaceTB/SmolLM2-135M` | ~270 MB |

Both models share the same tokenizer, which is what lets the student learn from the teacher's full probability distribution (not just its text). Total disk needed: about **2 GB**.

## How it works

```
data/prompts.txt ──► [Step 1] Teacher answers each question ──► data/distill_dataset.jsonl
                                                                     │
                     [Step 2] Student trains on teacher answers ◄────┘
                              Loss = α·KL(teacher ‖ student) + (1-α)·CrossEntropy
                                                                     │
                                       models/student-distilled ◄────┘
                                                │
            [Step 3] Terminal chat ◄────────────┤
            [Step 4] FastAPI server (uvicorn) ◄─┘   http://127.0.0.1:8000/docs
```

- **KL loss** – the student copies *how* the teacher thinks (its soft probabilities, softened by `TEMPERATURE`).
- **CE loss** – the student copies *what* the teacher said.

## Project structure

```
slm-distillation/
├── config.py               # all settings: models, epochs, batch size, paths
├── data/prompts.txt        # questions for the teacher (edit/add your own)
├── step1_generate_data.py  # Step 1: teacher creates training data
├── step2_train_student.py  # Step 2: distillation training
├── step3_chat.py           # Step 3: chat with the student in terminal
├── inference.py            # shared model-loading/generation code
├── api.py                  # Step 4: FastAPI app, run with uvicorn
├── test_api.sh             # curl test for the API
└── requirements.txt
```

## Setup (Mac, one time)

Open the folder in VS Code (**File → Open Folder…**), then open the terminal (**Ctrl + `**):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Python 3.10–3.12 recommended. In VS Code, pick the `.venv` interpreter when prompted (Cmd+Shift+P → *Python: Select Interpreter*).

## Run it step by step

```bash
# Step 1 – teacher answers questions (downloads teacher first time)  ~3-8 min
python step1_generate_data.py

# Step 2 – distil teacher into student                               ~5-15 min
python step2_train_student.py

# Step 3 – chat with the student (add --compare to see before vs after)
python step3_chat.py --compare

# Step 4 – start the API server
uvicorn api:app --reload
```

Then open **http://127.0.0.1:8000/docs**, click **POST /generate → Try it out → Execute**. Or in a second terminal:

```bash
bash test_api.sh
```

Times are for an M1/M2/M3 Mac. Intel Macs run on CPU and are slower.

## Tuning

Edit `config.py`:

- More/better data → add lines to `data/prompts.txt` (biggest quality gain).
- `EPOCHS`, `LEARNING_RATE`, `BATCH_SIZE` – training settings.
- `TEMPERATURE` (2.0) and `ALPHA` (0.5) – distillation balance.
- Out of memory? Set `BATCH_SIZE = 2` or `MAX_SEQ_LEN = 192`.

## Push to GitHub

Create an empty repo on github.com (no README), then:

```bash
git init
git add .
git commit -m "SLM distillation: teacher -> student with FastAPI"
git branch -M main
git remote add origin https://github.com/<your-username>/slm-distillation.git
git push -u origin main
```

`models/` and the generated dataset are excluded by `.gitignore` (too large, and anyone can recreate them by running steps 1–2).

## Troubleshooting

| Problem | Fix |
|---|---|
| `Trained student not found` | Run step 1 and step 2 before step 3 / the API. |
| `MPS backend out of memory` | Lower `BATCH_SIZE` in `config.py`, close other apps. |
| Slow download / timeout | Re-run; Hugging Face resumes. Files cache in `~/.cache/huggingface`. |
| `zsh: command not found: python` | Activate the venv: `source .venv/bin/activate`. |
