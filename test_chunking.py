from backend.chroma_indexer import ChromaIndexer

def test_chunking():
    """Test chunking with different file types"""
    
    # Test 1: Python code file
    python_doc = {
        'content': '''def hello_world():
    """Simple hello world function"""
    print('Hello, world!')
    return 'success'

class MyClass:
    """Example class for testing"""
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
    
    def set_value(self, new_value):
        self.value = new_value

def another_function():
    """This is a longer function with multiple lines to test chunking"""
    results = []
    for i in range(10):
        result = f'Number: {i}'
        results.append(result)
        print(result)
    return results

def final_function():
    """Final function to test boundary detection"""
    return "done"
''',
        'filename': 'test.py',
        'relative_path': 'test.py',
        'full_path': '/path/to/test.py',
        'language': 'Python'
    }
    
    # Test 2: Text file
    text_doc = {
        'content': '''This is a long text document that should be chunked properly.
        
It has multiple paragraphs and sections that need to be processed.
The chunking algorithm should handle this gracefully.

Here is another paragraph with more content to test the chunking behavior.
We want to make sure that the chunks are meaningful and preserve context.

This is the final paragraph of our test document.
It should be included in the appropriate chunk.''',
        'filename': 'test.txt',
        'relative_path': 'test.txt',
        'full_path': '/path/to/test.txt',
        'language': 'Text'
    }
    
    indexer = ChromaIndexer()
    config_dict = {
        'chunk_size': 300,  # Medium chunk size for testing
        'chunk_overlap': 50
    }
    
    print("=== PYTHON FILE CHUNKING ===")
    python_chunks = indexer._chunk_documents([python_doc], config_dict)
    print(f'Generated {len(python_chunks)} chunks from Python file:')
    for i, chunk in enumerate(python_chunks):
        print(f'\nChunk {i}:')
        print(f'Size: {len(chunk["content"])} characters')
        print(f'Chunk type: {chunk["chunk_type"]}')
        print(f'Language: {chunk["language"]}')
        print(f'Content:\n{chunk["content"][:200]}...')
    
    print("\n\n=== TEXT FILE CHUNKING ===")
    text_chunks = indexer._chunk_documents([text_doc], config_dict)
    print(f'Generated {len(text_chunks)} chunks from text file:')
    for i, chunk in enumerate(text_chunks):
        print(f'\nChunk {i}:')
        print(f'Size: {len(chunk["content"])} characters')
        print(f'Content:\n{chunk["content"][:200]}...')
    
    print("\n\n=== SMALL FILE TEST ===")
    small_doc = {
        'content': 'Small file content',
        'filename': 'small.txt',
        'relative_path': 'small.txt',
        'full_path': '/path/to/small.txt',
        'language': 'Text'
    }
    
    small_chunks = indexer._chunk_documents([small_doc], config_dict)
    print(f'Small file generated {len(small_chunks)} chunks (should be 1):')
    for i, chunk in enumerate(small_chunks):
        print(f'Chunk {i}: {chunk["content"]}')

if __name__ == "__main__":
    test_chunking()
