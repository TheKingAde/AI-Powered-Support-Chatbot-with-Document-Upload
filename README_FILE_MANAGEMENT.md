# Enhanced File Management System

## Overview

The backend has been enhanced with a comprehensive file management system that stores file metadata and associates it with vector embeddings. This allows users to:

- Upload files and see detailed metadata (filename, size, upload date, chunk count)
- Delete specific files by removing their chunks from the vector database
- Clear all files and start fresh
- View file statistics and system health

## Key Features

### 1. File Metadata Storage
- **File ID**: Unique UUID for each uploaded file
- **Filename**: Original filename
- **File Size**: Size in bytes
- **Upload Date**: ISO timestamp
- **File Type**: File extension (.txt, .pdf, .docx)
- **Chunk Count**: Number of text chunks created
- **Status**: File status (uploaded, processing, etc.)

### 2. Chunk Mapping System
- Each text chunk is mapped to its source file
- Chunks can be individually tracked and deleted
- Vector embeddings are associated with specific chunks

### 3. Vector Database Integration
- FAISS vector store for efficient similarity search
- Automatic rebuilding when files are deleted
- Chunk-level granularity for precise file management

## Backend Changes

### New Components

#### FileMetadataManager Class
```python
class FileMetadataManager:
    def add_file(self, filename, file_size, upload_date, chunk_count, file_type)
    def add_chunk_mapping(self, file_id, chunk_text, chunk_index)
    def get_file_metadata(self, file_id)
    def get_all_files(self)
    def delete_file(self, file_id)
    def clear_all(self)
```

#### Enhanced Endpoints

1. **GET /documents** - List all uploaded files with metadata
2. **DELETE /documents/<file_id>** - Delete specific file and its chunks
3. **POST /clear** - Clear all files and metadata
4. **GET /health** - Enhanced health check with file statistics

### File Upload Process

1. **File Processing**: Extract text from PDF, DOCX, or TXT files
2. **Text Chunking**: Split text into overlapping chunks (500 chars, 50 overlap)
3. **Metadata Storage**: Store file information in JSON file
4. **Chunk Mapping**: Create mappings between chunks and source files
5. **Vector Embedding**: Generate embeddings for each chunk
6. **Vector Storage**: Store embeddings in FAISS database

### File Deletion Process

1. **Metadata Removal**: Remove file entry from metadata
2. **Chunk Cleanup**: Remove all chunk mappings for the file
3. **Vector Rebuild**: Rebuild vector store with remaining chunks
4. **Database Cleanup**: Remove vector store if no chunks remain

## Frontend Enhancements

### Document Display
- **File Information**: Name, type, size, upload date, chunk count
- **Visual Indicators**: File type badges, size formatting
- **Delete Actions**: Individual file deletion with confirmation
- **Responsive Design**: Mobile-friendly layout

### Enhanced UI Elements
- **File Type Badges**: Color-coded file type indicators
- **Size Formatting**: Human-readable file sizes (KB, MB, GB)
- **Date Formatting**: Localized date display
- **Loading States**: Progress indicators for operations

### JavaScript Updates

#### Document Display Function
```javascript
displayDocuments(documents) {
    // Enhanced display with file metadata
    // File type badges, size formatting, date display
    // Individual delete buttons for each file
}
```

#### File Deletion Function
```javascript
async deleteDocument(fileId, filename) {
    // Delete specific file by ID
    // Show loading overlay during operation
    // Refresh document list after deletion
}
```

## API Endpoints

### Upload File
```
POST /upload
Content-Type: multipart/form-data

Response:
{
  "message": "Successfully processed 1 file(s)",
  "files": [
    {
      "filename": "document.pdf",
      "chunks": 5,
      "file_id": "uuid-here",
      "file_size": 1024000,
      "upload_date": "2025-08-01T16:34:03.257364"
    }
  ]
}
```

### List Documents
```
GET /documents

Response:
{
  "documents": [
    {
      "file_id": "uuid-here",
      "filename": "document.pdf",
      "file_size": 1024000,
      "upload_date": "2025-08-01T16:34:03.257364",
      "chunk_count": 5,
      "file_type": ".pdf",
      "status": "uploaded"
    }
  ]
}
```

### Delete Document
```
DELETE /documents/{file_id}

Response:
{
  "message": "Document document.pdf deleted successfully",
  "deleted_file": {
    "filename": "document.pdf",
    "file_size": 1024000,
    "upload_date": "2025-08-01T16:34:03.257364",
    "chunk_count": 5,
    "file_type": ".pdf",
    "status": "uploaded"
  }
}
```

### Health Check
```
GET /health

Response:
{
  "status": "healthy",
  "documents_count": 3,
  "total_chunks": 15,
  "files": ["document1.pdf", "document2.txt", "document3.docx"],
  "rate_limit_status": {
    "requests_last_minute": 10,
    "limit": 60
  }
}
```

## Data Storage

### Metadata File (`file_metadata.json`)
```json
{
  "files": {
    "file-uuid-1": {
      "filename": "document.pdf",
      "file_size": 1024000,
      "upload_date": "2025-08-01T16:34:03.257364",
      "chunk_count": 5,
      "file_type": ".pdf",
      "status": "uploaded"
    }
  },
  "chunk_mappings": {
    "0": {
      "file_id": "file-uuid-1",
      "chunk_text": "Text content...",
      "chunk_index": 0
    }
  },
  "next_chunk_id": 5
}
```

### Vector Database
- **FAISS Index**: Stored in `./vector_db/`
- **Embeddings**: 384-dimensional vectors (all-MiniLM-L6-v2)
- **Chunk Association**: Each embedding corresponds to a chunk mapping

## Installation and Setup

### Dependencies
```bash
pip install -r requirements.txt
pip install faiss-cpu python-docx
```

### Running the Application
```bash
source venv/bin/activate
python3 app.py
```

### Testing
1. **Upload Test**: Use the test page at `http://localhost:5000/test_frontend.html`
2. **API Testing**: Use curl commands for direct API testing
3. **Frontend Testing**: Access the main application at `http://localhost:5000`

## Benefits

### For Users
- **File Visibility**: See all uploaded files with detailed information
- **Selective Deletion**: Remove specific files without affecting others
- **System Transparency**: View file statistics and system health
- **Better UX**: Enhanced interface with file management capabilities

### For Developers
- **Granular Control**: Chunk-level file management
- **Data Integrity**: Proper cleanup when files are deleted
- **Scalability**: Efficient vector store management
- **Debugging**: Comprehensive logging and error handling

## Future Enhancements

1. **File Categories**: Organize files by type or tags
2. **Search Functionality**: Search through file names and content
3. **Bulk Operations**: Select and delete multiple files
4. **File Preview**: Show file content snippets
5. **Export Functionality**: Export file lists and metadata
6. **User Authentication**: Multi-user file management
7. **Storage Quotas**: Limit file storage per user

## Troubleshooting

### Common Issues

1. **FAISS Import Error**: Install `faiss-cpu` or `faiss-gpu`
2. **Memory Issues**: Large files may require more RAM
3. **Vector Store Corruption**: Delete `./vector_db/` to reset
4. **Metadata Corruption**: Delete `file_metadata.json` to reset

### Debug Commands
```bash
# Check file metadata
curl -s http://localhost:5000/documents

# Check system health
curl -s http://localhost:5000/health

# Test file upload
curl -X POST -F "files=@test.txt" http://localhost:5000/upload
```

This enhanced file management system provides a robust foundation for document-based AI applications with full user control over their uploaded content.