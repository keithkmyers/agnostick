# Simple one-shot scraper: dump all Agno docs into a single Markdown file.

import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path

# constants --------------------------------------------------------------- #
SITE = "https://docs.agno.com/"
OUTPUT_FILE = "./agno_llms_full.txt"
PROXY = None  # optional proxy

# helpers ----------------------------------------------------------------- #
def extract_pages(obj):
    """Recursively collect every page path from the nav structure."""
    pages = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'pages':
                pages.extend(_flatten_pages_value(value))
            else:
                pages.extend(extract_pages(value))
    elif isinstance(obj, list):
        for item in obj:
            pages.extend(extract_pages(item))
    return pages

def _flatten_pages_value(value):
    """Helper for extract_pages(), flattens nested 'pages' lists."""
    pages = []
    for item in value:
        if isinstance(item, str):
            pages.append(item)
        elif isinstance(item, dict):
            pages.extend(_flatten_pages_value(item.get('pages', [])))
    return pages

def show_progress(current: int, total: int, width: int = 40) -> None:
    """CLI progress bar."""
    pct = current / total
    filled = int(width * pct)
    bar = "█" * filled + "-" * (width - filled)
    print(f"\r[{bar}] {pct:6.2%}", end="", flush=True)

# main -------------------------------------------------------------------- #
def main() -> None:
    """Fetch sitemap, download each .md file, save to OUTPUT_FILE."""
    output_file_path = Path(OUTPUT_FILE)
    html = requests.get(SITE, proxies=PROXY).text
    soup = BeautifulSoup(html, "html.parser")
    json_text = soup.find("script", id="__NEXT_DATA__").string
    data = json.loads(json_text)['props']['pageProps']['pageData']['docsConfig']['navigation']

    all_pages = extract_pages(data)
    total = len(all_pages)
    success_count = 0
    output_lines = []

    print(f"Extracting {SITE} markdown...")

    for idx, page in enumerate(all_pages, 1):
        url = f"{SITE}/{page}.md"
        r = requests.get(url, proxies=PROXY)
        if r.status_code != 200:
            print("\nThrottling...")
            time.sleep(30) # Wait 30 seconds if we hit an error and retry that same page
            r = requests.get(url, proxies=PROXY)
            if r.status_code != 200:
                print(f"\n⚠️  failed page extraction after 2 attempts & throttle: {url}")
                show_progress(idx, total)
                continue
        success_count += 1
        output_lines.append(f"# {page}\n\n")
        output_lines.append(r.text)
        output_lines.append("\n\n")
        show_progress(idx, total)

    with open(output_file_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    success_pct = (success_count / total) * 100
    print(f"\n✅ combined {success_count}/{total} pages ({success_pct:.1f}%) → {output_file_path}")

if __name__ == "__main__":
    main()
