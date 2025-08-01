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
import json
import uuid
from typing import Dict, List, Optional

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
METADATA_FILE = "./file_metadata.json"

class FileMetadataManager:
    """Manages file metadata and vector associations"""
    
    def __init__(self, metadata_file: str):
        self.metadata_file = metadata_file
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        """Load metadata from file"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
        return {
            'files': {},
            'chunk_mappings': {},
            'next_chunk_id': 0
        }
    
    def _save_metadata(self):
        """Save metadata to file"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def add_file(self, filename: str, file_size: int, upload_date: str, 
                 chunk_count: int, file_type: str) -> str:
        """Add a new file to metadata"""
        file_id = str(uuid.uuid4())
        
        self.metadata['files'][file_id] = {
            'filename': filename,
            'file_size': file_size,
            'upload_date': upload_date,
            'chunk_count': chunk_count,
            'file_type': file_type,
            'status': 'uploaded'
        }
        
        self._save_metadata()
        return file_id
    
    def add_chunk_mapping(self, file_id: str, chunk_text: str, chunk_index: int) -> int:
        """Add a chunk mapping and return chunk ID"""
        chunk_id = self.metadata['next_chunk_id']
        self.metadata['next_chunk_id'] += 1
        
        self.metadata['chunk_mappings'][chunk_id] = {
            'file_id': file_id,
            'chunk_text': chunk_text,
            'chunk_index': chunk_index
        }
        
        self._save_metadata()
        return chunk_id
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict]:
        """Get metadata for a specific file"""
        return self.metadata['files'].get(file_id)
    
    def get_all_files(self) -> List[Dict]:
        """Get metadata for all files"""
        files = []
        for file_id, metadata in self.metadata['files'].items():
            file_info = metadata.copy()
            file_info['file_id'] = file_id
            files.append(file_info)
        return files
    
    def get_file_chunks(self, file_id: str) -> List[int]:
        """Get all chunk IDs for a specific file"""
        chunk_ids = []
        for chunk_id, mapping in self.metadata['chunk_mappings'].items():
            if mapping['file_id'] == file_id:
                chunk_ids.append(chunk_id)
        return chunk_ids
    
    def delete_file(self, file_id: str) -> bool:
        """Delete a file and all its chunks"""
        if file_id not in self.metadata['files']:
            return False
        
        # Remove file metadata
        del self.metadata['files'][file_id]
        
        # Remove all chunks for this file
        chunks_to_remove = []
        for chunk_id, mapping in self.metadata['chunk_mappings'].items():
            if mapping['file_id'] == file_id:
                chunks_to_remove.append(chunk_id)
        
        for chunk_id in chunks_to_remove:
            del self.metadata['chunk_mappings'][chunk_id]
        
        self._save_metadata()
        return True
    
    def clear_all(self):
        """Clear all metadata"""
        self.metadata = {
            'files': {},
            'chunk_mappings': {},
            'next_chunk_id': 0
        }
        self._save_metadata()

# Initialize metadata manager
metadata_manager = FileMetadataManager(METADATA_FILE)

