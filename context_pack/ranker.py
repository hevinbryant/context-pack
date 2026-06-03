"""Score files by relevance to a natural-language query."""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Dict, List, Tuple

# These words add noise; strip them before matching
_STOPWORDS = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "for",
    "of", "and", "or", "with", "how", "does", "do", "what", "why",
    "where", "when", "can", "i", "my", "we", "this", "that", "be",
    "are", "was", "were", "will", "would", "should", "could", "have",
    "has", "had", "not", "no", "want", "need", "get", "make", "add",
    "fix", "bug", "issue", "problem", "error", "code", "file", "function",
}

# Files that are almost always high-signal for any question
_ANCHOR_FILES = {
    "readme.md", "readme.rst", "readme.txt",
    "main.py", "app.py", "server.py", "index.js", "index.ts",
    "main.go", "main.rs", "main.c", "main.cpp",
    "package.json", "pyproject.toml", "cargo.toml", "go.mod",
}


def rank(query: str, files: List[Path], base: Path) -> List[Tuple[Path, float]]:
    """
    Return files sorted by relevance score (highest first).
    Score components:
      - Path/filename keyword overlap  (weight ×4)
      - Content keyword overlap        (weight ×1)
      - Content term frequency         (weight ×0.5 per distinct hit)
      - Anchor file bonus              (weight +5)
      - Recency bonus                  (weight up to +1)
    """
    terms = _extract_terms(query)
    results: Dict[Path, float] = {}

    for fp in files:
        score = _score_file(fp, base, terms)
        results[fp] = score

    return sorted(results.items(), key=lambda kv: kv[1], reverse=True)


# ── Private helpers ────────────────────────────────────────────────────────────

def _extract_terms(query: str) -> List[str]:
    """Tokenise the query and remove stopwords."""
    raw = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", query.lower())
    # Also split camelCase / snake_case tokens in the query
    expanded: List[str] = []
    for w in raw:
        parts = re.split(r"[_\-]", w)
        # camelCase split
        sub = re.sub(r"([a-z])([A-Z])", r"\1 \2", w).split()
        expanded.extend(parts)
        expanded.extend(sub)
    terms = [t for t in set(expanded) if t not in _STOPWORDS and len(t) > 1]
    return terms


def _score_file(fp: Path, base: Path, terms: List[str]) -> float:
    if not terms:
        return 0.0

    score = 0.0
    rel = str(fp.relative_to(base)).lower()
    name = fp.name.lower()

    # Anchor bonus
    if name in _ANCHOR_FILES:
        score += 5.0

    # Path / filename match
    path_tokens = set(re.findall(r"[a-z0-9]+", rel))
    for t in terms:
        if t in path_tokens:
            score += 4.0
        # Partial match (e.g. query "auth" hits "authentication.py")
        elif any(t in pt for pt in path_tokens):
            score += 1.5

    # Content match
    try:
        content = fp.read_text(encoding="utf-8", errors="ignore").lower()
        content_tokens = set(re.findall(r"[a-z_][a-z0-9_]*", content))
        for t in terms:
            if t in content_tokens:
                score += 1.0
            # Frequency bonus (capped)
            count = content.count(t)
            score += min(count * 0.05, 1.0)
    except Exception:
        pass

    # Recency bonus (files modified in the last 7 days get up to +1)
    try:
        age_sec = time.time() - fp.stat().st_mtime
        age_days = age_sec / 86_400
        if age_days < 7:
            score += max(0.0, 1.0 - age_days / 7)
    except Exception:
        pass

    return score
