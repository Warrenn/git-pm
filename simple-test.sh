#!/bin/bash
# Simple manual test for git-pm
# This creates a minimal test case you can inspect manually

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$SCRIPT_DIR/simple-test"

echo "============================================"
echo "git-pm Simple Manual Test"
echo "============================================"
echo ""

# Clean previous test
if [ -d "$TEST_DIR" ]; then
    echo "Cleaning previous test..."
    rm -rf "$TEST_DIR"
fi

# Create test directory
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "1. Creating a mock git repository..."
mkdir -p mock-repo/packages/mylib
cd mock-repo

git init
git config user.email "test@example.com"
git config user.name "Test User"

# Create package content
cat > packages/mylib/README.md << 'EOF'
# My Library

This is a test library.
EOF

cat > packages/mylib/mylib.py << 'EOF'
def greet(name):
    """Greet someone"""
    return f"Hello, {name}!"

def add(a, b):
    """Add two numbers"""
    return a + b
EOF

git add .
git commit -m "Initial commit"
git tag v1.0.0

echo "   ✓ Mock repository created with tag v1.0.0"
echo ""

# Create test project
cd "$TEST_DIR"
mkdir test-project
cd test-project

echo "2. Creating git-pm.yaml manifest..."
cat > git-pm.yaml << EOF
packages:
  mylib:
    repo: file://$TEST_DIR/mock-repo
    path: packages/mylib
    ref:
      type: tag
      value: v1.0.0
EOF

echo "   ✓ Manifest created"
echo ""

echo "3. Running git-pm install..."
python3 "$SCRIPT_DIR/git-pm.py" install
echo ""

echo "4. Verifying installation..."
if [ -d ".git-packages/mylib" ]; then
    echo "   ✓ Package directory exists"
else
    echo "   ✗ Package directory not found!"
    exit 1
fi

if [ -f ".git-packages/mylib/mylib.py" ]; then
    echo "   ✓ Package files accessible"
else
    echo "   ✗ Package files not accessible!"
    exit 1
fi

if [ -f "git-pm.lock" ]; then
    echo "   ✓ Lock file created"
else
    echo "   ✗ Lock file not created!"
    exit 1
fi

echo ""
echo "5. Testing Python import..."
python3 << 'PYEOF'
import sys
sys.path.insert(0, '.git-packages')

try:
    from mylib import greet, add
    
    result = greet("World")
    print(f"   ✓ Import successful: {result}")
    
    sum_result = add(5, 3)
    print(f"   ✓ Function call successful: 5 + 3 = {sum_result}")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)
PYEOF

echo ""
echo "6. Running git-pm list..."
python3 "$SCRIPT_DIR/git-pm.py" list
echo ""

echo "============================================"
echo "✅ All tests passed!"
echo "============================================"
echo ""
echo "Test files located at: $TEST_DIR"
echo "You can inspect:"
echo "  - $TEST_DIR/test-project/git-pm.yaml (manifest)"
echo "  - $TEST_DIR/test-project/git-pm.lock (lockfile)"
echo "  - $TEST_DIR/test-project/.git-packages/ (installed packages)"
echo ""
echo "To clean up: rm -rf $TEST_DIR"
