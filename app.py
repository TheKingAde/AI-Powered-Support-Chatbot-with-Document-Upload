import os
import json
import tempfile
import time
from datetime import datetime
from typing import List, Dict, Any
import logging

from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
import openai
from dotenv import load_dotenv

from services.file_processor import FileProcessor
from services.ai_service import AIService
from services.vector_store import VectorStore

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Enable CORS
CORS(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize services
file_processor = FileProcessor()
ai_service = AIService()
vector_store = VectorStore()

# Simple rate limiting - just track requests per minute per IP
request_tracking = {}

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'docx', 'xlsx', 'csv', 
    'jpg', 'jpeg', 'png', 'gif', 'bmp'
}

def simple_rate_limit_check(ip_address: str, max_requests: int = 60) -> bool:
    """Simple rate limiting - just track requests per minute"""
    current_time = time.time()
    
    if ip_address not in request_tracking:
        request_tracking[ip_address] = []
    
    # Remove old requests outside the window
    request_tracking[ip_address] = [
        timestamp for timestamp in request_tracking[ip_address]
        if current_time - timestamp < 60  # 1 minute window
    ]
    
    # Check if under limit
    if len(request_tracking[ip_address]) >= max_requests:
        return False
    
    # Add current request
    request_tracking[ip_address].append(current_time)
    return True

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve the main chatbot interface"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle multiple file uploads and process them"""
    try:
        # Get client IP for rate limiting
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Simple rate limiting check
        if not simple_rate_limit_check(client_ip, max_requests=30):  # 30 uploads per minute
            return jsonify({
                'error': 'Too many upload requests. Please wait a moment and try again.'
            }), 429
        
        if 'files' not in request.files:
            return jsonify({'error': 'No files selected'}), 400
        
        files = request.files.getlist('files')
        if not files or all(file.filename == '' for file in files):
            return jsonify({'error': 'No files selected'}), 400
        
        processed_files = []
        total_chunks = 0
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Save file temporarily
                file.save(filepath)
                logger.info(f"Processing file: {filename}")
                
                try:
                    # Process file and extract text
                    text_content = file_processor.process_file(filepath)
                    
                    if text_content:
                        # Create chunks and embeddings
                        chunks = file_processor.create_text_chunks(text_content)
                        embeddings = ai_service.create_embeddings(chunks)
                        
                        # Store in vector database
                        vector_store.add_documents(chunks, embeddings, filename)
                        
                        processed_files.append({
                            'filename': file.filename,
                            'processed_filename': filename,
                            'chunks': len(chunks),
                            'status': 'success'
                        })
                        total_chunks += len(chunks)
                        
                        logger.info(f"Successfully processed {filename}: {len(chunks)} chunks")
                    else:
                        processed_files.append({
                            'filename': file.filename,
                            'status': 'error',
                            'message': 'Could not extract text from file'
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing {filename}: {str(e)}")
                    processed_files.append({
                        'filename': file.filename,
                        'status': 'error',
                        'message': str(e)
                    })
                
                # Clean up temporary file
                try:
                    os.remove(filepath)
                except:
                    pass
            else:
                processed_files.append({
                    'filename': file.filename,
                    'status': 'error',
                    'message': 'File type not supported'
                })
        
        return jsonify({
            'message': f'Processed {len([f for f in processed_files if f["status"] == "success"])} files successfully',
            'files': processed_files,
            'total_chunks': total_chunks
        })
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages - simplified without complex rate limiting"""
    try:
        # Get client IP for basic rate limiting
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Simple rate limiting check - 60 requests per minute
        if not simple_rate_limit_check(client_ip, max_requests=60):
            return jsonify({
                'error': 'Too many requests. Please wait a moment and try again.'
            }), 429
        
        data = request.json
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Limit message length
        if len(user_message) > 1000:
            return jsonify({'error': 'Message too long. Please keep it under 1000 characters.'}), 400
        
        # Initialize chat history in session if not exists
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        # Get relevant context from uploaded documents
        relevant_context = vector_store.search_similar(user_message, top_k=3)
        
        # Generate AI response
        response = ai_service.generate_response(
            user_message, 
            relevant_context, 
            session['chat_history']
        )
        
        # Update chat history (keep it manageable)
        session['chat_history'].append({
            'user': user_message,
            'bot': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 10 exchanges
        if len(session['chat_history']) > 10:
            session['chat_history'] = session['chat_history'][-10:]
        
        return jsonify({
            'response': response,
            'context_used': len(relevant_context) > 0,
            'sources': len(relevant_context)
        })
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        
        # Check if it's a rate limit error from OpenAI
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
        documents = vector_store.get_all_documents()
        return jsonify({'documents': documents})
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/documents/<filename>', methods=['DELETE'])
def delete_document(filename):
    """Delete a specific document from the vector store"""
    try:
        success = vector_store.delete_document(filename)
        if success:
            return jsonify({'message': f'Document {filename} deleted successfully'})
        else:
            return jsonify({'error': 'Document not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/clear', methods=['POST'])
def clear_data():
    """Clear all uploaded documents and chat history"""
    try:
        vector_store.clear_all()
        ai_service.clear_cache()
        session.clear()
        return jsonify({'message': 'All data cleared successfully'})
    except Exception as e:
        logger.error(f"Error clearing data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        documents_count = len(vector_store.get_all_documents())
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Get rate limit status
        current_time = time.time()
        recent_requests = 0
        if client_ip in request_tracking:
            recent_requests = len([
                ts for ts in request_tracking[client_ip]
                if current_time - ts < 60
            ])
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'documents_count': documents_count,
            'rate_limit_status': {
                'requests_last_minute': recent_requests,
                'limit': 60
            }
        })
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 50MB.'}), 413

@app.errorhandler(429)
def rate_limit_handler(e):
    return jsonify({
        'error': 'Too many requests. Please wait a moment and try again.',
        'retry_after': 60
    }), 429

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)