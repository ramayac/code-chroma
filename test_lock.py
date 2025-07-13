#!/usr/bin/env python3
"""
Test script to simulate database locking by holding the connection open.
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.chroma_client import ChromaClient
from backend.logger import get_logger

logger = get_logger()

def main():
    print("🔒 Testing database locking...")
    
    try:
        # Create a client that will hold the database connection
        client = ChromaClient()
        print("✅ Database connection established")
        
        # Create a collection to ensure the database is actively used
        collection = client.get_or_create_collection("test_lock")
        print("✅ Test collection created")
        
        print("🔄 Holding database connection for 30 seconds...")
        print("   Try running 'python cli.py index-all --max-repos 1' in another terminal")
        print("   You should see the file locking error message")
        
        time.sleep(30)
        
        print("✅ Test completed - releasing database connection")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
