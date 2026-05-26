#!/usr/bin/env python3
"""Append DeepWiki episodic flight-recorder events and close-session summaries."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


def slugify(value: str, default: str = "session") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug[:72].strip("-") or default)


def normalize_platform(value: str) -> str:
    return slugify(value, default="agent")


def bullet_lines(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values if value]


def section(title: str, values: list[str], checkbox: bool = False) -> list[str]:
    if not values:
        return []
    prefix = "- [ ] " if checkbox else "- "
    return [f"\n#### {title}", *[f"{prefix}{value}" for value in values]]


@dataclass
class Event:
    deepwiki_root: Path
    platform: str
    summary: str
    event_type: str = "Checkpoint"
    session_slug: str = ""
    objective: list[str] | None = None
    plan: list[str] | None = None
    status: list[str] | None = None
    files: list[str] | None = None
    commands: list[str] | None = None
    decisions: list[str] | None = None
    surprises: list[str] | None = None
    unresolved: list[str] | None = None
    warnings: list[str] | None = None

    @property
    def path(self) -> Path:
        day = date.today().isoformat()
        platform_slug = normalize_platform(self.platform)
        session = slugify(self.session_slug or self.summary)
        return self.deepwiki_root / "memory" / "episodic" / f"{day}_{platform_slug}_{session}.md"


def ensure_episodic_header(event: Event) -> None:
    path = event.path
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    title = event.summary
    path.write_text(
        f"# Episodic Log - {today} | {event.platform} | {title}\n\n"
        "## Timeline\n",
        encoding="utf-8",
    )


def append_event(event: Event) -> Path:
    ensure_episodic_header(event)
    now = datetime.now().strftime("%H:%M:%S")
    lines = [
        "",
        f"### {now} - {event.event_type}: {event.summary}",
        *section("Objective", event.objective or []),
        *section("Plan", event.plan or []),
        *section("Status", event.status or []),
        *section("Files Touched", event.files or []),
        *section("Commands / Verification", event.commands or []),
        *section("Decisions / Rationale", event.decisions or []),
        *section("Surprises / Failures", event.surprises or []),
        *section("Unresolved / Next", event.unresolved or [], checkbox=True),
        *section("Warnings", event.warnings or []),
        "",
    ]
    with event.path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return event.path


def changelog_entry(
    platform: str,
    description: str,
    changes: list[str],
    decisions: list[str],
    schema_changes: list[str],
    unfinished: list[str],
    warnings: list[str],
) -> str:
    today = date.today().isoformat()
    lines = [
        f"\n## {today} | {platform} | {description}\n",
        "### Changes",
        *(bullet_lines(changes) or ["- None"]),
        "\n### Decisions",
        *(bullet_lines(decisions) or ["- None"]),
        "\n### Schema Changes",
        *(bullet_lines(schema_changes) or ["- None"]),
        "\n### Unfinished",
        *([f"- [ ] {item}" for item in unfinished if item] or ["- [ ] None"]),
        "\n### Warnings for Next Session",
        *(bullet_lines(warnings) or ["- None"]),
        "\n---\n",
    ]
    return "\n".join(lines)


def insert_changelog(deepwiki_root: Path, entry: str) -> Path:
    path = deepwiki_root / "memory" / "changelog.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Changelog\n\n> Append-only, newest first.\n"
    lines = existing.split("\n")
    insert_idx = next((i for i, line in enumerate(lines) if line.startswith("## ")), len(lines))
    lines.insert(insert_idx, entry)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--deepwiki-root", type=Path, default=Path(".deepwiki"))
    parser.add_argument("--platform", default="Codex")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--session-slug", default="")
    parser.add_argument("--objective", action="append", default=[])
    parser.add_argument("--plan", action="append", default=[])
    parser.add_argument("--status", action="append", default=[])
    parser.add_argument("--file", dest="files", action="append", default=[])
    parser.add_argument("--command", dest="commands", action="append", default=[])
    parser.add_argument("--decision", dest="decisions", action="append", default=[])
    parser.add_argument("--surprise", dest="surprises", action="append", default=[])
    parser.add_argument("--unresolved", action="append", default=[])
    parser.add_argument("--warning", dest="warnings", action="append", default=[])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    event_parser = subparsers.add_parser("event", help="Append an in-flight episodic event")
    add_common_arguments(event_parser)
    event_parser.add_argument("--event-type", default="Checkpoint")

    close_parser = subparsers.add_parser("close", help="Append final episodic event and changelog entry")
    add_common_arguments(close_parser)
    close_parser.add_argument("--change", dest="changes", action="append", default=[])
    close_parser.add_argument("--schema-change", dest="schema_changes", action="append", default=[])
    return parser


def event_from_args(args: argparse.Namespace, event_type: str) -> Event:
    return Event(
        deepwiki_root=args.deepwiki_root,
        platform=args.platform,
        summary=args.summary,
        event_type=event_type,
        session_slug=args.session_slug,
        objective=args.objective,
        plan=args.plan,
        status=args.status,
        files=args.files,
        commands=args.commands,
        decisions=args.decisions,
        surprises=args.surprises,
        unresolved=args.unresolved,
        warnings=args.warnings,
    )


def main() -> int:
    args = build_parser().parse_args()
    event_type = args.event_type if args.command == "event" else "Close"
    episodic_path = append_event(event_from_args(args, event_type))
    print(f"episodic={episodic_path}")

    if args.command == "close":
        entry = changelog_entry(
            platform=args.platform,
            description=args.summary,
            changes=args.changes or args.status,
            decisions=args.decisions,
            schema_changes=args.schema_changes,
            unfinished=args.unresolved,
            warnings=args.warnings,
        )
        changelog_path = insert_changelog(args.deepwiki_root, entry)
        print(f"changelog={changelog_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
