def calculate_priority_score(priority: str, match_count: int) -> int:
    """
    Calculate overall priority score for sorting.

    Args:
        priority: "high", "medium", or "low"
        match_count: Number of keyword matches

    Returns:
        Score (higher is more important)
    """
    base_scores = {
        "high": 1000,
        "medium": 500,
        "low": 100
    }

    base = base_scores.get(priority.lower(), 0)
    return base + (match_count * 10)
