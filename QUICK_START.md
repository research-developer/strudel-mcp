# Strudel-MCP Quick Start Guide

## 🚀 Get Started in 3 Minutes

### Step 1: Install Dependencies

```bash
cd /Users/preston/Projects/strudel-mcp
pip install -r requirements.txt
```

Or using `uv` (recommended):

```bash
uv pip install -r requirements.txt
```

### Step 2: Test the Server

```bash
# Run the test suite
python3 test_server.py

# Expected output: "8/8 tests passed"
```

### Step 3: Configure Claude Desktop

Add this to your Claude Desktop config:

**File**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "strudel": {
      "command": "python3",
      "args": [
        "/Users/preston/Projects/strudel-mcp/strudel_mcp.py"
      ]
    }
  }
}
```

### Step 4: Restart Claude Desktop

Quit and reopen Claude Desktop to load the MCP server.

---

## ✨ Try It Out

### Example 1: Check Current Pattern

```
You: "What's currently playing in the Strudel environment?"
```

Claude will use `strudel_get_pattern` to show you:
- Current BPM and tempo feel
- Chord progression
- Melody notes and waveform
- Drum patterns
- Filter settings

---

### Example 2: Make it Darker

```
You: "Make the music darker and more contemplative"
```

Claude will:
1. Use `strudel_suggest_modifications` with mood="darker"
2. Use `strudel_get_pattern` to get current pattern
3. Modify the pattern (lower BPM, reduce filter, etc.)
4. Use `strudel_validate_pattern` to check it's valid
5. Use `strudel_edit_pattern` to apply changes

Your browser will automatically update the music within 2 seconds!

---

### Example 3: Analyze Complexity

```
You: "How complex is the current pattern? Give me details."
```

Claude will use `strudel_get_pattern_info` to show:
- All unique notes used
- Melody density percentage
- Chord count and progression
- Sonic character from filter frequency
- Drum hit patterns

---

## 🎵 Understanding the Pattern Structure

### Basic Pattern

```javascript
{
    bpm: 30,  // Tempo (20-120)

    chords: {
        progression: [['C3', 'Eb3', 'G3']],
        interval: '4m',  // How often chords change
        duration: '2m',  // How long each chord sustains
        filter: 600      // Low-pass filter (100-2000 Hz)
    },

    melody: {
        notes: ['C5', '~', 'G5'],  // '~' = silence
        interval: '2m',
        duration: '1m',
        waveform: 'triangle',  // sine, triangle, sawtooth, square
        delay: 0.5  // Echo effect (0.0-1.0)
    },

    drums: {  // Optional
        kick: [1, 0, 0, 0],  // 1 = hit, 0 = silence
        snare: [0, 0, 1, 0],
        interval: '4m'
    }
}
```

---

## 🎨 Creative Prompts to Try

### Mood Changes
- "Make it more spacious and meditative"
- "Add energy by making it denser"
- "Create a minimal, zen-like atmosphere"
- "Brighten the sound with higher frequencies"

### Technical Changes
- "Slow down to 20 BPM"
- "Remove the drums for pure ambient"
- "Change the melody to use a sine wave"
- "Add more silence to the melody"

### Analysis
- "What notes are being used?"
- "How sparse is the melody?"
- "What's the filter frequency doing to the sound?"
- "Analyze the drum pattern"

---

## 🛠️ Available Tools

### 1. `strudel_get_pattern`
- **What**: Get current pattern
- **When**: Check what's playing
- **Output**: Markdown or JSON

### 2. `strudel_validate_pattern`
- **What**: Check if pattern is valid
- **When**: Before applying changes
- **Output**: Validation result

### 3. `strudel_edit_pattern`
- **What**: Modify the pattern
- **When**: Apply changes
- **Output**: Success/error message

### 4. `strudel_get_pattern_info`
- **What**: Detailed analysis
- **When**: Understand complexity
- **Output**: Metadata and metrics

### 5. `strudel_suggest_modifications`
- **What**: Get music theory suggestions
- **When**: Need ideas for changes
- **Moods**: darker, brighter, spacious, dense, minimal
- **Output**: Specific recommendations

---

## 🎯 Workflow Example

```
1. You: "What's playing?"
   → Claude uses strudel_get_pattern
   → Shows: BPM=30, filter=600Hz, triangle waveform

2. You: "Make it darker"
   → Claude uses strudel_suggest_modifications(mood="darker")
   → Gets suggestions: Lower BPM to 20, filter to 400Hz

3. You: "Apply those changes"
   → Claude uses strudel_get_pattern (get current)
   → Claude modifies pattern internally
   → Claude uses strudel_validate_pattern (check it's valid)
   → Claude uses strudel_edit_pattern (apply changes)
   → Music changes in browser within 2 seconds! 🎵
```

---

## 🔍 Debugging

### Server won't start?
```bash
# Check Python version (need 3.10+)
python3 --version

# Verify dependencies
pip list | grep mcp
pip list | grep pydantic

# Test syntax
python3 -m py_compile strudel_mcp.py
```

### Changes not reflected?
1. Check patterns.js was modified (look for new timestamp)
2. Browser should poll every 2 seconds
3. Try hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
4. Check browser console for errors

### Tool not working?
```bash
# Run test suite
python3 test_server.py

# Check logs in Claude Desktop
# View → Developer → Developer Tools → Console
```

---

## 📚 More Information

- **Full Documentation**: See `MCP_SERVER.md`
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`
- **Pattern Structure**: See `CLAUDE.md`
- **Test Suite**: Run `python3 test_server.py`
- **Evaluations**: See `evaluations.xml`

---

## 🎓 Learning Resources

### Valid Note Names
- Format: `NoteName[#/b]Octave`
- Examples: `C3`, `Eb4`, `F#5`, `Bb2`
- Octaves: 0-8
- Use `~` for silence in melody

### Time Intervals
- `1m` = 1 measure
- `2m` = 2 measures
- `4m` = 4 measures
- `8m` = 8 measures
- `8n` = eighth note

### Waveforms
- `sine` - Pure, soft
- `triangle` - Mellow, soft
- `sawtooth` - Bright, buzzy
- `square` - Hollow, electronic

### Filter Frequencies
- 100-400 Hz: Very warm and dark
- 400-800 Hz: Warm and mellow
- 800-1200 Hz: Balanced
- 1200-1600 Hz: Bright and open
- 1600-2000 Hz: Very bright and airy

---

## 🎉 You're Ready!

Start the browser with:
```bash
python3 -m http.server 8080
```

Open: `http://localhost:8080`

Then ask Claude to help you create beautiful ambient music! 🎵
