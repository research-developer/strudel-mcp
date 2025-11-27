#!/usr/bin/env python3
"""
Strudel MCP Server - Live Music Coding Environment

This MCP server provides tools to interact with the Strudel-MCP live music coding
environment. It enables AI agents to read, validate, and edit musical patterns
that are played in real-time through a browser-based Tone.js synthesizer.

The patterns.js file is polled by the browser every 2 seconds, so changes made
through this server are heard by the user within ~2 seconds.
"""

import json
import os
import re
import shutil
import httpx
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Initialize the MCP server
mcp = FastMCP("strudel_mcp")

# Constants
PATTERNS_FILE = Path(__file__).parent / "patterns.js"
CHARACTER_LIMIT = 10000

# Valid note names (without octave)
VALID_NOTE_NAMES = ["C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B"]

# Valid octaves (typical range for ambient music)
VALID_OCTAVES = ["0", "1", "2", "3", "4", "5", "6", "7", "8"]


# ============================================================================
# Enums for Input Validation
# ============================================================================

class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class TimeInterval(str, Enum):
    """Valid time interval notations for Tone.js."""
    ONE_M = "1m"
    TWO_M = "2m"
    FOUR_M = "4m"
    EIGHT_M = "8m"
    EIGHT_N = "8n"


class Waveform(str, Enum):
    """Valid synthesizer waveforms."""
    SINE = "sine"
    TRIANGLE = "triangle"
    SAWTOOTH = "sawtooth"
    SQUARE = "square"


class Mood(str, Enum):
    """Musical mood presets for pattern suggestions."""
    DARKER = "darker"
    BRIGHTER = "brighter"
    SPACIOUS = "spacious"
    DENSE = "dense"
    MINIMAL = "minimal"


# ============================================================================
# Pydantic Models for Pattern Structure
# ============================================================================

class ChordDefinition(BaseModel):
    """Chord configuration for the pattern."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    progression: List[List[str]] = Field(
        ...,
        description="List of chord arrays, where each chord is a list of note names (e.g., [['C3', 'Eb3', 'G3'], ['Ab3', 'C4', 'Eb4']])",
        min_length=1
    )
    interval: TimeInterval = Field(
        ...,
        description="How often to change chords (e.g., '4m' = every 4 measures)"
    )
    duration: TimeInterval = Field(
        ...,
        description="How long each chord sustains (e.g., '2m' = 2 measures)"
    )
    filter: int = Field(
        ...,
        description="Low-pass filter cutoff frequency in Hz (100-2000). Lower = warmer/darker",
        ge=100,
        le=2000
    )


class MelodyDefinition(BaseModel):
    """Melody configuration for the pattern."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    notes: List[str] = Field(
        ...,
        description="List of note names or '~' for silence/rest (e.g., ['C5', '~', 'G5', 'Eb5'])",
        min_length=1
    )
    interval: TimeInterval = Field(
        ...,
        description="Time between notes (e.g., '2m' = every 2 measures)"
    )
    duration: TimeInterval = Field(
        ...,
        description="Length of each note (e.g., '1m' = 1 measure)"
    )
    waveform: Waveform = Field(
        ...,
        description="Synthesizer waveform: 'sine' (pure), 'triangle' (soft), 'sawtooth' (bright), 'square' (hollow)"
    )
    delay: float = Field(
        ...,
        description="Delay/echo effect amount (0.0-1.0). Higher = more echo",
        ge=0.0,
        le=1.0
    )


class DrumDefinition(BaseModel):
    """Drum pattern configuration."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    kick: List[int] = Field(
        ...,
        description="Kick drum pattern: 1 = hit, 0 = silence (e.g., [1, 0, 0, 0])",
        min_length=1
    )
    snare: List[int] = Field(
        ...,
        description="Snare drum pattern: 1 = hit, 0 = silence (e.g., [0, 0, 1, 0])",
        min_length=1
    )
    interval: TimeInterval = Field(
        ...,
        description="Pattern loop length (e.g., '4m' = 4 measures per loop)"
    )

    @field_validator('kick', 'snare')
    @classmethod
    def validate_drum_pattern(cls, v: List[int]) -> List[int]:
        """Ensure drum patterns only contain 0 or 1."""
        if not all(hit in [0, 1] for hit in v):
            raise ValueError("Drum patterns must only contain 0 (silence) or 1 (hit)")
        return v


class PatternData(BaseModel):
    """Complete pattern structure for the music environment."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    bpm: int = Field(
        ...,
        description="Tempo in beats per minute (20-120 recommended for ambient music)",
        ge=20,
        le=120
    )
    chords: ChordDefinition = Field(
        ...,
        description="Chord progression configuration"
    )
    melody: MelodyDefinition = Field(
        ...,
        description="Melody configuration"
    )
    drums: Optional[DrumDefinition] = Field(
        default=None,
        description="Drum patterns (optional for pure ambient)"
    )


