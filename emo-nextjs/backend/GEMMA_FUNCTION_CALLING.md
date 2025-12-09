# Gemma 3 27B Function Calling

Implementation of manual function calling for Gemma 3 27B based on [Google's official documentation](https://ai.google.dev/gemma/docs/capabilities/function-calling).

## Features

✅ **Manual Function Calling** - Structured JSON prompting for tool execution
✅ **4 Integrated Tools** - Gmail, Calendar, Web Search
✅ **Automatic Parsing** - Extracts tool calls from model output
✅ **Backward Compatible** - Works alongside existing Groq/Gemini agents
✅ **Smart Context** - Memory integration for better responses

## Usage

### Enable Gemma Agent

Add to `.env`:
```bash
USE_GEMMA=true
```

### API Request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tìm email từ Hoa",
    "session_id": "optional-session-id"
  }'
```

## Architecture

### 1. Tool Definitions

Tools are defined in structured JSON format:

```python
TOOL_DEFINITIONS = [
    {
        "name": "search_gmail",
        "description": "Search Gmail for emails matching a query",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    }
]
```

### 2. System Prompt

Gemma receives a system prompt with:
- Tool definitions in JSON format
- Function calling instructions
- Output format examples
- Conversation rules

### 3. Function Call Flow

```
User Message
     ↓
Gemma 3 27B → Decides if tool needed
     ↓
Outputs JSON:
{
  "thought": "Need to search Gmail",
  "tool_name": "search_gmail",
  "parameters": {"query": "from:Hoa"}
}
     ↓
Parser extracts tool call
     ↓
Tool execution
     ↓
Result back to Gemma
     ↓
Final response to user
```

### 4. Example Interaction

**User:** "Tìm email từ Hoa"

**Gemma Output:**
```json
{
  "thought": "Cần search Gmail để tìm email từ Hoa",
  "tool_name": "search_gmail",
  "parameters": {
    "query": "from:Hoa"
  }
}
```

**Tool Result:** [List of emails from Hoa]

**Gemma Response:** "Tôi đã tìm thấy 5 email từ Hoa. Đây là danh sách..."

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `search_gmail` | Search emails | `query`, `limit` |
| `get_email` | Get email content | `email_id` |
| `search_calendar` | Search calendar events | `query`, `time_min`, `time_max` |
| `search_web` | Web search via DuckDuckGo | `query`, `num_results` |

## Code Structure

### Main Files

```
backend/
├── agent/
│   ├── gemma_agent.py       # Gemma 3 27B agent implementation
│   ├── agent.py             # Groq/Gemini agents (default)
│   └── tools.py             # Tool definitions
├── core/
│   └── config.py            # USE_GEMMA toggle
└── routers/
    └── chat.py              # Router with Gemma support
```

### Key Classes

**`GemmaAgent`** - Main agent class
- `chat(message)` - Process message with function calling
- `parse_tool_call(text)` - Extract tool call from output
- `execute_tool(name, params)` - Execute tool

## Configuration

### Environment Variables

```bash
# Enable Gemma (default: false, uses Groq)
USE_GEMMA=true

# Google API Key (required for Gemma)
GEMINI_API_KEY=your_api_key_here

# Model selection (optional)
GEMMA_27B_MODEL=gemma-3-27b-it  # default
```

### Model Options

- `gemma-3-27b-it` - 27B parameters, best quality (default)
- `gemma-3-12b-it` - 12B parameters, faster, balanced latency

## Testing

```python
from agent.gemma_agent import get_gemma_agent
import asyncio

async def test():
    agent = get_gemma_agent()
    result = await agent.chat("Tìm email từ Hoa")
    print(result["response"])
    print(result["tools_used"])

asyncio.run(test())
```

## Performance

| Metric | Value |
|--------|-------|
| Model | Gemma 3 27B IT |
| Latency | ~2-4s per response |
| Function calling | Manual via JSON |
| Max iterations | 5 tool calls per message |
| Context window | 8K tokens |

## Comparison: Gemma vs Groq/Gemini

| Feature | Gemma 3 27B | Groq/Gemini |
|---------|-------------|-------------|
| Function calling | Manual (JSON) | Native (built-in) |
| Speed | Moderate | Fast (Groq) |
| Quality | High | Very High (GPT-4 level) |
| Cost | Free tier | Rate limited |
| Tools | 4 tools | 4 tools |
| Setup | Custom prompt | LangGraph |

## Troubleshooting

### Issue: Tool not called

**Solution:** Check if tool name in output matches definition:
```python
# In gemma_agent.py
TOOL_DEFINITIONS  # Check tool names here
```

### Issue: JSON parsing error

**Solution:** Gemma might output invalid JSON. The parser handles:
- JSON in markdown code blocks
- Direct JSON objects
- Extra text around JSON

### Issue: Import errors

**Solution:** Ensure imports are correct:
```python
from agent.gemma_agent import get_gemma_agent  # ✅
from core.config import USE_GEMMA              # ✅
```

## Future Enhancements

- [ ] Add more tools (Tasks, Notes, Weather)
- [ ] Support multi-turn conversations
- [ ] Streaming responses for Gemma
- [ ] Performance optimization (caching)
- [ ] Fine-tune prompt for Vietnamese

## References

- [Gemma Function Calling Documentation](https://ai.google.dev/gemma/docs/capabilities/function-calling)
- [Google AI Studio](https://aistudio.google.com/)
- [Gemma Models](https://ai.google.dev/gemma)

## License

MIT License - See root LICENSE file
