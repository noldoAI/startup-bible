# startup-bible

A collection of startup resources designed to be LLM-ready and conversational. This repository gathers high-quality startup knowledge and structures it for easy access through conversational AI interfaces.

## Quick Start

```bash
# Clone the repository
git clone <your-repo-url>
cd startup-bible

# Set up Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Scrape Paul Graham essays
cd paul-graham
python scraper.py
```

## What's Included

### Paul Graham Essays

A web scraper that collects all 200+ essays from [paulgraham.com](http://paulgraham.com) in LLM-ready Markdown format.

- **Location**: `paul-graham/`
- **Output**: Individual `.md` files in `paul-graham/data/essays/`
- **Index**: `paul-graham/data/index.json` with metadata for all essays
- **Features**: Incremental updates, clean text extraction, YAML frontmatter, metadata index

See [paul-graham/README.md](paul-graham/README.md) for detailed usage.

## Project Goals

- Gather high-quality startup resources (essays, articles, guides)
- Structure content to be LLM-ready and conversational
- Enable easy querying and interaction with startup knowledge

## Future Plans

- Add more startup resource collections
- Implement search and query interfaces
- Create embeddings for RAG systems
- Build conversational interfaces for exploring startup knowledge