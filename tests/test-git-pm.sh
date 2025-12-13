#!/bin/bash
# Comprehensive test script for git-pm
# LOCATION: ./tests/test-git-pm.sh

set -e

# Get paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GIT_PM_SCRIPT="$REPO_ROOT/git-pm.py"

if [ ! -f "$GIT_PM_SCRIPT" ]; then
    echo "❌ git-pm.py not found at $GIT_PM_SCRIPT"
    exit 1
fi

TEST_DIR="$SCRIPT_DIR/test-workspace"
PYTHON="${PYTHON:-python3}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

cleanup() {
    print_header "Cleaning up"
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
        print_success "Removed test workspace"
    fi
}

setup_test_env() {
    print_header "Setting up test environment"
    cleanup
    mkdir -p "$TEST_DIR"
    cd "$TEST_DIR"
    print_success "Created: $TEST_DIR"
}

setup_gitpm_in_project() {
    local project_dir=$1
    mkdir -p "$project_dir"
    cp "$GIT_PM_SCRIPT" "$project_dir/git-pm.py"
}

run_gitpm() {
    $PYTHON git-pm.py "$@"
}

create_mock_repo() {
    local repo_name=$1
    local repo_dir="$TEST_DIR/mock-repos/$repo_name"
    
    print_info "Creating mock repo: $repo_name"
    
    mkdir -p "$repo_dir"
    cd "$repo_dir"
    
    git init
    git config user.email "test@example.com"
    git config user.name "Test User"
    
    mkdir -p packages/utils
    echo "# Utils" > packages/utils/README.md
    echo "def hello(): return 'Hello'" > packages/utils/utils.py
    cat > packages/utils/git-pm.json << 'EOF'
{"packages": {}}
EOF
    
    mkdir -p packages/components
    echo "# Components" > packages/components/README.md
    echo "def render(): return 'Component'" > packages/components/component.py
    cat > packages/components/git-pm.json << 'EOF'
{"packages": {}}
EOF
    
    git add .
    git commit -m "Initial commit"
    git tag v1.0.0
    
    git checkout -b develop
    echo "# Dev" >> packages/utils/README.md
    git add .
    git commit -m "Dev changes"
    
    git checkout main 2>/dev/null || git checkout master
    
    print_success "Created mock repo"
    cd "$TEST_DIR"
}

test_basic_install() {
    print_header "TEST 1: Basic Install (JSON)"
    
    local project_dir="$TEST_DIR/test-project-1"
    setup_gitpm_in_project "$project_dir"
    cd "$project_dir"
    
    cat > git-pm.json << EOF
{
    "packages": {
        "utils": {
            "repo": "file://$TEST_DIR/mock-repos/test-repo",
            "path": "packages/utils",
            "ref": {"type": "tag", "value": "v1.0.0"}
        }
    }
}
EOF
    
    run_gitpm install
    
    [ -d ".git-packages/utils" ] || { print_error "Package not installed"; return 1; }
    print_success "Package installed"
    
    [ -f "git-pm.lock" ] || { print_error "Lockfile missing"; return 1; }
    print_success "Lockfile created"
    
    $PYTHON -c "import json; json.load(open('git-pm.lock'))" || { print_error "Invalid lockfile"; return 1; }
    print_success "Lockfile is valid JSON"
    
    cd "$TEST_DIR"
}

test_local_override() {
    print_header "TEST 2: Local Override (New Schema)"
    
    local project_dir="$TEST_DIR/test-project-2"
    setup_gitpm_in_project "$project_dir"
    cd "$project_dir"
    
    mkdir -p "$TEST_DIR/local-dev/utils"
    echo "def hello(): return 'LOCAL'" > "$TEST_DIR/local-dev/utils/utils.py"
    
    cat > git-pm.json << EOF
{
    "packages": {
        "utils": {
            "repo": "file://$TEST_DIR/mock-repos/test-repo",
            "path": "packages/utils",
            "ref": {"type": "tag", "value": "v1.0.0"}
        }
    }
}
EOF
    
    cat > git-pm.local << EOF
{
    "packages": {
        "utils": {
            "repo": "file://$TEST_DIR/local-dev/utils"
        }
    }
}
EOF
    
    run_gitpm install
    
    [ -d ".git-packages/utils" ] || { print_error "Package not installed"; return 1; }
    print_success "Local override applied"
    
    cd "$TEST_DIR"
}

test_verify_command() {
    print_header "TEST 3: Verify Command"
    
    local project_dir="$TEST_DIR/test-project-3"
    setup_gitpm_in_project "$project_dir"
    cd "$project_dir"
    
    cat > git-pm.json << EOF
{
    "packages": {
        "utils": {
            "repo": "file://$TEST_DIR/mock-repos/test-repo",
            "path": "packages/utils",
            "ref": {"type": "tag", "value": "v1.0.0"}
        }
    }
}
EOF
    
    run_gitpm install > /dev/null 2>&1
    
    run_gitpm verify > /dev/null 2>&1 || { print_error "Verify failed on valid"; return 1; }
    print_success "Verify passes"
    
    rm -rf .git-packages/utils
    
    run_gitpm verify > /dev/null 2>&1 && { print_error "Verify didn't detect corruption"; return 1; }
    print_success "Verify detects corruption"
    
    cd "$TEST_DIR"
}

