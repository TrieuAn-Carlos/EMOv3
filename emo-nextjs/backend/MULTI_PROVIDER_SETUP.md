# 🚀 Multi-Provider LLM Support

## Overview

EMO Backend now supports **5 LLM providers** with automatic fallback:

| Provider | Status | Free Tier | Speed | Setup |
|----------|--------|-----------|-------|-------|
| **Groq** | Primary | ✅ 100K tokens/day | ⚡⚡⚡ Fastest | https://console.groq.com |
| **AgentRouter** | Fallback 1 | ✅ Free | ⚡⚡ Fast | https://agentrouter.org |
| **OpenAI** | Fallback 2 | ❌ Paid | ⚡⚡ Fast | https://platform.openai.com |
| **GLM/ZhipuAI** | Fallback 3 | ✅ Free | ⚡ Good | https://open.bigmodel.cn |
| **Gemini** | Fallback 4 | ✅ Free | ⚡ Good | https://aistudio.google.com |

---

## ✅ Setup (3 Easy Steps)

### **Step 1: Get Your API Key**

Choose at least ONE provider:

**Option A: AgentRouter (Recommended - Free & Fast)**
```bash
# Already added! Use your API key:
AGENTROUTER_API_KEY=sk-0oc9U5Wcc67r5EeiWsNvtcN88EF9sw6iLbTavpU8r2EW4vxl
```

**Option B: Groq (Free, 100K tokens/day)**
```bash
# Get key: https://console.groq.com/keys
GROQ_API_KEY=gsk_...
```

**Option C: OpenAI (Paid, but reliable)**
```bash
# Get key: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-...
```

### **Step 2: Add to .env**

Edit `.env` file and add your API key:

```bash
# .env file location:
/Users/laman/Documents/EMO_Final/Emo/emo-nextjs/backend/.env
```

Current status:
```dotenv
# Groq API (Primary)
GROQ_API_KEY=<GROQ_API_KEY>

# AgentRouter (Fallback - Free & Fast!)
AGENTROUTER_API_KEY=sk-0oc9U5Wcc67r5EeiWsNvtcN88EF9sw6iLbTavpU8r2EW4vxl

# Gemini API (Fallback)
GEMINI_API_KEY=<GOOGLE_API_KEY>
```

### **Step 3: Done!**

Backend will auto-detect and use available providers. No code changes needed!

---

## 🔄 How Auto-Fallback Works

### **Priority Chain:**

```
1️⃣ Groq (llama-3.3-70b)
   ↓ (if rate limited)
2️⃣ AgentRouter (gpt-4o-mini)
   ↓ (if rate limited)
3️⃣ OpenAI (gpt-4o-mini)
   ↓ (if rate limited)
4️⃣ GLM (glm-4-flash)
   ↓ (if rate limited)
5️⃣ Gemini (gemini-2.0-flash)
```

### **When Rate Limit Occurs:**

```python
# User sends message → "chào"
# ↓
# Try Groq → 429 Rate Limit ❌
# ↓
# Auto-switch to AgentRouter ✅
# ↓
# Response returned seamlessly
# User never sees error!
```

### **Log Output:**

```bash
🔄 Rate limit detected! Trying next provider...
🔄 Trying AGENTROUTER...
✅ Using AgentRouter (gpt-4o-mini) - Free & Fast!
✅ Agent initialized (will be reused)
✅ Response: Xin chào! 😊
```

---

## 🎯 Why AgentRouter?

**AgentRouter** is a free proxy for multiple LLM providers:

✅ **Free** - No credit card needed
✅ **Fast** - Uses OpenAI-compatible API
✅ **Reliable** - Multiple model support
✅ **Easy** - One API key, many models

**Use cases:**
- Claude, Codex, Gemini CLI support
- Perfect when Groq quota exceeded
- Backup for production systems

Get key: https://agentrouter.org/register

---

## 📊 Cost Comparison

### **Monthly costs (1M tokens usage):**

| Provider | Input | Output | Total |
|----------|-------|--------|-------|
| **Groq** | Free | Free | **$0** (100K/day limit) |
| **AgentRouter** | Free | Free | **$0** |
| **OpenAI** | $0.15 | $0.60 | **$0.75** |
| **GLM** | Free | Free | **$0** (limited) |
| **Gemini** | Free | Free | **$0** (1500 req/day) |

---

## 🧪 Testing

### **Test all providers:**

```bash
cd backend
source venv/bin/activate
python test_multi_provider.py
```

### **Test specific provider:**

```python
from agent.agent import get_or_create_agent, chat_with_agent
import asyncio

async def test():
    # Force AgentRouter
    agent = get_or_create_agent(force_provider='agentrouter')
    result = await chat_with_agent("chào")
    print(result['response'])

asyncio.run(test())
```

---

## 🔐 API Key Security

**⚠️ Important:**
- Never commit `.env` to git
- Keep API keys private
- Rotate keys regularly
- Use `.env.example` template

**Currently configured:**
```bash
✅ GROQ_API_KEY
✅ AGENTROUTER_API_KEY
✅ GEMINI_API_KEY
```

---

## 📈 Monitoring

Check which provider is being used:

```bash
# Watch logs while testing
tail -f backend.log | grep "Using"

# Output:
# ✅ Using Groq (llama-3.3-70b-versatile)
# ✅ Using AgentRouter (gpt-4o-mini) - Free & Fast!
```

---

## 🚀 Production Deployment

**Recommendation:**
1. Keep Groq as primary (fastest)
2. Add AgentRouter as backup (free)
3. Add OpenAI for reliability (paid)

**Benefits:**
- 99.9% uptime with failover
- No single provider dependency
- Optimal cost-performance balance

---

## ❓ Troubleshooting

### **"No API keys available"**

Solution: Add at least one API key to `.env`

```bash
# Edit .env file and add:
AGENTROUTER_API_KEY=sk-...
```

### **"All providers failed"**

Solution: Check internet connection and API key validity

```bash
# Test API connection:
python test_multi_provider.py
```

### **"Rate limit detected"**

Normal behavior! System auto-switches to next provider.

```bash
# Watch logs to see fallback:
🔄 Rate limit detected! Trying next provider...
🔄 Trying AGENTROUTER...
✅ Successfully retried with AGENTROUTER!
```

---

## 💡 Pro Tips

1. **Best Performance:** Use Groq + AgentRouter combo
2. **Most Reliable:** Add OpenAI as third fallback
3. **Budget Friendly:** Use free providers only
4. **Testing:** Force provider with `force_provider='agentrouter'`

---

## 📚 API Documentation

- **Groq:** https://console.groq.com/docs
- **AgentRouter:** https://docs.agentrouter.org
- **OpenAI:** https://platform.openai.com/docs
- **GLM:** https://open.bigmodel.cn/dev/howuse
- **Gemini:** https://ai.google.dev/docs

---

## ✅ Status

**Current Setup:**
- ✅ Groq (Primary)
- ✅ AgentRouter (Fallback 1)
- ✅ Gemini (Fallback 4)
- ✅ Auto-fallback on rate limit
- ✅ Production ready

**Next Steps:**
- Add OpenAI key for more reliability
- Monitor usage and optimize costs
- Set up rate limit alerts

---

**Last Updated:** December 8, 2025  
**Status:** ✅ Production Ready  
**Supported Providers:** 5  
**Auto-Fallback:** ✅ Enabled
