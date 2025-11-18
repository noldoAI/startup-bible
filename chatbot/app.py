#!/usr/bin/env python3
"""
Flask-based chatbot web interface that uses Claude Code in headless mode.
"""

import argparse
import json
import re
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
PAUL_GRAHAM_DIR = Path(__file__).parent.parent / "paul-graham" / "data"
ESSAYS_INDEX_FILE = PAUL_GRAHAM_DIR / "index.json"
ESSAYS_DIR = PAUL_GRAHAM_DIR / "essays"
CLAUDE_TIMEOUT = 600  # 10 minute timeout for Claude responses
DEFAULT_MODEL = "sonnet"
SYSTEM_PROMPT = "You are a helpful AI assistant. Respond to the user's message naturally and conversationally."


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


def load_essays_index() -> List[Dict]:
    """Load the Paul Graham essays index."""
    try:
        if not ESSAYS_INDEX_FILE.exists():
            return []
        with open(ESSAYS_INDEX_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # index.json has structure: {"essays": [...], "total_count": N, "last_updated": "..."}
            if isinstance(data, dict) and 'essays' in data:
                return data['essays']
            elif isinstance(data, list):
                return data
            else:
                return []
    except Exception as e:
        print(f"Error loading essays index: {e}")
        return []


def load_essay_content(essay_id: str) -> Optional[Dict]:
    """Load a specific essay's content from markdown file."""
    try:
        essay_file = ESSAYS_DIR / f"{essay_id}.md"
        if not essay_file.exists():
            return None

        with open(essay_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse frontmatter and content
        metadata = {}
        essay_content = content

        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                # Has frontmatter - parse it manually
                frontmatter = parts[1].strip()
                essay_content = parts[2].strip()

                # Simple YAML parsing for key: value pairs
                for line in frontmatter.split('\n'):
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()

                        # Try to convert to appropriate type
                        if value.lower() == 'true':
                            value = True
                        elif value.lower() == 'false':
                            value = False
                        elif value.isdigit():
                            value = int(value)

                        metadata[key] = value

        return {
            **metadata,
            'content': essay_content,
            'full_markdown': content
        }
    except Exception as e:
        print(f"Error loading essay {essay_id}: {e}")
        return None


def search_essays(query: str, limit: int = 10) -> List[Dict]:
    """
    LLM-powered semantic search for essays using Claude Code CLI.
    Uses semantic understanding to find relevant essays based on query intent.
    """
    if not query:
        return []

    essays = load_essays_index()
    if not essays:
        return []

    # Prepare essay metadata for LLM (streamlined for token efficiency)
    essay_metadata = []
    for essay in essays:
        essay_metadata.append({
            "id": essay.get("id"),
            "title": essay.get("title"),
            "summary": essay.get("summary", ""),
            "topics": essay.get("topics", []),
            "key_concepts": essay.get("key_concepts", []),
            "questions_answered": essay.get("questions_answered", []),
            "date": essay.get("date", "")
        })

    # Construct prompt for Claude
    prompt = f"""You are a semantic search engine for Paul Graham's essays.

Query: "{query}"

Your task: Analyze the query and find the top {limit} most relevant essays from the list below. Consider semantic meaning, intent, and context - not just keyword matching.

Essays metadata:
{json.dumps(essay_metadata, indent=2)}

Return ONLY a JSON array of essay IDs ranked by relevance (most relevant first), with this exact structure:
[
  {{"essay_id": "id1", "relevance_score": 9.5, "reason": "brief explanation"}},
  {{"essay_id": "id2", "relevance_score": 8.2, "reason": "brief explanation"}}
]

Return exactly {limit} results (or fewer if less than {limit} are relevant). Only include essays with relevance_score >= 5.0."""

    try:
        # Call Claude Code CLI in headless mode, using stdin to avoid "argument list too long" error
        result = subprocess.run(
            [
                "claude",
                "--output-format", "json",
                "--model", "haiku"  # Fast, cheap model for search
            ],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout for search
        )

        if result.returncode != 0:
            print(f"Claude CLI error for search: {result.stderr}")
            return _fallback_search(query, essays, limit)

        # Parse Claude's response
        try:
            response_data = json.loads(result.stdout)
            claude_response = response_data.get('result', '').strip()

            # Extract JSON array from response (Claude might wrap it in markdown)
            # Look for JSON array pattern
            json_match = re.search(r'\[[\s\S]*\]', claude_response)
            if json_match:
                ranked_results = json.loads(json_match.group(0))
            else:
                print(f"Could not parse JSON from Claude response: {claude_response}")
                return _fallback_search(query, essays, limit)

            # Map essay IDs back to full essay objects
            results = []
            essay_lookup = {e['id']: e for e in essays}

            for result_item in ranked_results:
                essay_id = result_item.get('essay_id')
                if essay_id in essay_lookup:
                    essay = essay_lookup[essay_id].copy()
                    essay['search_score'] = result_item.get('relevance_score', 0)
                    essay['search_reason'] = result_item.get('reason', '')
                    essay['matched_fields'] = ['llm_semantic']  # For compatibility
                    results.append(essay)

            return results

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Failed to parse Claude search response: {e}")
            return _fallback_search(query, essays, limit)

    except subprocess.TimeoutExpired:
        print("Claude search timed out")
        return _fallback_search(query, essays, limit)
    except Exception as e:
        print(f"Error in LLM search: {e}")
        return _fallback_search(query, essays, limit)


def _fallback_search(query: str, essays: List[Dict], limit: int) -> List[Dict]:
    """
    Fallback to simple keyword search if LLM search fails.
    This is the original hardcoded search logic.
    """
    query_lower = query.lower()
    results = []

    for essay in essays:
        score = 0
        matches = []

        # Search in title (highest weight)
        title = essay.get('title', '').lower()
        if query_lower in title:
            score += 10
            matches.append('title')

        # Search in topics
        topics = essay.get('topics', [])
        if any(query_lower in topic.lower() for topic in topics):
            score += 5
            matches.append('topics')

        # Search in key_concepts
        key_concepts = essay.get('key_concepts', [])
        if any(query_lower in concept.lower() for concept in key_concepts):
            score += 3
            matches.append('key_concepts')

        # Search in summary
        summary = essay.get('summary', '').lower()
        if query_lower in summary:
            score += 2
            matches.append('summary')

        # Search in questions_answered
        questions = essay.get('questions_answered', [])
        if any(query_lower in q.lower() for q in questions):
            score += 4
            matches.append('questions')

        if score > 0:
            results.append({
                **essay,
                'search_score': score,
                'matched_fields': matches
            })

    # Sort by score (descending)
    results.sort(key=lambda x: x['search_score'], reverse=True)

    return results[:limit]


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
                if "claude_session_id" not in data:
                    data["claude_session_id"] = None
                return data
        else:
            return {
                "session_id": self.session_id,
                "claude_session_id": None,  # Claude Code's native session ID
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

    def _build_message_with_context(self, user_message: str, injected_context: Optional[Dict] = None) -> str:
        """
        Build the actual message to send to Claude, optionally including context.

        Claude Code manages conversation history via --resume, so we don't need to
        manually include previous messages. We only augment the current message with
        additional context (essays, documents, etc.) if provided.

        Args:
            user_message: The user's question/message
            injected_context: Optional dict with keys like:
                - 'essays': list of essay dicts with 'title', 'file', 'content'
                - 'instructions': special instructions for this message
                - 'metadata': any other context metadata

        Returns:
            The message string to send to Claude (may include injected context)
        """
        if not injected_context:
            return user_message

        parts = []

        # Add essay context if provided
        if 'essays' in injected_context and injected_context['essays']:
            parts.append("=== CONTEXT FROM ESSAYS ===\n")
            for essay in injected_context['essays']:
                parts.append(f"Essay Title: {essay['title']}")
                if 'file' in essay:
                    parts.append(f"Source: {essay['file']}")
                parts.append(f"\nContent:\n{essay['content']}\n")
                parts.append("-" * 60)
            parts.append("=== END CONTEXT ===\n")

        # Add any special instructions
        if 'instructions' in injected_context and injected_context['instructions']:
            parts.append(f"{injected_context['instructions']}\n")

        # Add the actual user question
        parts.append(f"User question: {user_message}")

        return "\n".join(parts)

    def ask_claude(self, user_message: str, injected_context: Optional[Dict] = None) -> Dict:
        """
        Send message to Claude Code and get response.

        Uses Claude Code's native session management via --resume for conversation history.
        Optionally augments the message with additional context (essays, documents, etc.).

        Args:
            user_message: The user's question/message
            injected_context: Optional context to inject (essays, instructions, etc.)

        Returns:
            dict with 'success', 'response', 'debug_info', and optional 'error'
        """
        # Build the actual message to send (may include injected context)
        message_to_send = self._build_message_with_context(user_message, injected_context)

        # Check if this is the first message or a follow-up
        claude_session_id = self.conversation.get("claude_session_id")

        if not claude_session_id:
            # First message: Create new Claude Code session
            cmd = [
                "claude",
                "-p", message_to_send,
                "--output-format", "json",
                "--model", self.model,
                "--append-system-prompt", SYSTEM_PROMPT
            ]
        else:
            # Follow-up message: Resume existing Claude Code session
            cmd = [
                "claude",
                "--resume", claude_session_id,
                message_to_send,
                "--output-format", "json"
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

            # Parse JSON response from Claude Code
            try:
                response_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Failed to parse Claude response: {str(e)}",
                    "response": f"Error: Failed to parse response from Claude"
                }

            # Extract response and metadata
            # Claude Code returns 'result' field, not 'response'
            response = response_data.get('result', '').strip()

            # Store Claude Code's session ID (from first response)
            if 'session_id' in response_data:
                self.conversation["claude_session_id"] = response_data['session_id']

            # Build rich debug info
            debug_info = {
                "session_management": {
                    "claude_session_id": self.conversation.get("claude_session_id"),
                    "our_session_id": self.session_id,
                    "is_first_message": claude_session_id is None,
                    "model": self.model
                },
                "message_flow": {
                    "user_message_original": user_message,
                    "message_sent_to_claude": message_to_send,
                    "message_length": len(message_to_send),
                    "context_injected": injected_context is not None,
                    "injected_context": injected_context if injected_context else None
                },
                "performance": {
                    "token_cost": response_data.get('total_cost_usd'),
                    "duration_ms": response_data.get('duration_ms'),
                    "turn_count": response_data.get('num_turns'),
                    "response_length": len(response)
                },
                "metadata": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "system_prompt": SYSTEM_PROMPT,
                    "conversation_context": "Managed by Claude Code via --resume"
                }
            }

            # Prepare context metadata for user message
            context_metadata = None
            if injected_context and 'essays' in injected_context:
                context_metadata = {
                    "essays_included": [essay.get('file', essay.get('title', 'unknown'))
                                       for essay in injected_context['essays']],
                    "context_type": "essay_retrieval",
                    "essay_count": len(injected_context['essays'])
                }

            # Save messages to conversation history
            user_msg_data = {
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            if context_metadata:
                user_msg_data["context_metadata"] = context_metadata

            self.conversation["messages"].append(user_msg_data)
            self.conversation["messages"].append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "debug_info": debug_info
            })

            # Auto-generate title from first message if not set
            if not self.conversation.get("title") and len(self.conversation["messages"]) == 2:
                self.conversation["title"] = generate_title_from_message(user_message)

            self._save_session()

            return {
                "success": True,
                "response": response,
                "debug_info": debug_info
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

    # Optional: Context injection for RAG features
    context = data.get('context')  # Optional dict with 'essays', 'instructions', etc.

    if not user_message:
        return jsonify({"success": False, "error": "Message cannot be empty"}), 400

    # Get or create session
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id

    # Process message with optional context injection
    manager = ConversationManager(session_id, model)
    result = manager.ask_claude(user_message, injected_context=context)

    return jsonify(result)


@app.route('/api/essays', methods=['GET'])
def get_essays():
    """Get list of all Paul Graham essays."""
    try:
        essays = load_essays_index()
        return jsonify({
            "success": True,
            "essays": essays,
            "count": len(essays)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/essays/<essay_id>', methods=['GET'])
def get_essay(essay_id):
    """Get specific essay content by ID."""
    try:
        # Get metadata from index
        essays = load_essays_index()
        essay_metadata = next((e for e in essays if e.get('id') == essay_id), None)

        if not essay_metadata:
            return jsonify({"success": False, "error": "Essay not found"}), 404

        # Load full content
        essay_content = load_essay_content(essay_id)

        if not essay_content:
            return jsonify({"success": False, "error": "Essay content not found"}), 404

        # Combine metadata and content
        essay = {
            **essay_metadata,
            **essay_content
        }

        return jsonify({
            "success": True,
            "essay": essay
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/essays/search', methods=['GET'])
def search_essays_route():
    """Search essays by query string."""
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 10))

        if not query:
            return jsonify({"success": False, "error": "Query parameter 'q' is required"}), 400

        results = search_essays(query, limit=limit)

        return jsonify({
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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
