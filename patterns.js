// 🎵 STRUDEL-MCP - Ambient Pattern (Tone.js format)
// Slowed to ambient tempo, added sparse dreamy melody, darker chord progression, minimal drums
// TIMESTAMP: 2025-11-26 @ 12:36:49

({
    bpm: 52,
    
    chords: {
        progression: [
            ['E2', 'G2', 'B2'],
            ['A2', 'C3', 'E3'],
            ['D2', 'F2', 'A2'],
            ['G2', 'B2', 'D3'],
        ],
        interval: '2m',
        duration: '2m',
        filter: 280
    },
    
    melody: {
        notes: ['~', 'B4', '~', '~', 'D5', '~', 'E5', '~', '~', 'G5', '~', '~', '~', 'A5', '~', '~'],
        interval: '8n',
        duration: '8n',
        waveform: 'triangle',
        delay: 0.6
    }
,
    
    drums: {
        kick: [1, 0, 0, 0, 0, 0, 0, 0],
        snare: [0, 0, 0, 0, 0, 0, 1, 0],
        interval: '1m'
    }
})
