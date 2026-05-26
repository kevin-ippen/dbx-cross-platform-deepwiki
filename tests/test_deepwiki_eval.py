from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "deepwiki_eval.py"
SPEC = importlib.util.spec_from_file_location("deepwiki_eval", SCRIPT_PATH)
deepwiki_eval = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["deepwiki_eval"] = deepwiki_eval
SPEC.loader.exec_module(deepwiki_eval)

RESOLVE_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "deepwiki_resolve_project.py"
RESOLVE_SPEC = importlib.util.spec_from_file_location("deepwiki_resolve_project", RESOLVE_SCRIPT_PATH)
deepwiki_resolve_project = importlib.util.module_from_spec(RESOLVE_SPEC)
assert RESOLVE_SPEC and RESOLVE_SPEC.loader
sys.modules["deepwiki_resolve_project"] = deepwiki_resolve_project
RESOLVE_SPEC.loader.exec_module(deepwiki_resolve_project)

ALL_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "deepwiki_eval_all.py"
ALL_SPEC = importlib.util.spec_from_file_location("deepwiki_eval_all", ALL_SCRIPT_PATH)
deepwiki_eval_all = importlib.util.module_from_spec(ALL_SPEC)
assert ALL_SPEC and ALL_SPEC.loader
sys.modules["deepwiki_eval_all"] = deepwiki_eval_all
ALL_SPEC.loader.exec_module(deepwiki_eval_all)

LOG_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "deepwiki_log_event.py"
LOG_SPEC = importlib.util.spec_from_file_location("deepwiki_log_event", LOG_SCRIPT_PATH)
deepwiki_log_event = importlib.util.module_from_spec(LOG_SPEC)
assert LOG_SPEC and LOG_SPEC.loader
sys.modules["deepwiki_log_event"] = deepwiki_log_event
LOG_SPEC.loader.exec_module(deepwiki_log_event)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_changelog_parser_counts_entries() -> None:
    text = """# Changelog

## 2026-05-26 | Codex | Phase - Work

### Changes
- A

## 2026-05-25 | Claude Code | Phase - Prior Work

### Changes
- B
"""
    entries = deepwiki_eval.changelog_entries(text)
    assert len(entries) == 2
    assert entries[0].startswith("## 2026-05-26")


def test_probe_scores_missing_gotchas(tmp_path: Path) -> None:
    root = tmp_path / ".deepwiki"
    write(root / "memory" / "changelog.md", "## 2026-05-26\n\n### Warnings for Next Session\n- Avoid stale data\n")
    probes = [
        {
            "id": "known_gotchas",
            "expected_paths": ["memory/semantic/gotchas.md"],
            "keywords": ["avoid"],
        }
    ]
    result = deepwiki_eval.run_probes(root, probes)[0]
    assert result.score < 70
    assert result.missing_paths == ["memory/semantic/gotchas.md"]


def test_probe_scores_expected_paths_proportionally(tmp_path: Path) -> None:
    root = tmp_path / ".deepwiki"
    write(root / "NORTH_STAR.md", "# North Star\n\nsuccess Databricks\n")
    probes = [
        {
            "id": "partial_paths",
            "expected_paths": ["NORTH_STAR.md", "memory/semantic/gotchas.md"],
            "keywords": ["success", "Databricks"],
        }
    ]
    result = deepwiki_eval.run_probes(root, probes)[0]
    assert result.score == 70.0
    assert result.found_paths == ["NORTH_STAR.md"]
    assert result.missing_paths == ["memory/semantic/gotchas.md"]


def test_episodic_quality_requires_flight_recorder_events(tmp_path: Path) -> None:
    episodic_dir = tmp_path / ".deepwiki" / "memory" / "episodic"
    write(
        episodic_dir / "2026-05-26_codex_session.md",
        """# Episodic Log - 2026-05-26 | Codex | Session

## Timeline

### 09:00:00 - Plan: Start

#### Plan
- Inspect context
- Read the protocol, review the latest changelog, identify the current failure, and define the smallest verification command before editing.

### 09:10:00 - Checkpoint: Patched

#### Status
- Applied fix
- Updated the evaluator and the CLI helper, then reran the narrow regression tests to confirm the behavior changed for the intended reason.

### 09:20:00 - Close: Finished

#### Commands / Verification
- pytest: passed
- The scorecard can now recover plan, status, verification, and close state from this episodic log.
""",
    )
    quality = deepwiki_eval.inspect_episodic_quality(episodic_dir)
    assert quality["score"] == 100.0
    assert quality["has_plan"] is True
    assert quality["has_checkpoint"] is True
    assert quality["has_close"] is True


def test_findings_surface_low_handoff_and_skipped_uc_mirror() -> None:
    inventory = {
        "required_files": {path: True for path in deepwiki_eval.REQUIRED_PROJECT_FILES},
        "optional_files": {},
        "episodic_logs": ["2026-05-26_codex_demo.md"],
        "episodic_quality": {
            "has_plan": True,
            "has_checkpoint": True,
            "has_close": True,
            "structured_section_count": 3,
            "score": 100.0,
        },
    }
    changelog = {"latest_missing_sections": [], "entry_count": 1}
    sessions = {
        "claude": {
            "project_rows": 0,
            "project_rows_with_checkpoint_field": 0,
            "project_rows_with_checkpoint_true": 0,
        },
        "codex": {"project_rows": 0},
    }
    scores = {
        "retrieval_utility": 90.0,
        "protocol_compliance": 95.0,
        "handoff_quality": 55.0,
        "drift_freshness": 80.0,
        "efficiency": 90.0,
    }
    findings, recommendations = deepwiki_eval.build_findings(
        inventory,
        changelog,
        sessions,
        probes=[],
        scores=scores,
        uc_mirror=None,
    )
    assert any("Handoff Quality score is below target" in finding for finding in findings)
    assert any("UC mirror freshness was not evaluated" in finding for finding in findings)
    assert any("--uc-mirror" in rec for rec in recommendations)


