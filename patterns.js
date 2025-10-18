// 🎵 STRUDEL-MCP - Ambient Pattern (Tone.js format)
// Edit 2: Opening up the filter, darker chords
// TIMESTAMP: 2025-10-13 @ 21:47:30

({
    bpm: 30,
    
    chords: {
        progression: [
            ['C3', 'Eb3', 'G3'],
            ['Ab3', 'C4', 'Eb4'],
            ['F3', 'Ab3', 'C4'],
            ['Bb2', 'D3', 'F3']
        ],
        interval: '4m',
        duration: '2m',
        filter: 600
    },
    
    melody: {
        notes: ['C5', '~', 'G5', '~', 'Eb5', '~', 'Bb4', '~'],
        interval: '2m',
        duration: '1m',
        waveform: 'triangle',
        delay: 0.5
    },
    
    drums: {
        kick: [1, 0, 0, 0, 0, 0, 0, 0],
        snare: [0, 0, 0, 0, 0, 0, 1, 0],
        interval: '4m'
    }
})
