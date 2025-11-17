#!/usr/bin/env python3
"""
Flask-based chatbot web interface that uses Claude Code in headless mode.
"""

import argparse
import json
import secrets
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, render_template, request, jsonify, session, send_file, redirect
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # Change this in production!

# Configuration
SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
SHARES_FILE = SESSIONS_DIR / "shares.json"
CLAUDE_TIMEOUT = 60  # 1 minute timeout for Claude responses
DEFAULT_MODEL = "sonnet"


def generate_title_from_message(message: str, max_length: int = 50) -> str:
    """Generate a conversation title from the first message."""
    if not message:
        return "New Conversation"
    # Truncate and add ellipsis if too long
    if len(message) > max_length:
        return message[:max_length].strip() + "..."
    return message.strip()


def get_all_sessions() -> List[Dict]:
    """Get metadata for all saved sessions."""
    sessions = []
    for session_file in SESSIONS_DIR.glob("*.json"):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Calculate preview and message count
                message_count = len(data.get("messages", []))
                preview = ""
                if message_count > 0:
                    # Get first user message as preview
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

    # Sort by updated_at (most recent first), handle None values
    sessions.sort(key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)
    return sessions


def load_shares() -> Dict:
    """Load the shares registry from file."""
    if SHARES_FILE.exists():
        try:
            with open(SHARES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading shares: {e}")
            return {}
    return {}


def save_shares(shares: Dict):
    """Save the shares registry to file."""
    try:
        with open(SHARES_FILE, 'w', encoding='utf-8') as f:
            json.dump(shares, f, indent=2)
    except Exception as e:
        print(f"Error saving shares: {e}")


def generate_share_token() -> str:
    """Generate a secure random token for sharing."""
    return secrets.token_urlsafe(32)


def create_share_link(session_id: str) -> str:
    """Create a shareable link for a conversation."""
    shares = load_shares()

    # Check if there's already a share token for this session
    for token, data in shares.items():
        if data.get("session_id") == session_id:
            # Return existing token
            return token

    # Generate new token
    token = generate_share_token()
    shares[token] = {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True
    }
    save_shares(shares)
    return token


def get_session_from_token(token: str) -> Optional[str]:
    """Get session ID from share token."""
    shares = load_shares()
    share_data = shares.get(token)
    if share_data:
        return share_data.get("session_id")
    return None


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
                data = json.load(f)
                # Add default values for new fields if missing (backward compatibility)
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

            # Auto-generate title from first message if not set
            if not self.conversation.get("title") and len(self.conversation["messages"]) == 2:
                self.conversation["title"] = generate_title_from_message(user_message)

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

    def update_title(self, title: str) -> None:
        """Update conversation title."""
        self.conversation["title"] = title
        self._save_session()

    def update_archived(self, archived: bool) -> None:
        """Update archived status."""
        self.conversation["archived"] = archived
        self._save_session()

    def get_metadata(self) -> Dict:
        """Get conversation metadata."""
        return {
            "session_id": self.conversation["session_id"],
            "title": self.conversation.get("title"),
            "archived": self.conversation.get("archived", False),
            "model": self.conversation["model"],
            "created_at": self.conversation.get("created_at"),
            "updated_at": self.conversation.get("updated_at"),
            "message_count": len(self.conversation["messages"])
        }


# Flask Routes

@app.route('/')
def index():
    """Redirect to latest conversation or create new one."""
    # Get all sessions and redirect to latest, or create new
    sessions = get_all_sessions()

    if sessions and len(sessions) > 0:
        # Redirect to latest conversation
        latest_id = sessions[0]['session_id']
        return redirect(f'/c/{latest_id}')
    else:
        # Create new conversation
        new_id = str(uuid.uuid4())
        return redirect(f'/c/{new_id}')


@app.route('/c/<session_id>')
def chat_session(session_id):
    """Serve the chat interface for a specific conversation."""
    try:
        # Validate session format (UUID)
        try:
            uuid.UUID(session_id)
        except ValueError:
            return render_template('error.html',
                                 message="Invalid conversation ID"), 400

        # Session file might not exist yet (for new conversations)
        # That's OK - it will be created on first message

        # Set Flask session for backward compatibility
        session['session_id'] = session_id

        # Return the chat template with session_id
        return render_template('index.html', session_id=session_id)
    except Exception as e:
        return render_template('error.html',
                             message=f"Error loading conversation: {str(e)}"), 500


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


@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get list of all conversations."""
    try:
        sessions = get_all_sessions()
        return jsonify({"success": True, "conversations": sessions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/conversations/new', methods=['POST'])
def new_conversation():
    """Create a new conversation."""
    try:
        # Generate new session ID
        new_session_id = str(uuid.uuid4())
        session['session_id'] = new_session_id

        # Create new conversation manager (this will create the session file)
        data = request.get_json() or {}
        model = data.get('model', DEFAULT_MODEL)
        manager = ConversationManager(new_session_id, model)

        return jsonify({
            "success": True,
            "session_id": new_session_id,
            "metadata": manager.get_metadata()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/conversations/<session_id>/switch', methods=['POST'])
def switch_conversation(session_id):
    """Switch to a different conversation."""
    try:
        # Check if session exists
        session_file = SESSIONS_DIR / f"{session_id}.json"
        if not session_file.exists():
            return jsonify({"success": False, "error": "Session not found"}), 404

        # Update Flask session
        session['session_id'] = session_id

        # Load conversation
        data = request.get_json() or {}
        model = data.get('model', DEFAULT_MODEL)
        manager = ConversationManager(session_id, model)

        return jsonify({
            "success": True,
            "session_id": session_id,
            "messages": manager.get_history(),
            "metadata": manager.get_metadata()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/conversations/<session_id>', methods=['DELETE'])
def delete_conversation(session_id):
    """Delete a conversation."""
    try:
        session_file = SESSIONS_DIR / f"{session_id}.json"
        if not session_file.exists():
            return jsonify({"success": False, "error": "Session not found"}), 404

        # Delete the file
        os.remove(session_file)

        # Clear current session if it's the one being deleted
        if session.get('session_id') == session_id:
            session.pop('session_id', None)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/conversations/<session_id>/export', methods=['GET'])
def export_conversation(session_id):
    """Export conversation as JSON file."""
    try:
        session_file = SESSIONS_DIR / f"{session_id}.json"
        if not session_file.exists():
            return jsonify({"success": False, "error": "Session not found"}), 404

        # Send file as attachment
        return send_file(
            session_file,
            mimetype='application/json',
            as_attachment=True,
            download_name=f"conversation_{session_id}.json"
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/conversations/<session_id>/title', methods=['PUT'])
def update_conversation_title(session_id):
    """Update conversation title."""
    try:
        data = request.get_json()
        title = data.get('title', '').strip()

        if not title:
            return jsonify({"success": False, "error": "Title cannot be empty"}), 400

        session_file = SESSIONS_DIR / f"{session_id}.json"
        if not session_file.exists():
            return jsonify({"success": False, "error": "Session not found"}), 404

        model = data.get('model', DEFAULT_MODEL)
        manager = ConversationManager(session_id, model)
        manager.update_title(title)

        return jsonify({"success": True, "title": title})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/conversations/<session_id>/archive', methods=['PUT'])
def update_conversation_archive(session_id):
    """Update conversation archived status."""
    try:
        data = request.get_json()
        archived = data.get('archived', False)

        session_file = SESSIONS_DIR / f"{session_id}.json"
        if not session_file.exists():
            return jsonify({"success": False, "error": "Session not found"}), 404

        model = data.get('model', DEFAULT_MODEL)
        manager = ConversationManager(session_id, model)
        manager.update_archived(archived)

        return jsonify({"success": True, "archived": archived})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/conversations/search', methods=['GET'])
def search_conversations():
    """Search across all conversations."""
    try:
        query = request.args.get('q', '').strip().lower()
        if not query:
            return jsonify({"success": False, "error": "Query cannot be empty"}), 400

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
                            "match_type": "title",
                            "excerpt": title
                        })
                        continue

                    # Search in messages
                    for msg in data.get("messages", []):
                        content = msg.get("content", "")
                        if query in content.lower():
                            # Extract excerpt around match
                            idx = content.lower().index(query)
                            start = max(0, idx - 50)
                            end = min(len(content), idx + len(query) + 50)
                            excerpt = content[start:end]
                            if start > 0:
                                excerpt = "..." + excerpt
                            if end < len(content):
                                excerpt = excerpt + "..."

                            results.append({
                                "session_id": data.get("session_id"),
                                "title": data.get("title", generate_title_from_message(
                                    next((m["content"] for m in data.get("messages", []) if m.get("role") == "user"), "")
                                )),
                                "match_type": "message",
                                "excerpt": excerpt
                            })
                            break  # Only include each conversation once
            except Exception as e:
                print(f"Error searching session {session_file}: {e}")
                continue

        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/conversations/<session_id>/share', methods=['POST'])
def share_conversation(session_id):
    """Create a shareable link for a conversation."""
    try:
        session_file = SESSIONS_DIR / f"{session_id}.json"
        if not session_file.exists():
            return jsonify({"success": False, "error": "Session not found"}), 404

        # Generate share token
        token = create_share_link(session_id)

        # Return full URL
        share_url = request.host_url.rstrip('/') + f'/share/{token}'

        return jsonify({"success": True, "share_url": share_url, "token": token})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/share/<token>')
def view_shared_conversation(token):
    """View a shared conversation (read-only)."""
    try:
        # Get session ID from token
        session_id = get_session_from_token(token)
        if not session_id:
            return render_template('error.html',
                                 message="Invalid or expired share link"), 404

        session_file = SESSIONS_DIR / f"{session_id}.json"
        if not session_file.exists():
            return render_template('error.html',
                                 message="Conversation not found"), 404

        # Load conversation data
        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Render read-only view
        return render_template('shared.html',
                             conversation=data,
                             token=token)
    except Exception as e:
        return render_template('error.html',
                             message=f"Error loading shared conversation: {str(e)}"), 500


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
