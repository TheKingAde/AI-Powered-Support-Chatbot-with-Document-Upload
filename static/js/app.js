// AI-Powered Support Chatbot - Frontend JavaScript (Simplified)
class ChatbotApp {
    constructor() {
        this.initializeElements();
        this.bindEvents();
        this.loadDocuments();
        this.setupAnimations();
        
        // Simple state tracking
        this.isRequestInProgress = false;
    }

    initializeElements() {
        // Upload elements
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        this.uploadProgress = document.getElementById('uploadProgress');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        this.uploadedFiles = document.getElementById('uploadedFiles');

        // Chat elements
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.charCounter = document.getElementById('charCounter');

        // Document elements
        this.documentsList = document.getElementById('documentsList');
        this.clearDocuments = document.getElementById('clearDocuments');
        this.clearChat = document.getElementById('clearChat');
        this.exportChat = document.getElementById('exportChat');

        // Modal elements
        this.aboutModal = document.getElementById('aboutModal');
        this.aboutBtn = document.getElementById('aboutBtn');
        this.closeAbout = document.getElementById('closeAbout');
        this.healthCheck = document.getElementById('healthCheck');

        // Utility elements
        this.toastContainer = document.getElementById('toastContainer');
        this.loadingOverlay = document.getElementById('loadingOverlay');
    }