def ensure_vector_db_directory():
    """Ensure the vector database directory exists"""
    try:
        os.makedirs(VECTOR_DB_PATH, exist_ok=True)
        logger.debug(f"Vector database directory ensured: {VECTOR_DB_PATH}")
    except Exception as e:
        logger.error(f"Error creating vector database directory: {e}")
        raise

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

            # Store file metadata
            file_size = os.path.getsize(file_path)
            upload_date = datetime.now().isoformat()
            file_type = os.path.splitext(filename)[1].lower()
            
            file_id = metadata_manager.add_file(
                filename=file.filename,
                file_size=file_size,
                upload_date=upload_date,
                chunk_count=len(texts),
                file_type=file_type
            )

            # Create or update vector store
            try:
                # Ensure vector database directory exists
                ensure_vector_db_directory()
                
                if os.path.exists(VECTOR_DB_PATH) and os.path.getsize(VECTOR_DB_PATH) > 0:
                    try:
                        vectorstore = FAISS.load_local(VECTOR_DB_PATH, EMBEDDING_MODEL, allow_dangerous_deserialization=True)
                        new_vectorstore = FAISS.from_documents(texts, EMBEDDING_MODEL)
                        vectorstore.merge_from(new_vectorstore)
                        vectorstore.save_local(VECTOR_DB_PATH)
                        logger.info(f"Vector store updated successfully for {filename}")
                    except Exception as e:
                        logger.warning(f"Failed to load existing vector store, creating new one: {e}")
                        vectorstore = FAISS.from_documents(texts, EMBEDDING_MODEL)
                        vectorstore.save_local(VECTOR_DB_PATH)
                        logger.info(f"Created new vector store for {filename}")
                else:
                    vectorstore = FAISS.from_documents(texts, EMBEDDING_MODEL)
                    vectorstore.save_local(VECTOR_DB_PATH)
                    logger.info(f"Created new vector store for {filename}")
                    
            except Exception as e:
                logger.error(f"Error creating vector store for {filename}: {e}")
                raise Exception(f"Vector store error: {str(e)}")
            
            # Store chunk mappings
            for i, text_doc in enumerate(texts):
                metadata_manager.add_chunk_mapping(file_id, text_doc.page_content, i)
            
            processed_files.append({
                'filename': file.filename,
                'chunks': len(texts),
                'file_id': file_id,
                'file_size': file_size,
                'upload_date': upload_date
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
        files = metadata_manager.get_all_files()
        return jsonify({'documents': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/documents/<file_id>', methods=['DELETE'])
def delete_document(file_id):
    """Delete a specific document and its chunks"""
    try:
        # Get file metadata
        file_metadata = metadata_manager.get_file_metadata(file_id)
        if not file_metadata:
            return jsonify({'error': 'File not found'}), 404
        
        # Delete from metadata
        success = metadata_manager.delete_file(file_id)
        if not success:
            return jsonify({'error': 'Failed to delete file'}), 500
        
        # Rebuild vector store without the deleted chunks
        if os.path.exists(VECTOR_DB_PATH):
            try:
                # Load existing vectorstore
                vectorstore = FAISS.load_local(VECTOR_DB_PATH, EMBEDDING_MODEL, allow_dangerous_deserialization=True)
                
                # Get all remaining chunks from metadata
                all_chunks = []
                for chunk_id, mapping in metadata_manager.metadata['chunk_mappings'].items():
                    all_chunks.append(mapping['chunk_text'])
                
                if all_chunks:
                    # Create new vectorstore with remaining chunks
                    new_vectorstore = FAISS.from_texts(all_chunks, EMBEDDING_MODEL)
                    new_vectorstore.save_local(VECTOR_DB_PATH)
                else:
                    # No chunks left, remove vector store
                    shutil.rmtree(VECTOR_DB_PATH)
                    
            except Exception as e:
                logger.error(f"Error rebuilding vector store: {e}")
                # If rebuilding fails, clear the vector store
                if os.path.exists(VECTOR_DB_PATH):
                    shutil.rmtree(VECTOR_DB_PATH)
        
        return jsonify({
            'message': f'Document {file_metadata["filename"]} deleted successfully',
            'deleted_file': file_metadata
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """System health check"""
    try:
        files = metadata_manager.get_all_files()
        total_chunks = len(metadata_manager.metadata['chunk_mappings'])
        
        return jsonify({
            'status': 'healthy',
            'documents_count': len(files),
            'total_chunks': total_chunks,
            'files': [f['filename'] for f in files],
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
    try:
        # Clear session data
        session.pop('chat_history', None)
        session.pop('file_content', None)
        logger.info("Session data cleared")
        
        # Clear metadata
        metadata_manager.clear_all()
        logger.info("Metadata cleared")
        
        # Clear vector database
        if os.path.exists(VECTOR_DB_PATH):
            try:
                shutil.rmtree(VECTOR_DB_PATH)
                logger.info("Vector database cleared successfully")
            except Exception as e:
                logger.error(f"Error clearing vector database: {e}")
                # Continue even if vector database clearing fails
        
        logger.info("All data cleared successfully")
        return jsonify({
            'message': 'Chat history and file content cleared successfully.',
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error in clear_data: {e}")
        return jsonify({
            'error': f'Failed to clear data: {str(e)}',
            'status': 'error'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)