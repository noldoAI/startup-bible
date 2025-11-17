#!/usr/bin/env python3
"""
Flask-based chatbot web interface that uses Claude Code in headless mode.
"""

import argparse
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # Change this in production!

# Configuration
SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
CLAUDE_TIMEOUT = 60  # 1 minute timeout for Claude responses
DEFAULT_MODEL = "sonnet"


class ConversationManager:
    """Manages conversation history and Claude Code interaction."""

    def __init__(self, session_id: str, model: str = DEFAULT_MODEL):
        self.session_id = session_id
        self.model = model
        self.session_file = SESSIONS_DIR / f"{session_id}.json"
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

    def ask_claude(self, user_message: str) -> Dict:
        """
        Send message to Claude Code and get response.
        Returns dict with 'success', 'response', and optional 'error'.
        """
        prompt = self._build_prompt(user_message)

        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "text",
            "--model", self.model
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=CLAUDE_TIMEOUT
            )

            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error occurred"
                return {
                    "success": False,
                    "error": error_msg,
                    "response": f"Error: {error_msg}"
                }

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

            return {
                "success": True,
                "response": response
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Request timed out",
                "response": "Error: Request timed out. Please try again."
            }
        except Exception as e:
            error_msg = str(e)
            return {
                "success": False,
                "error": error_msg,
                "response": f"Error: {error_msg}"
            }

    def get_history(self) -> List[Dict]:
        """Get conversation history."""
        return self.conversation["messages"]

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation["messages"] = []
        self._save_session()


# Flask Routes

@app.route('/')
def index():
    """Serve the chat interface."""
    # Initialize session ID if not exists
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages."""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    model = data.get('model', DEFAULT_MODEL)

    if not user_message:
        return jsonify({"success": False, "error": "Message cannot be empty"}), 400

    # Get or create session
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id

    # Process message
    manager = ConversationManager(session_id, model)
    result = manager.ask_claude(user_message)

    return jsonify(result)


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get conversation history."""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({"messages": []})

    model = request.args.get('model', DEFAULT_MODEL)
    manager = ConversationManager(session_id, model)
    history = manager.get_history()

    return jsonify({"messages": history})


@app.route('/api/clear', methods=['POST'])
def clear_history():
    """Clear conversation history."""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({"success": True})

    model = request.args.get('model', DEFAULT_MODEL)
    manager = ConversationManager(session_id, model)
    manager.clear_history()

    return jsonify({"success": True})


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Claude Code Chatbot Web Interface'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to bind to (default: 5000)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Claude Code Chatbot Web Interface")
    print("=" * 60)
    print(f"Starting server at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
