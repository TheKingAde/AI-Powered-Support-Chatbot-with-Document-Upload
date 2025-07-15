import logging
import numpy as np
from typing import List, Dict, Any, Tuple
from sklearn.metrics.pairwise import cosine_similarity

from .ai_service import AIService

logger = logging.getLogger(__name__)

class VectorStore:
    """In-memory vector store for document embeddings and similarity search"""
    
    def __init__(self):
        """Initialize the vector store"""
        self.documents = []  # List of document chunks with metadata
        self.embeddings = []  # Corresponding embeddings matrix
        self.ai_service = None  # Will be initialized when needed
    
    def _get_ai_service(self):
        """Lazy initialization of AI service to avoid circular imports"""
        if self.ai_service is None:
            self.ai_service = AIService()
        return self.ai_service
    
    def add_documents(self, chunks: List[str], embeddings: List[List[float]], filename: str):
        """
        Add document chunks and their embeddings to the store
        
        Args:
            chunks: List of text chunks from the document
            embeddings: Corresponding embedding vectors
            filename: Name of the source file
        """
        try:
            if len(chunks) != len(embeddings):
                raise ValueError("Number of chunks and embeddings must match")
            
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                doc_metadata = {
                    'text': chunk,
                    'filename': filename,
                    'chunk_index': i,
                    'id': f"{filename}_{i}"
                }
                
                self.documents.append(doc_metadata)
                self.embeddings.append(embedding)
            
            logger.info(f"Added {len(chunks)} chunks from {filename} to vector store")
            
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {str(e)}")
            raise
    
    def search_similar(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search for documents similar to the query
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            
        Returns:
            List of similar documents with metadata and scores
        """
        try:
            if not self.documents or not self.embeddings:
                return []
            
            # Get query embedding
            ai_service = self._get_ai_service()
            query_embedding = ai_service.create_query_embedding(query)
            
            # Calculate similarities
            similarities = self._calculate_similarities(query_embedding)
            
            # Get top-k results
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # Minimum similarity threshold
                    result = self.documents[idx].copy()
                    result['similarity'] = float(similarities[idx])
                    results.append(result)
            
            logger.info(f"Found {len(results)} similar documents for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar documents: {str(e)}")
            return []
    
    def _calculate_similarities(self, query_embedding: List[float]) -> np.ndarray:
        """
        Calculate cosine similarities between query and stored embeddings
        
        Args:
            query_embedding: Query embedding vector
            
        Returns:
            Array of similarity scores
        """
        try:
            # Convert to numpy arrays
            query_vec = np.array(query_embedding).reshape(1, -1)
            embeddings_matrix = np.array(self.embeddings)
            
            # Calculate cosine similarities
            similarities = cosine_similarity(query_vec, embeddings_matrix)[0]
            
            return similarities
            
        except Exception as e:
            logger.error(f"Error calculating similarities: {str(e)}")
            return np.array([])
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        Get metadata for all stored documents
        
        Returns:
            List of document metadata grouped by filename
        """
        try:
            # Group documents by filename
            doc_groups = {}
            for doc in self.documents:
                filename = doc['filename']
                if filename not in doc_groups:
                    doc_groups[filename] = {
                        'filename': filename,
                        'chunks': 0,
                        'sample_text': ''
                    }
                
                doc_groups[filename]['chunks'] += 1
                
                # Keep first chunk as sample text
                if not doc_groups[filename]['sample_text']:
                    sample = doc['text'][:200]
                    doc_groups[filename]['sample_text'] = sample + "..." if len(doc['text']) > 200 else sample
            
            return list(doc_groups.values())
            
        except Exception as e:
            logger.error(f"Error getting documents: {str(e)}")
            return []
    
    def delete_document(self, filename: str) -> bool:
        """
        Delete all chunks from a specific document
        
        Args:
            filename: Name of the file to delete
            
        Returns:
            True if document was found and deleted, False otherwise
        """
        try:
            initial_count = len(self.documents)
            
            # Find indices of documents to remove
            indices_to_remove = []
            for i, doc in enumerate(self.documents):
                if doc['filename'] == filename:
                    indices_to_remove.append(i)
            
            if not indices_to_remove:
                logger.warning(f"Document {filename} not found in vector store")
                return False
            
            # Remove documents and embeddings in reverse order to maintain indices
            for idx in sorted(indices_to_remove, reverse=True):
                del self.documents[idx]
                del self.embeddings[idx]
            
            logger.info(f"Deleted {len(indices_to_remove)} chunks from {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {filename}: {str(e)}")
            return False
    
    def clear_all(self):
        """Clear all documents and embeddings from the store"""
        try:
            count = len(self.documents)
            self.documents.clear()
            self.embeddings.clear()
            logger.info(f"Cleared all {count} documents from vector store")
            
        except Exception as e:
            logger.error(f"Error clearing vector store: {str(e)}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store
        
        Returns:
            Dictionary with store statistics
        """
        try:
            unique_files = set(doc['filename'] for doc in self.documents)
            
            return {
                'total_chunks': len(self.documents),
                'total_files': len(unique_files),
                'files': list(unique_files),
                'embedding_dimension': len(self.embeddings[0]) if self.embeddings else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting vector store stats: {str(e)}")
            return {
                'total_chunks': 0,
                'total_files': 0,
                'files': [],
                'embedding_dimension': 0
            }