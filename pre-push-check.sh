#!/bin/bash
# Pre-push verification script

echo "================================================"
echo "Git-PM Pre-Push Verification"
echo "================================================"
echo ""

EXIT_CODE=0

# 1. Syntax check
echo "1. Checking Python syntax..."
if python3 -m py_compile git-pm.py 2>/dev/null; then
    echo "   ✓ Syntax OK"
else
    echo "   ✗ Syntax error"
    EXIT_CODE=1
fi

# 2. Python 3.7 compatibility
echo "2. Checking Python 3.7 compatibility..."
# Check if dirs_exist_ok is used as a parameter (not just in comments)
if ! grep -E "copytree.*dirs_exist_ok\s*=" git-pm.py > /dev/null; then
    echo "   ✓ No dirs_exist_ok parameter (Python 3.7 compatible)"
else
    echo "   ✗ Still has dirs_exist_ok parameter"
    EXIT_CODE=1
fi

# 3. Azure SSH support
echo "3. Checking Azure DevOps SSH support..."
if grep -q "ssh.dev.azure.com" git-pm.py; then
    echo "   ✓ Azure SSH format present"
else
    echo "   ✗ Azure SSH format missing"
    EXIT_CODE=1
fi

# 4. Add command
echo "4. Checking add command..."
if python git-pm.py add --help > /dev/null 2>&1; then
    echo "   ✓ Add command works"
else
    echo "   ✗ Add command error"
    EXIT_CODE=1
fi

# 5. Default config
echo "5. Checking default config file..."
if [ -f git-pm.default.yaml ]; then
    echo "   ✓ Default config exists"
else
    echo "   ✗ Default config missing"
    EXIT_CODE=1
fi

# 6. Examples directory
echo "6. Checking examples directory..."
if [ -d examples ] && [ -f examples/git-pm.yaml ] && [ -f examples/git-pm.local.yaml ]; then
    echo "   ✓ Examples directory complete"
else
    echo "   ✗ Examples directory incomplete"
    EXIT_CODE=1
fi

# 7. Core files
echo "7. Checking core files..."
MISSING=0
for file in git-pm.py simple-test.sh test-git-pm.sh README.md; do
    if [ ! -f "$file" ]; then
        echo "   ✗ Missing: $file"
        MISSING=1
    fi
done
if [ $MISSING -eq 0 ]; then
    echo "   ✓ All core files present"
else
    EXIT_CODE=1
fi

echo ""
echo "================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All checks passed - Ready to push!"
    echo ""
    echo "Next steps:"
    echo "  git add ."
    echo '  git commit -m "Complete implementation with Python 3.7 fix"'
    echo "  git push origin main"
else
    echo "❌ Some checks failed - Fix issues before pushing"
fi
echo "================================================"

exit $EXIT_CODE
