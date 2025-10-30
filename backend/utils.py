"""Utility helpers for the reagent-ology backend."""
from __future__ import annotations

import re


def slugify(*values: str) -> str:
    """Generate a URL-friendly slug from provided string fragments."""
    combined = "-".join(v for v in values if v)
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", combined).strip("-").lower()
    return normalized or "reagent"
