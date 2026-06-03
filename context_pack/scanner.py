"""Scan a directory and return code files, respecting ignore rules."""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import List

# Directories that are never useful for AI context
IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", ".svelte-kit", "target",
    "vendor", ".tox", "htmlcov", "coverage", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".eggs", "eggs", ".idea", ".vscode",
    "out", "bin", "obj", ".gradle", ".mvn", "Pods",
}

# File extensions worth including in AI context
CODE_EXTENSIONS = {
    # General purpose
    ".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
    # Systems / compiled
    ".rs", ".go", ".c", ".cpp", ".h", ".hpp", ".cs", ".java",
    ".kt", ".swift", ".zig", ".ex", ".exs", ".erl", ".scala",
    # Web
    ".html", ".css", ".scss", ".sass", ".vue", ".svelte",
    # Config / infra
    ".yaml", ".yml", ".toml", ".json", ".env.example",
    ".dockerfile", ".tf", ".hcl",
    # Docs / text
    ".md", ".mdx", ".txt", ".rst",
    # Scripts
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".rb", ".lua",
    ".r", ".jl", ".php", ".dart",
}

# Specific important filenames (no extension or unusual names)
IMPORTANT_NAMES = {
    "Makefile", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "Gemfile", "Rakefile", "Procfile", "CMakeLists.txt",
    "package.json", "pyproject.toml", "setup.py", "Cargo.toml",
    "go.mod", "pom.xml", "build.gradle",
}

MAX_FILE_SIZE = 200 * 1024  # 200 KB — skip unusually large files


def scan(path: Path, contextignore: Path | None = None) -> List[Path]:
    """
    Recursively collect code files under *path*.
    Respects a .contextignore file if present (same syntax as .gitignore).
    Returns a flat sorted list of Path objects.
    """
    ignore_patterns = _load_contextignore(contextignore or path / ".contextignore")
    files: List[Path] = []

    for root, dirs, filenames in os.walk(path):
        root_path = Path(root)

        # Prune ignored directories in-place
        dirs[:] = [
            d for d in sorted(dirs)
            if d not in IGNORE_DIRS
            and not d.startswith(".")
            and not _matches_any(str(root_path / d), ignore_patterns)
        ]

        for name in filenames:
            fp = root_path / name
            rel = str(fp.relative_to(path))

            # Skip by ignore patterns
            if _matches_any(rel, ignore_patterns):
                continue

            # Skip by size
            try:
                if fp.stat().st_size > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue

            # Include if matching extension or important name
            if fp.suffix.lower() in CODE_EXTENSIONS or name in IMPORTANT_NAMES:
                files.append(fp)

    return sorted(files)


def _load_contextignore(path: Path) -> List[str]:
    """Load patterns from a .contextignore file."""
    if not path.is_file():
        return []
    patterns = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def _matches_any(rel_path: str, patterns: List[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(Path(rel_path).name, pat):
            return True
    return False
