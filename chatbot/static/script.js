// Chat Application JavaScript

// DOM Elements - Main
const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const clearBtn = document.getElementById('clear-btn');
const modelSelect = document.getElementById('model');
const loading = document.getElementById('loading');

// DOM Elements - Sidebar
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');
const conversationsList = document.getElementById('conversations-list');
const newChatBtn = document.getElementById('new-chat-btn');
const searchInput = document.getElementById('search-conversations');
const showArchivedCheckbox = document.getElementById('show-archived');

// DOM Elements - Header
const conversationTitle = document.getElementById('conversation-title');
const editTitleBtn = document.getElementById('edit-title-btn');
const exportBtn = document.getElementById('export-btn');
const archiveBtn = document.getElementById('archive-btn');
const deleteBtn = document.getElementById('delete-btn');

// DOM Elements - Modal
const modal = document.getElementById('modal');
const modalTitle = document.getElementById('modal-title');
const modalMessage = document.getElementById('modal-message');
const modalCancel = document.getElementById('modal-cancel');
const modalConfirm = document.getElementById('modal-confirm');

// State
let isProcessing = false;
let currentSessionId = null;
let allConversations = [];
let modalCallback = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadConversations();
    loadHistory();
    setupEventListeners();
    userInput.focus();
});

// Event Listeners
function setupEventListeners() {
    // Send message
    sendBtn.addEventListener('click', sendMessage);
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

    // Clear chat
    clearBtn.addEventListener('click', () => {
        showModal('Clear Chat', 'Are you sure you want to clear the chat history?', clearChat);
    });

    // Sidebar toggle (mobile)
    sidebarToggle.addEventListener('click', toggleSidebar);

    // New chat
    newChatBtn.addEventListener('click', createNewConversation);

    // Search conversations
    searchInput.addEventListener('input', filterConversations);

    // Show archived toggle
    showArchivedCheckbox.addEventListener('change', filterConversations);

    // Edit title
    editTitleBtn.addEventListener('click', enableTitleEdit);
    conversationTitle.addEventListener('blur', saveTitleEdit);
    conversationTitle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            conversationTitle.blur();
        }
        if (e.key === 'Escape') {
            e.preventDefault();
            conversationTitle.textContent = conversationTitle.dataset.originalTitle || 'Claude Code Chatbot';
            conversationTitle.setAttribute('contenteditable', 'false');
        }
    });

    // Export conversation
    exportBtn.addEventListener('click', exportConversation);

    // Archive conversation
    archiveBtn.addEventListener('click', toggleArchiveConversation);

    // Delete conversation
    deleteBtn.addEventListener('click', () => {
        showModal('Delete Conversation', 'Are you sure you want to delete this conversation? This cannot be undone.', deleteConversation);
    });

    // Modal
    modalCancel.addEventListener('click', hideModal);
    modalConfirm.addEventListener('click', () => {
        if (modalCallback) {
            modalCallback();
        }
        hideModal();
    });

    // Click outside modal to close
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            hideModal();
        }
    });

    // Click outside sidebar to close (mobile)
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 && sidebar.classList.contains('active')) {
            if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                sidebar.classList.remove('active');
            }
        }
    });
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
            // Reload conversations to update title/metadata
            await loadConversations();
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
            await loadConversations();
            userInput.focus();
        }
    } catch (error) {
        console.error('Error clearing chat:', error);
        alert('Failed to clear chat. Please try again.');
    }
}

// Load Conversations List
async function loadConversations() {
    try {
        const response = await fetch('/api/conversations');
        const data = await response.json();

        if (data.success) {
            allConversations = data.conversations;
            renderConversations();
        }
    } catch (error) {
        console.error('Error loading conversations:', error);
    }
}

