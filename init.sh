#!/bin/bash
set -e

echo "=== Chat Retro Environment Setup ==="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Check uv is available
if ! command -v uv &> /dev/null; then
    echo "ERROR: uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install/sync dependencies
echo "Syncing dependencies..."
uv sync

# Check Claude Code CLI is available
if ! command -v claude &> /dev/null; then
    echo "WARNING: Claude Code CLI not found."
    echo "Install with: npm install -g @anthropic-ai/claude-code"
    echo "Then run: claude --version"
fi

# Verify import works
echo "Verifying package import..."
if uv run python -c "import chat_retro" 2>/dev/null; then
    echo "Package import: OK"
else
    echo "Package import: PENDING (expected before Phase 1 complete)"
fi

# Run tests if they exist
if [ -d "tests" ] && [ "$(ls -A tests/*.py 2>/dev/null)" ]; then
    echo "Running tests..."
    uv run pytest tests/ -v --tb=short || echo "Tests: FAILED (may be expected during development)"
else
    echo "Tests: PENDING (no test files yet)"
fi

echo ""
echo "=== Setup Complete ==="
echo "Next: Implement features from feature_list.json"
