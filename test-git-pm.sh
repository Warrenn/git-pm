#!/bin/bash
# Test script for git-pm v0.1.2
# Updated to work with parent-first manifest finding

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$SCRIPT_DIR/test-workspace"
PYTHON="${PYTHON:-python}"

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
    print_header "Cleaning up test workspace"
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
    print_success "Created test workspace: $TEST_DIR"
}

setup_gitpm_in_project() {
    local project_dir=$1
    mkdir -p "$project_dir/git-pm"
    
    if [ -f "$SCRIPT_DIR/git-pm.py" ]; then
        cp "$SCRIPT_DIR/git-pm.py" "$project_dir/git-pm/git-pm.py"
    else
        print_error "git-pm.py not found in $SCRIPT_DIR"
        return 1
    fi
}

run_gitpm() {
    $PYTHON git-pm/git-pm.py "$@"
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
    echo "# Utils Package" > packages/utils/README.md"
    echo "def hello():\n    return 'Hello from utils'" > packages/utils/utils.py
    
    mkdir -p packages/components
    echo "# Components Package" > packages/components/README.md
    echo "def render():\n    return 'Component'" > packages/components/component.py
    
    git add .
    git commit -m "Initial commit"
    git tag v1.0.0
    
    git checkout -b develop
    echo "# Development version" >> packages/utils/README.md
    git add .
    git commit -m "Dev changes"
    
    git checkout main 2>/dev/null || git checkout master
    
    print_success "Created mock repo with packages"
    cd "$TEST_DIR"
}

test_basic_install() {
    print_header "TEST 1: Basic Install"
    
    local project_dir="$TEST_DIR/test-project-1"
    mkdir -p "$project_dir"
    
    setup_gitpm_in_project "$project_dir"
    cd "$project_dir"
    
    cat > git-pm.yaml << EOF
packages:
  utils:
    repo: file://$TEST_DIR/mock-repos/test-repo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
  
  components:
    repo: file://$TEST_DIR/mock-repos/test-repo
    path: packages/components
    ref:
      type: branch
      value: main
EOF
    
    print_info "Created manifest with 2 packages"
    run_gitpm install
    
    if [ -d ".git-packages/utils" ] && [ -d ".git-packages/components" ]; then
        print_success "Packages installed successfully"
    else
        print_error "Packages not found in .git-packages/"
        return 1
    fi
    
    if [ -f "git-pm.lock" ]; then
        print_success "Lockfile created"
    else
        print_error "Lockfile not created"
        return 1
    fi
    
    if [ -f ".git-packages/utils/utils.py" ]; then
        print_success "Package files accessible"
    else
        print_error "Package files not accessible"
        return 1
    fi
    
    cd "$TEST_DIR"
}

test_local_override() {
    print_header "TEST 2: Local Override"
    
    local project_dir="$TEST_DIR/test-project-2"
    mkdir -p "$project_dir"
    
    setup_gitpm_in_project "$project_dir"
    cd "$project_dir"
    
    mkdir -p "$TEST_DIR/local-dev/utils"
    echo "def hello():\n    return 'Hello from LOCAL dev'" > "$TEST_DIR/local-dev/utils/utils.py"
    echo "# Local Development Version" > "$TEST_DIR/local-dev/utils/README.md"
    
    cat > git-pm.yaml << EOF
packages:
  utils:
    repo: file://$TEST_DIR/mock-repos/test-repo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
EOF
    
    cat > git-pm.local.yaml << EOF
overrides:
  utils:
    type: local
    path: $TEST_DIR/local-dev/utils
EOF
    
    print_info "Created local override"
    run_gitpm install
    
    if [ -d ".git-packages/utils" ]; then
        if [ -f ".git-packages/utils/utils.py" ]; then
            print_success "Local override applied"
        else
            print_error "Local override files not found"
            return 1
        fi
    else
        print_error "Package directory not created"
        return 1
    fi
    
    cd "$TEST_DIR"
}

