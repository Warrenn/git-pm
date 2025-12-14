#!/bin/bash
# Comprehensive test for git-pm config command

set -e

TEST_DIR="/tmp/git-pm-config-test-$$"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cleanup() {
    rm -rf "$TEST_DIR"
    rm -rf ~/.git-pm/config.test-backup
}

trap cleanup EXIT

echo "============================================"
echo "git-pm config Command Test"
echo "============================================"
echo "Test location: $TEST_DIR"
echo ""

# Find git-pm.py BEFORE changing directories
# Try multiple locations for flexibility
GIT_PM_PATH=""

if [ -f "$SCRIPT_DIR/../git-pm.py" ]; then
    # Script is in tests/ subdirectory, git-pm.py is in parent (typical)
    GIT_PM_PATH="$SCRIPT_DIR/../git-pm.py"
elif [ -f "$SCRIPT_DIR/git-pm.py" ]; then
    # Script is in same directory as git-pm.py
    GIT_PM_PATH="$SCRIPT_DIR/git-pm.py"
elif [ -f "git-pm.py" ]; then
    # git-pm.py is in current directory
    GIT_PM_PATH="$(pwd)/git-pm.py"
else
    echo "Error: Cannot find git-pm.py"
    echo "Searched in:"
    echo "  - $SCRIPT_DIR/../git-pm.py"
    echo "  - $SCRIPT_DIR/git-pm.py"
    echo "  - $(pwd)/git-pm.py"
    exit 1
fi

echo "✓ Found git-pm.py at: $GIT_PM_PATH"

# Backup existing user config if it exists
if [ -f ~/.git-pm/config ]; then
    cp ~/.git-pm/config ~/.git-pm/config.test-backup
    echo "✓ Backed up existing user config"
fi

# Remove user config for clean test
rm -f ~/.git-pm/config

# Setup test environment
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Copy git-pm.py using the absolute path we found earlier
cp "$GIT_PM_PATH" .

# Initialize a minimal git-pm project
cat > git-pm.json << 'EOF'
{
    "packages": {}
}
EOF

git init
git config user.email "test@test.com"
git config user.name "Test User"

echo "✓ Test environment ready"
echo ""

# Test 1: Show help
echo "Test 1: Show help"
python3 git-pm.py config --help | grep -q "Configuration key"
echo "✓ Help works"
echo ""

# Test 2: List without any configs (should show defaults)
echo "Test 2: List configuration (defaults only)"
python3 git-pm.py config --list
echo ""

# Test 3: Get a default value
echo "Test 3: Get default value"
VALUE=$(python3 git-pm.py config packages_dir)
if [ "$VALUE" = ".git-packages" ]; then
    echo "✓ Got default value: $VALUE"
else
    echo "✗ Expected '.git-packages', got: $VALUE"
    exit 1
fi
echo ""

# Test 4: Set a value at project level
echo "Test 4: Set value at project level"
python3 git-pm.py config packages_dir ".deps"

# Verify it was written
if [ -f "git-pm.config" ]; then
    echo "✓ git-pm.config created"
    cat git-pm.config
else
    echo "✗ git-pm.config not created"
    exit 1
fi
echo ""

# Test 5: Get the set value
echo "Test 5: Get set value"
VALUE=$(python3 git-pm.py config packages_dir)
if [ "$VALUE" = ".deps" ]; then
    echo "✓ Got project value: $VALUE"
else
    echo "✗ Expected '.deps', got: $VALUE"
    exit 1
fi
echo ""

# Test 6: Set a value at user level (--global)
echo "Test 6: Set value at user level (--global)"
python3 git-pm.py config --global cache_dir "/tmp/my-cache"

# Verify it was written
if [ -f ~/.git-pm/config ]; then
    echo "✓ ~/.git-pm/config created"
    cat ~/.git-pm/config
else
    echo "✗ ~/.git-pm/config not created"
    exit 1
fi
echo ""

# Test 7: List shows both levels
echo "Test 7: List shows merged configuration"
python3 git-pm.py config --list
echo ""

# Test 8: Project value overrides user value
echo "Test 8: Test config precedence (project > user)"
python3 git-pm.py config --global packages_dir ".vendor"
python3 git-pm.py config packages_dir ".project-deps"

