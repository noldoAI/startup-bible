#!/usr/bin/env python3
"""
Paul Graham Essay Scraper

Scrapes essays from paulgraham.com and saves them as individual Markdown files.
Supports incremental updates to avoid re-scraping existing essays.
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# Configuration
BASE_URL = "http://paulgraham.com"
ARTICLES_URL = f"{BASE_URL}/articles.html"
DATA_DIR = Path(__file__).parent / "data"
ESSAYS_DIR = DATA_DIR / "essays"
INDEX_FILE = DATA_DIR / "index.json"
REQUEST_DELAY = 0.2  # 200ms between requests
TIMEOUT = 30  # Request timeout in seconds


class EssayScraper:
    """Scraper for Paul Graham's essays."""

    def __init__(self, force_rescrape: bool = False):
        self.force_rescrape = force_rescrape
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; PaulGrahamScraper/1.0)'
        })
        self.existing_essays: Set[str] = set()
        self.all_essays: List[dict] = []

    def load_existing_essays(self) -> None:
        """Load previously scraped essays by checking for .md files."""
        if not self.force_rescrape and ESSAYS_DIR.exists():
            md_files = list(ESSAYS_DIR.glob("*.md"))
            for md_file in md_files:
                essay_id = md_file.stem  # filename without extension
                self.existing_essays.add(essay_id)

            if self.existing_essays:
                print(f"Found {len(self.existing_essays)} existing essays")

        # Also load index.json if it exists
        if INDEX_FILE.exists():
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
                self.all_essays = index_data.get('essays', [])

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a page."""
        try:
            response = self.session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'lxml')
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}", file=sys.stderr)
            return None

    def get_essay_urls(self) -> List[tuple[str, str]]:
        """
        Scrape the articles page to get all essay URLs and titles.
        Returns list of (essay_id, url, title) tuples.
        """
        print(f"Fetching essay list from {ARTICLES_URL}")
        soup = self.fetch_page(ARTICLES_URL)
        if not soup:
            raise RuntimeError("Failed to fetch articles page")

        essays = []
        # Find all links that end with .html (excluding index.html and articles.html)
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.endswith('.html') and href not in ['index.html', 'articles.html']:
                # Extract essay ID from filename
                essay_id = href.replace('.html', '')
                title = link.get_text(strip=True)
                url = urljoin(BASE_URL, href)
                essays.append((essay_id, url, title))

        print(f"Found {len(essays)} essays")
        return essays

    def extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date from essay page."""
        # Look for date pattern like "July 2023" or "September 2024"
        text = soup.get_text()
        # Common pattern: Month Year (at the beginning of the essay)
        date_pattern = r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b'
        match = re.search(date_pattern, text[:2000])  # Search in first 2000 chars
        if match:
            month, year = match.groups()
            # Convert to YYYY-MM format
            month_num = {
                'January': '01', 'February': '02', 'March': '03', 'April': '04',
                'May': '05', 'June': '06', 'July': '07', 'August': '08',
                'September': '09', 'October': '10', 'November': '11', 'December': '12'
            }[month]
            return f"{year}-{month_num}"
        return None

    def extract_content(self, soup: BeautifulSoup) -> Dict[str, any]:
        """Extract essay content, footnotes, and other metadata."""
        # Remove script and style elements
        for element in soup(['script', 'style', 'img', 'map', 'area']):
            element.decompose()

        # Paul Graham's essays use <font> tags with <br><br> for paragraphs
        # Find the main font tag containing the essay
        font_tag = soup.find('font', {'size': '2', 'face': 'verdana'})

        if not font_tag:
            # Fallback: try to find any font tag
            font_tag = soup.find('font')

        if not font_tag:
            # Last resort: use the whole body
            font_tag = soup.find('body')

        if not font_tag:
            return {'content': '', 'footnotes': [], 'word_count': 0}

        # Get HTML content and split by <br><br> or <br /><br />
        html_content = str(font_tag)

        # Replace various br combinations with a marker
        html_content = re.sub(r'<br\s*/?>\s*<br\s*/?>', '\n\n||PARAGRAPH||\n\n', html_content, flags=re.IGNORECASE)

        # Parse the modified HTML
        temp_soup = BeautifulSoup(html_content, 'lxml')

        # Get text and split on our marker
        text = temp_soup.get_text()
        paragraphs = [p.strip() for p in text.split('||PARAGRAPH||') if p.strip()]

        content_paras = []
        footnotes = []
        in_footnotes = False
        started_content = False

        for para in paragraphs:
            if not para:
                continue

            # Look for "Notes" section
            if para.lower().strip() == 'notes':
                in_footnotes = True
                continue

            # Look for "Thanks" section (usually at the end)
            if para.lower().startswith('thanks to'):
                break

            if in_footnotes:
                footnotes.append(para)
            else:
                # Skip very short paragraphs at the start (likely navigation)
                if not started_content and len(para) < 20:
                    continue

                started_content = True
                content_paras.append(para)

        # Join paragraphs with double newlines
        content = '\n\n'.join(content_paras)

        # Calculate word count
        word_count = len(content.split())

        return {
            'content': content,
            'footnotes': footnotes,
            'word_count': word_count
        }

    def scrape_essay(self, essay_id: str, url: str, title: str) -> Optional[dict]:
        """Scrape a single essay."""
        # Check if already scraped
        if not self.force_rescrape and essay_id in self.existing_essays:
            return None

        print(f"Scraping: {title} ({essay_id})")

        soup = self.fetch_page(url)
        if not soup:
            return None

        # Extract date
        date = self.extract_date(soup)

        # Extract content
        content_data = self.extract_content(soup)

        # Build essay object
        from datetime import timezone
        essay = {
            'id': essay_id,
            'title': title,
            'url': url,
            'date': date,
            'content': content_data['content'],
            'footnotes': content_data['footnotes'],
            'word_count': content_data['word_count'],
            'scraped_at': datetime.now(timezone.utc).isoformat()
        }

        return essay

    def save_essay(self, essay: dict) -> None:
        """Save essay as individual Markdown file with YAML frontmatter."""
        # Ensure essays directory exists
        ESSAYS_DIR.mkdir(parents=True, exist_ok=True)

        # Build Markdown content with YAML frontmatter
        md_content = f"""---
id: {essay['id']}
title: {essay['title']}
date: {essay['date'] or 'unknown'}
url: {essay['url']}
word_count: {essay['word_count']}
has_footnotes: {len(essay['footnotes']) > 0}
scraped_at: {essay['scraped_at']}
---

# {essay['title']}

{essay['content']}
"""

        # Add footnotes section if present
        if essay['footnotes']:
            md_content += "\n\n## Notes\n\n"
            for i, footnote in enumerate(essay['footnotes'], 1):
                md_content += f"[{i}] {footnote}\n\n"

        # Write to file
        essay_file = ESSAYS_DIR / f"{essay['id']}.md"
        with open(essay_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

        # Add to all_essays list for index
        essay_metadata = {
            'id': essay['id'],
            'title': essay['title'],
            'date': essay['date'],
            'url': essay['url'],
            'file': f"essays/{essay['id']}.md",
            'word_count': essay['word_count'],
            'has_footnotes': len(essay['footnotes']) > 0,
            'scraped_at': essay['scraped_at']
        }
        self.all_essays.append(essay_metadata)

    def create_index(self) -> None:
        """Create or update index.json with essay metadata."""
        # Sort essays by date (most recent first), then by title
        sorted_essays = sorted(
            self.all_essays,
            key=lambda e: (e['date'] or '0000-00', e['title']),
            reverse=True
        )

        from datetime import timezone
        index_data = {
            'essays': sorted_essays,
            'total_count': len(sorted_essays),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }

        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True)

        # Write index file
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

        print(f"\nIndex updated: {INDEX_FILE}")
        print(f"Total essays in index: {len(sorted_essays)}")

    def run(self) -> None:
        """Run the scraper."""
        print("=" * 60)
        print("Paul Graham Essay Scraper")
        print("=" * 60)

        # Load existing essays
        self.load_existing_essays()

        # Get list of all essays
        essays = self.get_essay_urls()

        # Filter out already scraped essays
        if not self.force_rescrape:
            new_essays = [(id, url, title) for id, url, title in essays
                         if id not in self.existing_essays]
            print(f"\nNew essays to scrape: {len(new_essays)}")
            essays = new_essays
        else:
            print(f"\nForce re-scraping all {len(essays)} essays")
            # Clear essays directory if force re-scraping
            if ESSAYS_DIR.exists():
                shutil.rmtree(ESSAYS_DIR)
            # Clear existing data
            self.all_essays = []

        if not essays:
            print("No new essays to scrape!")
            # Still create/update index if we have existing essays
            if self.all_essays:
                self.create_index()
            return

        # Scrape each essay
        print("\nStarting scrape...")
        scraped_count = 0
        failed_count = 0

        for i, (essay_id, url, title) in enumerate(essays, 1):
            print(f"\n[{i}/{len(essays)}] ", end='')

            essay = self.scrape_essay(essay_id, url, title)

            if essay:
                self.save_essay(essay)
                scraped_count += 1
                print(f"✓ Saved ({essay['word_count']} words)")
            else:
                failed_count += 1
                print("✗ Failed or skipped")

            # Rate limiting (except for last essay)
            if i < len(essays):
                time.sleep(REQUEST_DELAY)

        # Create/update index
        self.create_index()

        # Summary
        print("\n" + "=" * 60)
        print(f"Scraping complete!")
        print(f"Successfully scraped: {scraped_count}")
        print(f"Failed: {failed_count}")
        print(f"Essays saved to: {ESSAYS_DIR}")
        print(f"Index saved to: {INDEX_FILE}")
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Scrape Paul Graham essays and save as individual Markdown files'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-scrape all essays, even if already downloaded'
    )

    args = parser.parse_args()

    try:
        scraper = EssayScraper(force_rescrape=args.force)
        scraper.run()
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
