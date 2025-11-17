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
const debugModeCheckbox = document.getElementById('debug-mode');
const exportBtn = document.getElementById('export-btn');
const shareBtn = document.getElementById('share-btn');
const archiveBtn = document.getElementById('archive-btn');
const deleteBtn = document.getElementById('delete-btn');

// DOM Elements - Modal
const modal = document.getElementById('modal');
const modalTitle = document.getElementById('modal-title');
const modalMessage = document.getElementById('modal-message');
const modalCancel = document.getElementById('modal-cancel');
const modalConfirm = document.getElementById('modal-confirm');

// DOM Elements - Share Modal
const shareModal = document.getElementById('share-modal');
const shareLink = document.getElementById('share-link');
const copyShareBtn = document.getElementById('copy-share-btn');
const copyFeedback = document.getElementById('copy-feedback');
const shareCloseBtn = document.getElementById('share-close-btn');

// DOM Elements - Essay Navigator
const essaySidebar = document.getElementById('essay-sidebar');
const essayToggleBtn = document.getElementById('essay-toggle-btn');
const essaySidebarClose = document.getElementById('essay-sidebar-close');
const essaySearchInput = document.getElementById('essay-search-input');
const essayList = document.getElementById('essay-list');
const essayListStatus = document.getElementById('essay-list-status');
const selectedEssaysContainer = document.getElementById('selected-essays-container');
const selectedEssaysCount = document.getElementById('selected-essays-count');
const selectedEssaysChips = document.getElementById('selected-essays-chips');
const clearSelectionBtn = document.getElementById('clear-selection-btn');
const selectedEssaysBadge = document.getElementById('selected-essays-badge');
const badgeText = document.getElementById('badge-text');
const badgeClearBtn = document.getElementById('badge-clear-btn');

// State
let isProcessing = false;
let currentSessionId = null;
let allConversations = [];
let modalCallback = null;
let isDebugMode = false;

