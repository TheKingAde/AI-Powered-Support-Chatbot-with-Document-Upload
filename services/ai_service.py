import os
import logging
import time
import hashlib
from typing import List, Dict, Any, Optional
import openai
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIService:
    """Service for interacting with OpenAI API with rate limiting and caching"""
    
    def __init__(self):
        """Initialize the AI service with OpenAI client and rate limiting"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=api_key)
        self.embedding_model = "text-embedding-ada-002"
        self.chat_model = "gpt-3.5-turbo"
        
        # Rate limiting (adjust for free plan - 3 requests per minute)
        self.max_requests_per_minute = 3
        self.request_timestamps = []
        
        # Response caching
        self.response_cache = {}
        self.cache_duration = 3600  # 1 hour cache
        
        # Embedding cache to avoid re-computing for same queries
        self.embedding_cache = {}
        
        # Enhanced FAQ knowledge base with more responses
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
                "keywords": ["secure", "security", "data safe", "privacy"],
                "answer": "Your uploaded documents are processed temporarily and stored only in memory during your session. The documents are not permanently saved on the server."
            },
            {
                "keywords": ["hello", "hi", "hey", "greetings"],
                "answer": "Hello! I'm your AI assistant. I can help you with questions about your uploaded documents, or answer general questions. Upload some documents to get started!"
            },
            {
                "keywords": ["help", "what can you do", "features"],
                "answer": "I can help you with: 📄 Document analysis (PDF, DOCX, XLSX, CSV, TXT, Images), 🔍 Searching content within your files, 💬 Answering questions based on your documents, 📊 Extracting insights from your data. Upload documents to get started!"
            },
            {
                "keywords": ["error", "not working", "problem"],
                "answer": "If you're experiencing issues, try: 1) Refreshing the page, 2) Checking your internet connection, 3) Ensuring your files are in supported formats, 4) Trying with smaller files. If problems persist, the system may be experiencing high load."
            },
            {
                "keywords": ["thank", "thanks", "appreciate"],
                "answer": "You're welcome! I'm here to help. Feel free to ask any questions about your documents or anything else I can assist with."
            }
        ]
    
    def _check_rate_limit(self) -> bool:
        """Check if we can make an API request without hitting rate limits"""
        current_time = time.time()
        
        # Remove timestamps older than 1 minute
        self.request_timestamps = [
            ts for ts in self.request_timestamps 
            if current_time - ts < 60
        ]
        
        # Check if we've hit the rate limit
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            return False
        
        return True
    
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
        
        # If no documents uploaded, provide helpful guidance
        if not hasattr(self, '_has_documents') or not self._has_documents:
            if len(user_message.split()) > 3:  # Complex question without documents
                return """I don't have any documents to reference yet. To get the most accurate answers:

1. Upload relevant documents using the upload area above
2. Wait for them to be processed 
3. Ask your question again

