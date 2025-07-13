# Code Search

Code Search is a command-line tool for fast, semantic search across your code repositories, powered by ChromaDB.

Key Features:
- **ChromaDB Integration**  
  Persistent vector database for high-performance semantic indexing and search.
- **Multi-repository Support**  
  Index and query 1,000+ repositories seamlessly.
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

Database location: `index/chroma_db/`

## Configuration

The search behavior can be customized via `config.json`. Key settings include:

- **`min_search`**: Minimum similarity score for search results (default: 0.3)
  - Higher values (0.7-0.9) return only very similar matches
  - Lower values (0.1-0.3) return more diverse results
  - Can be overridden per search using `--min-score` flag

- **`chunk_size`**: Size of text chunks for indexing (default: 5000)
- **`chunk_overlap`**: Overlap between chunks to maintain context (default: 100)
- **`supported_extensions`**: File types to index
- **`ignore_patterns`**: Files/folders to skip during indexing
- **`batch_size`**: Number of items to process in parallel (default: 32)
