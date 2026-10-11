"""ASO Lilit — isolated read-only MCP observer for Andreslav."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

BASE = Path(__file__).resolve().parent
CONFIG = BASE / "config.json"

def load_config():
    with CONFIG.open(encoding="utf-8") as f:
        config = json.load(f)
    roots = config.get("allowed_roots", {})
    if not isinstance(roots, dict) or not roots:
        raise ValueError("Configure at least one allowed root")
    return {key: Path(value).resolve(strict=True) for key, value in roots.items()}

ROOTS = load_config()
mcp = FastMCP("ASO Lilit", instructions="Read-only observer of Andreslav. Never modifies project files.")


def safe_path(root_name: str, relative_path: str) -> Path:
    if root_name not in ROOTS:
        raise ValueError("Unknown allowed root")
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Absolute or parent traversal paths are not allowed")
    root = ROOTS[root_name]
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Path escapes selected root")
    return path


@mcp.tool()
def health() -> dict:
    """Report observer configuration and current UTC time; no project mutation."""
    return {"name": "ASO Lilit", "mode": "read_only", "time_utc": datetime.now(timezone.utc).isoformat(),
            "roots": {name: str(path) for name, path in ROOTS.items()}}


@mcp.tool()
def list_files(root_name: str = "andreslav", relative_path: str = ".", limit: int = 100) -> dict:
    """List immediate directory entries under an allowed root."""
    limit = max(1, min(limit, 200))
    directory = safe_path(root_name, relative_path)
    if not directory.is_dir():
        raise ValueError("Not a directory")
    items = []
    for p in sorted(directory.iterdir(), key=lambda x: x.name.lower()):
        if p.name == ".git" or p.is_symlink():
            continue
        items.append({"name": p.name, "kind": "directory" if p.is_dir() else "file"})
        if len(items) >= limit:
            break
    return {"root": root_name, "path": relative_path, "entries": items}


@mcp.tool()
def read_project_text(root_name: str, relative_path: str, max_lines: int = 160) -> dict:
    """Read a bounded portion of a project text file from an allowed root."""
    max_lines = max(1, min(max_lines, 300))
    path = safe_path(root_name, relative_path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("Not a regular file")
    if path.suffix.lower() not in {".md", ".txt", ".csv", ".mq4", ".mqh", ".json", ".yml", ".yaml", ".ps1"}:
        raise ValueError("Extension not permitted")
    if path.stat().st_size > 2_000_000:
        raise ValueError("File too large")
    lowered = path.name.lower()
    if any(x in lowered for x in ("secret", "token", "credential", "password", ".env")):
        raise ValueError("Sensitive filename denied")
    lines = []
    with path.open("r", encoding="utf-8-sig", errors="replace") as f:
        for _, line in zip(range(max_lines), f):
            lines.append(line.rstrip("\r\n")[:2000])
    return {"root": root_name, "path": relative_path, "lines": lines}


def git(*args: str) -> dict:
    root = ROOTS["andreslav"]
    binary = os.environ.get("ASO_GIT", "git")
    result = subprocess.run([binary, "-C", str(root), *args], shell=False,
                            capture_output=True, text=True, errors="replace", timeout=12, stdin=subprocess.DEVNULL)
    return {"exit_code": result.returncode, "stdout": result.stdout[:16000], "stderr": result.stderr[:2000]}


@mcp.tool()
def git_status() -> dict:
    """Report current branch and uncommitted changes; no fetch/pull/push."""
    return git("status", "--short", "--branch")


@mcp.tool()
def git_recent_commits(count: int = 8) -> dict:
    """Return recent local commit metadata; no network requests."""
    return git("log", f"-{max(1, min(count, 30))}", "--date=iso-strict", "--pretty=format:%h %ad %s")


if __name__ == "__main__":
    mcp.run(transport="stdio")
