# Paul Graham Essays

This directory contains a web scraper for collecting Paul Graham's essays from [paulgraham.com](http://paulgraham.com) in LLM-ready JSONL format.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the scraper
python scraper.py
```

## Usage

### First Time Scraping

```bash
python scraper.py
```

This will:
- Fetch the list of all essays from paulgraham.com/articles.html
- Download each essay (200+ essays)
- Extract title, date, content, and footnotes
- Save to `data/essays.jsonl` (one essay per JSON line)
- Use 200ms delay between requests (respectful scraping)
- Take approximately 40-60 seconds total

### Incremental Updates

Run the same command to check for new essays:

```bash
python scraper.py
```

The scraper automatically:
- Loads existing `data/essays.jsonl`
- Only scrapes essays that aren't already downloaded
- Appends new essays to the file

### Force Re-scrape

To re-download all essays (overwriting existing data):

```bash
python scraper.py --force
```

## Output Format

Essays are saved in JSONL format (one JSON object per line) at `data/essays.jsonl`.

Each essay contains:

```json
{
  "id": "greatwork",
  "title": "How to Do Great Work",
  "url": "http://paulgraham.com/greatwork.html",
  "date": "2023-07",
  "content": "Full essay text...",
  "footnotes": ["Footnote 1", "Footnote 2"],
  "word_count": 8432,
  "scraped_at": "2025-11-17T15:30:00Z"
}
```

### Loading the Data

**Python:**
```python
import json

essays = []
with open('data/essays.jsonl', 'r') as f:
    for line in f:
        essays.append(json.loads(line))

print(f"Loaded {len(essays)} essays")
```

**Command line (view first essay):**
```bash
head -n 1 data/essays.jsonl | python -m json.tool
```

## Features

- **Incremental updates**: Only scrapes new essays on subsequent runs
- **Respectful scraping**: 200ms delay between requests
- **Clean text extraction**: Removes HTML, scripts, navigation elements
- **Metadata extraction**: Dates, word counts, footnotes
- **Error handling**: Continues on failures, reports at end
- **Progress tracking**: Shows scraping progress in real-time

## Attribution

All essays are authored by Paul Graham and available at [paulgraham.com](http://paulgraham.com). This scraper is for personal and educational use. Please respect copyright and attribution requirements.
