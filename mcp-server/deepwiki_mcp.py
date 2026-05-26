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
          episodic/
          changelog.md
          semantic/

Set DEEPWIKI_VOLUME env var: /Volumes/{catalog}/{schema}/{volume}
For local testing, point it at a local .deepwiki directory.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime
from difflib import SequenceMatcher
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


def _normalize_project_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _project_tokens(value: str) -> set[str]:
    return {tok for tok in re.split(r"[^a-z0-9]+", value.lower()) if tok}


def _project_aliases(name: str) -> set[str]:
    aliases = {name, name.replace("_", "-"), name.replace("-", "_"), name.replace("-", " ")}
    aliases.add(_normalize_project_name(name))
    return {alias for alias in aliases if alias}


def _project_similarity(query: str, candidate: str) -> float:
    q_norm = _normalize_project_name(query)
    c_norm = _normalize_project_name(candidate)
    seq = SequenceMatcher(None, q_norm, c_norm).ratio() if q_norm and c_norm else 0.0
    q_tokens = _project_tokens(query)
    c_tokens = _project_tokens(candidate)
    if q_tokens or c_tokens:
        token = len(q_tokens & c_tokens) / max(1, len(q_tokens | c_tokens))
        query_coverage = len(q_tokens & c_tokens) / max(1, len(q_tokens))
    else:
        token = 0.0
        query_coverage = 0.0
    contains = 1.0 if q_norm and (q_norm in c_norm or c_norm in q_norm) else 0.0
    return round(max(seq, 0.82 * token + 0.18 * contains, 0.88 * query_coverage + 0.12 * token), 4)


def _resolve_project(project: str, min_score: float = 0.72) -> dict:
    projects_dir = Path(VOLUME_BASE) / "projects"
    projects = sorted(p.name for p in projects_dir.iterdir() if p.is_dir()) if projects_dir.exists() else []
    scored = []
    requested = project.strip()
    for candidate in projects:
        score = max(_project_similarity(project, alias) for alias in _project_aliases(candidate))
        if requested == candidate:
            score = 1.0
        if score >= min_score:
            scored.append({"project": candidate, "score": score})
    scored.sort(key=lambda row: (-row["score"], row["project"]))
    exact = [row for row in scored if row["project"] == requested]
    status = "exact" if len(exact) == 1 else "ambiguous" if len(scored) > 1 else "candidate" if scored else "not_found"
    return {"query": project, "status": status, "matches": scored}


def _resolved_project(project: str, *, require_exact: bool = False) -> tuple[str, str]:
    resolution = _resolve_project(project)
    if require_exact and resolution["status"] != "exact":
        candidates = ", ".join(f"{m['project']} ({m['score']:.2f})" for m in resolution["matches"][:5])
        detail = f" Candidates: {candidates}" if candidates else ""
        raise ValueError(
            f"Project '{project}' did not resolve exactly (status={resolution['status']})."
            f"{detail} Call deepwiki_resolve_project and retry with the exact project name."
        )
    if resolution["matches"]:
        top = resolution["matches"][0]
        warning = ""
        if top["project"] != project:
            warning = (
                f"NOTE: Project name '{project}' fuzzy-resolved to '{top['project']}' "
                f"(score={top['score']:.2f}).\n\n"
            )
        return top["project"], warning
    return project, ""


def _slugify(value: str, default: str = "session") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug[:72].strip("-") or default)


def _section(title: str, values: list[str] | None, checkbox: bool = False) -> list[str]:
    if not values:
        return []
    prefix = "- [ ] " if checkbox else "- "
    return [f"\n#### {title}", *[f"{prefix}{v}" for v in values if v]]


