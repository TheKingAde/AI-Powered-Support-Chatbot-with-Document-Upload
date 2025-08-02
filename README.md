# AI-Powered Support Chatbot with Document Upload

## Project Overview

Web application that allows users to upload various types of documents (PDF, XLSX, CSV, images, and more) to train/customize the chatbot’s knowledge base. The chatbot integrates with the **g4f ** to provide smart, human-like answers based on uploaded content or predefined FAQs.

---

## Technology Stack

- **Frontend:** HTML, CSS (modern frameworks or vanilla with animations), JavaScript  
- **Backend:** Python Flask  
- **AI Integration:** g4f  (chat/completion + embeddings)  
- **File Processing:** Support for PDF, XLSX, CSV, images (e.g., OCR)  
- **Storage:** Temporary document storage, embeddings stored in a vector database or in-memory store  
- **Optional:** Use vector DB (like FAISS) or lightweight search index for retrieval

---

## Functional Requirements

### 1. User Interface

- Modern, clean, responsive design with smooth animations (page transitions, buttons, loading spinners)
- Homepage with:
  - Brief intro about the chatbot
  - Upload area with drag & drop and file selector (accepting multiple files of any format)
  - Instructions on supported file types: PDF, XLSX, CSV, JPG/PNG (image), TXT, DOCX, etc.
- Chat interface:
  - Real-time chat messages with user and bot styling
  - Typing indicators and animated message bubbles
  - Scrollable chat history
- Admin or user dashboard (optional):
  - View uploaded documents
  - Manage/delete uploaded data
- Search bar to ask questions directly

### 2. File Upload & Processing

- Allow uploading of multiple files of different formats in one session
- Backend processing pipeline that:
  - Extracts text from PDFs, XLSX (spreadsheets), CSV, TXT, DOCX files
  - Uses OCR (e.g., Tesseract or another library) to extract text from image files (JPG, PNG, etc.)
  - Cleans and chunks extracted text into manageable pieces for embeddings
- Store processed chunks temporarily (in memory or DB) for retrieval

### 3. AI Integration

- Use g4f  to:
  - Generate vector embeddings for all document chunks (using embedding models)
  - Store embeddings in a vector search system (can be simple in-memory or FAISS)
- When user asks a question:
  - Use similarity search on embeddings to find relevant chunks
  - Send retrieved context along with user query to g4f chat/completion 
  - Return human-like, context-aware answers
- Support fallback to a default FAQ knowledge base if no documents are uploaded

### 4. Chatbot Interaction

- User can interact with chatbot naturally in chat UI
- Bot answers based on uploaded content and FAQs
- Ability to handle follow-up questions and maintain conversation context (session-based)

### 5. Backend API Endpoints

- `/upload` — POST endpoint to accept multiple file uploads and process them
- `/chat` — POST endpoint for sending user messages and returning AI-generated replies
- `/documents` — GET/DELETE endpoints to list and manage uploaded documents (optional)
- `/faq` — Endpoint to manage default FAQs (optional)
- Secure endpoints if needed (authentication optional for MVP)

### 6. Additional Features

- Loading spinners or skeleton UI during file processing and API calls
- Toast notifications for success/error states (file upload success, API errors)
- Error handling for unsupported file types or corrupted files
- Pagination or lazy loading in chat history if needed
- Option to download chat transcript or export FAQ

---

## Non-Functional Requirements

- Responsive design supporting desktop and mobile
- Fast and smooth UI with subtle animations:
  - Animated file upload progress bars
  - Typing indicator for bot
  - Button hover and click effects
- Code structured with clear separation:
  - Frontend: components, services, utils
  - Backend: routes, services (file processing, AI calls), models
- Modular, maintainable codebase ready for future extensions (e.g., user auth, persistent DB)
- Clear user instructions and validation messages

---

## Summary

Deliver a **user-friendly, visually appealing chatbot web app** powered by g4f and trained dynamically on uploaded documents of any format — PDFs, spreadsheets, CSVs, images (OCR), and more. The chatbot should provide smart, context-aware responses based on the uploaded knowledge base, with a modern frontend featuring animations and smooth interactions.

This project demonstrates your skills in:

- Natural language processing & AI integration  
- Multi-format file processing & OCR  
- Fullstack web development with Flask & JS  
- UX/UI with animations and responsive design  
- API design and asynchronous workflows

---

If needed, please help generate code snippets for:

- File upload handling and text extraction  
- Vector embedding generation & similarity search  
- Chatbot frontend with real-time updates and animations  
- g4f integration with context retrieval  

---

Thank you!
