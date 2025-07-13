# Code Search System - Sequence Diagram

The system follows a three-layer architecture with optimized change detection:
- **CLI Layer**: User interface (cli.py)
- **Service Layer**: Business logic with intelligent change detection (chroma_indexer.py, chroma_search.py)
- **Data Layer**: Database abstraction with caching (chroma_client.py, ChromaDB)

## Indexing Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI as CLI (cli.py)
    participant Indexer as ChromaIndexer
    participant Client as ChromaClient
    participant Config as Config
    participant ChromaDB as ChromaDB Collections
    participant FileSystem as File System

    User->>CLI: python cli.py index /path/to/repo
    CLI->>Indexer: ChromaIndexer()
    Indexer->>Config: Load configuration
    Config-->>Indexer: Config settings
    Indexer->>Client: ChromaClient(db_path)
    Client->>ChromaDB: Create/get collections (files, chunks)
    ChromaDB-->>Client: Collection references
    Client-->>Indexer: Client instance
    
    CLI->>Indexer: index_repository(repo_path, repo_name)
    Indexer->>Indexer: _index_files_and_chunks()
    Indexer->>FileSystem: _load_files(repo_path, config)
    FileSystem-->>Indexer: List of file documents
    
    Indexer->>Indexer: _index_files_with_progress(raw_docs)
    Indexer->>ChromaDB: Get existing files metadata
    ChromaDB-->>Indexer: Existing file data with size/mtime/hash
    
    loop For each file
        Indexer->>Indexer: _has_file_changed(file_path, existing_metadata)
        Indexer->>Indexer: Check size → mtime → hash (cached)
        alt File changed
            Indexer->>Indexer: Add to changed_files list
            Note over Indexer: Progress: *modified or +added
        else File unchanged
            Indexer->>Indexer: Add to unchanged_files list
            Note over Indexer: Progress: =unchanged
        end
    end
    
    Indexer->>ChromaDB: Delete old file documents
    loop For each changed file
        Indexer->>ChromaDB: Upsert file document with new metadata
        ChromaDB-->>Indexer: Confirmation
    end
    
    Indexer->>Indexer: _chunk_documents(changed_files_only)
    Note over Indexer: Smart chunking with semantic boundaries
    Indexer->>Indexer: _index_chunks_with_progress(chunks, changed_files)
    
    alt Has changed files
        Indexer->>ChromaDB: Delete chunks only for changed files
        loop For each new chunk
            Indexer->>ChromaDB: Upsert chunk document
            ChromaDB-->>Indexer: Confirmation
        end
    else No changes
        Note over Indexer: Skip chunk processing entirely
    end
    
    Indexer-->>CLI: Indexing complete
    CLI-->>User: Success message with stats
    Note over CLI: Shows: X files (Y changed) → Z chunks (W processed)
    Note over CLI: Progress indicators: +added *modified =unchanged -removed
```

## Search Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI as CLI (cli.py)
    participant Search as ChromaSearch
    participant Client as ChromaClient
    participant Config as Config
    participant ChromaDB as ChromaDB Collections

    User->>CLI: python cli.py search "query" --type all
    CLI->>Search: ChromaSearch()
    Search->>Config: Load configuration
    Config-->>Search: Config settings
    Search->>Client: ChromaClient(db_path)
    Client->>ChromaDB: Get existing collections
    ChromaDB-->>Client: Collection references
    Client-->>Search: Client instance
    
    CLI->>Search: search_all(query, limit, min_score)
    
    par Search Repositories
        Search->>Search: search_repositories(query)
        Search->>ChromaDB: Query repositories collection
        ChromaDB-->>Search: Raw results
        Search->>Search: _format_results(results, "repository")
        Search->>Search: Apply min_score filter
        Search-->>Search: Formatted repository results
    and Search Files
        Search->>Search: search_files(query)
        Search->>ChromaDB: Query files collection
        ChromaDB-->>Search: Raw results
        Search->>Search: _format_results(results, "file")
        Search->>Search: Apply min_score filter
        Search-->>Search: Formatted file results
    and Search Chunks
        Search->>Search: search_chunks(query)
        Search->>ChromaDB: Query chunks collection
        ChromaDB-->>Search: Raw results
        Search->>Search: _format_results(results, "chunk")
        Search->>Search: Apply min_score filter
        Search-->>Search: Formatted chunk results
    end
    
    Search-->>CLI: Combined results {repos, files, chunks}
    CLI->>CLI: _display_results() for each type
    CLI-->>User: Formatted search results
```

## Change Detection Flow

