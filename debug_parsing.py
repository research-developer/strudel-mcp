import re
import json

content = """// 🎵 STRUDEL-MCP - Ambient Pattern (Tone.js format)
// Change 26: Wind down - return to contemplative space
// TIMESTAMP: 2025-11-24 @ 05:56:30

({
    bpm: 110,

    chords: {
        progression: [
            ['D3', 'F3', 'A3'],
            ['Bb2', 'D3', 'F3'],
            ['F3', 'A3', 'C4'],
            ['C3', 'E3', 'G3'],
        ],
        interval: '1m',
        duration: '1m',
        filter: 450
    },

    melody: {
        notes: ['~', '~', '~', '~', '~', '~', '~', '~'],
        interval: '8n',
        duration: '8n',
        waveform: 'sine',
        delay: 0.0
    },

    drums: {
        kick: [1, 0, 0, 0, 1, 0, 0, 0],
        snare: [0, 0, 1, 0, 0, 0, 1, 0],
        hihat: [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
        interval: '1m'
    }
})
"""

def parse(content):
    print("Original Content Length:", len(content))
    
    # Remove single-line comments
    clean_content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    
    # Strip whitespace
    clean_content = clean_content.strip()
    
    # Find the object literal
    match = re.search(r'\(\s*\{.*\}\s*\)', clean_content, re.DOTALL)
    if not match:
        print("No object found")
        return
        
    obj_str = match.group(0)[1:-1]
    print("\nExtracted Object:\n", obj_str)

    # 1. Replace single quotes
    json_str = obj_str.replace("'", '"')
    
    # 2. Quote keys
    json_str = re.sub(r'(\w+)(?=\s*:)', r'"\1"', json_str)
    
    # 3. Remove trailing commas
    json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
    
    print("\nTransformed JSON:\n", json_str)
    
    try:
        json.loads(json_str)
        print("\nSUCCESS: Valid JSON")
    except json.JSONDecodeError as e:
        print(f"\nERROR: {e}")
        # Print context around error
        lines = json_str.split('\n')
        if e.lineno <= len(lines):
            print(f"Line {e.lineno}: {lines[e.lineno-1]}")

parse(content)
