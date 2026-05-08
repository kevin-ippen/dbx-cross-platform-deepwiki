"""
DeepWiki MCP Server — Persistent memory for cross-platform agent sessions.

Implements the MCP Streamable HTTP transport via the MCP Python SDK so
Genie Code can discover and invoke tools via JSON-RPC. Deploy as a
Databricks App named mcp-deepwiki.

Volume structure expected:
  {DEEPWIKI_VOLUME}/
    workspace/        ← workspace-level memory
    projects/         ← per-project memory
      {project-name}/
        NORTH_STAR.md
        planning/
        memory/
          changelog.md
          semantic/

Set DEEPWIKI_VOLUME env var: /Volumes/{catalog}/{schema}/{volume}
For local testing, point it at a local .deepwiki directory.
"""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VOLUME_BASE = os.environ.get(
    "DEEPWIKI_VOLUME",
    "/Volumes/{your-catalog}/{your-schema}/{your-volume}"
)

mcp = FastMCP("mcp-deepwiki")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError):
        return ""


def _list_md_files(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(str(f.relative_to(root)) for f in root.rglob("*.md"))


def _last_n_changelog_entries(text: str, n: int = 3) -> str:
    entries = re.split(r"^## ", text, flags=re.MULTILINE)
    last = entries[1 : n + 1] if len(entries) > 1 else []
    return "\n\n## ".join([""] + last).strip()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def deepwiki_preflight(project: str) -> str:
    """Load all pre-flight context for a project in one call.

    Returns: AGENT_PROTOCOL + workspace gotchas + workspace patterns +
    project changelog (last 3 entries) + project schemas + project gotchas
    + north star + current goals. Call this at the start of every session.
    """
    sections: dict[str, str] = {}

    ws = Path(VOLUME_BASE) / "workspace"
    sections["protocol"]           = _safe_read(ws / "AGENT_PROTOCOL.md")
    sections["workspace_gotchas"]  = _safe_read(ws / "memory" / "semantic" / "gotchas.md")
    sections["workspace_patterns"] = _safe_read(ws / "memory" / "semantic" / "patterns.md")

    proj = Path(VOLUME_BASE) / "projects" / project
    if not proj.exists():
        return f"ERROR: Project '{project}' not found at {VOLUME_BASE}/projects/"

    sections["changelog_last_3"]  = _last_n_changelog_entries(
        _safe_read(proj / "memory" / "changelog.md"), 3
    )
    sections["project_schemas"]   = _safe_read(proj / "memory" / "semantic" / "schemas.md")
    sections["project_gotchas"]   = _safe_read(proj / "memory" / "semantic" / "gotchas.md")

    north_star = _safe_read(proj / "NORTH_STAR.md")
    if north_star:
        sections["north_star"] = north_star

    goals = _safe_read(proj / "planning" / "goals.md")
    if goals:
        sections["goals"] = goals

    total_chars = sum(len(v) for v in sections.values())
    parts = [f"=== {k.upper()} ===\n{v}" for k, v in sections.items() if v]
    return f"# DeepWiki Pre-Flight: {project} ({total_chars} chars)\n\n" + "\n\n".join(parts)


@mcp.tool()
async def deepwiki_read(project: str, file: str) -> str:
    """Read a specific file from a project's .deepwiki memory.

    Use project='workspace' to read workspace-level files.
    file is a relative path, e.g. 'memory/semantic/schemas.md'.
    """
    if project == "workspace":
        path = Path(VOLUME_BASE) / "workspace" / file
    else:
        path = Path(VOLUME_BASE) / "projects" / project / file

    content = _safe_read(path)
    if not content:
        return f"ERROR: File not found: {project}/{file}"

    return f"# {project}/{file}\n\n{content}"


@mcp.tool()
async def deepwiki_search(query: str, project: str = "") -> str:
    """Full-text search across .deepwiki files. Case-insensitive.

    Leave project empty to search all projects and the workspace.
    Returns up to 10 matching excerpts with file path and line number.
    """
    results: list[str] = []
    query_lower = query.lower()
    base = Path(VOLUME_BASE)
    max_results = 10

    if project:
        search_dirs = [(project, base / "projects" / project)]
    else:
        search_dirs = [("workspace", base / "workspace")]
        projects_dir = base / "projects"
        if projects_dir.exists():
            for p in sorted(projects_dir.iterdir()):
                if p.is_dir():
                    search_dirs.append((p.name, p))

    for project_name, root in search_dirs:
        if not root.exists():
            continue
        for md_file in root.rglob("*.md"):
            try:
                lines = md_file.read_text(encoding="utf-8").split("\n")
            except Exception:
                continue
            for i, line in enumerate(lines):
                if query_lower in line.lower():
                    start, end = max(0, i - 1), min(len(lines), i + 2)
                    context = "\n".join(lines[start:end])
                    rel = str(md_file.relative_to(root))
                    results.append(f"[{project_name}/{rel}:{i + 1}]\n{context}")
                    if len(results) >= max_results:
                        return (
                            f"# Search: '{query}' (truncated at {max_results})\n\n"
                            + "\n\n---\n\n".join(results)
                        )

    if not results:
        return f"No results found for '{query}'"
    return f"# Search: '{query}' ({len(results)} results)\n\n" + "\n\n---\n\n".join(results)


@mcp.tool()
async def deepwiki_changelog(
    project: str,
    changes: list[str],
    description: str = "",
    decisions: list[str] | None = None,
    schema_changes: list[str] | None = None,
    warnings: list[str] | None = None,
) -> str:
    """Append a formatted changelog entry to a project.

    Call at the end of every session that changed anything.
    - changes: what was created, modified, or deleted (required)
    - decisions: non-obvious choices made and why
    - schema_changes: table/column changes with full catalog.schema.table paths
    - warnings: things the next agent must know to avoid breaking something
    """
    proj_dir = Path(VOLUME_BASE) / "projects" / project
    changelog_path = proj_dir / "memory" / "changelog.md"

    if not proj_dir.exists():
        return f"ERROR: Project '{project}' not found"

    today = date.today().isoformat()
    desc = description or "Session work"
    entry_lines = [f"\n## {today} | Genie Code | {desc}\n", "### Changes"]
    entry_lines += [f"- {c}" for c in changes]

    if decisions:
        entry_lines += ["\n### Decisions"] + [f"- {d}" for d in decisions]
    if schema_changes:
        entry_lines += ["\n### Schema Changes"] + [f"- {s}" for s in schema_changes]
    if warnings:
        entry_lines += ["\n### Warnings for Next Session"] + [f"- {w}" for w in warnings]
    entry_lines.append("\n---\n")
    entry = "\n".join(entry_lines)

    existing = _safe_read(changelog_path)
    if existing:
        split = existing.split("\n")
        insert_idx = next(
            (i for i, ln in enumerate(split) if ln.startswith("## ") and i > 2),
            len(split),
        )
        split.insert(insert_idx, entry)
        new_content = "\n".join(split)
    else:
        new_content = f"# Changelog\n\n> Append-only, newest first.\n{entry}"

    changelog_path.parent.mkdir(parents=True, exist_ok=True)
    changelog_path.write_text(new_content, encoding="utf-8")

    return f"Changelog updated for '{project}' on {today}."


@mcp.tool()
async def deepwiki_list(project: str = "") -> str:
    """List .deepwiki files for a project, or list all available projects.

    Leave project empty to see all projects.
    Use project='workspace' for workspace-level files.
    """
    base = Path(VOLUME_BASE)

    if not project:
        projects_dir = base / "projects"
        projects = (
            sorted(p.name for p in projects_dir.iterdir() if p.is_dir())
            if projects_dir.exists()
            else []
        )
        return "# Available Projects\n\n" + "\n".join(f"- {p}" for p in projects)

    root = base / "workspace" if project == "workspace" else base / "projects" / project

    if not root.exists():
        return f"ERROR: Project '{project}' not found"

    files = _list_md_files(root)
    return f"# Files in {project} ({len(files)} files)\n\n" + "\n".join(f"- {f}" for f in files)


# ---------------------------------------------------------------------------
# ASGI app — served by uvicorn; MCP endpoint is at /mcp
# ---------------------------------------------------------------------------

app = mcp.streamable_http_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
