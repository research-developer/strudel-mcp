# Strudel-MCP Server Documentation

## Overview

The Strudel-MCP server is a Model Context Protocol (MCP) server that enables AI agents to interact with the live ambient music coding environment. It provides tools for reading, validating, and editing musical patterns that are played in real-time through a browser-based Tone.js synthesizer.

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or using uv (recommended):

```bash
uv pip install -r requirements.txt
```

### 2. Verify Installation

```bash
python3 -m py_compile strudel_mcp.py
```

### 3. Test the Server

```bash
# Check help
python3 strudel_mcp.py --help

# Run in development mode
mcp dev strudel_mcp.py
```

## Configuration

### Claude Desktop Configuration

Add to your Claude Desktop config file (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "strudel": {
      "command": "python3",
      "args": ["/Users/preston/Projects/strudel-mcp/strudel_mcp.py"],
      "env": {}
    }
  }
}
```

### Alternative: Using uv

```json
{
  "mcpServers": {
    "strudel": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/preston/Projects/strudel-mcp",
        "run",
        "strudel_mcp.py"
      ],
      "env": {}
    }
  }
}
```

## Available Tools

### 1. `strudel_get_pattern`

**Purpose**: Retrieve the current music pattern from patterns.js

**Parameters**:
- `response_format` (optional): "markdown" (default) or "json"
- `include_metadata` (optional): Include analysis metadata (default: true)

**Example Usage**:
```
What's currently playing?
Show me the current pattern in JSON format
```

---

### 2. `strudel_validate_pattern`

**Purpose**: Validate a pattern structure before applying it

**Parameters**:
- `pattern_data` (required): Complete pattern object to validate

**Example Usage**:
```
Validate this pattern before I apply it
Check if this pattern structure is valid
```

---

### 3. `strudel_edit_pattern`

**Purpose**: Modify the music pattern file (DESTRUCTIVE)

**Parameters**:
- `pattern_data` (required): Complete pattern object
- `edit_description` (required): Description of changes (5-200 chars)
- `validate` (optional): Validate before writing (default: true)

**Example Usage**:
```
Change the BPM to 25
Make the music darker by lowering the filter to 400
Add more silence to the melody
Remove the drums completely
```

---

### 4. `strudel_get_pattern_info`

**Purpose**: Get detailed analysis and metadata about the current pattern

**Parameters**:
- `response_format` (optional): "markdown" (default) or "json"

**Example Usage**:
```
Analyze the current pattern
What notes are being used?
How complex is this melody?
What's the melody density?
```

---

### 5. `strudel_suggest_modifications`

**Purpose**: Get music theory-based suggestions for pattern modifications

**Parameters**:
- `current_pattern` (optional): Pattern to analyze (uses file if not provided)
- `desired_mood` (required): One of: "darker", "brighter", "spacious", "dense", "minimal"
- `response_format` (optional): "markdown" (default) or "json"

**Example Usage**:
```
Make the music darker
How can I make this more spacious?
Suggest changes for a brighter sound
I want this to be more minimal
```

## Available Resources

### `pattern://current`

Direct access to the raw patterns.js file contents.

### `pattern://info`

Pattern analysis and metadata in JSON format.

## Pattern Structure

A valid pattern must have this structure:

```javascript
{
    bpm: 30,  // Tempo (20-120 for ambient)

    chords: {
        progression: [
            ['C3', 'Eb3', 'G3'],  // Array of note names
            ['Ab3', 'C4', 'Eb4']
        ],
        interval: '4m',    // Chord change frequency ('1m', '2m', '4m', '8m', '8n')
        duration: '2m',    // Note sustain length
        filter: 600        // Low-pass filter (100-2000 Hz)
    },

    melody: {
        notes: ['C5', '~', 'G5', 'Eb5'],  // '~' = silence/rest
        interval: '2m',     // Time between notes
        duration: '1m',     // Note length
        waveform: 'triangle',  // 'sine', 'triangle', 'sawtooth', 'square'
        delay: 0.5          // Delay effect (0.0-1.0)
    },

    drums: {  // Optional
        kick: [1, 0, 0, 0],   // 1 = hit, 0 = silence
        snare: [0, 0, 1, 0],
        interval: '4m'
    }
}
```

### Valid Note Names

Format: `NoteName[#/b]Octave`
- Examples: `C3`, `Eb4`, `F#5`, `Bb2`
- Octave range: 0-8
- Use `~` for silence in melody

