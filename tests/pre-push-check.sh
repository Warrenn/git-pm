#!/bin/bash
# Pre-push verification script
# LOCATION: ./tests/pre-push-check.sh
# RUN FROM: Repository root

# Get paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to repository root
cd "$REPO_ROOT"

echo "================================================"
echo "Git-PM Pre-Push Verification"
echo "================================================"
echo "Repository: $REPO_ROOT"
echo ""

EXIT_CODE=0

# 1. Check we're in the right place
echo "1. Verifying repository structure..."
if [ ! -f "git-pm.py" ]; then
    echo "   ✗ git-pm.py not found (run from repository root)"
    EXIT_CODE=1
else
    echo "   ✓ git-pm.py found"
fi

if [ ! -d "tests" ]; then
    echo "   ✗ tests/ directory not found"
    EXIT_CODE=1
else
    echo "   ✓ tests/ directory exists"
fi

# 2. Syntax check
echo "2. Checking Python syntax..."
if python3 -m py_compile git-pm.py 2>/dev/null; then
    echo "   ✓ Syntax OK"
else
    echo "   ✗ Syntax error"
    EXIT_CODE=1
fi

# 3. Python 3.8+ compatibility
echo "3. Checking Python 3.8+ compatibility..."
if ! grep -E "match\s+.*:" git-pm.py > /dev/null 2>&1; then
    echo "   ✓ No match statements (3.10+ only)"
else
    echo "   ✗ Contains match statements"
    EXIT_CODE=1
fi

# 4. JSON format (not YAML)
echo "4. Checking JSON format..."
if grep -q "SimpleYAML" git-pm.py; then
    echo "   ✗ Still contains SimpleYAML"
    EXIT_CODE=1
else
    echo "   ✓ No SimpleYAML (JSON format)"
fi

# 5. Test files
echo "5. Checking test files..."
MISSING=0
for file in tests/test_features.py tests/simple-test.sh tests/test-git-pm.sh tests/pre-push-check.sh; do
    if [ ! -f "$file" ]; then
        echo "   ✗ Missing: $file"
        MISSING=1
    fi
done
if [ $MISSING -eq 0 ]; then
    echo "   ✓ All test files present"
else
    EXIT_CODE=1
fi

# 6. CI workflow
echo "6. Checking CI workflow..."
if [ -f ".github/workflows/ci.yml" ]; then
    echo "   ✓ CI workflow present"
else
    echo "   ✗ CI workflow missing"
    EXIT_CODE=1
fi

# 7. Core files
echo "7. Checking core files..."
MISSING=0
for file in git-pm.py README.md; do
    if [ ! -f "$file" ]; then
        echo "   ✗ Missing: $file"
        MISSING=1
    fi
done
if [ $MISSING -eq 0 ]; then
    echo "   ✓ Core files present"
else
    EXIT_CODE=1
fi

# 8. New features
echo "8. Checking new features..."

if grep -q "_deep_merge" git-pm.py; then
    echo "   ✓ Config merging"
else
    echo "   ✗ Config merging missing"
    EXIT_CODE=1
fi

if grep -q "def cmd_verify" git-pm.py; then
    echo "   ✓ Verify command"
else
    echo "   ✗ Verify command missing"
    EXIT_CODE=1
fi

if grep -q "install_from_lockfile" git-pm.py; then
    echo "   ✓ Lockfile features"
else
    echo "   ✗ Lockfile features missing"
    EXIT_CODE=1
fi

# 9. Version check
echo "9. Checking version..."
VERSION=$(python3 git-pm.py --version 2>&1 | grep -oE "[0-9]+\.[0-9]+\.[0-9]+")
if [ -n "$VERSION" ]; then
    echo "   ✓ Version: $VERSION"
else
    echo "   ✗ Version not found"
    EXIT_CODE=1
fi

# 10. Test executability
echo "10. Checking test scripts are executable..."
TESTS_EXEC=1
for script in tests/simple-test.sh tests/test-git-pm.sh tests/pre-push-check.sh; do
    if [ -x "$script" ]; then
        echo "   ✓ $script is executable"
    else
        echo "   ⚠️  $script not executable (run: chmod +x $script)"
        TESTS_EXEC=0
    fi
done

echo ""
echo "================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All checks passed - Ready to push!"
    echo ""
    if [ $TESTS_EXEC -eq 0 ]; then
        echo "Recommended: Make test scripts executable"
        echo "  cd $REPO_ROOT"
        echo "  chmod +x tests/*.sh"
        echo ""
    fi
    echo "Next steps:"
    echo "  git add ."
    echo '  git commit -m "Update test suite for JSON format"'
    echo "  git push origin main"
else
    echo "❌ Some checks failed - Fix issues before pushing"
fi
echo "================================================"

exit $EXIT_CODE