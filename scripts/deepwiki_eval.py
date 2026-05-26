#!/usr/bin/env python3
"""Evaluate DeepWiki memory health for a local project.

The evaluator is intentionally deterministic and dependency-free. It inspects
the DeepWiki file tree, Claude/Codex session metadata, optional UC mirror state,
and a small question-probe config to produce a memory scorecard.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCORE_WEIGHTS = {
    "retrieval_utility": 30,
    "protocol_compliance": 25,
    "handoff_quality": 20,
    "drift_freshness": 15,
    "efficiency": 10,
}

REQUIRED_PROJECT_FILES = [
    "NORTH_STAR.md",
    "planning/goals.md",
    "planning/phases.md",
    "memory/changelog.md",
    "memory/semantic/schemas.md",
]

OPTIONAL_PROJECT_FILES = [
    "memory/semantic/gotchas.md",
    "memory/semantic/patterns.md",
    "planning/decisions.md",
    "planning/open_questions.md",
    "context/codebase_map.md",
]

CHANGELOG_REQUIRED_SECTIONS = [
    "### Changes",
    "### Decisions",
    "### Schema Changes",
    "### Unfinished",
    "### Warnings for Next Session",
]

EPISODIC_EVENT_PATTERNS = {
    "has_plan": re.compile(r"(?mi)^###\s+.+-\s+Plan:"),
    "has_checkpoint": re.compile(r"(?mi)^###\s+.+-\s+(Checkpoint|Status):"),
    "has_close": re.compile(r"(?mi)^###\s+.+-\s+Close:"),
}

EPISODIC_STRUCTURED_SECTION = re.compile(
    r"(?mi)^####\s+(Objective|Plan|Status|Files Touched|Commands / Verification|Decisions / Rationale|Surprises / Failures|Unresolved / Next|Warnings)$"
)


@dataclass
class ProbeResult:
    id: str
    score: float
    found_paths: list[str] = field(default_factory=list)
    missing_paths: list[str] = field(default_factory=list)
    found_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    project: str
    root: str
    generated_at: str
    scores: dict[str, float]
    overall_score: float
    findings: list[str]
    recommendations: list[str]
    inventory: dict[str, Any]
    session_metadata: dict[str, Any]
    probes: list[ProbeResult]


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return ""


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def rel_files(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and path.name != ".DS_Store"
    )


def changelog_entries(text: str) -> list[str]:
    parts = re.split(r"(?m)^## ", text)
    return ["## " + part.strip() for part in parts[1:] if part.strip()]


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def file_age_days(path: Path, now: datetime) -> float | None:
    if not path.exists():
        return None
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return max(0.0, (now - mtime).total_seconds() / 86400)


def discover_project(root: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    north_star = read_text(root / "NORTH_STAR.md")
    match = re.search(r"^#\s+North Star\s+[—-]\s+(.+)$", north_star, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return root.parent.name if root.name == ".deepwiki" else root.name


def inspect_inventory(root: Path, now: datetime, project_root: Path) -> dict[str, Any]:
    files = rel_files(root)
    optional_files = list(OPTIONAL_PROJECT_FILES)
    has_databricks_manifest = (project_root / "databricks.yml").exists() or (project_root / "databricks.yaml").exists() or (project_root / "app.yaml").exists()
    if has_databricks_manifest:
        optional_files.append("context/dab_manifest.md")
    required = {path: (root / path).exists() for path in REQUIRED_PROJECT_FILES}
    optional = {path: (root / path).exists() for path in optional_files}
    ages = {
        path: file_age_days(root / path, now)
        for path in REQUIRED_PROJECT_FILES + optional_files
        if (root / path).exists()
    }
    sizes = {
        path: word_count(read_text(root / path))
        for path in files
        if path.endswith(".md")
    }
    episodic_dir = root / "memory" / "episodic"
    handoff_dir = root / "agents"
    episodic_logs = rel_files(episodic_dir)
    return {
        "files": files,
        "required_files": required,
        "optional_files": optional,
        "file_age_days": ages,
        "word_counts": sizes,
        "episodic_logs": episodic_logs,
        "episodic_quality": inspect_episodic_quality(episodic_dir),
        "handoff_files": rel_files(handoff_dir),
        "has_databricks_manifest": has_databricks_manifest,
    }


def inspect_episodic_quality(episodic_dir: Path, recent_limit: int = 5) -> dict[str, Any]:
    if not episodic_dir.exists():
        return {
            "recent_logs_checked": 0,
            "has_plan": False,
            "has_checkpoint": False,
            "has_close": False,
            "structured_section_count": 0,
            "recent_word_count": 0,
            "score": 0.0,
        }

    files = sorted(episodic_dir.glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    recent_texts = [read_text(path) for path in files[:recent_limit]]
    combined = "\n".join(recent_texts)
    has_plan = bool(EPISODIC_EVENT_PATTERNS["has_plan"].search(combined))
    has_checkpoint = bool(EPISODIC_EVENT_PATTERNS["has_checkpoint"].search(combined))
    has_close = bool(EPISODIC_EVENT_PATTERNS["has_close"].search(combined))
    structured_section_count = len(EPISODIC_STRUCTURED_SECTION.findall(combined))
    recent_word_count = word_count(combined)

    score = 0.0
    if files:
        score += 20.0
    if has_plan:
        score += 25.0
    if has_checkpoint:
        score += 25.0
    if has_close:
        score += 20.0
    if structured_section_count >= 3 and recent_word_count >= 80:
        score += 10.0

    return {
        "recent_logs_checked": min(len(files), recent_limit),
        "has_plan": has_plan,
        "has_checkpoint": has_checkpoint,
        "has_close": has_close,
        "structured_section_count": structured_section_count,
        "recent_word_count": recent_word_count,
        "score": round(score, 1),
    }


def inspect_changelog(root: Path) -> dict[str, Any]:
    text = read_text(root / "memory" / "changelog.md")
    entries = changelog_entries(text)
    section_counts = Counter()
    for entry in entries[:5]:
        for section in CHANGELOG_REQUIRED_SECTIONS:
            if section in entry:
                section_counts[section] += 1
    latest = entries[0] if entries else ""
    latest_missing = [s for s in CHANGELOG_REQUIRED_SECTIONS if s not in latest]
    return {
        "entry_count": len(entries),
        "latest_missing_sections": latest_missing,
        "section_counts_last_5": dict(section_counts),
        "latest_entry_words": word_count(latest),
    }


def session_rows_for_project(rows: list[dict[str, Any]], project: str, cwd: Path) -> list[dict[str, Any]]:
    cwd_str = str(cwd)
    project_lower = project.lower()
    matched = []
    for row in rows:
        row_project = str(row.get("project", "")).lower()
        row_cwd = str(row.get("cwd", ""))
        thread_name = str(row.get("thread_name", "")).lower()
        if row_project == project_lower or project_lower in thread_name or cwd_str in row_cwd or cwd.name.lower() in row_cwd.lower():
            matched.append(row)
    return matched


def inspect_sessions(project: str, cwd: Path, home: Path) -> dict[str, Any]:
    claude_path = home / ".claude" / "sessions-index.jsonl"
    codex_path = home / ".codex" / "session_index.jsonl"
    codex_history_path = home / ".codex" / "history.jsonl"

    claude_all = parse_jsonl(claude_path)
    codex_all = parse_jsonl(codex_path)
    codex_history = parse_jsonl(codex_history_path)

    claude_project = session_rows_for_project(claude_all, project, cwd)
    codex_project = session_rows_for_project(codex_all, project, cwd)

    claude_checkpoint_known = [r for r in claude_project if "has_checkpoint" in r]
    claude_checkpoint_true = [r for r in claude_checkpoint_known if r.get("has_checkpoint") is True]
    claude_changed = [r for r in claude_project if r.get("files_changed")]
    codex_deepwiki_threads = [
        r for r in codex_project if "deepwiki" in str(r.get("thread_name", "")).lower()
    ]

    latest_times = []
    for row in claude_project:
        dt = parse_iso(str(row.get("ts", "")))
        if dt:
            latest_times.append(dt)
    for row in codex_project:
        dt = parse_iso(str(row.get("updated_at", "")))
        if dt:
            latest_times.append(dt)

    return {
        "claude": {
            "path": str(claude_path),
            "total_rows": len(claude_all),
            "project_rows": len(claude_project),
            "project_rows_with_changed_files": len(claude_changed),
            "project_rows_with_checkpoint_true": len(claude_checkpoint_true),
            "project_rows_with_checkpoint_field": len(claude_checkpoint_known),
        },
        "codex": {
            "path": str(codex_path),
            "total_rows": len(codex_all),
            "project_rows": len(codex_project),
            "deepwiki_thread_rows": len(codex_deepwiki_threads),
            "history_rows": len(codex_history),
        },
        "latest_session_at": max(latest_times).isoformat() if latest_times else None,
    }


def load_probe_config(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError:
        return []
    return list(data.get("questions", []))


def resolve_probe_path(root: Path, rel: str) -> Path:
    path = (root / rel).resolve()
    try:
        path.relative_to(root.parent.resolve())
    except ValueError:
        return root / rel
    return path


def run_probes(root: Path, probes: list[dict[str, Any]]) -> list[ProbeResult]:
    results: list[ProbeResult] = []
    for probe in probes:
        expected_paths = list(probe.get("expected_paths", []))
        keywords = list(probe.get("keywords", []))
        found_paths: list[str] = []
        missing_paths: list[str] = []
        corpus = ""
        for rel in expected_paths:
            path = resolve_probe_path(root, rel)
            text = read_text(path)
            if text:
                found_paths.append(rel)
                corpus += "\n" + text
            else:
                missing_paths.append(rel)

        corpus_lower = corpus.lower()
        found_keywords = [kw for kw in keywords if kw.lower() in corpus_lower]
        missing_keywords = [kw for kw in keywords if kw.lower() not in corpus_lower]
        path_score = (
            100.0
            if not expected_paths
            else 100.0 * len(found_paths) / len(expected_paths)
        )
        keyword_score = 100.0 if not keywords else (100.0 * len(found_keywords) / len(keywords))
        score = 0.6 * path_score + 0.4 * keyword_score
        results.append(
            ProbeResult(
                id=str(probe.get("id", "unknown")),
                score=round(score, 1),
                found_paths=found_paths,
                missing_paths=missing_paths,
                found_keywords=found_keywords,
                missing_keywords=missing_keywords,
            )
        )
    return results


def score_retrieval_utility(probes: list[ProbeResult], inventory: dict[str, Any]) -> float:
    if probes:
        probe_score = sum(p.score for p in probes) / len(probes)
    else:
        probe_score = 50.0
    required = inventory["required_files"]
    required_score = 100.0 * sum(1 for ok in required.values() if ok) / len(required)
    return round(0.7 * probe_score + 0.3 * required_score, 1)


def score_protocol_compliance(inventory: dict[str, Any], changelog: dict[str, Any], sessions: dict[str, Any]) -> float:
    required = inventory["required_files"]
    required_score = 100.0 * sum(1 for ok in required.values() if ok) / len(required)
    latest_sections = CHANGELOG_REQUIRED_SECTIONS
    latest_section_score = 100.0 * (
        len(latest_sections) - len(changelog["latest_missing_sections"])
    ) / len(latest_sections)
    episodic_score = inventory["episodic_quality"]["score"]

    return round(
        0.30 * required_score
        + 0.45 * latest_section_score
        + 0.25 * episodic_score,
        1,
    )


def score_handoff_quality(inventory: dict[str, Any], changelog: dict[str, Any], sessions: dict[str, Any]) -> float:
    handoff_score = 100.0 if inventory["handoff_files"] else 35.0
    warnings_score = 0.0 if "### Warnings for Next Session" in changelog["latest_missing_sections"] else 100.0
    unfinished_score = 0.0 if "### Unfinished" in changelog["latest_missing_sections"] else 100.0
    platform_diversity = sum(
        1
        for key in ["claude", "codex"]
        if sessions[key]["project_rows"] > 0
    )
    diversity_score = 50.0 * platform_diversity
    return round(0.25 * handoff_score + 0.25 * warnings_score + 0.25 * unfinished_score + 0.25 * diversity_score, 1)


def score_drift_freshness(inventory: dict[str, Any], changelog: dict[str, Any], now: datetime, uc_mirror: Path | None) -> float:
    changelog_age = inventory["file_age_days"].get("memory/changelog.md")
    if changelog_age is None:
        freshness_score = 0.0
    elif changelog_age <= 7:
        freshness_score = 100.0
    elif changelog_age <= 30:
        freshness_score = 75.0
    elif changelog_age <= 90:
        freshness_score = 45.0
    else:
        freshness_score = 15.0

    schema_present = inventory["required_files"].get("memory/semantic/schemas.md", False)
    schema_score = 100.0 if schema_present else 0.0
    uc_score = 50.0
    if uc_mirror:
        mirror_changelog = uc_mirror / "memory" / "changelog.md"
        if mirror_changelog.exists():
            age = file_age_days(mirror_changelog, now)
            local_age = inventory["file_age_days"].get("memory/changelog.md")
            if age is not None and local_age is not None and abs(age - local_age) < 0.05:
                uc_score = 100.0
            else:
                uc_score = 70.0
        else:
            uc_score = 0.0

    section_score = 100.0 if changelog["entry_count"] else 0.0
    return round(0.35 * freshness_score + 0.25 * schema_score + 0.25 * uc_score + 0.15 * section_score, 1)


def score_efficiency(inventory: dict[str, Any], sessions: dict[str, Any]) -> float:
    word_counts = inventory["word_counts"]
    required_words = sum(word_counts.get(path, 0) for path in REQUIRED_PROJECT_FILES)
    if required_words <= 3500:
        token_budget_score = 100.0
    elif required_words <= 7000:
        token_budget_score = 80.0
    elif required_words <= 12000:
        token_budget_score = 55.0
    else:
        token_budget_score = 25.0

    total_files = len(inventory["files"])
    discoverability_score = 100.0 if total_files <= 30 else max(40.0, 100.0 - (total_files - 30) * 2)

    metadata_score = 0.0
    if sessions["claude"]["project_rows"] or sessions["codex"]["project_rows"]:
        metadata_score = 100.0
    elif sessions["claude"]["total_rows"] or sessions["codex"]["total_rows"]:
        metadata_score = 60.0

    return round(0.45 * token_budget_score + 0.30 * discoverability_score + 0.25 * metadata_score, 1)


def weighted_overall(scores: dict[str, float]) -> float:
    total = 0.0
    for key, weight in SCORE_WEIGHTS.items():
        total += scores[key] * weight / 100.0
    return round(total, 1)


def build_findings(
    inventory: dict[str, Any],
    changelog: dict[str, Any],
    sessions: dict[str, Any],
    probes: list[ProbeResult],
    scores: dict[str, float],
    uc_mirror: Path | None,
) -> tuple[list[str], list[str]]:
    findings: list[str] = []
    recommendations: list[str] = []

    missing_required = [path for path, ok in inventory["required_files"].items() if not ok]
    if missing_required:
        findings.append(f"Missing required DeepWiki files: {', '.join(missing_required)}.")
        recommendations.append("Create the missing required files before relying on cold-start preflight.")

    missing_optional = [path for path, ok in inventory["optional_files"].items() if not ok]
    if missing_optional:
        findings.append(f"Optional memory surfaces absent: {', '.join(missing_optional)}.")

    if changelog["latest_missing_sections"]:
        findings.append(
            "Latest changelog entry is missing sections: "
            + ", ".join(changelog["latest_missing_sections"])
            + "."
        )
        recommendations.append("Use the full changelog template for every session that changes files or decisions.")

    if not inventory["episodic_logs"]:
        findings.append("No episodic logs found under memory/episodic.")
        recommendations.append("Add raw episodic session logs or explicitly mark this workspace as changelog-only.")
    else:
        quality = inventory["episodic_quality"]
        missing_events = [
            label
            for label, present in [
                ("Plan", quality["has_plan"]),
                ("Checkpoint", quality["has_checkpoint"]),
                ("Close", quality["has_close"]),
            ]
            if not present
        ]
        if missing_events:
            findings.append(
                "Recent episodic logs are missing expected event types: "
                + ", ".join(missing_events)
                + "."
            )
            recommendations.append("Write in-flight Plan/Checkpoint events and a final Close event so interrupted sessions are recoverable.")
        if quality["structured_section_count"] < 3:
            findings.append("Recent episodic logs have too few structured sections for reliable handoff.")

    if sessions["claude"]["project_rows_with_checkpoint_field"] and sessions["claude"]["project_rows_with_checkpoint_true"] == 0:
        findings.append("Claude session metadata exposes has_checkpoint, but it is false for matched project rows; score ignores this signal until the hook is validated.")
        recommendations.append("Validate the Claude checkpoint hook before using has_checkpoint as a compliance metric.")

    low_probes = [p.id for p in probes if p.score < 70]
    if low_probes:
        findings.append(f"Low-scoring retrieval probes: {', '.join(low_probes)}.")
        recommendations.append("Add or enrich the files those probes expect, especially gotchas and handoff readiness.")

    low_dimensions = {
        "retrieval_utility": 70.0,
        "protocol_compliance": 80.0,
        "handoff_quality": 70.0,
        "drift_freshness": 70.0,
        "efficiency": 70.0,
    }
    for dimension, threshold in low_dimensions.items():
        score = scores[dimension]
        if score < threshold:
            findings.append(
                f"{dimension.replace('_', ' ').title()} score is below target: {score:.1f} < {threshold:.1f}."
            )
            if dimension == "handoff_quality":
                recommendations.append("Improve handoff memory with explicit warnings, unfinished work, agent handoff files, and cross-platform session metadata.")

    if uc_mirror is None:
        findings.append("UC mirror freshness was not evaluated because --uc-mirror was not provided.")
        recommendations.append("Run with --uc-mirror when a mounted or synced UC Volume mirror is available; local freshness alone is not proof of remote sync.")

    if not findings:
        findings.append("No major deterministic issues found.")
    if not recommendations:
        recommendations.append("Run the cold-resume evaluation with a fresh agent for qualitative validation.")

    return findings, recommendations


def evaluate(args: argparse.Namespace) -> EvalResult:
    root = Path(args.deepwiki_root).expanduser().resolve()
    cwd = Path(args.project_root).expanduser().resolve()
    now = datetime.now(timezone.utc)
    project = discover_project(root, args.project)
    config_path = Path(args.questions).expanduser().resolve()
    uc_mirror = Path(args.uc_mirror).expanduser().resolve() if args.uc_mirror else None

    inventory = inspect_inventory(root, now, cwd)
    changelog = inspect_changelog(root)
    sessions = inspect_sessions(project, cwd, Path.home())
    probes = run_probes(root, load_probe_config(config_path))
    inventory["uc_mirror_evaluated"] = uc_mirror is not None

    scores = {
        "retrieval_utility": score_retrieval_utility(probes, inventory),
        "protocol_compliance": score_protocol_compliance(inventory, changelog, sessions),
        "handoff_quality": score_handoff_quality(inventory, changelog, sessions),
        "drift_freshness": score_drift_freshness(inventory, changelog, now, uc_mirror),
        "efficiency": score_efficiency(inventory, sessions),
    }
    findings, recommendations = build_findings(inventory, changelog, sessions, probes, scores, uc_mirror)
    inventory["changelog"] = changelog

    return EvalResult(
        project=project,
        root=str(root),
        generated_at=now.isoformat(),
        scores=scores,
        overall_score=weighted_overall(scores),
        findings=findings,
        recommendations=recommendations,
        inventory=inventory,
        session_metadata=sessions,
        probes=probes,
    )


def result_to_dict(result: EvalResult) -> dict[str, Any]:
    return {
        "project": result.project,
        "root": result.root,
        "generated_at": result.generated_at,
        "overall_score": result.overall_score,
        "scores": result.scores,
        "findings": result.findings,
        "recommendations": result.recommendations,
        "inventory": result.inventory,
        "session_metadata": result.session_metadata,
        "probes": [probe.__dict__ for probe in result.probes],
    }


def grade(score: float) -> str:
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "healthy"
    if score >= 60:
        return "usable with gaps"
    if score >= 40:
        return "fragile"
    return "needs repair"


def render_markdown(result: EvalResult) -> str:
    lines = [
        f"# DeepWiki Memory Scorecard — {result.project}",
        "",
        f"Generated: `{result.generated_at}`",
        f"Root: `{result.root}`",
        "",
        f"**Overall:** {result.overall_score}/100 ({grade(result.overall_score)})",
        "",
        "## Scores",
        "",
        "| Dimension | Score | Weight |",
        "|---|---:|---:|",
    ]
    for key, weight in SCORE_WEIGHTS.items():
        label = key.replace("_", " ").title()
        lines.append(f"| {label} | {result.scores[key]:.1f} | {weight}% |")

    lines += ["", "## Findings", ""]
    lines += [f"- {finding}" for finding in result.findings]
    lines += ["", "## Recommendations", ""]
    lines += [f"- {rec}" for rec in result.recommendations]

    lines += ["", "## Retrieval Probes", "", "| Probe | Score | Missing Paths | Missing Keywords |", "|---|---:|---|---|"]
    for probe in result.probes:
        missing_paths = ", ".join(probe.missing_paths) or "-"
        missing_keywords = ", ".join(probe.missing_keywords) or "-"
        lines.append(f"| `{probe.id}` | {probe.score:.1f} | {missing_paths} | {missing_keywords} |")

    inv = result.inventory
    sessions = result.session_metadata
    lines += [
        "",
        "## Metadata Signals",
        "",
        f"- DeepWiki markdown files: {len([f for f in inv['files'] if f.endswith('.md')])}",
        f"- Changelog entries: {inv['changelog']['entry_count']}",
        f"- Episodic logs: {len(inv['episodic_logs'])}",
        f"- Handoff files: {len(inv['handoff_files'])}",
        f"- Claude matched session rows: {sessions['claude']['project_rows']} of {sessions['claude']['total_rows']}",
        f"- Codex matched session rows: {sessions['codex']['project_rows']} of {sessions['codex']['total_rows']}",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(result: EvalResult, markdown_path: str | None, json_path: str | None) -> None:
    if markdown_path:
        path = Path(markdown_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown(result), encoding="utf-8")
    if json_path:
        path = Path(json_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result_to_dict(result), indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate local DeepWiki memory health.")
    parser.add_argument("--deepwiki-root", default=".deepwiki", help="Path to the project .deepwiki root.")
    parser.add_argument("--project-root", default=".", help="Path to the project root used for session matching.")
    parser.add_argument("--project", default="", help="Project name override.")
    parser.add_argument(
        "--questions",
        default="configs/deepwiki_eval_questions.json",
        help="JSON probe config path.",
    )
    parser.add_argument("--uc-mirror", default="", help="Optional UC Volume mirror path mounted locally.")
    parser.add_argument("--markdown-out", default="", help="Optional Markdown report output path.")
    parser.add_argument("--json-out", default="", help="Optional JSON output path.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = evaluate(args)
    write_outputs(result, args.markdown_out or None, args.json_out or None)
    if args.format == "json":
        print(json.dumps(result_to_dict(result), indent=2))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