# ============================================================================
# Shared Utility Functions
# ============================================================================

def _read_pattern_file() -> str:
    """
    Read the patterns.js file and return its contents.

    Returns:
        str: Raw file contents

    Raises:
        FileNotFoundError: If patterns.js doesn't exist
        PermissionError: If file can't be read
    """
    try:
        with open(PATTERNS_FILE, 'r') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"patterns.js not found at {PATTERNS_FILE}. "
            "Is the MCP server running in the correct directory?"
        )
    except PermissionError:
        raise PermissionError(
            f"Cannot read {PATTERNS_FILE}. Check file permissions."
        )


def _parse_pattern(content: str) -> Dict[str, Any]:
    """
    Parse the patterns.js file content into a Python dictionary.

    Args:
        content: Raw JavaScript file content

    Returns:
        Dict containing the pattern data

    Raises:
        ValueError: If the pattern can't be parsed
    """
    try:
        # Remove single-line comments
        clean_content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)

        # Strip whitespace
        clean_content = clean_content.strip()

        # Find the object literal (should start with '({' and end with '})')
        match = re.search(r'\(\s*\{.*\}\s*\)', clean_content, re.DOTALL)
        if not match:
            raise ValueError("Could not find pattern object in file")

        # Extract the object (remove outer parentheses)
        obj_str = match.group(0)[1:-1]  # Remove '(' and ')'

        # Convert JavaScript object to JSON
        # 1. Replace single quotes with double quotes
        json_str = obj_str.replace("'", '"')

        # 2. Add quotes around unquoted property names
        # Match: word characters followed by colon (not already in quotes)
        json_str = re.sub(r'(\w+)(?=\s*:)', r'"\1"', json_str)

        # 3. Remove trailing commas (invalid in JSON)
        json_str = re.sub(r',\s*([\]}])', r'\1', json_str)

        # DEBUG: Print to stderr to see what we're parsing
        import sys
        print(f"DEBUG JSON:\n{json_str}", file=sys.stderr)

        # Parse as JSON
        pattern = json.loads(json_str)

        return pattern

    except json.JSONDecodeError as e:
        import sys
        print(f"DEBUG JSON:\n{json_str}", file=sys.stderr)
        raise ValueError(f"Could not parse pattern as valid JavaScript/JSON: {e}\nJSON was:\n{json_str}")
    except Exception as e:
        raise ValueError(f"Error parsing pattern: {e}")


