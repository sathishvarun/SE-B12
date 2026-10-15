# Week 3 -- Day 3: AI-Powered Employee Data Cleaning Workflow

## 1. Project Overview

This project uses **n8n** to automate the processing of employee records
from an Excel (`.xlsx`) file. The workflow extracts rows from the
uploaded spreadsheet, sends each record through an AI-powered cleaning
step, applies JavaScript processing, checks a configured condition, and
exports the results into Excel files.

The workflow shown in the screenshot is named
**`Week3-Day3-Workflow2`**.

> **Important:** The screenshot shows the workflow structure and a
> successful execution. The exact cleaning rules and the `If` condition
> depend on the settings inside those nodes. This README describes the
> visible workflow and does not assume an unshown condition.

## 2. Problem Statement

Employee spreadsheets can contain inconsistent names, email addresses,
department names, missing values, duplicate emails, and invalid salary
values. Reviewing these records manually can be time-consuming.

The goal of this workflow is to build an automated process that can help
standardize and validate employee data, separate records based on a
rule, and produce Excel output files for review.

## 3. Workflow Diagram

``` text
File Upload
    |
    v
Extract from File (XLSX)
    |
    v
Basic LLM Chain <---- OpenAI Chat Model
    |
    v
Loop Over Items
    | loop
    v
Code in JavaScript
    |
    +---------- back to Loop Over Items
    |
    | done
    v
If (configured condition)
    | true                     | false
    v                          v
Convert to File             Convert to File1
(XLSX output)               (XLSX output)
```

## 4. Node-by-Node Explanation

### 4.1 File Upload

**Purpose:** Starts the workflow with the input spreadsheet.

**What to do:** 1. Open the `File Upload` node. 2. Check the configured
upload method. 3. Upload the employee Excel file expected by the
workflow. 4. Confirm that the input file is available to the next node.

**Expected input:** An Excel file containing employee records.

### 4.2 Extract from File

The node is configured with the operation **Extract From XLSX**.

**Purpose:** Reads the spreadsheet and converts its rows into n8n items
that downstream nodes can process.

**Check:** - The correct worksheet or sheet options are selected, if
applicable. - Column headers are present and spelled consistently. - The
output contains the expected employee fields.

The screenshot shows **50 items** leaving this node.

### 4.3 Basic LLM Chain

**Purpose:** Sends input data to an AI language model according to the
prompt configured in the node.

For an employee-data-cleaning task, the prompt may ask the model to: -
Trim extra spaces from names. - Standardize names to title case. -
Convert email addresses to lowercase. - Identify missing or invalid
email addresses. - Standardize department names using an agreed
mapping. - Identify duplicate email addresses. - Flag negative or
non-numeric salaries. - Preserve employee IDs. - Return a status and an
issues list for each record. - Avoid inventing information that is
missing from the source.

**Important configuration checks:** - Review the prompt and ensure the
input fields are mapped correctly. - Request a consistent structured
response (for example, JSON) if later nodes expect structured data. -
Make sure the model output is parsed before downstream nodes use it, if
required. - Validate the AI output against the original data;
AI-generated cleaning results should not be treated as guaranteed facts.

The screenshot shows the `Basic LLM Chain` connected to an
`OpenAI Chat Model` and passing **50 items** onward.

### 4.4 OpenAI Chat Model

**Purpose:** Supplies the language model used by the `Basic LLM Chain`.

**Setup checklist:** 1. Open the model node. 2. Select the appropriate
OpenAI credential. 3. Choose an available model supported by your
account and n8n configuration. 4. Confirm the model is connected to the
`Model` input of the Basic LLM Chain. 5. Run a small test and inspect
the returned output.

Keep API keys and credentials private. Do not paste them into this
README or commit them to GitHub.

### 4.5 Loop Over Items

**Purpose:** Processes incoming items through a loop path and provides a
`done` output when the loop is complete.

In this screenshot, the loop sends items to `Code in JavaScript`; the
code node's output returns to the loop. The loop's `done` output then
connects to the `If` node.

**Check:** - The loop output is connected to the intended processing
node. - The code node returns the expected item structure. - The
loop-back connection is present. - The `done` output connects to the
next stage.

The screenshot displays **50 items total** at the loop stage. The exact
batch behavior depends on the node's configuration.

### 4.6 Code in JavaScript

**Purpose:** Applies custom JavaScript logic to each item or batch,
based on the code and mode configured in the node.

Possible uses in this project include: - Reading the AI response and
extracting the required fields. - Normalizing values into a consistent
output structure. - Ensuring employee IDs are preserved. - Creating or
standardizing an `issues` array. - Setting a record status such as
`Valid`, `Needs Review`, or another status defined by the project. -
Preparing fields for the condition and Excel export.

**Important:** These are suggested responsibilities, not confirmation of
the exact code currently saved in the node. Open the node and document
its actual logic before changing it.

**Validation checklist:** - The code handles missing or unexpected AI
output safely. - Field names match the input and output schemas. - It
does not silently discard employee records. - It returns items in the
structure expected by the next node. - It handles strings, numbers, null
values, and arrays appropriately.

### 4.7 If

**Purpose:** Checks a configured condition and sends each item to one of
two outputs.

-   **True output:** Records for which the condition evaluates to true.
-   **False output:** Records for which the condition evaluates to
    false.

The screenshot shows **16 items** on the true branch and **34 items** on
the false branch. This accounts for the 50 items shown entering the
condition.

