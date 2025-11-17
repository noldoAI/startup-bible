#!/usr/bin/env python3
"""
Command-line chatbot interface that uses Claude Code in headless mode.
"""

import argparse
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

# Configuration
SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
CLAUDE_TIMEOUT = 60  # 1 minute timeout
DEFAULT_MODEL = "sonnet"


class CLIChatbot:
    """Command-line chatbot using Claude Code."""

    def __init__(self, model: str = DEFAULT_MODEL, session_id: str = None):
        self.model = model
        self.session_id = session_id or str(uuid.uuid4())
        self.session_file = SESSIONS_DIR / f"{self.session_id}.json"
        self.conversation = self._load_or_create_session()

    def _load_or_create_session(self) -> Dict:
        """Load existing session or create new one."""
        if self.session_file.exists():
            with open(self.session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "session_id": self.session_id,
                "model": self.model,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "messages": []
            }

    def _save_session(self) -> None:
        """Save session to disk."""
        self.conversation["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(self.conversation, f, ensure_ascii=False, indent=2)

    def _build_prompt(self, user_message: str) -> str:
        """Build prompt with conversation history."""
        prompt_parts = []

        # Add system instruction
        prompt_parts.append("You are a helpful AI assistant. Respond to the user's message naturally and conversationally.")

        # Add conversation history (last 10 messages for context)
        if self.conversation["messages"]:
            prompt_parts.append("\nConversation history:")
            for msg in self.conversation["messages"][-10:]:
                role = msg["role"].capitalize()
                content = msg["content"]
                prompt_parts.append(f"{role}: {content}")

        # Add current message
        prompt_parts.append(f"\nUser: {user_message}")
        prompt_parts.append("\nAssistant:")

        return "\n".join(prompt_parts)

    def ask_claude(self, user_message: str) -> str:
        """Send message to Claude Code and get response."""
        prompt = self._build_prompt(user_message)

        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "text",
            "--model", self.model
        ]

        try:
            print("\n[Claude is thinking...]")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=CLAUDE_TIMEOUT
            )

            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error occurred"
                return f"Error: {error_msg}"

            response = result.stdout.strip()

            # Save messages to conversation history
            self.conversation["messages"].append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            self.conversation["messages"].append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            self._save_session()

            return response

        except subprocess.TimeoutExpired:
            return "Error: Request timed out. Please try again."
        except Exception as e:
            return f"Error: {str(e)}"

    def show_history(self) -> None:
        """Display conversation history."""
        if not self.conversation["messages"]:
            print("\nNo conversation history yet.")
            return

        print("\n" + "=" * 60)
        print("Conversation History")
        print("=" * 60)

        for i, msg in enumerate(self.conversation["messages"], 1):
            role = msg["role"].upper()
            content = msg["content"]
            print(f"\n[{i}] {role}:")
            print(content)

        print("\n" + "=" * 60)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation["messages"] = []
        self._save_session()
        print("\nConversation history cleared.")

    def run(self) -> None:
        """Run the interactive chatbot REPL."""
        print("=" * 60)
        print("Claude Code Chatbot (CLI)")
        print("=" * 60)
        print(f"Model: {self.model}")
        print(f"Session ID: {self.session_id}")
        print("\nCommands:")
        print("  /help     - Show help")
        print("  /history  - Show conversation history")
        print("  /clear    - Clear conversation history")
        print("  /quit     - Exit chatbot")
        print("=" * 60)

        # Load existing history if any
        if self.conversation["messages"]:
            print(f"\n[Loaded {len(self.conversation['messages'])} previous messages]")

        while True:
            try:
                # Get user input
                print("\n" + "-" * 60)
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith('/'):
                    command = user_input.lower()

                    if command == '/quit' or command == '/exit':
                        print("\nGoodbye!")
                        break
                    elif command == '/help':
                        print("\nCommands:")
                        print("  /help     - Show this help message")
                        print("  /history  - Show conversation history")
                        print("  /clear    - Clear conversation history")
                        print("  /quit     - Exit chatbot")
                    elif command == '/history':
                        self.show_history()
                    elif command == '/clear':
                        confirm = input("\nAre you sure you want to clear history? (yes/no): ")
                        if confirm.lower() in ['yes', 'y']:
                            self.clear_history()
                    else:
                        print(f"\nUnknown command: {user_input}")
                    continue

                # Get response from Claude
                response = self.ask_claude(user_input)

                # Display response
                print("\n" + "=" * 60)
                print("Claude:")
                print("-" * 60)
                print(response)
                print("=" * 60)

            except KeyboardInterrupt:
                print("\n\nInterrupted. Use /quit to exit.")
            except EOFError:
                print("\n\nGoodbye!")
                break


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Claude Code Chatbot CLI'
    )
    parser.add_argument(
        '--model',
        choices=['opus', 'sonnet', 'haiku'],
        default=DEFAULT_MODEL,
        help=f'Claude model to use (default: {DEFAULT_MODEL})'
    )
    parser.add_argument(
        '--session-id',
        help='Resume a previous session by ID'
    )

    args = parser.parse_args()

    try:
        chatbot = CLIChatbot(model=args.model, session_id=args.session_id)
        chatbot.run()
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