    bindEvents() {
        // File upload events
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Drag and drop events
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));

        // Chat events - simplified
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        this.chatInput.addEventListener('input', () => this.updateCharCounter());

        // Control events
        this.clearChat.addEventListener('click', () => this.clearChatHistory());
        this.exportChat.addEventListener('click', () => this.exportChatHistory());
        this.clearDocuments.addEventListener('click', () => this.clearAllDocuments());

        // Modal events
        this.aboutBtn.addEventListener('click', () => this.showModal(this.aboutModal));
        this.closeAbout.addEventListener('click', () => this.hideModal(this.aboutModal));
        this.healthCheck.addEventListener('click', () => this.checkSystemHealth());

        // Click outside modal to close
        this.aboutModal.addEventListener('click', (e) => {
            if (e.target === this.aboutModal) {
                this.hideModal(this.aboutModal);
            }
        });

        // Escape key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !this.aboutModal.style.display === 'none') {
                this.hideModal(this.aboutModal);
            }
        });
    }

    setupAnimations() {
        // Add scroll animation observer
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, observerOptions);

        // Observe elements for animation
        document.querySelectorAll('.upload-card, .chat-card, .controls-card').forEach(el => {
            observer.observe(el);
        });
    }

    // Chat Functionality - Simplified
    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || this.isRequestInProgress) return;

        // Add user message to chat
        this.addMessage(message, 'user');
        this.chatInput.value = '';
        this.updateCharCounter();
        
        // Set request state
        this.isRequestInProgress = true;
        this.setInputState(false);
        this.showTypingIndicator();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            const result = await response.json();

            if (response.ok) {
                // Hide typing indicator and add bot response
                this.hideTypingIndicator();
                setTimeout(() => {
                    this.addMessage(result.response, 'bot', {
                        contextUsed: result.context_used,
                        sources: result.sources
                    });
                }, 500);
            } else {
                throw new Error(result.error || 'Failed to get response');
            }

        } catch (error) {
            console.error('Chat error:', error);
            this.hideTypingIndicator();
            
            if (error.message.includes('429') || error.message.includes('Too many requests')) {
                this.addMessage(
                    'I\'m receiving too many requests right now. Please wait a moment and try again.', 
                    'bot'
                );
            } else {
                this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
            }
            this.showToast(`Error: ${error.message}`, 'error');
        } finally {
            // Re-enable input
            this.isRequestInProgress = false;
            this.setInputState(true);
        }
    }

    addMessage(text, sender, metadata = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const avatar = sender === 'user' ? 'fas fa-user' : 'fas fa-robot';
        const time = new Date().toLocaleTimeString();
        
        let contextInfo = '';
        if (metadata.contextUsed) {
            contextInfo = `<div class="context-info">
                <i class="fas fa-file-alt"></i>
                Referenced ${metadata.sources} document${metadata.sources > 1 ? 's' : ''}
            </div>`;
        }
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="${avatar}"></i>
            </div>
            <div class="message-content">
                <div class="message-text">${this.formatMessage(text)}</div>
                ${contextInfo}
                <div class="message-time">${time}</div>
            </div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        
        // Add animation
        setTimeout(() => {
            messageDiv.classList.add('message-appear');
        }, 100);
    }

    formatMessage(text) {
        // Convert markdown-style formatting to HTML
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    showTypingIndicator() {
        if (this.typingIndicator) {
            this.typingIndicator.style.display = 'flex';
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }

    hideTypingIndicator() {
        if (this.typingIndicator) {
            this.typingIndicator.style.display = 'none';
        }
    }

    setInputState(enabled) {
        this.chatInput.disabled = !enabled;
        this.sendButton.disabled = !enabled;
        
        if (enabled) {
            this.chatInput.focus();
            this.sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
        } else {
            this.sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        }
    }

    updateCharCounter() {
        if (this.charCounter) {
            const length = this.chatInput.value.length;
            const maxLength = 1000;
            this.charCounter.textContent = `${length}/${maxLength}`;
            
            if (length > maxLength * 0.8) {
                this.charCounter.style.color = '#ff6b6b';
            } else {
                this.charCounter.style.color = '#6c757d';
            }
        }
    }

    // File Upload Functions - Simplified
    handleFileSelect(event) {
        const files = Array.from(event.target.files);
        this.uploadFiles(files);
    }

    handleDragOver(event) {
        event.preventDefault();
        this.uploadArea.classList.add('drag-over');
    }

    handleDragLeave(event) {
        event.preventDefault();
        this.uploadArea.classList.remove('drag-over');
    }

    handleDrop(event) {
        event.preventDefault();
        this.uploadArea.classList.remove('drag-over');
        
        const files = Array.from(event.dataTransfer.files);
        this.uploadFiles(files);
    }

    async uploadFiles(files) {
        if (!files.length) return;

        this.showLoadingOverlay();
        this.showProgress(0);

        const formData = new FormData();
        files.forEach(file => formData.append('files', file));

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                this.showToast(`Successfully processed ${result.files.length} files`, 'success');
                this.loadDocuments();
            } else {
                throw new Error(result.error || 'Upload failed');
            }

        } catch (error) {
            console.error('Upload error:', error);
            this.showToast(`Upload failed: ${error.message}`, 'error');
        } finally {
            this.hideLoadingOverlay();
        }
    }

    showProgress(percent) {
        if (this.uploadProgress) {
            this.uploadProgress.style.display = 'block';
            this.progressFill.style.width = `${percent}%`;
            
            if (this.progressText) {
                this.progressText.textContent = `${Math.round(percent)}%`;
            }
        }
    }

    hideProgress() {
        if (this.uploadProgress) {
            this.uploadProgress.style.display = 'none';
        }
    }

    // Document Management
    async loadDocuments() {
        try {
            const response = await fetch('/documents');
            const data = await response.json();

            if (response.ok) {
                this.displayDocuments(data.documents);
            } else {
                console.error('Failed to load documents:', data.error);
            }

        } catch (error) {
            console.error('Error loading documents:', error);
        }
    }

    displayDocuments(documents) {
        if (!this.documentsList) return;

        if (documents.length === 0) {
            this.documentsList.innerHTML = '<p class="no-documents">No documents uploaded yet</p>';
            return;
        }

        this.documentsList.innerHTML = documents.map(doc => `
            <div class="document-item">
                <div class="document-info">
                    <h4>${doc.filename}</h4>
                    <p>${doc.chunks} chunks</p>
                    <small>${doc.sample_text}</small>
                </div>
                <button class="delete-btn" onclick="app.deleteDocument('${doc.filename}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `).join('');
    }

    async deleteDocument(filename) {
        if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;

        try {
            const response = await fetch(`/documents/${filename}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (response.ok) {
                this.showToast(result.message, 'success');
                this.loadDocuments();
            } else {
                throw new Error(result.error || 'Delete failed');
            }

        } catch (error) {
            console.error('Delete error:', error);
            this.showToast(`Delete failed: ${error.message}`, 'error');
        }
    }

    // Utility Functions
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'exclamation-triangle' : 'info'}"></i>
                <span>${message}</span>
            </div>
        `;

        this.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('show');
        }, 100);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }

    showLoadingOverlay() {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = 'flex';
        }
    }

    hideLoadingOverlay() {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = 'none';
        }
    }

    showModal(modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    hideModal(modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }

    // Control Functions
    async clearChatHistory() {
        if (!confirm('Are you sure you want to clear the chat history?')) return;

        this.chatMessages.innerHTML = '';
        this.showToast('Chat history cleared', 'success');
    }

    async clearAllDocuments() {
        if (!confirm('Are you sure you want to clear all documents and chat history?')) return;

        try {
            const response = await fetch('/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            if (response.ok) {
                this.showToast(result.message, 'success');
                this.loadDocuments();
                this.chatMessages.innerHTML = '';
            } else {
                throw new Error(result.error || 'Clear failed');
            }

        } catch (error) {
            console.error('Clear error:', error);
            this.showToast(`Clear failed: ${error.message}`, 'error');
        }
    }

    exportChatHistory() {
        const messages = Array.from(this.chatMessages.querySelectorAll('.message'));
        const chatHistory = messages.map(msg => {
            const isUser = msg.classList.contains('user-message');
            const text = msg.querySelector('.message-text').textContent;
            const time = msg.querySelector('.message-time').textContent;
            return `${isUser ? 'You' : 'Bot'} (${time}): ${text}`;
        }).join('\n\n');

        const blob = new Blob([chatHistory], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat-history-${new Date().toISOString().split('T')[0]}.txt`;
        a.click();
        URL.revokeObjectURL(url);

        this.showToast('Chat history exported', 'success');
    }

    async checkSystemHealth() {
        try {
            const response = await fetch('/health');
            const data = await response.json();

            if (response.ok) {
                this.showToast(
                    `System Status: ${data.status.toUpperCase()} | Documents: ${data.documents_count} | Requests: ${data.rate_limit_status.requests_last_minute}/${data.rate_limit_status.limit}`,
                    'success'
                );
            } else {
                throw new Error(data.error || 'Health check failed');
            }

        } catch (error) {
            console.error('Health check error:', error);
            this.showToast(`Health check failed: ${error.message}`, 'error');
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ChatbotApp();
});