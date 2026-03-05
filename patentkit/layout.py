from __future__ import annotations


def assign_columns(words: list[dict]) -> list[list[dict]]:
    if not words:
        return []
    xs = sorted(w.get("x0", 0) for w in words)
    midpoint = (xs[0] + xs[-1]) / 2
    left = [w for w in words if w.get("x0", 0) <= midpoint]
    right = [w for w in words if w.get("x0", 0) > midpoint]
    return [left, right] if left and right else [words]