def _validate_note_name(note: str) -> Tuple[bool, str]:
    """
    Validate a musical note name.

    Args:
        note: Note name to validate (e.g., "C3", "Eb4", "F#5", "~")

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Allow silence marker
    if note == "~":
        return True, ""

    # Match pattern: Note[#/b]Octave
    match = re.match(r'^([A-G][#b]?)(\d)$', note)
    if not match:
        return False, f"Invalid note format '{note}'. Use format: Note[#/b]Octave (e.g., C3, Eb4, F#5) or '~' for silence"

    note_name, octave = match.groups()

    if note_name not in VALID_NOTE_NAMES:
        return False, f"Invalid note name '{note_name}'. Valid notes: {', '.join(VALID_NOTE_NAMES)}"

    if octave not in VALID_OCTAVES:
        return False, f"Invalid octave '{octave}'. Valid octaves: 0-8"

    return True, ""


def _validate_pattern_structure(pattern: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate the structure and content of a pattern.

    Args:
        pattern: Pattern dictionary to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Use Pydantic to validate the structure
        PatternData(**pattern)

        # Additional validation: check all note names in chords
        for chord in pattern['chords']['progression']:
            for note in chord:
                is_valid, error = _validate_note_name(note)
                if not is_valid:
                    return False, f"Invalid note in chord: {error}"

        # Check all note names in melody
        for note in pattern['melody']['notes']:
            is_valid, error = _validate_note_name(note)
            if not is_valid:
                return False, f"Invalid note in melody: {error}"

        return True, ""

    except Exception as e:
        return False, f"Pattern validation failed: {str(e)}"


def _format_pattern_js(pattern: Dict[str, Any], description: str) -> str:
    """
    Format a pattern dictionary as JavaScript code for patterns.js.

    Args:
        pattern: Pattern dictionary
        description: Description of the edit for the timestamp comment

    Returns:
        Formatted JavaScript code
    """
    timestamp = datetime.now().strftime("%Y-%m-%d @ %H:%M:%S")

    # Start building the file content
    lines = [
        "// 🎵 STRUDEL-MCP - Ambient Pattern (Tone.js format)",
        f"// {description}",
        f"// TIMESTAMP: {timestamp}",
        "",
        "({",
        f"    bpm: {pattern['bpm']},",
        "    ",
    ]

    # Format chords
    lines.append("    chords: {")
    lines.append("        progression: [")
    for chord in pattern['chords']['progression']:
        chord_str = "[" + ", ".join(f"'{note}'" for note in chord) + "]"
        lines.append(f"            {chord_str},")
    lines.append("        ],")
    lines.append(f"        interval: '{pattern['chords']['interval']}',")
    lines.append(f"        duration: '{pattern['chords']['duration']}',")
    lines.append(f"        filter: {pattern['chords']['filter']}")
    lines.append("    },")
    lines.append("    ")

    # Format melody
    lines.append("    melody: {")
    notes_str = "[" + ", ".join(f"'{note}'" for note in pattern['melody']['notes']) + "]"
    lines.append(f"        notes: {notes_str},")
    lines.append(f"        interval: '{pattern['melody']['interval']}',")
    lines.append(f"        duration: '{pattern['melody']['duration']}',")
    lines.append(f"        waveform: '{pattern['melody']['waveform']}',")
    lines.append(f"        delay: {pattern['melody']['delay']}")
    lines.append("    }")

    # Format drums if present
    if pattern.get('drums'):
        lines.append(",")
        lines.append("    ")
        lines.append("    drums: {")
        kick_str = "[" + ", ".join(str(hit) for hit in pattern['drums']['kick']) + "]"
        snare_str = "[" + ", ".join(str(hit) for hit in pattern['drums']['snare']) + "]"
        lines.append(f"        kick: {kick_str},")
        lines.append(f"        snare: {snare_str},")
        lines.append(f"        interval: '{pattern['drums']['interval']}'")
        lines.append("    }")

    lines.append("})")
    lines.append("")

    return "\n".join(lines)


def _write_pattern_file(content: str) -> Tuple[bool, str]:
    """
    Write content to patterns.js with atomic operation and backup.

    Args:
        content: JavaScript code to write

    Returns:
        Tuple of (success, message)
    """
    try:
        # Create backup
        backup_file = PATTERNS_FILE.with_suffix('.js.bak')
        if PATTERNS_FILE.exists():
            shutil.copy2(PATTERNS_FILE, backup_file)

        # Write to temporary file first (atomic operation)
        temp_file = PATTERNS_FILE.with_suffix('.js.tmp')
        with open(temp_file, 'w') as f:
            f.write(content)

        # Move temp file to actual file (atomic on most systems)
        temp_file.replace(PATTERNS_FILE)

        return True, "Pattern file updated successfully"

    except PermissionError:
        return False, f"Cannot write to {PATTERNS_FILE}. Check file permissions."
    except Exception as e:
        return False, f"Error writing pattern file: {str(e)}"


def _analyze_pattern(pattern: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a pattern and extract metadata and characteristics.

    Args:
        pattern: Pattern dictionary

    Returns:
        Dictionary containing analysis results
    """
    # Collect all unique notes (excluding silence)
    all_notes = set()

    for chord in pattern['chords']['progression']:
        all_notes.update(note for note in chord if note != "~")

    for note in pattern['melody']['notes']:
        if note != "~":
            all_notes.add(note)

    # Sort notes by octave and name
    sorted_notes = sorted(all_notes, key=lambda n: (n[-1], n[:-1]))

    # Analyze melody density
    melody_notes = pattern['melody']['notes']
    silence_count = sum(1 for note in melody_notes if note == "~")
    melody_density = (len(melody_notes) - silence_count) / len(melody_notes) if melody_notes else 0

    # Analyze drum characteristics
    drum_info = None
    if pattern.get('drums'):
        kick_hits = sum(pattern['drums']['kick'])
        snare_hits = sum(pattern['drums']['snare'])
        total_steps = len(pattern['drums']['kick'])
        drum_info = {
            "kick_hits": kick_hits,
            "snare_hits": snare_hits,
            "total_steps": total_steps,
            "kick_density": kick_hits / total_steps,
            "snare_density": snare_hits / total_steps
        }

    # Tempo description
    bpm = pattern['bpm']
    if bpm < 30:
        tempo_desc = "Very Slow - Extremely Meditative"
    elif bpm < 40:
        tempo_desc = "Very Slow - Meditative"
    elif bpm < 60:
        tempo_desc = "Slow - Ambient"
    elif bpm < 80:
        tempo_desc = "Moderate - Relaxed"
    elif bpm < 100:
        tempo_desc = "Moderate - Steady"
    else:
        tempo_desc = "Faster - Energetic"

    return {
        "bpm": bpm,
        "tempo_description": tempo_desc,
        "all_notes_used": sorted_notes,
        "note_count": len(sorted_notes),
        "chord_count": len(pattern['chords']['progression']),
        "melody_note_count": len(melody_notes),
        "melody_density": round(melody_density, 2),
        "filter_cutoff": pattern['chords']['filter'],
        "waveform": pattern['melody']['waveform'],
        "delay_amount": pattern['melody']['delay'],
        "drums": drum_info
    }