I can also answer general questions about how to use this system or provide basic information."""

        return None

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a list of text chunks with rate limiting"""
        try:
            if not texts:
                return []
            
            # Check rate limit before making API calls
            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded for embeddings - using fallback")
                # Return dummy embeddings or cache if available
                return [[0.0] * 1536 for _ in texts]  # OpenAI ada-002 dimension
            
            logger.info(f"Creating embeddings for {len(texts)} text chunks")
            
            # Check cache for each text
            cached_embeddings = []
            uncached_texts = []
            uncached_indices = []
            
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if cache_key in self.embedding_cache:
                    cached_data = self.embedding_cache[cache_key]
                    if self._is_cache_valid(cached_data['timestamp']):
                        cached_embeddings.append((i, cached_data['embedding']))
                        continue
                
                uncached_texts.append(text)
                uncached_indices.append(i)
            
            # Create embeddings for uncached texts
            all_embeddings = [None] * len(texts)
            
            # Fill in cached embeddings
            for idx, embedding in cached_embeddings:
                all_embeddings[idx] = embedding
            
            # Process uncached texts in smaller batches
            if uncached_texts:
                batch_size = 50  # Smaller batches for free plan
                
                for i in range(0, len(uncached_texts), batch_size):
                    batch = uncached_texts[i:i + batch_size]
                    batch_indices = uncached_indices[i:i + batch_size]
                    
                    self._add_request_timestamp()
                    response = self.client.embeddings.create(
                        model=self.embedding_model,
                        input=batch
                    )
                    
                    batch_embeddings = [item.embedding for item in response.data]
                    
                    # Cache and store embeddings
                    for j, embedding in enumerate(batch_embeddings):
                        original_idx = batch_indices[j]
                        all_embeddings[original_idx] = embedding
                        
                        # Cache the embedding
                        cache_key = self._get_cache_key(batch[j])
                        self.embedding_cache[cache_key] = {
                            'embedding': embedding,
                            'timestamp': time.time()
                        }
            
            logger.info(f"Successfully created {len(all_embeddings)} embeddings")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            # Return dummy embeddings to prevent system failure
            return [[0.0] * 1536 for _ in texts]
    
    def create_query_embedding(self, query: str) -> List[float]:
        """Create embedding for a user query with caching"""
        try:
            # Check cache first
            cache_key = self._get_cache_key(query)
            if cache_key in self.embedding_cache:
                cached_data = self.embedding_cache[cache_key]
                if self._is_cache_valid(cached_data['timestamp']):
                    return cached_data['embedding']
            
            # Check rate limit
            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded for query embedding")
                return [0.0] * 1536  # Return dummy embedding
            
            self._add_request_timestamp()
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=[query]
            )
            
            embedding = response.data[0].embedding
            
            # Cache the result
            self.embedding_cache[cache_key] = {
                'embedding': embedding,
                'timestamp': time.time()
            }
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error creating query embedding: {str(e)}")
            return [0.0] * 1536  # Return dummy embedding
    
    def generate_response(
        self, 
        user_message: str, 
        context_chunks: List[Dict[str, Any]], 
        chat_history: List[Dict[str, Any]] = None
    ) -> str:
        """Generate AI response with improved rate limiting and fallback"""
        try:
            # Set document availability flag
            self._has_documents = len(context_chunks) > 0
            
            # Check cache first
            cache_key = self._get_cache_key(user_message + str(len(context_chunks)))
            if cache_key in self.response_cache:
                cached_data = self.response_cache[cache_key]
                if self._is_cache_valid(cached_data['timestamp']):
                    logger.info("Returning cached response")
                    return cached_data['response']
            
            # Try fallback response first (no API call needed)
            fallback_response = self._get_fallback_response(user_message)
            if fallback_response:
                logger.info("Using fallback response")
                return fallback_response
            
            # Check rate limit before making API call
            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded - using enhanced fallback")
                return self._get_rate_limit_fallback(user_message, context_chunks)
            
            # Build the context from relevant chunks
            context_text = ""
            if context_chunks:
                context_text = "\n\n".join([chunk['text'] for chunk in context_chunks])
                context_text = f"Relevant information from uploaded documents:\n{context_text}\n\n"
            
            # Build conversation history (keep it shorter for free plan)
            conversation_history = ""
            if chat_history:
                for exchange in chat_history[-2:]:  # Only last 2 exchanges to save tokens
                    conversation_history += f"User: {exchange['user']}\nBot: {exchange['bot']}\n\n"
            
            # Create system prompt
            system_prompt = self._create_system_prompt(bool(context_chunks))
            
            # Build messages for the API
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add context and conversation history if available
            if context_text or conversation_history:
                context_message = ""
                if conversation_history:
                    context_message += f"Previous conversation:\n{conversation_history}"
                if context_text:
                    context_message += context_text
                
                messages.append({"role": "user", "content": context_message})
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Generate response
            self._add_request_timestamp()
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                max_tokens=300,  # Reduced for free plan
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Cache the response
            self.response_cache[cache_key] = {
                'response': ai_response,
                'timestamp': time.time()
            }
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return self._get_error_fallback(user_message, str(e))
    
    def _get_rate_limit_fallback(self, user_message: str, context_chunks: List[Dict[str, Any]]) -> str:
        """Enhanced fallback when rate limited"""
        if context_chunks:
            # Simple keyword matching in context
            message_lower = user_message.lower()
            relevant_text = ""
            
            for chunk in context_chunks[:2]:  # Check first 2 chunks
                chunk_text = chunk.get('text', '').lower()
                if any(word in chunk_text for word in message_lower.split() if len(word) > 3):
                    relevant_text = chunk.get('text', '')[:200] + "..."
                    break
            
            if relevant_text:
                return f"Based on your documents: {relevant_text}\n\n⚠️ I'm currently experiencing high load. For more detailed responses, please try again in a moment."
        
        return """⚠️ I'm experiencing high usage right now. Here's what you can do:

1. **Try again in a minute** - I'll have more capacity then
2. **Ask simpler questions** - I can handle basic queries better during high load
3. **Upload documents** - This helps me provide more relevant answers

I appreciate your patience! 🙏"""
    
    def _get_error_fallback(self, user_message: str, error: str) -> str:
        """Fallback response for API errors"""
        if "rate" in error.lower() or "429" in error:
            return self._get_rate_limit_fallback(user_message, [])
        
        return """I apologize, but I'm experiencing technical difficulties right now. 

**Quick fixes you can try:**
- Refresh the page and try again
- Ask a simpler question
- Upload documents for better context

**Common questions I can help with:**
- How to upload documents
- Supported file formats  
- How the chatbot works
- Data security information

If the problem persists, please check back in a few minutes! 🔧"""

    def _create_system_prompt(self, has_context: bool) -> str:
        """Create system prompt based on whether context is available"""
        base_prompt = """You are a helpful AI assistant. Be concise, friendly, and accurate. 
Keep responses under 200 words when possible."""
        
        if has_context:
            return base_prompt + """
You have access to user documents. Use this information to provide accurate answers. 
If documents don't contain relevant info, say so clearly and offer general help.
"""
        else:
            return base_prompt + """
The user hasn't uploaded documents yet. Encourage document upload for specific questions.
Answer general questions about the system and provide helpful guidance.
"""
    
    def get_default_faqs(self) -> List[Dict[str, str]]:
        """Get the default FAQ knowledge base"""
        return [{"question": faq["keywords"][0], "answer": faq["answer"]} for faq in self.default_faqs]
    
    def clear_cache(self):
        """Clear all caches"""
        self.response_cache.clear()
        self.embedding_cache.clear()
        logger.info("Cleared all caches")