"""
Delay manipulation functions for macro events.

All functions return NEW lists without mutating the originals.
Each function creates fresh event objects, supporting MouseEvent,
KeyboardEvent, and SystemEvent.
"""

import copy
from core.event_model import MouseEvent, KeyboardEvent, SystemEvent


def _clone_event_with_timestamp(event, new_timestamp: float):
    """Create a copy of any event type with an updated timestamp."""
    cloned = copy.deepcopy(event)
    cloned.timestamp = round(new_timestamp, 4)
    return cloned


def inject_delay(events: list, after_index: int, delay_seconds: float) -> list:
    """
    Insert a pause into the event list at a specific position.
    All events after the insertion point are shifted forward by delay_seconds.

    Args:
        events: Original event list (MouseEvent, KeyboardEvent, or SystemEvent)
        after_index: Insert pause AFTER this event index
        delay_seconds: How long to pause (in seconds)

    Returns:
        New event list with adjusted timestamps
    """
    if not events or after_index < 0 or after_index >= len(events):
        return list(events)

    result = []
    for i, event in enumerate(events):
        if i <= after_index:
            result.append(event)
        else:
            result.append(_clone_event_with_timestamp(
                event, event.timestamp + delay_seconds
            ))

    return result


def inject_delay_at_time(events: list, at_timestamp: float, delay_seconds: float) -> list:
    """
    Insert a pause at a specific time position in the recording.
    All events after `at_timestamp` are shifted forward.
    """
    result = []
    for event in events:
        if event.timestamp <= at_timestamp:
            result.append(event)
        else:
            result.append(_clone_event_with_timestamp(
                event, event.timestamp + delay_seconds
            ))
    return result


def scale_timing(events: list, factor: float) -> list:
    """
    Scale all timestamps by a factor.
    factor=0.5 → 2x faster, factor=2.0 → 2x slower.
    Different from speed_multiplier: this permanently alters the event list.
    """
    return [
        _clone_event_with_timestamp(e, e.timestamp * factor)
        for e in events
    ]


def remove_idle_gaps(events: list, max_gap: float = 2.0) -> list:
    """
    Compress long idle periods in a recording.
    Any gap longer than max_gap seconds is reduced to max_gap.
    Useful when you paused mid-recording.
    """
    if len(events) < 2:
        return list(events)

    result = [events[0]]
    offset = 0.0

    for i in range(1, len(events)):
        gap = events[i].timestamp - events[i - 1].timestamp
        if gap > max_gap:
            offset += gap - max_gap

        result.append(_clone_event_with_timestamp(
            events[i], events[i].timestamp - offset
        ))

    return result


def find_pause_points(events: list, min_gap: float = 0.5) -> list[tuple[int, float]]:
    """
    Find indices where gap to next event exceeds min_gap.
    Returns list of (event_index, gap_duration) tuples.
    Useful to know where to inject custom delays.
    """
    pauses = []
    for i in range(len(events) - 1):
        gap = events[i + 1].timestamp - events[i].timestamp
        if gap >= min_gap:
            pauses.append((i, round(gap, 4)))
    return pauses
