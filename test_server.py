#!/usr/bin/env python3
"""
Test suite for Strudel MCP Server

This script performs basic validation tests to ensure the server is working correctly.
"""

import json
import sys
from pathlib import Path

# Import the server functions
import strudel_mcp

def test_read_pattern():
    """Test reading the current pattern file."""
    print("✓ Testing pattern file reading...")
    try:
        content = strudel_mcp._read_pattern_file()
        assert content, "Pattern file is empty"
        assert "bpm" in content.lower(), "Pattern doesn't contain BPM"
        print("  ✓ Pattern file read successfully")
        return True
    except Exception as e:
        print(f"  ✗ Failed to read pattern: {e}")
        return False


def test_parse_pattern():
    """Test parsing the pattern file."""
    print("✓ Testing pattern parsing...")
    try:
        content = strudel_mcp._read_pattern_file()
        pattern = strudel_mcp._parse_pattern(content)
        assert isinstance(pattern, dict), "Pattern is not a dictionary"
        assert "bpm" in pattern, "Pattern missing BPM"
        assert "chords" in pattern, "Pattern missing chords"
        assert "melody" in pattern, "Pattern missing melody"
        print(f"  ✓ Pattern parsed successfully: BPM={pattern['bpm']}")
        return True
    except Exception as e:
        print(f"  ✗ Failed to parse pattern: {e}")
        return False


def test_validate_note_names():
    """Test note name validation."""
    print("✓ Testing note name validation...")

    valid_notes = ["C3", "Eb4", "F#5", "Bb2", "A0", "C8", "~"]
    invalid_notes = ["X3", "C", "3", "C9", "Hb4", "C#", ""]

    all_passed = True

    for note in valid_notes:
        is_valid, _ = strudel_mcp._validate_note_name(note)
        if not is_valid:
            print(f"  ✗ Valid note '{note}' failed validation")
            all_passed = False

    for note in invalid_notes:
        is_valid, _ = strudel_mcp._validate_note_name(note)
        if is_valid:
            print(f"  ✗ Invalid note '{note}' passed validation")
            all_passed = False

    if all_passed:
        print("  ✓ All note validations passed")
    return all_passed


def test_validate_pattern_structure():
    """Test pattern structure validation."""
    print("✓ Testing pattern structure validation...")
    try:
        content = strudel_mcp._read_pattern_file()
        pattern = strudel_mcp._parse_pattern(content)

        is_valid, error_msg = strudel_mcp._validate_pattern_structure(pattern)

        if is_valid:
            print("  ✓ Current pattern is valid")
            return True
        else:
            print(f"  ✗ Current pattern is invalid: {error_msg}")
            return False
    except Exception as e:
        print(f"  ✗ Failed to validate pattern: {e}")
        return False


def test_analyze_pattern():
    """Test pattern analysis."""
    print("✓ Testing pattern analysis...")
    try:
        content = strudel_mcp._read_pattern_file()
        pattern = strudel_mcp._parse_pattern(content)
        analysis = strudel_mcp._analyze_pattern(pattern)

        assert "bpm" in analysis, "Analysis missing BPM"
        assert "tempo_description" in analysis, "Analysis missing tempo description"
        assert "all_notes_used" in analysis, "Analysis missing notes list"

        print(f"  ✓ Pattern analyzed: {analysis['note_count']} unique notes, "
              f"{int(analysis['melody_density'] * 100)}% melody density")
        return True
    except Exception as e:
        print(f"  ✗ Failed to analyze pattern: {e}")
        return False


def test_suggest_modifications():
    """Test mood suggestions."""
    print("✓ Testing mood suggestions...")
    try:
        content = strudel_mcp._read_pattern_file()
        pattern = strudel_mcp._parse_pattern(content)

        moods = ["darker", "brighter", "spacious", "dense", "minimal"]

        for mood in moods:
            suggestions = strudel_mcp._suggest_for_mood(pattern, mood)
            assert "mood" in suggestions, f"Suggestions missing mood for {mood}"
            assert "changes" in suggestions, f"Suggestions missing changes for {mood}"
            assert len(suggestions["changes"]) > 0, f"No suggestions for {mood}"

        print(f"  ✓ Generated suggestions for {len(moods)} moods")
        return True
    except Exception as e:
        print(f"  ✗ Failed to generate suggestions: {e}")
        return False


def test_format_pattern():
    """Test pattern formatting."""
    print("✓ Testing pattern formatting...")
    try:
        content = strudel_mcp._read_pattern_file()
        pattern = strudel_mcp._parse_pattern(content)

        formatted = strudel_mcp._format_pattern_js(pattern, "Test formatting")

        assert "bpm:" in formatted, "Formatted pattern missing BPM"
        assert "TIMESTAMP:" in formatted, "Formatted pattern missing timestamp"
        assert "Test formatting" in formatted, "Formatted pattern missing description"

        print("  ✓ Pattern formatted successfully")
        return True
    except Exception as e:
        print(f"  ✗ Failed to format pattern: {e}")
        return False


def test_pydantic_models():
    """Test Pydantic model validation."""
    print("✓ Testing Pydantic model validation...")
    try:
        # Test valid pattern
        valid_pattern = {
            "bpm": 30,
            "chords": {
                "progression": [["C3", "Eb3", "G3"]],
                "interval": "4m",
                "duration": "2m",
                "filter": 600
            },
            "melody": {
                "notes": ["C5", "~", "G5"],
                "interval": "2m",
                "duration": "1m",
                "waveform": "triangle",
                "delay": 0.5
            },
            "drums": {
                "kick": [1, 0, 0, 0],
                "snare": [0, 0, 1, 0],
                "interval": "4m"
            }
        }

        model = strudel_mcp.PatternData(**valid_pattern)
        assert model.bpm == 30, "Model BPM mismatch"

        # Test invalid BPM (should raise validation error)
        try:
            invalid_pattern = valid_pattern.copy()
            invalid_pattern["bpm"] = 150  # Too high
            strudel_mcp.PatternData(**invalid_pattern)
            print("  ✗ Invalid BPM passed validation")
            return False
        except Exception:
            pass  # Expected

        print("  ✓ Pydantic models working correctly")
        return True
    except Exception as e:
        print(f"  ✗ Pydantic model test failed: {e}")
        return False



def main():
    """Run all tests."""
    print("=" * 60)
    print("Strudel MCP Server Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_read_pattern,
        test_parse_pattern,
        test_validate_note_names,
        test_validate_pattern_structure,
        test_analyze_pattern,
        test_suggest_modifications,
        test_format_pattern,
        test_pydantic_models,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ✗ Test crashed: {e}")
            results.append(False)
        print()

    # Summary
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All tests passed! Server is ready to use.")
        return 0
    else:
        print("✗ Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