test_list_command() {
    print_header "TEST 3: List Command"
    
    local project_dir="$TEST_DIR/test-project-3"
    mkdir -p "$project_dir"
    
    setup_gitpm_in_project "$project_dir"
    cd "$project_dir"
    
    cat > git-pm.yaml << EOF
packages:
  utils:
    repo: file://$TEST_DIR/mock-repos/test-repo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
EOF
    
    run_gitpm install > /dev/null 2>&1
    
    print_info "Running list command..."
    run_gitpm list
    
    print_success "List command executed"
    cd "$TEST_DIR"
}

test_update_command() {
    print_header "TEST 4: Update Command"
    
    local project_dir="$TEST_DIR/test-project-4"
    mkdir -p "$project_dir"
    
    setup_gitpm_in_project "$project_dir"
    cd "$project_dir"
    
    cat > git-pm.yaml << EOF
packages:
  utils:
    repo: file://$TEST_DIR/mock-repos/test-repo
    path: packages/utils
    ref:
      type: branch
      value: develop
EOF
    
    run_gitpm install > /dev/null 2>&1
    
    print_info "Running update command..."
    run_gitpm update
    
    print_success "Update command executed"
    cd "$TEST_DIR"
}

test_clean_command() {
    print_header "TEST 5: Clean Command"
    
    local project_dir="$TEST_DIR/test-project-5"
    mkdir -p "$project_dir"
    
    setup_gitpm_in_project "$project_dir"
    cd "$project_dir"
    
    cat > git-pm.yaml << EOF
packages:
  utils:
    repo: file://$TEST_DIR/mock-repos/test-repo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
EOF
    
    run_gitpm install > /dev/null 2>&1
    
    if [ ! -d ".git-packages/utils" ]; then
        print_error "Package not installed before clean"
        return 1
    fi
    
    print_info "Running clean command..."
    run_gitpm clean
    
    if [ ! -d ".git-packages" ]; then
        print_success "Packages cleaned successfully"
    else
        print_error "Packages directory still exists after clean"
        return 1
    fi
    
    cd "$TEST_DIR"
}

test_add_command() {
    print_header "TEST 6: Add Command"
    
    local project_dir="$TEST_DIR/test-project-6"
    mkdir -p "$project_dir"
    
    setup_gitpm_in_project "$project_dir"
    cd "$project_dir"
    
    print_info "Running add command..."
    run_gitpm add mypackage file://$TEST_DIR/mock-repos/test-repo --path packages/utils --ref-type tag --ref-value v1.0.0
    
    if [ -f "git-pm.yaml" ]; then
        print_success "Manifest created by add command"
    else
        print_error "Manifest not created"
        return 1
    fi
    
    if grep -q "mypackage" git-pm.yaml; then
        print_success "Package added to manifest"
    else
        print_error "Package not found in manifest"
        return 1
    fi
    
    cd "$TEST_DIR"
}

main() {
    print_header "Git-PM Test Suite"
    
    setup_test_env
    create_mock_repo "test-repo"
    
    git config --global --add safe.directory "$TEST_DIR/mock-repos/test-repo" 2>/dev/null || true
    export GIT_CONFIG_COUNT=1
    export GIT_CONFIG_KEY_0="safe.directory"
    export GIT_CONFIG_VALUE_0="*"
    
    case "${1:-all}" in
        "basic")
            test_basic_install
            ;;
        "override")
            test_local_override
            ;;
        "list")
            test_list_command
            ;;
        "update")
            test_update_command
            ;;
        "clean")
            test_clean_command
            ;;
        "add")
            test_add_command
            ;;
        "all")
            test_basic_install
            test_local_override
            test_list_command
            test_update_command
            test_clean_command
            test_add_command
            ;;
        *)
            echo "Usage: $0 [basic|override|list|update|clean|add|all]"
            exit 1
            ;;
    esac
    
    print_header "All Tests Completed Successfully!"
    cleanup
}

main "$@"