# Code Search

Code Search is a command-line tool for fast, semantic search across your code repositories, powered by ChromaDB.

Key Features:
- **ChromaDB Integration**  
  Persistent vector database for high-performance semantic indexing and search.
- **Multi-repository Support**  
  Index and query 1,000+ repositories seamlessly.
- **Intelligent Change Detection**  
  Multi-layered change detection (size, mtime, hash) with optimized file hashing cache.
- **Smart Code Chunking**  
  Code-aware chunking with semantic boundaries for better context preservation.
- **Incremental Processing**  
  Only processes changed files and chunks, skipping unchanged content for efficiency.
- **Advanced Filters**  
  Filter by repository, file, code chunk and programming language.
- **Interactive Search Mode**  
  Interactive search interface for exploring your repositories.
- **Collection Management**  
  View stats, inspect contents or delete collections on demand.

Getting Started:

```bash
# Install dependencies
pip install -r requirements.txt

# Index a single repository
python cli.py index /path/to/your/repo --name "MyProject"

# Search across all repositories
python cli.py search "authentication function"

# Start interactive search
python cli.py interactive
```

Project Layout:

```
.
├── cli.py                   # CLI entry point
├── backend/
│   ├── chroma_client.py     # ChromaDB singleton client
│   ├── chroma_indexer.py    # Indexing logic
│   ├── chroma_search.py     # Search logic
│   └── logger.py            # Logging configuration
├── docs/
│   └── sequence-diagram.md  # System architecture and flow diagrams
├── config.json              # Default settings
├── requirements.txt         # Python dependencies
└── Readme.md                # This documentation
```

For detailed system flow and interaction diagrams, see the [Sequence Diagram Documentation](docs/sequence-diagram.md).

## CLI Commands

```bash
# Index repositories
python cli.py index /path/to/repo --name "MyProject"
python cli.py index-all /path/to/repos --max-repos 50

# Search with filters
python cli.py search "authentication function"
python cli.py search "react components" --type repos --limit 10
python cli.py search "auth" --repo MyProject --lang Python --min-score 0.4

# Repository management
python cli.py info MyProject
python cli.py stats
python cli.py delete MyProject

# Interactive search
python cli.py interactive
```

## Data Storage

ChromaDB stores data in three collections:
- **Repositories**: High-level repository metadata
- **Files**: Individual file content for file-level search  
- **Chunks**: Granular code/content chunks for precise search

The system uses intelligent change detection to only process modified files:
- **Size-based detection**: Quick check for file size changes
- **Modification time**: Detects file system-level changes
- **Hash-based verification**: SHA-256 content hashing with caching for accuracy
- **Incremental chunking**: Only re-processes chunks for changed files

Database location: `index/chroma_db/`

## Configuration

The search behavior can be customized via `config.json`. Key settings include:

- **`min_search`**: Minimum similarity score for search results (default: 0.35)
  - Higher values (0.7-0.9) return only very similar matches
  - Lower values (0.1-0.3) return more diverse results
  - Can be overridden per search using `--min-score` flag

- **`chunk_size`**: Size of text chunks for indexing (default: 5000)
  - System warns if chunks exceed 1.5x this size
  - Larger chunks provide more context but may reduce search precision

- **`chunk_overlap`**: Overlap between chunks to maintain context (default: 100)
  - Smart overlap preserves semantic boundaries (functions, classes)
  - Higher values improve context continuity but increase storage

- **`supported_extensions`**: File types to index
- **`ignore_patterns`**: Files/folders to skip during indexing (includes minified files)
- **`batch_size`**: Number of items to process in parallel (default: 32)

## Performance Features

- **Change Detection**: Multi-layered approach (size → mtime → hash) for efficient re-indexing
- **Hash Caching**: Avoids recalculating file hashes for unchanged files
- **Incremental Processing**: Only processes chunks for modified files
- **Semantic Chunking**: Code-aware chunking preserves function/class boundaries
- **Progress Tracking**: Visual indicators show +added, *modified, =unchanged, -removed files
