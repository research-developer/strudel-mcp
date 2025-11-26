# Strudel Agent Setup Guide

## 🎉 What's New

Your Strudel-MCP project now includes a **Claude Agent** that you can chat with directly from the browser! The agent can:

- 🎵 Control the music using the Strudel MCP tools
- 💬 Have conversations about the music
- ⏰ Schedule pattern changes with a queue system
- 🔄 Auto-fall back to agent reasoning if find/replace fails

---

## Architecture

```
Browser (localhost:8080)
├── Music Player (left panel)
│   └── Tone.js audio engine
│   └── Polls patterns.js every 2s
└── Chat UI (right panel)
    └── Send messages to Claude
        ↓
FastAPI Server (strudel_server.py)
├── POST /api/chat - Chat with Claude
├── POST /api/queue - Schedule changes
└── GET /api/queue - View queue
        ↓
Claude Agent SDK (v0.1.9)
├── ClaudeSDKClient with persistent context
├── Configured with Strudel MCP server
└── Access to all strudel_* tools
        ↓
Strudel MCP Server (strudel_mcp.py)
├── Runs as subprocess via MCP protocol
└── 5 tools for pattern control
```

---

## Quick Start

### 1. Set Your API Key

Get your key from https://console.anthropic.com/

**Option A: Use .env file (recommended)**

Copy the example file and edit it:
```bash
cp .env.example .env
```

Then edit `.env` and add your key:
```bash
ANTHROPIC_API_KEY=your_api_key_here

# Optional: Custom API endpoint
# ANTHROPIC_BASE_URL=https://api.anthropic.com
```

**Option B: Environment variable**
```bash
export ANTHROPIC_API_KEY='your_api_key_here'
```

### 2. Start the Server

**Option A: Run directly**
```bash
cd /Users/preston/Projects/strudel-mcp
python3 strudel_server.py
```

**Option B: Run with uvicorn (for development)**
```bash
uvicorn strudel_server:app --reload --port 8080
```

### 3. Open in Browser

Navigate to: **http://localhost:8080**

- Click to start audio
- Use the chat panel on the right to talk to Claude!

---

## Using the Chat Interface

### Example Conversations

**Get Current State:**
```
You: What's currently playing?
Claude: [Uses strudel_get_pattern to show current BPM, chords, melody, etc.]
```

**Make Changes:**
```
You: Make it darker and slower
Claude: [Uses strudel_suggest_modifications, then strudel_edit_pattern]
        [Music changes within 2 seconds!]
```

**Analyze:**
```
You: How complex is this pattern?
Claude: [Uses strudel_get_pattern_info to show analysis]
```

**Schedule Changes:**
```
You: Change the BPM to 20 in 30 seconds
Claude: [Schedules the change in the queue]
```

---

## API Endpoints

### POST /api/chat

Send a message to Claude and get a response.

**Request:**
```json
{
  "message": "Make it more ambient"
}
```

**Response:**
```json
{
  "response": "I'll make the music more spacious and ambient...",
  "tool_calls": [
    {"name": "strudel_suggest_modifications", "id": "..."},
    {"name": "strudel_edit_pattern", "id": "..."}
  ]
}
```

### POST /api/queue

Schedule a find/replace change.

**Request:**
```json
{
  "find": "bpm: 30",
  "replace": "bpm: 20",
  "delay_seconds": 30,
  "description": "Slow down to 20 BPM"
}
```

**Response:**
```json
{
  "change_id": 0,
  "execute_at": "2025-01-24T15:30:00",
  "status": "scheduled"
}
```

### GET /api/queue

View all pending changes.

**Response:**
```json
{
  "pending_changes": [...],
  "total_count": 3
}
```

### DELETE /api/queue/{change_id}

Cancel a scheduled change.

---

## Change Queue System

The queue system allows you to schedule pattern changes:

### How It Works

1. **Add to Queue:** POST a find/replace change with a delay
2. **Scheduler:** APScheduler runs the change at the scheduled time
3. **Find/Replace:** Tries to find and replace text in patterns.js
4. **Agent Fallback:** If find fails, asks Claude to make the change

### Example: Schedule Multiple Changes

