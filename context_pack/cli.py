"""Command-line interface for context-pack."""
from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .formatter import render
from .packer import pack
from .ranker import rank
from .scanner import scan

console = Console()

_BUDGET_PRESETS = {
    "8k": 8_000,
    "16k": 16_000,
    "32k": 32_000,
    "50k": 50_000,
    "100k": 100_000,
    "128k": 128_000,
    "200k": 200_000,
}


def _parse_budget(value: str) -> int:
    v = value.strip().lower()
    if v in _BUDGET_PRESETS:
        return _BUDGET_PRESETS[v]
    try:
        return int(v)
    except ValueError:
        raise click.BadParameter(
            f"Budget must be a number or one of: {', '.join(_BUDGET_PRESETS)}"
        )


# ── Root group ─────────────────────────────────────────────────────────────────

@click.group()
@click.version_option(package_name="context-pack")
def main() -> None:
    """context-pack — Pack your codebase for AI assistants.

    Intelligently selects the most relevant files for your query and
    packages them within a token budget, ready to paste into Claude,
    ChatGPT, or any other AI assistant.
    """


# ── pack command ───────────────────────────────────────────────────────────────

@main.command("pack")
@click.argument("query")
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--budget", "-b", default="100k", show_default=True,
    help="Token budget: 8k / 16k / 32k / 50k / 100k / 128k / 200k, or a raw number.",
)
@click.option(
    "--output", "-o", default=None,
    type=click.Path(dir_okay=False),
    help="Write output to a file instead of stdout.",
)
@click.option(
    "--clipboard", "-c", is_flag=True, default=False,
    help="Copy output to clipboard.",
)
@click.option(
    "--scores", is_flag=True, default=False,
    help="Show relevance scores as HTML comments in output.",
)
@click.option(
    "--top", "-n", default=None, type=int,
    help="Only consider the top N ranked files (before budget check).",
)
def pack_cmd(
    query: str,
    path: str,
    budget: str,
    output: str | None,
    clipboard: bool,
    scores: bool,
    top: int | None,
) -> None:
    """Pack the most relevant files from PATH for QUERY.

    \b
    Examples:
      context-pack pack "authentication middleware"
      context-pack pack "payment flow" ./backend --budget 50k
      context-pack pack "dark mode toggle" --clipboard
      context-pack pack "API structure" --output context.md
    """
    base = Path(path).resolve()
    budget_tokens = _parse_budget(budget)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        t = progress.add_task("🔍  Scanning files …", total=None)
        files = scan(base)

        progress.update(t, description=f"📊  Ranking {len(files)} files …")
        ranked = rank(query, files, base)
        if top:
            ranked = ranked[:top]

        progress.update(t, description="📦  Packing within budget …")
        ctx = pack(ranked, base, budget_tokens=budget_tokens)

        progress.update(t, description="✍️   Rendering output …")
        result = render(ctx, query=query, base=base, show_scores=scores)

    # ── Stats panel ────────────────────────────────────────────────────────────
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("Files scanned", str(len(files)))
    table.add_row("Files included", f"[green]{len(ctx.included)}[/]")
    table.add_row("Files excluded", str(len(ctx.excluded)))
    table.add_row("Estimated tokens", f"~{ctx.total_tokens:,}")
    table.add_row("Budget used", f"{ctx.utilisation_pct:.1f}%")
    console.print(Panel(table, title="context-pack", expand=False))

    if ctx.included:
        console.print("\n[dim]Included files (by relevance):[/]")
        for fp, _, sc in ctx.included[:10]:
            rel = str(fp.relative_to(base))
            console.print(f"  [cyan]{rel}[/]  [dim](score {sc:.1f})[/]")
        if len(ctx.included) > 10:
            console.print(f"  [dim]… and {len(ctx.included) - 10} more[/]")

    # ── Output routing ─────────────────────────────────────────────────────────
    if output:
        Path(output).write_text(result, encoding="utf-8")
        console.print(f"\n[green]✅ Saved to[/] [bold]{output}[/]")
    elif clipboard:
        _copy_to_clipboard(result)
        console.print("\n[green]✅ Copied to clipboard![/] Paste into your AI assistant.")
    else:
        # Print to stdout (pipe-friendly)
        click.echo(result)


# ── scan command ───────────────────────────────────────────────────────────────

@main.command("scan")
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
def scan_cmd(path: str) -> None:
    """List all files that context-pack would consider for a given PATH."""
    base = Path(path).resolve()
    files = scan(base)
    console.print(f"\n[bold]{len(files)} files found[/] under [cyan]{base}[/]\n")
    for fp in files:
        console.print(f"  {fp.relative_to(base)}")


# ── Clipboard helper ───────────────────────────────────────────────────────────

def _copy_to_clipboard(text: str) -> None:
    """Copy text to system clipboard (cross-platform)."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return
    except ImportError:
        pass
    # Fallback: platform-specific
    import subprocess, sys
    if sys.platform == "darwin":
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
    elif sys.platform == "win32":
        subprocess.run(["clip"], input=text.encode("utf-16"), check=True)
    else:
        try:
            subprocess.run(["xclip", "-selection", "clipboard"],
                           input=text.encode(), check=True)
        except FileNotFoundError:
            subprocess.run(["xdotool", "type", "--clearmodifiers", text], check=False)
