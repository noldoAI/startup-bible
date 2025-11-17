# Claude Code Chatbot

An interactive chatbot with both **Web UI** and **CLI** interfaces that uses Claude Code in headless mode for conversational AI.

## Features

- **Web Interface**: Modern, responsive chat UI accessible via browser
- **CLI Interface**: Terminal-based chatbot for command-line users
- **Model Selection**: Choose between Sonnet, Opus, or Haiku models
- **Conversation History**: Persistent session storage across restarts
- **Real-time Responses**: Subprocess integration with Claude Code
- **Simple Architecture**: Pure Python backend with vanilla JavaScript frontend

## Prerequisites

- Python 3.8+
- Claude Code CLI installed and configured
- Virtual environment (recommended)

## Installation

1. **Navigate to the chatbot directory**:
   ```bash
   cd chatbot
   ```

2. **Create and activate virtual environment** (recommended):
   ```bash
   # Create venv
   python3 -m venv venv

   # Activate (Linux/Mac)
   source venv/bin/activate

   # Activate (Windows)
   # venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Web Interface

1. **Start the web server**:
   ```bash
   python app.py
   ```

   Or with custom options:
   ```bash
   python app.py --host 0.0.0.0 --port 8080 --debug
   ```

2. **Open your browser**:
   ```
   http://127.0.0.1:5000
   ```

3. **Start chatting**:
   - Type your message in the input box
   - Press Enter or click "Send"
   - Select model (Sonnet/Opus/Haiku) from the dropdown
   - Click "Clear Chat" to reset conversation

### CLI Interface

1. **Start the CLI chatbot**:
   ```bash
   python chatbot_cli.py
   ```

   Or with options:
   ```bash
   # Use a specific model
   python chatbot_cli.py --model opus

   # Resume a previous session
   python chatbot_cli.py --session-id <session-id>
   ```

2. **Available commands**:
   - `/help` - Show help message
   - `/history` - Display conversation history
   - `/clear` - Clear conversation history
   - `/quit` - Exit the chatbot

3. **Chat normally**:
   - Just type your message and press Enter
   - Use Shift+Enter for multi-line input (web only)

## Architecture

### Backend (Flask)

**app.py** - Web server with REST API:
- `/` - Serve chat interface
- `/api/chat` - POST endpoint for sending messages
- `/api/history` - GET conversation history
- `/api/clear` - POST to clear history

**ConversationManager** class:
- Manages conversation sessions
- Builds prompts with history context
- Calls Claude Code via subprocess
- Persists sessions to JSON files

### Frontend

**HTML** ([templates/index.html](templates/index.html)):
- Clean, responsive chat interface
- Model selector
- Clear chat button

**CSS** ([static/style.css](static/style.css)):
- Modern gradient design
- Message bubbles
- Responsive layout
- Smooth animations

**JavaScript** ([static/script.js](static/script.js)):
- Message sending/receiving
- DOM manipulation
- History loading
- Auto-scroll and auto-resize

### CLI

**chatbot_cli.py**:
- Interactive REPL loop
- Same backend logic as web
- Session management
- Command handling

## Session Storage

Conversations are stored in `sessions/` directory as JSON files:

```json
{
  "session_id": "uuid",
  "model": "sonnet",
  "created_at": "timestamp",
  "updated_at": "timestamp",
  "messages": [
    {
      "role": "user",
      "content": "Hello!",
      "timestamp": "timestamp"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help?",
      "timestamp": "timestamp"
    }
  ]
}
```

Sessions persist across restarts and can be resumed using the session ID.

## Configuration

### Environment Variables

You can configure the app using environment variables:

```bash
export FLASK_HOST=127.0.0.1
export FLASK_PORT=5000
export CLAUDE_MODEL=sonnet
```

### Command-Line Arguments

**Web Server** ([app.py](app.py)):
```bash
python app.py --host 127.0.0.1 --port 5000 --debug
```

**CLI** ([chatbot_cli.py](chatbot_cli.py)):
```bash
python chatbot_cli.py --model sonnet --session-id <id>
```

## How It Works

The chatbot uses Claude Code in headless mode, similar to the pattern in `paul-graham/enrich_index.py`:

```python
cmd = [
    "claude",
    "-p", prompt,                    # Prompt with conversation history
    "--output-format", "text",       # Text output for chat
    "--model", model                 # sonnet/opus/haiku
]

result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=60
)

response = result.stdout.strip()
```

**Context Management**:
1. Build prompt with system instruction
2. Include last 10 messages as conversation history
3. Add current user message
4. Call Claude Code subprocess
5. Parse and return response
6. Save both messages to session

## Development

### File Structure

```
chatbot/
├── app.py                 # Flask web server
├── chatbot_cli.py         # CLI interface
├── templates/
│   └── index.html         # Chat UI
├── static/
│   ├── style.css          # Styling
│   └── script.js          # Frontend logic
├── sessions/              # Session storage (gitignored)
│   └── *.json
├── requirements.txt       # Dependencies
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

### Adding Features

**Backend enhancements** (app.py):
- Add streaming responses with Server-Sent Events (SSE)
- Implement user authentication
- Add rate limiting
- Export conversation to PDF/TXT

**Frontend enhancements**:
- Add markdown rendering for responses
- Implement code syntax highlighting
- Add file upload capability
- Voice input/output

**CLI enhancements** (chatbot_cli.py):
- Use `prompt-toolkit` for autocomplete
- Add `rich` for better formatting
- Implement search within history
- Add conversation export

## Troubleshooting

### Claude Code not found

Make sure Claude Code CLI is installed and in your PATH:
```bash
claude --version
```

### Port already in use

Change the port:
```bash
python app.py --port 8080
```

### Session not loading

Check that `sessions/` directory exists and is writable:
```bash
ls -la sessions/
```

### Timeout errors

Increase the timeout in the code:
```python
CLAUDE_TIMEOUT = 120  # 2 minutes
```

## License

This project is part of the startup-bible repository.

## Contributing

Feel free to submit issues and enhancement requests!