// Render Conversations List
function renderConversations() {
    const searchQuery = searchInput.value.toLowerCase();
    const showArchived = showArchivedCheckbox.checked;

    // Filter conversations
    const filtered = allConversations.filter(conv => {
        if (!showArchived && conv.archived) return false;
        if (searchQuery) {
            return conv.title?.toLowerCase().includes(searchQuery) ||
                   conv.preview?.toLowerCase().includes(searchQuery);
        }
        return true;
    });

    // Clear list
    conversationsList.innerHTML = '';

    if (filtered.length === 0) {
        conversationsList.innerHTML = '<div class="empty-state"><p>No conversations found</p></div>';
        return;
    }

    // Render each conversation
    filtered.forEach(conv => {
        const item = document.createElement('div');
        item.className = 'conversation-item';
        if (conv.archived) {
            item.classList.add('archived');
        }

        // Check if this is the current session (use session_id from Flask session)
        // We'll mark it active when clicked or on initial load

        const title = conv.title || 'New Conversation';
        const messageCount = conv.message_count || 0;
        const updatedAt = formatTimestamp(conv.updated_at);
        const preview = conv.preview || '';

        item.innerHTML = `
            <div class="conversation-item-header">
                <div class="conversation-item-title">${escapeHtml(title)}</div>
                <div class="conversation-item-actions">
                    <button class="btn-conversation-action" onclick="exportConversationById('${conv.session_id}')" title="Export">💾</button>
                    <button class="btn-conversation-action" onclick="deleteConversationById('${conv.session_id}')" title="Delete">🗑️</button>
                </div>
            </div>
            <div class="conversation-item-meta">
                <span>${messageCount} messages</span>
                <span>${updatedAt}</span>
            </div>
            ${preview ? `<div class="conversation-item-preview">${escapeHtml(preview)}</div>` : ''}
        `;

        item.addEventListener('click', (e) => {
            // Don't switch if clicking action buttons
            if (e.target.closest('.btn-conversation-action')) {
                return;
            }
            switchConversation(conv.session_id);
        });

        conversationsList.appendChild(item);
    });
}

// Filter Conversations
function filterConversations() {
    renderConversations();
}

