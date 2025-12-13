#!/bin/bash
# Comprehensive test for git-pm remove command
# Tests dependency cascade, deep recursion, and all edge cases

set -e

TEST_DIR="/tmp/git-pm-remove-test-$$"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cleanup() {
    rm -rf "$TEST_DIR"
}

trap cleanup EXIT

echo "============================================"
echo "git-pm remove Command Test"
echo "============================================"
echo "Test location: $TEST_DIR"
echo ""

# Setup test environment
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Copy git-pm.py
cp "$SCRIPT_DIR/git-pm.py" .

echo "Creating test package structure..."
echo ""

# Create test packages with dependencies
# Dependency tree:
#   project depends on: pkg-a, pkg-x
#   pkg-a depends on: pkg-b, pkg-c
#   pkg-b depends on: pkg-d
#   pkg-c depends on: pkg-d
#   pkg-x depends on: pkg-d
#   pkg-d has no dependencies
#
# Expected behavior when removing pkg-a:
#   - pkg-a: removed (explicitly requested)
#   - pkg-b: removed (only needed by pkg-a)
#   - pkg-c: removed (only needed by pkg-a)
#   - pkg-d: KEPT (also needed by pkg-x)
#   - pkg-x: KEPT (still in manifest)

# Create package directories
for pkg in pkg-a pkg-b pkg-c pkg-d pkg-x; do
    mkdir -p "packages/$pkg"
    echo "# $pkg" > "packages/$pkg/README.md"
done

# Create pkg-d manifest (no dependencies)
cat > packages/pkg-d/git-pm.json << 'EOF'
{
    "packages": {}
}
EOF

# Create pkg-c manifest (depends on pkg-d)
cat > packages/pkg-c/git-pm.json << 'EOF'
{
    "packages": {
        "pkg-d": {
            "repo": "file:///tmp/mock",
            "ref": {"type": "tag", "value": "v1.0.0"}
        }
    }
}
EOF

# Create pkg-b manifest (depends on pkg-d)
cat > packages/pkg-b/git-pm.json << 'EOF'
{
    "packages": {
        "pkg-d": {
            "repo": "file:///tmp/mock",
            "ref": {"type": "tag", "value": "v1.0.0"}
        }
    }
}
EOF

# Create pkg-a manifest (depends on pkg-b and pkg-c)
cat > packages/pkg-a/git-pm.json << 'EOF'
{
    "packages": {
        "pkg-b": {
            "repo": "file:///tmp/mock",
            "ref": {"type": "tag", "value": "v1.0.0"}
        },
        "pkg-c": {
            "repo": "file:///tmp/mock",
            "ref": {"type": "tag", "value": "v1.0.0"}
        }
    }
}
EOF

# Create pkg-x manifest (depends on pkg-d)
cat > packages/pkg-x/git-pm.json << 'EOF'
{
    "packages": {
        "pkg-d": {
            "repo": "file:///tmp/mock",
            "ref": {"type": "tag", "value": "v1.0.0"}
        }
    }
}
EOF

echo "Creating test project..."

# Initialize project
git init
git config user.email "test@test.com"
git config user.name "Test User"

# Create project manifest (depends on pkg-a and pkg-x)
cat > git-pm.json << EOF
{
    "packages": {
        "pkg-a": {
            "repo": "file://$TEST_DIR/packages/pkg-a",
            "ref": {"type": "tag", "value": "v1.0.0"}
        },
        "pkg-x": {
            "repo": "file://$TEST_DIR/packages/pkg-x",
            "ref": {"type": "tag", "value": "v1.0.0"}
        }
    }
}
EOF

# Simulate installation by creating .git-packages structure
mkdir -p .git-packages/{pkg-a,pkg-b,pkg-c,pkg-d,pkg-x}

# Copy package contents
for pkg in pkg-a pkg-b pkg-c pkg-d pkg-x; do
    cp "packages/$pkg/README.md" ".git-packages/$pkg/"
    if [ -f "packages/$pkg/git-pm.json" ]; then
        cp "packages/$pkg/git-pm.json" ".git-packages/$pkg/"
    fi
done

# Create .git-pm.env
cat > .git-pm.env << EOF
GIT_PM_PACKAGES_DIR=$TEST_DIR/.git-packages
GIT_PM_PROJECT_ROOT=$TEST_DIR
GIT_PM_PACKAGE_pkg_a=$TEST_DIR/.git-packages/pkg-a
GIT_PM_PACKAGE_pkg_b=$TEST_DIR/.git-packages/pkg-b
GIT_PM_PACKAGE_pkg_c=$TEST_DIR/.git-packages/pkg-c
GIT_PM_PACKAGE_pkg_d=$TEST_DIR/.git-packages/pkg-d
GIT_PM_PACKAGE_pkg_x=$TEST_DIR/.git-packages/pkg-x
EOF

echo "✓ Test environment ready"
echo ""

# Test 1: Show help
echo "Test 1: Show help"
python3 git-pm.py remove --help
echo ""

