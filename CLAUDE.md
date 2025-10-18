# 🎵 CLAUDE.md - AI Agent Guide for Strudel MCP

## Project Overview
This is a **live ambient music coding environment** where you (an AI agent) can edit pattern files and the user hears changes in real-time through their browser. No manual intervention required from the user!

## How It Works

### Architecture
1. **Python HTTP server** runs on `localhost:8080` serving the web interface
2. **Browser** polls `patterns.js` every 2 seconds for changes
3. **Tone.js** synthesizes and plays the patterns automatically
4. **You edit** `patterns.js` → **User hears** changes within ~2 seconds

### File Structure
```
strudel-mcp/
├── index.html        # Web interface with Tone.js player
├── patterns.js       # EDIT THIS FILE to change the music
├── README.md         # User-facing documentation
└── CLAUDE.md         # This file (for AI agents)
```

## Your Job: Editing Patterns

### Location
Edit the file: `/Users/preston/Projects/strudel-mcp/patterns.js`

### Pattern Format
The pattern is a JavaScript object with these properties:

```javascript
({
    bpm: 30,  // Tempo (20-120 recommended for ambient)
    
    chords: {
        progression: [
            ['C3', 'Eb3', 'G3'],  // Array of chord notes
            ['Ab3', 'C4', 'Eb4']
        ],
        interval: '4m',    // How often to change chords (e.g., '2m', '4m', '8m')
        duration: '2m',     // How long each chord sustains
        filter: 600         // Low-pass filter cutoff (100-2000 Hz)
    },
    
    melody: {
        notes: ['C5', '~', 'G5', 'Eb5'],  // '~' = silence/rest
        interval: '2m',     // Time between notes
        duration: '1m',     // Note length
        waveform: 'triangle',  // 'sine', 'triangle', 'sawtooth', 'square'
        delay: 0.5          // Delay effect (0.0-1.0)
    },
    
    drums: {
        kick: [1, 0, 0, 0],   // 1 = hit, 0 = silence
        snare: [0, 0, 1, 0],  // Pattern array
        interval: '4m'        // Pattern loop length
    }
})
```

### Time Notation
- `'1m'` = 1 measure
- `'2m'` = 2 measures
- `'4m'` = 4 measures
- `'8m'` = 8 measures
- `'8n'` = eighth note

### Note Naming
- Format: `NoteName + Octave` (e.g., `'C3'`, `'Eb4'`, `'G5'`)
- Flats: Use `b` (e.g., `'Bb3'`, `'Eb4'`)
- Sharps: Use `#` (e.g., `'C#4'`, `'F#3'`)
- Silence: Use `'~'` in melody note arrays

## Workflow for Sequential Edits

### Rule #1: ONE CHANGE AT A TIME
Make small, focused edits so the user can hear the evolution clearly.

### Rule #2: ADD TIMESTAMPS
Always add a comment with timestamp when making edits:
```javascript
// Edit 3: Adding reverb and slower tempo
// TIMESTAMP: 2025-10-13 @ 21:50:15
```

### Rule #3: WAIT FOR CONFIRMATION
After each edit, wait for the user to confirm they heard the change before making the next edit.

### Example Edit Sequence

**Edit 1: Slow it down**
- Change `bpm: 40` → `bpm: 30`
- Result: More spacious, meditative

**Edit 2: Darker harmony**
- Change chord progression to use lower notes
- Lower the filter cutoff
- Result: Moodier, deeper sound

**Edit 3: Sparser melody**
- Add more `'~'` rests in melody.notes array
- Result: More silence, contemplative

**Edit 4: Remove drums**
- Comment out or remove the entire `drums` section
- Result: Pure ambient texture

**Edit 5: Longer chord changes**
- Change `interval: '4m'` → `interval: '8m'`
- Result: Even slower evolution

## Creative Ideas for Ambient Music

### For More Spaciousness
- Lower BPM (20-30 range)
- Add more `'~'` rests in melodies
- Increase intervals ('4m' → '8m')
- Reduce drum hits

### For Darker Vibes
- Lower filter cutoff (400-600 Hz)
- Use lower octaves (C2, Bb2 instead of C3, Bb3)
- Minor chords and diminished intervals
- 'sawtooth' waveform for grittier sound

### For Brighter Vibes
- Higher filter cutoff (1000-1500 Hz)
- Use higher octaves (C5, G5)
- 'triangle' or 'sine' waveforms
- Major chord progressions

### For Rhythmic Interest
- Add more drum hits in patterns
- Vary kick/snare patterns
- Shorter drum intervals ('2m' instead of '4m')

### For Dreamy Textures
- Increase delay (0.6-0.8)
- Long sustained notes (duration: '4m')
- Overlapping chord changes

## Technical Details

### Audio Engine
- Uses **Tone.js v14.8.49** (loaded via CDN)
- All synthesis happens in the browser
- Auto-polling checks for file changes every 2 seconds

### Browser Requirements
- User must click page once to start (browser autoplay policy)
- Works best in Chrome/Edge/Firefox
- Requires modern JavaScript support

### Server
- Simple Python HTTP server on port 8080
- Started with: `python3 -m http.server 8080`
- Serves static files from project directory

## Troubleshooting

### User hears nothing after clicking
- Check browser console for errors
- Verify Tone.js loaded correctly
- Ensure pattern.js syntax is valid JavaScript

### Changes not updating
- Check if server is still running (PID from earlier)
- Verify file saved correctly (check timestamps)
- Browser may be caching - user can hard refresh (Cmd+Shift+R / Ctrl+Shift+R)

### Syntax errors in patterns.js
- Must be valid JavaScript object
- All arrays must have closing brackets
- All strings must have closing quotes
- Watch for missing commas

## Pro Tips

### 🎯 Start Simple
Begin with minimal changes to understand the user's taste before getting experimental.

### 🎨 Build Narratives
Think of edits as a journey - each change should feel intentional and tell a story.

### 🔊 Balance Elements
Not everything needs to play at once. Silence and space are crucial in ambient music.

### 🎭 Experiment with Extremes
Try very slow (BPM 20), very filtered (200 Hz), very sparse patterns - ambient music thrives on restraint.

### 📊 Layer Gradually
Start with just chords, then add melody, then maybe minimal drums. Build up over multiple edits.

## Current State (Last Edit)

**Edit 2** - Darker chords with lower filter
- BPM: 30
- Filter: 600 Hz
- Chord progression includes Ab and F chords
- Lower bass notes (Bb2)

## Next Steps Suggestions

Good directions to explore:
1. Remove drums entirely for pure ambient
2. Extend chord intervals to 8 measures
3. Experiment with sine wave for ethereal sound
4. Add more harmonic complexity to chords
5. Try very minimal melody (only 2-3 notes total)

---

**Remember**: You're creating a *living soundscape*. Each edit should feel intentional and musical. Have fun! 🎵✨
