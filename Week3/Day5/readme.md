# News Headlines Scraper

A lightweight Python script that fetches and extracts the top 5 unique headlines from BBC News using `requests` and `BeautifulSoup4`.

---

## Overview

This project was built as part of the **Week 3 · Day 5** assignment: *Print the Top 5 Headlines from a News Site*. It demonstrates web scraping fundamentals by requesting web pages, parsing raw HTML, and extracting targeted DOM elements cleanly.

---

## Project Structure

```text
headlines/
├── venv/               # Virtual environment directory
├── headlines.py        # Main Python scraping script
└── README.md           # Project documentation
```

---

## Source Code (`headlines.py`)

```python
import sys
import requests
from bs4 import BeautifulSoup

URL = "https://www.bbc.com/news"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

try:
    response = requests.get(URL, headers=HEADERS, timeout=10)
    # Check if the HTTP request was successful (status code 200)
    response.raise_for_status()
except requests.exceptions.RequestException as err:
    print(f"Error fetching the page: {err}")
    sys.exit(1)

soup = BeautifulSoup(response.text, "html.parser")

# Target BBC News headline elements using the data-testid attribute
headline_elements = soup.find_all("h2", attrs={"data-testid": "card-headline"})

# Fallback: if data-testid changes, query generic headline tags
if not headline_elements:
    headline_elements = soup.find_all(["h2", "h3"])

unique_headlines = []
seen = set()

for tag in headline_elements:
    text = tag.get_text(strip=True)
    # Filter empty strings and duplicate entries
    if text and text not in seen:
        seen.add(text)
        unique_headlines.append(text)
    if len(unique_headlines) == 5:
        break

# Handle edge case where fewer than 5 headlines are found
if not unique_headlines:
    print("No headlines found. The site may require JavaScript or updated selectors.")
else:
    for i, headline in enumerate(unique_headlines, 1):
        print(f"{i}. {headline}")
```

---

## Features & Implementation Details

- **Custom User-Agent:** Prevents anti-scraping blocks and 403 Forbidden errors by mimicking a modern desktop browser.
- **Robust Status Checking:** Employs `response.raise_for_status()` inside a `try-except` block to capture network and HTTP errors safely.
- **Precise DOM Selection:** Locates headlines using `h2[data-testid="card-headline"]` to avoid picking up unrelated body text or sidebar navigation links.
- **Deduplication & Sanitization:** Uses a set to prevent repeating stories and applies `.get_text(strip=True)` to remove surrounding whitespace and newline characters.
- **Graceful Fallbacks:** Validates element presence before printing and handles scenarios where fewer than 5 items are found.

---

## Getting Started

### 1. Set Up the Project Directory

```bash
mkdir headlines && cd headlines
python -m venv venv
```

### 2. Activate the Virtual Environment

- **macOS / Linux:**
  ```bash
  source venv/bin/activate
  ```

- **Windows (PowerShell):**
  ```powershell
  venv\Scripts\Activate.ps1
  ```

### 3. Install Dependencies

```bash
pip install requests beautifulsoup4
```

### 4. Run the Script

```bash
python headlines.py
```

---

## Sample Terminal Output

```text
(base) sathishvarun@sathishs-MacBook-Pro Day5 % python headlines.py
1. Inside Ukrainian offensive pushing Russia back - with Starlink playing a key role
2. Watch: BBC follows Ukraine's Operation Vivaldi pushing Russia back on frontline
3. Watch: Will Ukraine get the support needed as tensions with US rise?
4. Watch: Did Tesla really just unveil a flying car?
5. India's 'cockroach' party founder detained ahead of protest
```

---

## Technical Q&A

**Q: What would you do if the page loads its headlines dynamically via JavaScript?**

1. **Direct API Access (DevTools Network Tab):** Modern JavaScript sites often request data asynchronously from internal REST/GraphQL endpoints. Using browser developer tools (`Network` -> `Fetch/XHR`), you can identify the exact JSON feed and pull data directly using `requests.get().json()`.
2. **Headless Browser Engines:** If the HTML is generated entirely on the client without accessible endpoints, use automated browser drivers such as **Playwright** or **Selenium** to wait for the JavaScript to execute and render the elements before parsing.