// Switch Conversation
async function switchConversation(sessionId) {
    try {
        const response = await fetch(`/api/conversations/${sessionId}/switch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model: modelSelect.value
            })
        });

        const data = await response.json();

        if (data.success) {
            currentSessionId = sessionId;

            // Clear and reload chat
            chatContainer.innerHTML = '';
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    addMessage(msg.role, msg.content);
                });
            } else {
                chatContainer.innerHTML = `
                    <div class="welcome-message">
                        <h2>Welcome! 👋</h2>
                        <p>Start a conversation with Claude Code. Ask me anything!</p>
                    </div>
                `;
            }

            // Update title
            conversationTitle.textContent = data.metadata.title || 'Claude Code Chatbot';
            conversationTitle.dataset.sessionId = sessionId;
            conversationTitle.dataset.archived = data.metadata.archived || false;

            // Update archive button
            archiveBtn.textContent = data.metadata.archived ? '📂' : '📦';
            archiveBtn.title = data.metadata.archived ? 'Unarchive conversation' : 'Archive conversation';

            // Reload conversations to update active state
            await loadConversations();

            // Highlight active conversation
            document.querySelectorAll('.conversation-item').forEach(item => {
                item.classList.remove('active');
            });
            const activeItem = Array.from(document.querySelectorAll('.conversation-item'))
                .find(item => item.querySelector('.conversation-item-title').textContent === (data.metadata.title || 'New Conversation'));
            if (activeItem) {
                activeItem.classList.add('active');
            }

            // Close sidebar on mobile
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('active');
            }

            userInput.focus();
        }
    } catch (error) {
        console.error('Error switching conversation:', error);
        alert('Failed to switch conversation. Please try again.');
    }
}

// Create New Conversation
async function createNewConversation() {
    try {
        const response = await fetch('/api/conversations/new', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model: modelSelect.value
            })
        });

        const data = await response.json();

        if (data.success) {
            currentSessionId = data.session_id;

            // Clear chat
            chatContainer.innerHTML = `
                <div class="welcome-message">
                    <h2>Welcome! 👋</h2>
                    <p>Start a conversation with Claude Code. Ask me anything!</p>
                </div>
            `;

            // Update title
            conversationTitle.textContent = 'New Conversation';
            conversationTitle.dataset.sessionId = data.session_id;
            conversationTitle.dataset.archived = false;

            // Update archive button
            archiveBtn.textContent = '📦';
            archiveBtn.title = 'Archive conversation';

            // Reload conversations
            await loadConversations();

            // Close sidebar on mobile
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('active');
            }

            userInput.focus();
        }
    } catch (error) {
        console.error('Error creating new conversation:', error);
        alert('Failed to create new conversation. Please try again.');
    }
}

// Enable Title Edit
function enableTitleEdit() {
    conversationTitle.dataset.originalTitle = conversationTitle.textContent;
    conversationTitle.setAttribute('contenteditable', 'true');
    conversationTitle.focus();

    // Select all text
    const range = document.createRange();
    range.selectNodeContents(conversationTitle);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
}

// Save Title Edit
async function saveTitleEdit() {
    conversationTitle.setAttribute('contenteditable', 'false');
    const newTitle = conversationTitle.textContent.trim();
    const sessionId = conversationTitle.dataset.sessionId;

    if (!newTitle || !sessionId) {
        conversationTitle.textContent = conversationTitle.dataset.originalTitle || 'Claude Code Chatbot';
        return;
    }

    try {
        const response = await fetch(`/api/conversations/${sessionId}/title`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title: newTitle,
                model: modelSelect.value
            })
        });

        const data = await response.json();

        if (data.success) {
            conversationTitle.textContent = newTitle;
            await loadConversations();
        } else {
            conversationTitle.textContent = conversationTitle.dataset.originalTitle || 'Claude Code Chatbot';
            alert('Failed to update title. Please try again.');
        }
    } catch (error) {
        console.error('Error updating title:', error);
        conversationTitle.textContent = conversationTitle.dataset.originalTitle || 'Claude Code Chatbot';
        alert('Failed to update title. Please try again.');
    }
}

// Export Conversation
async function exportConversation() {
    const sessionId = conversationTitle.dataset.sessionId;
    if (!sessionId) {
        alert('No active conversation to export.');
        return;
    }
    exportConversationById(sessionId);
}

// Export Conversation by ID
async function exportConversationById(sessionId) {
    try {
        window.location.href = `/api/conversations/${sessionId}/export`;
    } catch (error) {
        console.error('Error exporting conversation:', error);
        alert('Failed to export conversation. Please try again.');
    }
}

// Toggle Archive Conversation
async function toggleArchiveConversation() {
    const sessionId = conversationTitle.dataset.sessionId;
    if (!sessionId) {
        alert('No active conversation to archive.');
        return;
    }

    const isArchived = conversationTitle.dataset.archived === 'true';

    try {
        const response = await fetch(`/api/conversations/${sessionId}/archive`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                archived: !isArchived,
                model: modelSelect.value
            })
        });

        const data = await response.json();

        if (data.success) {
            conversationTitle.dataset.archived = !isArchived;
            archiveBtn.textContent = !isArchived ? '📂' : '📦';
            archiveBtn.title = !isArchived ? 'Unarchive conversation' : 'Archive conversation';
            await loadConversations();
        } else {
            alert('Failed to update archive status. Please try again.');
        }
    } catch (error) {
        console.error('Error updating archive status:', error);
        alert('Failed to update archive status. Please try again.');
    }
}

// Delete Conversation
async function deleteConversation() {
    const sessionId = conversationTitle.dataset.sessionId;
    if (!sessionId) {
        alert('No active conversation to delete.');
        return;
    }

    try {
        const response = await fetch(`/api/conversations/${sessionId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            // Create new conversation or load first available
            await createNewConversation();
        } else {
            alert('Failed to delete conversation. Please try again.');
        }
    } catch (error) {
        console.error('Error deleting conversation:', error);
        alert('Failed to delete conversation. Please try again.');
    }
}

// Delete Conversation by ID
async function deleteConversationById(sessionId) {
    showModal('Delete Conversation', 'Are you sure you want to delete this conversation? This cannot be undone.', async () => {
        try {
            const response = await fetch(`/api/conversations/${sessionId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.success) {
                // If deleting current conversation, create new one
                if (sessionId === conversationTitle.dataset.sessionId) {
                    await createNewConversation();
                } else {
                    await loadConversations();
                }
            } else {
                alert('Failed to delete conversation. Please try again.');
            }
        } catch (error) {
            console.error('Error deleting conversation:', error);
            alert('Failed to delete conversation. Please try again.');
        }
    });
}

// Toggle Sidebar (Mobile)
function toggleSidebar() {
    sidebar.classList.toggle('active');
}

// Modal Functions
function showModal(title, message, callback) {
    modalTitle.textContent = title;
    modalMessage.textContent = message;
    modalCallback = callback;
    modal.style.display = 'flex';
}

function hideModal() {
    modal.style.display = 'none';
    modalCallback = null;
}

// Utility Functions
function formatTimestamp(timestamp) {
    if (!timestamp) return '';

    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;

    return date.toLocaleDateString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Handle errors
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
});
