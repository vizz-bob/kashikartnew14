def _to_int(priority) -> int:
    """Convert 'p1'..'p11' or int to int range 1..11."""
    if isinstance(priority, str) and priority.lower().startswith("p"):
        try:
            priority = int(priority[1:])
        except Exception:
            priority = 5
    try:
        priority = int(priority)
    except Exception:
        priority = 5
    return max(1, min(priority, 11))


def calculate_priority_score(priority, match_count: int) -> int:
    """
    Calculate overall priority score for sorting.

    Args:
        priority: 'p1'..'p11' or int 1..11
        match_count: Number of keyword matches

    Returns:
        Score (higher is more important)
    """
    pr = _to_int(priority)
    return pr * 1000 + (match_count * 10)
