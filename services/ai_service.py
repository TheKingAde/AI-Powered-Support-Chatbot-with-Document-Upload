import os
import logging
from typing import List, Dict, Any, Optional
import openai
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIService:
    """Service for interacting with OpenAI API for embeddings and chat completion"""
    
    def __init__(self):
        """Initialize the AI service with OpenAI client"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=api_key)
        self.embedding_model = "text-embedding-ada-002"
        self.chat_model = "gpt-3.5-turbo"
        
        # Default FAQ knowledge base
        self.default_faqs = [
            {
                "question": "How do I upload documents?",
                "answer": "You can upload documents by clicking the upload area or dragging and dropping files. Supported formats include PDF, DOCX, XLSX, CSV, TXT, and images (JPG, PNG, etc.)."
            },
            {
                "question": "What file formats are supported?",
                "answer": "I support PDF, DOCX, XLSX, CSV, TXT files, and images (JPG, JPEG, PNG, GIF, BMP). For images, I use OCR to extract text content."
            },
            {
                "question": "How does the chatbot work?",
                "answer": "I analyze your uploaded documents and create embeddings to understand the content. When you ask questions, I search for relevant information from your documents and provide context-aware answers using AI."
            },
            {
                "question": "Is my data secure?",
                "answer": "Your uploaded documents are processed temporarily and stored only in memory during your session. The documents are not permanently saved on the server."
            }
        ]
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for a list of text chunks
        
        Args:
            texts: List of text chunks to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            if not texts:
                return []
            
            logger.info(f"Creating embeddings for {len(texts)} text chunks")
            
            # OpenAI API can handle multiple texts at once, but let's batch them for safety
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=batch
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            
            logger.info(f"Successfully created {len(all_embeddings)} embeddings")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            raise
    
    def create_query_embedding(self, query: str) -> List[float]:
        """
        Create embedding for a user query
        
        Args:
            query: User query text
            
        Returns:
            Embedding vector for the query
        """
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=[query]
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error creating query embedding: {str(e)}")
            raise
    
    def generate_response(
        self, 
        user_message: str, 
        context_chunks: List[Dict[str, Any]], 
        chat_history: List[Dict[str, Any]] = None
    ) -> str:
        """
        Generate AI response based on user message, context, and chat history
        
        Args:
            user_message: User's input message
            context_chunks: Relevant document chunks for context
            chat_history: Previous chat exchanges
            
        Returns:
            AI-generated response
        """
        try:
            # Build the context from relevant chunks
            context_text = ""
            if context_chunks:
                context_text = "\n\n".join([chunk['text'] for chunk in context_chunks])
                context_text = f"Relevant information from uploaded documents:\n{context_text}\n\n"
            
            # Build conversation history
            conversation_history = ""
            if chat_history:
                for exchange in chat_history[-3:]:  # Include last 3 exchanges for context
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
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            # Return fallback response
            return self._get_fallback_response(user_message)
    
    def _create_system_prompt(self, has_context: bool) -> str:
        """Create system prompt based on whether context is available"""
        base_prompt = """You are an intelligent AI assistant helping users with their questions. 
You are friendly, helpful, and provide accurate information. Keep your responses concise but comprehensive.
"""
        
        if has_context:
            return base_prompt + """
You have access to information from documents uploaded by the user. Use this information to provide 
accurate and relevant answers. If the uploaded documents don't contain relevant information for 
the user's question, let them know and offer to help with general questions or suggest they upload 
relevant documents.

Always base your answers primarily on the provided document context when available.
"""
        else:
            return base_prompt + """
The user hasn't uploaded any documents yet, so you're working with general knowledge. 
Encourage them to upload relevant documents for more specific and accurate assistance.
You can also answer general questions and help with common support inquiries.
"""
    
    def _get_fallback_response(self, user_message: str) -> str:
        """Provide fallback response when API fails"""
        # Check if the question matches any default FAQs
        user_message_lower = user_message.lower()
        
        for faq in self.default_faqs:
            if any(keyword in user_message_lower for keyword in faq["question"].lower().split()):
                return faq["answer"]
        
        return """I apologize, but I'm experiencing technical difficulties right now. 
Please try again in a moment. In the meantime, you can:

1. Upload documents to train me on your specific content
2. Ask general questions about file formats and features
3. Check if your OpenAI API key is properly configured

If the problem persists, please check the server logs for more details."""

    def get_default_faqs(self) -> List[Dict[str, str]]:
        """Get the default FAQ knowledge base"""
        return self.default_faqs