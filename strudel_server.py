#!/usr/bin/env python3
"""
Strudel Web Server with Claude Agent Integration

This FastAPI server provides:
1. Web UI serving (index.html, patterns.js)
2. Chat interface with Claude Agent SDK
3. Change queue system with scheduling
4. Find/replace functionality with agent fallback

The agent has access to the Strudel MCP server for controlling music patterns.
"""

import asyncio

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from dotenv import load_dotenv

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

# Load environment variables from .env file
load_dotenv()

# Get the project directory
PROJECT_DIR = Path(__file__).parent
PATTERNS_FILE = PROJECT_DIR / "patterns.js"

# Global state
scheduler = AsyncIOScheduler()
change_queue: List[Dict[str, Any]] = []
change_id_counter: int = 0
claude_client: Optional[ClaudeSDKClient] = None
SERVER_PORT = 8080


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatMessage(BaseModel):
    """Chat message from the user."""
    message: str = Field(..., description="User's message to Claude", min_length=1)


class ChatResponse(BaseModel):
    """Response from Claude."""
    response: str = Field(..., description="Claude's response")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="Tools used by Claude")


class QueuedChange(BaseModel):
    """A change queued for future execution."""
    find: str = Field(..., description="Text to find in patterns.js")
    replace: str = Field(..., description="Text to replace with")
    delay_seconds: int = Field(default=0, description="Delay before executing (0 = immediate)", ge=0)
    description: Optional[str] = Field(None, description="Optional description of the change")


class QueueStatus(BaseModel):
    """Status of the change queue."""
    pending_changes: List[Dict[str, Any]] = Field(..., description="List of pending changes")
    total_count: int = Field(..., description="Total number of changes in queue")


# ============================================================================
# Agent Client Setup
# ============================================================================

def get_mcp_server_config() -> Dict[str, Any]:
    """
    Get MCP server configuration for the strudel_mcp server.

    Returns the configuration needed to connect to our MCP server
    as a subprocess.
    """
    return {
        "strudel": {
            "command": "python3",
            "args": [str(PROJECT_DIR / "strudel_mcp.py")],
            "env": {}
        }
    }


async def initialize_claude_client() -> ClaudeSDKClient:
    """
    Initialize the Claude SDK client with access to Strudel MCP tools.

    The client is configured with:
    - Access to all strudel_* MCP tools
    - Custom system prompt for music control
    - Permission to use tools automatically
    """
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not set. "
            "Add it to .env file or set as environment variable. "
            "Get your key from https://console.anthropic.com/"
        )

    # Get optional base URL (for custom endpoints)
    api_base_url = os.getenv("ANTHROPIC_BASE_URL")
    
    # Prevent self-referencing URL
    if api_base_url and ("localhost:8080" in api_base_url or "127.0.0.1:8080" in api_base_url):
        print(f"⚠️  Warning: ANTHROPIC_BASE_URL '{api_base_url}' points to this server. Ignoring to prevent loops.")
        api_base_url = None
        # Also remove from os.environ so subprocesses don't inherit it
        if "ANTHROPIC_BASE_URL" in os.environ:
            del os.environ["ANTHROPIC_BASE_URL"]

    # Configure the agent options
    agent_options = {
        "system_prompt": """You are a music composition assistant controlling the Strudel live ambient music environment.

You have access to tools that let you:
- View the current pattern (strudel_get_pattern)
- Analyze pattern complexity (strudel_get_pattern_info)
- Get music theory suggestions (strudel_suggest_modifications)
- Validate patterns before applying (strudel_validate_pattern)
- Edit patterns (strudel_edit_pattern)
- Schedule delayed changes (strudel_schedule_change)

The user is listening to music in their browser that updates automatically when you change patterns.js.
Be creative, musical, and responsive to their requests. When making changes, explain what you're doing
and why it will affect the sound.""",

        # Allow all strudel MCP tools
        "allowed_tools": [
            "strudel_get_pattern",
            "strudel_validate_pattern",
            "strudel_edit_pattern",
            "strudel_get_pattern_info",
            "strudel_suggest_modifications",
            "strudel_schedule_change"
        ],

        # Configure MCP servers
        "mcp_servers": get_mcp_server_config(),

        # Set working directory
        "cwd": str(PROJECT_DIR),

        # Enable automatic tool usage
        "permission_mode": "bypassPermissions"  # Tools run automatically without asking
    }

    # Add base URL if provided (for custom API endpoints)
    if api_base_url:
        agent_options["env"] = {"ANTHROPIC_BASE_URL": api_base_url}

    options = ClaudeAgentOptions(**agent_options)

    # Create and return the client
    client = ClaudeSDKClient(options)
    return client