def _suggest_for_mood(pattern: Dict[str, Any], mood: str) -> Dict[str, Any]:
    """
    Generate suggestions for modifying a pattern to achieve a desired mood.

    Args:
        pattern: Current pattern dictionary
        mood: Desired mood (darker, brighter, spacious, dense, minimal)

    Returns:
        Dictionary containing suggestions
    """
    suggestions = {
        "mood": mood,
        "current_bpm": pattern['bpm'],
        "current_filter": pattern['chords']['filter'],
        "changes": []
    }

    if mood == "darker":
        suggestions["changes"] = [
            f"Lower BPM from {pattern['bpm']} to {max(20, pattern['bpm'] - 10)} for a heavier feel",
            f"Reduce filter cutoff from {pattern['chords']['filter']} to {max(100, pattern['chords']['filter'] - 200)} Hz for warmer, darker tones",
            "Consider lowering chord notes by an octave (e.g., C3 → C2)",
            "Use 'sawtooth' waveform for grittier, darker melody",
            "Add more '~' rests in melody for sparse, contemplative feel"
        ]

    elif mood == "brighter":
        suggestions["changes"] = [
            f"Raise filter cutoff from {pattern['chords']['filter']} to {min(2000, pattern['chords']['filter'] + 300)} Hz for brighter, airier tones",
            "Consider raising chord notes by an octave (e.g., C3 → C4)",
            "Use 'triangle' or 'sine' waveform for softer, brighter melody",
            "Increase delay amount for more shimmer (try 0.7-0.8)",
            "Use major chords and higher notes"
        ]

    elif mood == "spacious":
        suggestions["changes"] = [
            f"Lower BPM from {pattern['bpm']} to {max(20, pattern['bpm'] - 10)} for more space between events",
            "Increase chord interval to '8m' (8 measures) for slower evolution",
            "Increase melody interval to '4m' for more silence",
            "Add many more '~' rests in melody (aim for 70-80% silence)",
            "Reduce or remove drums entirely for pure ambient texture",
            "Increase delay to 0.6-0.8 for longer trails"
        ]

    elif mood == "dense":
        suggestions["changes"] = [
            f"Increase BPM from {pattern['bpm']} to {min(120, pattern['bpm'] + 15)} for more activity",
            "Reduce melody interval to '1m' or '8n' for faster note changes",
            "Remove most '~' rests from melody - fill with notes",
            "Add more drum hits to kick and snare patterns",
            "Shorten chord interval to '2m' for faster harmonic movement",
            "Reduce delay to 0.2-0.3 to avoid muddy mix"
        ]

    elif mood == "minimal":
        suggestions["changes"] = [
            f"Lower BPM to {max(20, pattern['bpm'] - 15)} for extreme minimalism",
            "Use only 2-3 notes total in melody",
            "Use 80-90% '~' rests in melody",
            "Increase all intervals to maximum ('8m')",
            "Remove drums entirely",
            "Use simple, sparse chord progression (2 chords maximum)",
            "Lower filter to 400-500 Hz for subdued sound"
        ]

    return suggestions


# ============================================================================
# Tool Implementations
# ============================================================================

