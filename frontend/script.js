// Configuration
const API_BASE = 'http://127.0.0.1:8000';
let conversationHistory = [];
let currentAction = 'chat';
let isSidebarOpen = false;

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const newChatBtn = document.getElementById('newChatBtn');
const debugBtn = document.getElementById('debugBtn');
const explainBtn = document.getElementById('explainBtn');
const generateBtn = document.getElementById('generateBtn');
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadConversation();
    setupEventListeners();
    checkMobileView();
});

// Event Listeners
function setupEventListeners() {
    sendBtn.addEventListener('click', handleSend);
    
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });
    
    chatInput.addEventListener('input', autoResize);
    
    newChatBtn.addEventListener('click', startNewChat);
    
    // Action buttons
    debugBtn.addEventListener('click', () => {
        currentAction = 'debug';
        handleSend();
    });
    
    explainBtn.addEventListener('click', () => {
        currentAction = 'explain';
        handleSend();
    });
    
    generateBtn.addEventListener('click', () => {
        currentAction = 'generate';
        handleSend();
    });
    
    // Sidebar toggle
    sidebarToggle.addEventListener('click', toggleSidebar);
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
        if (isSidebarOpen && window.innerWidth <= 768) {
            if (!sidebar.contains(e.target) && e.target !== sidebarToggle) {
                closeSidebar();
            }
        }
    });
}

// Sidebar functions
function toggleSidebar() {
    if (window.innerWidth <= 768) {
        sidebar.classList.toggle('open');
        isSidebarOpen = !isSidebarOpen;
    }
}

function closeSidebar() {
    if (window.innerWidth <= 768) {
        sidebar.classList.remove('open');
        isSidebarOpen = false;
    }
}

function checkMobileView() {
    if (window.innerWidth <= 768) {
        sidebar.classList.add('collapsed');
        isSidebarOpen = false;
    } else {
        sidebar.classList.remove('collapsed');
        isSidebarOpen = true;
    }
}

// Auto-resize textarea
function autoResize() {
    chatInput.style.height = 'auto';
    chatInput.style.height = chatInput.scrollHeight + 'px';
}

// Handle send based on current action
async function handleSend() {
    const message = chatInput.value.trim();
    if (!message) return;
    
    addMessage('user', message);
    chatInput.value = '';
    chatInput.style.height = 'auto';
    chatInput.focus();
    
    showTypingIndicator();
    
    try {
        let response;
        
        switch (currentAction) {
            case 'debug':
                response = await handleDebugRequest(message);
                break;
                
            case 'explain':
                response = await handleExplainRequest(message);
                break;
                
            case 'generate':
                response = await handleGenerateRequest(message);
                break;
                
            default:
                response = await handleChatRequest(message);
        }
        
        removeTypingIndicator();
        addMessage('assistant', response);
        
    } catch (error) {
        removeTypingIndicator();
        addMessage('assistant', `Error: ${error.message}`);
    }
    
    currentAction = 'chat';
}

// API request handlers
async function handleChatRequest(message) {
    const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            prompt: message,
            history: conversationHistory.slice(0, -1)
        })
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data.reply;
}

async function handleDebugRequest(message) {
    const response = await fetch(`${API_BASE}/debug`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code: message })
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data.reply;
}

async function handleExplainRequest(message) {
    const response = await fetch(`${API_BASE}/explain`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code: message })
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data.reply;
}

async function handleGenerateRequest(message) {
    const response = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ spec: message })
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data.reply;
}

// Add message to chat
function addMessage(role, content) {
    conversationHistory.push({ role, content });
    saveConversation();
    renderMessages();
    scrollToBottom();
}

// Show typing indicator
function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant';
    typingDiv.id = 'typing-indicator';
    
    typingDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-robot"></i>
        </div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    
    chatMessages.appendChild(typingDiv);
    scrollToBottom();
}

// Remove typing indicator
function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Render messages
function renderMessages() {
    chatMessages.innerHTML = '';
    
    conversationHistory.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${msg.role}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = msg.role === 'user' ? 
            '<i class="fas fa-user"></i>' : 
            '<i class="fas fa-robot"></i>';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = marked.parse(msg.content);
        
        // Add copy buttons to code blocks
        content.querySelectorAll('pre code').forEach(codeBlock => {
            const pre = codeBlock.parentElement;
            const toolbar = document.createElement('div');
            toolbar.className = 'code-toolbar';
            toolbar.innerHTML = `
                <button onclick="copyCode(this)" title="Copy code">
                    <i class="fas fa-copy"></i>
                </button>
            `;
            pre.style.position = 'relative';
            pre.appendChild(toolbar);
        });
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        chatMessages.appendChild(messageDiv);
    });
    
    scrollToBottom();
}

// Copy code to clipboard
function copyCode(button) {
    const codeBlock = button.closest('pre').querySelector('code');
    navigator.clipboard.writeText(codeBlock.textContent).then(() => {
        const originalHtml = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i>';
        setTimeout(() => {
            button.innerHTML = originalHtml;
        }, 2000);
    });
}

// Scroll to bottom
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Save conversation
function saveConversation() {
    localStorage.setItem('verilogai_conversation', JSON.stringify(conversationHistory));
}

// Load conversation
function loadConversation() {
    const saved = localStorage.getItem('verilogai_conversation');
    if (saved) {
        try {
            conversationHistory = JSON.parse(saved);
            renderMessages();
        } catch (error) {
            console.error('Error loading conversation:', error);
        }
    }
}

// Start new chat
function startNewChat() {
    if (conversationHistory.length > 1 && !confirm('Start a new chat? Current conversation will be cleared.')) {
        return;
    }
    conversationHistory = [];
    saveConversation();
    renderMessages();
    closeSidebar();
}

// Handle window resize
window.addEventListener('resize', checkMobileView);

// Configure marked.js
marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: function(code, lang) {
        return code;
    }
});