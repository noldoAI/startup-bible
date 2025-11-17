# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is a collection of startup resources designed to be LLM-ready and conversational. The initial focus is on gathering and structuring essays from Paul Graham, with the goal of making this knowledge easily accessible through conversational interfaces.

## Project Goals

- Gather high-quality startup resources (essays, articles, guides)
- Structure the content to be LLM-ready and conversational
- Enable easy querying and interaction with startup knowledge

## Development Setup

**Create and activate virtual environment:**
```bash
# Create venv
python3 -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
# venv\Scripts\activate
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Deactivate when done:**
```bash
deactivate
```

## Repository Structure

### paul-graham/
Contains a web scraper for Paul Graham's essays from paulgraham.com.

**Key files:**
- `scraper.py` - Main scraping script
- `requirements.txt` - Python dependencies (requests, beautifulsoup4, lxml)
- `data/essays/` - Individual Markdown files for each essay
- `data/index.json` - Metadata index for all essays
- `README.md` - Detailed documentation

## Common Commands

### Paul Graham Essay Scraper

**Scrape essays (incremental):**
```bash
cd paul-graham
python scraper.py
```

This automatically:
- Downloads only new essays (if run previously)
- Saves each essay as individual Markdown file in `data/essays/`
- Updates `data/index.json` with metadata
- Uses respectful 200ms delay between requests

**Force re-scrape all essays:**
```bash
cd paul-graham
python scraper.py --force
```

## Data Format

### Individual Markdown Files
Each essay is saved as `paul-graham/data/essays/{essay-id}.md` with:
- **YAML frontmatter**: Contains id, title, date, url, word_count, has_footnotes, scraped_at
- **Main content**: Essay text with proper formatting
- **Notes section**: Footnotes (if present)

### Index File
`paul-graham/data/index.json` contains metadata for all essays:
- `essays`: Array of essay metadata (id, title, date, url, file path, word_count, etc.)
- `total_count`: Total number of essays
- `last_updated`: Timestamp of last scrape

**Future extensibility**: The index can be enhanced with AI-generated summaries, topics, key_concepts, and related_essays for better LLM navigation.
