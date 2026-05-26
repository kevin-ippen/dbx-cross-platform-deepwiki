# dbx-cross-platform-deepwiki

A persistent, file-based memory system that lets **any agent** (Claude Code, Genie Code, GitHub Copilot, Cursor, or a custom agent) pick up exactly where the last session left off — even on a different platform.

## The problem it solves

Multi-agent, multi-platform projects fail because agents start cold. They re-ask the same clarifying questions, re-discover the same schema quirks, and make the same avoidable mistakes. When you work across Databricks Genie Code, Claude Code, and GitHub Copilot in the same week, you have no shared memory layer.

DeepWiki is that layer. It's a folder of structured Markdown files that any agent can read, and a lightweight protocol that tells agents what to read, when to write, and how to hand off between sessions and platforms.

The portable contract lives in [CORE_PROTOCOL.md](CORE_PROTOCOL.md). It is deliberately model-agnostic and harness-agnostic: a model can comply through direct file reads/writes, CLI scripts, MCP tools, IDE hooks, or any future agent runtime.

## How it works

```
.deepwiki/
  workspace/            ← facts shared across all projects
    AGENT_PROTOCOL.md   ← the rulebook every agent reads first
    PROJECT_INDEX.md    ← what exists and where
    memory/semantic/    ← compiled knowledge: gotchas, patterns, glossary
    context/            ← infrastructure: catalogs, integrations, stacks
  projects/             ← per-project memory
    my-project/
      NORTH_STAR.md     ← the why (human-authored)
      planning/         ← goals, phases, decisions, open questions
      memory/
        episodic/       ← raw session logs (source material)
        changelog.md    ← structured session summary (pre-flight read)
        semantic/       ← compiled facts: schemas, gotchas, patterns
      context/          ← codebase map, DAB manifest
  agents/               ← reusable subagent prompt templates
  mcp-server/           ← optional MCP SDK server for Genie Code
```

**Session start ritual** (any platform):
1. Resolve the project name against existing project folders before creating or writing memory
2. Read `workspace/AGENT_PROTOCOL.md` — it tells you exactly what else to read
3. Load the project slice relevant to your task, including bounded recent episodic tails
4. State your phase/goal, plan, regression risk, and scope before acting

**Session end ritual** (any platform):
1. Append to `memory/episodic/YYYY-MM-DD_{platform}_{slug}.md` throughout the session — plans, status updates, checkpoints, errors, decisions, close
2. Append to `projects/{name}/memory/changelog.md` — structured summary
3. If switching platforms, write `agents/session_handoff.md`

**Write-safety rule:** fuzzy names are for discovery. Writes must target an exact canonical `projects/{name}/` directory, so `lake find` can resolve to `lakefind`, but the write is retried as `lakefind`.

## Platform integration

| Platform | How to load DeepWiki |
|----------|----------------------|
| **Claude Code** | Add `Read .deepwiki/workspace/AGENT_PROTOCOL.md` to `CLAUDE.md` |
| **Genie Code / DBSQL Assistant** | Deploy the MCP server (see `mcp-server/`) and register it as a custom MCP |
| **GitHub Copilot** | Add `#file:.deepwiki/workspace/AGENT_PROTOCOL.md` to `.github/copilot-instructions.md` |
| **Cursor** | Reference `AGENT_PROTOCOL.md` in `.cursorrules` |
| **Custom agents** | Include `AGENT_PROTOCOL.md` in the system prompt; inject project slices as context |

For a model/harness-neutral prompt, use [agents/core_agent_instructions.md](agents/core_agent_instructions.md).

### UC Volume sync (Databricks)

If you use Genie Code on multiple machines, store DeepWiki on a UC Volume so all agents share the same source of truth:

```
/Volumes/{catalog}/{schema}/{volume}/
  workspace/
  projects/
```

The MCP server reads from the volume — no sync scripts needed.

## Memory tiers

| Tier | File(s) | Who writes | When |
|------|---------|------------|------|
| **Vision** | `NORTH_STAR.md` | Human only | When the goal changes |
| **Priorities** | `planning/goals.md`, `planning/phases.md` | Human only | When priorities shift |
| **Architecture** | `planning/decisions.md` | Agent (human-approved) | When architectural choices are made |
| **Episodic** | `memory/episodic/{date}_{platform}_{slug}.md` | Agent (mandatory) | Plans, status changes, checkpoints, errors, decisions, close |
| **Structured log** | `memory/changelog.md` | Agent (mandatory) | Every session — formatted summary for pre-flight reads |
| **Compiled facts** | `memory/semantic/*.md` | Agent (compilation task) | Every 3-5 sessions or at phase boundaries |

The key insight: episodic logs act as a flight recorder for interrupted work; compilation distills them into dense semantic memory. Agents read recent episodic logs for recovery and compiled semantic memory for durable facts.

## Getting started

```bash
# 1. Clone this repo into your project
git clone https://github.com/kevin-ippen/dbx-cross-platform-deepwiki .deepwiki-template

# 2. Run the bootstrap script to scaffold your workspace
chmod +x .deepwiki-template/bootstrap.sh
.deepwiki-template/bootstrap.sh --workspace my-workspace --project my-first-project

# 3. Fill in the placeholders
#    - workspace/PROJECT_INDEX.md → your projects
#    - workspace/context/stack.md → your workspaces/warehouses
#    - projects/my-first-project/NORTH_STAR.md → your goal
```

See [SETUP.md](SETUP.md) for the platform wiring walkthrough.
See [BOOTSTRAP.md](BOOTSTRAP.md) for the 7-prompt sequence to populate your first project.

## MCP server (for Genie Code)

The `mcp-server/` directory contains an MCP Python SDK server that exposes DeepWiki as tools. Deploy it as a Databricks App and register it with Genie Code — then Genie can call `deepwiki_preflight("my-project")` to load all session context in a single tool call.

See [mcp-server/README.md](mcp-server/README.md).

## Memory Evaluation

The `scripts/` directory includes deterministic scorecard tools for checking whether a DeepWiki tree is useful for cold-resume work.

```bash
python3 scripts/deepwiki_eval.py \
  --deepwiki-root projects/my-project \
  --project-root /path/to/my-project \
  --project my-project

python3 scripts/deepwiki_eval_all.py \
  --base-dir /path/to/projects \
  --markdown-out docs/deepwiki-cross-project-scorecard.md \
  --json-out docs/deepwiki-cross-project-scorecard.json
```

The evaluator scores retrieval utility, protocol compliance, handoff quality, drift freshness, and efficiency. Pass `--uc-mirror` when you have a mounted UC Volume mirror; otherwise the scorecard reports local freshness only and explicitly flags that remote sync was not evaluated.

Scorecards are intentionally conservative: partial missing expected files are penalized, recent episodic logs must contain Plan/Checkpoint/Close events, handoff scores below target are surfaced as findings, and skipped UC mirror checks are not treated as proof of sync.

## Philosophy

- **Markdown only.** No databases, no vector stores, no external services required.
- **Platform-agnostic.** The protocol is a text file. Any agent that can read files can follow it.
- **Human-owned, agent-maintained.** Vision and priorities are human-written. Logs and compiled facts are agent-written.
- **Promotion over duplication.** Facts that apply to one project live in that project. Facts that apply everywhere get promoted to workspace level.