**The exact meaning of the two groups depends on the condition
configured in the node.** For example, the condition might separate
records that pass validation from records that need review, but verify
the actual configuration before assigning those labels.

**Check:** 1. Open the `If` node. 2. Read the condition and the fields
it evaluates. 3. Confirm which branch represents each outcome. 4. Test
known valid and invalid examples.

### 4.8 Convert to File

The true branch connects to `Convert to File`, configured to **Convert
to XLSX**.

**Purpose:** Converts the items on the true branch into an Excel file.

### 4.9 Convert to File1

The false branch connects to `Convert to File1`, also configured to
**Convert to XLSX**.

**Purpose:** Converts the items on the false branch into a separate
Excel file.

The two nodes allow the results from each branch to be exported
separately. Check the node configuration and execution output to confirm
the generated binary files and their filenames.

## 5. How to Run the Workflow

1.  Open the `Week3-Day3-Workflow2` workflow in n8n.
2.  Confirm the OpenAI credential is configured correctly.
3.  Open the `Basic LLM Chain` and review its prompt.
4.  Confirm the JavaScript code and `If` condition match your
    requirements.
5.  Click **Execute** or the equivalent manual-run control in your n8n
    editor.
6.  Upload the input employee Excel file when prompted.
7.  Wait for the execution to finish.
8.  Click each node and inspect its **Input** and **Output** data.
9.  Check the `If` node's true and false outputs.
10. Open the file-conversion nodes and download or inspect their
    generated files from the execution data, according to your n8n
    interface.

## 6. Expected Results

Based on the visible execution in the screenshot:

  Workflow stage         Visible item count
  -------------------- --------------------
  File Upload               1 uploaded file
  Extract from File                50 items
  Basic LLM Chain                  50 items
  Loop Over Items            50 items total
  If -- true branch                16 items
  If -- false branch               34 items


https://n8n-2fqi.srv2061895.hstgr.cloud/workflow/eKxykMZ7QSlR1xfA?projectId=J7Gtn8p6q7qFLIsv

The screenshot shows both `Convert to File` nodes completed
successfully. It displays **1 item** after each conversion node; this
generally represents the generated file item, not the number of
spreadsheet rows.

The counts above describe the execution visible in the screenshot. Your
counts may differ when a different input file is uploaded.

## 7. Data Quality and Safety Checks

Before using the exported files:

-   Compare the output record count with the input record count.
-   Confirm employee IDs are unchanged.
-   Check that blank values remain blank rather than being guessed.
-   Validate email format and duplicate detection.
-   Confirm salary values are numeric and investigate negative values.
-   Review all records routed to the false branch.
-   Inspect a sample of AI-cleaned records against the source
    spreadsheet.
-   Avoid uploading sensitive employee information to external AI
    services unless your organization permits it and appropriate
    safeguards are in place.

## 8. Troubleshooting

### The Excel file is not extracted

-   Confirm that the uploaded file is a supported `.xlsx` file.
-   Check the `Extract from File` node's operation and input binary
    property.
-   Verify that the sheet contains data and appropriate headers.

### The OpenAI model fails

-   Check the selected credential and API access.
-   Review the execution error for authentication, quota, model, or
    connection issues.
-   Test with a small sample to reduce debugging time.
-   Never include the API key in screenshots or source control.

### The AI output is not valid JSON

-   Review the Basic LLM Chain prompt and ask for only the required
    structured output.
-   Inspect the actual model response.
-   Add or configure a parser if your workflow requires structured
    output.
-   Make the JavaScript node handle invalid responses and report them
    for review rather than silently dropping them.

### The JavaScript node fails

-   Check the selected execution mode and the expected input structure.
-   Inspect the input JSON in n8n.
-   Confirm property names match the data returned by the previous node.
-   Handle missing fields and unexpected data types.

### The If node sends records to an unexpected branch

-   Open the `If` node and verify its condition.
-   Check whether it tests a boolean, string, or another value.
-   Test one record that should pass and one that should fail.

### The Excel output is missing or contains unexpected data

-   Inspect the output of the relevant branch.
-   Confirm `Convert to File` is configured for XLSX and receives the
    intended JSON fields.
-   Check the output file data in the execution details.
-   Confirm that the branch has records and that the output file is
    actually available to download.

## 9. Suggested Output Columns

Adjust these columns to match your actual input and JavaScript output
schema.

  Column          Description
  --------------- ------------------------------------------------
  `employee_id`   Original employee identifier; preserve it
  `first_name`    Standardized first name
  `last_name`     Standardized last name
  `email`         Lowercase email, if present
  `department`    Standardized department
  `salary`        Salary value after validation
  `status`        Validation result defined by the workflow
  `issues`        List of missing, invalid, or suspicious values

Do not add columns that are not produced by your workflow unless you
also update the relevant node configuration.

## 10. Workflow Summary

This n8n workflow demonstrates an AI-assisted data processing pipeline:

1.  Upload an employee spreadsheet.
2.  Extract spreadsheet rows into n8n items.
3.  Use an OpenAI model through a Basic LLM Chain to process the data.
4.  Loop through items and apply JavaScript logic.
5.  Evaluate a configured condition.
6.  Export the two branches into separate Excel files.
7.  Review the output and verify data quality.

The workflow can reduce manual effort, but the final output should be
validated before being used for HR, payroll, or other business
decisions.


