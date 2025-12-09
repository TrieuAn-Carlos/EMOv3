"""
Check LLM Connection
====================
Simple script to verify backend LLM configuration.
Usage: python backend/scripts/check_llm.py
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.append(str(backend_path))

try:
    from core.llm import get_llm, LLM_PROVIDER
    from langchain_core.messages import HumanMessage
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you are running this from the project root and venv is active.")
    sys.exit(1)

def check_connection():
    print(f"🔍 Checking LLM Connection")
    print(f"Selected Provider: {LLM_PROVIDER}")
    
    try:
        # Initialize LLM
        llm = get_llm(max_tokens=50)
        print(f"✅ LLM Client initialized successfully")
        
        # Test generation
        print("💬 Sending test message...")
        msg = HumanMessage(content="Hello! return only the word 'Connected' if you see this.")
        response = llm.invoke([msg])
        
        print(f"✅ Response received: {response.content}")
        print("🎉 Configuration is valid!")
        
    except Exception as e:
        print(f"\n❌ Connection Failed!")
        print(f"Error: {e}")
        print("\nPossible solutions:")
        print("1. Check your .env file")
        print("2. Verify API Keys and Base URLs")
        print("3. Ensure the LLM server is running (if local/LitGPT)")

if __name__ == "__main__":
    check_connection()
