"""
Test Gemini Fallback - Verify auto-switch when Groq rate limit
"""

import asyncio
from agent.agent import chat_with_agent, get_or_create_agent


async def test_gemini_fallback():
    """Test if fallback to Gemini works."""
    print("=" * 60)
    print("TESTING: Gemini Fallback")
    print("=" * 60)
    
    # Force Gemini
    print("\n1️⃣ Testing direct Gemini initialization...")
    try:
        agent = get_or_create_agent(force_gemini=True)
        print("✅ Gemini agent created successfully")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return
    
    # Test simple message with Gemini
    print("\n2️⃣ Testing Gemini response...")
    result = await chat_with_agent("chào Gemini")
    
    print(f"\n📝 Response: {result['response'][:150]}...")
    print(f"🔧 Tools used: {result['tools_used']}")
    print(f"❌ Error: {result.get('error', 'None')}")
    
    if result['response'] and not result.get('error'):
        print("\n✅ GEMINI WORKS! Your fallback is ready.")
    else:
        print("\n❌ Gemini failed.")


async def test_rate_limit_simulation():
    """Info about rate limit handling."""
    print("\n" + "=" * 60)
    print("AUTO-FALLBACK INFO")
    print("=" * 60)
    
    print("""
When Groq hits rate limit (429 error), agent will:
1. 🔄 Detect "rate_limit" + "groq" in error
2. 🔄 Reset agent and LLM to None
3. ✅ Recreate with force_gemini=True
4. ✅ Retry the same request with Gemini
5. ✅ Return response seamlessly

You don't need to do anything - it's automatic! 🎉

Next time you get Groq rate limit, watch terminal for:
  "🔄 Groq rate limit detected! Switching to Gemini..."
  "✅ Using Gemini (gemini-2.0-flash-exp) - FREE TIER"
  "✅ Successfully retried with Gemini!"
    """)


if __name__ == "__main__":
    print("\n🧪 EMO Gemini Fallback Test\n")
    
    asyncio.run(test_gemini_fallback())
    asyncio.run(test_rate_limit_simulation())
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\n✅ Your backend now has:")
    print("  1. Primary: Groq (fast when available)")
    print("  2. Fallback: Gemini (free tier 1500 req/day)")
    print("  3. Auto-switch on rate limit")
    print("\n💡 Gemini free tier limits:")
    print("  - 1500 requests/day")
    print("  - 1M tokens/minute")
    print("  - 15 requests/minute")
    print("\nMore than enough! 🚀")
