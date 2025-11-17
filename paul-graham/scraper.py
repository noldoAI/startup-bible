#!/usr/bin/env python3
"""
Paul Graham Essay Scraper

Scrapes essays from paulgraham.com and saves them in LLM-ready JSONL format.
Supports incremental updates to avoid re-scraping existing essays.
"""

import argparse
import json
import os
import re
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
OUTPUT_FILE = DATA_DIR / "essays.jsonl"
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
        self.existing_essays: Dict[str, dict] = {}

    def load_existing_essays(self) -> None:
        """Load previously scraped essays from JSONL file."""
        if not self.force_rescrape and OUTPUT_FILE.exists():
            print(f"Loading existing essays from {OUTPUT_FILE}")
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    essay = json.loads(line.strip())
                    self.existing_essays[essay['id']] = essay
            print(f"Found {len(self.existing_essays)} existing essays")

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
        for element in soup(['script', 'style', 'img']):
            element.decompose()

        # Get all text
        all_text = soup.get_text()

        # Split into lines and clean
        lines = [line.strip() for line in all_text.split('\n') if line.strip()]

        # Try to identify where main content starts and ends
        # Usually starts after the date, ends before "Notes" or extensive whitespace
        content_lines = []
        in_content = False
        footnotes = []
        in_footnotes = False

        for i, line in enumerate(lines):
            # Skip very short lines at the start (likely navigation)
            if not in_content and len(line) < 10:
                continue

            # Look for "Notes" section
            if line.lower() == 'notes':
                in_footnotes = True
                in_content = False
                continue

            # Look for "Thanks" section (usually at the end)
            if line.lower().startswith('thanks to'):
                break

            if in_footnotes:
                footnotes.append(line)
            elif not in_content:
                # Start content after we find a substantial paragraph
                if len(line) > 50:
                    in_content = True
                    content_lines.append(line)
            else:
                content_lines.append(line)

        # Join paragraphs with double newlines
        content = '\n\n'.join(content_lines)

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
        essay = {
            'id': essay_id,
            'title': title,
            'url': url,
            'date': date,
            'content': content_data['content'],
            'footnotes': content_data['footnotes'],
            'word_count': content_data['word_count'],
            'scraped_at': datetime.utcnow().isoformat() + 'Z'
        }

        return essay

    def save_essay(self, essay: dict) -> None:
        """Append essay to JSONL file."""
        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True)

        # Append to file
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
            json.dump(essay, f, ensure_ascii=False)
            f.write('\n')

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
            # Clear output file if force re-scraping
            if OUTPUT_FILE.exists():
                OUTPUT_FILE.unlink()

        if not essays:
            print("No new essays to scrape!")
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

        # Summary
        print("\n" + "=" * 60)
        print(f"Scraping complete!")
        print(f"Successfully scraped: {scraped_count}")
        print(f"Failed: {failed_count}")
        print(f"Output saved to: {OUTPUT_FILE}")
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Scrape Paul Graham essays and save to JSONL format'
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