class GetPatternInput(BaseModel):
    """Input parameters for getting the current pattern."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )
    include_metadata: bool = Field(
        default=True,
        description="Include additional metadata like tempo description and edit history"
    )


@mcp.tool(
    name="strudel_get_pattern",
    annotations={
        "title": "Get Current Music Pattern",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def strudel_get_pattern(params: GetPatternInput) -> str:
    """
    Retrieve the current music pattern from patterns.js.

    This tool reads the active pattern that's currently being played in the user's
    browser. The pattern defines the tempo, chord progression, melody, and drum
    patterns for the live ambient music environment.

    Args:
        params (GetPatternInput): Input parameters containing:
            - response_format (ResponseFormat): Output format - 'markdown' (default, human-readable)
              or 'json' (machine-readable)
            - include_metadata (bool): Whether to include analysis metadata (default: True)

    Returns:
        str: Pattern information in the requested format.

        Markdown format includes:
        - Tempo and BPM with description
        - Chord progression with interval and filter info
        - Melody notes with waveform and effects
        - Drum patterns (if present)
        - Edit timestamp

        JSON format includes:
        - Complete pattern structure as JSON object
        - Optional metadata if include_metadata=True

    Examples:
        - Use when: "What's currently playing?"
        - Use when: "Show me the current pattern"
        - Use when: "What BPM is the music at?"
        - Don't use when: You want to modify the pattern (use strudel_edit_pattern)

    Error Handling:
        - Returns "Error: patterns.js not found..." if file doesn't exist
        - Returns "Error: Could not parse pattern..." if file is malformed
    """
    try:
        # Read and parse the pattern file
        content = _read_pattern_file()
        pattern = _parse_pattern(content)

        # Get metadata if requested
        metadata = None
        if params.include_metadata:
            metadata = _analyze_pattern(pattern)

        # Format response based on requested format
        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# Current Pattern", ""]

            # Tempo section
            lines.append("## Tempo")
            lines.append(f"- **BPM**: {pattern['bpm']}")
            if metadata:
                lines.append(f"  *{metadata['tempo_description']}*")
            lines.append("")

            # Chords section
            lines.append("## Chords")
            chord_names = []
            for chord in pattern['chords']['progression']:
                chord_names.append(", ".join(chord))
            lines.append(f"**Progression**: {' → '.join(chord_names)}")
            lines.append(f"- **Interval**: {pattern['chords']['interval']} (chord change frequency)")
            lines.append(f"- **Duration**: {pattern['chords']['duration']} (note sustain)")
            lines.append(f"- **Filter**: {pattern['chords']['filter']} Hz")
            lines.append("")

            # Melody section
            lines.append("## Melody")
            melody_display = [note if note != "~" else "[rest]" for note in pattern['melody']['notes']]
            lines.append(f"**Notes**: {', '.join(melody_display)}")
            lines.append(f"- **Waveform**: {pattern['melody']['waveform']}")
            lines.append(f"- **Interval**: {pattern['melody']['interval']}")
            lines.append(f"- **Delay**: {pattern['melody']['delay']}")
            lines.append("")

            if metadata:
                lines.append(f"*Melody density: {int(metadata['melody_density'] * 100)}% notes*")
                lines.append("")

            # Drums section (if present)
            if pattern.get('drums'):
                lines.append("## Drums")
                kick_display = [str(h) for h in pattern['drums']['kick']]
                snare_display = [str(h) for h in pattern['drums']['snare']]
                lines.append(f"**Kick**: [{', '.join(kick_display)}]")
                lines.append(f"**Snare**: [{', '.join(snare_display)}]")
                lines.append(f"- **Interval**: {pattern['drums']['interval']}")

                if metadata and metadata['drums']:
                    lines.append(f"\n*Kick: {metadata['drums']['kick_hits']} hits, "
                               f"Snare: {metadata['drums']['snare_hits']} hits*")
                lines.append("")

            # Metadata section
            if metadata:
                lines.append("---")
                lines.append("## Pattern Info")
                lines.append(f"- **Total unique notes**: {metadata['note_count']}")
                lines.append(f"- **Notes used**: {', '.join(metadata['all_notes_used'])}")

            # Extract timestamp from file
            timestamp_match = re.search(r'TIMESTAMP:\s*(.+)$', content, re.MULTILINE)
            if timestamp_match:
                lines.append(f"\n*Last edited: {timestamp_match.group(1)}*")

            return "\n".join(lines)

        else:  # JSON format
            result = {"pattern": pattern}
            if metadata:
                result["metadata"] = metadata
            return json.dumps(result, indent=2)

    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error reading pattern: {str(e)}"


class ValidatePatternInput(BaseModel):
    """Input parameters for validating a pattern."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    pattern_data: Dict[str, Any] = Field(
        ...,
        description="Pattern object to validate, containing bpm, chords, melody, and optionally drums"
    )