```python
import requests

# Schedule 3 changes over time
requests.post('http://localhost:8080/api/queue', json={
    "find": "bpm: 30",
    "replace": "bpm: 25",
    "delay_seconds": 10,
    "description": "First change: slow to 25 BPM"
})

requests.post('http://localhost:8080/api/queue', json={
    "find": "filter: 600",
    "replace": "filter: 400",
    "delay_seconds": 20,
    "description": "Second change: darken filter"
})

requests.post('http://localhost:8080/api/queue', json={
    "find": "drums: {",
    "replace": "// drums: {",
    "delay_seconds": 30,
    "description": "Third change: comment out drums"
})
```

The music will evolve over 30 seconds!

---

## Agent Configuration

The agent is configured in `strudel_server.py` with:

### System Prompt

```python
"You are a music composition assistant controlling the Strudel live ambient
music environment. You have access to tools that let you view, analyze, and
edit musical patterns..."
```

### Allowed Tools

- `strudel_get_pattern` - View current pattern
- `strudel_validate_pattern` - Check if valid
- `strudel_edit_pattern` - Modify pattern
- `strudel_get_pattern_info` - Analyze pattern
- `strudel_suggest_modifications` - Get suggestions

### Permission Mode

```python
permission_mode="auto"  # Tools run automatically
```

This means Claude can use tools without asking for permission each time.

---

## Troubleshooting

### Chat Returns Error

**Problem:** `ANTHROPIC_API_KEY not set`

**Solution:**
```bash
export ANTHROPIC_API_KEY='your_key_here'
python3 strudel_server.py
```

### Server Won't Start

**Problem:** Port 8080 already in use

**Solution:**
```bash
# Find process using port 8080
lsof -ti:8080 | xargs kill -9

# Or use a different port
uvicorn strudel_server:app --port 8081
```

### MCP Server Not Working

**Problem:** Agent can't access strudel tools

**Check:**
1. Is `strudel_mcp.py` in the same directory?
2. Check server logs for MCP connection errors
3. Verify with health check: http://localhost:8080/health

### Music Not Changing

**Problem:** Pattern edits don't affect music

**Check:**
1. Is the browser still polling? (Check browser console)
2. Is patterns.js being modified? (Check timestamps)
3. Try hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

---

## Advanced Usage

### Custom System Prompt

Edit `strudel_server.py` and change the `system_prompt` in `ClaudeAgentOptions`:

```python
system_prompt="You are a jazz composition AI specializing in modal harmony..."
```

### Add More Tools

To give the agent access to additional tools:

1. Add tool names to `allowed_tools` list
2. Ensure they're available via MCP or custom tools
3. Restart the server

### Stream Responses

To enable streaming responses (see words appear in real-time):

1. Update the chat endpoint to use `receive_response()` generator
2. Modify the browser JavaScript to handle Server-Sent Events
3. Return a `StreamingResponse` from FastAPI

---

## Files Created

### New Files

- `strudel_server.py` (600+ lines) - FastAPI server with Agent SDK
- `AGENT_SETUP.md` (this file) - Setup and usage guide

### Modified Files

- `index.html` - Added chat UI panel
- `requirements.txt` - Added new dependencies

### Unchanged Files

- `strudel_mcp.py` - MCP server (works as before)
- `patterns.js` - Music pattern file
- `test_server.py` - Test suite

---

## Dependencies Installed

```
fastapi>=0.115.0          # Web framework
uvicorn[standard]>=0.32.0 # ASGI server
python-multipart>=0.0.9   # Form handling
claude-agent-sdk>=0.1.9   # Claude Agent SDK (latest!)
apscheduler>=3.10.0       # Task scheduling
```

---

## Next Steps

### Ideas to Explore

1. **Voice Control:** Add speech-to-text for voice commands
2. **Pattern Library:** Save/load favorite patterns
3. **Visualization:** Add audio visualizer
4. **Multi-Room:** Control multiple instances
5. **MIDI Export:** Export patterns as MIDI files
6. **Collaborative:** Multiple users controlling same instance

### Further Reading

- [Claude Agent SDK Docs](https://docs.claude.com/en/api/agent-sdk/overview)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Tone.js Documentation](https://tonejs.github.io/)
- [APScheduler Docs](https://apscheduler.readthedocs.io/)

---

## Sources

- [claude-agent-sdk on PyPI](https://pypi.org/project/claude-agent-sdk/)
- [Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Claude Agent SDK Python Reference](https://platform.claude.com/docs/en/api/agent-sdk/python)

---

**Enjoy your AI-powered music coding environment!** 🎵✨