```mermaid
sequenceDiagram
    participant Indexer as ChromaIndexer
    participant FileSystem as File System
    participant Cache as Hash Cache
    participant ChromaDB as ChromaDB Collections

    Indexer->>ChromaDB: Get existing files metadata
    ChromaDB-->>Indexer: {file_id: {size, mtime, hash}}
    
    loop For each file in repository
        Indexer->>FileSystem: Get current file stats
        FileSystem-->>Indexer: {size, mtime}
        
        alt Size changed
            Note over Indexer: Quick detection - file changed
            Indexer->>Indexer: Mark as changed
        else Size unchanged
            alt mtime changed
                Note over Indexer: File system change detected
                Indexer->>Indexer: Mark as changed
            else mtime unchanged
                Indexer->>Cache: Check hash cache
                alt Hash cached
                    Cache-->>Indexer: Cached hash
                else Hash not cached
                    Indexer->>FileSystem: Calculate SHA-256 hash
                    FileSystem-->>Indexer: File hash
                    Indexer->>Cache: Store hash with key (path_mtime_size)
                end
                
                alt Hash different
                    Note over Indexer: Content changed
                    Indexer->>Indexer: Mark as changed
                else Hash same
                    Note over Indexer: File unchanged
                    Indexer->>Indexer: Mark as unchanged
                end
            end
        end
    end
    
    Indexer->>Indexer: Return (changed_files, unchanged_files)
```

## Smart Chunking Process

```mermaid
sequenceDiagram
    participant Indexer as ChromaIndexer
    participant Doc as Document
    participant Chunker as Smart Chunker

    Indexer->>Doc: Get file content and language
    Doc-->>Indexer: {content, language, metadata}
    
    alt Small file (< chunk_size)
        Indexer->>Indexer: Create single chunk
    else Large file
        alt Code file (Python, JS, etc.)
            Indexer->>Chunker: _chunk_code_intelligently()
            Chunker->>Chunker: Define semantic markers for language
            Note over Chunker: Python: def, class, @decorator<br/>JS: function, class, export
            
            loop For each line
                Chunker->>Chunker: Check if semantic boundary
                alt At boundary AND chunk size > 60%
                    Chunker->>Chunker: Split chunk here
                    Chunker->>Chunker: Add smart overlap (preserve context)
                else Normal line
                    Chunker->>Chunker: Add to current chunk
                end
            end
            
            Chunker->>Chunker: Validate chunk sizes
            alt Chunk > 1.5x limit
                Note over Chunker: Log warning about oversized chunk
            end
            
            Chunker-->>Indexer: Code chunks with semantic boundaries
        else Text file
            Indexer->>Chunker: _chunk_text_by_lines()
            Chunker->>Chunker: Split by lines with overlap
            Chunker-->>Indexer: Text chunks
        end
    end
    
    Indexer->>Indexer: Add metadata (start_pos, end_pos, size)
```

## Repository Information Retrieval

```mermaid
sequenceDiagram
    participant User
    participant CLI as CLI (cli.py)
    participant Search as ChromaSearch
    participant Client as ChromaClient
    participant ChromaDB as ChromaDB Collections

    User->>CLI: python cli.py info repo_name
    CLI->>Search: ChromaSearch()
    Search->>Client: ChromaClient(db_path)
    Client-->>Search: Client instance
    
    CLI->>Search: get_repo_info(repo_name)
    Search->>ChromaDB: Get repository by name
    ChromaDB-->>Search: Repository document + metadata
    Search->>Client: format_repository_info(metadata, document)
    Client-->>Search: Formatted repository info
    Search-->>CLI: Repository details
    CLI-->>User: Repository information display
```

## Statistics and Collection Management

```mermaid
sequenceDiagram
    participant User
    participant CLI as CLI (cli.py)
    participant Search as ChromaSearch
    participant ChromaDB as ChromaDB Collections

    User->>CLI: python cli.py stats
    CLI->>Search: ChromaSearch()
    Search-->>CLI: Search instance
    
    CLI->>Search: get_collection_stats()
    
    par Count Collections
        Search->>ChromaDB: repos_collection.count()
        ChromaDB-->>Search: Repository count
    and
        Search->>ChromaDB: files_collection.count()
        ChromaDB-->>Search: File count
    and
        Search->>ChromaDB: chunks_collection.count()
        ChromaDB-->>Search: Chunk count
    end
    
    Search->>Search: get_languages()
    Search->>ChromaDB: Get all file metadata
    ChromaDB-->>Search: File metadata list
    Search->>Search: Extract unique languages
    Search-->>Search: Language list
    
    Search->>Search: get_repositories_list()
    Search->>ChromaDB: Get all repository metadata
    ChromaDB-->>Search: Repository metadata list
    Search->>Search: Extract repository names
    Search-->>Search: Repository names list
    
    Search-->>CLI: Complete statistics
    CLI-->>User: Statistics display
```
