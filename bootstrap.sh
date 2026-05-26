#!/usr/bin/env bash
# bootstrap.sh — Scaffold a .deepwiki workspace from the template
#
# Usage:
#   ./bootstrap.sh --workspace my-workspace --project my-first-project
#   ./bootstrap.sh --workspace my-workspace --project proj-a --project proj-b
#
# What it does:
#   1. Creates workspace/ from the template (if it doesn't exist)
#   2. Creates projects/{project-name}/ from projects/_template/ for each --project
#   3. Prints next steps

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR/projects/_template"

WORKSPACE_NAME=""
declare -a PROJECT_NAMES=()
OUTPUT_DIR="."   # default: current directory

usage() {
  echo "Usage: $0 --workspace <name> --project <name> [--project <name> ...] [--output <dir>]"
  echo ""
  echo "  --workspace   Name of your workspace (used for documentation only)"
  echo "  --project     Name of a project to scaffold (can be repeated)"
  echo "  --output      Directory to write .deepwiki into (default: current dir)"
  exit 1
}

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --workspace) WORKSPACE_NAME="$2"; shift 2 ;;
    --project)   PROJECT_NAMES+=("$2"); shift 2 ;;
    --output)    OUTPUT_DIR="$2"; shift 2 ;;
    -h|--help)   usage ;;
    *) echo "Unknown argument: $1"; usage ;;
  esac
done

if [[ -z "$WORKSPACE_NAME" || ${#PROJECT_NAMES[@]} -eq 0 ]]; then
  echo "Error: --workspace and at least one --project are required."
  usage
fi

DEEPWIKI_DIR="$OUTPUT_DIR/.deepwiki"

echo "Scaffolding DeepWiki at: $DEEPWIKI_DIR"
echo ""

# ---------------------------------------------------------------------------
# 1. Copy workspace/ template
# ---------------------------------------------------------------------------
if [[ -d "$DEEPWIKI_DIR/workspace" ]]; then
  echo "  workspace/ already exists — skipping (no overwrite)"
else
  echo "  Creating workspace/..."
  cp -r "$SCRIPT_DIR/workspace" "$DEEPWIKI_DIR/workspace"
  echo "  Done."
fi

# ---------------------------------------------------------------------------
# 2. Copy agents/ template
# ---------------------------------------------------------------------------
if [[ -d "$DEEPWIKI_DIR/agents" ]]; then
  echo "  agents/ already exists — skipping"
else
  echo "  Creating agents/..."
  cp -r "$SCRIPT_DIR/agents" "$DEEPWIKI_DIR/agents"
  echo "  Done."
fi

# ---------------------------------------------------------------------------
# 3. Create project scaffolds
# ---------------------------------------------------------------------------
mkdir -p "$DEEPWIKI_DIR/projects"

for project in "${PROJECT_NAMES[@]}"; do
  dest="$DEEPWIKI_DIR/projects/$project"
  if [[ -d "$dest" ]]; then
    echo "  projects/$project/ already exists — skipping"
  else
    echo "  Creating projects/$project/..."
    cp -r "$TEMPLATE_DIR" "$dest"
    echo "  Done."
  fi
done

# ---------------------------------------------------------------------------
# 4. Print next steps
# ---------------------------------------------------------------------------
echo ""
echo "DeepWiki scaffolded successfully."
echo ""
echo "Next steps:"
echo ""
echo "  1. Set your workspace infrastructure details:"
echo "     $DEEPWIKI_DIR/workspace/context/stack.md"
echo ""
echo "  2. Describe your projects:"
echo "     $DEEPWIKI_DIR/workspace/PROJECT_INDEX.md"
echo ""
for project in "${PROJECT_NAMES[@]}"; do
  echo "  3. Write the north star for '$project':"
  echo "     $DEEPWIKI_DIR/projects/$project/NORTH_STAR.md"
  echo ""
  echo "  4. List current goals for '$project':"
  echo "     $DEEPWIKI_DIR/projects/$project/planning/goals.md"
  echo ""
done
echo "  5. Wire up your agent platform (see SETUP.md for Claude Code, Genie, Copilot, Cursor)"
echo ""
echo "  Optional: deploy the MCP server for Genie Code integration:"
echo "    cd mcp-server/ && databricks apps deploy mcp-deepwiki --source-code-path ."