def _tail_text(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    return "[truncated: showing most recent content]\n" + text[-max_chars:]


def _recent_episodic(root: Path, limit: int = 2, max_chars_per_file: int = 6000) -> dict[str, str]:
    episodic_dir = root / "memory" / "episodic"
    if not episodic_dir.exists():
        return {}
    files = sorted(episodic_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {
        f"episodic_{idx + 1}_{path.name}": _tail_text(_safe_read(path), max_chars_per_file)
        for idx, path in enumerate(files[:limit])
    }


def _append_episodic_event(
    project: str,
    summary: str,
    event_type: str = "Checkpoint",
    platform: str = "Genie Code",
    session_slug: str = "",
    objective: list[str] | None = None,
    plan: list[str] | None = None,
    status: list[str] | None = None,
    files: list[str] | None = None,
    commands: list[str] | None = None,
    decisions: list[str] | None = None,
    surprises: list[str] | None = None,
    unresolved: list[str] | None = None,
    warnings: list[str] | None = None,
) -> tuple[Path, str, str]:
    resolved, warning = _resolved_project(project, require_exact=True)
    proj_dir = Path(VOLUME_BASE) / "projects" / resolved
    if not proj_dir.exists():
        raise FileNotFoundError(f"Project '{project}' not found")

    today = date.today().isoformat()
    path = proj_dir / "memory" / "episodic" / f"{today}_{_slugify(platform, 'agent')}_{_slugify(session_slug or summary)}.md"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# Episodic Log - {today} | {platform} | {summary}\n\n## Timeline\n",
            encoding="utf-8",
        )

    now = datetime.now().strftime("%H:%M:%S")
    lines = [
        "",
        f"### {now} - {event_type}: {summary}",
        *_section("Objective", objective),
        *_section("Plan", plan),
        *_section("Status", status),
        *_section("Files Touched", files),
        *_section("Commands / Verification", commands),
        *_section("Decisions / Rationale", decisions),
        *_section("Surprises / Failures", surprises),
        *_section("Unresolved / Next", unresolved, checkbox=True),
        *_section("Warnings", warnings),
        "",
    ]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return path, resolved, warning


def _append_changelog_entry(
    project: str,
    changes: list[str],
    description: str = "",
    decisions: list[str] | None = None,
    schema_changes: list[str] | None = None,
    unfinished: list[str] | None = None,
    warnings: list[str] | None = None,
    platform: str = "Genie Code",
) -> tuple[Path, str, str]:
    resolved, warning = _resolved_project(project, require_exact=True)
    proj_dir = Path(VOLUME_BASE) / "projects" / resolved
    changelog_path = proj_dir / "memory" / "changelog.md"

    if not proj_dir.exists():
        raise FileNotFoundError(f"Project '{project}' not found")

    today = date.today().isoformat()
    desc = description or "Session work"
    entry_lines = [f"\n## {today} | {platform} | {desc}\n", "### Changes"]
    entry_lines += [f"- {c}" for c in (changes or ["None"])]
    entry_lines += ["\n### Decisions"] + [f"- {d}" for d in (decisions or ["None"])]
    entry_lines += ["\n### Schema Changes"] + [f"- {s}" for s in (schema_changes or ["None"])]
    entry_lines += ["\n### Unfinished"]
    entry_lines += [f"- [ ] {u}" for u in unfinished] if unfinished else ["- None"]
    entry_lines += ["\n### Warnings for Next Session"] + [f"- {w}" for w in (warnings or ["None"])]
    entry_lines.append("\n---\n")
    entry = "\n".join(entry_lines)

    existing = _safe_read(changelog_path)
    if existing:
        split = existing.split("\n")
        insert_idx = next((i for i, ln in enumerate(split) if ln.startswith("## ")), len(split))
        split.insert(insert_idx, entry)
        new_content = "\n".join(split)
    else:
        new_content = f"# Changelog\n\n> Append-only, newest first.\n{entry}"

    changelog_path.parent.mkdir(parents=True, exist_ok=True)
    changelog_path.write_text(new_content, encoding="utf-8")
    return changelog_path, resolved, warning


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def deepwiki_preflight(project: str) -> str:
    """Load all pre-flight context for a project in one call.

    Returns: AGENT_PROTOCOL + workspace gotchas + workspace patterns +
    project changelog (last 3 entries) + recent episodic logs + project schemas
    + project gotchas + north star + current goals. Call this at the start of every session.
    """
    sections: dict[str, str] = {}
    resolved, warning = _resolved_project(project)

    ws = Path(VOLUME_BASE) / "workspace"
    sections["protocol"]           = _safe_read(ws / "AGENT_PROTOCOL.md")
    sections["workspace_gotchas"]  = _safe_read(ws / "memory" / "semantic" / "gotchas.md")
    sections["workspace_patterns"] = _safe_read(ws / "memory" / "semantic" / "patterns.md")

    proj = Path(VOLUME_BASE) / "projects" / resolved
    if not proj.exists():
        return f"ERROR: Project '{project}' not found at {VOLUME_BASE}/projects/"

    sections["changelog_last_3"]  = _last_n_changelog_entries(
        _safe_read(proj / "memory" / "changelog.md"), 3
    )
    sections["project_schemas"]   = _safe_read(proj / "memory" / "semantic" / "schemas.md")
    sections["project_gotchas"]   = _safe_read(proj / "memory" / "semantic" / "gotchas.md")
    sections.update(_recent_episodic(proj, limit=2))

    north_star = _safe_read(proj / "NORTH_STAR.md")
    if north_star:
        sections["north_star"] = north_star

    goals = _safe_read(proj / "planning" / "goals.md")
    if goals:
        sections["goals"] = goals

    total_chars = sum(len(v) for v in sections.values())
    parts = [f"=== {k.upper()} ===\n{v}" for k, v in sections.items() if v]
    return f"# DeepWiki Pre-Flight: {resolved} ({total_chars} chars)\n\n{warning}" + "\n\n".join(parts)


@mcp.tool()
async def deepwiki_resolve_project(project: str, min_score: float = 0.72) -> str:
    """Fuzzy-resolve a project name before preflight or creating memory."""
    result = _resolve_project(project, min_score)
    if not result["matches"]:
        return f"# Project resolution: {project}\n\nstatus: not_found\n"
    lines = [f"# Project resolution: {project}", "", f"status: {result['status']}"]
    lines += [f"- {m['project']} ({m['score']:.2f})" for m in result["matches"]]
    return "\n".join(lines)


@mcp.tool()
async def deepwiki_read(project: str, file: str) -> str:
    """Read a specific file from a project's .deepwiki memory.

    Use project='workspace' to read workspace-level files.
    file is a relative path, e.g. 'memory/semantic/schemas.md'.
    """
    if project == "workspace":
        path = Path(VOLUME_BASE) / "workspace" / file
    else:
        resolved, warning = _resolved_project(project)
        path = Path(VOLUME_BASE) / "projects" / resolved / file

    content = _safe_read(path)
    if not content:
        return f"ERROR: File not found: {project}/{file}"

    return f"# {project}/{file}\n\n{locals().get('warning', '')}{content}"


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
        resolved, _warning = _resolved_project(project)
        search_dirs = [(resolved, base / "projects" / resolved)]
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
    unfinished: list[str] | None = None,
    warnings: list[str] | None = None,
    platform: str = "Genie Code",
) -> str:
    """Append a formatted changelog entry to a project.

    Call at the end of every session that changed anything.
    - changes: what was created, modified, or deleted (required)
    - decisions: non-obvious choices made and why
    - schema_changes: table/column changes with full catalog.schema.table paths
    - warnings: things the next agent must know to avoid breaking something
    """
    try:
        path, resolved, warning = _append_changelog_entry(
            project=project,
            changes=changes,
            description=description,
            decisions=decisions,
            schema_changes=schema_changes,
            unfinished=unfinished,
            warnings=warnings,
            platform=platform,
        )
    except (FileNotFoundError, ValueError) as exc:
        return f"ERROR: {exc}"
    return f"{warning}Changelog updated for '{resolved}' at {path.relative_to(Path(VOLUME_BASE) / 'projects' / resolved)}."


