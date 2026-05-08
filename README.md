# dbx-cross-platform-deepwiki

A persistent, file-based memory system that lets **any agent** (Claude Code, Genie Code, GitHub Copilot, OpenAI Codex, or a custom agent) pick up exactly where the last session left off — even on a different platform.

## The problem it solves

Multi-agent, multi-platform projects fail because agents start cold. They re-ask the same clarifying questions, re-discover the same schema quirks, and make the same avoidable mistakes. When you work across Databricks Genie Code, Claude Code, and GitHub Copilot in the same week, you have no shared memory layer.

DeepWiki is that layer. It's a folder of structured Markdown files that any agent can read, and a lightweight protocol that tells agents what to read, when to write, and how to hand off between sessions and platforms.

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
        changelog.md    ← append-only session log
        semantic/       ← schemas, gotchas, patterns (compiled from changelog)
  agents/               ← reusable subagent prompt templates
  mcp-server/           ← optional FastAPI MCP server for Genie Code / DBSQL Assistant
```

**Session start ritual** (any platform):
1. Read `workspace/AGENT_PROTOCOL.md` — it tells you exactly what else to read
2. Load the project slice relevant to your task
3. State your plan before acting

**Session end ritual** (any platform):
1. Append to `projects/{name}/memory/changelog.md`
2. If switching platforms, write `agents/session_handoff.md`

## Platform integration

| Platform | How to load DeepWiki |
|----------|----------------------|
| **Claude Code** | Add `Read .deepwiki/workspace/AGENT_PROTOCOL.md` to CLAUDE.md or project prompt |
| **Genie Code / DBSQL Assistant** | Deploy the MCP server (see `mcp-server/`) and register it |
| **GitHub Copilot** | Add `#file:.deepwiki/workspace/AGENT_PROTOCOL.md` to your Copilot instructions |
| **OpenAI Codex / custom agents** | Include AGENT_PROTOCOL.md in the system prompt; pass project slices as context |
| **Cursor** | Reference in `.cursorrules` |

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
| **Raw log** | `memory/changelog.md` | Agent (mandatory) | Every session that changes anything |
| **Compiled facts** | `memory/semantic/*.md` | Agent (compilation task) | Every 3-5 sessions or at phase boundaries |
| **Architecture** | `planning/decisions.md` | Agent (with human approval) | When architectural choices are made |

The key insight: agents write raw logs (cheap, low judgment), and a separate compilation pass distills those logs into clean semantic memory. This keeps the live-session write cost low while keeping the read quality high.

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

The `mcp-server/` directory contains a FastAPI server that exposes DeepWiki as MCP tools. Deploy it as a Databricks App and register it with Genie Code — then Genie can call `deepwiki_preflight("my-project")` to load all session context in a single tool call.

See [mcp-server/README.md](mcp-server/README.md).

## Philosophy

- **Markdown only.** No databases, no vector stores, no external services required.
- **Platform-agnostic.** The protocol is a text file. Any agent that can read files can follow it.
- **Human-owned, agent-maintained.** Vision and priorities are human-written. Logs and compiled facts are agent-written.
- **Promotion over duplication.** Facts that apply to one project live in that project. Facts that apply everywhere get promoted to workspace level.
