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
from dotenv import load_dotenv

from services.file_processor import FileProcessor
from services.ai_service import AIService
# Note: vector_store is kept for potential future use but not used in main flow

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
# vector_store = VectorStore()  # Commented out for simplified flow

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
    """Handle file uploads - simplified without chunking and embedding"""
    try:
        # Get client IP for basic rate limiting
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Simple rate limiting check - 10 uploads per minute
        if not simple_rate_limit_check(client_ip, max_requests=10):
            return jsonify({
                'error': 'Too many uploads. Please wait a moment and try again.'
            }), 429
        
        # Check if files were uploaded
        if 'files' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        
        if not files or files[0].filename == '':
            return jsonify({'error': 'No files selected'}), 400
        
        processed_files = []
        combined_content = ""
        
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
                        # Simply store the full content
                        combined_content += f"\n\n--- Content from {file.filename} ---\n{text_content}"
                        
                        processed_files.append({
                            'filename': file.filename,
                            'processed_filename': filename,
                            'status': 'success'
                        })
                        
                        logger.info(f"Successfully processed {filename}")
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
        
        # Store combined content in session
        session['file_content'] = combined_content.strip()
        
        return jsonify({
            'message': f'Processed {len([f for f in processed_files if f["status"] == "success"])} files successfully',
            'files': processed_files
        })
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages - simplified without chunking and embedding"""
    try:
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
        
        # Get file content if available (simplified - no chunking/embedding)
        file_content = ""
        if 'file_content' in session:
            file_content = session['file_content']
        
        # Generate AI response directly with file content
        response = ai_service.generate_simple_response(
            user_message, 
            file_content,
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
            'has_file_content': bool(file_content),
            'history_length': len(session['chat_history'])
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

@app.route('/clear', methods=['POST'])
def clear_data():
    """Clear file content and chat history"""
    try:
        ai_service.clear_cache()
        session.clear()
        return jsonify({'message': 'Chat history and file content cleared successfully'})
    except Exception as e:
        logger.error(f"Error clearing data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Get current chat status"""
    try:
        return jsonify({
            'has_file_content': 'file_content' in session and bool(session['file_content']),
            'chat_history_length': len(session.get('chat_history', [])),
            'session_active': bool(session)
        })
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'file_processor': 'active',
            'ai_service': 'active'
        }
    })

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