@mcp.tool()
async def deepwiki_checkpoint(
    project: str,
    summary: str,
    event_type: str = "Checkpoint",
    platform: str = "Genie Code",
    session_slug: str = "",
    objective: list[str] | None = None,
    plan: list[str] | None = None,
    status: list[str] | None = None,
    files: list[str] | None = None,
    commands: list[str] | None = None,
    decisions: list[str] | None = None,
    surprises: list[str] | None = None,
    unresolved: list[str] | None = None,
    warnings: list[str] | None = None,
) -> str:
    """Append an in-flight plan/status/checkpoint event to episodic memory."""
    try:
        path, resolved, warning = _append_episodic_event(
            project=project,
            summary=summary,
            event_type=event_type,
            platform=platform,
            session_slug=session_slug,
            objective=objective,
            plan=plan,
            status=status,
            files=files,
            commands=commands,
            decisions=decisions,
            surprises=surprises,
            unresolved=unresolved,
            warnings=warnings,
        )
    except (FileNotFoundError, ValueError) as exc:
        return f"ERROR: {exc}"
    return f"{warning}Episodic event appended for '{resolved}' at {path.relative_to(Path(VOLUME_BASE) / 'projects' / resolved)}."


@mcp.tool()
async def deepwiki_episodic(
    project: str,
    summary: str,
    event_type: str = "Checkpoint",
    platform: str = "Genie Code",
    session_slug: str = "",
    objective: list[str] | None = None,
    plan: list[str] | None = None,
    status: list[str] | None = None,
    files: list[str] | None = None,
    commands: list[str] | None = None,
    decisions: list[str] | None = None,
    surprises: list[str] | None = None,
    unresolved: list[str] | None = None,
    warnings: list[str] | None = None,
) -> str:
    """Append an episodic flight-recorder event."""
    return await deepwiki_checkpoint(
        project=project,
        summary=summary,
        event_type=event_type,
        platform=platform,
        session_slug=session_slug,
        objective=objective,
        plan=plan,
        status=status,
        files=files,
        commands=commands,
        decisions=decisions,
        surprises=surprises,
        unresolved=unresolved,
        warnings=warnings,
    )


