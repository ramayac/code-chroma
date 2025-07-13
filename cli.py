"""
CLI interface for ChromaDB-based smart search.
Provides commands for indexing, searching, and managing repositories.
"""

import click
import os
import atexit
from pathlib import Path
from typing import List, Dict, Any
from backend.chroma_indexer import ChromaIndexer
from backend.chroma_search import ChromaSearch
from backend.chroma_client import ChromaClient
from backend.logger import get_logger
from backend.config import config

logger = get_logger()

# Register cleanup function
def cleanup_on_exit():
    """Cleanup function to ensure proper database closure"""
    try:
        ChromaClient.close()
    except:
        pass

atexit.register(cleanup_on_exit)

@click.group()
def cli():
    """Smart Search CLI with ChromaDB - Fast semantic search across your repositories"""
    pass

@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.option('--name', '-n', help='Repository name (defaults to folder name)')
def index(repo_path, name):
    """Index a single repository"""
    try:
        indexer = ChromaIndexer()
        repo_name = name or Path(repo_path).name
        
        click.echo(f"🔍 {repo_name}")
        click.echo(f"📁 {repo_path}")
        click.echo(f"Legend: + added, * modified, = unchanged, - removed, ! error")
        
        indexer.index_repository(repo_path, repo_name)
        
        # Show summary
        info = indexer.get_collections_info()
        click.echo(f"✅ Success!")
        click.echo(f"📊 Total documents: {info.get('total_documents', 'unknown')}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        logger.error(f"Indexing error: {e}")

@cli.command()
@click.argument('repos_dir', type=click.Path(exists=True), required=False)
@click.option('--max-repos', '-m', default=10, help='Maximum number of repositories to index')
def index_all(repos_dir, max_repos):
    """Index all repositories in a directory (defaults to source_folder from config)"""
    try:
        # Use config source_folder if no repos_dir provided
        if repos_dir is None:
            repos_dir = config.source_folder
            if not os.path.exists(repos_dir):
                click.echo(f"❌ Source folder not found: {repos_dir}")
                click.echo("💡 Please update the 'source_folder' in config.json or provide a REPOS_DIR argument")
                return
        
        indexer = ChromaIndexer()
        repos_path = Path(repos_dir)
        
        click.echo(f"🔍 Scanning for repositories in: {repos_path}")
        
        # Find all git repositories
        git_repos = []
        for item in repos_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                if (item / '.git').exists():
                    git_repos.append(item)
        
        if not git_repos:
            click.echo("❌ No Git repositories found in the specified directory")
            return
        
        # Limit number of repos
        repos_to_index = git_repos[:max_repos]
        
        click.echo(f"🔍 Found {len(git_repos)} Git repositories")
        click.echo(f"📦 Indexing {len(repos_to_index)} repositories...")
        click.echo(f"Legend: + added, * modified, = unchanged, - removed, ! error")
        
        for i, repo_dir in enumerate(repos_to_index, 1):
            click.echo(f"\n[{i}/{len(repos_to_index)}] {repo_dir.name}")
            try:
                indexer.index_repository(str(repo_dir), repo_dir.name)
                click.echo("✅ Success")
            except Exception as e:
                click.echo(f"❌ Error: {e}")
                try:
                    logger.error(f"Error indexing {repo_dir.name}: {e}")
                except:
                    pass
        
        # Show final summary
        info = indexer.get_collections_info()
        click.echo(f"\n🎉 Indexing complete!")
        click.echo(f"📊 Total documents: {info.get('total_documents', 'unknown')}")
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        
        if "being used by another process" in error_msg or "WinError 32" in error_msg:
            click.echo(f"❌ Database file is locked: {error_msg}")
            click.echo("💡 This usually means another instance of the application is running.")
            click.echo("🔧 Solution:")
            click.echo("   1. Close any other instances of this application")
            click.echo("   2. Check Windows Task Manager for any lingering Python processes")
            click.echo("   3. Wait a few seconds and try again")
            click.echo("   4. If the issue persists, restart your computer")
        elif "no such column" in error_msg.lower() or "database" in error_msg.lower():
            click.echo(f"❌ ChromaDB database issue detected: {error_msg}")
            click.echo("💡 This usually indicates a corrupted or incompatible database.")
            click.echo("🔧 The system will attempt to reset the database automatically.")
            click.echo("   If the issue persists, try manually deleting the index/chroma_db folder.")
        else:
            click.echo(f"❌ Error during batch indexing: {e}")
            click.echo(f"Traceback: {traceback.format_exc()}")
        
        try:
            logger.error(f"Batch indexing error: {e}")
        except:
            # Fallback if logger is not available
            pass

@cli.command()
@click.argument('query')
@click.option('--type', '-t', type=click.Choice(['repos', 'files', 'chunks', 'all']), default='all', help='Search type')
@click.option('--repo', '-r', help='Filter by repository name')
@click.option('--lang', '-l', help='Filter by programming language')
@click.option('--limit', '-n', default=5, help='Number of results per type')
@click.option('--min-score', '-s', type=float, help='Minimum similarity score (overrides config default)')
def search(query, type, repo, lang, limit, min_score):
    """Search indexed repositories and files"""
    try:
        # Lazy initialization - only create searcher when needed
        searcher = ChromaSearch()
        
        click.echo(f"🔍 Searching for: '{query}'")
        if repo:
            click.echo(f"📁 Repository filter: {repo}")
        if lang:
            click.echo(f"🔤 Language filter: {lang}")
        if min_score is not None:
            click.echo(f"📊 Minimum score: {min_score}")
        click.echo()
        
        if type == 'repos':
            results = searcher.search_repositories(query, limit, min_score)
            _display_results("Repositories", results, "📁")
        
        elif type == 'files':
            results = searcher.search_files(query, repo, limit, min_score)
            _display_results("Files", results, "📄")
        
        elif type == 'chunks':
            results = searcher.search_chunks(query, repo, lang, limit, min_score)
            _display_results("Code Chunks", results, "🔗")
        
        else:  # all
            all_results = searcher.search_all(query, limit, min_score)
            
            for result_type, results in all_results.items():
                if results:
                    icons = {"repositories": "📁", "files": "📄", "chunks": "🔗"}
                    _display_results(result_type.title(), results, icons[result_type])
                    click.echo()
        
    except Exception as e:
        click.echo(f"❌ Search error: {e}")
        logger.error(f"Search error: {e}")

@cli.command()
@click.argument('repo_name')
def info(repo_name):
    """Get detailed information about a repository"""
    try:
        # Lazy initialization - only create searcher when needed
        searcher = ChromaSearch()
        repo_info = searcher.get_repo_info(repo_name)
        
        if repo_info:
            click.echo(f"📁 Repository: {repo_info['name']}")
            click.echo(f"🔤 Language: {repo_info['language']}")
            click.echo(f"📊 Files: {repo_info['file_count']} supported / {repo_info['total_files']} total")
            click.echo(f"📅 Indexed: {repo_info['indexed_at']}")
            click.echo(f"📍 Path: {repo_info['path']}")
            click.echo(f"📝 Description: {repo_info['description']}")
            
            # Show files
            files = searcher.get_repo_files(repo_name, 10)
            if files:
                click.echo(f"\n📄 Sample files:")
                for file in files[:5]:
                    click.echo(f"  • {file['file_path']} ({file['language']})")
        else:
            click.echo(f"❌ Repository '{repo_name}' not found")
            
            # Suggest similar repositories
            similar = searcher.search_repositories(repo_name, 3)
            if similar:
                click.echo(f"\n💡 Did you mean:")
                for repo in similar:
                    click.echo(f"  • {repo['metadata']['repo_name']}")
    
    except Exception as e:
        click.echo(f"❌ Error getting repository info: {e}")
        logger.error(f"Info error: {e}")

@cli.command()
def stats():
    """Show database statistics"""
    try:
        # Lazy initialization - only create searcher when needed
        searcher = ChromaSearch()
        stats = searcher.get_collection_stats()
        
        click.echo("📊 Database Statistics:")
        click.echo(f"  📁 Repositories: {stats.get('repositories', 0)}")
        click.echo(f"  📄 Files: {stats.get('files', 0)}")
        click.echo(f"  🔗 Chunks: {stats.get('chunks', 0)}")
        click.echo(f"  🔤 Languages: {stats.get('languages', 0)}")
        
        # Show repositories
        repos = stats.get('repo_names', [])
        if repos:
            click.echo(f"\n📁 Indexed repositories:")
            for repo in repos:
                click.echo(f"  • {repo}")
        
        # Show languages
        languages = searcher.get_languages()
        if languages:
            click.echo(f"\n🔤 Available languages:")
            for lang in languages:
                click.echo(f"  • {lang}")
    
    except Exception as e:
        click.echo(f"❌ Error getting statistics: {e}")
        logger.error(f"Stats error: {e}")

@cli.command()
@click.argument('collection', type=click.Choice(['repositories', 'files', 'chunks']))
@click.option('--limit', '-n', default=5, help='Number of items to show')
def inspect(collection, limit):
    """Inspect collection data for debugging"""
    try:
        # Lazy initialization - only create searcher when needed
        searcher = ChromaSearch()
        data = searcher.inspect_collection(collection, limit)
        
        if 'error' in data:
            click.echo(f"❌ Error: {data['error']}")
            return
        
        click.echo(f"🔍 Collection: {collection}")
        click.echo(f"📊 Total items: {data['total_count']}")
        click.echo(f"📋 Sample size: {data['sample_size']}")
        click.echo()
        
        for item in data['sample_data']:
            click.echo(f"🆔 ID: {item['id']}")
            click.echo(f"📝 Content: {item['document_preview']}")
            click.echo(f"📊 Metadata: {item['metadata']}")
            click.echo("-" * 50)
    
    except Exception as e:
        click.echo(f"❌ Inspection error: {e}")
        logger.error(f"Inspection error: {e}")

@cli.command()
@click.argument('repo_name')
@click.confirmation_option(prompt='Are you sure you want to delete this repository?')
def delete(repo_name):
    """Delete a repository and all its data"""
    try:
        # Lazy initialization - only create indexer when needed
        indexer = ChromaIndexer()
        indexer.delete_repository(repo_name)
        click.echo(f"✅ Repository '{repo_name}' deleted successfully!")
    
    except Exception as e:
        click.echo(f"❌ Error deleting repository: {e}")
        logger.error(f"Delete error: {e}")

@cli.command()
def interactive():
    """Interactive search mode for exploring your repositories"""
    try:
        # Lazy initialization - only create searcher when needed
        searcher = ChromaSearch()
        click.echo("🔍 Interactive Search Mode")
        click.echo("Enter search queries to find repositories, files, and code! (type 'quit' to exit)")
        click.echo("Examples:")
        click.echo("  • 'authentication'")
        click.echo("  • 'database connection'")
        click.echo("  • 'Python machine learning'")
        click.echo()
        
        while True:
            try:
                query = click.prompt("🔍 Search", type=str)
                if query.lower() in ['quit', 'exit', 'bye']:
                    click.echo("👋 Goodbye!")
                    break
                
                # Perform search
                click.echo(f"\n🔍 Searching for: '{query}'")
                all_results = searcher.search_all(query, 3)
                
                found_any = False
                for result_type, results in all_results.items():
                    if results:
                        found_any = True
                        icons = {"repositories": "📁", "files": "📄", "chunks": "🔗"}
                        _display_results(result_type.title(), results, icons[result_type])
                        click.echo()
                
                if not found_any:
                    click.echo("❌ No results found. Try a different search term.")
                    click.echo("💡 Use 'stats' command to see available repositories.")
                
                click.echo()
                
            except KeyboardInterrupt:
                click.echo("\n👋 Goodbye!")
                break
            except EOFError:
                click.echo("\n👋 Goodbye!")
                break
    
    except Exception as e:
        click.echo(f"❌ Interactive search error: {e}")
        logger.error(f"Interactive search error: {e}")

@cli.command()
@click.option('--max-repos', '-m', default=None, help='Maximum number of repositories to index (default: all)')
@click.option('--force', '-f', is_flag=True, help='Force reindex of existing repositories')
def reindex(max_repos, force):
    """Reindex all repositories from the configured source folder"""
    try:
        source_folder = config.source_folder
        
        if not os.path.exists(source_folder):
            click.echo(f"❌ Source folder not found: {source_folder}")
            click.echo("💡 Please update the 'source_folder' in config.json")
            return
        
        indexer = ChromaIndexer()
        repos_path = Path(source_folder)
        
        click.echo(f"🔍 Scanning for repositories in: {source_folder}")
        
        # Find all git repositories
        git_repos = []
        for item in repos_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                if (item / '.git').exists():
                    git_repos.append(item)
        
        if not git_repos:
            click.echo("❌ No Git repositories found in the configured source folder")
            click.echo(f"💡 Checked directory: {source_folder}")
            return
        
        # Apply max_repos limit if specified
        if max_repos:
            max_repos = int(max_repos)
            repos_to_index = git_repos[:max_repos]
            click.echo(f"🔍 Found {len(git_repos)} Git repositories, indexing first {len(repos_to_index)}")
        else:
            repos_to_index = git_repos
            click.echo(f"🔍 Found {len(git_repos)} Git repositories, indexing all")
        
        click.echo(f"📁 Source folder: {source_folder}")
        click.echo(f"📦 Repositories to index: {len(repos_to_index)}")
        click.echo(f"Legend: + added, * modified, = unchanged, - removed, ! error")
        click.echo()
        
        successful = 0
        failed = 0
        
        for i, repo_dir in enumerate(repos_to_index, 1):
            click.echo(f"[{i}/{len(repos_to_index)}] {repo_dir.name}")
            try:
                # Check if already indexed (unless force flag is used)
                if not force:
                    # Lazy initialization - only create searcher when needed for checking
                    searcher = ChromaSearch()
                    existing = searcher.get_repo_info(repo_dir.name)
                    if existing:
                        click.echo(f"⏭️  Already indexed (use --force to reindex)")
                        successful += 1
                        continue
                
                indexer.index_repository(str(repo_dir), repo_dir.name)
                click.echo("✅ Success")
                successful += 1
                
            except Exception as e:
                click.echo(f"❌ Error: {e}")
                logger.error(f"Error indexing {repo_dir.name}: {e}")
                failed += 1
        
        # Show final summary
        info = indexer.get_collections_info()
        click.echo(f"\n🎉 Reindexing complete!")
        click.echo(f"✅ Successful: {successful}")
        click.echo(f"❌ Failed: {failed}")
        click.echo(f"📊 Total documents in database: {info.get('total_documents', 'unknown')}")
        
    except Exception as e:
        click.echo(f"❌ Error during reindexing: {e}")
        logger.error(f"Reindexing error: {e}")

@cli.command(name='config')
def config_cmd():
    """Show current configuration"""
    try:
        config_dict = config.get_all()
        
        click.echo("⚙️  Current Configuration:")
        click.echo(f"📁 Source folder: {config_dict.get('source_folder', 'Not set')}")
        click.echo(f"📂 Index folder: {config_dict.get('index_folder', 'Not set')}")
        click.echo(f"📄 Supported extensions: {len(config_dict.get('supported_extensions', []))} types")
        click.echo(f"📝 Chunk size: {config_dict.get('chunk_size', 'Not set')}")
        click.echo(f"🔄 Chunk overlap: {config_dict.get('chunk_overlap', 'Not set')}")
        click.echo(f"📊 Min search score: {config_dict.get('min_search', 'Not set')}")
        
        # Show source folder contents if it exists
        source_folder = config_dict.get('source_folder')
        if source_folder and os.path.exists(source_folder):
            repos_path = Path(source_folder)
            git_repos = [item for item in repos_path.iterdir() 
                        if item.is_dir() and not item.name.startswith('.') and (item / '.git').exists()]
            click.echo(f"\n📊 Found {len(git_repos)} Git repositories in source folder")
            
            if git_repos and len(git_repos) <= 10:
                click.echo("📋 Repository list:")
                for repo in git_repos:
                    click.echo(f"  • {repo.name}")
            elif git_repos:
                click.echo(f"📋 First 10 repositories:")
                for repo in git_repos[:10]:
                    click.echo(f"  • {repo.name}")
                click.echo(f"  ... and {len(git_repos) - 10} more")
        else:
            click.echo(f"\n❌ Source folder not accessible: {source_folder}")
        
    except Exception as e:
        click.echo(f"❌ Error reading configuration: {e}")
        logger.error(f"Config error: {e}")

def _display_results(title: str, results: List[Dict], icon: str):
    """Display search results"""
    if not results:
        click.echo(f"{icon} {title}: No results found")
        return
    
    click.echo(f"{icon} {title}:")
    for result in results:
        similarity = result.get('similarity', 0)
        click.echo(f"  • {result['display_name']} (similarity: {similarity:.2f})")
        click.echo(f"    {result['summary']}")
        if len(result['content']) > 100:
            preview = result['content'][:100] + "..."
            click.echo(f"    Preview: {preview}")
        click.echo()

@cli.command()
def check_db():
    """Check database status and diagnose issues"""
    try:
        from backend.chroma_client import check_database_lock
        from backend.config import config
        import os
        
        db_path = Path(os.path.join(config.index_folder, "chroma_db"))
        sqlite_file = db_path / "chroma.sqlite3"
        
        click.echo("🔍 Checking ChromaDB status...")
        click.echo(f"📁 Database path: {db_path}")
        
        if not db_path.exists():
            click.echo("❌ Database directory does not exist")
            return
        
        if not sqlite_file.exists():
            click.echo("✅ No database file found - ready for first-time setup")
            return
        
        # Check file size
        file_size = sqlite_file.stat().st_size
        click.echo(f"📊 Database file size: {file_size:,} bytes")
        
        # Check if locked
        if check_database_lock(db_path):
            click.echo("🔒 Database is currently LOCKED by another process")
            click.echo("💡 Solutions:")
            click.echo("   1. Close any other instances of this application")
            click.echo("   2. Check Windows Task Manager for Python processes")
            click.echo("   3. Wait a few moments and try again")
        else:
            click.echo("✅ Database is available and not locked")
            
            # Try to connect
            try:
                client = ChromaClient()
                if client.client:
                    collections_info = client.client.list_collections()
                    click.echo(f"✅ Successfully connected to database")
                    click.echo(f"📚 Collections found: {len(collections_info)}")
                    for collection in collections_info:
                        click.echo(f"   - {collection.name}")
                else:
                    click.echo("❌ Failed to initialize database client")
            except Exception as e:
                click.echo(f"❌ Failed to connect to database: {e}")
                
    except Exception as e:
        click.echo(f"❌ Error checking database: {e}")

@cli.command()
def reset_db():
    """Reset the ChromaDB database (WARNING: This will delete all data!)"""
    try:
        from backend.config import config
        import shutil
        
        db_path = Path(os.path.join(config.index_folder, "chroma_db"))
        
        if not click.confirm(f"⚠️  This will permanently delete all indexed data in {db_path}. Continue?"):
            click.echo("❌ Operation cancelled")
            return
            
        if db_path.exists():
            shutil.rmtree(db_path)
            click.echo(f"✅ Database directory deleted: {db_path}")
        else:
            click.echo(f"ℹ️  Database directory does not exist: {db_path}")
            
        click.echo("✅ Database reset complete. You can now run indexing commands.")
        
    except Exception as e:
        click.echo(f"❌ Error resetting database: {e}")

if __name__ == '__main__':
    cli()
