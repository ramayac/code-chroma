"""
ChromaDB integration for smart search indexing.
Provides lightweight vector database functionality for fast iteration.
"""

import chromadb
from chromadb.config import Settings
import os
import sys
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
import json
from datetime import datetime
from backend.logger import get_logger
from backend.chroma_client import ChromaClient
from backend.config import config

logger = get_logger()

class ChromaIndexer:
    def __init__(self, db_path: Optional[str] = None):
        # Use config for default path if not provided
        if db_path is None:
            db_path = os.path.join(config.index_folder, "chroma_db")
        
        # Use singleton client
        self.chroma_client = ChromaClient(db_path)
        
        # Create collections
        self.files_collection = self.chroma_client.get_or_create_collection(
            name="files",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.chunks_collection = self.chroma_client.get_or_create_collection(
            name="chunks",
            metadata={"hnsw:space": "cosine"}
        )
    
    def index_repository(self, repo_path: str, repo_name: Optional[str] = None):
        """Index a single repository"""
        repo_path_obj = Path(repo_path)
        if not repo_name:
            repo_name = repo_path_obj.name
        
        # Index individual files and chunks
        self._index_files_and_chunks(repo_path_obj, repo_name)
    
    def _index_files_and_chunks(self, repo_path: Path, repo_name: str):
        """Index individual files and their chunks with progress tracking"""
        # Use configuration from config.json
        indexer_config = {
            'source_folder': str(repo_path),
            'supported_extensions': config.supported_extensions,
            'chunk_size': config.chunk_size,
            'chunk_overlap': config.chunk_overlap,
            'ignore_patterns': config.ignore_patterns
        }
        
        try:
            # Load files directly
            raw_docs = self._load_files(repo_path, indexer_config)
            if not raw_docs:
                logger.warning(f"No files found in {repo_path}")
                return

            # Temporarily suppress ChromaDB logging for cleaner output
            chromadb_logger = logging.getLogger('chromadb')
            original_level = chromadb_logger.level
            chromadb_logger.setLevel(logging.ERROR)
            
            # Also suppress the root logger temporarily
            root_logger = logging.getLogger()
            original_root_level = root_logger.level
            root_logger.setLevel(logging.ERROR)
            
            # Suppress console output from ChromaDB completely
            import sys
            original_stderr = sys.stderr
            from io import StringIO
            sys.stderr = StringIO()
            
            try:
                # Index files with progress tracking and get change info
                changed_files, unchanged_files = self._index_files_with_progress(raw_docs, repo_name)

                # Only process chunks for changed files
                if changed_files:
                    changed_chunks = self._chunk_documents(changed_files, indexer_config)
                    self._index_chunks_with_progress(changed_chunks, repo_name, changed_files)
                else:
                    print("Chunks: [=] (no changes to process)")
                
                # Show final summary
                total_chunks = len(self._chunk_documents(raw_docs, indexer_config)) if raw_docs else 0
                changed_chunk_count = len(self._chunk_documents(changed_files, indexer_config)) if changed_files else 0
                print(f"Summary: {len(raw_docs)} files ({len(changed_files)} changed) → {total_chunks} chunks ({changed_chunk_count} processed)")
            finally:
                # Restore all logging and output
                sys.stderr = original_stderr
                chromadb_logger.setLevel(original_level)
                root_logger.setLevel(original_root_level)

        except Exception as e:
            logger.error(f"Error indexing files and chunks: {e}")
            # Restore logging level in case of error
            logging.getLogger('chromadb').setLevel(logging.WARNING)
    
    def _index_files_with_progress(self, raw_docs: List[Dict], repo_name: str) -> Tuple[List[Dict], List[Dict]]:
        """Index file summaries with progress tracking and return changed/unchanged files"""
        # Get existing files metadata for this repo
        existing_files_metadata = self._get_existing_files_metadata(repo_name)
        existing_file_ids = set(existing_files_metadata.keys())
        
        # Process new files
        new_file_ids = set()
        documents = []
        metadatas = []
        ids = []
        
        # Track changed and unchanged files
        changed_files = []
        unchanged_files = []
        
        # Progress tracking
        added = modified = unchanged = 0
        
        # Show progress header
        print(f"Files: [", end="", flush=True)
        
        for i, doc in enumerate(raw_docs):
            try:
                content = doc.get('content', '')
                if not content:
                    continue
                    
                relative_path = doc.get('relative_path', doc['filename'])
                file_id = f"file_{repo_name}_{relative_path}".replace("/", "_").replace("\\", "_").replace(".", "_")
                new_file_ids.add(file_id)
                
                # Get current file path for metadata comparison
                current_file_path = Path(doc['filename'])
                
                # Determine operation type and track changes
                is_changed = False
                if file_id in existing_file_ids:
                    # Use improved change detection
                    existing_metadata = existing_files_metadata.get(file_id, {})
                    if self._has_file_changed(current_file_path, existing_metadata):
                        modified += 1
                        symbol = "*"  # Modified
                        is_changed = True
                    else:
                        unchanged += 1
                        symbol = "="  # Unchanged
                        is_changed = False
                else:
                    added += 1
                    symbol = "+"  # Added
                    is_changed = True
                
                # Track file status
                if is_changed:
                    changed_files.append(doc)
                else:
                    unchanged_files.append(doc)
                
                print(symbol, end="", flush=True)
                
                # Truncate content for file-level indexing
                file_content = content[:5000] + "..." if len(content) > 5000 else content
                
                # Get file metadata for storage
                file_metadata = self._get_file_metadata(current_file_path)
                
                documents.append(file_content)
                metadatas.append({
                    'repo_name': repo_name,
                    'file_path': relative_path,
                    'file_name': os.path.basename(doc['filename']),
                    'language': self._detect_language(Path(doc['filename']).suffix),
                    'file_type': doc.get('file_type', 'unknown'),
                    'size': file_metadata['size'],
                    'mtime': file_metadata['mtime'],
                    'hash': file_metadata['hash'],
                    'type': 'file'
                })
                ids.append(file_id)
                
            except Exception as e:
                print("!", end="", flush=True)  # Error symbol
                logger.error(f"Error processing file {doc.get('filename', 'unknown')}: {e}")
                continue
        
        # Find deleted files
        deleted_files = existing_file_ids - new_file_ids
        if deleted_files:
            for _ in deleted_files:
                print("-", end="", flush=True)
        
        print("] ", end="", flush=True)
        
        if documents:
            try:
                # Remove existing files for this repo
                try:
                    existing_file_results = self.files_collection.get(where={"repo_name": repo_name})
                    if existing_file_results and existing_file_results.get('ids'):
                        self.files_collection.delete(ids=existing_file_results['ids'])
                except Exception as e:
                    logger.debug(f"No existing files to delete for {repo_name}: {e}")
                
                # Add new files
                self.files_collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                print(f"({len(documents)} files: +{added} *{modified} ={unchanged} -{len(deleted_files)})")
            except Exception as e:
                logger.error(f"Error adding files to collection: {e}")
        else:
            print("(no files to index)")
        
        return changed_files, unchanged_files

    def _get_existing_files_data(self, repo_name: str) -> Dict[str, str]:
        """Get existing file data for a repository (legacy method - kept for compatibility)"""
        try:
            existing_files = self.files_collection.get(where={"repo_name": repo_name})
            result = {}
            if existing_files and existing_files.get('ids'):
                documents = existing_files.get('documents')
                for i, file_id in enumerate(existing_files['ids']):
                    content = documents[i] if documents and i < len(documents) else ''
                    result[file_id] = content
            return result
        except Exception:
            return {}

    def _index_files(self, raw_docs: List[Dict], repo_name: str):
        """Index file summaries"""
        documents = []
        metadatas = []
        ids = []
        
        for doc in raw_docs:
            try:
                content = doc.get('content', '')
                if not content:
                    continue
                    
                if len(content) > 5000:  # Truncate very large files for file-level indexing
                    content = content[:5000] + "..."
                
                relative_path = doc.get('relative_path', doc['filename'])
                file_id = f"file_{repo_name}_{relative_path}".replace("/", "_").replace("\\", "_").replace(".", "_")
                
                documents.append(content)
                metadatas.append({
                    'repo_name': repo_name,
                    'file_path': relative_path,
                    'file_name': os.path.basename(doc['filename']),
                    'language': self._detect_language(Path(doc['filename']).suffix),
                    'file_type': doc.get('file_type', 'unknown'),
                    'size': len(content),
                    'type': 'file'
                })
                ids.append(file_id)
                
            except Exception as e:
                logger.error(f"Error processing file {doc.get('filename', 'unknown')}: {e}")
                continue
        
        if documents:
            try:
                # Remove existing files for this repo
                try:
                    existing_files = self.files_collection.get(where={"repo_name": repo_name})
                    if existing_files and existing_files.get('ids'):
                        self.files_collection.delete(ids=existing_files['ids'])
                except Exception as e:
                    logger.debug(f"No existing files to delete for {repo_name}: {e}")
                
                # Add new files
                self.files_collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"✅ Indexed {len(documents)} files")
            except Exception as e:
                logger.error(f"Error adding files to collection: {e}")
    
    def _index_chunks_with_progress(self, chunks: List[Dict], repo_name: str, changed_files: Optional[List[Dict]] = None):
        """Index document chunks with progress tracking, only for changed files"""
        if not chunks:
            print("Chunks: [=] (no chunks to process)")
            return
            
        # Get existing chunks for this repo
        existing_chunks = self._get_existing_chunk_ids(repo_name)
        
        # If we have changed_files list, only delete chunks for those files
        if changed_files:
            changed_file_paths = {doc.get('relative_path', doc['filename']) for doc in changed_files}
            chunks_to_delete = []
            
            # Get all existing chunks and filter by changed files
            try:
                existing_chunk_results = self.chunks_collection.get(where={"repo_name": repo_name})
                if existing_chunk_results and existing_chunk_results.get('ids'):
                    metadatas = existing_chunk_results.get('metadatas')
                    for i, chunk_id in enumerate(existing_chunk_results['ids']):
                        if metadatas and i < len(metadatas):
                            metadata = metadatas[i]
                            file_path = metadata.get('file_path', '')
                            if file_path in changed_file_paths:
                                chunks_to_delete.append(chunk_id)
                    
                    if chunks_to_delete:
                        self.chunks_collection.delete(ids=chunks_to_delete)
            except Exception as e:
                logger.debug(f"No existing chunks to delete for changed files: {e}")
        else:
            # Delete all chunks for this repo (fallback behavior)
            try:
                existing_chunk_results = self.chunks_collection.get(where={"repo_name": repo_name})
                if existing_chunk_results and existing_chunk_results.get('ids'):
                    self.chunks_collection.delete(ids=existing_chunk_results['ids'])
            except Exception as e:
                logger.debug(f"No existing chunks to delete for {repo_name}: {e}")
        
        # Process new chunks
        new_chunk_ids = set()
        documents = []
        metadatas = []
        ids = []
        
        # Progress tracking
        added = modified = unchanged = 0
        
        # Show progress header
        print(f"Chunks: [", end="", flush=True)
        
        # Process chunks in groups to avoid overwhelming the console
        group_size = max(1, len(chunks) // 50)  # Show up to 50 symbols max
        for i, chunk in enumerate(chunks):
            try:
                relative_path = chunk.get('relative_path', chunk['filename'])
                chunk_id = f"chunk_{repo_name}_{relative_path}_{chunk.get('chunk_index', 0)}".replace("/", "_").replace("\\", "_").replace(".", "_")
                new_chunk_ids.add(chunk_id)
                
                # Determine operation type
                if chunk_id in existing_chunks:
                    modified += 1
                    symbol = "*"  # Modified
                else:
                    added += 1
                    symbol = "+"  # Added
                
                # Only show symbol every group_size chunks
                if i % group_size == 0 or i == len(chunks) - 1:
                    print(symbol, end="", flush=True)
                
                documents.append(chunk['content'])
                metadatas.append({
                    'repo_name': repo_name,
                    'file_path': relative_path,
                    'file_name': os.path.basename(chunk['filename']),
                    'chunk_id': chunk.get('chunk_index', 0),
                    'chunk_type': chunk.get('chunk_type', 'text'),
                    'language': self._detect_language(Path(chunk['filename']).suffix),
                    'file_type': chunk.get('file_type', 'unknown'),
                    'type': 'chunk'
                })
                ids.append(chunk_id)
                
            except Exception as e:
                print("!", end="", flush=True)  # Error symbol
                logger.error(f"Error processing chunk: {e}")
                continue
        
        # Find deleted chunks
        deleted_chunks = existing_chunks - new_chunk_ids
        if deleted_chunks:
            print("-" * min(len(deleted_chunks), 5), end="", flush=True)
        
        print("] ", end="", flush=True)
        
        if documents:
            try:
                # Remove existing chunks for this repo
                try:
                    existing_chunk_results = self.chunks_collection.get(where={"repo_name": repo_name})
                    if existing_chunk_results and existing_chunk_results.get('ids'):
                        self.chunks_collection.delete(ids=existing_chunk_results['ids'])
                except Exception as e:
                    logger.debug(f"No existing chunks to delete for {repo_name}: {e}")
                
                # Add new chunks in batches
                batch_size = config.batch_size
                for i in range(0, len(documents), batch_size):
                    batch_docs = documents[i:i + batch_size]
                    batch_metas = metadatas[i:i + batch_size]
                    batch_ids = ids[i:i + batch_size]
                    
                    self.chunks_collection.add(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids
                    )
                
                print(f"({len(documents)} chunks: +{added} *{modified} -{len(deleted_chunks)})")
            except Exception as e:
                logger.error(f"Error adding chunks to collection: {e}")
        else:
            print("(no chunks to index)")

    def _get_existing_file_ids(self, repo_name: str) -> Set[str]:
        """Get existing file IDs for a repository"""
        try:
            existing_files = self.files_collection.get(where={"repo_name": repo_name})
            return set(existing_files.get('ids', []))
        except Exception:
            return set()

    def _get_existing_chunk_ids(self, repo_name: str) -> Set[str]:
        """Get existing chunk IDs for a repository"""
        try:
            existing_chunks = self.chunks_collection.get(where={"repo_name": repo_name})
            return set(existing_chunks.get('ids', []))
        except Exception:
            return set()

    def _index_chunks(self, chunks: List[Dict], repo_name: str):
        """Index document chunks"""
        documents = []
        metadatas = []
        ids = []
        
        for chunk in chunks:
            try:
                relative_path = chunk.get('relative_path', chunk['filename'])
                chunk_id = f"chunk_{repo_name}_{relative_path}_{chunk.get('chunk_index', 0)}".replace("/", "_").replace("\\", "_").replace(".", "_")
                
                documents.append(chunk['content'])
                metadatas.append({
                    'repo_name': repo_name,
                    'file_path': relative_path,
                    'file_name': os.path.basename(chunk['filename']),
                    'chunk_id': chunk.get('chunk_index', 0),
                    'chunk_type': chunk.get('chunk_type', 'text'),
                    'language': self._detect_language(Path(chunk['filename']).suffix),
                    'file_type': chunk.get('file_type', 'unknown'),
                    'type': 'chunk'
                })
                ids.append(chunk_id)
                
            except Exception as e:
                logger.error(f"Error processing chunk: {e}")
                continue
        
        if documents:
            try:
                # Remove existing chunks for this repo
                try:
                    existing_chunks = self.chunks_collection.get(where={"repo_name": repo_name})
                    if existing_chunks and existing_chunks.get('ids'):
                        self.chunks_collection.delete(ids=existing_chunks['ids'])
                except Exception as e:
                    logger.debug(f"No existing chunks to delete for {repo_name}: {e}")
                
                # Add new chunks in batches
                batch_size = config.batch_size
                for i in range(0, len(documents), batch_size):
                    batch_docs = documents[i:i + batch_size]
                    batch_metas = metadatas[i:i + batch_size]
                    batch_ids = ids[i:i + batch_size]
                    
                    self.chunks_collection.add(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids
                    )
                
                logger.info(f"✅ Indexed {len(documents)} chunks")
            except Exception as e:
                logger.error(f"Error adding chunks to collection: {e}")
    
    def _is_supported_file(self, file_path: Path) -> bool:
        """Check if file is supported"""
        supported_extensions = set(config.supported_extensions)
        return file_path.suffix.lower() in supported_extensions
    
    def _detect_language(self, suffix: str) -> str:
        """Detect programming language from file extension"""
        lang_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.h': 'C',
            '.hpp': 'C++',
            '.cs': 'C#',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.go': 'Go',
            '.rs': 'Rust',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.md': 'Markdown',
            '.txt': 'Text',
            '.json': 'JSON',
            '.yml': 'YAML',
            '.yaml': 'YAML'
        }
        return lang_map.get(suffix.lower(), 'Unknown')
    
    def get_collections_info(self) -> Dict:
        """Get information about all collections"""
        try:
            files_count = self.files_collection.count()
            chunks_count = self.chunks_collection.count()
            
            return {
                'files': files_count,
                'chunks': chunks_count,
                'total_documents': files_count + chunks_count
            }
        except Exception as e:
            logger.error(f"Error getting collections info: {e}")
            return {'error': str(e)}
    
    def delete_repository(self, repo_name: str):
        """Delete a repository and all its associated data"""
        try:
            # Delete from files collection
            files_to_delete = self.files_collection.get(where={"repo_name": repo_name})
            if files_to_delete['ids']:
                self.files_collection.delete(ids=files_to_delete['ids'])
            
            # Delete from chunks collection
            chunks_to_delete = self.chunks_collection.get(where={"repo_name": repo_name})
            if chunks_to_delete['ids']:
                self.chunks_collection.delete(ids=chunks_to_delete['ids'])
            
            logger.info(f"✅ Repository '{repo_name}' deleted successfully!")
        except Exception as e:
            logger.error(f"Error deleting repository '{repo_name}': {e}")
    
    def _load_files(self, repo_path: Path, indexer_config: Dict) -> List[Dict]:
        """Load files from repository"""
        documents = []
        supported_extensions = indexer_config.get('supported_extensions', config.supported_extensions)
        ignore_patterns = indexer_config.get('ignore_patterns', config.ignore_patterns)
        
        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue
                
            # Check if file should be ignored
            if self._should_ignore_file(file_path, ignore_patterns):
                continue
                
            # Check if file extension is supported
            if file_path.suffix.lower() not in supported_extensions:
                continue
                
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Skip empty files
                if not content.strip():
                    continue
                
                documents.append({
                    'content': content,
                    'filename': str(file_path.relative_to(repo_path)),
                    'relative_path': str(file_path.relative_to(repo_path)),
                    'full_path': str(file_path),
                    'language': self._detect_language(file_path.suffix),
                    'file_type': 'text',
                    'size': len(content)
                })
                
            except Exception as e:
                logger.warning(f"Error reading file {file_path}: {e}")
                continue
        
        return documents
    
    def _chunk_documents(self, documents: List[Dict], indexer_config: Dict) -> List[Dict]:
        """Chunk documents into smaller pieces with proper overlap and metadata"""
        chunks = []
        chunk_size = indexer_config.get('chunk_size', config.chunk_size)
        chunk_overlap = indexer_config.get('chunk_overlap', config.chunk_overlap)
        
        for doc in documents:
            content = doc['content']
            file_path = doc.get('relative_path', doc['filename'])
            language = doc['language']
            
            # For small files, create a single chunk
            if len(content) <= chunk_size:
                chunks.append({
                    'content': content,
                    'filename': doc['filename'],
                    'relative_path': file_path,
                    'full_path': doc['full_path'],
                    'language': language,
                    'chunk_type': 'text',
                    'chunk_index': 0,
                    'start_pos': 0,
                    'end_pos': len(content)
                })
                continue
            
            # Use code-aware chunking for programming languages
            if self._is_code_file(language):
                file_chunks = self._chunk_code_intelligently(content, doc, chunk_size, chunk_overlap)
            else:
                file_chunks = self._chunk_text_by_lines(content, doc, chunk_size, chunk_overlap)
            
            chunks.extend(file_chunks)
        
        return chunks
    
    def _is_code_file(self, language: str) -> bool:
        """Check if this is a code file that benefits from intelligent chunking"""
        code_languages = {
            'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C', 'C#', 
            'PHP', 'Ruby', 'Go', 'Rust', 'Swift', 'Kotlin', 'Scala'
        }
        return language in code_languages
    
    def _chunk_code_intelligently(self, content: str, doc: Dict, chunk_size: int, chunk_overlap: int) -> List[Dict]:
        """Chunk code files by preserving semantic boundaries like functions, classes"""
        chunks = []
        lines = content.split('\n')
        file_path = doc.get('relative_path', doc['filename'])
        
        # Define semantic boundaries for different languages
        semantic_markers = {
            'Python': [r'^\s*def\s+', r'^\s*class\s+', r'^\s*@\w+', r'^\s*if\s+__name__'],
            'JavaScript': [r'^\s*function\s+', r'^\s*class\s+', r'^\s*const\s+\w+\s*=\s*\(', r'^\s*export\s+'],
            'TypeScript': [r'^\s*function\s+', r'^\s*class\s+', r'^\s*interface\s+', r'^\s*type\s+'],
            'Java': [r'^\s*public\s+class\s+', r'^\s*private\s+\w+', r'^\s*public\s+\w+', r'^\s*@\w+'],
            'C++': [r'^\s*class\s+', r'^\s*struct\s+', r'^\s*\w+\s*::\s*', r'^\s*template\s*<'],
            'C': [r'^\s*\w+\s+\w+\s*\(', r'^\s*struct\s+', r'^\s*typedef\s+', r'^\s*#define\s+']
        }
        
        language = doc['language']
        markers = semantic_markers.get(language, [])
        
        current_chunk_lines = []
        current_size = 0
        chunk_index = 0
        
        import re
        
        for i, line in enumerate(lines):
            line_size = len(line) + 1  # +1 for newline
            
            # Check if this line is a semantic boundary
            is_boundary = False
            if markers:
                for marker in markers:
                    if re.match(marker, line):
                        is_boundary = True
                        break
            
            # If we're at a boundary and have content, consider splitting
            if is_boundary and current_chunk_lines and current_size > chunk_size * 0.6:
                # Save current chunk
                chunk_content = '\n'.join(current_chunk_lines)
                chunks.append(self._create_chunk(chunk_content, doc, chunk_index, content))
                
                # Start new chunk with overlap
                overlap_lines = self._get_overlap_lines(current_chunk_lines, chunk_overlap)
                current_chunk_lines = overlap_lines + [line]
                current_size = sum(len(l) + 1 for l in current_chunk_lines)
                chunk_index += 1
                continue
            
            # Normal line processing
            if current_size + line_size > chunk_size and current_chunk_lines:
                # Save current chunk
                chunk_content = '\n'.join(current_chunk_lines)
                chunks.append(self._create_chunk(chunk_content, doc, chunk_index, content))
                
                # Start new chunk with overlap
                overlap_lines = self._get_overlap_lines(current_chunk_lines, chunk_overlap)
                current_chunk_lines = overlap_lines + [line]
                current_size = sum(len(l) + 1 for l in current_chunk_lines)
                chunk_index += 1
            else:
                current_chunk_lines.append(line)
                current_size += line_size
        
        # Add remaining content
        if current_chunk_lines:
            chunk_content = '\n'.join(current_chunk_lines)
            chunks.append(self._create_chunk(chunk_content, doc, chunk_index, content))
        
        return chunks
    
    def _chunk_text_by_lines(self, content: str, doc: Dict, chunk_size: int, chunk_overlap: int) -> List[Dict]:
        """Chunk non-code files by lines with proper overlap"""
        chunks = []
        lines = content.split('\n')
        current_chunk_lines = []
        current_chunk_size = 0
        chunk_index = 0
        
        for line in lines:
            line_size = len(line) + 1  # +1 for newline
            
            # If adding this line would exceed chunk size and we have content
            if current_chunk_size + line_size > chunk_size and current_chunk_lines:
                # Save current chunk
                chunk_content = '\n'.join(current_chunk_lines)
                chunks.append(self._create_chunk(chunk_content, doc, chunk_index, content))
                
                # Start new chunk with overlap
                overlap_lines = self._get_overlap_lines(current_chunk_lines, chunk_overlap)
                current_chunk_lines = overlap_lines + [line]
                current_chunk_size = sum(len(l) + 1 for l in current_chunk_lines)
                chunk_index += 1
            else:
                current_chunk_lines.append(line)
                current_chunk_size += line_size
        
        # Add remaining content
        if current_chunk_lines:
            chunk_content = '\n'.join(current_chunk_lines)
            chunks.append(self._create_chunk(chunk_content, doc, chunk_index, content))
        
        return chunks
    
    def _get_overlap_lines(self, lines: List[str], overlap_size: int) -> List[str]:
        """Get overlap lines up to overlap_size characters"""
        if not lines or overlap_size <= 0:
            return []
        
        overlap_lines = []
        overlap_text = ''
        
        # Work backwards from end to get overlap_size characters
        for i in range(len(lines) - 1, -1, -1):
            test_line = lines[i]
            if len(overlap_text) + len(test_line) + 1 <= overlap_size:  # +1 for newline
                overlap_lines.insert(0, test_line)
                overlap_text = '\n'.join(overlap_lines)
            else:
                break
        
        return overlap_lines
    
    def _create_chunk(self, chunk_content: str, doc: Dict, chunk_index: int, full_content: str) -> Dict:
        """Create a chunk dictionary with proper metadata"""
        file_path = doc.get('relative_path', doc['filename'])
        
        # Find position in original content
        start_pos = full_content.find(chunk_content)
        if start_pos == -1:
            start_pos = 0
        
        return {
            'content': chunk_content,
            'filename': doc['filename'],
            'relative_path': file_path,
            'full_path': doc['full_path'],
            'language': doc['language'],
            'chunk_type': 'text',
            'chunk_index': chunk_index,
            'start_pos': start_pos,
            'end_pos': start_pos + len(chunk_content)
        }

    def _get_existing_files_metadata(self, repo_name: str) -> Dict[str, Dict]:
        """Get existing file metadata for change detection"""
        try:
            existing_files = self.files_collection.get(where={"repo_name": repo_name})
            result = {}
            if existing_files and existing_files.get('ids'):
                metadatas = existing_files.get('metadatas')
                for i, file_id in enumerate(existing_files['ids']):
                    metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                    result[file_id] = {
                        'size': metadata.get('size', 0),
                        'mtime': metadata.get('mtime', 0),
                        'hash': metadata.get('hash', '')
                    }
            return result
        except Exception:
            return {}

    def _has_file_changed(self, file_path: Path, existing_metadata: Dict) -> bool:
        """Check if file has changed using multiple methods"""
        current_metadata = self._get_file_metadata(file_path)
        
        # Quick checks first
        if current_metadata['size'] != existing_metadata.get('size', 0):
            return True
        
        if current_metadata['mtime'] != existing_metadata.get('mtime', 0):
            return True
        
        # Hash check as final verification
        if current_metadata['hash'] != existing_metadata.get('hash', ''):
            return True
        
        return False

    def _should_ignore_file(self, file_path: Path, ignore_patterns: List[str]) -> bool:
        """Check if file should be ignored based on patterns"""
        file_str = str(file_path)
        
        for pattern in ignore_patterns:
            if pattern.endswith('/'):
                # Directory pattern
                if f"/{pattern[:-1]}/" in file_str or file_str.endswith(f"/{pattern[:-1]}"):
                    return True
            elif '*' in pattern:
                # Wildcard pattern
                if pattern.startswith('*.'):
                    if file_path.suffix == pattern[1:]:
                        return True
                elif pattern.endswith('*'):
                    if file_path.name.startswith(pattern[:-1]):
                        return True
            else:
                # Exact match
                if pattern in file_str:
                    return True
        
        return False

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return ""

    def _get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get file metadata for change detection"""
        try:
            stat = file_path.stat()
            return {
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'hash': self._get_file_hash(file_path)
            }
        except Exception:
            return {'size': 0, 'mtime': 0, 'hash': ''}
