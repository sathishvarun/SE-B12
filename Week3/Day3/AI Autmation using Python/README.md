# Employee Data Cleaning ETL Automation

A beginner-friendly Python project that reads an employee Excel
workbook, cleans and validates records, optionally uses the OpenAI API
to normalize approved category values, and creates a new Excel output
workbook.

## 1. What this project does

The program follows the ETL process:

1.  **Extract** --- reads the `Dirty Employee Data` worksheet from the
    Excel workbook.
2.  **Transform** --- trims extra spaces, standardizes selected text
    fields, normalizes known department/state values, lowercases email
    addresses, and normalizes valid Indian mobile numbers.
3.  **AI-assisted normalization** --- optionally sends only distinct
    values from approved category columns to OpenAI. It does not send
    full employee records, names, emails, phone numbers, salaries, IDs,
    or bank fields.
4.  **Validate** --- flags missing required fields, invalid or duplicate
    emails, invalid phone numbers, and missing, negative, or non-numeric
    salaries.
5.  **Load** --- writes a new Excel workbook with cleaned data and
    reports. The source workbook is not overwritten.

> Important: validation checks syntax and configured rules; they cannot
> guarantee that employee details are factually correct. Review rows
> marked `Needs Review`.

## 2. Project files

Keep these files together in your project folder (for example,
`AI Automation`):

``` text
AI Automation/
├── main.py
├── employee_sample_data_50_fields_50_records(2).xlsx
├── .env
├── .gitignore
├── requirements.txt
└── .venv/
```

-   `main.py` --- the single-file ETL application. If your downloaded
    file is named `employee_etl_single_file.py`, rename it to `main.py`
    or use its actual name in the run command.
-   `employee_sample_data_50_fields_50_records(2).xlsx` --- input
    workbook.
-   `.env` --- stores your OpenAI API key locally.
-   `.gitignore` --- prevents local secrets and generated files from
    being committed.
-   `requirements.txt` --- lists the Python packages.
-   `.venv/` --- your local Python virtual environment.

## 3. Prerequisites

-   macOS
-   Python 3 installed
-   VS Code
-   Your employee Excel workbook
-   An OpenAI API key if you want to use AI-assisted category
    normalization

A ChatGPT subscription does not automatically include API usage credit.
API access and billing may need to be configured separately.

## 4. Open the project in VS Code

1.  Open VS Code.
2.  Choose **File → Open Folder**.
3.  Open your existing project folder, such as
    `Downloads/SE-B12/Week3/Day3/AI Automation`.
4.  Make sure the Excel workbook and `main.py` are in this same folder.

Open **Terminal → New Terminal** in VS Code.

## 5. Activate the virtual environment

If you already created `.venv` in this project, activate it:

``` bash
source .venv/bin/activate
```

The terminal prompt should show `(.venv)`.

If you have not created a virtual environment in this project yet, run
these commands from the project folder:

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

## 6. Install the required packages

Create a file named `requirements.txt` and add:

``` text
pandas
openpyxl
openai
python-dotenv
```

Then install the packages:

``` bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The ETL script uses: - `pandas` to read, transform, and validate tabular
data. - `openpyxl` to write Excel workbooks. - `openai` to call the
OpenAI API. - `python-dotenv` to load the local `.env` file.

## 7. Configure the OpenAI API key

Create a file named `.env` in the same folder as `main.py`.

Add the following lines, replacing the example with your real API key:

``` text
OPENAI_API_KEY=your_real_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Do not include the placeholder text. Do not share your API key in chat,
screenshots, or GitHub.

If you have not created an API key, use the official OpenAI API Keys
page: https://platform.openai.com/api-keys

The API may require separate billing or available credits.

### Protect your key

Create a `.gitignore` file in the project folder and add:

``` text
.env
.venv/
__pycache__/
*.pyc
employee_cleaned_output.xlsx
```

Never commit `.env` to GitHub.

## 8. Run the ETL program

First, confirm the input filename and worksheet name match the values
configured near the top of `main.py`:

-   Input file: `employee_sample_data_50_fields_50_records(2).xlsx`
-   Worksheet: `Dirty Employee Data`

Run the full process:

``` bash
python main.py
```

Run local cleanup without an OpenAI API call:

``` bash
python main.py --no-openai
```

If your input workbook has a different filename or location, specify it:

``` bash
python main.py --input "your_input_file.xlsx" --output "employee_cleaned_output.xlsx"
```

If the employee worksheet has a different name, specify it:

``` bash
python main.py --sheet "Your Worksheet Name"
```

## 9. Output workbook

By default, the program creates:

`employee_cleaned_output.xlsx`

It contains four worksheets:

1.  **Cleaned Data** --- original fields plus cleaning issues, record
    status, and OpenAI normalization note.
2.  **Validation Report** --- row number, issues, and status for each
    record.
3.  **Summary** --- totals for records processed, valid records, and
    records needing review.
4.  **Cleaning Rules** --- a description of the implemented rules.

The input workbook is not overwritten.

## 10. Implemented cleaning and validation rules

-   Trim leading, trailing, and repeated whitespace.
-   Convert configured name and descriptive fields to title case.
-   Lowercase and validate email syntax.
-   Flag duplicate primary email addresses.
-   Standardize known state names and department labels.
-   Normalize valid Indian mobile numbers to `+91` plus 10 digits.
-   Flag missing required employee fields.
-   Flag missing, negative, and non-numeric salary values.
-   Preserve ambiguous or invalid values for review instead of guessing
    replacements.
-   Optionally normalize distinct values from approved category columns
    with OpenAI.

### Notes about column names

The script matches supported columns by their header names
(case-insensitively). If your workbook uses different headers, update
the configured column lists in `main.py` to match your actual Excel
headers.

### Notes about mobile numbers

The current rule is designed primarily for Indian mobile numbers. It
does not guess missing digits or infer unknown country codes. Invalid or
ambiguous numbers should be reviewed manually.

### Notes about AI normalization

OpenAI normalization is optional. The script sends distinct values from
approved category columns, not full employee rows. The model may still
return an unsuitable mapping, so review category values before using the
output operationally. If the API call fails, the script retains local
cleaning and reports the failure type without printing your API key.

## 11. Troubleshooting

### `FileNotFoundError`

-   Confirm the Excel workbook is in the same folder as `main.py`.
-   Check the filename carefully.
-   Or run the script with `--input "full/path/to/file.xlsx"`.

### Worksheet not found

The script expects `Dirty Employee Data`. Check the worksheet names in
Excel and pass the exact name with `--sheet`.

### `ModuleNotFoundError`

Activate `.venv`, then run:

``` bash
python -m pip install -r requirements.txt
```

### OpenAI key missing

-   Confirm `.env` is in the same folder as `main.py`.
-   Confirm the variable is named `OPENAI_API_KEY`.
-   Replace the example placeholder with the real key.
-   Save `.env` and rerun the script.

### OpenAI authentication, quota, or model error

Do not paste your API key into chat. Check your API key, project access,
billing/credits, and model access. You can continue testing the local
Python cleanup with:

``` bash
python main.py --no-openai
```

### Output file is open in Excel

Close `employee_cleaned_output.xlsx` in Excel and rerun the script.

## 12. n8n integration --- planned next step

The Python ETL script is a local command-line program. A cloud-hosted
n8n workflow cannot automatically run a script stored only on your Mac.

To connect n8n, the next phase is to expose this Python ETL program
through a secured Python API service in an environment that n8n can
reach. The high-level workflow will be:

``` text
n8n Form/Webhook
    ↓
Receive Excel upload
    ↓
HTTP Request to secured Python API
    ↓
Python ETL: Extract → Transform → Validate → Load
    ↓
Return the generated Excel workbook
```

Do not expose an unauthenticated file-processing endpoint to the public
internet. The n8n integration is not configured by this README; it is a
separate implementation step.
