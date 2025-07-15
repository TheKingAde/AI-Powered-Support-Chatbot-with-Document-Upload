// AI-Powered Support Chatbot - Frontend JavaScript
class ChatbotApp {
    constructor() {
        this.initializeElements();
        this.bindEvents();
        this.loadDocuments();
        this.setupAnimations();
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

        // Chat events
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
            rootMargin: '0px 0px -100px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);

        // Observe animatable elements
        document.querySelectorAll('.upload-card, .chat-card, .documents-card').forEach(el => {
            observer.observe(el);
        });
    }

    // File Upload Functionality
    handleDragOver(e) {
        e.preventDefault();
        this.uploadArea.classList.add('drag-over');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('drag-over');
    }

    handleDrop(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('drag-over');
        const files = Array.from(e.dataTransfer.files);
        this.uploadFiles(files);
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.uploadFiles(files);
    }

    async uploadFiles(files) {
        if (!files.length) return;

        // Validate files
        const validFiles = this.validateFiles(files);
        if (!validFiles.length) {
            this.showToast('No valid files selected', 'error');
            return;
        }

        // Show progress
        this.showUploadProgress();
        
        try {
            const formData = new FormData();
            validFiles.forEach(file => {
                formData.append('files', file);
            });

            // Simulate progress animation
            this.animateProgress(0, 30, 500);

            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            // Complete progress animation
            this.animateProgress(30, 90, 1000);

            const result = await response.json();

            if (response.ok) {
                this.animateProgress(90, 100, 200);
                setTimeout(() => {
                    this.hideUploadProgress();
                    this.displayUploadResults(result);
                    this.loadDocuments();
                    this.showToast(result.message, 'success');
                }, 300);
            } else {
                throw new Error(result.error || 'Upload failed');
            }

        } catch (error) {
            console.error('Upload error:', error);
            this.hideUploadProgress();
            this.showToast(`Upload failed: ${error.message}`, 'error');
        }

        // Reset file input
        this.fileInput.value = '';
    }

    validateFiles(files) {
        const maxSize = 50 * 1024 * 1024; // 50MB
        const allowedTypes = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel',
            'text/csv',
            'text/plain',
            'image/jpeg',
            'image/jpg',
            'image/png',
            'image/gif',
            'image/bmp'
        ];

