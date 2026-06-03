# 📦 context-pack

![Python](https://img.shields.io/badge/python-3.9%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-0.1.0-orange)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

**Pack your codebase for AI assistants — intelligently, within a token budget.**

You have a question about your code. You open Claude or ChatGPT. And then you spend 10 minutes manually copy-pasting files, hitting context limits, and hoping you picked the right ones.

`context-pack` fixes that. Give it your question and your project folder — it ranks every file by relevance, fits as many as possible within your token budget, and outputs a clean, paste-ready context block in seconds.

```bash
context-pack pack "how does authentication work?"
context-pack pack "payment flow is broken" ./backend --budget 50k --clipboard
context-pack pack "add dark mode" --output context.md
```

---

## Why it exists

Modern AI assistants have large context windows (100k–200k tokens), but filling them *smartly* is still a manual chore. Most developers either:

- Paste too little → AI gives generic advice
- Paste too much → hits limits, slow, expensive
- Paste the wrong files → AI misses the point entirely

`context-pack` solves this with automatic relevance ranking. No API key required — it works with keyword matching and file analysis, entirely offline.

---

## Features

- 🎯 **Relevance ranking** — scores files by filename, content, and recency; most relevant files go first
- 💰 **Token budget** — fits as much as possible within your limit (8k / 32k / 100k / 128k / 200k…)
- 📋 **Clipboard mode** — `--clipboard` copies the result, ready to paste instantly
- 📄 **File output** — save to `.md` for reuse or sharing
- 🙈 **`.contextignore`** — exclude files you never want in AI context (like `.gitignore`)
- ⚡ **Fast** — no API calls needed; scans most projects in under a second
- 🎛️ **Accurate tokens** — uses `tiktoken` when available, approximates otherwise

---

## Installation

```bash
pip install context-pack
```

For accurate token counting (recommended):

```bash
pip install "context-pack[fast-tokens]"
```

From source:

```bash
git clone https://github.com/hevinbryant/context-pack.git
cd context-pack
pip install -e .
```

---

## Usage

### Basic — print to terminal

```bash
context-pack pack "how does the login flow work?"
```

### Copy to clipboard

```bash
context-pack pack "why is the payment failing?" --clipboard
```

Open Claude or ChatGPT, paste, ask your question.

### Save to a file

```bash
context-pack pack "refactor the auth module" --output context.md
```

### Set a token budget

```bash
# Budget presets: 8k, 16k, 32k, 50k, 100k, 128k, 200k
context-pack pack "database schema" ./backend --budget 32k

# Or specify an exact number
context-pack pack "API routes" --budget 75000
```

### Specify a directory

```bash
context-pack pack "React component structure" ./frontend
```

### List all files context-pack can see

```bash
context-pack scan ./my-project
```

---

## How it works

```
Your question + project folder
          │
          ▼
    Scan all code files
    (respects .contextignore)
          │
          ▼
    Score each file
    ┌─────────────────────────────┐
    │  Filename / path match  ×4  │
    │  Content keyword match  ×1  │
    │  Term frequency bonus  ×0.5 │
    │  Recency bonus         +1   │
    │  Anchor file bonus     +5   │
    └─────────────────────────────┘
          │
          ▼
    Greedily pack highest-scoring
    files within token budget
          │
          ▼
    Render clean Markdown
    with stats header + code blocks
          │
          ▼
    stdout / clipboard / file ✅
```

---

## The `.contextignore` file

Place a `.contextignore` in your project root to permanently exclude files from AI context. Same syntax as `.gitignore`:

```gitignore
# .contextignore

# Never expose generated code
src/generated/
**/*_pb2.py

# Large data files
data/
*.csv
*.parquet

# Test snapshots
tests/fixtures/snapshots/
```

See [`.contextignore.example`](.contextignore.example) for more patterns.

---

## Output format

The output is structured Markdown, designed to be pasted directly into any AI chat:

```markdown
# AI Context Pack

**Query:** how does authentication work?

| Stat             | Value   |
|------------------|---------|
| Files included   | 6       |
| Estimated tokens | ~12,400 |
| Budget used      | 12.4%   |

---

## `src/auth/middleware.py`
```python
[file contents]
```

## `src/auth/jwt.py`
```python
[file contents]
```
...
```

---

## All options

```
context-pack pack [OPTIONS] QUERY [PATH]

  QUERY   What you want to ask or do with this code
  PATH    Project directory (default: current directory)

Options:
  -b, --budget TEXT    Token budget (default: 100k)
  -o, --output FILE    Save to a file
  -c, --clipboard      Copy to clipboard
  -n, --top INTEGER    Only consider top N ranked files
  --scores             Show relevance scores in output
  --help               Show this message and exit.
```

---

## Contributing

Issues and PRs welcome. To run locally:

```bash
git clone https://github.com/hevinbryant/context-pack.git
cd context-pack
pip install -e ".[dev]"
pytest
ruff check context_pack/
```

---

## License

[MIT](LICENSE) © hevinbryant