VALUE=$(python3 git-pm.py config packages_dir)
if [ "$VALUE" = ".project-deps" ]; then
    echo "✓ Project value overrides user value: $VALUE"
else
    echo "✗ Expected '.project-deps', got: $VALUE"
    exit 1
fi
echo ""

# Test 9: Unset project value, should fallback to user
echo "Test 9: Unset value at project level"
python3 git-pm.py config --unset packages_dir

VALUE=$(python3 git-pm.py config packages_dir)
if [ "$VALUE" = ".vendor" ]; then
    echo "✓ Falls back to user value after unset: $VALUE"
else
    echo "✗ Expected '.vendor', got: $VALUE"
    exit 1
fi
echo ""

# Test 10: Unset user value, should fallback to default
echo "Test 10: Unset value at user level"
python3 git-pm.py config --unset --global packages_dir

VALUE=$(python3 git-pm.py config packages_dir)
if [ "$VALUE" = ".git-packages" ]; then
    echo "✓ Falls back to default after unset: $VALUE"
else
    echo "✗ Expected '.git-packages', got: $VALUE"
    exit 1
fi
echo ""

# Test 11: Try to set unknown key
echo "Test 11: Try to set unknown key (should error)"
if python3 git-pm.py config unknown_key value 2>&1 | grep -q "Unknown configuration key"; then
    echo "✓ Correctly rejects unknown key"
else
    echo "✗ Should have rejected unknown key"
    exit 1
fi
echo ""

# Test 12: Unset non-existent key (should succeed silently)
echo "Test 12: Unset non-existent key (should succeed silently)"
python3 git-pm.py config --unset azure_devops_pat  # Valid key, but not in config
echo "✓ Silently succeeded"
echo ""

# Test 13: Set and get all valid keys
echo "Test 13: Set and get all valid configuration keys"
python3 git-pm.py config packages_dir ".test-packages"
python3 git-pm.py config cache_dir "/tmp/test-cache"

VALUE1=$(python3 git-pm.py config packages_dir)
VALUE2=$(python3 git-pm.py config cache_dir)

if [ "$VALUE1" = ".test-packages" ] && [ "$VALUE2" = "/tmp/test-cache" ]; then
    echo "✓ All keys work correctly"
else
    echo "✗ Key retrieval failed"
    exit 1
fi
echo ""

# Test 14: Verify config files have correct JSON format
echo "Test 14: Verify JSON format"
if python3 -c "import json; json.load(open('git-pm.config'))" 2>/dev/null; then
    echo "✓ Project config is valid JSON"
else
    echo "✗ Project config has invalid JSON"
    exit 1
fi

if python3 -c "import json, os; json.load(open(os.path.expanduser('~/.git-pm/config')))" 2>/dev/null; then
    echo "✓ User config is valid JSON"
else
    echo "✗ User config has invalid JSON"
    exit 1
fi
echo ""

# Test 15: Check that list shows correct sources
echo "Test 15: Verify list shows sources correctly"
OUTPUT=$(python3 git-pm.py config --list)

if echo "$OUTPUT" | grep -q "(project)"; then
    echo "✓ List shows project source"
else
    echo "✗ List doesn't show project source"
    exit 1
fi

if echo "$OUTPUT" | grep -q "(default)"; then
    echo "✓ List shows default source"
else
    echo "✗ List doesn't show default source"
    exit 1
fi
echo ""

# Restore original user config if it existed
if [ -f ~/.git-pm/config.test-backup ]; then
    mv ~/.git-pm/config.test-backup ~/.git-pm/config
    echo "✓ Restored original user config"
else
    rm -f ~/.git-pm/config
fi

echo "============================================"
echo "✅ All tests passed!"
echo "============================================"
echo ""
echo "Test results:"
echo "  ✓ Help command works"
echo "  ✓ List shows defaults"
echo "  ✓ Get returns default values"
echo "  ✓ Set at project level"
echo "  ✓ Set at user level (--global)"
echo "  ✓ List shows merged config"
echo "  ✓ Config precedence (project > user > default)"
echo "  ✓ Unset at project level"
echo "  ✓ Unset at user level"
echo "  ✓ Unknown key validation"
echo "  ✓ Silent unset of missing keys"
echo "  ✓ All valid keys work"
echo "  ✓ Valid JSON format"
echo "  ✓ List shows sources"
echo ""