@mcp.tool(
    name="strudel_validate_pattern",
    annotations={
        "title": "Validate Music Pattern",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def strudel_validate_pattern(params: ValidatePatternInput) -> str:
    """
    Validate a music pattern structure and values before applying it.

    This tool checks that a pattern has valid structure, note names, time intervals,
    and parameter ranges. Use this before editing the pattern to ensure the music
    engine will be able to play it correctly.

    Args:
        params (ValidatePatternInput): Input parameters containing:
            - pattern_data (dict): Pattern object to validate with structure:
                {
                    "bpm": int (20-120),
                    "chords": {
                        "progression": [[note strings]],
                        "interval": time string,
                        "duration": time string,
                        "filter": int (100-2000)
                    },
                    "melody": {
                        "notes": [note strings or "~"],
                        "interval": time string,
                        "duration": time string,
                        "waveform": waveform string,
                        "delay": float (0.0-1.0)
                    },
                    "drums": {  // optional
                        "kick": [0 or 1],
                        "snare": [0 or 1],
                        "interval": time string
                    }
                }

    Returns:
        str: Validation result message.
            - Success: "✓ Pattern is valid and ready to use!"
            - Error: Detailed error message explaining what's wrong and how to fix it

    Examples:
        - Use when: Before calling strudel_edit_pattern to ensure pattern is correct
        - Use when: "Check if this pattern is valid"
        - Use when: You've modified a pattern and want to verify it before applying
        - Don't use when: You just want to see the current pattern (use strudel_get_pattern)

    Error Handling:
        - Returns specific error for each validation failure with guidance
        - Examples: "Invalid note 'X2'. Use format: Note[#/b]Octave (e.g., C3, Eb4, F#5)"
        - Examples: "BPM must be between 20-120 for ambient music"
    """
    try:
        is_valid, error_message = _validate_pattern_structure(params.pattern_data)

        if is_valid:
            return "✓ Pattern is valid and ready to use!"
        else:
            return f"✗ Pattern validation failed:\n{error_message}"

    except Exception as e:
        return f"Error during validation: {str(e)}"


class EditPatternInput(BaseModel):
    """Input parameters for editing the pattern."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    pattern_data: Dict[str, Any] = Field(
        ...,
        description="Complete pattern object to write to patterns.js"
    )
    edit_description: str = Field(
        ...,
        description="Brief description of what changed (e.g., 'Slowed tempo and darkened chords')",
        min_length=5,
        max_length=200
    )
    validate_before_write: bool = Field(
        default=True,
        description="Validate pattern before writing (recommended: true)"
    )


@mcp.tool(
    name="strudel_edit_pattern",
    annotations={
        "title": "Edit Music Pattern",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def strudel_edit_pattern(params: EditPatternInput) -> str:
    """
    Modify the music pattern file with new configuration.

    This tool writes a new pattern to patterns.js. The browser will automatically
    detect the change within ~2 seconds and update the music playback. A backup
    of the previous pattern is created automatically.

    IMPORTANT: This overwrites the entire pattern file. Make sure to provide a
    complete, valid pattern structure.

    Args:
        params (EditPatternInput): Input parameters containing:
            - pattern_data (dict): Complete pattern object (see strudel_validate_pattern for structure)
            - edit_description (str): Description of changes for timestamp comment (5-200 chars)
            - validate (bool): Whether to validate before writing (default: True, recommended)

    Returns:
        str: Result message indicating success or failure.
            - Success: "✓ Pattern updated successfully! ..." with details
            - Error: Detailed error message with guidance

    Examples:
        - Use when: "Change the BPM to 25"
        - Use when: "Make the music darker"
        - Use when: "Add more silence to the melody"
        - Use when: "Remove the drums"
        - Don't use when: You just want to see the pattern (use strudel_get_pattern)
        - Don't use when: You want to check validity first (use strudel_validate_pattern)

    Error Handling:
        - Returns validation errors if pattern is invalid
        - Returns "Error: Cannot write to patterns.js..." if permission denied
        - Backup file (.js.bak) is always created before writing
    """
    try:
        # Validate if requested
        if params.validate_before_write:
            is_valid, error_message = _validate_pattern_structure(params.pattern_data)
            if not is_valid:
                return f"✗ Pattern validation failed. Cannot write invalid pattern:\n{error_message}\n\nUse validate_before_write=False to skip validation (not recommended)."

        # Format the pattern as JavaScript
        js_content = _format_pattern_js(params.pattern_data, params.edit_description)

        # Write to file
        success, message = _write_pattern_file(js_content)

        if success:
            return f"✓ Pattern updated successfully!\n\nChanges: {params.edit_description}\n\nThe browser will detect the new pattern within ~2 seconds and update the music automatically."
        else:
            return f"✗ Failed to write pattern: {message}"

    except Exception as e:
        return f"Error: Unexpected error during pattern edit: {str(e)}"


class GetPatternInfoInput(BaseModel):
    """Input parameters for getting pattern analysis."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )


@mcp.tool(
    name="strudel_get_pattern_info",
    annotations={
        "title": "Analyze Music Pattern",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def strudel_get_pattern_info(params: GetPatternInfoInput) -> str:
    """
    Get detailed analysis and metadata about the current music pattern.

    This tool analyzes the pattern to extract characteristics like note usage,
    melody density, tempo feel, and complexity metrics. Useful for understanding
    the pattern before making changes.

    Args:
        params (GetPatternInfoInput): Input parameters containing:
            - response_format (ResponseFormat): Output format - 'markdown' (default) or 'json'

    Returns:
        str: Analysis information in the requested format.

        Includes:
        - Tempo analysis (BPM and qualitative description)
        - All unique notes used (sorted)
        - Chord progression characteristics
        - Melody density (percentage of notes vs. silences)
        - Filter cutoff and sonic characteristics
        - Drum pattern analysis (if present)

    Examples:
        - Use when: "Analyze the current pattern"
        - Use when: "What notes are being used?"
        - Use when: "How complex is this pattern?"
        - Use when: "What's the melody density?"
        - Don't use when: You just want the raw pattern (use strudel_get_pattern)

    Error Handling:
        - Returns "Error: patterns.js not found..." if file doesn't exist
        - Returns "Error: Could not parse pattern..." if file is malformed
    """
    try:
        # Read and parse the pattern file
        content = _read_pattern_file()
        pattern = _parse_pattern(content)

        # Analyze the pattern
        analysis = _analyze_pattern(pattern)

        # Format response
        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# Pattern Analysis", ""]

            lines.append("## Tempo")
            lines.append(f"- **BPM**: {analysis['bpm']}")
            lines.append(f"- **Feel**: {analysis['tempo_description']}")
            lines.append("")

            lines.append("## Harmonic Content")
            lines.append(f"- **Total unique notes**: {analysis['note_count']}")
            lines.append(f"- **Notes used**: {', '.join(analysis['all_notes_used'])}")
            lines.append(f"- **Chord count**: {analysis['chord_count']} chords in progression")
            lines.append("")

            lines.append("## Melody Characteristics")
            lines.append(f"- **Total melody steps**: {analysis['melody_note_count']}")
            lines.append(f"- **Melody density**: {int(analysis['melody_density'] * 100)}% (notes vs. silences)")
            lines.append(f"- **Waveform**: {analysis['waveform']}")
            lines.append(f"- **Delay amount**: {analysis['delay_amount']}")
            lines.append("")

            lines.append("## Sonic Character")
            lines.append(f"- **Filter cutoff**: {analysis['filter_cutoff']} Hz")
            if analysis['filter_cutoff'] < 500:
                lines.append("  *Very warm and dark*")
            elif analysis['filter_cutoff'] < 800:
                lines.append("  *Warm and mellow*")
            elif analysis['filter_cutoff'] < 1200:
                lines.append("  *Balanced*")
            elif analysis['filter_cutoff'] < 1600:
                lines.append("  *Bright and open*")
            else:
                lines.append("  *Very bright and airy*")
            lines.append("")

            if analysis['drums']:
                lines.append("## Drum Characteristics")
                lines.append(f"- **Kick hits**: {analysis['drums']['kick_hits']} per cycle")
                lines.append(f"- **Snare hits**: {analysis['drums']['snare_hits']} per cycle")
                lines.append(f"- **Total steps**: {analysis['drums']['total_steps']}")
                lines.append(f"- **Kick density**: {int(analysis['drums']['kick_density'] * 100)}%")
                lines.append(f"- **Snare density**: {int(analysis['drums']['snare_density'] * 100)}%")
            else:
                lines.append("## Drums")
                lines.append("*No drums (pure ambient)*")

            return "\n".join(lines)

        else:  # JSON format
            return json.dumps(analysis, indent=2)

    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error analyzing pattern: {str(e)}"


class SuggestModificationsInput(BaseModel):
    """Input parameters for getting pattern modification suggestions."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    current_pattern: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Pattern to analyze (if None, uses current pattern from file)"
    )
    desired_mood: Mood = Field(
        ...,
        description="Target mood: 'darker', 'brighter', 'spacious', 'dense', or 'minimal'"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )


@mcp.tool(
    name="strudel_suggest_modifications",
    annotations={
        "title": "Suggest Pattern Modifications",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def strudel_suggest_modifications(params: SuggestModificationsInput) -> str:
    """
    Get music theory-based suggestions for modifying a pattern to achieve a desired mood.

    This tool provides concrete, actionable suggestions for changing the pattern based
    on music theory principles. It analyzes the current pattern and recommends specific
    parameter changes to achieve the target mood.

    Args:
        params (SuggestModificationsInput): Input parameters containing:
            - current_pattern (dict, optional): Pattern to analyze. If None, reads from patterns.js
            - desired_mood (Mood): Target mood - one of:
                * 'darker' - Lower, warmer, more somber
                * 'brighter' - Higher, airier, more uplifting
                * 'spacious' - Slower, more silence, contemplative
                * 'dense' - Faster, more notes, energetic
                * 'minimal' - Extremely sparse, meditative
            - response_format (ResponseFormat): Output format - 'markdown' (default) or 'json'

    Returns:
        str: Suggestions for modifications in the requested format.

        Includes specific recommendations for:
        - BPM adjustments
        - Filter cutoff changes
        - Chord progression modifications
        - Melody density changes
        - Waveform selections
        - Interval adjustments
        - Drum pattern changes

    Examples:
        - Use when: "Make the music darker"
        - Use when: "How can I make this more spacious?"
        - Use when: "Suggest changes for a brighter sound"
        - Use when: "I want this to be more minimal"
        - Don't use when: You want to apply changes directly (use strudel_edit_pattern after getting suggestions)

    Error Handling:
        - Returns "Error: patterns.js not found..." if file doesn't exist and no pattern provided
        - Returns "Error: Could not parse pattern..." if pattern is malformed
    """
    try:
        # Get the pattern to analyze
        if params.current_pattern is None:
            content = _read_pattern_file()
            pattern = _parse_pattern(content)
        else:
            pattern = params.current_pattern

        # Generate suggestions
        suggestions = _suggest_for_mood(pattern, params.desired_mood.value)

        # Format response
        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [f"# Suggestions for '{suggestions['mood']}' Mood", ""]

            lines.append("## Current State")
            lines.append(f"- **BPM**: {suggestions['current_bpm']}")
            lines.append(f"- **Filter**: {suggestions['current_filter']} Hz")
            lines.append("")

            lines.append("## Recommended Changes")
            for i, change in enumerate(suggestions['changes'], 1):
                lines.append(f"{i}. {change}")

            lines.append("")
            lines.append("---")
            lines.append("*These are suggestions based on music theory principles. Feel free to experiment!*")

            return "\n".join(lines)

        else:  # JSON format
            return json.dumps(suggestions, indent=2)

    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error generating suggestions: {str(e)}"


class ScheduleChangeInput(BaseModel):
    """Input parameters for scheduling a change."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    find: str = Field(..., description="Text to find in patterns.js")
    replace: str = Field(..., description="Text to replace with")
    delay_seconds: int = Field(..., description="Delay in seconds (0 for immediate)", ge=0)
    description: str = Field(..., description="Description of the change")


@mcp.tool(
    name="strudel_schedule_change",
    annotations={
        "title": "Schedule Pattern Change",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def strudel_schedule_change(params: ScheduleChangeInput) -> str:
    """
    Schedule a pattern change to be executed after a delay.

    This tool sends a request to the main Strudel server to schedule a find/replace operation.
    Useful for queuing changes or creating timed transitions.

    Args:
        params (ScheduleChangeInput):
            - find (str): Text to find
            - replace (str): Text to replace
            - delay_seconds (int): Seconds to wait
            - description (str): What is changing

    Returns:
        str: Success message with schedule details or error.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Use configurable URL or default
            api_url = os.environ.get("STRUDEL_API_URL", "http://localhost:8080/api/queue")
            
            response = await client.post(
                api_url,
                json=params.model_dump()
            )
            response.raise_for_status()
            result = response.json()
            
            return f"✓ Change scheduled! (ID: {result.get('change_id')})\nExecute at: {result.get('execute_at')}\nStatus: {result.get('status')}"
            
    except httpx.RequestError as e:
        return f"Error connecting to server: {str(e)}. Is strudel_server.py running?"
    except httpx.HTTPStatusError as e:
        return f"Server returned error: {e.response.text}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# ============================================================================
# Resources
# ============================================================================

@mcp.resource("pattern://current")
async def get_current_pattern_resource() -> str:
    """
    Resource providing direct access to the current patterns.js file contents.

    This is useful for quick access to the raw pattern file without parsing.
    """
    try:
        return _read_pattern_file()
    except Exception as e:
        return f"Error reading pattern file: {str(e)}"


@mcp.resource("pattern://info")
async def get_pattern_info_resource() -> str:
    """
    Resource providing pattern analysis and metadata.

    This gives quick access to pattern characteristics without needing a tool call.
    """
    try:
        content = _read_pattern_file()
        pattern = _parse_pattern(content)
        info = _analyze_pattern(pattern)
        return json.dumps(info, indent=2)
    except Exception as e:
        return f"Error analyzing pattern: {str(e)}"


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    mcp.run()