@mcp.tool()
async def deepwiki_close_session(
    project: str,
    summary: str,
    changes: list[str],
    platform: str = "Genie Code",
    session_slug: str = "",
    objective: list[str] | None = None,
    files: list[str] | None = None,
    commands: list[str] | None = None,
    decisions: list[str] | None = None,
    schema_changes: list[str] | None = None,
    surprises: list[str] | None = None,
    unfinished: list[str] | None = None,
    warnings: list[str] | None = None,
) -> str:
    """Append a final episodic close event and a changelog entry."""
    try:
        episodic_path, resolved, warning = _append_episodic_event(
            project=project,
            summary=summary,
            event_type="Close",
            platform=platform,
            session_slug=session_slug,
            objective=objective,
            status=changes,
            files=files,
            commands=commands,
            decisions=decisions,
            surprises=surprises,
            unresolved=unfinished,
            warnings=warnings,
        )
        changelog_path, _, _ = _append_changelog_entry(
            project=resolved,
            changes=changes,
            description=summary,
            decisions=decisions,
            schema_changes=schema_changes,
            unfinished=unfinished,
            warnings=warnings,
            platform=platform,
        )
    except (FileNotFoundError, ValueError) as exc:
        return f"ERROR: {exc}"
    root = Path(VOLUME_BASE) / "projects" / resolved
    return (
        f"{warning}Session closed for '{resolved}'.\n"
        f"- Episodic: {episodic_path.relative_to(root)}\n"
        f"- Changelog: {changelog_path.relative_to(root)}"
    )


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