### Valid Time Intervals

- `1m` = 1 measure
- `2m` = 2 measures
- `4m` = 4 measures
- `8m` = 8 measures
- `8n` = eighth note

### Valid Waveforms

- `sine` - Pure, soft tone
- `triangle` - Mellow, soft tone
- `sawtooth` - Bright, buzzy tone
- `square` - Hollow, electronic tone

## Workflow Examples

### Example 1: Checking Current State

```
User: "What's currently playing?"
Tool: strudel_get_pattern (response_format: "markdown")
Result: Shows current BPM, chords, melody, drums with analysis
```

### Example 2: Making it Darker

```
User: "Make the music darker"
Tool: strudel_suggest_modifications (desired_mood: "darker")
Result: Shows suggestions for lowering BPM, reducing filter, etc.

User: "Apply those changes"
Tool: strudel_get_pattern (to get current pattern)
Tool: strudel_edit_pattern (with modified pattern)
Result: Pattern updated, music changes within 2 seconds
```

### Example 3: Safe Editing with Validation

```
User: "Change BPM to 25 and remove drums"
Tool: strudel_get_pattern
Tool: Modify pattern internally
Tool: strudel_validate_pattern (with new pattern)
Result: Validation passes

Tool: strudel_edit_pattern (with validated pattern)
Result: Music updated successfully
```

## Error Handling

The server provides clear, actionable error messages:

- **File not found**: "Error: patterns.js not found. Is the server running in the correct directory?"
- **Invalid note**: "Error: Invalid note 'X2'. Use format: Note[#/b]Octave (e.g., C3, Eb4, F#5)"
- **Invalid BPM**: "Error: BPM must be between 20-120 for ambient music"
- **Permission denied**: "Error: Cannot write to patterns.js. Check file permissions."

## Development

### Running Tests

```bash
# Verify syntax
python3 -m py_compile strudel_mcp.py

# Run with MCP inspector
mcp dev strudel_mcp.py

# Access inspector at http://localhost:5173
```

### Debugging

The server logs to stderr, so you can capture logs:

```bash
python3 strudel_mcp.py 2> server.log
```

## Architecture

```
┌─────────────────┐
│  AI Agent       │
│  (Claude)       │
└────────┬────────┘
         │ MCP Protocol
         │ (stdio)
┌────────▼────────┐
│ strudel_mcp.py  │
│  - 5 tools      │
│  - 2 resources  │
│  - Validation   │
└────────┬────────┘
         │ File I/O
┌────────▼────────┐
│  patterns.js    │
└────────┬────────┘
         │ HTTP polling
         │ (every 2s)
┌────────▼────────┐
│  Browser        │
│  Tone.js        │
│  Audio Engine   │
└─────────────────┘
```

## Safety Features

1. **Validation**: All patterns validated before writing (can be disabled)
2. **Atomic Writes**: Temp file + rename for atomic operations
3. **Backups**: Automatic backup (.js.bak) before overwriting
4. **Error Handling**: Comprehensive error messages with guidance
5. **Type Safety**: Pydantic models for all inputs

## Music Theory Helpers

The server includes built-in music theory knowledge:

- **Mood suggestions**: Concrete changes for darker, brighter, spacious, dense, minimal moods
- **Note validation**: Ensures valid musical note names
- **Filter recommendations**: Maps filter frequencies to sonic characteristics
- **Tempo descriptions**: Human-readable tempo feels (e.g., "Very Slow - Meditative")

## Best Practices

1. **Always validate** before editing (default behavior)
2. **Use descriptive edit descriptions** for timestamp comments
3. **Check pattern info** before making changes to understand current state
4. **Use suggestions tool** for music theory guidance
5. **Make small, incremental changes** for best musical results

## Troubleshooting

### Server won't start
- Check Python version (requires 3.10+)
- Verify dependencies: `pip list | grep mcp`
- Check for syntax errors: `python3 -m py_compile strudel_mcp.py`

### Changes not reflected in browser
- Verify patterns.js was actually modified (check timestamp)
- Browser should poll every 2 seconds
- Try hard refresh (Cmd+Shift+R / Ctrl+Shift+R)
- Check browser console for errors

### Validation errors
- Review pattern structure in this documentation
- Use `strudel_validate_pattern` to get specific error messages
- Check note names follow format: `Note[#/b]Octave`

## License

MIT License - See parent project for details.
