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
- `data/essays.jsonl` - Output file with scraped essays (JSONL format)
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
- Saves to `data/essays.jsonl` (one essay per line)
- Uses respectful 200ms delay between requests

**Force re-scrape all essays:**
```bash
cd paul-graham
python scraper.py --force
```

## Data Format

Essays are stored in JSONL format where each line is a JSON object containing:
- `id`: Essay identifier (filename without .html)
- `title`: Essay title
- `url`: Source URL
- `date`: Publication date (YYYY-MM format)
- `content`: Full essay text (cleaned, no HTML)
- `footnotes`: Array of footnote texts
- `word_count`: Number of words
- `scraped_at`: Timestamp of scraping
