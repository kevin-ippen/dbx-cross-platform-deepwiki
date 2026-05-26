#!/usr/bin/env python3
"""Resolve DeepWiki project names with fuzzy matching.

Use this before creating a new project memory folder or calling preflight with
an uncertain project name. It catches near-duplicates such as `soa_dashboard`,
`soa-pilot`, and `soa pilot`.
"""

from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def token_set(value: str) -> set[str]:
    return {tok for tok in re.split(r"[^a-z0-9]+", value.lower()) if tok}


def project_aliases(name: str) -> set[str]:
    aliases = {name, name.replace("_", "-"), name.replace("-", "_"), name.replace("-", " ")}
    aliases.add(normalize_name(name))
    return {alias for alias in aliases if alias}


def discover_projects(base_dir: Path, include_hidden: bool = False) -> list[dict]:
    projects: list[dict] = []
    for child in sorted(base_dir.iterdir()):
        if not child.is_dir():
            continue
        if not include_hidden and child.name.startswith("."):
            continue
        deepwiki = child / ".deepwiki"
        if deepwiki.is_dir():
            projects.append(
                {
                    "name": child.name,
                    "path": str(child),
                    "deepwiki": str(deepwiki),
                    "aliases": sorted(project_aliases(child.name)),
                }
            )
    return projects


def similarity(query: str, candidate: str) -> float:
    q_norm = normalize_name(query)
    c_norm = normalize_name(candidate)
    seq = SequenceMatcher(None, q_norm, c_norm).ratio() if q_norm and c_norm else 0.0
    q_tokens = token_set(query)
    c_tokens = token_set(candidate)
    if q_tokens or c_tokens:
        token = len(q_tokens & c_tokens) / max(1, len(q_tokens | c_tokens))
        query_coverage = len(q_tokens & c_tokens) / max(1, len(q_tokens))
    else:
        token = 0.0
        query_coverage = 0.0
    contains = 1.0 if q_norm and (q_norm in c_norm or c_norm in q_norm) else 0.0
    return round(max(seq, 0.82 * token + 0.18 * contains, 0.88 * query_coverage + 0.12 * token), 4)


def resolve_project(query: str, projects: list[dict], min_score: float = 0.72) -> dict:
    scored = []
    for project in projects:
        scores = [similarity(query, alias) for alias in project["aliases"]]
        score = max(scores) if scores else 0.0
        if normalize_name(query) == normalize_name(project["name"]):
            score = 1.0
        if score >= min_score:
            scored.append({**project, "score": score})
    scored.sort(key=lambda row: (-row["score"], row["name"]))
    exact = [row for row in scored if row["score"] == 1.0]
    return {
        "query": query,
        "status": "exact" if len(exact) == 1 else "ambiguous" if len(scored) > 1 else "not_found" if not scored else "candidate",
        "matches": scored,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fuzzy-resolve a DeepWiki project name.")
    parser.add_argument("query", help="Project name or alias to resolve.")
    parser.add_argument(
        "--base-dir",
        default="/Users/kevin.ippen/Documents/local_development",
        help="Directory containing project folders.",
    )
    parser.add_argument("--min-score", type=float, default=0.72)
    parser.add_argument("--include-hidden", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    base_dir = Path(args.base_dir).expanduser().resolve()
    result = resolve_project(
        args.query,
        discover_projects(base_dir, include_hidden=args.include_hidden),
        min_score=args.min_score,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"query: {result['query']}")
        print(f"status: {result['status']}")
        for match in result["matches"][:10]:
            print(f"- {match['name']} ({match['score']:.2f}) -> {match['deepwiki']}")
    return 0 if result["matches"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
