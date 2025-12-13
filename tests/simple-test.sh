#!/bin/bash
# Simple isolated test for git-pm (no lockfile tests)
# LOCATION: ./tests/simple-test.sh

set -e

# Get script directory (./tests/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Repository root is parent of tests directory
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GIT_PM_SCRIPT="$REPO_ROOT/git-pm.py"

if [ ! -f "$GIT_PM_SCRIPT" ]; then
    echo "❌ git-pm.py not found at $GIT_PM_SCRIPT"
    echo "   Expected: <repo-root>/git-pm.py"
    exit 1
fi

TEST_ROOT="/tmp/git-pm-test-$$"

echo "============================================"
echo "git-pm Simple Test (Lockfile-Free)"
echo "============================================"
echo "Repository: $REPO_ROOT"
echo "Test location: $TEST_ROOT"
echo ""

# Create isolated test
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
"""My Library"""
from .mylib import greet, add
__all__ = ['greet', 'add']
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

# JSON manifest
cat > git-pm.json << EOF
{
    "packages": {
        "mylib": {
            "repo": "file://$TEST_ROOT/workspace/mock-repo",
            "path": "packages/mylib",
            "ref": {
                "type": "tag",
                "value": "v1.0.0"
            }
        }
    }
}
EOF

echo "   ✓ JSON manifest created"
echo ""

echo "3. Copying git-pm.py..."
cp "$GIT_PM_SCRIPT" git-pm.py
echo "   ✓ Script ready"
echo ""

echo "4. Version check:"
python3 git-pm.py --version
echo ""

# Git config
git config --global --add safe.directory "$TEST_ROOT/workspace/mock-repo" 2>/dev/null || true

echo "5. Running install..."
python3 git-pm.py install
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "   ✗ Install failed"
    exit 1
fi

echo ""
echo "6. Verifying installation..."

[ ! -d ".git-packages/mylib" ] && echo "   ✗ No package dir" && exit 1
echo "   ✓ Package directory"

[ ! -f ".git-packages/mylib/mylib.py" ] && echo "   ✗ No package files" && exit 1
echo "   ✓ Package files"

echo ""
echo "7. Testing imports..."
python3 << 'PYEOF'
import sys
sys.path.insert(0, '.git-packages')
from mylib import greet, add
print(f"   ✓ Import: {greet('Test')}")
print(f"   ✓ Function: {add(2, 3)} = 5")
assert add(2, 3) == 5
PYEOF

echo ""
echo "8. Testing dependency resolution..."
python3 git-pm.py install 2>&1 | grep -q "Discovering dependencies" && echo "   ✓ Dependencies resolved" || echo "   ⚠️  Dependency resolution not mentioned"

echo ""
echo "9. List packages..."
ls -la .git-packages/

echo ""
echo "============================================"
echo "✅ All tests passed!"
echo "============================================"
echo ""
echo "Test location: $TEST_ROOT"
echo "Clean up: rm -rf $TEST_ROOT"
echo ""

if [ "$AUTO_CLEANUP" = "true" ]; then
    rm -rf "$TEST_ROOT"
    echo "✓ Cleaned up"
fi