# Test 2: Try to remove non-existent package
echo "Test 2: Remove non-existent package (should fail gracefully)"
if python3 git-pm.py remove non-existent-pkg -y 2>&1 | grep -q "not found"; then
    echo "✓ Correctly rejects non-existent package"
else
    echo "✗ Should have rejected non-existent package"
    exit 1
fi
echo ""

# Test 3: Remove with dependency cascade
echo "Test 3: Remove pkg-a (should cascade to pkg-b and pkg-c, but keep pkg-d and pkg-x)"
echo ""

# Show initial state
echo "Initial packages in .git-packages/:"
ls -1 .git-packages/
echo ""

# Remove pkg-a with auto-confirm
python3 git-pm.py remove pkg-a -y

echo ""
echo "Verifying results..."

# Check manifest
if grep -q "pkg-a" git-pm.json; then
    echo "✗ pkg-a still in git-pm.json"
    exit 1
else
    echo "✓ pkg-a removed from git-pm.json"
fi

# Check filesystem
if [ -d ".git-packages/pkg-a" ]; then
    echo "✗ pkg-a still exists in .git-packages/"
    exit 1
else
    echo "✓ pkg-a removed from .git-packages/"
fi

if [ -d ".git-packages/pkg-b" ]; then
    echo "✗ pkg-b still exists (should be removed)"
    exit 1
else
    echo "✓ pkg-b removed from .git-packages/"
fi

if [ -d ".git-packages/pkg-c" ]; then
    echo "✗ pkg-c still exists (should be removed)"
    exit 1
else
    echo "✓ pkg-c removed from .git-packages/"
fi

if [ ! -d ".git-packages/pkg-d" ]; then
    echo "✗ pkg-d was removed (should be kept - needed by pkg-x)"
    exit 1
else
    echo "✓ pkg-d kept (still needed by pkg-x)"
fi

if [ ! -d ".git-packages/pkg-x" ]; then
    echo "✗ pkg-x was removed (should be kept)"
    exit 1
else
    echo "✓ pkg-x kept (still in manifest)"
fi

# Check .git-pm.env
if grep -q "pkg_a" .git-pm.env; then
    echo "✗ pkg-a still in .git-pm.env"
    exit 1
else
    echo "✓ pkg-a removed from .git-pm.env"
fi

if grep -q "pkg_b" .git-pm.env; then
    echo "✗ pkg-b still in .git-pm.env"
    exit 1
else
    echo "✓ pkg-b removed from .git-pm.env"
fi

if grep -q "pkg_c" .git-pm.env; then
    echo "✗ pkg-c still in .git-pm.env"
    exit 1
else
    echo "✓ pkg-c removed from .git-pm.env"
fi

if ! grep -q "pkg_d" .git-pm.env; then
    echo "✗ pkg-d removed from .git-pm.env (should be kept)"
    exit 1
else
    echo "✓ pkg-d kept in .git-pm.env"
fi

if ! grep -q "pkg_x" .git-pm.env; then
    echo "✗ pkg-x removed from .git-pm.env (should be kept)"
    exit 1
else
    echo "✓ pkg-x kept in .git-pm.env"
fi

echo ""
echo "Final packages in .git-packages/:"
ls -1 .git-packages/
echo ""

# Test 4: Test git-pm.local removal
echo "Test 4: Remove package from git-pm.local"
echo ""

# Add a package to git-pm.local
cat > git-pm.local << EOF
{
    "packages": {
        "pkg-x": {
            "repo": "file://$TEST_DIR/packages/pkg-x-local"
        }
    }
}
EOF

echo "Added pkg-x to git-pm.local"
python3 git-pm.py remove pkg-x -y

if grep -q "pkg-x" git-pm.local 2>/dev/null; then
    echo "✗ pkg-x still in git-pm.local"
    exit 1
else
    echo "✓ pkg-x removed from git-pm.local"
fi

if grep -q "pkg-x" git-pm.json; then
    echo "✗ pkg-x still in git-pm.json"
    exit 1
else
    echo "✓ pkg-x removed from git-pm.json"
fi

# pkg-x should be removed from disk now (no longer in manifest)
# But pkg-d should still be there (has dependencies in its manifest that were discovered)
# Actually, pkg-d should be removed now because pkg-x was the only thing keeping it
if [ -d ".git-packages/pkg-x" ]; then
    echo "✗ pkg-x still in .git-packages/"
    exit 1
else
    echo "✓ pkg-x removed from .git-packages/"
fi

if [ -d ".git-packages/pkg-d" ]; then
    echo "✗ pkg-d still in .git-packages/ (should be removed - no longer needed)"
    exit 1
else
    echo "✓ pkg-d removed from .git-packages/ (no longer needed)"
fi

echo ""
echo "============================================"
echo "✅ All tests passed!"
echo "============================================"
echo ""
echo "Test results:"
echo "  ✓ Non-existent package handling"
echo "  ✓ Dependency cascade (deep recursion)"
echo "  ✓ Keeping packages needed by others"
echo "  ✓ Manifest removal (both files)"
echo "  ✓ .git-pm.env cleanup"
echo "  ✓ Filesystem cleanup"
echo ""