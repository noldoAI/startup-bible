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
from typing import Dict, List, Optional

# Configuration
SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
CLAUDE_TIMEOUT = 60  # 1 minute timeout
DEFAULT_MODEL = "sonnet"


def generate_title_from_message(message: str, max_length: int = 50) -> str:
    """Generate a conversation title from the first message."""
    if not message:
        return "New Conversation"
    if len(message) > max_length:
        return message[:max_length].strip() + "..."
    return message.strip()


def list_all_sessions() -> List[Dict]:
    """List all saved sessions."""
    sessions = []
    for session_file in SESSIONS_DIR.glob("*.json"):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                message_count = len(data.get("messages", []))
                preview = ""
                if message_count > 0:
                    for msg in data.get("messages", []):
                        if msg.get("role") == "user":
                            preview = msg.get("content", "")[:100]
                            break

                sessions.append({
                    "session_id": data.get("session_id"),
                    "title": data.get("title", generate_title_from_message(preview)),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "message_count": message_count,
                    "preview": preview,
                    "archived": data.get("archived", False),
                    "model": data.get("model", DEFAULT_MODEL)
                })
        except Exception as e:
            print(f"Error loading session {session_file}: {e}")
            continue

    sessions.sort(key=lambda x: x.get("updated_at", x.get("created_at", "")), reverse=True)
    return sessions


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
                data = json.load(f)
                # Add default values for new fields if missing
                if "title" not in data:
                    data["title"] = None
                if "archived" not in data:
                    data["archived"] = False
                return data
        else:
            return {
                "session_id": self.session_id,
                "title": None,
                "archived": False,
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

            # Auto-generate title from first message if not set
            if not self.conversation.get("title") and len(self.conversation["messages"]) == 2:
                self.conversation["title"] = generate_title_from_message(user_message)

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

    def list_conversations(self) -> None:
        """List all saved conversations."""
        sessions = list_all_sessions()

        if not sessions:
            print("\nNo saved conversations found.")
            return

        print("\n" + "=" * 80)
        print("Saved Conversations")
        print("=" * 80)

        for i, sess in enumerate(sessions, 1):
            title = sess.get("title") or "Untitled"
            session_id = sess.get("session_id", "")[:8]  # Show first 8 chars
            msg_count = sess.get("message_count", 0)
            archived = " [ARCHIVED]" if sess.get("archived") else ""
            current = " [CURRENT]" if sess.get("session_id") == self.session_id else ""

            print(f"\n[{i}] {title}{archived}{current}")
            print(f"    ID: {session_id}... | Messages: {msg_count}")
            if sess.get("preview"):
                preview = sess["preview"][:70]
                print(f"    Preview: {preview}...")

        print("\n" + "=" * 80)

    def switch_conversation(self, session_id: str) -> bool:
        """Switch to a different conversation."""
        session_file = SESSIONS_DIR / f"{session_id}.json"

        if not session_file.exists():
            print(f"\nError: Session {session_id} not found.")
            return False

        self.session_id = session_id
        self.session_file = session_file
        self.conversation = self._load_or_create_session()

        title = self.conversation.get("title") or "Untitled"
        msg_count = len(self.conversation.get("messages", []))
        print(f"\nSwitched to conversation: {title}")
        print(f"Session ID: {session_id}")
        print(f"Messages: {msg_count}")
        return True

    def new_conversation(self) -> None:
        """Start a new conversation."""
        self.session_id = str(uuid.uuid4())
        self.session_file = SESSIONS_DIR / f"{self.session_id}.json"
        self.conversation = self._load_or_create_session()
        print(f"\nStarted new conversation.")
        print(f"Session ID: {self.session_id}")

    def delete_conversation(self, session_id: str) -> None:
        """Delete a conversation."""
        session_file = SESSIONS_DIR / f"{session_id}.json"

        if not session_file.exists():
            print(f"\nError: Session {session_id} not found.")
            return

        confirm = input(f"\nAre you sure you want to delete session {session_id[:8]}...? (yes/no): ")
        if confirm.lower() in ['yes', 'y']:
            session_file.unlink()
            print(f"\nSession deleted.")

            # If deleting current session, create new one
            if session_id == self.session_id:
                self.new_conversation()
        else:
            print("\nDeletion cancelled.")

    def set_title(self, title: str) -> None:
        """Set conversation title."""
        self.conversation["title"] = title
        self._save_session()
        print(f"\nTitle updated to: {title}")

    def export_conversation(self, session_id: Optional[str] = None) -> None:
        """Export conversation to file."""
        target_id = session_id or self.session_id
        session_file = SESSIONS_DIR / f"{target_id}.json"

        if not session_file.exists():
            print(f"\nError: Session {target_id} not found.")
            return

        output_file = Path.cwd() / f"conversation_{target_id}.json"

        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\nConversation exported to: {output_file}")

    def search_conversations(self, query: str) -> None:
        """Search across all conversations."""
        query = query.lower()
        results = []

        for session_file in SESSIONS_DIR.glob("*.json"):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # Search in title
                    title = data.get("title", "")
                    if title and query in title.lower():
                        results.append({
                            "session_id": data.get("session_id"),
                            "title": title,
                            "match_type": "title"
                        })
                        continue

                    # Search in messages
                    for msg in data.get("messages", []):
                        if query in msg.get("content", "").lower():
                            results.append({
                                "session_id": data.get("session_id"),
                                "title": title or "Untitled",
                                "match_type": "message"
                            })
                            break
            except Exception as e:
                continue

        if not results:
            print(f"\nNo results found for: {query}")
            return

        print("\n" + "=" * 80)
        print(f"Search Results for: {query}")
        print("=" * 80)

        for i, result in enumerate(results, 1):
            title = result["title"]
            session_id = result["session_id"][:8]
            match_type = result["match_type"]
            print(f"\n[{i}] {title}")
            print(f"    ID: {session_id}... | Match in: {match_type}")

        print("\n" + "=" * 80)

    def run(self) -> None:
        """Run the interactive chatbot REPL."""
        print("=" * 60)
        print("Claude Code Chatbot (CLI)")
        print("=" * 60)
        print(f"Model: {self.model}")
        print(f"Session ID: {self.session_id}")
        title = self.conversation.get("title") or "Untitled"
        print(f"Title: {title}")
        print("\nCommands:")
        print("  /help              - Show help")
        print("  /history           - Show conversation history")
        print("  /clear             - Clear conversation history")
        print("  /list              - List all conversations")
        print("  /new               - Start new conversation")
        print("  /switch <id>       - Switch to conversation by ID")
        print("  /delete <id>       - Delete conversation by ID")
        print("  /title <text>      - Set conversation title")
        print("  /export [id]       - Export conversation to file")
        print("  /search <query>    - Search conversations")
        print("  /quit              - Exit chatbot")
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
                    parts = user_input.split(maxsplit=1)
                    command = parts[0].lower()
                    args = parts[1] if len(parts) > 1 else ""

                    if command == '/quit' or command == '/exit':
                        print("\nGoodbye!")
                        break
                    elif command == '/help':
                        print("\nCommands:")
                        print("  /help              - Show this help message")
                        print("  /history           - Show conversation history")
                        print("  /clear             - Clear conversation history")
                        print("  /list              - List all conversations")
                        print("  /new               - Start new conversation")
                        print("  /switch <id>       - Switch to conversation by ID")
                        print("  /delete <id>       - Delete conversation by ID")
                        print("  /title <text>      - Set conversation title")
                        print("  /export [id]       - Export conversation to file")
                        print("  /search <query>    - Search conversations")
                        print("  /quit              - Exit chatbot")
                    elif command == '/history':
                        self.show_history()
                    elif command == '/clear':
                        confirm = input("\nAre you sure you want to clear history? (yes/no): ")
                        if confirm.lower() in ['yes', 'y']:
                            self.clear_history()
                    elif command == '/list':
                        self.list_conversations()
                    elif command == '/new':
                        self.new_conversation()
                    elif command == '/switch':
                        if not args:
                            print("\nError: Please provide a session ID.")
                            print("Usage: /switch <session_id>")
                        else:
                            self.switch_conversation(args)
                    elif command == '/delete':
                        if not args:
                            print("\nError: Please provide a session ID.")
                            print("Usage: /delete <session_id>")
                        else:
                            self.delete_conversation(args)
                    elif command == '/title':
                        if not args:
                            print("\nError: Please provide a title.")
                            print("Usage: /title <new title>")
                        else:
                            self.set_title(args)
                    elif command == '/export':
                        self.export_conversation(args if args else None)
                    elif command == '/search':
                        if not args:
                            print("\nError: Please provide a search query.")
                            print("Usage: /search <query>")
                        else:
                            self.search_conversations(args)
                    else:
                        print(f"\nUnknown command: {command}")
                        print("Type /help to see available commands.")
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
