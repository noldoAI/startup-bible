// Chat Application JavaScript

// DOM Elements
const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const clearBtn = document.getElementById('clear-btn');
const modelSelect = document.getElementById('model');
const loading = document.getElementById('loading');

// State
let isProcessing = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    setupEventListeners();
    userInput.focus();
});

// Event Listeners
function setupEventListeners() {
    // Send button click
    sendBtn.addEventListener('click', sendMessage);

    // Enter key to send (Shift+Enter for new line)
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    userInput.addEventListener('input', () => {
        userInput.style.height = 'auto';
        userInput.style.height = userInput.scrollHeight + 'px';
    });

    // Clear chat button
    clearBtn.addEventListener('click', clearChat);
}

// Send Message
async function sendMessage() {
    const message = userInput.value.trim();

    if (!message || isProcessing) {
        return;
    }

    // Remove welcome message if present
    const welcomeMessage = chatContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }

    // Add user message to UI
    addMessage('user', message);

    // Clear input
    userInput.value = '';
    userInput.style.height = 'auto';

    // Disable input while processing
    setProcessing(true);

    try {
        // Send to backend
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                model: modelSelect.value
            })
        });

        const data = await response.json();

        if (data.success) {
            // Add assistant response
            addMessage('assistant', data.response);
        } else {
            // Show error
            addMessage('assistant', `Error: ${data.error || 'Unknown error occurred'}`);
        }

    } catch (error) {
        console.error('Error:', error);
        addMessage('assistant', 'Error: Failed to communicate with server. Please try again.');
    } finally {
        setProcessing(false);
        userInput.focus();
    }
}

// Add Message to UI
function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = content;

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(messageContent);

    chatContainer.appendChild(messageDiv);

    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Set Processing State
function setProcessing(processing) {
    isProcessing = processing;
    sendBtn.disabled = processing;
    userInput.disabled = processing;
    loading.style.display = processing ? 'flex' : 'none';

    if (processing) {
        sendBtn.textContent = 'Sending...';
    } else {
        sendBtn.textContent = 'Send';
    }
}

// Load Conversation History
async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();

        if (data.messages && data.messages.length > 0) {
            // Remove welcome message
            const welcomeMessage = chatContainer.querySelector('.welcome-message');
            if (welcomeMessage) {
                welcomeMessage.remove();
            }

            // Add messages
            data.messages.forEach(msg => {
                addMessage(msg.role, msg.content);
            });
        }
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

// Clear Chat
async function clearChat() {
    if (!confirm('Are you sure you want to clear the chat history?')) {
        return;
    }

    try {
        const response = await fetch('/api/clear', {
            method: 'POST'
        });

        if (response.ok) {
            // Clear UI
            chatContainer.innerHTML = `
                <div class="welcome-message">
                    <h2>Welcome! 👋</h2>
                    <p>Start a conversation with Claude Code. Ask me anything!</p>
                </div>
            `;
            userInput.focus();
        }
    } catch (error) {
        console.error('Error clearing chat:', error);
        alert('Failed to clear chat. Please try again.');
    }
}

// Handle errors
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
});