def test_evaluate_generates_weighted_score(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "demo"
    root = project / ".deepwiki"
    write(root / "NORTH_STAR.md", "# North Star - demo\n\nSuccess criteria for a Databricks agent app.\n")
    write(root / "planning" / "goals.md", "# Active Goals\n\nCurrent phase goal.\n")
    write(root / "planning" / "phases.md", "# Phases\n\nPhase 1 completed.\n")
    write(
        root / "memory" / "changelog.md",
        """# Changelog

## 2026-05-26 | Codex | Phase - Work

### Changes
- Changed files

### Decisions
- Kept it small

### Schema Changes
- None

### Unfinished
- [ ] Forward-test

### Warnings for Next Session
- Avoid drift
""",
    )
    write(root / "memory" / "semantic" / "schemas.md", "# Schemas\n\nTable schema details.\n")
    write(
        root / "memory" / "episodic" / "2026-05-26_codex_demo.md",
        """# Episodic Log - 2026-05-26 | Codex | Demo

## Timeline

### 09:00:00 - Plan: Start

#### Objective
- Validate scorecard behavior

### 09:15:00 - Checkpoint: Scored

#### Status
- Evaluation ran

### 09:30:00 - Close: Done

#### Commands / Verification
- pytest: passed
""",
    )
    config = tmp_path / "questions.json"
    config.write_text(
        json.dumps(
            {
                "questions": [
                    {
                        "id": "north_star",
                        "expected_paths": ["NORTH_STAR.md"],
                        "keywords": ["success", "Databricks"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    args = deepwiki_eval.build_parser().parse_args(
        [
            "--deepwiki-root",
            str(root),
            "--project-root",
            str(project),
            "--project",
            "demo",
            "--questions",
            str(config),
        ]
    )
    result = deepwiki_eval.evaluate(args)
    assert result.overall_score > 60
    assert result.scores["retrieval_utility"] > 80


def test_discover_project_deepwikis_skips_hidden(tmp_path: Path) -> None:
    (tmp_path / "alpha" / ".deepwiki").mkdir(parents=True)
    (tmp_path / ".codex_snapshots" / "alpha" / ".deepwiki").mkdir(parents=True)
    projects = deepwiki_eval_all.discover_project_deepwikis(tmp_path)
    assert [(name, root.name) for name, root, _ in projects] == [("alpha", "alpha")]


def test_fuzzy_project_resolver_matches_name_variants(tmp_path: Path) -> None:
    (tmp_path / "wings-demand-forecasting-prep-intelligence" / ".deepwiki").mkdir(parents=True)
    projects = deepwiki_resolve_project.discover_projects(tmp_path)
    result = deepwiki_resolve_project.resolve_project("wings demand prep", projects, min_score=0.4)
    assert result["matches"]
    assert result["matches"][0]["name"] == "wings-demand-forecasting-prep-intelligence"


def test_deepwiki_log_event_writes_episodic_checkpoint(tmp_path: Path) -> None:
    root = tmp_path / ".deepwiki"
    event = deepwiki_log_event.Event(
        deepwiki_root=root,
        platform="Codex",
        summary="Test checkpoint",
        event_type="Plan",
        plan=["Inspect memory"],
        status=["Ready to patch"],
        session_slug="unit-test",
    )
    path = deepwiki_log_event.append_event(event)
    text = path.read_text(encoding="utf-8")
    assert path.name.endswith("_codex_unit-test.md")
    assert "### " in text
    assert "Plan: Test checkpoint" in text
    assert "- Inspect memory" in text
    assert "- Ready to patch" in text


def test_deepwiki_log_event_close_writes_changelog(tmp_path: Path) -> None:
    root = tmp_path / ".deepwiki"
    event = deepwiki_log_event.Event(
        deepwiki_root=root,
        platform="Codex",
        summary="Close session",
        event_type="Close",
        status=["Implemented flight recorder"],
        unresolved=["Redeploy MCP app"],
        session_slug="unit-close",
    )
    episodic_path = deepwiki_log_event.append_event(event)
    entry = deepwiki_log_event.changelog_entry(
        platform="Codex",
        description="Phase - Close session",
        changes=["Implemented flight recorder"],
        decisions=["Use episodic files as recovery source"],
        schema_changes=[],
        unfinished=["Redeploy MCP app"],
        warnings=["MCP changes require app restart"],
    )
    changelog_path = deepwiki_log_event.insert_changelog(root, entry)
    assert "Close: Close session" in episodic_path.read_text(encoding="utf-8")
    changelog = changelog_path.read_text(encoding="utf-8")
    assert "## " in changelog
    assert "### Unfinished" in changelog
    assert "- [ ] Redeploy MCP app" in changelog


def test_deepwiki_log_event_close_without_unfinished_is_not_checkbox_none(tmp_path: Path) -> None:
    root = tmp_path / ".deepwiki"
    entry = deepwiki_log_event.changelog_entry(
        platform="Codex",
        description="Phase - Close session",
        changes=["Implemented flight recorder"],
        decisions=[],
        schema_changes=[],
        unfinished=[],
        warnings=[],
    )
    assert "- None" in entry
    assert "- [ ] None" not in entry
