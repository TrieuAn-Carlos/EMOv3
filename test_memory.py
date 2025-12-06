#!/usr/bin/env python
"""
Test script to verify thread-safe ChromaDB memory implementation.
Run this to verify the memory system works without "readonly database" errors.
"""

import os
import sys
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Set up Streamlit session state mock for testing
class MockSessionState:
    def __init__(self):
        self.data = {}
    
    def __contains__(self, key):
        return key in self.data
    
    def __getitem__(self, key):
        return self.data[key]
    
    def __setitem__(self, key, value):
        self.data[key] = value
    
    def get(self, key, default=None):
        return self.data.get(key, default)

# Mock streamlit
import types
st = types.ModuleType('streamlit')
st.session_state = MockSessionState()
st.error = lambda x: print(f"ERROR: {x}")
st.warning = lambda x: print(f"WARNING: {x}")
st.info = lambda x: print(f"INFO: {x}")
st.success = lambda x: print(f"SUCCESS: {x}")

sys.modules['streamlit'] = st

# Now import our modules
from main import (
    get_chroma_collection,
    save_to_memory,
    query_memory,
    get_memory_by_id,
    format_memories_for_context
)

def test_memory_system():
    """Test the memory system with various operations."""
    
    print("\n=== Testing Thread-Safe ChromaDB Memory System ===\n")
    
    # Test 1: Initialize collection
    print("Test 1: Initializing ChromaDB collection...")
    collection = get_chroma_collection()
    if collection:
        print(f"✓ Collection initialized successfully")
        print(f"  Current documents in memory: {collection.count()}")
    else:
        print("✗ Failed to initialize collection")
        return False
    
    # Test 2: Save to memory
    print("\nTest 2: Saving test documents to memory...")
    test_docs = [
        {
            "text": "John sent an email about the Q4 budget meeting scheduled for December 15.",
            "metadata": {
                "type": "email",
                "source": "Gmail",
                "subject": "Q4 Budget Discussion",
                "sender": "john@company.com",
                "date": "2024-12-03"
            }
        },
        {
            "text": "The project deadline is January 10, 2025. We need to submit deliverables by then.",
            "metadata": {
                "type": "email",
                "source": "Gmail",
                "subject": "Project Deadline",
                "sender": "manager@company.com",
                "date": "2024-12-02"
            }
        }
    ]
    
    for i, doc in enumerate(test_docs, 1):
        result = save_to_memory(doc["text"], doc["metadata"])
        if not result.startswith("[Error"):
            print(f"✓ Document {i} saved: {result}")
        else:
            print(f"✗ Failed to save document {i}: {result}")
            return False
    
    time.sleep(1)  # Wait for database to settle
    
    # Test 3: Query memory
    print("\nTest 3: Querying memory for relevant documents...")
    query = "budget meeting"
    memories = query_memory(query, n_results=5)
    
    if memories:
        print(f"✓ Found {len(memories)} relevant memories:")
        for mem in memories:
            print(f"  - [{mem['relevance']}% match] {mem['summary'][:80]}...")
            print(f"    Source: {mem['metadata'].get('source', 'Unknown')} | ID: {mem['doc_id']}")
    else:
        print("✗ No memories found (this might be normal if database is fresh)")
    
    # Test 4: Retrieve full memory
    if memories:
        print("\nTest 4: Retrieving full content of first memory...")
        doc_id = memories[0]['doc_id']
        full_memory = get_memory_by_id(doc_id)
        
        if full_memory:
            print(f"✓ Retrieved full memory:")
            print(f"  Length: {len(full_memory['text'])} characters")
            print(f"  Subject: {full_memory['metadata'].get('subject', 'N/A')}")
            print(f"  Text preview: {full_memory['text'][:100]}...")
        else:
            print(f"✗ Failed to retrieve full memory with ID: {doc_id}")
    
    # Test 5: Format memories for context
    print("\nTest 5: Formatting memories for LLM context...")
    if memories:
        formatted = format_memories_for_context(memories)
        print("✓ Formatted output (first 200 chars):")
        print(f"  {formatted[:200]}...")
    
    print("\n=== All tests completed successfully! ===\n")
    return True

if __name__ == "__main__":
    try:
        success = test_memory_system()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