# ============================================================================
# Change Queue Functions
# ============================================================================

async def execute_find_replace(find: str, replace: str, description: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a find/replace operation on patterns.js.

    If the find/replace fails (text not found), falls back to asking
    the Claude agent to make the change.

    Args:
        find: Text to find
        replace: Text to replace with
        description: Optional description of what changed

    Returns:
        Dict with success status and message
    """
    try:
        # Read current file
        with open(PATTERNS_FILE, 'r') as f:
            content = f.read()

        # Try find/replace
        if find in content:
            new_content = content.replace(find, replace)

            # Write back
            with open(PATTERNS_FILE, 'w') as f:
                f.write(new_content)

            return {
                "success": True,
                "method": "find_replace",
                "message": f"Successfully replaced '{find[:50]}...' with '{replace[:50]}...'"
            }
        else:
            # Find failed - fall back to agent
            print(f"Find/replace failed - text not found. Falling back to agent...")

            # Ask Claude to make the change
            prompt = f"The scheduled find/replace failed because the text wasn't found. Please make this change: {description or f'Replace {find} with {replace}'}"

            response_text = ""
            async for message in claude_client.receive_response(prompt):
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            response_text += block.text

            return {
                "success": True,
                "method": "agent_fallback",
                "message": f"Agent handled the change: {response_text[:200]}..."
            }

    except Exception as e:
        return {
            "success": False,
            "method": "error",
            "message": f"Error executing change: {str(e)}"
        }


async def process_queued_change(change_id: int, change: Dict[str, Any]):
    """
    Process a queued change.

    This is called by the scheduler when it's time to execute a change.
    """
    print(f"Processing queued change {change_id}: {change.get('description', 'No description')}")

    result = await execute_find_replace(
        change['find'],
        change['replace'],
        change.get('description')
    )

    print(f"Change {change_id} result: {result}")

    # Remove from queue
    global change_queue
    change_queue = [c for c in change_queue if c.get('id') != change_id]


def schedule_change(change: QueuedChange) -> Dict[str, Any]:
    """
    Schedule a change to be executed after a delay.

    Args:
        change: The change to schedule

    Returns:
        Dict with change ID and scheduled time
    """
    # Generate unique ID
    global change_id_counter
    change_id_counter += 1
    change_id = change_id_counter

    # Calculate execution time
    execute_at = datetime.now() + timedelta(seconds=change.delay_seconds)

    # Store in queue
    change_dict = {
        "id": change_id,
        "find": change.find,
        "replace": change.replace,
        "description": change.description,
        "scheduled_at": datetime.now().isoformat(),
        "execute_at": execute_at.isoformat(),
        "status": "pending"
    }
    change_queue.append(change_dict)

    # Schedule with APScheduler
    if change.delay_seconds > 0:
        scheduler.add_job(
            process_queued_change,
            trigger=DateTrigger(run_date=execute_at),
            args=[change_id, change_dict],
            id=f"change_{change_id}"
        )
    else:
        # Execute immediately
        asyncio.create_task(process_queued_change(change_id, change_dict))

    return {
        "change_id": change_id,
        "execute_at": execute_at.isoformat(),
        "status": "scheduled"
    }


# ============================================================================
# FastAPI Application
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.

    Handles startup and shutdown:
    - Startup: Initialize Claude client and scheduler
    - Shutdown: Clean up resources
    """
    global claude_client

    # Startup
    print("🚀 Starting Strudel Server with Claude Agent...")

    # Initialize Claude client
    try:
        claude_client = await initialize_claude_client()
        await claude_client.connect()
        print("✓ Claude Agent SDK initialized")
    except ValueError as e:
        print(f"⚠️  Warning: {e}")
        print("   The server will run but chat will not work without an API key.")
        claude_client = None

    # Start scheduler
    scheduler.start()
    print("✓ Change queue scheduler started")

    print(f"✓ Server ready at http://localhost:{SERVER_PORT}")

    yield

    # Shutdown
    print("Shutting down...")
    scheduler.shutdown()
    if claude_client:
        await claude_client.disconnect()


app = FastAPI(
    title="Strudel Music Server with Claude Agent",
    description="Live ambient music coding with AI assistance",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Endpoints
# ============================================================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatMessage) -> ChatResponse:
    """
    Send a message to Claude and get a response.

    Claude has access to all Strudel MCP tools and can read/modify
    the music pattern based on your requests.
    """
    if not claude_client:
        raise HTTPException(
            status_code=500,
            detail="Claude Agent SDK not initialized. Set ANTHROPIC_API_KEY environment variable."
        )

    try:
        response_text = ""
        tool_calls = []

        # Send message
        await claude_client.query(message.message)

        # Collect response
        async for msg in claude_client.receive_response():
            # Collect text content
            if hasattr(msg, 'content'):
                for block in msg.content:
                    if hasattr(block, 'text'):
                        response_text += block.text
                    elif hasattr(block, 'tool_use'):
                        # Track tool calls
                        tool_calls.append({
                            "name": block.tool_use.name,
                            "id": block.tool_use.id
                        })

        return ChatResponse(
            response=response_text or "I received your message and took action.",
            tool_calls=tool_calls
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@app.post("/api/queue")
async def add_to_queue(change: QueuedChange) -> Dict[str, Any]:
    """
    Add a change to the queue.

    Changes can be scheduled for future execution with a delay.
    If delay_seconds is 0, the change executes immediately.
    """
    try:
        result = schedule_change(change)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scheduling change: {str(e)}")


@app.get("/api/queue", response_model=QueueStatus)
async def get_queue() -> QueueStatus:
    """
    Get the current state of the change queue.

    Returns all pending changes and their scheduled execution times.
    """
    return QueueStatus(
        pending_changes=change_queue,
        total_count=len(change_queue)
    )


@app.delete("/api/queue/{change_id}")
async def cancel_change(change_id: int) -> Dict[str, str]:
    """
    Cancel a scheduled change.

    Removes the change from the queue and cancels its scheduled execution.
    """
    global change_queue

    # Find the change
    change = next((c for c in change_queue if c['id'] == change_id), None)
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")

    # Cancel scheduler job
    try:
        scheduler.remove_job(f"change_{change_id}")
    except Exception:
        pass  # Job might not exist if already executed

    # Remove from queue
    change_queue = [c for c in change_queue if c['id'] != change_id]

    return {"status": "cancelled", "change_id": str(change_id)}


# ============================================================================
# Static File Serving
# ============================================================================

@app.get("/")
async def serve_index():
    """Serve the main HTML page."""
    return FileResponse(PROJECT_DIR / "index.html")


@app.get("/patterns.js")
async def serve_patterns():
    """Serve the patterns.js file."""
    return FileResponse(PATTERNS_FILE, media_type="application/javascript")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "claude_ready": claude_client is not None,
        "queue_size": len(change_queue),
        "scheduler_running": scheduler.running
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🎵 Strudel Music Server with Claude Agent")
    print("=" * 60)
    print()
    print(f"Starting server on http://localhost:{SERVER_PORT}")
    print()
    print("Features:")
    print("  • Live music player with Tone.js")
    print("  • Chat with Claude to control music")
    print("  • Schedule pattern changes with queue")
    print("  • Find/replace with agent fallback")
    print()
    print("API Endpoints:")
    print("  POST /api/chat - Send messages to Claude")
    print("  POST /api/queue - Schedule changes")
    print("  GET  /api/queue - View queue status")
    print("  GET  /health - Health check")
    print()
    print("=" * 60)
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=SERVER_PORT,
        log_level="info"
    )
