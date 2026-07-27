#!/bin/bash
# =============================================================================
# install_hooks.sh
#
# One-time setup script that installs the AI test-case-gen pre-push hook
# into a target git repository's .git/hooks/ directory.
#
# Usage:
#   # Install into THIS repo (Ai_Test_Case_Gen):
#   ./scripts/install_hooks.sh
#
#   # Install into ANOTHER repo (e.g. your source project):
#   ./scripts/install_hooks.sh /path/to/your/other/repo
#
# The hook will run `scripts/gen_on_push.py` (relative to Ai_Test_Case_Gen root)
# every time you do `git push` in the target repo.
# To bypass for a specific push: git push --no-verify
# =============================================================================

set -euo pipefail

# ── Colours
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
RESET='\033[0m'

print_banner() {
    echo ""
    echo -e "${CYAN}=================================================${RESET}"
    echo -e "${CYAN}   🔧  AI Test Case Gen — Hook Installer         ${RESET}"
    echo -e "${CYAN}=================================================${RESET}"
    echo ""
}

# ── Resolve paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AI_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOK_SOURCE="$SCRIPT_DIR/pre-push.hook"
GEN_SCRIPT="$SCRIPT_DIR/gen_on_push.py"

# Target repo: argument or current (Ai_Test_Case_Gen) repo
if [ -n "${1:-}" ]; then
    TARGET_REPO="$(cd "$1" && pwd)"
else
    TARGET_REPO="$AI_PROJECT_ROOT"
fi

print_banner

echo -e "  ${CYAN}AI Project Root :${RESET} $AI_PROJECT_ROOT"
echo -e "  ${CYAN}Target Repo     :${RESET} $TARGET_REPO"
echo ""

# ── Validate source files exist
if [ ! -f "$HOOK_SOURCE" ]; then
    echo -e "  ${RED}[ERROR]${RESET} Hook source not found: $HOOK_SOURCE"
    exit 1
fi
if [ ! -f "$GEN_SCRIPT" ]; then
    echo -e "  ${RED}[ERROR]${RESET} Generator script not found: $GEN_SCRIPT"
    exit 1
fi

# ── Validate target is a git repo
GIT_HOOKS_DIR="$TARGET_REPO/.git/hooks"
if [ ! -d "$GIT_HOOKS_DIR" ]; then
    echo -e "  ${RED}[ERROR]${RESET} '$TARGET_REPO' is not a git repository (no .git/hooks found)."
    exit 1
fi

DEST_HOOK="$GIT_HOOKS_DIR/pre-push"

# ── Warn if an existing hook will be replaced
if [ -f "$DEST_HOOK" ]; then
    echo -e "  ${YELLOW}[WARN]${RESET} An existing pre-push hook was found:"
    echo "         $DEST_HOOK"
    echo ""
    echo -n "  Replace it? [y/N] "
    read -r REPLY
    if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "  ${YELLOW}Aborted.${RESET} Existing hook was not changed."
        echo ""
        exit 0
    fi
    echo ""
fi

# ── If target repo != AI project root, generate a wrapper that points back
if [ "$TARGET_REPO" = "$AI_PROJECT_ROOT" ]; then
    # Simple copy — hook already has correct relative paths
    cp "$HOOK_SOURCE" "$DEST_HOOK"
else
    # Generate a custom hook that hard-codes the path to gen_on_push.py
    # so it works regardless of where the target repo lives.
    cat > "$DEST_HOOK" << HOOK_EOF
#!/bin/bash
# Auto-generated pre-push hook by install_hooks.sh
# Triggers AI test case generation on every git push.
# To bypass: git push --no-verify

AI_PROJECT_ROOT="$AI_PROJECT_ROOT"
SCRIPT="\$AI_PROJECT_ROOT/scripts/gen_on_push.py"
TARGET_REPO="$TARGET_REPO"

if [ ! -f "\$SCRIPT" ]; then
    echo "  [⚠️ ] AI Test Case Gen script not found at \$SCRIPT — skipping."
    exit 0
fi

if [ -f "\$AI_PROJECT_ROOT/venv/bin/python" ]; then
    PYTHON="\$AI_PROJECT_ROOT/venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "  [❌] Python not found — skipping AI test case generation."
    exit 0
fi

"\$PYTHON" "\$SCRIPT" "\$TARGET_REPO"
exit \$?
HOOK_EOF
fi

# ── Make executable
chmod +x "$DEST_HOOK"

echo -e "  ${GREEN}[OK]${RESET}  Hook installed → $DEST_HOOK"
echo ""

# ── Verify .env exists in AI project
if [ ! -f "$AI_PROJECT_ROOT/.env" ]; then
    echo -e "  ${YELLOW}[WARN]${RESET} No .env found in $AI_PROJECT_ROOT"
    echo "         Copy .env.example → .env and fill in your credentials:"
    echo "         cp $AI_PROJECT_ROOT/.env.example $AI_PROJECT_ROOT/.env"
    echo ""
fi

# ── Check Ollama is reachable
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
if curl -s --max-time 2 "$OLLAMA_URL" > /dev/null 2>&1; then
    echo -e "  ${GREEN}[OK]${RESET}  Ollama is reachable at $OLLAMA_URL"
else
    echo -e "  ${YELLOW}[WARN]${RESET} Ollama not reachable at $OLLAMA_URL"
    echo "         Make sure Ollama is running before you push."
    echo "         Start it with: ollama serve"
fi
echo ""

echo -e "${CYAN}=================================================${RESET}"
echo -e "${GREEN}  ✅  Hook installation complete!${RESET}"
echo -e "${CYAN}=================================================${RESET}"
echo ""
echo "  Next steps:"
echo "    1. Ensure Ollama is running:  ollama serve"
echo "    2. Make any code change and commit it."
echo "    3. Run:  git push"
echo "    4. Watch test cases generate automatically!"
echo ""
echo "  To bypass for a single push:  git push --no-verify"
echo ""
