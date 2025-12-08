"""
Performance Test - Measure chat response time
"""

import asyncio
import time
from agent.agent import chat_with_agent


async def test_simple_greeting():
    """Test performance of simple greeting."""
    print("=" * 60)
    print("TESTING: Simple Greeting Performance")
    print("=" * 60)
    
    test_messages = [
        "chào",
        "hello",
        "hi bạn",
    ]
    
    for msg in test_messages:
        print(f"\n>>> Message: '{msg}'")
        
        start = time.time()
        result = await chat_with_agent(msg)
        elapsed = time.time() - start
        
        print(f"⏱️  Time: {elapsed:.2f}s")
        print(f"📝 Response: {result['response'][:100]}...")
        print(f"🔧 Tools used: {result['tools_used']}")
        
        if elapsed < 5:
            print("✅ PASSED - Under 5s")
        else:
            print("❌ FAILED - Over 5s")


async def test_complex_query():
    """Test performance of complex query."""
    print("\n" + "=" * 60)
    print("TESTING: Complex Query Performance")
    print("=" * 60)
    
    msg = "tạo task nhắc tôi họp lúc 3pm ngày mai"
    
    print(f"\n>>> Message: '{msg}'")
    
    start = time.time()
    result = await chat_with_agent(msg)
    elapsed = time.time() - start
    
    print(f"⏱️  Time: {elapsed:.2f}s")
    print(f"📝 Response: {result['response'][:150]}...")
    print(f"🔧 Tools used: {result['tools_used']}")
    
    if elapsed < 10:
        print("✅ PASSED - Under 10s")
    else:
        print("❌ FAILED - Over 10s")


if __name__ == "__main__":
    print("\n🚀 EMO Performance Test\n")
    
    asyncio.run(test_simple_greeting())
    asyncio.run(test_complex_query())
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\n✅ Expected:")
    print("  - Simple greetings: < 5s")
    print("  - Complex queries: < 10s")
    print("\n📊 Optimizations applied:")
    print("  1. Lazy agent initialization (reuse)")
    print("  2. Skip memory query for greetings")
    print("  3. Reduced memory results (5→2)")
    print("  4. Removed session history loading")
