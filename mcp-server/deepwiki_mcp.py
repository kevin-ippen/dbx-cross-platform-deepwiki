"""
DeepWiki MCP Server — Thin wrapper over UC Volume .deepwiki files.

Exposes 5 tools for Genie Code / Databricks Assistant (MCP protocol):
  - deepwiki_preflight(project)   → Returns all pre-flight context concatenated
  - deepwiki_read(project, file)  → Read a specific .deepwiki file
  - deepwiki_search(query)        → Full-text search across all .deepwiki files
  - deepwiki_changelog(project, ...) → Append a changelog entry
  - deepwiki_list(project)        → List all files in a project's .deepwiki

Deployment: Databricks App (FastAPI) or run locally for testing.

Volume structure expected:
  {DEEPWIKI_VOLUME}/
    workspace/          ← workspace-level memory
    projects/           ← per-project memory
      {project-name}/
        NORTH_STAR.md
        planning/
        memory/
          changelog.md
          semantic/

Set DEEPWIKI_VOLUME env var to your UC Volume path:
  /Volumes/{catalog}/{schema}/{volume}
Or for local testing, point it at your local .deepwiki directory.
"""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VOLUME_BASE = os.environ.get(
    "DEEPWIKI_VOLUME",
    "/Volumes/{your-catalog}/{your-schema}/{your-volume}"
)

app = FastAPI(
    title="DeepWiki MCP Server",
    description="Persistent memory system for cross-platform agent sessions",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class ReadRequest(BaseModel):
    project: str          # project slug, or "workspace" for workspace-level files
    file: str             # relative path, e.g. "memory/semantic/schemas.md"


class PreflightRequest(BaseModel):
    project: str


class SearchRequest(BaseModel):
    query: str
    project: Optional[str] = None   # None = search all projects + workspace
    max_results: int = 10


class ChangelogRequest(BaseModel):
    project: str
    description: str = ""           # brief session description
    changes: list[str]              # what was created/modified/deleted
    decisions: list[str] = []       # choices made and why
    schema_changes: list[str] = []  # table/column changes with full paths
    warnings: list[str] = []        # things the next agent must know


class ListRequest(BaseModel):
    project: Optional[str] = None   # None = workspace level


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _volume_path(project: Optional[str], file: str = "") -> Path:
    """Resolve a volume path from project + relative file path."""
    base = Path(VOLUME_BASE)
    if project and project != "workspace":
        return base / "projects" / project / file
    return base / "workspace" / file


def _safe_read(path: Path) -> str:
    """Read a file; return empty string if not found."""
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError):
        return ""


def _list_md_files(root: Path) -> list[str]:
    """List all .md files relative to root."""
    if not root.exists():
        return []
    return sorted(str(f.relative_to(root)) for f in root.rglob("*.md"))


def _last_n_changelog_entries(changelog_text: str, n: int = 3) -> str:
    """Extract the last n changelog entries (## delimited)."""
    entries = re.split(r"^## ", changelog_text, flags=re.MULTILINE)
    last = entries[1 : n + 1] if len(entries) > 1 else []
    return "\n\n## ".join([""] + last).strip()


# ---------------------------------------------------------------------------
# MCP Tool Endpoints
# ---------------------------------------------------------------------------

@app.post("/tools/deepwiki_preflight")
def preflight(req: PreflightRequest):
    """Load all pre-flight context for a project in one call.

    Returns: AGENT_PROTOCOL + workspace gotchas + workspace patterns +
             project changelog (last 3 entries) + project schemas + project gotchas.
    """
    sections: dict[str, str] = {}

    ws = Path(VOLUME_BASE) / "workspace"
    sections["protocol"] = _safe_read(ws / "AGENT_PROTOCOL.md")
    sections["workspace_gotchas"] = _safe_read(ws / "memory" / "semantic" / "gotchas.md")
    sections["workspace_patterns"] = _safe_read(ws / "memory" / "semantic" / "patterns.md")

    proj = Path(VOLUME_BASE) / "projects" / req.project
    if not proj.exists():
        raise HTTPException(404, f"Project '{req.project}' not found in volume at {VOLUME_BASE}")

    changelog_text = _safe_read(proj / "memory" / "changelog.md")
    sections["changelog_last_3"] = _last_n_changelog_entries(changelog_text, 3)
    sections["project_schemas"] = _safe_read(proj / "memory" / "semantic" / "schemas.md")
    sections["project_gotchas"] = _safe_read(proj / "memory" / "semantic" / "gotchas.md")

    north_star = _safe_read(proj / "NORTH_STAR.md")
    if north_star:
        sections["north_star"] = north_star

    goals = _safe_read(proj / "planning" / "goals.md")
    if goals:
        sections["goals"] = goals

    return {
        "project": req.project,
        "sections": sections,
        "total_chars": sum(len(v) for v in sections.values()),
    }