        return files.filter(file => {
            if (file.size > maxSize) {
                this.showToast(`File ${file.name} is too large (max 50MB)`, 'error');
                return false;
            }
            
            const isValidType = allowedTypes.includes(file.type) || 
                              /\.(pdf|docx|xlsx|xls|csv|txt|jpg|jpeg|png|gif|bmp)$/i.test(file.name);
            
            if (!isValidType) {
                this.showToast(`File ${file.name} has unsupported format`, 'error');
                return false;
            }
            
            return true;
        });
    }

    showUploadProgress() {
        this.uploadProgress.style.display = 'block';
        this.progressFill.style.width = '0%';
        this.progressText.textContent = 'Processing files...';
    }

    hideUploadProgress() {
        this.uploadProgress.style.display = 'none';
    }

    animateProgress(from, to, duration) {
        const startTime = performance.now();
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const currentValue = from + (to - from) * this.easeOutCubic(progress);
            
            this.progressFill.style.width = `${currentValue}%`;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        requestAnimationFrame(animate);
    }

    easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    displayUploadResults(result) {
        this.uploadedFiles.innerHTML = '';
        
        if (result.files && result.files.length > 0) {
            result.files.forEach(file => {
                const fileElement = this.createFileResultElement(file);
                this.uploadedFiles.appendChild(fileElement);
            });
        }
    }

    createFileResultElement(file) {
        const div = document.createElement('div');
        div.className = `file-result ${file.status}`;
        
        const icon = file.status === 'success' ? 'fas fa-check' : 'fas fa-times';
        const chunks = file.chunks ? `${file.chunks} chunks` : '';
        const message = file.message || '';
        
        div.innerHTML = `
            <div class="file-info">
                <div class="file-icon">
                    <i class="${icon}"></i>
                </div>
                <div class="file-details">
                    <h4>${file.filename}</h4>
                    <div class="file-meta">${chunks} ${message}</div>
                </div>
            </div>
        `;
        
        return div;
    }

    // Chat Functionality
    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || this.sendButton.disabled) return;

        // Add user message to chat
        this.addMessage(message, 'user');
        this.chatInput.value = '';
        this.updateCharCounter();
        
        // Disable input and show typing indicator
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
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
            this.showToast(`Chat error: ${error.message}`, 'error');
        }

        // Re-enable input
        this.setInputState(true);
    }

    addMessage(text, sender, metadata = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const avatar = sender === 'user' ? 'fas fa-user' : 'fas fa-robot';
        const time = new Date().toLocaleTimeString();
        
        let contextInfo = '';
        if (metadata.contextUsed) {
            contextInfo = `<div class="context-info">📚 Used ${metadata.sources} document(s)</div>`;
        }
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="${avatar}"></i>
            </div>
            <div class="message-content">
                <p>${this.formatMessage(text)}</p>
                ${contextInfo}
                <div class="message-time">${time}</div>
            </div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessage(text) {
        // Simple text formatting
        return text
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }

    showTypingIndicator() {
        this.typingIndicator.style.display = 'flex';
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }

    setInputState(enabled) {
        this.chatInput.disabled = !enabled;
        this.sendButton.disabled = !enabled;
        if (enabled) {
            this.chatInput.focus();
        }
    }

    updateCharCounter() {
        const length = this.chatInput.value.length;
        this.charCounter.textContent = `${length}/500`;
        
        if (length > 450) {
            this.charCounter.style.color = 'var(--error-color)';
        } else if (length > 400) {
            this.charCounter.style.color = 'var(--warning-color)';
        } else {
            this.charCounter.style.color = 'var(--text-secondary)';
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }

    clearChatHistory() {
        if (confirm('Are you sure you want to clear the chat history?')) {
            // Keep only the welcome message
            const welcomeMessage = this.chatMessages.querySelector('.welcome-message');
            this.chatMessages.innerHTML = '';
            if (welcomeMessage) {
                this.chatMessages.appendChild(welcomeMessage);
            }
            this.showToast('Chat history cleared', 'success');
        }
    }

    exportChatHistory() {
        const messages = Array.from(this.chatMessages.querySelectorAll('.message:not(.welcome-message)'));
        if (messages.length === 0) {
            this.showToast('No messages to export', 'warning');
            return;
        }

        let exportText = 'AI Support Chat Export\n';
        exportText += '========================\n\n';

        messages.forEach(msg => {
            const isUser = msg.classList.contains('user-message');
            const content = msg.querySelector('.message-content p').textContent;
            const time = msg.querySelector('.message-time').textContent;
            
            exportText += `${isUser ? 'You' : 'AI'} (${time}):\n${content}\n\n`;
        });

        const blob = new Blob([exportText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat-export-${new Date().toISOString().split('T')[0]}.txt`;
        a.click();
        URL.revokeObjectURL(url);

        this.showToast('Chat exported successfully', 'success');
    }

    // Document Management
    async loadDocuments() {
        try {
            const response = await fetch('/documents');
            const result = await response.json();

            if (response.ok) {
                this.displayDocuments(result.documents);
            } else {
                console.error('Failed to load documents:', result.error);
            }
        } catch (error) {
            console.error('Error loading documents:', error);
        }
    }

    displayDocuments(documents) {
        if (!documents || documents.length === 0) {
            this.documentsList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-folder-open"></i>
                    <p>No documents uploaded yet</p>
                </div>
            `;
            return;
        }

        this.documentsList.innerHTML = '';
        documents.forEach(doc => {
            const docElement = this.createDocumentElement(doc);
            this.documentsList.appendChild(docElement);
        });
    }

    createDocumentElement(doc) {
        const div = document.createElement('div');
        div.className = 'document-item';
        
        div.innerHTML = `
            <div class="document-info">
                <h4>${doc.filename}</h4>
                <div class="document-meta">${doc.chunks} chunks • ${doc.sample_text}</div>
            </div>
            <div class="document-actions">
                <button class="btn btn-danger" onclick="app.deleteDocument('${doc.filename}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        return div;
    }

    async deleteDocument(filename) {
        if (!confirm(`Delete ${filename}?`)) return;

        try {
            const response = await fetch(`/documents/${encodeURIComponent(filename)}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (response.ok) {
                this.loadDocuments();
                this.showToast(result.message, 'success');
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Delete error:', error);
            this.showToast(`Failed to delete: ${error.message}`, 'error');
        }
    }

    async clearAllDocuments() {
        if (!confirm('Clear all documents and chat history?')) return;

        this.showLoading();

        try {
            const response = await fetch('/clear', {
                method: 'POST'
            });

            const result = await response.json();

            if (response.ok) {
                this.loadDocuments();
                this.clearChatHistory();
                this.uploadedFiles.innerHTML = '';
                this.showToast(result.message, 'success');
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Clear error:', error);
            this.showToast(`Failed to clear: ${error.message}`, 'error');
        }

        this.hideLoading();
    }

    // System Health Check
    async checkSystemHealth() {
        try {
            const response = await fetch('/health');
            const result = await response.json();

            if (response.ok) {
                this.showToast(`System healthy • ${result.documents_count} documents loaded`, 'success');
            } else {
                this.showToast('System check failed', 'error');
            }
        } catch (error) {
            this.showToast('Cannot connect to server', 'error');
        }
    }

    // Utility Functions
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        
        toast.innerHTML = `
            <div class="toast-content">
                <i class="toast-icon ${icons[type]}"></i>
                <span>${message}</span>
            </div>
        `;
        
        this.toastContainer.appendChild(toast);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.classList.add('fade-out');
                setTimeout(() => {
                    toast.remove();
                }, 300);
            }
        }, 5000);
    }

    showLoading() {
        this.loadingOverlay.style.display = 'flex';
    }

    hideLoading() {
        this.loadingOverlay.style.display = 'none';
    }

    showModal(modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    hideModal(modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ChatbotApp();
});

// Service Worker for PWA capabilities (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => {
                console.log('SW registered: ', registration);
            })
            .catch(registrationError => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}