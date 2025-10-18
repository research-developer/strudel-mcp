# 🎵 Strudel MCP

Live music coding environment using Strudel!

## 🚀 Quick Start

1. **Open in browser**: http://localhost:8080
2. **Click "Start"** to begin playback
3. **I'll edit `patterns.js`** whenever you want changes
4. **Click "Reload Pattern"** to hear the updates

## 🎹 How It Works

- `index.html` - The web interface (loads Strudel from CDN)
- `patterns.js` - Your music patterns (Claude edits this)
- Python HTTP server running on port 8080

## 🎵 Pattern Structure

The patterns.js file uses Strudel mini-notation:
- `sound("bd")` - bass drum
- `sound("sd")` - snare drum  
- `sound("hh")` - hi-hat
- `sound("cp")` - clap
- `~` means rest/silence
- `*` multiplies events (e.g., `hh*8` = 8 hi-hats)

## 🔄 Workflow

1. Tell Claude what kind of pattern you want
2. Claude edits `patterns.js`
3. Click "Reload Pattern" in your browser
4. Enjoy the new groove!

## 📚 Learn More

- [Strudel Documentation](https://strudel.cc/)
- [Strudel Tutorial](https://strudel.cc/learn/getting-started/)
