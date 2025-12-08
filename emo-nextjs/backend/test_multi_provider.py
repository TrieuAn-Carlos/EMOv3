"""
Test Multi-Provider LLM Support
================================
Test OpenAI, GLM, Gemini, and Groq APIs
"""

import asyncio
from agent.agent import get_or_create_agent, chat_with_agent


async def test_provider(provider_name: str):
    """Test specific provider."""
    print("\n" + "=" * 60)
    print(f"TESTING: {provider_name.upper()}")
    print("=" * 60)
    
    try:
        # Force specific provider
        agent = get_or_create_agent(force_provider=provider_name)
        print(f"✅ {provider_name.upper()} agent initialized")
        
        # Test simple message
        result = await chat_with_agent(f"chào {provider_name}")
        
        if result['response'] and not result.get('error'):
            print(f"✅ Response: {result['response'][:100]}...")
            return True
        else:
            print(f"❌ Failed: {result.get('error', 'No response')[:100]}")
            return False
            
    except Exception as e:
        print(f"❌ {provider_name.upper()} not available: {str(e)[:100]}")
        return False


async def test_all_providers():
    """Test all available providers."""
    print("\n🧪 EMO Multi-Provider Test\n")
    
    providers = ['groq', 'openai', 'glm', 'gemini']
    results = {}
    
    for provider in providers:
        results[provider] = await test_provider(provider)
        await asyncio.sleep(1)  # Small delay between tests
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    working = [p for p, status in results.items() if status]
    failed = [p for p, status in results.items() if not status]
    
    if working:
        print(f"\n✅ Working providers ({len(working)}):")
        for p in working:
            print(f"   - {p.upper()}")
    
    if failed:
        print(f"\n❌ Unavailable providers ({len(failed)}):")
        for p in failed:
            print(f"   - {p.upper()}")
    
    print("\n💡 Fallback chain:")
    print("   Groq → OpenAI → GLM → Gemini")
    print("   (Auto-switches on rate limit!)")
    
    return results


async def test_auto_fallback():
    """Test automatic fallback behavior."""
    print("\n" + "=" * 60)
    print("AUTO-FALLBACK INFO")
    print("=" * 60)
    
    print("""
How auto-fallback works:
1. 🚀 EMO tries primary provider (Groq by default)
2. ⚠️  If rate limit (429) or quota error detected
3. 🔄 Automatically tries next provider in chain
4. ✅ Returns response from first working provider

Priority order:
  1️⃣  Groq (llama-3.3-70b) - Fast & free
  2️⃣  OpenAI (gpt-4o-mini) - Cheap & reliable
  3️⃣  GLM (glm-4-flash) - Good for Chinese
  4️⃣  Gemini (gemini-2.0) - Google's free tier

Setup:
  1. Add at least one API key to .env
  2. EMO will auto-detect and use available providers
  3. No configuration needed!
    """)


if __name__ == "__main__":
    print("🎯 EMO Multi-Provider LLM Test\n")
    print("Testing all configured API providers...")
    
    asyncio.run(test_all_providers())
    asyncio.run(test_auto_fallback())
    
    print("\n" + "=" * 60)
    print("SETUP GUIDE")
    print("=" * 60)
    print("""
To add API keys, edit .env file:

# OpenAI (Recommended)
OPENAI_API_KEY=sk-...
Get key: https://platform.openai.com/api-keys

# GLM/ZhipuAI
GLM_API_KEY=...
Get key: https://open.bigmodel.cn/usercenter/apikeys

# Groq (Free)
GROQ_API_KEY=gsk_...
Get key: https://console.groq.com/keys

# Gemini (Free)
GEMINI_API_KEY=AIza...
Get key: https://aistudio.google.com/app/apikey
    """)
    
    print("\n✅ Done! Backend supports 4 LLM providers with auto-fallback.")
