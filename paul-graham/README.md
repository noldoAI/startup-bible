# Paul Graham Essays

This directory contains a web scraper for collecting Paul Graham's essays from [paulgraham.com](http://paulgraham.com) in LLM-ready Markdown format.

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
- Save each essay as an individual Markdown file in `data/essays/`
- Generate `data/index.json` with metadata for all essays
- Use 200ms delay between requests (respectful scraping)
- Take approximately 40-60 seconds total

### Incremental Updates

Run the same command to check for new essays:

```bash
python scraper.py
```

The scraper automatically:
- Checks for existing `.md` files in `data/essays/`
- Only scrapes essays that aren't already downloaded
- Updates `index.json` with new entries

### Force Re-scrape

To re-download all essays (overwriting existing data):

```bash
python scraper.py --force
```

## Output Format

### Individual Markdown Files

Each essay is saved as `data/essays/{essay-id}.md` with YAML frontmatter:

```markdown
---
id: greatwork
title: How to Do Great Work
date: 2023-07
url: http://paulgraham.com/greatwork.html
word_count: 8432
has_footnotes: true
scraped_at: 2025-11-17T15:30:00Z
---

# How to Do Great Work

Essay content here...

## Notes

[1] Footnote text...
```

### Index File

The `data/index.json` file contains metadata for all essays:

```json
{
  "essays": [
    {
      "id": "greatwork",
      "title": "How to Do Great Work",
      "date": "2023-07",
      "url": "http://paulgraham.com/greatwork.html",
      "file": "essays/greatwork.md",
      "word_count": 8432,
      "has_footnotes": true,
      "scraped_at": "2025-11-17T15:30:00Z"
    }
  ],
  "total_count": 218,
  "last_updated": "2025-11-17T15:30:00Z"
}
```

**Future extensibility**: The index can be enhanced with:
- `summary`: AI-generated essay summaries
- `topics`: Categorization tags
- `key_concepts`: Main ideas
- `related_essays`: Cross-references

### Loading the Data

**Read index:**
```python
import json

with open('data/index.json', 'r') as f:
    index = json.load(f)

print(f"Total essays: {index['total_count']}")
for essay in index['essays'][:5]:
    print(f"- {essay['title']} ({essay['date']})")
```

**Read individual essay:**
```python
with open('data/essays/greatwork.md', 'r') as f:
    content = f.read()
print(content)
```

**Command line (view essay list):**
```bash
python -m json.tool data/index.json | grep title
```

## Features

- **Individual Markdown files**: Each essay saved separately for easy LLM consumption
- **Metadata index**: Quick navigation via index.json
- **Incremental updates**: Only scrapes new essays on subsequent runs
- **Respectful scraping**: 200ms delay between requests
- **Clean text extraction**: Removes HTML, scripts, navigation elements
- **YAML frontmatter**: Structured metadata in each file
- **Error handling**: Continues on failures, reports at end
- **Progress tracking**: Shows scraping progress in real-time

## Attribution

All essays are authored by Paul Graham and available at [paulgraham.com](http://paulgraham.com). This scraper is for personal and educational use. Please respect copyright and attribution requirements.
