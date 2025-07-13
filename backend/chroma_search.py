"""
ChromaDB search functionality for smart search.
Provides semantic search across repositories, files, and chunks.
"""

import os
import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.logger import get_logger
from backend.chroma_client import ChromaClient
from backend.config import config

logger = get_logger()

class ChromaSearch:
    def __init__(self, db_path: Optional[str] = None):
        try:
            # Use config for default path if not provided
            if db_path is None:
                db_path = os.path.join(config.index_folder, "chroma_db")
            
            # Use singleton client
            self.chroma_client = ChromaClient(db_path)
            
            # Use get_or_create_collection to avoid errors if collections don't exist
            self.repos_collection = self.chroma_client.get_or_create_collection("repositories")
            self.files_collection = self.chroma_client.get_or_create_collection("files")
            self.chunks_collection = self.chroma_client.get_or_create_collection("chunks")
            
        except Exception as e:
            logger.error(f"Error initializing ChromaSearch: {e}")
            raise
    
    def search_repositories(self, query: str, limit: int = 10, min_score: Optional[float] = None) -> List[Dict]:
        """Search repositories by semantic similarity"""
        try:
            results = self.repos_collection.query(
                query_texts=[query],
                n_results=min(limit, self.repos_collection.count())
            )
            
            return self._format_results(results, "repository", min_score)
        except Exception as e:
            logger.error(f"Error searching repositories: {e}")
            return []
    
    def search_files(self, query: str, repo_name: Optional[str] = None, limit: int = 10, min_score: Optional[float] = None) -> List[Dict]:
        """Search files, optionally filtered by repository"""
        try:
            where_clause = {}
            if repo_name:
                where_clause["repo_name"] = repo_name
            
            collection_count = self.files_collection.count()
            if collection_count == 0:
                return []
            
            results = self.files_collection.query(
                query_texts=[query],
                n_results=min(limit, collection_count),
                where=where_clause if where_clause else None
            )
            
            return self._format_results(results, "file", min_score)
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return []
    
    def search_chunks(self, query: str, repo_name: Optional[str] = None, language: Optional[str] = None, limit: int = 10, min_score: Optional[float] = None) -> List[Dict]:
        """Search chunks with optional filters"""
        try:
            where_clause = {"type": "chunk"}
            if repo_name:
                where_clause["repo_name"] = repo_name
            if language:
                where_clause["language"] = language
            
            results = self.chunks_collection.query(
                query_texts=[query],
                n_results=min(limit, self.chunks_collection.count()),
                where=where_clause
            )
            
            return self._format_results(results, "chunk", min_score)
        except Exception as e:
            logger.error(f"Error searching chunks: {e}")
            return []
    
    def search_all(self, query: str, limit: int = 5, min_score: Optional[float] = None) -> Dict[str, List[Dict]]:
        """Search across all collections"""
        return {
            "repositories": self.search_repositories(query, limit, min_score),
            "files": self.search_files(query, limit=limit, min_score=min_score),
            "chunks": self.search_chunks(query, limit=limit, min_score=min_score)
        }
    
    def get_repo_info(self, repo_name: str) -> Optional[Dict]:
        """Get detailed information about a specific repository"""
        try:
            results = self.repos_collection.get(
                where={"repo_name": repo_name}
            )
            
            if results['documents']:
                metadata = results['metadatas'][0]
                return self.chroma_client.format_repository_info(
                    metadata, 
                    document=results['documents'][0], 
                    include_path=True
                )
            return None
        except Exception as e:
            logger.error(f"Error getting repo info for {repo_name}: {e}")
            return None
    
    def get_repo_files(self, repo_name: str, limit: int = 50) -> List[Dict]:
        """Get all files for a specific repository"""
        try:
            results = self.files_collection.get(
                where={"repo_name": repo_name},
                limit=limit
            )
            
            return self.chroma_client.batch_format_files(results, preview_length=200)
        except Exception as e:
            logger.error(f"Error getting files for repo {repo_name}: {e}")
            return []
    
    def find_similar_code(self, query: str, language: Optional[str] = None, limit: int = 10, min_score: Optional[float] = None) -> List[Dict]:
        """Find similar code chunks"""
        try:
            where_clause = {"type": "chunk"}
            if language:
                where_clause["language"] = language
            
            results = self.chunks_collection.query(
                query_texts=[query],
                n_results=min(limit, self.chunks_collection.count()),
                where=where_clause
            )
            
            return self._format_results(results, "chunk", min_score)
        except Exception as e:
            logger.error(f"Error finding similar code: {e}")
            return []
    
    def get_languages(self) -> List[str]:
        """Get all available programming languages"""
        try:
            # Get unique languages from files collection
            results = self.files_collection.get()
            languages = set()
            
            for metadata in results['metadatas']:
                if metadata.get('language'):
                    languages.add(metadata['language'])
            
            return sorted(list(languages))
        except Exception as e:
            logger.error(f"Error getting languages: {e}")
            return []
    
    def get_repositories_list(self) -> List[str]:
        """Get list of all repository names"""
        try:
            results = self.repos_collection.get()
            repo_names = []
            
            for metadata in results['metadatas']:
                repo_names.append(metadata['repo_name'])
            
            return sorted(repo_names)
        except Exception as e:
            logger.error(f"Error getting repositories list: {e}")
            return []
    
    def _format_results(self, results: Any, result_type: str, min_score: Optional[float] = None) -> List[Dict]:
        """Format ChromaDB results and filter by minimum search score"""
        formatted = []
        
        if not results['documents']:
            return formatted
        
        # Get minimum search threshold from config or parameter
        min_search_score = min_score if min_score is not None else config.min_search
        
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i] if 'distances' in results else 0
            similarity = 1 - distance  # Convert distance to similarity
            
            # Filter out results below minimum search score
            if similarity < min_search_score:
                continue
            
            formatted_result = {
                'content': doc,
                'metadata': metadata,
                'distance': distance,
                'similarity': similarity,
                'type': result_type
            }
            
            # Add type-specific formatting
            if result_type == "repository":
                formatted_result['display_name'] = metadata.get('repo_name', 'Unknown')
                formatted_result['summary'] = f"{metadata.get('language', 'Unknown')} project with {metadata.get('file_count', 0)} files"
            
            elif result_type == "file":
                formatted_result['display_name'] = f"{metadata.get('repo_name', 'Unknown')}/{metadata.get('file_path', 'Unknown')}"
                formatted_result['summary'] = f"{metadata.get('language', 'Unknown')} file ({metadata.get('size', 0)} chars)"
            
            elif result_type == "chunk":
                formatted_result['display_name'] = f"{metadata.get('repo_name', 'Unknown')}/{metadata.get('file_path', 'Unknown')} (chunk {metadata.get('chunk_id', 0)})"
                formatted_result['summary'] = f"{metadata.get('language', 'Unknown')} {metadata.get('chunk_type', 'text')}"
            
            formatted.append(formatted_result)
        
        return formatted
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about all collections"""
        try:
            return {
                'repositories': self.repos_collection.count(),
                'files': self.files_collection.count(),
                'chunks': self.chunks_collection.count(),
                'languages': len(self.get_languages()),
                'repo_names': self.get_repositories_list()
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {'error': str(e)}
    
    def inspect_collection(self, collection_name: str, limit: int = 10) -> Dict:
        """Inspect a specific collection for debugging"""
        try:
            collection_map = {
                'repositories': self.repos_collection,
                'files': self.files_collection,
                'chunks': self.chunks_collection
            }
            
            if collection_name not in collection_map:
                return {'error': f"Collection '{collection_name}' not found"}
            
            collection = collection_map[collection_name]
            results = collection.get(limit=limit)
            
            return {
                'collection': collection_name,
                'total_count': collection.count(),
                'sample_size': len(results['documents']),
                'sample_data': [
                    {
                        'id': results['ids'][i],
                        'document_preview': results['documents'][i][:200] + "..." if len(results['documents'][i]) > 200 else results['documents'][i],
                        'metadata': results['metadatas'][i]
                    }
                    for i in range(min(limit, len(results['documents'])))
                ]
            }
        except Exception as e:
            logger.error(f"Error inspecting collection {collection_name}: {e}")
            return {'error': str(e)}
