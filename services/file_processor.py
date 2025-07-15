import os
import re
import logging
from typing import List, Optional
import tempfile

import PyPDF2
import pandas as pd
from docx import Document
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

class FileProcessor:
    """Service for processing various file formats and extracting text content"""
    
    def __init__(self):
        """Initialize the file processor"""
        self.chunk_size = 1000  # Characters per chunk
        self.overlap = 200      # Character overlap between chunks
    
    def process_file(self, filepath: str) -> Optional[str]:
        """
        Process a file and extract text content based on file extension
        
        Args:
            filepath: Path to the file to process
            
        Returns:
            Extracted text content or None if processing fails
        """
        try:
            file_extension = os.path.splitext(filepath)[1].lower()
            
            if file_extension == '.pdf':
                return self._extract_from_pdf(filepath)
            elif file_extension == '.txt':
                return self._extract_from_txt(filepath)
            elif file_extension == '.docx':
                return self._extract_from_docx(filepath)
            elif file_extension in ['.xlsx', '.xls']:
                return self._extract_from_excel(filepath)
            elif file_extension == '.csv':
                return self._extract_from_csv(filepath)
            elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                return self._extract_from_image(filepath)
            else:
                logger.warning(f"Unsupported file format: {file_extension}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing file {filepath}: {str(e)}")
            return None
    
    def _extract_from_pdf(self, filepath: str) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            with open(filepath, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Error extracting from PDF: {str(e)}")
            raise
        return text.strip()
    
    def _extract_from_txt(self, filepath: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(filepath, 'r', encoding='latin-1') as file:
                return file.read()
    
    def _extract_from_docx(self, filepath: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = Document(filepath)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting from DOCX: {str(e)}")
            raise
    
    def _extract_from_excel(self, filepath: str) -> str:
        """Extract text from Excel file"""
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(filepath)
            text = ""
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(filepath, sheet_name=sheet_name)
                
                # Add sheet name as header
                text += f"Sheet: {sheet_name}\n"
                
                # Convert dataframe to string representation
                text += df.to_string(index=False, na_rep='') + "\n\n"
            
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting from Excel: {str(e)}")
            raise
    
    def _extract_from_csv(self, filepath: str) -> str:
        """Extract text from CSV file"""
        try:
            df = pd.read_csv(filepath)
            return df.to_string(index=False, na_rep='')
        except Exception as e:
            logger.error(f"Error extracting from CSV: {str(e)}")
            raise
    
    def _extract_from_image(self, filepath: str) -> str:
        """Extract text from image using OCR"""
        try:
            # Open image
            image = Image.open(filepath)
            
            # Use Tesseract OCR to extract text
            text = pytesseract.image_to_string(image)
            
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting from image: {str(e)}")
            # OCR might fail, but we shouldn't crash the entire upload
            return f"OCR extraction failed for image: {os.path.basename(filepath)}"
    
    def create_text_chunks(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks for better context preservation
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        if not text or len(text.strip()) == 0:
            return []
        
        # Clean up text
        text = self._clean_text(text)
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Find the end position for this chunk
            end = start + self.chunk_size
            
            # If we're not at the end of the text, try to break at a sentence or word boundary
            if end < len(text):
                # Look for sentence boundary (period followed by space and capital letter)
                sentence_end = text.rfind('. ', start, end)
                if sentence_end != -1 and sentence_end > start + self.chunk_size // 2:
                    end = sentence_end + 1
                else:
                    # Look for word boundary
                    word_end = text.rfind(' ', start, end)
                    if word_end != -1 and word_end > start + self.chunk_size // 2:
                        end = word_end
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = max(start + 1, end - self.overlap)
            
            # Prevent infinite loop
            if start >= len(text):
                break
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might interfere with processing
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
        
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text.strip()