"""
Shared utilities for the editorial module
"""

from typing import List, Dict


def format_timestamp(seconds: float) -> str:
    """
    Convert seconds to MM:SS format

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string (e.g., "05:23")

    Example:
        >>> format_timestamp(125.5)
        '02:05'
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def calculate_duration(start_time: float, end_time: float) -> float:
    """
    Calculate duration between two timestamps

    Args:
        start_time: Start time in seconds
        end_time: End time in seconds

    Returns:
        Duration in seconds

    Example:
        >>> calculate_duration(10.5, 25.3)
        14.8
    """
    return end_time - start_time


def extract_clip_text(
    transcript_segments: List[Dict],
    start_time: float,
    end_time: float
) -> str:
    """
    Extract transcript text for a specific time range

    Args:
        transcript_segments: List of segments with 'start', 'end', 'text'
        start_time: Start time in seconds
        end_time: End time in seconds

    Returns:
        Concatenated transcript text for the time range

    Example:
        >>> segments = [
        ...     {'start': 0.0, 'end': 5.0, 'text': 'Hello world'},
        ...     {'start': 5.0, 'end': 10.0, 'text': 'This is a test'}
        ... ]
        >>> extract_clip_text(segments, 2.0, 8.0)
        'Hello world This is a test'
    """
    text_parts = []

    for segment in transcript_segments:
        seg_start = segment.get('start', 0)
        seg_end = segment.get('end', 0)

        # Check if segment overlaps with our time range
        if seg_start < end_time and seg_end > start_time:
            text = segment.get('text', '').strip()
            if text:
                text_parts.append(text)

    return ' '.join(text_parts)


def format_transcript_with_timestamps(segments: List[Dict]) -> str:
    """
    Format transcript segments with timestamps for prompts

    Args:
        segments: List of transcript segments

    Returns:
        Formatted transcript string with timestamps

    Example:
        >>> segments = [{'start': 0.0, 'text': 'Hello'}, {'start': 5.0, 'text': 'World'}]
        >>> format_transcript_with_timestamps(segments)
        '[00:00] Hello\\n[00:05] World'
    """
    lines = []
    for segment in segments:
        start = segment.get('start', 0)
        text = segment.get('text', '').strip()
        if text:
            timestamp = format_timestamp(start)
            lines.append(f"[{timestamp}] {text}")

    return '\n'.join(lines)
