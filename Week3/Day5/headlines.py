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
    # Check if the request was successful
    response.raise_for_status()
except requests.exceptions.RequestException as err:
    print(f"Error fetching the page: {err}")
    sys.exit(1)

soup = BeautifulSoup(response.text, "html.parser")

# On BBC News, headline text is consistently stored inside an <h2> element 
# with the attribute data-testid="card-headline"
headline_elements = soup.find_all("h2", attrs={"data-testid": "card-headline"})

# Fallback: if data-testid changes, search for standard semantic headline tags
if not headline_elements:
    headline_elements = soup.find_all(["h2", "h3"])

unique_headlines = []
seen = set()

for tag in headline_elements:
    text = tag.get_text(strip=True)
    # Ignore empty strings or duplicate titles
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