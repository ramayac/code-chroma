"""
Singleton ChromaDB client for smart search.
Ensures only one instance of ChromaDB client exists.
"""

import os
import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import Optional, Dict, Any, List
from backend.logger import get_chroma_logger
from backend.config import config

# Set environment variable to disable telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# Monkey patch ChromaDB telemetry to prevent errors
try:
    import chromadb.telemetry.product.posthog
    original_capture = chromadb.telemetry.product.posthog.Posthog.capture
    
    def silent_capture(self, event=None, properties=None, uuid=None):
        # Do nothing - completely disable telemetry
        pass
    
    chromadb.telemetry.product.posthog.Posthog.capture = silent_capture
except (ImportError, AttributeError):
    # If the structure is different, just ignore
    pass

logger = get_chroma_logger()

class ChromaClient:
    _instance = None
    _client = None
    _db_path = None
    
    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Use config for default path if not provided
            if db_path is None:
                db_path = os.path.join(config.index_folder, "chroma_db")
            cls._db_path = Path(db_path)
            cls._db_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize ChromaDB client with telemetry disabled
            cls._client = chromadb.PersistentClient(
                path=str(cls._db_path),
                settings=Settings(anonymized_telemetry=False)
            )
            if logger:
                logger.info(f"ChromaDB client initialized at {cls._db_path}")
        return cls._instance
    
    @property
    def client(self):
        return self._client
    
    @classmethod
    def reset(cls):
        """Reset the singleton instance"""
        if cls._client:
            cls._client.reset()
        cls._instance = None
        cls._client = None
        cls._db_path = None
    
    def get_or_create_collection(self, name: str, metadata: Optional[dict] = None):
        """Get or create a collection"""
        if metadata is None:
            metadata = {"hnsw:space": "cosine"}
        return self._client.get_or_create_collection(name=name, metadata=metadata)
    
    def get_collection(self, name: str):
        """Get an existing collection"""
        return self._client.get_collection(name)
    
    @staticmethod
    def format_repository_info(metadata: Any, document: Optional[str] = None, include_path: bool = True) -> Dict[str, Any]:
        """
        Format repository metadata into a standardized dictionary.
        
        Args:
            metadata: Repository metadata from ChromaDB
            document: Optional document content (description)
            include_path: Whether to include the path field
            
        Returns:
            Formatted repository information
        """
        repo_info = {
            'name': metadata.get('repo_name', 'Unknown'),
            'language': metadata.get('language', 'Unknown'),
            'file_count': metadata.get('file_count', 0),
            'indexed_at': metadata.get('indexed_at', ''),
        }
        
        # Add optional fields
        if 'total_files' in metadata:
            repo_info['total_files'] = metadata['total_files']
        
        if document is not None:
            repo_info['description'] = document
        
        if include_path and 'path' in metadata:
            repo_info['path'] = metadata['path']
            
        return repo_info
    
    @staticmethod
    def format_file_info(metadata: Any, document: Optional[str] = None, preview_length: int = 200) -> Dict[str, Any]:
        """
        Format file metadata into a standardized dictionary.
        
        Args:
            metadata: File metadata from ChromaDB
            document: Optional document content
            preview_length: Length of content preview
            
        Returns:
            Formatted file information
        """
        file_info = {
            'file_path': metadata.get('file_path', 'Unknown'),
            'file_name': metadata.get('file_name', 'Unknown'),
            'language': metadata.get('language', 'Unknown'),
            'size': metadata.get('size', 0),
        }
        
        if document is not None:
            if len(document) > preview_length:
                file_info['content_preview'] = document[:preview_length] + "..."
            else:
                file_info['content_preview'] = document
                
        return file_info
    
    @staticmethod
    def format_chunk_info(metadata: Any, document: Optional[str] = None) -> Dict[str, Any]:
        """
        Format chunk metadata into a standardized dictionary.
        
        Args:
            metadata: Chunk metadata from ChromaDB
            document: Optional document content
            
        Returns:
            Formatted chunk information
        """
        chunk_info = {
            'repo_name': metadata.get('repo_name', 'Unknown'),
            'file_path': metadata.get('file_path', 'Unknown'),
            'file_name': metadata.get('file_name', 'Unknown'),
            'chunk_id': metadata.get('chunk_id', 0),
            'chunk_type': metadata.get('chunk_type', 'text'),
            'language': metadata.get('language', 'Unknown'),
            'file_type': metadata.get('file_type', 'unknown'),
        }
        
        if document is not None:
            chunk_info['content'] = document
            
        return chunk_info
    
    @staticmethod
    def batch_format_repositories(results: Any, include_description: bool = True, 
                                 description_max_length: int = 100) -> List[Dict[str, Any]]:
        """
        Batch format repository results from ChromaDB query.
        
        Args:
            results: Results from ChromaDB query
            include_description: Whether to include description field
            description_max_length: Maximum length for description preview
            
        Returns:
            List of formatted repository information
        """
        repos = []
        if not results.get('documents'):
            return repos
            
        for i, doc in enumerate(results['documents']):
            metadata = results['metadatas'][i]
            repo_info = ChromaClient.format_repository_info(metadata, include_path=True)
            
            if include_description:
                if len(doc) > description_max_length:
                    repo_info['description'] = doc[:description_max_length] + "..."
                else:
                    repo_info['description'] = doc
                    
            repos.append(repo_info)
            
        return repos
    
    @staticmethod
    def batch_format_files(results: Any, preview_length: int = 200) -> List[Dict[str, Any]]:
        """
        Batch format file results from ChromaDB query.
        
        Args:
            results: Results from ChromaDB query
            preview_length: Length of content preview
            
        Returns:
            List of formatted file information
        """
        files = []
        if not results.get('documents'):
            return files
            
        for i, doc in enumerate(results['documents']):
            metadata = results['metadatas'][i]
            file_info = ChromaClient.format_file_info(metadata, doc, preview_length)
            files.append(file_info)
            
        return files
