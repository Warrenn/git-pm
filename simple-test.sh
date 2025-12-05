#!/bin/bash
# Completely isolated test in /tmp - no parent contamination possible

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="/tmp/git-pm-test-$$"

echo "============================================"
echo "git-pm Isolated Test"
echo "============================================"
echo "Creating test in: $TEST_ROOT"
echo ""

# Create isolated test directory
rm -rf "$TEST_ROOT" 2>/dev/null || true
mkdir -p "$TEST_ROOT/workspace"
cd "$TEST_ROOT/workspace"

echo "1. Creating mock repository..."
mkdir -p mock-repo/packages/mylib
cd mock-repo

git init
git config user.email "test@example.com"
git config user.name "Test User"

cat > packages/mylib/__init__.py << 'EOF'
"""My Library Package"""
from .mylib import greet, add
__all__ = ['greet', 'add']
EOF

cat > packages/mylib/README.md << 'EOF'
# My Library
This is a test library.
EOF

cat > packages/mylib/mylib.py << 'EOF'
def greet(name):
    return f"Hello, {name}!"

def add(a, b):
    return a + b
EOF

git add .
git commit -m "Initial commit"
git tag v1.0.0
cd "$TEST_ROOT/workspace"

echo "   ✓ Mock repository created"
echo ""

echo "2. Creating test project..."
mkdir test-project
cd test-project

cat > git-pm.yaml << EOF
packages:
  mylib:
    repo: file://$TEST_ROOT/workspace/mock-repo
    path: packages/mylib
    ref:
      type: tag
      value: v1.0.0
EOF

echo "   ✓ Manifest created"
echo ""

echo "3. Setting up script..."
mkdir git-pm

if [ -f "$SCRIPT_DIR/git-pm-modified.py" ]; then
    cp "$SCRIPT_DIR/git-pm-modified.py" git-pm/git-pm.py
elif [ -f "$SCRIPT_DIR/git-pm.py" ]; then
    cp "$SCRIPT_DIR/git-pm.py" git-pm/
else
    echo "   ✗ git-pm.py not found"
    exit 1
fi

echo "   ✓ Script ready"
echo ""

echo "4. Script version:"
python git-pm/git-pm.py --version
echo ""

# Git config
git config --global --add safe.directory "$TEST_ROOT/workspace/mock-repo" 2>/dev/null || true
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0="safe.directory"
export GIT_CONFIG_VALUE_0="*"

echo "5. Environment check..."
echo "   Working dir: $(pwd)"
echo "   Manifest exists: $([ -f git-pm.yaml ] && echo 'YES' || echo 'NO')"
echo "   Script exists: $([ -f git-pm/git-pm.py ] && echo 'YES' || echo 'NO')"
echo "   Parent has no git-pm.yaml: $([ ! -f ../git-pm.yaml ] && echo 'GOOD' || echo 'BAD')"
echo ""

echo "6. Running install..."
python git-pm/git-pm.py install
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "   ✗ Install failed"
    echo "   Debug: PWD=$(pwd)"
    echo "   Files:"
    ls -la
    exit 1
fi

echo ""
echo "7. Verifying..."

[ ! -d ".git-packages/mylib" ] && echo "   ✗ No package dir" && exit 1
echo "   ✓ Package directory"

[ ! -f ".git-packages/mylib/mylib.py" ] && echo "   ✗ No package files" && exit 1
echo "   ✓ Package files"

[ ! -f "git-pm.lock" ] && echo "   ✗ No lock file" && exit 1
echo "   ✓ Lock file"

echo ""
echo "8. Testing imports..."
python << 'PYEOF'
import sys
sys.path.insert(0, '.git-packages')
from mylib import greet, add
print(f"   ✓ Import: {greet('Test')}")
print(f"   ✓ Function: {add(2, 3)} = 5")
assert add(2, 3) == 5
PYEOF

[ $? -ne 0 ] && exit 1

echo ""
echo "9. List packages..."
python git-pm/git-pm.py list

echo ""
echo "============================================"
echo "✅ All tests passed!"
echo "============================================"
echo ""
echo "Test at: $TEST_ROOT/workspace/test-project"
echo "Clean up: rm -rf $TEST_ROOT"
echo ""

# Auto cleanup
if [ "$AUTO_CLEANUP" = "true" ]; then
    rm -rf "$TEST_ROOT"
    echo "✓ Cleaned up"
fi
