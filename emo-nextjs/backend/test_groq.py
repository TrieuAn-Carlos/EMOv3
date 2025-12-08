#!/usr/bin/env python3
"""
Test Groq Model Configuration
==============================
Verify that the new Llama 3.3 70B model works correctly.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import GROQ_API_KEY, GROQ_MODEL, TEMPERATURE


def test_groq_config():
    """Test Groq configuration."""
    print("🔍 Checking Groq Configuration...")
    print(f"   Model: {GROQ_MODEL}")
    print(f"   Temperature: {TEMPERATURE}")
    print(f"   API Key: {'✅ Set' if GROQ_API_KEY else '❌ Missing'}")
    
    if not GROQ_API_KEY:
        print("\n❌ ERROR: GROQ_API_KEY not found!")
        print("   Please set it in .env file:")
        print("   GROQ_API_KEY=your_api_key_here")
        return False
    
    print("\n✅ Configuration looks good!")
    return True


def test_groq_connection():
    """Test actual connection to Groq API."""
    print("\n🧪 Testing Groq API connection...")
    
    try:
        from langchain_groq import ChatGroq
        
        llm = ChatGroq(
            model=GROQ_MODEL,
            api_key=GROQ_API_KEY,
            temperature=TEMPERATURE,
        )
        
        print(f"   Sending test message to {GROQ_MODEL}...")
        response = llm.invoke("Say 'Hello from EMO!' in one short sentence.")
        
        print(f"   Response: {response.content}")
        print("\n✅ Groq API connection successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {str(e)}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("EMO Backend - Groq Model Test")
    print("=" * 60)
    print()
    
    # Test 1: Configuration
    if not test_groq_config():
        sys.exit(1)
    
    # Test 2: Connection
    if not test_groq_connection():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 All tests passed! Groq is ready to use.")
    print("=" * 60)


if __name__ == "__main__":
    main()
