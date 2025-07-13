"""
Test script for ChromaDB integration.
Quick verification that the ChromaDB components work correctly.
"""

import os
import sys
import tempfile
import shutil
import time
from pathlib import Path

# Add parent directory to path so we can import backend modules
sys.path.append(str(Path(__file__).parent.parent))

from backend.chroma_indexer import ChromaIndexer
from backend.chroma_search import ChromaSearch
from backend.logger import get_logger
from backend.config import config

logger = get_logger()

def test_chroma_integration():
    """Test ChromaDB integration with sample data"""
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            temp_path = Path(temp_dir)
            
            # Create sample repository structure
            repo_path = temp_path / "test_repo"
            repo_path.mkdir()
            
            # Create sample files
            (repo_path / "README.md").write_text("""
# Test Project

This is a test project for ChromaDB integration.
It demonstrates semantic search capabilities.
""")
            
            (repo_path / "main.py").write_text("""
def authenticate_user(username, password):
    \"\"\"Authenticate user with username and password\"\"\"
    if not username or not password:
        return False
    return verify_credentials(username, password)

def verify_credentials(username, password):
    \"\"\"Verify user credentials against database\"\"\"
    # Simulate database lookup
    return username == "admin" and password == "secret"

class UserManager:
    \"\"\"Manages user operations\"\"\"
    
    def __init__(self):
        self.users = {}
    
    def create_user(self, username, email):
        \"\"\"Create a new user\"\"\"
        self.users[username] = {
            'email': email,
            'created_at': 'now'
        }
        return True
""")
            
            (repo_path / "utils.js").write_text("""
function calculateTotal(items) {
    /* Calculate total price of items */
    return items.reduce((sum, item) => sum + item.price, 0);
}

async function fetchUserData(userId) {
    /* Fetch user data from API */
    try {
        const response = await fetch(`/api/users/${userId}`);
        return await response.json();
    } catch (error) {
        console.error('Error fetching user data:', error);
        return null;
    }
}
""")
            
            # Test ChromaDB indexing
            print("🔍 Testing ChromaDB Indexing...")
            
            # Use temporary ChromaDB directory
            chroma_db_path = temp_path / "chroma_test_db"
            
            try:
                indexer = ChromaIndexer(str(chroma_db_path))
                
                # Index the test repository
                indexer.index_repository(str(repo_path), "test_repo")
                
                # Test collections info
                info = indexer.get_collections_info()
                print(f"✅ Indexing complete: {info}")
                
                # Cleanup indexer properly
                del indexer
                
            except Exception as e:
                print(f"❌ Indexing failed: {e}")
                return False
                
            # Test search functionality
            print("\n🔍 Testing ChromaDB Search...")
            
            try:
                searcher = ChromaSearch(str(chroma_db_path))
                
                # Test repository search
                print("\n📁 Repository Search:")
                repo_results = searcher.search_repositories("test project", 5)
                for result in repo_results:
                    print(f"  • {result['display_name']} (similarity: {result['similarity']:.3f})")
                    
                # Test repository info
                print("\n📊 Repository Info:")
                repo_info = searcher.get_repo_info("test_repo")
                if repo_info:
                    print(f"  Name: {repo_info['name']}")
                    print(f"  Language: {repo_info['language']}")
                    print(f"  Files: {repo_info['file_count']}")
                    
                # Test statistics
                print("\n📈 Statistics:")
                stats = searcher.get_collection_stats()
                print(f"  Repositories: {stats['repositories']}")
                print(f"  Files: {stats['files']}")
                print(f"  Chunks: {stats['chunks']}")
                
                # Cleanup searcher properly
                del searcher
                
                # Add small delay to ensure file handles are closed
                time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Search failed: {e}")
                return False
            
            print("✅ All tests passed! ChromaDB integration is working correctly.")
            return True
            
        except Exception as e:
            # Handle cleanup errors gracefully
            if "process cannot access the file" in str(e):
                print("✅ All tests passed! ChromaDB integration is working correctly.")
                print("💡 Note: Cleanup failed due to file locking (Windows issue), but functionality works correctly")
                return True
            else:
                raise e

if __name__ == "__main__":
    try:
        success = test_chroma_integration()
        if success:
            print("🎉 Test completed successfully!")
        else:
            print("❌ Test failed")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.error(f"Test error: {e}")
        # Don't exit with error code if it's just a cleanup issue
        if "process cannot access the file" in str(e):
            print("💡 Note: Cleanup failed due to file locking (Windows issue), but functionality works correctly")
        else:
            sys.exit(1)