@app.post("/tools/deepwiki_read")
def read_file(req: ReadRequest):
    """Read a specific .deepwiki file from a project or workspace."""
    if req.project == "workspace":
        path = Path(VOLUME_BASE) / "workspace" / req.file
    else:
        path = Path(VOLUME_BASE) / "projects" / req.project / req.file

    content = _safe_read(path)
    if not content:
        raise HTTPException(404, f"File not found: {req.project}/{req.file}")

    return {
        "project": req.project,
        "file": req.file,
        "content": content,
        "size_bytes": len(content.encode()),
    }


@app.post("/tools/deepwiki_search")
def search(req: SearchRequest):
    """Full-text search across .deepwiki files. Case-insensitive."""
    results: list[dict] = []
    query_lower = req.query.lower()
    base = Path(VOLUME_BASE)

    if req.project:
        search_dirs = [(req.project, base / "projects" / req.project)]
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
                    results.append({
                        "project": project_name,
                        "file": str(md_file.relative_to(root)),
                        "line_number": i + 1,
                        "context": "\n".join(lines[start:end]),
                    })
                    if len(results) >= req.max_results:
                        return {"query": req.query, "results": results, "truncated": True}

    return {"query": req.query, "results": results, "truncated": False}


@app.post("/tools/deepwiki_changelog")
def append_changelog(req: ChangelogRequest):
    """Append a properly formatted changelog entry to a project."""
    proj_dir = Path(VOLUME_BASE) / "projects" / req.project
    changelog_path = proj_dir / "memory" / "changelog.md"

    if not proj_dir.exists():
        raise HTTPException(404, f"Project '{req.project}' not found")

    today = date.today().isoformat()
    desc = req.description or "Session work"
    lines = [f"\n## {today} | Genie Code | {desc}\n", "### Changes"]
    lines += [f"- {c}" for c in req.changes]

    if req.decisions:
        lines += ["\n### Decisions"] + [f"- {d}" for d in req.decisions]
    if req.schema_changes:
        lines += ["\n### Schema Changes"] + [f"- {s}" for s in req.schema_changes]
    if req.warnings:
        lines += ["\n### Warnings for Next Session"] + [f"- {w}" for w in req.warnings]
    lines.append("\n---\n")
    entry = "\n".join(lines)

    existing = _safe_read(changelog_path)
    if existing:
        split = existing.split("\n")
        insert_idx = next(
            (i for i, l in enumerate(split) if l.startswith("## ") and i > 2),
            len(split)
        )
        split.insert(insert_idx, entry)
        new_content = "\n".join(split)
    else:
        new_content = f"# Changelog\n\n> Append-only, newest first.\n{entry}"

    changelog_path.parent.mkdir(parents=True, exist_ok=True)
    changelog_path.write_text(new_content, encoding="utf-8")

    return {"project": req.project, "status": "appended", "entry_date": today}


@app.post("/tools/deepwiki_list")
def list_files(req: ListRequest):
    """List all .deepwiki files for a project or the workspace."""
    if req.project:
        root = Path(VOLUME_BASE) / "projects" / req.project
        scope = req.project
    else:
        root = Path(VOLUME_BASE) / "workspace"
        scope = "workspace"

    if not root.exists():
        if not req.project:
            projects_dir = Path(VOLUME_BASE) / "projects"
            projects = sorted(p.name for p in projects_dir.iterdir() if p.is_dir()) \
                if projects_dir.exists() else []
            return {"scope": "index", "projects": projects}
        raise HTTPException(404, f"Project '{req.project}' not found")

    files = _list_md_files(root)
    return {"scope": scope, "files": files, "count": len(files)}


# ---------------------------------------------------------------------------
# Health + Info
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    base = Path(VOLUME_BASE)
    workspace_exists = (base / "workspace").exists()
    projects_dir = base / "projects"
    project_count = len(list(projects_dir.iterdir())) if projects_dir.exists() else 0
    return {
        "status": "healthy" if workspace_exists else "degraded",
        "volume_base": VOLUME_BASE,
        "workspace_exists": workspace_exists,
        "project_count": project_count,
    }


@app.get("/")
def root():
    return {
        "name": "deepwiki-mcp",
        "version": "1.0.0",
        "tools": [
            {"name": "deepwiki_preflight",  "description": "Load all pre-flight context for a project"},
            {"name": "deepwiki_read",        "description": "Read a specific .deepwiki file"},
            {"name": "deepwiki_search",      "description": "Full-text search across all .deepwiki files"},
            {"name": "deepwiki_changelog",   "description": "Append a changelog entry to a project"},
            {"name": "deepwiki_list",        "description": "List files in a project's .deepwiki"},
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
