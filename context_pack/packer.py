"""Pack ranked files into a context block within a token budget."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

# One token ≈ 3.5 characters for mixed prose + code.
# This is a fast approximation; tiktoken is optional.
_CHARS_PER_TOKEN = 3.5


def count_tokens(text: str) -> int:
    """Estimate token count.  Uses tiktoken when available, else approximates."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, int(len(text) / _CHARS_PER_TOKEN))


@dataclass
class PackedContext:
    """Result of a pack operation."""
    included: List[Tuple[Path, str, float]] = field(default_factory=list)
    # (filepath, content, score)
    excluded: List[Tuple[Path, str]] = field(default_factory=list)
    # (filepath, reason)
    total_tokens: int = 0
    budget_tokens: int = 0

    @property
    def utilisation_pct(self) -> float:
        if self.budget_tokens == 0:
            return 0.0
        return self.total_tokens / self.budget_tokens * 100


def pack(
    ranked: List[Tuple[Path, float]],
    base: Path,
    budget_tokens: int = 100_000,
) -> PackedContext:
    """
    Greedily include files from *ranked* (highest score first) until the
    token budget is exhausted.
    """
    result = PackedContext(budget_tokens=budget_tokens)
    used = 0

    for fp, score in ranked:
        try:
            content = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            result.excluded.append((fp, f"read error: {exc}"))
            continue

        tokens = count_tokens(content)

        if used + tokens > budget_tokens:
            if used == 0:
                # Single file already over budget — include truncated version
                limit_chars = int(budget_tokens * _CHARS_PER_TOKEN * 0.9)
                content = content[:limit_chars] + "\n\n... [truncated to fit budget]"
                tokens = count_tokens(content)
                result.included.append((fp, content, score))
                used += tokens
            else:
                result.excluded.append((fp, "budget exhausted"))
            continue

        result.included.append((fp, content, score))
        used += tokens

    result.total_tokens = used
    return result
