import os
import logging
import time
import hashlib
from typing import List, Dict, Any, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)

class AIService:
    """Service for interacting with Google Generative AI API with simplified rate limiting"""
    
    def __init__(self):
        """Initialize the AI service with Google Generative AI client"""
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        # Configure Google Generative AI
        genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Simple rate limiting - just track requests per minute
        self.request_timestamps = []
        self.max_requests_per_minute = 60  # Reasonable limit
        
        # Basic response caching
        self.response_cache = {}
        self.cache_duration = 300  # 5 minutes cache
        
        # FAQ knowledge base
        self.default_faqs = [
            {
                "keywords": ["upload", "how to upload", "upload documents"],
                "answer": "You can upload documents by clicking the upload area or dragging and dropping files. Supported formats include PDF, DOCX, XLSX, CSV, TXT, and images (JPG, PNG, etc.)."
            },
            {
                "keywords": ["file formats", "supported formats", "what formats"],
                "answer": "I support PDF, DOCX, XLSX, CSV, TXT files, and images (JPG, JPEG, PNG, GIF, BMP). For images, I use OCR to extract text content."
            },
            {
                "keywords": ["how does", "how it works", "chatbot work"],
                "answer": "I analyze your uploaded documents and create embeddings to understand the content. When you ask questions, I search for relevant information from your documents and provide context-aware answers using AI."
            },
            {
                "keywords": ["hello", "hi", "hey", "greetings"],
                "answer": "Hello! I'm your AI assistant. I can help you with questions about your uploaded documents, or answer general questions. Upload some documents to get started!"
            },
            {
                "keywords": ["help", "what can you do", "features"],
                "answer": "I can help you with: 📄 Document analysis (PDF, DOCX, XLSX, CSV, TXT, Images), 🔍 Searching content within your files, 💬 Answering questions based on your documents, 📊 Extracting insights from your data. Upload documents to get started!"
            }
        ]
    
    def _check_rate_limit(self) -> bool:
        """Simple rate limiting check - only track requests per minute"""
        current_time = time.time()
        
        # Remove timestamps older than 1 minute
        self.request_timestamps = [
            ts for ts in self.request_timestamps 
            if current_time - ts < 60
        ]
        
        return len(self.request_timestamps) < self.max_requests_per_minute
    
    def _add_request_timestamp(self):
        """Add current timestamp to track API usage"""
        self.request_timestamps.append(time.time())
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid"""
        return time.time() - timestamp < self.cache_duration
    
    def _get_fallback_response(self, user_message: str) -> Optional[str]:
        """Get response from FAQ knowledge base if available"""
        user_message_lower = user_message.lower()
        
        # Check for exact keyword matches
        for faq in self.default_faqs:
            if any(keyword.lower() in user_message_lower for keyword in faq["keywords"]):
                return faq["answer"]
        
        return None

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a list of text chunks - simplified for Google Generative AI"""
        try:
            if not texts:
                return []
            
            logger.info(f"Creating embeddings for {len(texts)} text chunks")
            
            # For now, return dummy embeddings as Google Generative AI doesn't have a direct embedding API
            # In a real implementation, you might use a different embedding service
            all_embeddings = []
            for text in texts:
                # Create a simple hash-based embedding for compatibility
                embedding = [hash(text[:100]) % 1000 / 1000.0 for _ in range(768)]
                all_embeddings.append(embedding)
            
            logger.info(f"Successfully created {len(all_embeddings)} embeddings")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            raise
    
    def create_query_embedding(self, query: str) -> List[float]:
        """Create embedding for a user query - simplified for Google Generative AI"""
        try:
            # Create a simple hash-based embedding for compatibility
            embedding = [hash(query[:100]) % 1000 / 1000.0 for _ in range(768)]
            return embedding
            
        except Exception as e:
            logger.error(f"Error creating query embedding: {str(e)}")
            raise
    
    def generate_response(
        self, 
        user_message: str, 
        context_chunks: List[Dict[str, Any]], 
        chat_history: List[Dict[str, Any]] = None
    ) -> str:
        """Generate AI response using Google Generative AI"""
        try:
            # Check cache first
            cache_key = self._get_cache_key(user_message + str(len(context_chunks)))
            if cache_key in self.response_cache:
                cached_data = self.response_cache[cache_key]
                if self._is_cache_valid(cached_data['timestamp']):
                    logger.info("Returning cached response")
                    return cached_data['response']
            
            # Try fallback response first (no API call needed)
            fallback_response = self._get_fallback_response(user_message)
            if fallback_response and not context_chunks:
                logger.info("Using fallback response")
                return fallback_response
            
            # Check rate limit
            if not self._check_rate_limit():
                logger.warning("Rate limit reached, waiting...")
                time.sleep(60)  # Wait 1 minute
            
            # Build the context from relevant chunks
            context_text = ""
            if context_chunks:
                context_text = "\n\n".join([chunk['text'] for chunk in context_chunks])
                context_text = f"Relevant information from uploaded documents:\n{context_text}\n\n"
            
            # Build conversation history
            conversation_history = ""
            if chat_history:
                for exchange in chat_history[-3:]:  # Last 3 exchanges
                    conversation_history += f"User: {exchange['user']}\nBot: {exchange['bot']}\n\n"
            
            # Create system prompt
            system_prompt = """You are a helpful AI assistant. Be concise, friendly, and accurate. 
Keep responses under 300 words when possible."""
            
            if context_chunks:
                system_prompt += """
You have access to user documents. Use this information to provide accurate answers. 
If documents don't contain relevant info, say so clearly and offer general help.
"""
            
            # Build the complete prompt
            prompt = system_prompt + "\n\n"
            
            # Add context and conversation history if available
            if conversation_history:
                prompt += f"Previous conversation:\n{conversation_history}\n"
            if context_text:
                prompt += context_text
            
            # Add current user message
            prompt += f"User: {user_message}\nBot:"
            
            # Generate response using Google Generative AI
            self._add_request_timestamp()
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=400,
                )
            )
            
            ai_response = response.text.strip()
            
            # Cache the response
            self.response_cache[cache_key] = {
                'response': ai_response,
                'timestamp': time.time()
            }
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            if "rate" in str(e).lower() or "429" in str(e):
                return "I'm experiencing high usage right now. Please try again in a moment."
            return "I apologize, but I'm experiencing technical difficulties. Please try again."
    
    def generate_simple_response(
        self, 
        user_message: str, 
        file_content: str = "",
        chat_history: List[Dict[str, Any]] = None
    ) -> str:
        """Generate AI response without chunking or embedding - simplified approach using Google Generative AI"""
        try:
            # Check cache first
            cache_key = self._get_cache_key(user_message + str(len(file_content)))
            if cache_key in self.response_cache:
                cached_data = self.response_cache[cache_key]
                if self._is_cache_valid(cached_data['timestamp']):
                    logger.info("Returning cached response")
                    return cached_data['response']
            
            # Try fallback response first (no API call needed)
            fallback_response = self._get_fallback_response(user_message)
            if fallback_response and not file_content:
                logger.info("Using fallback response")
                return fallback_response
            
            # Check rate limit
            if not self._check_rate_limit():
                logger.warning("Rate limit reached, waiting...")
                time.sleep(60)  # Wait 1 minute
            
            # Build conversation history
            conversation_history = ""
            if chat_history:
                for exchange in chat_history[-3:]:  # Last 3 exchanges
                    conversation_history += f"User: {exchange['user']}\nBot: {exchange['bot']}\n\n"
            
            # Create system prompt
            system_prompt = """You are a helpful AI assistant. Be concise, friendly, and accurate. 
Keep responses under 300 words when possible."""
            
            if file_content:
                system_prompt += """
You have access to the user's uploaded file content. Use this information to provide accurate answers. 
If the file content doesn't contain relevant info, say so clearly and offer general help.
"""
            
            # Build the complete prompt
            prompt = system_prompt + "\n\n"
            
            # Add conversation history if available
            if conversation_history:
                prompt += f"Previous conversation:\n{conversation_history}\n"
            
            # Add file content if available
            if file_content:
                prompt += f"File content:\n{file_content[:4000]}\n\n"  # Limit to 4000 chars
            
            # Add current user message
            prompt += f"User: {user_message}\nBot:"
            
            # Make API call to Google Generative AI
            self._add_request_timestamp()
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=500,
                )
            )
            
            ai_response = response.text.strip()
            
            # Cache the response
            self.response_cache[cache_key] = {
                'response': ai_response,
                'timestamp': time.time()
            }
            
            logger.info("Generated AI response successfully")
            return ai_response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"I apologize, but I'm having trouble processing your request right now. Please try again later. Error: {str(e)}"
    
    def clear_cache(self):
        """Clear response cache"""
        self.response_cache.clear()
        logger.info("Cleared response cache")