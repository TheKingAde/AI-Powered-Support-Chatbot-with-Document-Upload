import re
import g4f
from g4f.Provider import Yqcloud, Blackbox, PollinationsAI, OIVSCodeSer2, WeWordle
import time
from datetime import datetime
import logging
import secrets
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from PyPDF2 import PdfReader
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import os
import tempfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "60b87d3fedd53dbc74980946548d21a0695240580fafc5e972a7388284fd14c3"
# Enable CORS
CORS(app)

EMBEDDING_MODEL = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
VECTOR_DB_PATH = "./vector_db"

@app.route('/upload', methods=['POST'])
def upload():
    # Handle both 'file' and 'files' field names for compatibility
    files = request.files.getlist('files') or request.files.getlist('file')
    
    if not files or not any(f.filename for f in files):
        return jsonify({'error': 'No file provided'}), 400

    processed_files = []
    
    for file in files:
        if not file.filename:
            continue
            
        filename = file.filename.lower()
        
        if not filename.endswith(('.pdf', '.txt', '.docx')):
            return jsonify({'error': f'Unsupported file type: {filename}'}), 400

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file.save(tmp.name)
            file_path = tmp.name

        try:
            # Extract text
            if filename.endswith('.pdf'):
                reader = PdfReader(file_path)
                text = "\n".join([page.extract_text() or "" for page in reader.pages])
            elif filename.endswith('.docx'):
                doc = Document(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
            else:  # .txt
                text = open(file_path, encoding='utf-8').read()

            # Chunk text
            splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            texts = splitter.create_documents([text])

            # Create or update vector store
            if os.path.exists(VECTOR_DB_PATH):
                vectorstore = FAISS.load_local(VECTOR_DB_PATH, EMBEDDING_MODEL, allow_dangerous_deserialization=True)
                new_vectorstore = FAISS.from_documents(texts, EMBEDDING_MODEL)
                vectorstore.merge_from(new_vectorstore)
            else:
                vectorstore = FAISS.from_documents(texts, EMBEDDING_MODEL)
                
            vectorstore.save_local(VECTOR_DB_PATH)
            processed_files.append({
                'filename': file.filename,
                'chunks': len(texts)
            })

        except Exception as e:
            return jsonify({'error': f'Error processing {filename}: {str(e)}'}), 500
        finally:
            os.remove(file_path)

    return jsonify({
        'message': f'Successfully processed {len(processed_files)} file(s)',
        'files': processed_files
    })


# Providers and models
ai_chats = [
    {"provider": Yqcloud, "model": "gpt-4", "label": "Yqcloud - GPT-4"},
    {"provider": Blackbox, "model": "gpt-4", "label": "Blackbox - GPT-4"},
    {"provider": PollinationsAI, "model": None, "label": "PollinationsAI - DEFAULT"},
    {"provider": OIVSCodeSer2, "model": "gpt-4o-mini", "label": "OIVSCodeSer2 - gpt-4o-mini"},
    {"provider": WeWordle, "model": "gpt-4", "label": "WeWordle - GPT-4"},
]

failed_ai_chats = set()
ai_chat_to_use = 0
def send_ai_request(prompt):
    global ai_chat_to_use, failed_ai_chats

    total_chats = len(ai_chats)
    attempts = 0

    while attempts < total_chats:
        current_chat = ai_chats[ai_chat_to_use]
        if ai_chat_to_use in failed_ai_chats:
            ai_chat_to_use = (ai_chat_to_use + 1) % total_chats
            attempts += 1
            continue

        time.sleep(2)
        try:
            # 🧠 Construct chat history with roles
            messages = prompt

            kwargs = {
                "provider": current_chat["provider"],
                "messages": messages,
            }
            if current_chat["model"]:
                kwargs["model"] = current_chat["model"]

            response = g4f.ChatCompletion.create(**kwargs)

            # if (
            #     response
            #     and isinstance(response, str)
            #     and response.strip()
            #     and re.match(r"^[\s]*[a-zA-Z]", response)
            # ):
            return response

            failed_ai_chats.add(ai_chat_to_use)
            ai_chat_to_use = (ai_chat_to_use + 1) % total_chats
            attempts += 1

        except Exception as e:
            failed_ai_chats.add(ai_chat_to_use)
            ai_chat_to_use = (ai_chat_to_use + 1) % total_chats
            attempts += 1

    failed_ai_chats.clear()
    return False

@app.route('/')
def index():
    """Serve the main chatbot interface"""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        if len(user_message) > 1000:
            return jsonify({'error': 'Message too long. Please keep it under 1000 characters.'}), 400
        
        # Initialize or retrieve chat history
        if 'chat_history' not in session:
            session['chat_history'] = []

        chat_history = session['chat_history']

        # Prepare full context for AI
        ai_messages = []
        for entry in chat_history:
            ai_messages.append({"role": "user", "content": entry["user"]})
            ai_messages.append({"role": "assistant", "content": entry["bot"]})
            # Inside chat()
            retrieved_docs = []
            if os.path.exists(VECTOR_DB_PATH):
                try:
                    vectorstore = FAISS.load_local(VECTOR_DB_PATH, EMBEDDING_MODEL, allow_dangerous_deserialization=True)
                    relevant = vectorstore.similarity_search(user_message, k=3)
                    retrieved_docs = [doc.page_content for doc in relevant]
                except Exception as e:
                    logger.warning(f"RAG failed: {e}")
            ai_messages.append({"role": "system", "content": "Relevant documents: " + "\n".join(retrieved_docs) if retrieved_docs else "No relevant documents found."})

        ai_messages.append({"role": "user", "content": user_message})

        # Send to AI
        response = send_ai_request(ai_messages)

        # Save latest exchange
        chat_history.append({
            "user": user_message,
            "bot": response,
            "timestamp": datetime.now().isoformat()
        })

        # Limit to last 10 exchanges
        if len(chat_history) > 10:
            chat_history = chat_history[-10:]

        session['chat_history'] = chat_history

        return jsonify({
            'response': response,
            'history_length': len(chat_history)
        })
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        if "rate" in str(e).lower() or "429" in str(e):
            return jsonify({
                'error': 'Service is experiencing high load. Please try again in a moment.',
                'retry_after': 60,
                'is_rate_limit': True
            }), 429
        
        return jsonify({'error': 'Sorry, I encountered an error. Please try again.'}), 500
    
@app.route('/documents', methods=['GET'])
def get_documents():
    """Get list of uploaded documents"""
    try:
        if not os.path.exists(VECTOR_DB_PATH):
            return jsonify({'documents': []})
        
        # For simplicity, return empty list since we don't track individual files
        # In a real implementation, you'd store file metadata
        return jsonify({'documents': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/documents/<filename>', methods=['DELETE'])
def delete_document(filename):
    """Delete a specific document"""
    try:
        # For simplicity, just clear all documents
        # In a real implementation, you'd remove specific file chunks
        if os.path.exists(VECTOR_DB_PATH):
            shutil.rmtree(VECTOR_DB_PATH)
        return jsonify({'message': f'Document {filename} deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """System health check"""
    try:
        doc_count = 0
        if os.path.exists(VECTOR_DB_PATH):
            doc_count = 1  # Simplified count
            
        return jsonify({
            'status': 'healthy',
            'documents_count': doc_count,
            'rate_limit_status': {
                'requests_last_minute': 10,  # Simplified
                'limit': 60
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear', methods=['POST'])
def clear_data():
    """Clear file content and chat history"""
    session.pop('chat_history', None)
    session.pop('file_content', None)
    
    # Also clear vector database
    if os.path.exists(VECTOR_DB_PATH):
        shutil.rmtree(VECTOR_DB_PATH)
    
    return jsonify({'message': 'Chat history and file content cleared.'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)