test_reproducible_builds() {
    print_header "TEST 4: Reproducible Builds"
    
    local project_dir="$TEST_DIR/test-project-4"
    setup_gitpm_in_project "$project_dir"
    cd "$project_dir"
    
    cat > git-pm.json << EOF
{
    "packages": {
        "utils": {
            "repo": "file://$TEST_DIR/mock-repos/test-repo",
            "path": "packages/utils",
            "ref": {"type": "branch", "value": "develop"}
        }
    }
}
EOF
    
    run_gitpm install > /dev/null 2>&1
    
    local locked=$($PYTHON -c "import json; print(json.load(open('git-pm.lock'))['packages']['utils']['commit'])")
    print_info "Locked: ${locked:0:8}"
    
    run_gitpm clean > /dev/null 2>&1
    run_gitpm install > /dev/null 2>&1
    
    local new=$($PYTHON -c "import json; print(json.load(open('git-pm.lock'))['packages']['utils']['commit'])")
    
    [ "$locked" = "$new" ] || { print_error "Not reproducible"; return 1; }
    print_success "Reproducible build"
    
    cd "$TEST_DIR"
}

test_force_fresh() {
    print_header "TEST 5: Force Fresh Flag"
    
    local project_dir="$TEST_DIR/test-project-5"
    setup_gitpm_in_project "$project_dir"
    cd "$project_dir"
    
    cat > git-pm.json << EOF
{
    "packages": {
        "utils": {
            "repo": "file://$TEST_DIR/mock-repos/test-repo",
            "path": "packages/utils",
            "ref": {"type": "tag", "value": "v1.0.0"}
        }
    }
}
EOF
    
    run_gitpm install > /dev/null 2>&1
    
    run_gitpm install --force-fresh 2>&1 | grep -q "Forcing fresh" || { print_error "Flag didn't work"; return 1; }
    print_success "--force-fresh works"
    
    cd "$TEST_DIR"
}

test_list_command() {
    print_header "TEST 6: List Command"
    
    local project_dir="$TEST_DIR/test-project-6"
    setup_gitpm_in_project "$project_dir"
    cd "$project_dir"
    
    cat > git-pm.json << EOF
{
    "packages": {
        "utils": {
            "repo": "file://$TEST_DIR/mock-repos/test-repo",
            "path": "packages/utils",
            "ref": {"type": "tag", "value": "v1.0.0"}
        }
    }
}
EOF
    
    run_gitpm install > /dev/null 2>&1
    run_gitpm list
    
    print_success "List command works"
    cd "$TEST_DIR"
}

test_clean_command() {
    print_header "TEST 7: Clean Command"
    
    local project_dir="$TEST_DIR/test-project-7"
    setup_gitpm_in_project "$project_dir"
    cd "$project_dir"
    
    cat > git-pm.json << EOF
{
    "packages": {
        "utils": {
            "repo": "file://$TEST_DIR/mock-repos/test-repo",
            "path": "packages/utils",
            "ref": {"type": "tag", "value": "v1.0.0"}
        }
    }
}
EOF
    
    run_gitpm install > /dev/null 2>&1
    run_gitpm clean
    
    [ ! -d ".git-packages" ] || { print_error "Packages not removed"; return 1; }
    print_success "Clean works"
    
    cd "$TEST_DIR"
}

test_add_command() {
    print_header "TEST 8: Add Command"
    
    local project_dir="$TEST_DIR/test-project-8"
    setup_gitpm_in_project "$project_dir"
    cd "$project_dir"
    
    run_gitpm add pkg file://$TEST_DIR/mock-repos/test-repo --path packages/utils --ref-type tag --ref-value v1.0.0
    
    [ -f "git-pm.json" ] || { print_error "Manifest not created"; return 1; }
    print_success "Manifest created"
    
    $PYTHON -c "import json; json.load(open('git-pm.json'))" || { print_error "Invalid JSON"; return 1; }
    print_success "Valid JSON"
    
    grep -q "pkg" git-pm.json || { print_error "Package not added"; return 1; }
    print_success "Package added"
    
    cd "$TEST_DIR"
}

main() {
    print_header "git-pm Test Suite (from ./tests/)"
    
    setup_test_env
    create_mock_repo "test-repo"
    
    git config --global --add safe.directory "$TEST_DIR/mock-repos/test-repo" 2>/dev/null || true
    
    case "${1:-all}" in
        "basic") test_basic_install ;;
        "override") test_local_override ;;
        "verify") test_verify_command ;;
        "reproducible") test_reproducible_builds ;;
        "force-fresh") test_force_fresh ;;
        "list") test_list_command ;;
        "clean") test_clean_command ;;
        "add") test_add_command ;;
        "all")
            test_basic_install
            test_local_override
            test_verify_command
            test_reproducible_builds
            test_force_fresh
            test_list_command
            test_clean_command
            test_add_command
            ;;
        *)
            echo "Usage: $0 [basic|override|verify|reproducible|force-fresh|list|clean|add|all]"
            exit 1
            ;;
    esac
    
    print_header "All Tests Completed!"
    cleanup
}

main "$@"