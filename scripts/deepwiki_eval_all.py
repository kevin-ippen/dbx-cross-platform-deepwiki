#!/usr/bin/env python3
"""Run the DeepWiki evaluator across local projects."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

import deepwiki_eval
import deepwiki_resolve_project


DEFAULT_EXCLUDE_NAMES = {
    ".codex_snapshots",
    ".deepwiki",
    ".git",
    ".venv",
    ".venv312",
    "__pycache__",
}


def discover_project_deepwikis(base_dir: Path, include_hidden: bool = False) -> list[tuple[str, Path, Path]]:
    projects: list[tuple[str, Path, Path]] = []
    for child in sorted(base_dir.iterdir()):
        if not child.is_dir():
            continue
        if not include_hidden and child.name.startswith("."):
            continue
        if child.name in DEFAULT_EXCLUDE_NAMES:
            continue
        deepwiki_root = child / ".deepwiki"
        if deepwiki_root.is_dir():
            projects.append((child.name, child, deepwiki_root))
    return projects


def evaluate_project(
    project_name: str,
    project_root: Path,
    deepwiki_root: Path,
    questions: Path,
) -> dict:
    parser = deepwiki_eval.build_parser()
    args = parser.parse_args(
        [
            "--deepwiki-root",
            str(deepwiki_root),
            "--project-root",
            str(project_root),
            "--project",
            project_name,
            "--questions",
            str(questions),
        ]
    )
    result = deepwiki_eval.evaluate(args)
    data = deepwiki_eval.result_to_dict(result)
    data["project_root"] = str(project_root)
    return data


def risk_label(score: float) -> str:
    if score >= 85:
        return "healthy"
    if score >= 70:
        return "watch"
    if score >= 55:
        return "fragile"
    return "needs attention"


def summarize(results: list[dict]) -> dict:
    dimensions = list(deepwiki_eval.SCORE_WEIGHTS)
    averages = {
        dim: round(mean(row["scores"][dim] for row in results), 1)
        for dim in dimensions
    } if results else {}
    return {
        "project_count": len(results),
        "overall_average": round(mean(row["overall_score"] for row in results), 1) if results else 0,
        "dimension_averages": averages,
        "healthy_count": sum(1 for row in results if row["overall_score"] >= 85),
        "watch_count": sum(1 for row in results if 70 <= row["overall_score"] < 85),
        "fragile_count": sum(1 for row in results if 55 <= row["overall_score"] < 70),
        "needs_attention_count": sum(1 for row in results if row["overall_score"] < 55),
    }


def find_potential_duplicates(results: list[dict], threshold: float = 0.86) -> list[dict]:
    duplicates: list[dict] = []
    for i, left in enumerate(results):
        for right in results[i + 1:]:
            score = deepwiki_resolve_project.similarity(left["project"], right["project"])
            if score >= threshold:
                duplicates.append(
                    {
                        "left": left["project"],
                        "right": right["project"],
                        "score": score,
                    }
                )
    return sorted(duplicates, key=lambda row: (-row["score"], row["left"], row["right"]))


def render_markdown(results: list[dict], base_dir: Path) -> str:
    ordered = sorted(results, key=lambda row: row["overall_score"])
    summary = summarize(results)
    lines = [
        "# DeepWiki Cross-Project Scorecard",
        "",
        f"Base directory: `{base_dir}`",
        f"Projects evaluated: **{summary['project_count']}**",
        f"Average score: **{summary['overall_average']}/100**",
        "",
        "## Portfolio Health",
        "",
        f"- Healthy: {summary['healthy_count']}",
        f"- Watch: {summary['watch_count']}",
        f"- Fragile: {summary['fragile_count']}",
        f"- Needs attention: {summary['needs_attention_count']}",
        "",
        "## Dimension Averages",
        "",
        "| Dimension | Average |",
        "|---|---:|",
    ]
    for dim, score in summary["dimension_averages"].items():
        lines.append(f"| {dim.replace('_', ' ').title()} | {score:.1f} |")

    duplicates = find_potential_duplicates(results)
    lines += ["", "## Potential Duplicate Names", ""]
    if duplicates:
        lines += ["| Project A | Project B | Similarity |", "|---|---|---:|"]
        for dup in duplicates[:20]:
            lines.append(f"| `{dup['left']}` | `{dup['right']}` | {dup['score']:.2f} |")
    else:
        lines.append("- No likely duplicates detected at the current threshold.")

    lines += [
        "",
        "## Project Ranking",
        "",
        "| Project | Score | Risk | Retrieval | Protocol | Handoff | Drift | Efficiency | Top Finding |",
        "|---|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in ordered:
        scores = row["scores"]
        finding = row["findings"][0] if row["findings"] else "-"
        lines.append(
            f"| `{row['project']}` | {row['overall_score']:.1f} | {risk_label(row['overall_score'])} "
            f"| {scores['retrieval_utility']:.1f} | {scores['protocol_compliance']:.1f} "
            f"| {scores['handoff_quality']:.1f} | {scores['drift_freshness']:.1f} "
            f"| {scores['efficiency']:.1f} | {finding} |"
        )

    lines += ["", "## Common Gaps", ""]
    common = {}
    for row in results:
        for finding in row["findings"]:
            common[finding] = common.get(finding, 0) + 1
    for finding, count in sorted(common.items(), key=lambda item: (-item[1], item[0]))[:12]:
        lines.append(f"- {count} projects: {finding}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run DeepWiki scorecards across project directories.")
    parser.add_argument(
        "--base-dir",
        default="/Users/kevin.ippen/Documents/local_development",
        help="Directory containing project folders.",
    )
    parser.add_argument(
        "--questions",
        default="configs/deepwiki_eval_questions.json",
        help="Probe config path.",
    )
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden directories.")
    parser.add_argument(
        "--exclude-project",
        action="append",
        default=[],
        help="Project directory name to exclude. May be provided multiple times.",
    )
    parser.add_argument("--markdown-out", default="", help="Markdown report path.")
    parser.add_argument("--json-out", default="", help="JSON report path.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base_dir = Path(args.base_dir).expanduser().resolve()
    questions = Path(args.questions).expanduser().resolve()
    projects = discover_project_deepwikis(base_dir, include_hidden=args.include_hidden)
    excluded = set(args.exclude_project or [])
    projects = [project for project in projects if project[0] not in excluded]
    results = [
        evaluate_project(project_name, project_root, deepwiki_root, questions)
        for project_name, project_root, deepwiki_root in projects
    ]
    payload = {
        "base_dir": str(base_dir),
        "summary": summarize(results),
        "potential_duplicates": find_potential_duplicates(results),
        "results": sorted(results, key=lambda row: row["overall_score"]),
    }
    markdown = render_markdown(results, base_dir)

    if args.markdown_out:
        path = Path(args.markdown_out).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
    if args.json_out:
        path = Path(args.json_out).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