// Essay State
let allEssays = [];
let selectedEssayIds = new Set();
let essaySearchTimeout = null;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Extract session ID from URL or template
    const appContainer = document.querySelector('.app-container');
    const templateSessionId = appContainer?.dataset.sessionId;
    const urlMatch = window.location.pathname.match(/^\/c\/([a-f0-9-]+)$/);
    const urlSessionId = urlMatch ? urlMatch[1] : null;

    const sessionId = templateSessionId || urlSessionId;

    if (sessionId) {
        currentSessionId = sessionId;
        conversationTitle.dataset.sessionId = sessionId;
    }

    // Load debug mode preference from localStorage
    isDebugMode = localStorage.getItem('debugMode') === 'true';
    debugModeCheckbox.checked = isDebugMode;

    // Load selected essays from localStorage
    const savedEssays = localStorage.getItem('selectedEssays');
    if (savedEssays) {
        try {
            selectedEssayIds = new Set(JSON.parse(savedEssays));
        } catch (e) {
            console.error('Failed to load selected essays:', e);
        }
    }

    loadConversations();
    loadHistory();
    setupEventListeners();
    loadEssays(); // Load essays on startup
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

    // Debug mode toggle
    debugModeCheckbox.addEventListener('change', toggleDebugMode);

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

    // Share conversation
    shareBtn.addEventListener('click', openShareModal);

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

    // Share Modal
    copyShareBtn.addEventListener('click', copyShareLink);
    shareCloseBtn.addEventListener('click', hideShareModal);

    // Click outside share modal to close
    shareModal.addEventListener('click', (e) => {
        if (e.target === shareModal) {
            hideShareModal();
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

    // Handle browser back/forward buttons
    window.addEventListener('popstate', (e) => {
        if (e.state && e.state.sessionId) {
            const urlMatch = window.location.pathname.match(/^\/c\/([a-f0-9-]+)$/);
            if (urlMatch) {
                switchConversation(urlMatch[1]);
            }
        }
    });

    // Essay Navigator
    essayToggleBtn.addEventListener('click', toggleEssaySidebar);
    essaySidebarClose.addEventListener('click', toggleEssaySidebar);

    // Essay search with debounce
    essaySearchInput.addEventListener('input', (e) => {
        clearTimeout(essaySearchTimeout);
        const query = e.target.value.trim();

        if (query) {
            essaySearchTimeout = setTimeout(() => searchEssays(query), 300);
        } else {
            essaySearchTimeout = setTimeout(() => renderEssayList(allEssays), 300);
        }
    });

    // Clear essay selection
    clearSelectionBtn.addEventListener('click', clearEssaySelection);
    badgeClearBtn.addEventListener('click', clearEssaySelection);

    // Click outside essay sidebar to close (mobile)
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 && essaySidebar.classList.contains('active')) {
            if (!essaySidebar.contains(e.target) && !essayToggleBtn.contains(e.target)) {
                essaySidebar.classList.remove('active');
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
        // Build context if essays are selected
        let context = null;
        if (selectedEssayIds.size > 0) {
            // Fetch full content for selected essays
            const essayPromises = Array.from(selectedEssayIds).map(id =>
                fetch(`/api/essays/${id}`).then(r => r.json())
            );

            const essayResponses = await Promise.all(essayPromises);
            const essays = essayResponses
                .filter(r => r.success)
                .map(r => ({
                    title: r.essay.title,
                    file: r.essay.file,
                    content: r.essay.content
                }));

            if (essays.length > 0) {
                context = { essays };
            }
        }

        // Send to backend
        const requestBody = {
            message: message,
            model: modelSelect.value
        };

        if (context) {
            requestBody.context = context;
        }

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (data.success) {
            // Add assistant response with debug info
            addMessage('assistant', data.response, true, data.debug_info);
            // Reload conversations to update title/metadata
            await loadConversations();

            // Clear essay selection after successful send with context
            if (selectedEssayIds.size > 0) {
                clearEssaySelection();
            }
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
function addMessage(role, content, streaming = true, debug_info = null) {
    // Add debug panel BEFORE the message for assistant messages
    if (role === 'assistant' && debug_info) {
        const debugPanel = createDebugPanel(debug_info);
        chatContainer.appendChild(debugPanel);
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'You' : 'AI';

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(messageContent);
    chatContainer.appendChild(messageDiv);

    // For user messages or when loading history, show immediately
    if (role === 'user' || !streaming) {
        messageContent.textContent = content;
        chatContainer.scrollTop = chatContainer.scrollHeight;
    } else {
        // For assistant messages, add typing animation
        typeMessage(messageContent, content);
    }
}

// Typing animation for streaming effect
function typeMessage(element, text) {
    let index = 0;
    element.textContent = '';

    // Add typing cursor
    const cursor = document.createElement('span');
    cursor.className = 'typing-cursor';
    cursor.textContent = '▌';
    element.appendChild(cursor);

    function typeNextChar() {
        if (index < text.length) {
            // Remove cursor temporarily
            cursor.remove();

            // Add next character(s) - we'll add 1-3 chars at a time for more natural feel
            const charsToAdd = Math.random() > 0.7 ? Math.min(3, text.length - index) :
                               Math.random() > 0.5 ? Math.min(2, text.length - index) : 1;

            const currentText = element.textContent;
            element.textContent = currentText + text.substr(index, charsToAdd);
            index += charsToAdd;

            // Re-add cursor
            element.appendChild(cursor);

            // Scroll to bottom
            chatContainer.scrollTop = chatContainer.scrollHeight;

            // Variable speed for more natural feel (15-35ms per batch)
            const delay = Math.random() * 20 + 15;
            setTimeout(typeNextChar, delay);
        } else {
            // Remove cursor when done
            cursor.remove();
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }

    typeNextChar();
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

            // Add messages without streaming (instant for history)
            data.messages.forEach(msg => {
                addMessage(msg.role, msg.content, false, msg.debug_info);
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
                    <h2>Welcome</h2>
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
                    <button class="btn-conversation-action" onclick="exportConversationById('${conv.session_id}')" title="Export">Export</button>
                    <button class="btn-conversation-action" onclick="deleteConversationById('${conv.session_id}')" title="Delete">Delete</button>
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
                    addMessage(msg.role, msg.content, false, msg.debug_info);
                });
            } else {
                chatContainer.innerHTML = `
                    <div class="welcome-message">
                        <h2>Welcome</h2>
                        <p>Start a conversation with Claude Code. Ask me anything!</p>
                    </div>
                `;
            }

            // Update title
            conversationTitle.textContent = data.metadata.title || 'Claude Code Chatbot';
            conversationTitle.dataset.sessionId = sessionId;
            conversationTitle.dataset.archived = data.metadata.archived || false;

            // Update archive button
            archiveBtn.textContent = data.metadata.archived ? 'Unarchive' : 'Archive';
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

            // Update URL without page reload
            const newUrl = `/c/${sessionId}`;
            if (window.location.pathname !== newUrl) {
                window.history.pushState(
                    { sessionId: sessionId },
                    data.metadata.title || 'Claude Code Chatbot',
                    newUrl
                );
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
        // Generate new UUID
        const newSessionId = generateUUID();

        // Redirect to new conversation URL (page will reload)
        window.location.href = `/c/${newSessionId}`;
    } catch (error) {
        console.error('Error creating new conversation:', error);
        alert('Failed to create new conversation. Please try again.');
    }
}

// Generate UUID helper function
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
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
            archiveBtn.textContent = !isArchived ? 'Unarchive' : 'Archive';
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

// Share Conversation Functions
async function openShareModal() {
    const sessionId = conversationTitle.dataset.sessionId;
    if (!sessionId) {
        alert('No active conversation to share.');
        return;
    }

    try {
        // Use current URL as the share link
        const shareUrl = `${window.location.origin}/c/${sessionId}`;

        // Populate share link input
        shareLink.value = shareUrl;

        // Show modal
        shareModal.style.display = 'flex';

        // Auto-select the link for easy copying
        shareLink.select();
    } catch (error) {
        console.error('Error opening share modal:', error);
        alert('Failed to open share modal. Please try again.');
    }
}

function hideShareModal() {
    shareModal.style.display = 'none';
    copyFeedback.classList.remove('show');
}

async function copyShareLink() {
    try {
        // Copy to clipboard
        await navigator.clipboard.writeText(shareLink.value);

        // Show feedback
        copyFeedback.classList.add('show');

        // Hide feedback after 2 seconds
        setTimeout(() => {
            copyFeedback.classList.remove('show');
        }, 2000);
    } catch (error) {
        console.error('Error copying to clipboard:', error);

        // Fallback: Select the text for manual copy
        shareLink.select();
        alert('Please copy the link manually (Ctrl+C or Cmd+C)');
    }
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

// Debug Panel Functions
function createDebugPanel(debug_info) {
    const panel = document.createElement('div');
    // Always show panel when debug mode is enabled, otherwise hide
    panel.className = isDebugMode ? 'debug-panel' : 'debug-panel hidden';

    // Header
    const header = document.createElement('div');
    header.className = 'debug-panel-header';

    const headerLeft = document.createElement('div');
    headerLeft.className = 'debug-panel-header-left';

    const title = document.createElement('div');
    title.className = 'debug-panel-title';
    title.textContent = '🔧 DEBUG INFO';

    const preview = document.createElement('div');
    preview.className = 'debug-panel-preview';

    // Build preview based on new structure
    const model = debug_info.session_management?.model || 'unknown';
    const msgLength = debug_info.message_flow?.message_length || 0;
    const contextInjected = debug_info.message_flow?.context_injected || false;
    preview.textContent = `${model} · ${msgLength} chars${contextInjected ? ' · 📄 Context Injected' : ''}`;

    headerLeft.appendChild(title);
    headerLeft.appendChild(preview);

    header.appendChild(headerLeft);

    // Content
    const content = document.createElement('div');
    content.className = 'debug-panel-content';

    // Session Management Section
    if (debug_info.session_management) {
        const sessionSection = createDebugSection('Session Management', [
            { label: 'Claude Code Session', value: debug_info.session_management.claude_session_id || 'N/A' },
            { label: 'Our Session', value: debug_info.session_management.our_session_id || 'N/A' },
            { label: 'Model', value: debug_info.session_management.model || 'N/A' },
            { label: 'First Message', value: debug_info.session_management.is_first_message ? 'Yes' : 'No' }
        ]);
        content.appendChild(sessionSection);
    }

    // Message Flow Section
    if (debug_info.message_flow) {
        const items = [
            { label: 'User Message', value: debug_info.message_flow.user_message_original || 'N/A' },
            { label: 'Message Length', value: `${debug_info.message_flow.message_length || 0} characters` },
            { label: 'Context Injected', value: debug_info.message_flow.context_injected ? 'Yes ✅' : 'No' }
        ];

        // Add context details if injected
        if (debug_info.message_flow.context_injected && debug_info.message_flow.injected_context) {
            const ctx = debug_info.message_flow.injected_context;
            if (ctx.essays && ctx.essays.length > 0) {
                const essayTitles = ctx.essays.map(e => e.title || e.file || 'Unknown').join(', ');
                items.push({ label: '📄 Essays Included', value: essayTitles });
                items.push({ label: 'Essay Count', value: ctx.essays.length.toString() });
            }
        }

        const messageSection = createDebugSection('Message Flow', items);
        content.appendChild(messageSection);
    }

    // Performance Section
    if (debug_info.performance) {
        const perfItems = [];
        if (debug_info.performance.token_cost) {
            perfItems.push({ label: 'Token Cost', value: debug_info.performance.token_cost });
        }
        if (debug_info.performance.duration_ms) {
            perfItems.push({ label: 'Duration', value: `${debug_info.performance.duration_ms}ms` });
        }
        if (debug_info.performance.turn_count !== undefined) {
            perfItems.push({ label: 'Turn Count', value: debug_info.performance.turn_count.toString() });
        }
        if (debug_info.performance.response_length) {
            perfItems.push({ label: 'Response Length', value: `${debug_info.performance.response_length} chars` });
        }

        if (perfItems.length > 0) {
            const perfSection = createDebugSection('Performance', perfItems);
            content.appendChild(perfSection);
        }
    }

    // Context Information
    if (debug_info.metadata) {
        const contextInfo = document.createElement('div');
        contextInfo.className = 'debug-context-info';
        contextInfo.innerHTML = `
            <div class="debug-context-note">
                <strong>ℹ️ Conversation Context:</strong> ${escapeHtml(debug_info.metadata.conversation_context || 'Managed by Claude Code via --resume')}
            </div>
        `;
        content.appendChild(contextInfo);
    }

    // Full Message Sent Section (collapsible)
    if (debug_info.message_flow?.message_sent_to_claude) {
        const messageSection = document.createElement('div');
        messageSection.className = 'debug-prompt';

        const messageHeader = document.createElement('div');
        messageHeader.className = 'debug-prompt-header';

        const messageLabel = document.createElement('div');
        messageLabel.className = 'debug-prompt-label';
        messageLabel.textContent = 'Full Message Sent to Claude';

        const copyBtn = document.createElement('button');
        copyBtn.className = 'debug-copy-btn';
        copyBtn.textContent = 'Copy';
        copyBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            copyPromptToClipboard(debug_info.message_flow.message_sent_to_claude, copyBtn);
        });

        messageHeader.appendChild(messageLabel);
        messageHeader.appendChild(copyBtn);

        const messageContent = document.createElement('div');
        messageContent.className = 'debug-prompt-content';
        messageContent.innerHTML = highlightPrompt(debug_info.message_flow.message_sent_to_claude);

        messageSection.appendChild(messageHeader);
        messageSection.appendChild(messageContent);

        content.appendChild(messageSection);
    }

    panel.appendChild(header);
    panel.appendChild(content);

    return panel;
}

function createDebugSection(title, items) {
    const section = document.createElement('div');
    section.className = 'debug-section';

    const sectionTitle = document.createElement('div');
    sectionTitle.className = 'debug-section-title';
    sectionTitle.textContent = title;
    section.appendChild(sectionTitle);

    const metadata = document.createElement('div');
    metadata.className = 'debug-metadata';

    items.forEach(item => {
        const metadataItem = document.createElement('div');
        metadataItem.className = 'debug-metadata-item';
        metadataItem.innerHTML = `
            <strong>${escapeHtml(item.label)}:</strong>
            <span class="value">${escapeHtml(item.value)}</span>
        `;
        metadata.appendChild(metadataItem);
    });

    section.appendChild(metadata);
    return section;
}

async function copyPromptToClipboard(text, button) {
    try {
        await navigator.clipboard.writeText(text);

        // Update button state
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.classList.add('copied');

        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('copied');
        }, 2000);
    } catch (error) {
        console.error('Error copying to clipboard:', error);
        button.textContent = 'Failed';
        setTimeout(() => {
            button.textContent = 'Copy';
        }, 2000);
    }
}

function highlightPrompt(promptText) {
    // Escape HTML first
    const lines = promptText.split('\n');
    const highlightedLines = lines.map(line => {
        // Highlight "User:" and "Assistant:" labels
        if (line.match(/^(User|Assistant):/)) {
            return line.replace(/^(User|Assistant):/, '<span class="prompt-role">$1:</span>');
        }
        // Highlight system prompt (first few lines before "Conversation history:")
        else if (line.includes('You are a helpful AI assistant') ||
                 line.includes('Respond to the user\'s message')) {
            return `<span class="prompt-system">${escapeHtml(line)}</span>`;
        }
        // Regular content
        else {
            return escapeHtml(line);
        }
    });

    return highlightedLines.join('\n');
}

function toggleDebugMode() {
    isDebugMode = debugModeCheckbox.checked;
    localStorage.setItem('debugMode', isDebugMode.toString());

    // Show or hide all debug panels
    const debugPanels = document.querySelectorAll('.debug-panel');
    debugPanels.forEach(panel => {
        if (isDebugMode) {
            panel.classList.remove('hidden');
        } else {
            panel.classList.add('hidden');
        }
    });
}

// Essay Navigator Functions
async function loadEssays() {
    try {
        essayListStatus.textContent = 'Loading essays...';
        const response = await fetch('/api/essays');
        const data = await response.json();

        if (data.success) {
            allEssays = data.essays;
            essayListStatus.textContent = `${data.count} essays available`;
            renderEssayList(allEssays);
            updateSelectedEssaysUI();
        } else {
            essayListStatus.textContent = 'Failed to load essays';
            console.error('Failed to load essays:', data.error);
        }
    } catch (error) {
        essayListStatus.textContent = 'Error loading essays';
        console.error('Error loading essays:', error);
    }
}

async function searchEssays(query) {
    try {
        essayListStatus.textContent = `Searching for "${query}"...`;
        const response = await fetch(`/api/essays/search?q=${encodeURIComponent(query)}&limit=50`);
        const data = await response.json();

        if (data.success) {
            essayListStatus.textContent = `${data.results.length} results for "${query}"`;
            renderEssayList(data.results);
        } else {
            essayListStatus.textContent = 'Search failed';
            console.error('Search failed:', data.error);
        }
    } catch (error) {
        essayListStatus.textContent = 'Search error';
        console.error('Error searching essays:', error);
    }
}

function renderEssayList(essays) {
    essayList.innerHTML = '';

    if (essays.length === 0) {
        essayList.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">No essays found</div>';
        return;
    }

    essays.forEach(essay => {
        const item = document.createElement('div');
        item.className = 'essay-item';
        if (selectedEssayIds.has(essay.id)) {
            item.classList.add('selected');
        }

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'essay-checkbox';
        checkbox.checked = selectedEssayIds.has(essay.id);
        checkbox.addEventListener('change', (e) => {
            e.stopPropagation();
            toggleEssaySelection(essay.id);
        });

        const content = document.createElement('div');
        content.className = 'essay-item-content';

        const title = document.createElement('div');
        title.className = 'essay-item-title';
        title.textContent = essay.title;

        const meta = document.createElement('div');
        meta.className = 'essay-item-meta';

        if (essay.date) {
            const date = document.createElement('span');
            date.textContent = essay.date;
            meta.appendChild(date);
        }

        if (essay.word_count) {
            const words = document.createElement('span');
            words.textContent = `${essay.word_count.toLocaleString()} words`;
            meta.appendChild(words);
        }

        content.appendChild(title);
        content.appendChild(meta);

        // Add topics if available
        if (essay.topics && essay.topics.length > 0) {
            const topics = document.createElement('div');
            topics.className = 'essay-item-topics';

            essay.topics.slice(0, 3).forEach(topic => {
                const tag = document.createElement('span');
                tag.className = 'topic-tag';
                tag.textContent = topic;
                topics.appendChild(tag);
            });

            content.appendChild(topics);
        }

        item.appendChild(checkbox);
        item.appendChild(content);

        // Click on item to toggle selection
        item.addEventListener('click', (e) => {
            if (e.target !== checkbox) {
                toggleEssaySelection(essay.id);
            }
        });

        essayList.appendChild(item);
    });
}

function toggleEssaySelection(essayId) {
    if (selectedEssayIds.has(essayId)) {
        selectedEssayIds.delete(essayId);
    } else {
        selectedEssayIds.add(essayId);
    }

    // Save to localStorage
    localStorage.setItem('selectedEssays', JSON.stringify(Array.from(selectedEssayIds)));

    // Update UI
    updateSelectedEssaysUI();

    // Update essay list to reflect selection
    const query = essaySearchInput.value.trim();
    if (query) {
        // Re-render search results if searching
        const currentEssays = Array.from(essayList.children).map(item => {
            const id = item.querySelector('.essay-checkbox')?.id || '';
            return allEssays.find(e => e.id === id);
        }).filter(Boolean);
        renderEssayList(currentEssays);
    } else {
        renderEssayList(allEssays);
    }
}

function updateSelectedEssaysUI() {
    const count = selectedEssayIds.size;

    // Update badge above input
    if (count > 0) {
        selectedEssaysBadge.style.display = 'flex';
        badgeText.textContent = `${count} essay${count > 1 ? 's' : ''} selected`;
    } else {
        selectedEssaysBadge.style.display = 'none';
    }

    // Update selected essays container in sidebar
    if (count > 0) {
        selectedEssaysContainer.style.display = 'block';
        selectedEssaysCount.textContent = `${count} selected`;

        // Render chips
        selectedEssaysChips.innerHTML = '';
        const selectedEssays = allEssays.filter(e => selectedEssayIds.has(e.id));

        selectedEssays.forEach(essay => {
            const chip = document.createElement('div');
            chip.className = 'selected-essay-chip';

            const title = document.createElement('span');
            title.className = 'essay-title-short';
            title.textContent = essay.title;
            title.title = essay.title; // Full title on hover

            const removeBtn = document.createElement('button');
            removeBtn.className = 'btn-remove-essay';
            removeBtn.textContent = '×';
            removeBtn.title = 'Remove essay';
            removeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleEssaySelection(essay.id);
            });

            chip.appendChild(title);
            chip.appendChild(removeBtn);
            selectedEssaysChips.appendChild(chip);
        });
    } else {
        selectedEssaysContainer.style.display = 'none';
    }
}

function clearEssaySelection() {
    selectedEssayIds.clear();
    localStorage.removeItem('selectedEssays');
    updateSelectedEssaysUI();

    // Re-render essay list to update checkboxes
    const query = essaySearchInput.value.trim();
    if (query) {
        searchEssays(query);
    } else {
        renderEssayList(allEssays);
    }
}

function toggleEssaySidebar() {
    essaySidebar.classList.toggle('active');
}

// Handle errors
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
});
