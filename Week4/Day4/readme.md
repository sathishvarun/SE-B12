# Week 4 – Day 4: Build a Two-Agent Crew for a Tech Newsletter

## Project Overview

This project demonstrates how to build a multi-agent AI workflow using Python and CrewAI. Two AI agents work sequentially: a Researcher Agent searches the web for current technology news, and a Writer Agent transforms the research into a concise five-line technology newsletter.

The project uses SerperDevTool for web search and the OpenAI API for language model capabilities. API keys and model configuration are managed through environment variables in a `.env` file.

## Project Objectives

- Build a multi-agent workflow using CrewAI.
- Create a Researcher Agent with web-search capabilities.
- Create a Writer Agent without search tools.
- Execute tasks sequentially using `Process.sequential`.
- Pass the Researcher's output to the Writer using task context.
- Generate a newsletter containing exactly five non-empty lines.
- Store API credentials securely using a `.env` file.

## Technologies Used

- Python 3.12
- CrewAI
- CrewAI Tools
- SerperDevTool
- OpenAI API
- python-dotenv
- Visual Studio Code

## Project Structure

```text
Day4/
├── news_crew.py
├── .env
├── .gitignore
└── README.md
```

**File descriptions:**

- `news_crew.py` — Contains the agents, tasks, sequential crew configuration, and newsletter output validation.
- `.env` — Stores the OpenAI API key, Serper API key, and model configuration.
- `.gitignore` — Prevents sensitive files and virtual environment files from being committed to Git.
- `README.md` — Documents the project, setup instructions, execution, and results.

## System Architecture

```text
Start
  |
  v
Load environment variables
  |
  v
Researcher Agent
  |
  v
Search web using SerperDevTool
  |
  v
Identify top 3 technology news stories
  |
  v
Pass research through task context
  |
  v
Writer Agent
  |
  v
Generate 5-line newsletter
  |
  v
Validate output line count
  |
  v
Display final newsletter
```

## Agent Responsibilities

### 1. Researcher Agent

**Role:** Technology News Researcher

**Responsibilities:**
- Search the web for current technology news.
- Identify three relevant and significant stories.
- Include headlines, publication dates, summaries, publishers, and source URLs.
- Return the research in a structured format.

**Tool:** `SerperDevTool`

The Researcher is the only agent configured with a web-search tool.

### 2. Writer Agent

**Role:** Technology Newsletter Writer

**Responsibilities:**
- Read the research supplied by the Researcher.
- Summarize the three stories concisely.
- Explain why the developments matter.
- Produce exactly five non-empty physical lines.

The Writer has no search tools and works only with the Researcher's output.

## Task Execution

The project contains two tasks.

**Task 1 — Research Technology News**

The Researcher searches for three current technology stories and returns a structured research brief.

**Task 2 — Write the Newsletter**

The Writer converts the research brief into a five-line newsletter.

The tasks run sequentially using:

```python
process=Process.sequential
```

The Researcher's output is passed explicitly to the Writer using:

```python
context=[find]
```

This ensures that the second task receives the first task's output.

## Newsletter Output Format

The final newsletter follows this structure:

```text
Tech in 5 Lines — [Today's date]
1. [First technology news story]
2. [Second technology news story]
3. [Third technology news story]
Why it matters: [Overall takeaway]
```

The Python script checks the output to confirm whether it contains exactly five non-empty lines.

Actual news stories depend on the live search results returned when the program runs.

## Setup Instructions

### Step 1: Activate the virtual environment

On macOS or Linux:

```bash
source venv312/bin/activate
```

Use the appropriate virtual environment path if your environment is stored elsewhere.

### Step 2: Install dependencies

```bash
python -m pip install --upgrade pip
pip install "crewai[tools]" python-dotenv
```

### Step 3: Configure environment variables

Create a `.env` file in the project folder:

```dotenv
OPENAI_API_KEY=your_actual_openai_api_key
SERPER_API_KEY=your_actual_serper_api_key
MODEL=openai/gpt-4o-mini
```

Replace the placeholders with valid credentials and a model available to your account.

Obtain API credentials from:

- OpenAI: https://platform.openai.com/api-keys
- Serper: https://serper.dev/

**Security:** Never commit your `.env` file or publish API keys in your repository.

### Step 4: Configure `.gitignore`

Add the following entries:

```gitignore
.env
.venv/
venv/
venv312/
__pycache__/
*.pyc
```

### Step 5: Run the application

```bash
python news_crew.py
```

The application loads environment variables, executes the Researcher task, passes its result to the Writer, and displays the generated newsletter.

## Error Handling and Validation

The program checks that the required environment variables are present before starting the workflow.

It also validates the final newsletter's line count.

Common issues include:

- **403 Unauthorized from Serper:** Check the API key, account status, and search API access.
- **OpenAI authentication errors:** Verify the API key and API access.
- **Missing environment variables:** Check the `.env` filename and location.
- **Missing Python packages:** Activate the correct virtual environment and reinstall dependencies.
- **Incorrect output line count:** Review the Writer's instructions and rerun the workflow.

A successful five-line validation does not independently verify the accuracy of every news story; review the returned source URLs and publication dates.

## Results and Testing

The workflow should demonstrate the following:

1. The Researcher searches for current technology news.
2. Three stories are returned in a structured research brief.
3. The Writer receives the research through task context.
4. The Writer generates a five-line newsletter.
5. The program reports whether the output meets the five-line requirement.

Run the program on different days to check whether the stories reflect the latest available news.

## Assignment Deliverables

- `news_crew.py` — Complete Python implementation.
- `README.md` — Project documentation.
- Screenshot — A full run showing Researcher execution and the final newsletter.
- Screen recording — Demonstration of the two-agent workflow.


## Learning Outcomes

Through this assignment, I learned how to:

- Create and configure multiple AI agents.
- Assign tools to specific agents.
- Define clear task descriptions and expected outputs.
- Execute tasks in sequence using CrewAI.
- Transfer task results through explicit context.
- Manage API keys with environment variables.
- Validate AI-generated output programmatically.

## Conclusion

This project demonstrates a basic sequential multi-agent architecture in which one agent researches information and another transforms it into a structured deliverable. It provides practical experience with CrewAI, tool integration, task dependencies, environment configuration, and output validation.
