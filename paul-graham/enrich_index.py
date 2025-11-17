#!/usr/bin/env python3
"""
Paul Graham Essay Index Enrichment Script

Uses Claude Code in headless mode to enrich index.json with metadata for
conversational chatbot retrieval:
- Summary
- Topics
- Key concepts
- Questions answered
- Related essays
- Target audience
- Difficulty level
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# Configuration
DATA_DIR = Path(__file__).parent / "data"
ESSAYS_DIR = DATA_DIR / "essays"
INDEX_FILE = DATA_DIR / "index.json"
LOG_FILE = Path(__file__).parent / "enrichment.log"
REQUEST_DELAY = 2.0  # 2 seconds between requests
CLAUDE_TIMEOUT = 300  # 5 minutes per essay


class IndexEnricher:
    """Enriches index.json with AI-generated metadata."""

    def __init__(self, limit: Optional[int] = None, force: bool = False, model: str = "opus"):
        self.limit = limit
        self.force = force
        self.model = model
        self.index_data = {}
        self.processed_count = 0
        self.failed_count = 0
        self.skipped_count = 0

    def load_index(self) -> None:
        """Load the current index.json file."""
        if not INDEX_FILE.exists():
            raise FileNotFoundError(f"Index file not found: {INDEX_FILE}")

        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            self.index_data = json.load(f)

        print(f"Loaded index with {self.index_data['total_count']} essays")

    def save_index(self) -> None:
        """Save the updated index.json file."""
        from datetime import timezone
        self.index_data['last_updated'] = datetime.now(timezone.utc).isoformat()

        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.index_data, f, ensure_ascii=False, indent=2)

    def log(self, message: str, level: str = "INFO") -> None:
        """Write to log file and print to console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"

        print(log_message)

        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')

    def needs_enrichment(self, essay: Dict) -> bool:
        """Check if an essay needs enrichment."""
        if self.force:
            return True

        # Check if all required metadata fields exist
        required_fields = [
            'summary', 'topics', 'key_concepts', 'questions_answered',
            'target_audience', 'difficulty_level'
        ]

        return not all(field in essay for field in required_fields)

    def extract_metadata(self, essay: Dict) -> Optional[Dict]:
        """Use Claude Code to extract metadata from an essay."""
        essay_path = DATA_DIR / essay['file']

        if not essay_path.exists():
            self.log(f"Essay file not found: {essay_path}", "ERROR")
            return None

        # Construct the prompt
        prompt = f"""Analyze the essay at {essay_path} and extract metadata in JSON format.

Read the essay and provide the following metadata:

1. **summary**: A 2-3 sentence overview of the main points
2. **topics**: Array of 3-6 topic tags (e.g., ["startups", "fundraising", "product-market-fit"])
3. **key_concepts**: Array of 3-5 main ideas or key terms from the essay
4. **questions_answered**: Array of 2-4 questions this essay addresses
5. **target_audience**: Array of 1-3 audience types (e.g., ["founders", "investors", "programmers"])
6. **difficulty_level**: One of "beginner", "intermediate", or "advanced"

Return ONLY a JSON object with these exact keys. No additional text or explanation.

Example format:
{{
  "summary": "Brief overview of the essay...",
  "topics": ["topic1", "topic2"],
  "key_concepts": ["concept1", "concept2"],
  "questions_answered": ["Question 1?", "Question 2?"],
  "target_audience": ["audience1", "audience2"],
  "difficulty_level": "intermediate"
}}"""

        try:
            # Call Claude Code in headless mode
            cmd = [
                "claude",
                "-p", prompt,
                "--output-format", "json",
                "--model", self.model
            ]

            self.log(f"Processing: {essay['title']} ({essay['id']})")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=CLAUDE_TIMEOUT
            )

            if result.returncode != 0:
                self.log(f"Claude Code failed: {result.stderr}", "ERROR")
                return None

            # Parse the JSON output
            try:
                response = json.loads(result.stdout)

                # Extract the result field from Claude's JSON response
                if 'result' in response:
                    # The result field contains the actual metadata as a string
                    # We need to parse it again
                    metadata_str = response['result']

                    # Try to find JSON in the result string
                    # Claude might return it wrapped in markdown code blocks
                    if '```json' in metadata_str:
                        # Extract JSON from markdown code block
                        start = metadata_str.find('{')
                        end = metadata_str.rfind('}') + 1
                        metadata_str = metadata_str[start:end]
                    elif '```' in metadata_str:
                        # Remove markdown code blocks
                        metadata_str = metadata_str.replace('```', '').strip()

                    metadata = json.loads(metadata_str)

                    # Log cost if available
                    if 'total_cost_usd' in response:
                        self.log(f"Cost: ${response['total_cost_usd']:.4f}")

                    return metadata
                else:
                    self.log(f"Unexpected response format: {response}", "ERROR")
                    return None

            except json.JSONDecodeError as e:
                self.log(f"Failed to parse JSON response: {e}", "ERROR")
                self.log(f"Response: {result.stdout[:500]}", "ERROR")
                return None

        except subprocess.TimeoutExpired:
            self.log(f"Timeout processing essay: {essay['id']}", "ERROR")
            return None
        except Exception as e:
            self.log(f"Error processing essay: {e}", "ERROR")
            return None

    def enrich_essay(self, essay: Dict) -> bool:
        """Enrich a single essay with metadata."""
        if not self.needs_enrichment(essay):
            self.log(f"Skipping (already enriched): {essay['title']}")
            self.skipped_count += 1
            return True

        metadata = self.extract_metadata(essay)

        if metadata is None:
            self.failed_count += 1
            return False

        # Merge metadata into essay
        essay.update(metadata)

        # Mark as enriched
        from datetime import timezone
        essay['enriched_at'] = datetime.now(timezone.utc).isoformat()

        self.processed_count += 1
        self.log(f"✓ Enriched: {essay['title']}")

        return True

    def run(self) -> None:
        """Run the enrichment process."""
        print("=" * 60)
        print("Paul Graham Essay Index Enrichment")
        print("=" * 60)
        print(f"Model: {self.model}")
        print(f"Limit: {self.limit if self.limit else 'None (all essays)'}")
        print(f"Force re-enrich: {self.force}")
        print("=" * 60)

        # Initialize log
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"Enrichment started at {datetime.now()}\n")
            f.write("=" * 60 + "\n")

        # Load index
        self.load_index()

        # Get essays to process
        essays = self.index_data['essays']

        if self.limit:
            essays = essays[:self.limit]
            self.log(f"Processing first {self.limit} essays")
        else:
            self.log(f"Processing all {len(essays)} essays")

        # Process each essay
        for i, essay in enumerate(essays, 1):
            print(f"\n[{i}/{len(essays)}]", end=" ")

            # Enrich the essay
            success = self.enrich_essay(essay)

            # Save progress incrementally
            if success:
                self.save_index()

            # Rate limiting (except for last essay)
            if i < len(essays):
                time.sleep(REQUEST_DELAY)

        # Final summary
        print("\n" + "=" * 60)
        print("Enrichment Complete!")
        print(f"Successfully enriched: {self.processed_count}")
        print(f"Already enriched (skipped): {self.skipped_count}")
        print(f"Failed: {self.failed_count}")
        print(f"Index saved to: {INDEX_FILE}")
        print(f"Log saved to: {LOG_FILE}")
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Enrich Paul Graham essay index with AI-generated metadata'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of essays to process (for testing)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-enrich essays that already have metadata'
    )
    parser.add_argument(
        '--model',
        choices=['opus', 'sonnet', 'haiku'],
        default='opus',
        help='Claude model to use (default: opus)'
    )

    args = parser.parse_args()

    try:
        enricher = IndexEnricher(
            limit=args.limit,
            force=args.force,
            model=args.model
        )
        enricher.run()
    except KeyboardInterrupt:
        print("\n\nEnrichment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
